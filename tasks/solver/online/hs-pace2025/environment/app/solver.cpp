// Baseline hitting-set solver (PACE 2025 heuristic-track format).
//
// Textbook set-cover greedy on the hypergraph: repeatedly take the vertex
// that hits the most still-unhit hyperedges, using a lazy priority queue.
// One single pass, no reduction rules, no pruning, no restarts, no local
// search. Deterministic. This is your starting point -- improve it.
//
// Input  (stdin): PACE 2025 .hgr format
//   lines starting with 'c' are comments
//   header line:  p hs <n> <m>     (n vertices numbered 1..n, m hyperedges)
//   then m lines: v1 v2 ...        (one hyperedge per line, vertex ids)
//
// Output (stdout): PACE 2025 solution format
//   line 1:  k                     (number of chosen vertices)
//   next k lines: one vertex id per line
//
// Time budget: the judge hands you the per-instance wall-clock limit (in
// seconds) through the environment variable HS_TIME_POOL. This baseline
// ignores it because a single greedy pass is fast; an improved solver
// should read it (see instruction.md) and keep a safety margin for
// printing the solution.
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    string line;
    long long n = 0, m = 0;
    vector<vector<int>> sets;
    bool header = false;
    while (getline(cin, line)) {
        if (line.empty() || line[0] == 'c') continue;
        if (!header) {
            string p, hs;
            stringstream ss(line);
            ss >> p >> hs >> n >> m;
            header = true;
        } else {
            stringstream ss(line);
            vector<int> e;
            int v;
            while (ss >> v) e.push_back(v);
            if (!e.empty()) sets.push_back(std::move(e));
        }
    }

    // inc[v] = hyperedges containing v.
    vector<vector<int>> inc(n + 1);
    for (long long i = 0; i < (long long)sets.size(); ++i)
        for (int v : sets[i])
            if (v >= 1 && v <= n) inc[v].push_back((int)i);

    // cover[v] = how many still-unhit hyperedges v would newly hit.
    // Lazy max-heap over cover[].
    vector<long long> cover(n + 1);
    vector<char> in_set(n + 1, 0), hit(sets.size(), 0);
    priority_queue<pair<long long, int>> pq;
    for (long long v = 1; v <= n; ++v) {
        cover[v] = (long long)inc[v].size();
        if (cover[v] > 0) pq.push({cover[v], (int)v});
    }

    vector<int> sol;
    long long remaining = (long long)sets.size();
    while (remaining > 0 && !pq.empty()) {
        auto [c, v] = pq.top();
        pq.pop();
        if (in_set[v]) continue;
        if (c != cover[v]) { pq.push({cover[v], v}); continue; }  // stale entry
        if (c == 0) break;  // nothing left can hit anything new (should not happen)
        in_set[v] = 1;
        sol.push_back(v);
        for (int e : inc[v]) {
            if (hit[e]) continue;
            hit[e] = 1;
            --remaining;
            for (int w : sets[e]) --cover[w];
        }
    }

    printf("%zu\n", sol.size());
    for (int v : sol) printf("%d\n", v);
    return 0;
}
