// Baseline TSP solver for the tsp-tsplib task: nearest-neighbour starts,
// 2-opt local search (candidate lists + don't-look bits), and double-bridge
// iterated local search until the wall-clock budget runs out.
//
// usage: tsp_bin INSTANCE.tsp OUT.tour BUDGET_SECONDS [SEED]
//
// Anytime protocol: the incumbent tour is rewritten to OUT.tour (via a temp
// file + rename) after every improvement, so killing the process at any
// moment still leaves a valid best-so-far tour behind. SIGTERM flushes and
// exits.
#include <algorithm>
#include <chrono>
#include <csignal>
#include <numeric>
#include "tsplib.h"

static volatile sig_atomic_t g_term = 0;
static void on_term(int) { g_term = 1; }

using Clock = std::chrono::steady_clock;
static Clock::time_point g_deadline;
static inline bool time_up() {
    return g_term || Clock::now() >= g_deadline;
}

struct Rng {
    uint64_t s;
    explicit Rng(uint64_t seed) : s(seed ? seed : 0x9e3779b97f4a7c15ULL) {}
    uint64_t next() {
        s ^= s << 13; s ^= s >> 7; s ^= s << 17;
        return s;
    }
    int below(int n) { return (int)(next() % (uint64_t)n); }
};

struct Solver {
    const tsplib::Instance& inst;
    int n;
    bool use_matrix;
    std::vector<int32_t> mat;             // n*n, matrix mode only
    std::vector<std::vector<int>> cand;   // candidate lists (1-based cities)
    static const int K = 40;

    explicit Solver(const tsplib::Instance& i) : inst(i), n(i.n) {
        use_matrix = (n <= 6000);
        if (use_matrix) {
            mat.assign((size_t)n * n, 0);
            for (int a = 1; a <= n; a++) {
                for (int b = 1; b <= n; b++)
                    mat[(size_t)(a - 1) * n + (b - 1)] =
                        (int32_t)inst.dist(a, b);
                if ((a & 63) == 0 && time_up()) return;
            }
        }
    }
    inline int64_t d(int a, int b) const {
        return use_matrix ? mat[(size_t)(a - 1) * n + (b - 1)] : inst.dist(a, b);
    }

    void build_candidates() {
        int k = std::min(K, n - 1);
        cand.assign(n + 1, {});
        std::vector<int64_t> tmp(n + 1);
        std::vector<int> idx(n + 1);
        for (int a = 1; a <= n; a++) {
            for (int b = 1; b <= n; b++) { tmp[b] = d(a, b); idx[b] = b; }
            std::iota(idx.begin() + 1, idx.end(), 1);
            std::partial_sort(idx.begin() + 1, idx.begin() + 1 + k,
                              idx.end(),
                              [&](int x, int y) { return tmp[x] < tmp[y]; });
            cand[a].assign(idx.begin() + 1, idx.begin() + 1 + k);
            if ((a & 15) == 0 && time_up()) return;
        }
    }

    std::vector<int> nn_tour(int start) {
        std::vector<int> tour;
        tour.reserve(n);
        std::vector<char> used(n + 1, 0);
        int cur = start;
        tour.push_back(cur);
        used[cur] = 1;
        for (int step = 1; step < n; step++) {
            int best = -1;
            int64_t bd = INT64_MAX;
            for (int v : cand[cur])
                if (!used[v] && d(cur, v) < bd) { bd = d(cur, v); best = v; }
            if (best < 0) {  // candidates exhausted: full scan
                for (int v = 1; v <= n; v++)
                    if (!used[v] && d(cur, v) < bd) { bd = d(cur, v); best = v; }
            }
            if (best < 0 || ((step & 511) == 0 && time_up())) {
                // out of time mid-tour: append the rest in index order so the
                // tour is still a valid permutation
                for (int v = 1; v <= n; v++)
                    if (!used[v]) { tour.push_back(v); used[v] = 1; }
                return tour;
            }
            tour.push_back(best);
            used[best] = 1;
            cur = best;
        }
        return tour;
    }

    int64_t length(const std::vector<int>& t) {
        int64_t s = 0;
        for (int i = 0; i < n; i++) s += d(t[i], t[(i + 1) % n]);
        return s;
    }

