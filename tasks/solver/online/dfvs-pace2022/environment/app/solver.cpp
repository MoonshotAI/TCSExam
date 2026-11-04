// Baseline DFVS solver (naive starting point for the agent).
//
// Reads a directed graph on stdin in the PACE 2022 (Metis-like) format:
//   - lines starting with '%' are comments;
//   - the first non-comment line is "n m 0" (vertices are 1..n);
//   - the next n non-comment lines are the out-adjacency lists:
//     line u lists the out-neighbors of vertex u (may be empty).
// Writes a feedback vertex set on stdout: one vertex per line.
//
// Heuristic: peel vertices with in-degree 0 or out-degree 0 (they lie on no
// directed cycle); while anything remains, delete a vertex of maximum total
// degree (in + out) and add it to the feedback set. Deterministic, fast,
// and deliberately simple — there is a lot of room to improve (SCC
// decomposition, reduction rules, local search, smarter scoring, ...).
#include <iostream>
#include <queue>
#include <sstream>
#include <string>
#include <vector>
int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    // ---- parse ----
    // Comment lines (starting with '%') are skipped anywhere. The first
    // content line is the header; every following content line is the
    // out-adjacency list of the next vertex — including EMPTY lines (a
    // vertex with no out-edges has an empty adjacency line, and skipping
    // it would shift every later vertex by one).
    std::string line;
    long n = -1;
    std::vector<std::vector<int>> adj;  // 0-based out-adjacency
    long cur = 0;                       // adjacency lines consumed so far
    while (std::getline(std::cin, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (!line.empty() && line[0] == '%') continue;
        if (n < 0) {
            if (line.empty()) continue;  // tolerate blank lines before header
            std::stringstream ss(line);
            long m, t;
            ss >> n >> m >> t;
            if (n > 0) adj.assign(n, {});
        } else {
            std::stringstream ss(line);
            long v;
            if (cur < n) {
                while (ss >> v)
                    if (v >= 1 && v <= n) adj[cur].push_back((int)v - 1);
            }
            ++cur;
        }
    }
    if (n <= 0) return 0;  // empty input -> empty answer

    // ---- data structures ----
    std::vector<std::vector<int>> pred(n);  // in-neighbors
    std::vector<int> indeg(n, 0), outdeg(n, 0);
    std::vector<char> alive(n, 1);
    for (int u = 0; u < n; ++u) {
        outdeg[u] = (int)adj[u].size();
        for (int v : adj[u]) {
            ++indeg[v];
            pred[v].push_back(u);
        }
    }

    // Removing u lowers the in-degree of its out-neighbors and the
    // out-degree of its in-neighbors; newly peelable vertices are queued.
    std::queue<int> q;
    long remaining = n;
    auto erase_vertex = [&](int u) {
        alive[u] = 0;
        --remaining;
        for (int v : adj[u])
            if (alive[v] && --indeg[v] == 0) q.push(v);
        for (int p : pred[u])
            if (alive[p] && --outdeg[p] == 0) q.push(p);
    };

    // ---- greedy FVS ----
    // Lazy max-heap over (indeg+outdeg, vertex); degrees only decrease, so
    // stale entries are simply skipped (avoids an O(n) scan per deletion —
    // matters on the 131072-vertex instances).
    using Entry = std::pair<int, int>;  // (total degree, vertex)
    std::priority_queue<Entry> heap;
    for (int u = 0; u < n; ++u) heap.emplace(indeg[u] + outdeg[u], u);

    std::vector<int> answer;
    for (int u = 0; u < n; ++u)
        if (indeg[u] == 0 || outdeg[u] == 0) q.push(u);

    while (remaining > 0) {
        // Peel everything peelable: such vertices lie on no directed cycle,
        // so they never need to enter the feedback set.
        while (!q.empty()) {
            int u = q.front(); q.pop();
            if (alive[u] && (indeg[u] == 0 || outdeg[u] == 0)) erase_vertex(u);
        }
        if (remaining == 0) break;
        // Delete the alive vertex of maximum total degree (in + out);
        // ties break toward the smaller vertex id (deterministic).
        int best = -1;
        while (!heap.empty()) {
            auto [deg, u] = heap.top();
            if (!alive[u]) { heap.pop(); continue; }
            int cur_deg = indeg[u] + outdeg[u];
            if (deg != cur_deg) { heap.pop(); heap.emplace(cur_deg, u); continue; }
            best = u;
            break;
        }
        answer.push_back(best + 1);  // back to 1-based
        erase_vertex(best);
    }

    for (int v : answer) std::cout << v << "\n";
    return 0;
}
