// Baseline solver for the machine reassignment problem (ROADEF/EURO 2012).
//
// What this is: a working but naive starting point. It does a feasibility-
// preserving hill climb with two move types (shift one process, swap two
// processes), exact incremental delta evaluation, and a fixed, deterministic
// work budget (no wall-clock dependence except a safety cap far above the
// time it needs). It makes no attempt to escape local optima, to bias the
// candidate machines it samples, or to use the available time pool well.
// Improving it is the task.
//
// Interface (fixed — the judge relies on it):
//   ./solver MODEL_FILE INITIAL_ASSIGNMENT_FILE OUTPUT_FILE
// with the remaining time pool (seconds) in env MR_TIME_POOL. The solver
// reads the model and the initial assignment, and writes one machine id per
// process (whitespace-separated) to OUTPUT_FILE. The output is scored with
// the official challenge checker: hard constraints must hold, then the
// objective cost is recomputed from scratch (lower is better).
//
// Problem summary (see problem_definition_v1_1.pdf for the full spec):
//   - machines have capacities per resource; processes have requirements;
//     a process initially on machine m that is moved away still occupies its
//     transient resources on m for the CAPACITY check (transient usage);
//     the objective's load/balance terms use current usage only;
//   - hard constraints: capacities (transient-aware), at most one process of
//     a service per machine (conflict), each service spread over at least
//     spreadMin locations, and service dependencies via neighborhoods;
//   - objective (weighted sum): load cost (usage above safety capacity, per
//     resource), balance costs, process move cost, service move cost (max
//     number of moved processes over services), machine move cost.

#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

using std::vector;
using std::string;
using std::unordered_map;

typedef long long int64;

// ---------------------------------------------------------------------------
// Fast whitespace-separated integer reader (model files can be ~50 MB).
// ---------------------------------------------------------------------------
struct FastReader {
    char* buf;
    size_t pos = 0, len = 0;
    explicit FastReader(const char* path) {
        FILE* f = fopen(path, "rb");
        if (!f) { fprintf(stderr, "cannot open %s\n", path); exit(1); }
        fseek(f, 0, SEEK_END);
        len = ftell(f);
        fseek(f, 0, SEEK_SET);
        buf = (char*)malloc(len + 1);
        if (fread(buf, 1, len, f) != len) { fprintf(stderr, "read error\n"); exit(1); }
        fclose(f);
        buf[len] = 0;
    }
    ~FastReader() { free(buf); }
    int64 next() {
        while (pos < len && (buf[pos] < '0' || buf[pos] > '9') && buf[pos] != '-') pos++;
        bool neg = false;
        if (pos < len && buf[pos] == '-') { neg = true; pos++; }
        int64 v = 0;
        while (pos < len && buf[pos] >= '0' && buf[pos] <= '9') v = v * 10 + (buf[pos++] - '0');
        return neg ? -v : v;
    }
};

// Deterministic PRNG (xorshift64*).
struct Rng {
    uint64_t s;
    explicit Rng(uint64_t seed) : s(seed ? seed : 0x9E3779B97F4A7C15ULL) {}
    uint64_t next() {
        s ^= s >> 12; s ^= s << 25; s ^= s >> 27;
        return s * 0x2545F4914F6CDD1DULL;
    }
    int below(int n) { return (int)(next() % (uint64_t)n); }
};

// ---------------------------------------------------------------------------
// Instance data.
// ---------------------------------------------------------------------------
int R, M, S, P, NB;
vector<char> isTransient;      // [R]
vector<int64> loadW;           // [R] load cost weight per resource
vector<int64> cap, safe;       // [M][R] capacity / safety capacity
vector<int> mLoc, mNeigh;      // [M]
vector<int> mmc;               // [M*M] machine move cost matrix (int32 in spec)
vector<int> svcSpreadMin;      // [S]
vector<vector<int>> svcDeps;   // [S] services this service depends on
vector<vector<int>> svcRevDeps;// [S] services depending on this service
vector<int> pSvc;              // [P]
vector<vector<int>> pReq;      // [P][R]
vector<int64> pMoveCost;       // [P]
vector<int> balanceR1, balanceR2, balanceTarget;
vector<int64> balanceW;
int64 wProcMove, wSvcMove, wMachMove;
vector<int> origAssign;        // [P] initial assignment

