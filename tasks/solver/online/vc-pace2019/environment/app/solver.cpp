// Naive exact minimum-vertex-cover solver (baseline for vc-pace2019).
//
// Reads a graph in the PACE 2019 .gr format from stdin:
//   lines starting with 'c' are comments;
//   header line "p td <n> <m>";
//   then m edge lines "<u> <v>" (vertices numbered 1..n, undirected).
//
// On completion it prints a minimum vertex cover in the PACE 2019 .vc
// format on stdout:
//   one header line "s vc <n> <k>";
//   then k lines, one vertex number each.
// It prints nothing before the search completes: this solver only ever
// reports PROVEN optima. When the environment variable VC_TIME_LIMIT
// (seconds) is set and the search exceeds it, the solver exits quietly
// with no output (the instance then simply counts as unsolved).
//
// Algorithm (deliberately textbook):
//   * reductions applied exhaustively at every search node:
//       - isolated vertices are dropped;
//       - a degree-1 vertex u with neighbor v: taking v is never worse
//         than taking u, so take v and delete both;
//   * prune with a lower bound: taken so far + size of a greedily built
//     maximal matching of the remaining graph >= best solution found;
//   * otherwise branch on a maximum-degree vertex v:
//       branch 1: take v; branch 2: take all neighbors of v.
//
// There is no kernelization beyond the degree rules, no LP bound, no
// component splitting, no reduction-based branching — that headroom is
// the point of the task.

#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

static int n;
static long long m_declared;
static std::vector<std::vector<int>> adj;   // 0-based adjacency, deduplicated
static std::vector<char> alive0;            // vertices present at the root

static double time_limit = -1.0;            // seconds; <0 = no internal limit
static std::chrono::steady_clock::time_point t_start;
static bool time_up = false;

static std::vector<int> best_cover;         // best proven cover so far (0-based)
static bool have_cover = false;

static inline double elapsed() {
    return std::chrono::duration<double>(
        std::chrono::steady_clock::now() - t_start).count();
}

static inline void check_clock() {
    if (time_limit >= 0.0 && elapsed() > time_limit) time_up = true;
}

// Degree of v among alive vertices; last alive neighbor via *last_nb.
static int alive_degree(const std::vector<std::vector<int>>& g,
                        const std::vector<char>& alive, int v, int* last_nb) {
    int deg = 0;
    if (last_nb) *last_nb = -1;
    for (int u : g[v])
        if (alive[u]) { ++deg; if (last_nb) *last_nb = u; }
    return deg;
}

