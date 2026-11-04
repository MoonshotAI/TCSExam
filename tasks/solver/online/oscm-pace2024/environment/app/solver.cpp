// Baseline solver for one-sided crossing minimization (OSCM), PACE 2024.
//
// The textbook two-phase constructive heuristic (Sugiyama-style layered
// drawing): start from the barycenter ordering (each free vertex at the
// average position of its neighbors), then polish it with deterministic
// local search — adjacent-exchange sweeps plus sifting passes — until no
// further improvement is found. This is the classic "off-the-shelf" method;
// beating it needs stronger ideas (smarter neighborhoods, multi-start
// diversification, reduction rules, exact methods for hard cores).
//
// The solver is deterministic: termination is by convergence, not by wall
// clock, so the same input always yields the same output.
//
// I/O contract (fixed — do not change):
//   stdin : PACE 2024 .gr format —
//             lines starting with 'c' are comments;
//             "p ocr n1 n2 m" declares n1 fixed-layer vertices (1..n1),
//             n2 free-layer vertices (n1+1 .. n1+n2) and m edges;
//             then m lines "u v" with u <= v.
//   stdout: one free-layer vertex per line — the computed ordering of ALL
//           n2 free vertices (a permutation of n1+1 .. n1+n2), nothing else.
//
// The score of an ordering is its number of edge crossings (fewer = better).

#include <algorithm>
#include <cstdio>
#include <iostream>
#include <numeric>
#include <string>
#include <vector>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(nullptr);

    long long n1 = 0, n2 = 0, m = 0;
    bool have_header = false;
    std::string line;
    while (std::getline(std::cin, line)) {
        if (line.empty() || line[0] == 'c') continue;
        if (sscanf(line.c_str(), "p ocr %lld %lld %lld", &n1, &n2, &m) == 3) {
            have_header = true;
            break;
        }
    }
    if (!have_header) return 0;

    // Adjacency of free vertices (fixed endpoints), 0-based free indices.
    std::vector<std::vector<int>> adj(n2);
    long long u, v;
    while (std::cin >> u >> v) {
        if (u > v) std::swap(u, v);
        if (v >= 1 && v <= n1 && u > n1) std::swap(u, v);
        if (u >= 1 && u <= n1 && v > n1 && v <= n1 + n2)
            adj[v - (n1 + 1)].push_back((int)u);
    }
    for (auto &a : adj) std::sort(a.begin(), a.end());

    // Phase 1: barycenter ordering (isolated vertices last — crossing-free).
    std::vector<long long> bsum(n2, 0);
    for (int a = 0; a < n2; a++)
        for (int x : adj[a]) bsum[a] += x;
    std::vector<int> ord(n2);
    std::iota(ord.begin(), ord.end(), 0);
    std::stable_sort(ord.begin(), ord.end(), [&](int a, int b) {
        const auto &A = adj[a], &B = adj[b];
        if (A.empty() != B.empty()) return B.empty();
        if (A.empty()) return a < b;
        __int128 lhs = (__int128)bsum[a] * (long long)B.size();
        __int128 rhs = (__int128)bsum[b] * (long long)A.size();
        if (lhs != rhs) return lhs < rhs;
        return a < b;
    });

    std::vector<int> at(n2);
    for (int i = 0; i < n2; i++) at[ord[i]] = i;

    // Crossings between the edges of free vertex a (placed left) and free
    // vertex b (placed right): pairs (x in adj[a], y in adj[b]) with x > y.
    auto cross_uv = [&](int a, int b) -> long long {
        const auto &A = adj[a], &B = adj[b];
        long long c = 0;
        size_t j = 0;
        for (size_t i = 0; i < A.size(); i++) {
            while (j < B.size() && B[j] < A[i]) j++;
            c += (long long)j;
        }
        return c;
    };

    // Phase 2a: adjacent-exchange sweeps until convergence.
    bool improved = true;
    while (improved) {
        improved = false;
        for (int i = 0; i + 1 < n2; i++) {
            int a = ord[i], b = ord[i + 1];
            if (cross_uv(b, a) < cross_uv(a, b)) {
                std::swap(ord[i], ord[i + 1]);
                at[a] = i + 1;
                at[b] = i;
                improved = true;
            }
        }
    }

    // Phase 2b: sifting passes until convergence — reinsert each vertex at
    // its cheapest position (cumulative adjacent-swap deltas).
    bool any = true;
    while (any) {
        any = false;
        for (int vv = 0; vv < n2; vv++) {
            int cur = at[vv];
            int best = cur;
            long long bestdelta = 0, acc = 0;
            for (int i = cur - 1; i >= 0; i--) {
                int x = ord[i];
                acc += cross_uv(vv, x) - cross_uv(x, vv);
                if (acc < bestdelta) { bestdelta = acc; best = i; }
            }
            acc = 0;
            for (int i = cur + 1; i < n2; i++) {
                int x = ord[i];
                acc += cross_uv(x, vv) - cross_uv(vv, x);
                if (acc < bestdelta) { bestdelta = acc; best = i; }
            }
            if (best != cur) {
                int x = ord[cur];
                if (best < cur) {
                    for (int i = cur; i > best; i--) { ord[i] = ord[i-1]; at[ord[i]] = i; }
                } else {
                    for (int i = cur; i < best; i++) { ord[i] = ord[i+1]; at[ord[i]] = i; }
                }
                ord[best] = x;
                at[x] = best;
                any = true;
            }
        }
    }

    for (int i = 0; i < n2; i++) std::cout << ord[i] + (n1 + 1) << '\n';
    return 0;
}
