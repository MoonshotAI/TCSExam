// Baseline solver for the AHC058 "hierarchical production" task.
//
// Naive deterministic greedy: every turn, among all upgrades the current
// apples can afford, buy the CHEAPEST one (ties broken by lower level,
// then lower machine id); if nothing is affordable, do nothing (-1).
// It plays a legal game on every instance but leaves a large margin to
// any search-based approach — that margin is what your score measures.
//
// I/O contract (fixed): read the instance on stdin
//   N L T K
//   A_0 .. A_{N-1}
//   C[0][0..N-1]
//   ... (L rows)
// and print exactly T lines on stdout, each either "-1" (do nothing) or
// "<level> <id>" (buy one upgrade of machine <id> at level <level>).
//
// The remaining shared time pool is available in env AHC_TIME_POOL; this
// baseline finishes in milliseconds and ignores it.
#include <cstdio>
#include <cstdlib>
#include <vector>

using namespace std;

// The official judge simulates with signed 64-bit wrap-around; mirror it
// with unsigned storage (wraps naturally) and signed views for compares.
static inline long long s64(unsigned long long x) { return (long long)x; }

int main() {
    int N, L, T;
    long long K;
    if (scanf("%d %d %d %lld", &N, &L, &T, &K) != 4) return 1;
    vector<long long> A(N);
    for (auto &a : A) scanf("%lld", &a);
    vector<vector<long long>> C(L, vector<long long>(N));
    for (auto &row : C)
        for (auto &c : row) scanf("%lld", &c);

    vector<vector<unsigned long long>> B(L, vector<unsigned long long>(N, 1));
    vector<vector<long long>> P(L, vector<long long>(N, 0));
    unsigned long long apples = (unsigned long long)K;

    for (int t = 0; t < T; t++) {
        // Pick the cheapest affordable upgrade (tie: lower level, lower id).
        int bestL = -1, bestI = -1;
        unsigned long long bestCost = 0;
        for (int l = 0; l < L; l++)
            for (int i = 0; i < N; i++) {
                unsigned long long cost =
                    (unsigned long long)C[l][i] * (unsigned long long)(P[l][i] + 1);
                if (s64(apples) >= s64(cost) &&
                    (bestL < 0 || s64(cost) < s64(bestCost))) {
                    bestL = l; bestI = i; bestCost = cost;
                }
            }
        if (bestL < 0) {
            printf("-1\n");
        } else {
            printf("%d %d\n", bestL, bestI);
            apples -= bestCost;
            P[bestL][bestI] += 1;
        }
        // Production phase (level 0 produces apples, higher levels produce
        // machines one level below), same order as the official scorer.
        for (int l = 0; l < L; l++)
            for (int i = 0; i < N; i++) {
                if (l == 0)
                    apples += (unsigned long long)A[i] * B[0][i] * (unsigned long long)P[0][i];
                else
                    B[l - 1][i] += B[l][i] * (unsigned long long)P[l][i];
            }
    }
    return 0;
}
