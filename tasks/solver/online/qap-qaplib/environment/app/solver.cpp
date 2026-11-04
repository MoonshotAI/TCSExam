// Baseline QAP solver (naive starting point for the agent).
//
// Reads a quadratic assignment problem on stdin in the instance text format:
//   first token: n (facilities = locations = n);
//   next n*n tokens: flow matrix F, row by row;
//   next n*n tokens: distance matrix D, row by row.
// The cost of a permutation p (p[i] = location of facility i) is
//   sum_{i,j} F[i][j] * D[p[i]][p[j]].
// Writes a permutation on stdout: n integers from 1..n (whitespace
// separated), where token i is the location assigned to facility i.
//
// Heuristic: random restarts + first-improvement 2-swap local search.
// Deterministic seed, bounded number of restarts, and a small wall-clock
// cap derived from the remaining time pool (env QAP_TIME_POOL) so that it
// never endangers the pool for later instances. Deliberately simple —
// there is a lot of room to improve (tabu search, simulated annealing,
// better diversification, problem-specific structure, ...).
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <random>
#include <vector>

static int n;
static std::vector<std::vector<long long>> F, D;

static long long cost_of(const std::vector<int>& p) {
    long long c = 0;
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < n; ++j)
            c += F[i][j] * D[p[i]][p[j]];
    return c;
}

// Change in cost when swapping the occupants of positions r and s. O(n).
static long long delta_swap(const std::vector<int>& p, int r, int s) {
    int a = p[r], b = p[s];
    long long d = 0;
    for (int k = 0; k < n; ++k) {
        if (k == r || k == s) continue;
        int pk = p[k];
        d += F[r][k] * (D[b][pk] - D[a][pk]);
        d += F[k][r] * (D[pk][b] - D[pk][a]);
        d += F[s][k] * (D[a][pk] - D[b][pk]);
        d += F[k][s] * (D[pk][a] - D[pk][b]);
    }
    d += F[r][r] * (D[b][b] - D[a][a]);
    d += F[s][s] * (D[a][a] - D[b][b]);
    d += F[r][s] * (D[b][a] - D[a][b]);
    d += F[s][r] * (D[a][b] - D[b][a]);
    return d;
}

// First-improvement 2-swap descent until a local optimum.
static void local_search(std::vector<int>& p, long long& cur) {
    bool improved = true;
    while (improved) {
        improved = false;
        for (int r = 0; r < n && !improved; ++r)
            for (int s = r + 1; s < n; ++s) {
                long long d = delta_swap(p, r, s);
                if (d < 0) {
                    std::swap(p[r], p[s]);
                    cur += d;
                    improved = true;
                    break;
                }
            }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    // ---- parse: n, then F (n*n), then D (n*n) ----
    if (!(std::cin >> n) || n <= 0) return 1;
    F.assign(n, std::vector<long long>(n));
    D.assign(n, std::vector<long long>(n));
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < n; ++j)
            if (!(std::cin >> F[i][j])) return 1;
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < n; ++j)
            if (!(std::cin >> D[i][j])) return 1;

    // ---- budget: a small fixed cap, never a threat to the shared pool ----
    double pool = 30.0;
    const char* env = std::getenv("QAP_TIME_POOL");
    if (env) pool = std::max(0.0, std::atof(env));
    double cap = std::min(8.0, pool * 0.1);
    auto t0 = std::chrono::steady_clock::now();
    auto time_up = [&] {
        return std::chrono::duration<double>(std::chrono::steady_clock::now() - t0)
                   .count() > cap;
    };

    std::mt19937 rng(12345);
    std::vector<int> best(n);
    for (int i = 0; i < n; ++i) best[i] = i;
    long long best_cost = cost_of(best);

    // Random restarts + 2-swap descent; at most 100 restarts.
    for (int restart = 0; restart < 100 && !time_up(); ++restart) {
        std::vector<int> p(n);
        for (int i = 0; i < n; ++i) p[i] = i;
        for (int i = n - 1; i > 0; --i)
            std::swap(p[i], p[rng() % (i + 1)]);
        long long cur = cost_of(p);
        local_search(p, cur);
        if (cur < best_cost) {
            best_cost = cur;
            best = p;
        }
    }

    // ---- output: 1-based permutation ----
    for (int i = 0; i < n; ++i) {
        if (i) std::cout << ' ';
        std::cout << best[i] + 1;
    }
    std::cout << '\n';
    return 0;
}
