// Baseline dominating-set solver (PACE 2025 heuristic-track format).
//
// Textbook set-cover greedy: repeatedly take the vertex whose closed
// neighborhood covers the most still-undominated vertices, using a lazy
// priority queue. One single pass, no pruning, no restarts, no local
// search. Deterministic. This is your starting point -- improve it.
//
// Input  (stdin): PACE 2025 .gr format
//   lines starting with 'c' are comments
//   header line:  p ds <n> <m>     (vertices are numbered 1..n)
//   then m lines: u v              (undirected edges)
//
// Output (stdout): PACE 2025 solution format
//   line 1:  k                     (number of chosen vertices)
//   next k lines: one vertex id per line
//
// Time budget: the judge hands you the remaining total time pool (in
// seconds) through the environment variable DS_TIME_POOL. This baseline
// ignores it because a single greedy pass is fast; an improved solver
// should read it (see instruction.md) and decide how much to spend.
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    string line;
    long long n = 0, m = 0;
    vector<pair<int, int>> edges;
    bool header = false;
    while (getline(cin, line)) {
        if (line.empty() || line[0] == 'c') continue;
        if (!header) {
            string p, ds;
            stringstream ss(line);
            ss >> p >> ds >> n >> m;
            header = true;
        } else {
            stringstream ss(line);
            int u, v;
            if (ss >> u >> v) edges.push_back({u, v});
        }
    }

    vector<vector<int>> adj(n + 1);
    for (auto [u, v] : edges) {
        if (u < 1 || u > n || v < 1 || v > n || u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // cover[v] = how many still-undominated vertices v would newly dominate
    // (itself plus its undominated neighbors). Lazy max-heap over cover[].
    vector<long long> cover(n + 1);
    vector<char> dominated(n + 1, 0), in_set(n + 1, 0);
    priority_queue<pair<long long, int>> pq;
    for (long long v = 1; v <= n; ++v) {
        cover[v] = 1 + (long long)adj[v].size();
        pq.push({cover[v], (int)v});
    }

    vector<int> sol;
    long long remaining = n;
    while (remaining > 0 && !pq.empty()) {
        auto [c, v] = pq.top();
        pq.pop();
        if (in_set[v]) continue;
        if (c != cover[v]) { pq.push({cover[v], v}); continue; }  // stale entry
        if (c == 0) break;  // nothing left can cover anybody new (should not happen)
        in_set[v] = 1;
        sol.push_back(v);
        auto mark = [&](int x) {
            if (dominated[x]) return;
            dominated[x] = 1;
            --remaining;
            --cover[x];
            for (int w : adj[x]) --cover[w];
        };
        mark(v);
        for (int u : adj[v]) mark(u);
    }

    printf("%zu\n", sol.size());
    for (int v : sol) printf("%d\n", v);
    return 0;
}