// ---------------------------------------------------------------------------
// Current solution state.
// ---------------------------------------------------------------------------
vector<int> cur;                       // [P] current machine
vector<vector<int64>> used;            // [M][R] usage by current processes
vector<vector<int64>> ghost;           // [M][R] moved-out usage (transient only)
vector<vector<int>> machProcs;         // [M] current processes
vector<unordered_map<int, int>> svcMachCnt;   // [S] machine -> #processes
vector<unordered_map<int, int>> svcLocCnt;    // [S] location -> #processes
vector<unordered_map<int, int>> svcNeighCnt;  // [S] neighborhood -> #processes
vector<int> svcSpread;                 // [S] current distinct locations
vector<int> svcMoved;                  // [S] #moved processes
unordered_map<int, int> movedFreq;     // moved count -> #services with it
int svcMoveMax = 0;
int64 procMoveSum = 0, machMoveSum = 0;

// Machine-local objective: load cost + balance costs of one machine, given
// its current usage row (length R). NOTE: the official checker computes load
// and balance costs from the CURRENT usage only — the transient "ghost" usage
// of moved-out processes constrains feasibility (capacity check) but does not
// count toward the objective.
int64 machineCost(const vector<int64>& usedRow, int m) {
    int64 c = 0;
    for (int r = 0; r < R; ++r) {
        int64 over = usedRow[r] - safe[m * (int64)R + r];
        if (over > 0) c += loadW[r] * over;
    }
    for (int b = 0; b < NB; ++b) {
        int64 rem1 = cap[m * (int64)R + balanceR1[b]] - usedRow[balanceR1[b]];
        int64 rem2 = cap[m * (int64)R + balanceR2[b]] - usedRow[balanceR2[b]];
        int64 t = (int64)balanceTarget[b] * rem1 - rem2;
        if (t > 0) c += balanceW[b] * t;
    }
    return c;
}

int64 totalCost(const vector<int>& assign) {
    // Full recompute from scratch (used once at start; the checker does the
    // same thing, so this is cross-validated against the official checker).
    vector<vector<int64>> u(M, vector<int64>(R, 0));
    for (int p = 0; p < P; ++p) {
        int m = assign[p];
        for (int r = 0; r < R; ++r) u[m][r] += pReq[p][r];
    }
    int64 c = 0;
    for (int m = 0; m < M; ++m) c += machineCost(u[m], m);
    int64 pm = 0, mm = 0;
    for (int p = 0; p < P; ++p)
        if (assign[p] != origAssign[p]) {
            pm += pMoveCost[p];
            mm += mmc[origAssign[p] * (int64)M + assign[p]];
        } else {
            mm += mmc[origAssign[p] * (int64)M + assign[p]];  // normally 0
        }
    c += wProcMove * pm + wMachMove * mm;
    // service move cost
    vector<int> moved(S, 0);
    for (int p = 0; p < P; ++p)
        if (assign[p] != origAssign[p]) moved[pSvc[p]]++;
    int mx = 0;
    for (int s = 0; s < S; ++s) mx = std::max(mx, moved[s]);
    c += wSvcMove * mx;
    return c;
}

