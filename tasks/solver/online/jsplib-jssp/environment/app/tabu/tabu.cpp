// Tabu search for JSSP (second engine for the K reference values of the
// freshly generated hidden instances; also serves as the task author's
// "improved submission" calibration arm).
//
// Contract: tabu INSTANCE_FILE OUTPUT_FILE LIMIT_SECONDS [SEED]
// Anytime: OUTPUT_FILE is atomically rewritten on every improvement.
//
// Method: Nowicki-Smutnicki style tabu search over machine sequences.
//   - state: per-machine operation order; objective = makespan of the
//     semi-active schedule (longest path in the disjunctive graph)
//   - neighbourhood N1: swap the first two / last two operations of every
//     critical block (a maximal run of same-machine operations on one
//     critical path)
//   - tabu table on (machine, jobA, jobB) with tenure, aspiration by
//     global-best
//   - restart from a randomized Giffler-Thompson schedule when stuck
// Deterministic: fixed-seed xorshift; wall-clock only bounds the budget.

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <numeric>
#include <string>
#include <vector>

using namespace std;

static int N, M;
static vector<vector<int>> mach, proc;
static chrono::steady_clock::time_point T0;
static double TIME_LIMIT;
static uint64_t RNG_STATE;

static inline uint64_t xrand() {
    uint64_t x = RNG_STATE;
    x ^= x << 13; x ^= x >> 7; x ^= x << 17;
    RNG_STATE = x;
    return x;
}
static inline int randint(int n) { return n <= 1 ? 0 : int(xrand() % n); }

static void load(const char* path) {
    ifstream in(path);
    if (!in) { fprintf(stderr, "cannot open %s\n", path); exit(1); }
    in >> N >> M;
    mach.assign(N, vector<int>(M));
    proc.assign(N, vector<int>(M));
    for (int j = 0; j < N; j++)
        for (int k = 0; k < M; k++)
            if (!(in >> mach[j][k] >> proc[j][k])) {
                fprintf(stderr, "bad instance at job %d op %d\n", j, k);
                exit(1);
            }
}

struct Sched {
    vector<vector<pair<int,int>>> seq;
    int makespan = -1;
};

static int evaluate(const Sched& S, vector<vector<int>>& st) {
    st.assign(N, vector<int>(M, 0));
    vector<int> jobnext(N, 0), jobfree(N, 0), mpos(M, 0), mfree(M, 0);
    int remaining = N * M;
    while (remaining > 0) {
        bool progress = false;
        for (int m = 0; m < M; m++) {
            if (mpos[m] >= (int)S.seq[m].size()) continue;
            auto [j, k] = S.seq[m][mpos[m]];
            if (jobnext[j] != k) continue;
            int s = max(jobfree[j], mfree[m]);
            st[j][k] = s;
            jobfree[j] = s + proc[j][k];
            mfree[m] = s + proc[j][k];
            jobnext[j]++;
            mpos[m]++;
            remaining--;
            progress = true;
        }
        if (!progress) return INT32_MAX / 2;
    }
    int ms = 0;
    for (int j = 0; j < N; j++) ms = max(ms, jobfree[j]);
    return ms;
}

static Sched giffler_thompson(int randmix) {
    vector<int> jobop(N, 0), jobfree(N, 0), mfree(M, 0), remwork(N);
    for (int j = 0; j < N; j++)
        remwork[j] = accumulate(proc[j].begin(), proc[j].end(), 0);
    Sched S;
    S.seq.assign(M, {});
    int left = N * M;
    while (left > 0) {
        int bestc = INT32_MAX, bm = -1, bj = -1;
        vector<int> es(N, -1), ec(N, -1);
        for (int j = 0; j < N; j++) {
            if (jobop[j] >= M) continue;
            int k = jobop[j], m = mach[j][k];
            es[j] = max(jobfree[j], mfree[m]);
            ec[j] = es[j] + proc[j][k];
            if (ec[j] < bestc) { bestc = ec[j]; bm = m; bj = j; }
        }
        // conflict set (zero-duration safe: o* included explicitly)
        vector<int> cand;
        for (int j = 0; j < N; j++) {
            if (jobop[j] >= M) continue;
            int k = jobop[j];
            if (mach[j][k] == bm && (es[j] < bestc || j == bj))
                cand.push_back(j);
        }
        int pick;
        if (randmix > 0 && randint(100) < randmix) {
            pick = cand[randint((int)cand.size())];
        } else {
            pick = cand[0];
            for (int j : cand) {
                int k = jobop[j];
                if (remwork[j] > remwork[pick]) pick = j;   // MWR
            }
        }
        int k = jobop[pick];
        S.seq[bm].push_back({pick, k});
        int s = max(jobfree[pick], mfree[bm]);
        jobfree[pick] = s + proc[pick][k];
        mfree[bm] = s + proc[pick][k];
        remwork[pick] -= proc[pick][k];
        jobop[pick]++;
        left--;
    }
    return S;
}

// critical blocks: for each machine, the maximal runs of operations whose
// start+tail equals the makespan (both endpoints swappable per N1).
struct Move { int m, i; };                 // swap seq[m][i] and seq[m][i+1]

