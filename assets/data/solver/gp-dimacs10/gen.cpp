// Instance generators for gp-dimacs10 (judge-side tooling, NOT shipped).
//
//   gen rgg  SEED N AVGDEGE   - random geometric graph, unit square,
//                               radius chosen for the target average degree
//   gen kron SEED SCALE EF    - R-MAT Kronecker graph, Graph500 initiator
//                               (0.57, 0.19, 0.19, 0.05), n = 2^SCALE,
//                               ~EF*n sampled edges before dedup
//
// Both: duplicates and self-loops removed, largest connected component
// kept and vertices relabelled, output written to stdout in
// METIS/DIMACS10 format (header "n m", then n 1-based adjacency lines).
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <numeric>
#include <queue>
#include <random>
#include <unordered_map>
#include <utility>
#include <vector>

// ---------- largest connected component + relabel + write ----------
static void write_lcc(int n, std::vector<std::pair<int,int>>& edges) {
    std::vector<std::vector<int>> adj(n);
    for (auto& e : edges) {
        adj[e.first].push_back(e.second);
        adj[e.second].push_back(e.first);
    }
    std::vector<int> comp(n, -1);
    int best_id = -1, best_sz = -1, ncomp = 0;
    for (int s = 0; s < n; ++s) {
        if (comp[s] != -1) continue;
        int sz = 0;
        std::queue<int> q;
        q.push(s);
        comp[s] = ncomp;
        while (!q.empty()) {
            int u = q.front(); q.pop(); ++sz;
            for (int v : adj[u]) if (comp[v] == -1) { comp[v] = ncomp; q.push(v); }
        }
        if (sz > best_sz) { best_sz = sz; best_id = ncomp; }
        ++ncomp;
    }
    std::vector<int> relabel(n, -1);
    int nn = 0;
    for (int u = 0; u < n; ++u) if (comp[u] == best_id) relabel[u] = nn++;
    std::vector<std::vector<int>> out(nn);
    long long mm = 0;
    for (auto& e : edges) {
        if (comp[e.first] != best_id) continue;
        int a = relabel[e.first], b = relabel[e.second];
        out[a].push_back(b);
        out[b].push_back(a);
        ++mm;
    }
    for (auto& l : out) std::sort(l.begin(), l.end());
    std::fprintf(stdout, "%d %lld\n", nn, mm);
    for (int u = 0; u < nn; ++u) {
        for (size_t i = 0; i < out[u].size(); ++i)
            std::fprintf(stdout, "%s%d", i ? " " : "", out[u][i] + 1);
        std::fprintf(stdout, "\n");
    }
    std::fprintf(stderr, "n=%d m=%lld (dropped %d vertices outside LCC)\n",
            nn, mm, n - nn);
}

// ---------- rgg ----------
static void gen_rgg(unsigned long long seed, int n, double avgdeg) {
    std::mt19937_64 rng(seed);
    std::uniform_real_distribution<double> U(0.0, 1.0);
    std::vector<double> xs(n), ys(n);
    for (int i = 0; i < n; ++i) { xs[i] = U(rng); ys[i] = U(rng); }
    const double r = std::sqrt(avgdeg / (M_PI * n));
    const double r2 = r * r;
    const int G = std::max(1, (int)std::floor(1.0 / r));
    std::vector<std::vector<int>> cell(G * G);
    auto cid = [&](int i) {
        int cx = std::min(G - 1, (int)(xs[i] * G));
        int cy = std::min(G - 1, (int)(ys[i] * G));
        return cy * G + cx;
    };
    for (int i = 0; i < n; ++i) cell[cid(i)].push_back(i);
    std::vector<std::pair<int,int>> edges;
    for (int cy = 0; cy < G; ++cy) for (int cx = 0; cx < G; ++cx) {
        const auto& here = cell[cy * G + cx];
        for (int dy = 0; dy <= 1; ++dy) for (int dx = -1; dx <= 1; ++dx) {
            int nx = cx + dx, ny = cy + dy;
            if (nx < 0 || nx >= G || ny < 0 || ny >= G) continue;
            if (ny == cy && nx < cx) continue;          // each unordered cell pair once
            const auto& there = cell[ny * G + nx];
            const bool same = (ny == cy && nx == cx);
            for (int a : here) for (int b : there) {
                if (same && b <= a) continue;  // within one cell: dedupe only
                double ddx = xs[a] - xs[b], ddy = ys[a] - ys[b];
                if (ddx * ddx + ddy * ddy <= r2) edges.emplace_back(a, b);
            }
        }
    }
    std::sort(edges.begin(), edges.end());
    edges.erase(std::unique(edges.begin(), edges.end()), edges.end());
    write_lcc(n, edges);
}

// ---------- kronecker (R-MAT) ----------
static void gen_kron(unsigned long long seed, int scale, int ef) {
    const long long n = 1LL << scale;
    const long long target = (long long)ef * n;
    std::mt19937_64 rng(seed);
    std::uniform_real_distribution<double> U(0.0, 1.0);
    const double A = 0.57, B = 0.19, C = 0.19;  // D = 0.05
    std::vector<std::pair<int,int>> edges;
    edges.reserve(target);
    for (long long e = 0; e < target; ++e) {
        long long u = 0, v = 0;
        for (int s = 0; s < scale; ++s) {
            double p = U(rng);
            long long bit = 1LL << (scale - 1 - s);
            if (p < A) { /* 0,0 */ }
            else if (p < A + B) { v |= bit; }
            else if (p < A + B + C) { u |= bit; }
            else { u |= bit; v |= bit; }
        }
        if (u != v) edges.emplace_back((int)std::min(u, v), (int)std::max(u, v));
    }
    std::sort(edges.begin(), edges.end());
    edges.erase(std::unique(edges.begin(), edges.end()), edges.end());
    write_lcc((int)n, edges);
}

int main(int argc, char** argv) {
    if (argc < 2) {
        std::fprintf(stderr, "usage: gen rgg SEED N AVGDEG | gen kron SEED SCALE EF\n");
        return 2;
    }
    if (!std::strcmp(argv[1], "rgg") && argc == 5) {
        gen_rgg(std::strtoull(argv[2], nullptr, 10), std::atoi(argv[3]),
                std::atof(argv[4]));
        return 0;
    }
    if (!std::strcmp(argv[1], "kron") && argc == 5) {
        gen_kron(std::strtoull(argv[2], nullptr, 10), std::atoi(argv[3]),
                 std::atoi(argv[4]));
        return 0;
    }
    std::fprintf(stderr, "bad arguments\n");
    return 2;
}