void initState(const vector<int>& assign) {
    cur = assign;
    used.assign(M, vector<int64>(R, 0));
    ghost.assign(M, vector<int64>(R, 0));
    machProcs.assign(M, {});
    svcMachCnt.assign(S, {});
    svcLocCnt.assign(S, {});
    svcNeighCnt.assign(S, {});
    svcSpread.assign(S, 0);
    svcMoved.assign(S, 0);
    movedFreq.clear();
    svcMoveMax = 0;
    procMoveSum = machMoveSum = 0;
    for (int p = 0; p < P; ++p) {
        int m = cur[p], s = pSvc[p];
        machProcs[m].push_back(p);
        for (int r = 0; r < R; ++r) used[m][r] += pReq[p][r];
        svcMachCnt[s][m]++;
        svcLocCnt[s][mLoc[m]]++;
        svcNeighCnt[s][mNeigh[m]]++;
        if (m != origAssign[p]) {
            // ghost usage accrues on the ORIGIN machine (transient resources)
            for (int r = 0; r < R; ++r)
                if (isTransient[r]) ghost[origAssign[p]][r] += pReq[p][r];
            procMoveSum += pMoveCost[p];
            svcMoved[s]++;
        }
        machMoveSum += mmc[origAssign[p] * (int64)M + m];
    }
    for (int s = 0; s < S; ++s) {
        svcSpread[s] = (int)svcLocCnt[s].size();
        movedFreq[svcMoved[s]]++;
        svcMoveMax = std::max(svcMoveMax, svcMoved[s]);
    }
}

// svcMoved[s] += delta, keeping movedFreq and svcMoveMax exact.
void bumpServiceMoved(int s, int delta) {
    if (delta == 0) return;
    int oldCnt = svcMoved[s];
    int newCnt = oldCnt + delta;
    if (--movedFreq[oldCnt] == 0) movedFreq.erase(oldCnt);
    movedFreq[newCnt]++;
    svcMoved[s] = newCnt;
    if (newCnt > svcMoveMax) svcMoveMax = newCnt;
    else if (oldCnt == svcMoveMax && !movedFreq.count(svcMoveMax)) svcMoveMax--;
}

// What svcMoveMax would become if svcMoved[s] changed by delta.
int svcMoveMaxAfter(int s, int delta) {
    int oldCnt = svcMoved[s];
    int newCnt = oldCnt + delta;
    if (newCnt > svcMoveMax) return newCnt;
    if (delta < 0 && oldCnt == svcMoveMax) {
        auto it = movedFreq.find(svcMoveMax);
        if (it != movedFreq.end() && it->second == 1) return svcMoveMax - 1;
    }
    return svcMoveMax;
}

// Move p from u to v, assuming the caller already checked feasibility.
// Returns nothing; updates all incremental state. The caller updates the
// running cost itself via delta computed before the apply.
void applyMove(int p, int u, int v) {
    int s = pSvc[p];
    // capacity / ghost bookkeeping
    for (int r = 0; r < R; ++r) {
        used[u][r] -= pReq[p][r];
        used[v][r] += pReq[p][r];
        if (isTransient[r]) {
            if (origAssign[p] == u) ghost[u][r] += pReq[p][r];   // left home
            if (origAssign[p] == v) ghost[v][r] -= pReq[p][r];   // came home
        }
    }
    // process lists
    auto& lu = machProcs[u];
    for (size_t i = 0; i < lu.size(); ++i)
        if (lu[i] == p) { lu[i] = lu.back(); lu.pop_back(); break; }
    machProcs[v].push_back(p);
    // service maps
    if (--svcMachCnt[s][u] == 0) svcMachCnt[s].erase(u);
    svcMachCnt[s][v]++;
    int lu1 = mLoc[u], lv1 = mLoc[v];
    if (lu1 != lv1) {
        if (--svcLocCnt[s][lu1] == 0) { svcLocCnt[s].erase(lu1); svcSpread[s]--; }
        if (++svcLocCnt[s][lv1] == 1) svcSpread[s]++;
    }
    int nu = mNeigh[u], nv = mNeigh[v];
    if (nu != nv) {
        if (--svcNeighCnt[s][nu] == 0) svcNeighCnt[s].erase(nu);
        svcNeighCnt[s][nv]++;
    }
    // move costs
    bool wasMoved = (u != origAssign[p]);
    bool isMoved = (v != origAssign[p]);
    if (!wasMoved && isMoved) {
        procMoveSum += pMoveCost[p];
        bumpServiceMoved(s, +1);
    } else if (wasMoved && !isMoved) {
        procMoveSum -= pMoveCost[p];
        bumpServiceMoved(s, -1);
    }
    machMoveSum += mmc[origAssign[p] * (int64)M + v] - mmc[origAssign[p] * (int64)M + u];
    cur[p] = v;
}