static vector<Move> n1_moves(const Sched& S, const vector<vector<int>>& st,
                             int ms, const vector<vector<int>>& tail) {
    vector<Move> out;
    vector<vector<char>> crit(N, vector<char>(M, 0));
    for (int j = 0; j < N; j++)
        for (int k = 0; k < M; k++)
            crit[j][k] = (st[j][k] + tail[j][k] == ms);
    for (int m = 0; m < M; m++) {
        const auto& v = S.seq[m];
        int i = 0;
        while (i < (int)v.size()) {
            if (!crit[v[i].first][v[i].second]) { i++; continue; }
            int j = i;
            while (j + 1 < (int)v.size() && crit[v[j+1].first][v[j+1].second])
                j++;
            // block [i..j]; N1: swap first pair and last pair
            if (j > i) {
                out.push_back({m, i});
                if (j - 1 != i) out.push_back({m, j - 1});
            }
            i = j + 1;
        }
    }
    return out;
}

static void compute_tail(const Sched& S, const vector<vector<int>>& st,
                         int ms, vector<vector<int>>& tail) {
    tail.assign(N, vector<int>(M, 0));
    vector<vector<int>> mpos(N, vector<int>(M));
    for (int m = 0; m < M; m++)
        for (int i = 0; i < (int)S.seq[m].size(); i++)
            mpos[S.seq[m][i].first][S.seq[m][i].second] = i;
    vector<tuple<int,int,int>> ops;
    for (int j = 0; j < N; j++)
        for (int k = 0; k < M; k++)
            ops.emplace_back(st[j][k], j, k);
    sort(ops.begin(), ops.end(), greater<>());
    for (auto& [s, j, k] : ops) {
        int m = mach[j][k];
        int t = proc[j][k];             // include self: tail = longest path to sink
        if (k + 1 < M) t = max(t, proc[j][k] + tail[j][k + 1]);
        int pi = mpos[j][k];
        if (pi + 1 < (int)S.seq[m].size()) {
            auto [nj, nk] = S.seq[m][pi + 1];
            t = max(t, proc[j][k] + tail[nj][nk]);
        }
        tail[j][k] = t;
    }
}

int main(int argc, char** argv) {
    if (argc < 4) {
        fprintf(stderr, "usage: %s INSTANCE OUTPUT LIMIT_SECONDS [SEED]\n", argv[0]);
        return 2;
    }
    T0 = chrono::steady_clock::now();
    TIME_LIMIT = atof(argv[3]);
    RNG_STATE = argc > 4 ? strtoull(argv[4], nullptr, 10) : 88172645463325252ULL;
    double budget = TIME_LIMIT * 0.96;
    load(argv[1]);

    auto elapsed = [&]() {
        return chrono::duration<double>(chrono::steady_clock::now() - T0).count();
    };
    auto write_solution = [&](const Sched& S) {
        vector<vector<int>> st;
        evaluate(S, st);
        string tmp = string(argv[2]) + ".tmp";
        {
            ofstream out(tmp);
            for (int j = 0; j < N; j++) {
                for (int k = 0; k < M; k++) {
                    if (k) out << ' ';
                    out << st[j][k];
                }
                out << '\n';
            }
        }
        rename(tmp.c_str(), argv[2]);
    };

    Sched best;
    int bestms = INT32_MAX;
    vector<vector<int>> tabu(M, vector<int>(N * N, 0));  // per machine, job-pair key -> iter banned until
    int iter = 0;
    const int TENURE = 8 + (N + M) / 10;

    Sched cur = giffler_thompson(10);
    vector<vector<int>> st, tail;
    int curms = evaluate(cur, st);
    if (curms < bestms) {
        bestms = curms; best = cur; write_solution(best);
    }
    int since_improve = 0;

    while (elapsed() < budget) {
        iter++;
        compute_tail(cur, st, curms, tail);
        vector<Move> moves = n1_moves(cur, st, curms, tail);
        int bmv = -1, bval = INT32_MAX;
        vector<vector<int>> tmp;
        for (int t = 0; t < (int)moves.size(); t++) {
            Move mv = moves[t];
            auto& v = cur.seq[mv.m];
            int j1 = v[mv.i].first, j2 = v[mv.i + 1].first;
            int key = min(j1, j2) * N + max(j1, j2);
            swap(v[mv.i], v[mv.i + 1]);
            int val = evaluate(cur, tmp);
            swap(v[mv.i], v[mv.i + 1]);
            bool tabu_now = tabu[mv.m][key] > iter;
            if (tabu_now && val >= bestms) continue;   // aspiration: allow if beats global best
            if (val < bval) { bval = val; bmv = t; }
        }
        if (bmv < 0) {                                  // nothing admissible: restart
            cur = giffler_thompson(25);
            curms = evaluate(cur, st);
            if (curms < bestms) {
                bestms = curms; best = cur; write_solution(best);
            }
            since_improve = 0;
            continue;
        }
        Move mv = moves[bmv];
        auto& v = cur.seq[mv.m];
        int j1 = v[mv.i].first, j2 = v[mv.i + 1].first;
        int key = min(j1, j2) * N + max(j1, j2);
        swap(v[mv.i], v[mv.i + 1]);
        tabu[mv.m][key] = iter + TENURE + randint(5);
        curms = bval;
        if (curms < bestms) {
            bestms = curms;
            best = cur;
            best.makespan = curms;
            write_solution(best);
            since_improve = 0;
        } else {
            since_improve++;
            if (since_improve > 400) {                  // stagnation: kick
                cur = giffler_thompson(25);
                curms = evaluate(cur, st);
                if (curms < bestms) {
                    bestms = curms; best = cur; write_solution(best);
                }
                since_improve = 0;
            }
        }
    }
    if (bestms == INT32_MAX) {
        best = giffler_thompson(0);
        write_solution(best);
    }
    fprintf(stderr, "tabu done: best=%d iters=%d\n", bestms, iter);
    return 0;
}
