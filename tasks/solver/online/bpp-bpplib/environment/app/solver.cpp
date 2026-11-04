// Baseline BPP solver (naive starting point for the agent).
//
// Reads a one-dimensional bin packing instance on stdin in the task
// format:
//   first token:  n (number of items);
//   second token: C (bin capacity);
//   next n tokens: the integer item weights w_1 .. w_n.
// Writes a packing on stdout:
//   first token:  B (number of bins used);
//   next n tokens: the bin of each item, in input order, 1-based.
//
// Heuristic: First-Fit Decreasing (FFD) — sort items by nonincreasing
// weight (ties keep the input order), place each item into the first bin
// that can still hold it, opening a new bin when none fits. Deterministic,
// fast even on the largest instances, and deliberately simple: FFD leaves
// a gap of one or more bins above the optimum on many benchmark instances.
// There is a lot of room to improve (better construction orders, local
// search / repacking, complete methods such as bin completion or MTP-style
// branch-and-bound, instance reduction, time-pool-aware allocation, ...).
//
// The judging environment hands the remaining shared time pool to the
// solver in the environment variable BPP_TIME_POOL (seconds, wall clock).
// FFD is effectively instantaneous and ignores it; an improved solver is
// expected to use it to decide how much effort to spend on this instance.
#include <algorithm>
#include <cstdlib>
#include <iostream>
#include <vector>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    // ---- parse: n, C, then n weights ----
    long long n;
    if (!(std::cin >> n) || n <= 0) return 1;
    long long C;
    if (!(std::cin >> C) || C <= 0) return 1;
    std::vector<long long> w(n);
    for (long long i = 0; i < n; ++i)
        if (!(std::cin >> w[i])) return 1;

    // ---- First-Fit Decreasing ----
    std::vector<long long> order(n);
    for (long long i = 0; i < n; ++i) order[i] = i;
    std::stable_sort(order.begin(), order.end(),
                     [&](long long a, long long b) { return w[a] > w[b]; });

    std::vector<long long> remaining;   // remaining capacity of each open bin
    std::vector<long long> bin_of(n);   // 1-based bin index per item
    for (long long i : order) {
        long long b = -1;
        for (size_t j = 0; j < remaining.size(); ++j) {
            if (remaining[j] >= w[i]) { b = (long long)j; break; }
        }
        if (b < 0) {
            b = (long long)remaining.size();
            remaining.push_back(C);
        }
        remaining[b] -= w[i];
        bin_of[i] = b + 1;
    }

    // ---- output: B, then the bin of every item in input order ----
    std::cout << remaining.size() << "\n";
    for (long long i = 0; i < n; ++i) {
        if (i) std::cout << ' ';
        std::cout << bin_of[i];
    }
    std::cout << '\n';
    return 0;
}