// Check feasibility of moving p (currently on u) to v. Uses only incremental
// state; does not modify anything.
bool moveFeasible(int p, int u, int v) {
    int s = pSvc[p];
    // capacity on v (transient ghost at v shrinks if p returns home)
    for (int r = 0; r < R; ++r) {
        int64 e = used[v][r] + pReq[p][r];
        if (isTransient[r]) {
            int64 g = ghost[v][r];
            if (origAssign[p] == v) g -= pReq[p][r];
            e += g;
        }
        if (e > cap[v * (int64)R + r]) return false;
    }
    // conflict
    if (svcMachCnt[s].count(v)) return false;
    // spread
    int lu1 = mLoc[u], lv1 = mLoc[v];
    if (lu1 != lv1) {
        int spr = svcSpread[s];
        auto itU = svcLocCnt[s].find(lu1);
        if (itU != svcLocCnt[s].end() && itU->second == 1) spr--;
        if (!svcLocCnt[s].count(lv1)) spr++;
        if (spr < svcSpreadMin[s]) return false;
    }
    // dependencies: p needs every depended service present in v's neighborhood
    int nv = mNeigh[v], nu = mNeigh[u];
    if (nu != nv) {
        for (int t : svcDeps[s]) {
            if (t == s) continue;
            auto it = svcNeighCnt[t].find(nv);
            if (it == svcNeighCnt[t].end() || it->second == 0) return false;
        }
        // reverse deps: if p is the last of s in u's neighborhood, services
        // depending on s that have processes there would be violated
        auto itS = svcNeighCnt[s].find(nu);
        if (itS != svcNeighCnt[s].end() && itS->second == 1) {
            for (int w : svcRevDeps[s]) {
                if (w == s) continue;
                auto it = svcNeighCnt[w].find(nu);
                if (it != svcNeighCnt[w].end() && it->second > 0) return false;
            }
        }
    }
    return true;
}

// Objective delta of moving p from u to v (assumes feasibility checked).
// delta < 0 is an improvement.
int64 moveDelta(int p, int u, int v) {
    int64 before = machineCost(used[u], u) + machineCost(used[v], v);
    // simulate usage effect on u and v only (ghost rows affect feasibility,
    // not the objective)
    vector<int64> uu = used[u], uv = used[v];
    for (int r = 0; r < R; ++r) {
        uu[r] -= pReq[p][r];
        uv[r] += pReq[p][r];
    }
    int64 after = machineCost(uu, u) + machineCost(uv, v);
    int64 d = after - before;
    // process move cost
    bool wasMoved = (u != origAssign[p]);
    bool isMoved = (v != origAssign[p]);
    if (!wasMoved && isMoved) d += wProcMove * pMoveCost[p];
    if (wasMoved && !isMoved) d -= wProcMove * pMoveCost[p];
    // machine move cost
    d += wMachMove * (int64)(mmc[origAssign[p] * (int64)M + v] - mmc[origAssign[p] * (int64)M + u]);
    // service move cost via exact max tracking
    int s = pSvc[p];
    if (wasMoved != isMoved) {
        int mx = svcMoveMaxAfter(s, isMoved ? +1 : -1);
        d += wSvcMove * (mx - svcMoveMax);
    }
    return d;
}