// Solve the subproblem induced by `alive`. `taken` accumulates the vertices
// chosen on the path to this node. On completion of a leaf, updates
// best_cover / have_cover.
//
// Memory guard: every recursion level holds an O(n) copy of the alive
// flags plus the worklist, so depth x n ~ 10n bytes per level. On huge
// graphs with a large surviving kernel this would otherwise OOM the
// machine long before the time limit; a search that deep never completes
// within the budget anyway, so we exit quietly (no output -> unsolved),
// which is exactly the outcome a timeout or an OOM kill would produce.
static void solve(std::vector<std::vector<int>>& g,
                  std::vector<char>& alive,
                  std::vector<int>& taken, int depth) {
    static long long tick = 0;
    if ((++tick & 0xFFF) == 0) {
        check_clock();
        if (time_up) return;
    }
    if (10.0 * (double)n * (double)(depth + 1) > 1.8e9) {
        time_up = true;                     // reuse the quiet-exit path
        return;
    }

    // --- reductions (degree 0 / degree 1), exhaustively, with a worklist ---
    // (a full rescan after every single fold would be quadratic on
    // chain-heavy graphs)
    std::vector<int> work;
    work.reserve(n);
    for (int v = 0; v < n; ++v) if (alive[v]) work.push_back(v);
    long long red_tick = 0;
    while (!work.empty()) {
        if ((++red_tick & 0xFFF) == 0) {
            check_clock();
            if (time_up) return;
        }
        int v = work.back();
        work.pop_back();
        if (!alive[v]) continue;
        int nb = -1;
        int deg = alive_degree(g, alive, v, &nb);
        if (deg == 0) {
            alive[v] = 0;                   // covers nothing; drop
        } else if (deg == 1) {
            // taking the neighbor nb is never worse than taking v:
            // take nb, drop both, and re-check the affected neighborhood
            alive[v] = 0;
            alive[nb] = 0;
            taken.push_back(nb);
            for (int u : g[nb]) if (alive[u]) work.push_back(u);
        }
    }

    // --- remaining edge count; leaf when no edges survive ---
    long long edges = 0;
    int max_deg = 0, pivot = -1;
    for (int v = 0; v < n; ++v) {
        if (!alive[v]) continue;
        int deg = 0;
        for (int u : g[v]) if (alive[u]) ++deg;
        edges += deg;
        if (deg > max_deg) { max_deg = deg; pivot = v; }
    }
    edges /= 2;
    if (edges == 0) {
        if (!have_cover || taken.size() < best_cover.size()) {
            best_cover = taken;
            have_cover = true;
        }
        return;
    }

    // --- lower bound: greedy maximal matching ---
    // Every matching edge needs a distinct endpoint in any cover.
    {
        long long matching = 0;
        std::vector<char> used(n, 0);
        for (int v = 0; v < n; ++v) {
            if (!alive[v] || used[v]) continue;
            for (int u : g[v]) {
                if (alive[u] && !used[u]) {
                    used[v] = 1; used[u] = 1;
                    ++matching;
                    break;
                }
            }
        }
        if (have_cover &&
            (long long)taken.size() + matching >= (long long)best_cover.size())
            return;                          // cannot improve
    }

    // --- branch on the maximum-degree vertex ---
    // Branch 1: take the pivot itself.
    {
        std::vector<char> alive1(alive);
        std::vector<int> taken1(taken);
        alive1[pivot] = 0;
        taken1.push_back(pivot);
        solve(g, alive1, taken1, depth + 1);
        if (time_up) return;
    }
    // Branch 2: pivot stays out, so all its neighbors must go in.
    {
        std::vector<char> alive2(alive);
        std::vector<int> taken2(taken);
        alive2[pivot] = 0;                   // not taken, but resolved
        for (int u : g[pivot]) {
            if (alive2[u]) { alive2[u] = 0; taken2.push_back(u); }
        }
        solve(g, alive2, taken2, depth + 1);
    }
}

int main() {
    t_start = std::chrono::steady_clock::now();
    const char* tl = getenv("VC_TIME_LIMIT");
    if (tl) time_limit = atof(tl);

    // --- parse PACE 2019 .gr from stdin ---
    char line[256];
    bool have_header = false;
    std::vector<std::pair<int, int>> edges;
    while (fgets(line, sizeof(line), stdin)) {
        if (line[0] == 'c' || line[0] == '\n' || line[0] == '\0') continue;
        if (line[0] == 'p') {
            char tag[8];
            if (sscanf(line, "p %7s %d %lld", tag, &n, &m_declared) != 3) {
                fprintf(stderr, "bad header\n");
                return 1;
            }
            have_header = true;
            adj.assign(n, {});
            continue;
        }
        if (!have_header) { fprintf(stderr, "edge before header\n"); return 1; }
        int u, v;
        if (sscanf(line, "%d %d", &u, &v) != 2) continue;
        if (u < 1 || u > n || v < 1 || v > n || u == v) continue;
        edges.push_back({u - 1, v - 1});
    }
    if (!have_header) { fprintf(stderr, "no header\n"); return 1; }

    for (auto& e : edges) {
        adj[e.first].push_back(e.second);
        adj[e.second].push_back(e.first);
    }
    for (auto& lst : adj) {
        std::sort(lst.begin(), lst.end());
        lst.erase(std::unique(lst.begin(), lst.end()), lst.end());
    }

    alive0.assign(n, 1);
    std::vector<int> taken;
    std::vector<char> alive(alive0);
    solve(adj, alive, taken, 0);

    if (time_up || !have_cover) return 0;    // no proven optimum -> no output

    std::sort(best_cover.begin(), best_cover.end());
    best_cover.erase(std::unique(best_cover.begin(), best_cover.end()),
                     best_cover.end());
    printf("s vc %d %zu\n", n, best_cover.size());
    for (int v : best_cover) printf("%d\n", v + 1);
    return 0;
}