    // 2-opt first-improvement with candidate lists and don't-look bits.
    void two_opt(std::vector<int>& t) {
        std::vector<int> pos(n + 1);
        std::vector<char> dl(n + 1, 0);  // don't-look bits
        for (int i = 0; i < n; i++) pos[t[i]] = i;
        bool improved = true;
        while (improved && !time_up()) {
            improved = false;
            for (int i = 0; i < n && !time_up(); i++) {
                int a = t[i];
                if (dl[a]) continue;
                int b = t[(i + 1) % n];
                int64_t dab = d(a, b);
                bool moved = false;
                for (int c : cand[a]) {
                    int j = pos[c];
                    if (j == i || j == (i + 1) % n) continue;
                    // move: edges (a,b) and (c, e=t[j+1]) -> (a,c),(b,e)
                    int e = t[(j + 1) % n];
                    // require j+1 != i (handled: j != i-1 mod n when e==a)
                    if (e == a) continue;
                    int64_t delta = d(a, c) + d(b, e) - dab - d(c, e);
                    if (delta < 0) {
                        // reverse segment t[i+1 .. j]
                        int lo = (i + 1) % n, hi = j;
                        if (lo <= hi) {
                            std::reverse(t.begin() + lo, t.begin() + hi + 1);
                            for (int p = lo; p <= hi; p++) pos[t[p]] = p;
                        } else {  // wrap-around segment
                            std::vector<int> seg;
                            for (int p = lo; p < n; p++) seg.push_back(t[p]);
                            for (int p = 0; p <= hi; p++) seg.push_back(t[p]);
                            std::reverse(seg.begin(), seg.end());
                            int q = lo;
                            for (int v : seg) { t[q % n] = v; pos[v] = q % n; q++; }
                        }
                        dl[a] = dl[b] = dl[c] = dl[e] = 0;
                        improved = true;
                        moved = true;
                        break;
                    }
                }
                if (!moved) dl[a] = 1;
            }
        }
    }
};

static void write_tour(const std::string& out, const std::vector<int>& tour) {
    std::string tmp = out + ".tmp";
    FILE* f = fopen(tmp.c_str(), "w");
    if (!f) return;
    for (size_t i = 0; i < tour.size(); i++)
        fprintf(f, "%d%s", tour[i], (i + 1 < tour.size()) ? " " : "\n");
    fclose(f);
    rename(tmp.c_str(), out.c_str());
}

int main(int argc, char** argv) {
    if (argc < 4) {
        fprintf(stderr, "usage: %s INSTANCE.tsp OUT.tour BUDGET_SECONDS [SEED]\n",
                argv[0]);
        return 2;
    }
    std::signal(SIGTERM, on_term);
    std::signal(SIGINT, on_term);
    tsplib::Instance inst = tsplib::load(argv[1]);
    const std::string out = argv[2];
    double budget = atof(argv[3]);
    uint64_t seed = argc > 4 ? strtoull(argv[4], nullptr, 10) : 0;
    g_deadline = Clock::now() + std::chrono::milliseconds((int64_t)(budget * 1000));
    const int n = inst.n;

    Solver solver(inst);
    if (time_up()) return 0;
    solver.build_candidates();

    Rng rng(seed + 1);
    std::vector<int> best;
    int64_t best_len = INT64_MAX;

    // nearest-neighbour starts: city 1 plus up to 63 seeded starts
    int nstarts = std::min(n, 64);
    std::vector<int> starts = {1};
    while ((int)starts.size() < nstarts) {
        int s = 1 + rng.below(n);
        if (std::find(starts.begin(), starts.end(), s) == starts.end())
            starts.push_back(s);
    }
    for (int s : starts) {
        if (time_up()) break;
        std::vector<int> t = solver.nn_tour(s);
        solver.two_opt(t);
        int64_t L = solver.length(t);
        if (L < best_len) {
            best_len = L;
            best = t;
            write_tour(out, best);
        }
    }
    if (best.empty()) {  // deadline hit during setup: still emit *a* tour
        best = solver.nn_tour(1);
        best_len = solver.length(best);
        write_tour(out, best);
        return 0;
    }
    // iterated local search with double-bridge kicks
    std::vector<int> cur = best;
    int64_t cur_len = best_len;
    while (!time_up()) {
        std::vector<int> t = cur;
        // double-bridge: 3 random cut points, 4 segments reconnected 1-4-3-2
        int i1 = rng.below(n), i2 = rng.below(n), i3 = rng.below(n);
        if (i1 > i2) std::swap(i1, i2);
        if (i2 > i3) std::swap(i2, i3);
        if (i1 > i2) std::swap(i1, i2);
        if (i1 == i2 || i2 == i3 || i1 == 0) continue;
        std::vector<int> nt;
        nt.reserve(n);
        nt.insert(nt.end(), t.begin(), t.begin() + i1);
        nt.insert(nt.end(), t.begin() + i3, t.end());
        nt.insert(nt.end(), t.begin() + i2, t.begin() + i3);
        nt.insert(nt.end(), t.begin() + i1, t.begin() + i2);
        solver.two_opt(nt);
        int64_t L = solver.length(nt);
        if (L <= cur_len) {
            cur = nt;
            cur_len = L;
            if (L < best_len) {
                best_len = L;
                best = nt;
                write_tour(out, best);
            }
        }
    }
    write_tour(out, best);
    return 0;
}