// Swap p (on u) and q (on v), u != v. Feasibility first, then delta.
// Implemented as two shifts with the intermediate state handled exactly.
bool swapFeasibleAndDelta(int p, int q, int64* deltaOut) {
    int u = cur[p], v = cur[q];
    if (u == v) return false;
    // Apply p: u -> v tentatively is not directly possible (q still there and
    // conflict counting). We simulate exactly: remove both, then insert both.
    int sp = pSvc[p], sq = pSvc[q];
    // --- capacity on u and v after both moves ---
    // compute effective usage after removing p from u, q from v, adding p to v, q to u
    static thread_local vector<int64> eu, ev, gu, gv;
    eu = used[u]; ev = used[v]; gu = ghost[u]; gv = ghost[v];
    for (int r = 0; r < R; ++r) {
        eu[r] -= pReq[p][r]; ev[r] += pReq[p][r];
        ev[r] -= pReq[q][r]; eu[r] += pReq[q][r];
        if (isTransient[r]) {
            if (origAssign[p] == u) gu[r] += pReq[p][r];
            if (origAssign[p] == v) gv[r] -= pReq[p][r];
            if (origAssign[q] == v) gv[r] += pReq[q][r];
            if (origAssign[q] == u) gu[r] -= pReq[q][r];
        }
    }
    for (int r = 0; r < R; ++r) {
        if (eu[r] + (isTransient[r] ? gu[r] : 0) > cap[u * (int64)R + r]) return false;
        if (ev[r] + (isTransient[r] ? gv[r] : 0) > cap[v * (int64)R + r]) return false;
    }
    // --- conflict ---
    if (sp == sq) {
        // u and v each keep exactly one process of the service; need no other
        // same-service process on u or v
        if (svcMachCnt[sp].at(u) != 1 || svcMachCnt[sp].at(v) != 1) return false;
    } else {
        int cntPonV = 0;
        auto it = svcMachCnt[sp].find(v);
        if (it != svcMachCnt[sp].end()) cntPonV = it->second;
        if (cntPonV > 0) return false;  // v hosts another process of sp
        int cntQonU = 0;
        auto it2 = svcMachCnt[sq].find(u);
        if (it2 != svcMachCnt[sq].end()) cntQonU = it2->second;
        if (cntQonU > 0) return false;
    }
    // --- spread for sp and sq ---
    // When sp == sq the two moves cancel in every location count, so the
    // spread cannot change; check only the distinct-services case.
    auto spreadOK = [&](int s, int from, int to) {
        int lf = mLoc[from], lt = mLoc[to];
        if (lf == lt) return true;
        int spr = svcSpread[s];
        auto itU = svcLocCnt[s].find(lf);
        if (itU != svcLocCnt[s].end() && itU->second == 1) spr--;
        if (!svcLocCnt[s].count(lt)) spr++;
        return spr >= svcSpreadMin[s];
    };
    if (sp != sq) {
        if (!spreadOK(sp, u, v)) return false;
        if (!spreadOK(sq, v, u)) return false;
    }
    // --- dependencies (both services, both directions) ---
    int nu = mNeigh[u], nv = mNeigh[v];
    if (nu == nv) {
        // neighborhood composition unchanged: no dependency effect
    } else {
        // after the swap, presence counts of sp (and sq) in nu/nv change
        auto presAfter = [&](int s, int nh) {
            int c = 0;
            auto it = svcNeighCnt[s].find(nh);
            if (it != svcNeighCnt[s].end()) c = it->second;
            // p moves u->v, q moves v->u
            if (s == sp) { if (nh == nu) c--; if (nh == nv) c++; }
            if (s == sq) { if (nh == nv) c--; if (nh == nu) c++; }
            return c;
        };
        // p (service sp) lands in nv: needs all deps of sp present in nv
        for (int t : svcDeps[sp]) {
            if (t == sp) continue;
            int c = 0;
            auto it = svcNeighCnt[t].find(nv);
            if (it != svcNeighCnt[t].end()) c = it->second;
            if (t == sq) c--;  // q leaves nv (neighborhood of v)
            if (c <= 0) return false;
        }
        // q (service sq) lands in nu
        for (int t : svcDeps[sq]) {
            if (t == sq) continue;
            int c = 0;
            auto it = svcNeighCnt[t].find(nu);
            if (it != svcNeighCnt[t].end()) c = it->second;
            if (t == sp) c++;  // p arrives in nu
            if (c <= 0) return false;
        }
        // reverse deps of sp: if sp leaves nu empty, dependents of sp in nu break
        if (presAfter(sp, nu) == 0) {
            for (int w : svcRevDeps[sp]) {
                if (w == sp) continue;
                int c = 0;
                auto it = svcNeighCnt[w].find(nu);
                if (it != svcNeighCnt[w].end()) c = it->second;
                if (w == sq) c++;  // q arrives in nu
                if (c > 0) return false;
            }
        }
        // reverse deps of sq in nv
        if (presAfter(sq, nv) == 0) {
            for (int w : svcRevDeps[sq]) {
                if (w == sq || w == sp) continue;
                auto it = svcNeighCnt[w].find(nv);
                if (it != svcNeighCnt[w].end() && it->second > 0) return false;
            }
        }
    }
    // --- delta ---
    int64 before = machineCost(used[u], u) + machineCost(used[v], v);
    int64 after = machineCost(eu, u) + machineCost(ev, v);
    int64 d = after - before;
    // move costs for p and q
    auto moveCostDelta = [&](int x, int from, int to) -> int64 {
        int64 dd = 0;
        bool wasM = (from != origAssign[x]);
        bool isM = (to != origAssign[x]);
        if (!wasM && isM) dd += wProcMove * pMoveCost[x];
        if (wasM && !isM) dd -= wProcMove * pMoveCost[x];
        dd += wMachMove * (int64)(mmc[origAssign[x] * (int64)M + to] - mmc[origAssign[x] * (int64)M + from]);
        return dd;
    };
    d += moveCostDelta(p, u, v) + moveCostDelta(q, v, u);
    // service move max (exact: at most two services change by one each)
    {
        int adjP = 0, adjQ = 0;
        bool pWas = (u != origAssign[p]), pIs = (v != origAssign[p]);
        bool qWas = (v != origAssign[q]), qIs = (u != origAssign[q]);
        if (pWas != pIs) adjP = pIs ? 1 : -1;
        if (qWas != qIs) adjQ = qIs ? 1 : -1;
        if (adjP || adjQ) {
            int mx;
            if (sp == sq) {
                mx = svcMoveMaxAfter(sp, adjP + adjQ);
            } else {
                // exact: the max drops only if every current holder decreases
                int curMax = svcMoveMax;
                int holders = 0;
                auto itf = movedFreq.find(curMax);
                if (itf != movedFreq.end()) holders = itf->second;
                int leavers = ((svcMoved[sp] == curMax && adjP < 0) ? 1 : 0)
                            + ((svcMoved[sq] == curMax && adjQ < 0) ? 1 : 0);
                int base = (holders - leavers >= 1) ? curMax : curMax - 1;
                mx = std::max(base, std::max(svcMoved[sp] + adjP, svcMoved[sq] + adjQ));
            }
            d += wSvcMove * (mx - svcMoveMax);
        }
    }
    *deltaOut = d;
    return true;
}

