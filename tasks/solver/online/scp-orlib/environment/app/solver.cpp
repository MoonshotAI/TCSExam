// Baseline set covering solver (naive starting point for the agent).
//
// Reads a set covering instance on stdin in the canonical row-major
// row-major layout (all integers, whitespace is arbitrary):
//   first two tokens: m (rows) and n (columns);
//   next n tokens:    the integer column costs c_1 .. c_n;
//   then for each row i = 1..m: k_i followed by the k_i column indices
//                     (1-based) that cover row i.
// Writes a cover on stdout: the selected column indices (1-based,
// whitespace-separated, each at most once). Nothing else on stdout.
//
// Heuristic: Chvatal-style greedy — repeatedly take the column with the
// smallest cost per newly covered row until every row is covered — followed
// by one redundancy-removal pass (selected columns are re-examined in
// decreasing cost order and dropped while every row they cover stays
// covered at least twice counting the column itself). Deterministic
// (ties always broken by the smaller column index) and fast even on the
// largest instances. It leaves a visible gap above the optimum on most
// benchmark instances. There is a lot of room to improve (better scoring
// rules, randomization + restarts, Lagrangian-relaxation guided search,
// local search / flip neighborhoods, core-problem reduction, exact
// branch-and-bound on small instances, time-pool-aware allocation, ...).
//
// The judging environment hands the remaining shared time pool to the
// solver in the environment variable SCP_TIME_POOL (seconds, wall clock).
// This baseline is effectively instantaneous and ignores it; an improved
// solver is expected to use it to decide how much effort to spend on this
// instance.
#include <algorithm>
#include <cstdlib>
#include <iostream>
#include <queue>
#include <vector>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    // ---- parse: m, n, n costs, then m row blocks ----
    long long m, n;
    if (!(std::cin >> m >> n) || m <= 0 || n <= 0) return 1;
    std::vector<long long> cost(n + 1);
    for (long long j = 1; j <= n; ++j)
        if (!(std::cin >> cost[j])) return 1;
    std::vector<std::vector<int>> rows_of(n + 1);   // column -> rows it covers
    std::vector<int> cover_count(m + 1, 0);          // per-row selected coverage
    for (long long i = 1; i <= m; ++i) {
        long long k;
        if (!(std::cin >> k)) return 1;
        for (long long t = 0; t < k; ++t) {
            long long j;
            if (!(std::cin >> j) || j < 1 || j > n) return 1;
            rows_of[j].push_back((int)i);
        }
    }

    // ---- greedy: min cost per newly covered row, lazy heap ----
    // heap entry: (key = cost_j / newly_coverable_j, column j); stale entries
    // are recomputed on pop. Ties break on the smaller column index.
    typedef std::pair<double, int> Entry;
    std::priority_queue<Entry, std::vector<Entry>, std::greater<Entry>> heap;
    std::vector<int> newly(n + 1, 0);
    for (long long j = 1; j <= n; ++j) {
        newly[j] = (int)rows_of[j].size();
        if (newly[j] > 0) heap.push({(double)cost[j] / newly[j], (int)j});
    }
    long long uncovered = m;
    std::vector<char> selected(n + 1, 0);
    while (uncovered > 0 && !heap.empty()) {
        Entry e = heap.top();
        heap.pop();
        int j = e.second;
        int cnt = 0;
        for (int i : rows_of[j])
            if (cover_count[i] == 0) ++cnt;
        if (cnt == 0) continue;               // covers nothing new
        double key = (double)cost[j] / cnt;
        if (key > e.first) {                  // stale entry: reinsert
            heap.push({key, j});
            continue;
        }
        selected[j] = 1;
        for (int i : rows_of[j]) {
            if (cover_count[i] == 0) --uncovered;
            ++cover_count[i];
        }
    }
    if (uncovered > 0) return 1;              // instance guaranteed feasible

    // ---- redundancy removal: decreasing cost, ties by index ----
    std::vector<int> sel;
    for (long long j = 1; j <= n; ++j)
        if (selected[j]) sel.push_back((int)j);
    std::stable_sort(sel.begin(), sel.end(),
                     [&](int a, int b) { return cost[a] > cost[b]; });
    for (int j : sel) {
        bool redundant = true;
        for (int i : rows_of[j])
            if (cover_count[i] < 2) { redundant = false; break; }
        if (redundant) {
            selected[j] = 0;
            for (int i : rows_of[j]) --cover_count[i];
        }
    }

    // ---- output: selected columns, ascending, space-separated ----
    bool first = true;
    for (long long j = 1; j <= n; ++j) {
        if (!selected[j]) continue;
        if (!first) std::cout << ' ';
        std::cout << j;
        first = false;
    }
    std::cout << '\n';
    return 0;
}
