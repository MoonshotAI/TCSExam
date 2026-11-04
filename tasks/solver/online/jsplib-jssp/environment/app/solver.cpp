// Baseline solver for the job-shop scheduling task.
//
// Contract: solver INSTANCE_FILE OUTPUT_FILE LIMIT_SECONDS
//   - reads a job-shop instance in the standard text format,
//   - keeps the best schedule found so far in OUTPUT_FILE at all times
//     (atomic rewrite on every improvement, so the file is always a valid
//     best-so-far answer even if the process is SIGTERMed at the limit),
//   - stops its own search at 0.92 * LIMIT_SECONDS and exits 0.
//
// Algorithm: randomized Giffler-Thompson active-schedule generation with a
// rotating set of priority rules, followed by critical-path local search
// (N1 neighbourhood: swap adjacent operations inside critical blocks).
// Deterministic: all randomness comes from a fixed-seed xorshift; the only
// wall-clock dependence is the time budget itself.
//
// This is the shipped baseline (score-0 anchor). Everything about it can be
// improved: better construction rules, deeper neighbourhoods, tabu restarts,
// or a completely different engine (a CP-SAT wrapper is in /app too).

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <numeric>
#include <sstream>
#include <string>
#include <vector>

using namespace std;

static int N, M;                       // jobs, machines
static vector<vector<int>> mach;       // mach[j][k] = machine of job j's k-th op
static vector<vector<int>> proc;       // proc[j][k] = duration
static chrono::steady_clock::time_point T0;
static double TIME_LIMIT;

static uint64_t RNG_STATE = 88172645463325252ULL;
static inline uint64_t xrand() {
    uint64_t x = RNG_STATE;
    x ^= x << 13; x ^= x >> 7; x ^= x << 17;
    RNG_STATE = x;
    return x;
}
static inline int randint(int n) { return n <= 1 ? 0 : int(xrand() % n); }

// ---- instance ----
static void load(const char* path) {
    ifstream in(path);
    if (!in) { fprintf(stderr, "cannot open %s\n", path); exit(1); }
    in >> N >> M;
    mach.assign(N, vector<int>(M));
    proc.assign(N, vector<int>(M));
    for (int j = 0; j < N; j++)
        for (int k = 0; k < M; k++)
            if (!(in >> mach[j][k] >> proc[j][k])) {
                fprintf(stderr, "bad instance format at job %d op %d\n", j, k);
                exit(1);
            }
}

// ---- schedule representation ----
// seq[m][i] = (job, op) : i-th operation executed on machine m.
// Evaluation: longest path in the disjunctive graph = earliest-start
// (semi-active) schedule respecting both job chains and machine sequences.
struct Sched {
    vector<vector<pair<int,int>>> seq;  // per machine
    int makespan = -1;
};

// earliest start times for a given machine-sequence; returns makespan and
// fills st[j][k].
static int evaluate(const Sched& S, vector<vector<int>>& st) {
    // topological walk: each op ready when job-predecessor and
    // machine-predecessor done. Process in rounds over a position index.
    st.assign(N, vector<int>(M, 0));
    vector<int> jobnext(N, 0);               // next op index per job
    vector<int> jobfree(N, 0);               // time job's next op can start
    vector<int> mpos(M, 0);                  // next position per machine
    vector<int> mfree(M, 0);                 // machine free time
    int remaining = N * M;
    while (remaining > 0) {
        bool progress = false;
        for (int m = 0; m < M; m++) {
            if (mpos[m] >= (int)S.seq[m].size()) continue;
            auto [j, k] = S.seq[m][mpos[m]];
            if (jobnext[j] != k) continue;   // job predecessor not scheduled
            int s = max(jobfree[j], mfree[m]);
            st[j][k] = s;
            jobfree[j] = s + proc[j][k];
            mfree[m] = s + proc[j][k];
            jobnext[j]++;
            mpos[m]++;
            remaining--;
            progress = true;
        }
        if (!progress) return INT32_MAX / 2; // cycle -> invalid (shouldn't happen)
    }
    int ms = 0;
    for (int j = 0; j < N; j++) ms = max(ms, jobfree[j]);
    return ms;
}