int main(int argc, char** argv) {
    if (argc != 4) {
        fprintf(stderr, "usage: solver MODEL INITIAL_ASSIGNMENT OUTPUT\n");
        return 1;
    }
    double pool = 300.0;
    if (const char* e = getenv("MR_TIME_POOL")) pool = atof(e);
    auto t0 = std::chrono::steady_clock::now();
    // Safety cap only: the deterministic work below finishes far sooner on
    // any reasonable machine; this just prevents blowing the pool on a
    // pathologically slow one.
    double wallCap = std::min(240.0, pool * 0.9);

    // ---- parse model ----
    {
        FastReader fr(argv[1]);
        R = (int)fr.next();
        isTransient.resize(R); loadW.resize(R);
        for (int r = 0; r < R; ++r) { isTransient[r] = (char)fr.next(); loadW[r] = fr.next(); }
        M = (int)fr.next();
        cap.resize((int64)M * R); safe.resize((int64)M * R);
        mLoc.resize(M); mNeigh.resize(M);
        mmc.resize((int64)M * M);
        for (int m = 0; m < M; ++m) {
            mNeigh[m] = (int)fr.next();
            mLoc[m] = (int)fr.next();
            for (int r = 0; r < R; ++r) cap[m * (int64)R + r] = fr.next();
            for (int r = 0; r < R; ++r) safe[m * (int64)R + r] = fr.next();
            for (int m2 = 0; m2 < M; ++m2) mmc[m * (int64)M + m2] = (int)fr.next();
        }
        S = (int)fr.next();
        svcSpreadMin.resize(S); svcDeps.assign(S, {}); svcRevDeps.assign(S, {});
        for (int s = 0; s < S; ++s) {
            svcSpreadMin[s] = (int)fr.next();
            int nd = (int)fr.next();
            for (int k = 0; k < nd; ++k) svcDeps[s].push_back((int)fr.next());
        }
        for (int s = 0; s < S; ++s)
            for (int t : svcDeps[s]) svcRevDeps[t].push_back(s);
        P = (int)fr.next();
        pSvc.resize(P); pReq.assign(P, vector<int>(R)); pMoveCost.resize(P);
        for (int p = 0; p < P; ++p) {
            pSvc[p] = (int)fr.next();
            for (int r = 0; r < R; ++r) pReq[p][r] = (int)fr.next();
            pMoveCost[p] = fr.next();
        }
        NB = (int)fr.next();
        balanceR1.resize(NB); balanceR2.resize(NB);
        balanceTarget.resize(NB); balanceW.resize(NB);
        for (int b = 0; b < NB; ++b) {
            balanceR1[b] = (int)fr.next(); balanceR2[b] = (int)fr.next();
            balanceTarget[b] = (int)fr.next(); balanceW[b] = fr.next();
        }
        wProcMove = fr.next(); wSvcMove = fr.next(); wMachMove = fr.next();
    }
    // ---- parse initial assignment ----
    {
        FastReader fr(argv[2]);
        origAssign.resize(P);
        for (int p = 0; p < P; ++p) origAssign[p] = (int)fr.next();
    }

    Rng rng(12345);
    initState(origAssign);
    int64 best = totalCost(origAssign);
    int64 running = best;

    // Process visit order: largest total requirement first (big processes are
    // the hardest to place and dominate the load cost).
    vector<int> order(P);
    for (int i = 0; i < P; ++i) order[i] = i;
    {
        vector<int64> sz(P, 0);
        for (int p = 0; p < P; ++p)
            for (int r = 0; r < R; ++r) sz[p] += pReq[p][r] * loadW[r];
        std::sort(order.begin(), order.end(), [&](int a, int b) { return sz[a] > sz[b]; });
    }

    const int CAND = M <= 200 ? M : 100;  // candidate machines sampled per process

    auto timeUp = [&]() {
        double el = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
        return el > wallCap;
    };

    // ---- Phase 1: shift hill climb ----
    auto shiftPass = [&](int maxPasses) {
        for (int pass = 0; pass < maxPasses && !timeUp(); ++pass) {
            bool improved = false;
            for (int oi = 0; oi < P; ++oi) {
                int p = order[oi];
                int u = cur[p];
                int64 bestDelta = 0;
                int bestV = -1;
                for (int c = 0; c < CAND; ++c) {
                    int v = (CAND == M) ? c : rng.below(M);
                    if (v == u) continue;
                    if (!moveFeasible(p, u, v)) continue;
                    int64 d = moveDelta(p, u, v);
                    if (d < bestDelta) { bestDelta = d; bestV = v; }
                }
                if (bestV >= 0) {
                    applyMove(p, u, bestV);
                    running += bestDelta;
                    improved = true;
                }
            }
            if (!improved) break;
        }
    };
    shiftPass(20);

    // ---- Phase 2: big-process reassignment with eviction ----
    // A big process often fits nowhere directly: every candidate machine
    // lacks transient-aware capacity. This move evicts a few small processes
    // from the target machine to make room, then inserts the big one. The
    // whole chain is kept only if the total delta improves; otherwise every
    // eviction is rolled back (applyMove is exactly invertible).
    {
        int attempts = 0;
        const int MAX_ATTEMPTS = 8 * P > 40000 ? 40000 : 8 * P;
        vector<std::pair<int,int>> evMoves;  // (process, machine it came from)
        for (int oi = 0; oi < P && attempts < MAX_ATTEMPTS && !timeUp(); ++oi) {
            int p = order[oi];           // biggest processes first
            int u = cur[p];
            int sp = pSvc[p];
            for (int c = 0; c < 16 && attempts < MAX_ATTEMPTS; ++c) {
                int v = rng.below(M);
                if (v == u) continue;
                if (svcMachCnt[sp].count(v)) continue;  // same-service on v
                ++attempts;
                // deficit on v if p arrives (transient-aware)
                auto deficitLeft = [&]() {
                    for (int r = 0; r < R; ++r) {
                        int64 e = used[v][r] + pReq[p][r];
                        if (isTransient[r]) {
                            int64 g = ghost[v][r];
                            if (origAssign[p] == v) g -= pReq[p][r];
                            e += g;
                        }
                        if (e > cap[v * (int64)R + r]) return true;
                    }
                    return false;
                };
                if (!deficitLeft()) continue;  // plain shifts already handle it
                // evict smallest processes from v until p fits (at most 8)
                evMoves.clear();
                int64 evDelta = 0;
                bool ok = false;
                while (deficitLeft()) {
                    if ((int)evMoves.size() >= 8) break;
                    // smallest process still on v (any service)
                    int bestQ = -1;
                    int64 bestSz = 0;
                    for (int q : machProcs[v]) {
                        int64 szz = 0;
                        for (int r = 0; r < R; ++r) szz += pReq[q][r];
                        if (bestQ < 0 || szz < bestSz) { bestQ = q; bestSz = szz; }
                    }
                    if (bestQ < 0) break;
                    int q = bestQ;
                    // find a target machine for q
                    int64 bestD = 0;
                    int bestW = -1;
                    for (int c2 = 0; c2 < 16; ++c2) {
                        int w = rng.below(M);
                        if (w == v) continue;
                        if (!moveFeasible(q, v, w)) continue;
                        int64 d = moveDelta(q, v, w);
                        if (d < bestD) { bestD = d; bestW = w; }
                    }
                    if (bestW < 0) break;  // nowhere to put q
                    applyMove(q, v, bestW);
                    evMoves.push_back({q, bestW});
                    evDelta += bestD;
                }
                if (!deficitLeft() && moveFeasible(p, u, v)) {
                    int64 dP = moveDelta(p, u, v);
                    if (evDelta + dP < 0) {
                        applyMove(p, u, v);
                        running += evDelta + dP;
                        ok = true;
                    }
                }
                if (!ok) {
                    // roll back every eviction in reverse order
                    for (auto it = evMoves.rbegin(); it != evMoves.rend(); ++it)
                        applyMove(it->first, it->second, v);
                }
            }
        }
    }

    // ---- Phase 3: shifts again (the evictions unlocked new moves) ----
    shiftPass(20);

    // ---- Phase 4: random swap hill climb (fixed number of samples) ----
    {
        int64 samples = (int64)std::min(P, 20000) * 50;
        for (int64 it = 0; it < samples; ++it) {
            if ((it & 4095) == 0 && timeUp()) break;
            int p = rng.below(P), q = rng.below(P);
            if (p == q || cur[p] == cur[q]) continue;
            int64 d;
            if (!swapFeasibleAndDelta(p, q, &d)) continue;
            if (d >= 0) continue;
            int u = cur[p], v = cur[q];
            applyMove(p, u, v);   // p: u -> v (q still there; maps allow it)
            applyMove(q, v, u);
            running += d;
        }
    }

    // ---- write result ----
    FILE* f = fopen(argv[3], "w");
    if (!f) return 1;
    for (int p = 0; p < P; ++p) fprintf(f, "%d ", cur[p]);
    fprintf(f, "\n");
    fclose(f);
    fprintf(stderr, "cost %lld -> %lld\n", (long long)best, (long long)running);
    return 0;
}
