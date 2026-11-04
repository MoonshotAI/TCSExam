// Baseline cluster-editing solver (naive starting point for the agent).
//
// Reads an undirected graph on stdin in the PACE 2021 format:
//   - a header line "p cep n m" (vertices are 1..n);
//   - then m edge lines "u v" (undirected, 1-based).
// Lines starting with 'c' or '%' are treated as comments.
// Writes an edit set on stdout: one line "u v" per edited vertex pair
// (the pair is toggled: added if absent, deleted if present). Applying
// all edits must turn the graph into a disjoint union of cliques.
//
// Heuristic: greedy closed-neighborhood clustering. Repeatedly take a
// remaining vertex v of maximum remaining degree and compare two moves:
// declare {v} + N(v) a cluster (pay the edges leaving it plus the
// non-edges inside it), or declare {v} alone a cluster (pay all its
// remaining edges). Take whichever is cheaper; this keeps the total edit
// count below 2m and the solution printable even on huge sparse graphs.
// Deterministic and deliberately simple — there is a lot of room to
// improve (reduction rules, better pivots, local search on the
// clustering, ...).
#include <algorithm>
#include <cstdio>
#include <iostream>
#include <queue>
#include <sstream>
#include <string>
#include <vector>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    // ---- parse ----
    long n = -1;
    std::vector<std::pair<int, int>> edges;
    std::string line;
    while (std::getline(std::cin, line)) {
        if (line.empty()) continue;
        if (line.back() == '\r') line.pop_back();
        if (line.empty()) continue;
        char c = line[0];
        if (c == 'c' || c == '%') continue;
        if (c == 'p') {
            std::stringstream ss(line);
            std::string p, cep;
            long m;
            ss >> p >> cep >> n >> m;
            edges.reserve(m > 0 ? m : 0);
        } else {
            std::stringstream ss(line);
            long u, v;
            if (ss >> u >> v && n > 0 && u >= 1 && u <= n && v >= 1 && v <= n
                && u != v) {
                if (u > v) std::swap(u, v);
                edges.emplace_back((int)u - 1, (int)v - 1);
            }
        }
    }
    if (n <= 0) return 0;  // empty input -> empty edit set

    // ---- adjacency (deduplicated, sorted) ----
    std::vector<std::vector<int>> adj(n);
    for (auto [u, v] : edges) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    for (auto &a : adj) {
        std::sort(a.begin(), a.end());
        a.erase(std::unique(a.begin(), a.end()), a.end());
    }

    // ---- greedy closed-neighborhood clustering ----
    std::vector<char> alive(n, 1);
    std::vector<int> deg(n);
    for (int u = 0; u < n; ++u) deg[u] = (int)adj[u].size();
    std::priority_queue<std::pair<int, int>> heap;  // (alive degree, vertex)
    for (int u = 0; u < n; ++u) heap.emplace(deg[u], u);

    std::vector<int> in_clust(n, -1), nb_mark(n, -1);
    int stamp = 0;
    long remaining = n;
    const int CLUSTER_CAP = 20000;  // bound the O(|C|^2) addition scan

    std::vector<std::pair<int, int>> edits;
    edits.reserve(1u << 20);

    while (remaining > 0) {
        int v = -1;
        while (!heap.empty()) {
            auto [d, u] = heap.top();
            if (!alive[u]) { heap.pop(); continue; }
            if (d != deg[u]) { heap.pop(); heap.emplace(deg[u], u); continue; }
            v = u;
            heap.pop();
            break;
        }
        if (v < 0) break;  // nothing alive left in the heap

        // Candidate cluster C = {v} + alive N(v). Cost it first (one
        // linear pass): deletions = edges from C to the outside,
        // additions = non-edges inside C. If taking the whole
        // neighborhood is not cheaper than making v a singleton cluster
        // (cost = remaining degree of v), fall back to the singleton.
        ++stamp;
        std::vector<int> C;
        in_clust[v] = stamp;
        C.push_back(v);
        long deg_v = 0;  // remaining degree of v
        for (int w : adj[v])
            if (alive[w]) { in_clust[w] = stamp; C.push_back(w); ++deg_v; }
        long deletions = 0, internal2 = 0;  // internal2 = 2 * inner edges
        for (int u : C)
            for (int w : adj[u])
                if (alive[w]) {
                    if (in_clust[w] == stamp) ++internal2;
                    else ++deletions;
                }
        long sz = (long)C.size();
        long additions = sz * (sz - 1) / 2 - internal2 / 2;
        if (sz > CLUSTER_CAP || deletions + additions >= deg_v) {
            // Singleton cluster: pay every remaining edge incident to v.
            for (int w : C) in_clust[w] = -1;
            C.clear();
            in_clust[v] = stamp;
            C.push_back(v);
        }

        // Deletions: edges from C to the outside (seen once, from inside).
        // Additions: non-edges inside C (quadratic scan over the member
        // list with per-vertex neighbor marking; only reached when the
        // cluster is cheap, so additions < remaining degree of v).
        for (size_t i = 0; i < C.size(); ++i) {
            int u = C[i];
            for (int w : adj[u])
                if (alive[w]) {
                    nb_mark[w] = u;
                    if (in_clust[w] != stamp) {
                        int a = u, b = w;
                        if (a > b) std::swap(a, b);
                        edits.emplace_back(a, b);
                    }
                }
            for (size_t j = i + 1; j < C.size(); ++j)
                if (nb_mark[C[j]] != u) {
                    int a = u, b = C[j];
                    if (a > b) std::swap(a, b);
                    edits.emplace_back(a, b);
                }
        }
        for (int u : C)
            if (alive[u]) {
                alive[u] = 0;
                --remaining;
                for (int w : adj[u])
                    if (alive[w]) --deg[w];
            }
    }

    // ---- output: one edited pair per line ----
    std::string out;
    out.reserve(edits.size() * 12);
    char buf[32];
    for (auto [a, b] : edits) {
        int len = snprintf(buf, sizeof(buf), "%d %d\n", a + 1, b + 1);
        out.append(buf, len);
    }
    std::cout << out;
    return 0;
}