// ---- Giffler-Thompson active schedule generation ----
// rule: 0=SPT 1=LPT 2=MWR 3=LWR 4=MOR 5=LOR 6=FCFS ; randmix in [0,100]:
// probability (percent) of picking a random conflict-set member instead.
static Sched giffler_thompson(int rule, int randmix) {
    vector<int> jobop(N, 0);                 // next op per job
    vector<int> jobfree(N, 0);
    vector<int> mfree(M, 0);
    vector<int> remwork(N);                  // remaining processing per job
    for (int j = 0; j < N; j++)
        remwork[j] = accumulate(proc[j].begin(), proc[j].end(), 0);
    Sched S;
    S.seq.assign(M, {});
    int left = N * M;
    while (left > 0) {
        // candidate = each job's next op; earliest start on its machine
        int bestc = INT32_MAX, bm = -1, bj = -1;
        vector<int> es(N, -1), ec(N, -1);
        for (int j = 0; j < N; j++) {
            if (jobop[j] >= M) continue;
            int k = jobop[j], m = mach[j][k];
            es[j] = max(jobfree[j], mfree[m]);
            ec[j] = es[j] + proc[j][k];
            if (ec[j] < bestc) { bestc = ec[j]; bm = m; bj = j; }
        }
        // conflict set: unscheduled next-ops on machine bm with es < bestc.
        // With zero-duration operations o* itself may not satisfy es < ec*,
        // so include it explicitly (positive durations: identical behavior).
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
                bool better = false;
                switch (rule) {
                    case 0: better = proc[j][k] < proc[pick][jobop[pick]]; break;
                    case 1: better = proc[j][k] > proc[pick][jobop[pick]]; break;
                    case 2: better = remwork[j] > remwork[pick]; break;
                    case 3: better = remwork[j] < remwork[pick]; break;
                    case 4: better = (M - jobop[j]) > (M - jobop[pick]); break;
                    case 5: better = (M - jobop[j]) < (M - jobop[pick]); break;
                    default: better = es[j] < es[pick]; break;
                }
                if (better) pick = j;
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

// ---- critical path + N1 local search ----
// Recompute start times, then find one longest path; collect swappable
// adjacent pairs (same machine, both on the critical path). Try all such
// swaps, take the best improving one, repeat until local optimum or the
// per-call iteration cap.
static void local_search(Sched& S, int max_iter) {
    vector<vector<int>> st;
    int cur = evaluate(S, st);
    // machine-predecessor links for critical-path reconstruction
    while (max_iter-- > 0) {
        // rebuild start times and machine position maps
        cur = evaluate(S, st);
        vector<vector<int>> mpos(N, vector<int>(M));
        for (int m = 0; m < M; m++)
            for (int i = 0; i < (int)S.seq[m].size(); i++)
                mpos[S.seq[m][i].first][S.seq[m][i].second] = i;
        // longest path via reverse criticality: crit[j][k] = true if op is on
        // a longest path. Compute "tail" longest distance to sink.
        // Forward pass already gives st. Backward pass on the same graph.
        // Build graph edges lazily: job succ = (j,k+1); machine succ =
        // seq[m][mpos+1].
        vector<vector<int>> tail(N, vector<int>(M, 0));
        // process in reverse topological order: by decreasing st is valid
        // because all edges go from earlier-start to later-start ops.
        vector<tuple<int,int,int>> ops;      // (start, j, k)
        for (int j = 0; j < N; j++)
            for (int k = 0; k < M; k++)
                ops.emplace_back(st[j][k], j, k);
        sort(ops.begin(), ops.end(), greater<>());
        int ms = 0;
        for (auto& [s, j, k] : ops) ms = max(ms, s + proc[j][k]);
        for (auto& [s, j, k] : ops) {
            int m = mach[j][k];
            int t = proc[j][k];         // include self: tail = longest path to sink
            if (k + 1 < M) t = max(t, proc[j][k] + tail[j][k + 1]);
            int pi = mpos[j][k];
            if (pi + 1 < (int)S.seq[m].size()) {
                auto [nj, nk] = S.seq[m][pi + 1];
                t = max(t, proc[j][k] + tail[nj][nk]);
            }
            tail[j][k] = t;
        }
        // critical ops: st + tail == ms
        // collect adjacent machine pairs that are both critical
        vector<pair<int,int>> swaps;         // (machine, position)
        for (int m = 0; m < M; m++) {
            for (int i = 0; i + 1 < (int)S.seq[m].size(); i++) {
                auto [j1, k1] = S.seq[m][i];
                auto [j2, k2] = S.seq[m][i + 1];
                if (j1 == j2) continue;
                bool c1 = (st[j1][k1] + tail[j1][k1] == ms);
                bool c2 = (st[j2][k2] + tail[j2][k2] == ms);
                if (c1 && c2) swaps.emplace_back(m, i);
            }
        }
        int bestms = cur, bm = -1, bi = -1;
        for (auto [m, i] : swaps) {
            swap(S.seq[m][i], S.seq[m][i + 1]);
            vector<vector<int>> tmp;
            int v = evaluate(S, tmp);
            if (v < bestms) { bestms = v; bm = m; bi = i; }
            swap(S.seq[m][i], S.seq[m][i + 1]);
            if (chrono::duration<double>(chrono::steady_clock::now() - T0).count()
                > TIME_LIMIT) break;
        }
        if (bm < 0) break;                   // local optimum
        swap(S.seq[bm][bi], S.seq[bm][bi + 1]);
        cur = bestms;
        if (chrono::duration<double>(chrono::steady_clock::now() - T0).count()
            > TIME_LIMIT) break;
    }
    S.makespan = evaluate(S, st);
}

// ---- output ----
static void write_solution(const Sched& S, const char* out_path) {
    vector<vector<int>> st;
    evaluate(S, st);
    string tmp = string(out_path) + ".tmp";
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
    rename(tmp.c_str(), out_path);
}

int main(int argc, char** argv) {
    if (argc < 4) {
        fprintf(stderr, "usage: %s INSTANCE OUTPUT LIMIT_SECONDS\n", argv[0]);
        return 2;
    }
    T0 = chrono::steady_clock::now();
    TIME_LIMIT = atof(argv[3]);
    double budget = TIME_LIMIT * 0.92;       // keep margin for the final write
    load(argv[1]);

    Sched best;
    int bestms = INT32_MAX;
    auto elapsed = [&]() {
        return chrono::duration<double>(chrono::steady_clock::now() - T0).count();
    };

    // Round 0..5: one deterministic construction per rule, each followed by
    // local search. Then randomized restarts (rule 2 + 20% random tie-break)
    // until the budget is nearly exhausted.
    const int rules[6] = {2, 0, 1, 4, 3, 5};
    int round = 0;
    while (elapsed() < budget) {
        Sched S;
        if (round < 6) S = giffler_thompson(rules[round], 0);
        else S = giffler_thompson(2, 20);
        local_search(S, round < 6 ? 200 : 100);
        if (S.makespan < bestms) {
            bestms = S.makespan;
            best = S;
            write_solution(best, argv[2]);
        }
        round++;
    }
    if (bestms == INT32_MAX) {               // paranoia: always emit something
        best = giffler_thompson(6, 0);
        write_solution(best, argv[2]);
    }
    return 0;
}
