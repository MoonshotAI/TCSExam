// Baseline solver for ITC2021 sports timetabling (RobinX XML format).
//
// Reads an ITC2021 instance (<Instance> document) on stdin and writes a
// schedule (<Solution> document) on stdout.
//
// Method: circle-method construction of a mirrored compact double round
// robin, then simulated annealing over two feasibility-preserving moves
// (swap slots of two games between four distinct teams; swap the slots of
// the two mirrored games of a team pair = home/away flip). The internal
// objective is an exact port of the RobinX Validator 2.0 constraint
// semantics for the nine constraint classes used by ITC2021 (CA1, CA2,
// CA3, CA4, GA1, BR1, BR2, FA2, SE1), summed as hard * BIG + soft.
//
// Deterministic configuration: fixed seed + fixed iteration budget (env
// ITC_ITERS, looked up per instance by the build.sh wrapper in budgets.tsv).
// All transcendental math in the search path goes through det_exp/det_log
// below — fixed-evaluation-path polynomial approximations in plain IEEE
// doubles — so the trajectory is bit-identical across CPUs, compilers and
// libm variants. Wall clock appears only in safety backstops: if one ever
// fires, the run ends at a prefix of the one deterministic trajectory.

#include <bits/stdc++.h>
using namespace std;

// deterministic exp(): range reduction to [-ln2/2, ln2/2] + fixed 12-term
// Taylor; every operation is an exactly-rounded IEEE double op, so the
// result is the same on every machine (libm exp/pow are NOT guaranteed
// bit-identical across CPU-dispatched implementations).
static double det_exp(double x) {
    if (x <= -700.0) return 0.0;
    if (x >= 700.0) return 1e308;
    const double LN2 = 0.69314718055994531;
    const double INV_LN2 = 1.4426950408889634;
    double kd = x * INV_LN2;
    long long k = (long long)(kd >= 0.0 ? kd + 0.5 : kd - 0.5);
    double r = x - (double)k * LN2;
    // fixed 12-term Horner for e^r on |r| <= ln2/2: the dependence chain
    // cannot be reassociated (no fast-math, -ffp-contract=off), so every
    // machine evaluates the identical sequence of IEEE ops.
    static const double C[12] = {
        1.0, 1.0 / 2, 1.0 / 6, 1.0 / 24, 1.0 / 120, 1.0 / 720,
        1.0 / 5040, 1.0 / 40320, 1.0 / 362880, 1.0 / 3628800,
        1.0 / 39916800.0, 1.0 / 479001600.0
    };
    double p = C[11];
    for (int i = 10; i >= 0; i--) p = C[i] + r * p;
    return ldexp(p, (int)k);   // ldexp is exact scaling by a power of two
}

// deterministic log() for x > 0: frexp reduction + fixed atanh series.
static double det_log(double x) {
    const double LN2 = 0.69314718055994531;
    int e = 0;
    double m = frexp(x, &e);          // x = m * 2^e, m in [0.5, 1)
    if (m < 0.70710678118654752) { m *= 2.0; e -= 1; }
    double y = (m - 1.0) / (m + 1.0); // |y| <= 0.1716
    double y2 = y * y;
    static const double C[10] = {
        1.0, 1.0 / 3, 1.0 / 5, 1.0 / 7, 1.0 / 9,
        1.0 / 11, 1.0 / 13, 1.0 / 15, 1.0 / 17, 1.0 / 19
    };
    double s = C[9];
    for (int i = 8; i >= 0; i--) s = C[i] + y2 * s;
    return 2.0 * y * s + (double)e * LN2;
}

// ---------------------------------------------------------------------------
// Instance data
// ---------------------------------------------------------------------------

struct Constraint {
    string type;               // CA1 CA2 CA3 CA4 GA1 BR1 BR2 FA2 SE1
    bool hard = false;
    long long penalty = 0;
    // team masks (n <= 20 in ITC2021, fits in 32 bits)
    uint32_t t1 = 0, t2 = 0;
    // slots
    vector<int> slots;
    int mn = 0, mx = 0;
    int intp = 0;
    char mode = 0;             // CA1: H/A/HA ; CA2/CA3/CA4 mode1 ; FA2: H
    char mode2 = 0;            // CA4: GLOBAL/EVERY ; BR1/BR2: LEQ
    vector<pair<int,int>> games; // GA1
};

int nTeams = 0, nSlots = 0;
string instanceName;
bool phasedMode = false;   // gameMode P: each half must be a full round robin
vector<Constraint> cons;

// meetings: for pair (i,j), i<j: two meetings (i home) and (j home)
int nMeet = 0;
vector<int> mHome, mAway;      // size nMeet
map<pair<int,int>, int> meetIdx; // (home,away) -> index

static vector<string> splitSemi(const string& s) {
    vector<string> out; string cur;
    for (char c : s) { if (c == ';') { out.push_back(cur); cur.clear(); } else cur += c; }
    if (!cur.empty()) out.push_back(cur);
    return out;
}

static void parseAttrs(const string& tag, const string& body) {
    map<string,string> a;
    size_t p = 0;
    while (p < body.size()) {
        while (p < body.size() && (isspace((unsigned char)body[p]) || body[p] == '/')) p++;
        size_t q = body.find('=', p);
        if (q == string::npos || q >= body.size()) break;
        string key = body.substr(p, q - p);
        size_t r = body.find('"', q);
        if (r == string::npos) break;
        size_t s2 = body.find('"', r + 1);
        if (s2 == string::npos) break;
        a[key] = body.substr(r + 1, s2 - r - 1);
        p = s2 + 1;
    }
    auto ids = [&](const string& key) -> uint32_t {
        uint32_t mask = 0;
        auto it = a.find(key);
        if (it == a.end()) return 0;
        for (auto& tok : splitSemi(it->second)) {
            if (tok.empty()) continue;
            mask |= 1u << stoi(tok);
        }
        return mask;
    };
    auto idvec = [&](const string& key) -> vector<int> {
        vector<int> v;
        auto it = a.find(key);
        if (it == a.end()) return v;
        for (auto& tok : splitSemi(it->second)) {
            if (tok.empty()) continue;
            v.push_back(stoi(tok));
        }
        return v;
    };
    Constraint c;
    c.type = tag;
    c.hard = (a["type"] == "HARD");
    c.penalty = stoll(a["penalty"]);
    c.t1 = ids("teams"); c.t2 = ids("teams2");
    if (tag == "CA2" || tag == "CA3" || tag == "CA4") c.t1 = ids("teams1");
    if (tag == "CA1" || tag == "CA2" || tag == "CA4" || tag == "BR1" || tag == "BR2" || tag == "FA2")
        c.slots = idvec("slots");
    auto modeChar = [](const string& m) { return m == "A" ? 'A' : (m == "HA" ? 'M' : 'H'); };
    if (tag == "CA1") c.mode = modeChar(a["mode"]);
    if (tag == "CA2" || tag == "CA3" || tag == "CA4") c.mode = modeChar(a["mode1"]);
    if (tag == "CA4") c.mode2 = a["mode2"] == "EVERY" ? 'E' : 'G';
    if (tag == "FA2") c.mode = modeChar(a["mode"]);
    c.mn = a.count("min") ? stoi(a["min"]) : 0;
    c.mx = a.count("max") ? stoi(a["max"]) : 0;
    if (tag == "CA3" || tag == "BR1" || tag == "BR2" || tag == "FA2") c.intp = stoi(a["intp"]);
    if (tag == "GA1") {
        for (auto& tok : splitSemi(a["meetings"])) {
            if (tok.empty()) continue;
            size_t cpos = tok.find(',');
            c.games.push_back({stoi(tok.substr(0, cpos)), stoi(tok.substr(cpos + 1))});
        }
        c.slots = idvec("slots");
    }
    if (tag == "SE1") { c.mn = stoi(a["min"]); }
    cons.push_back(c);
}

static void parseInstance(const string& txt) {
    cons.clear(); mHome.clear(); mAway.clear(); meetIdx.clear();
    // instance name
    {
        size_t p = txt.find("<InstanceName>");
        if (p != string::npos) {
            size_t q = txt.find("</InstanceName>", p);
            instanceName = txt.substr(p + 14, q - p - 14);
        }
    }
    {
        size_t p = txt.find("<gameMode>");
        if (p != string::npos) phasedMode = txt.compare(p + 10, 1, "P") == 0;
    }
    // teams / slots: ids are 0..n-1 in ITC2021; take max id + 1
    {
        size_t p = 0;
        int mx = -1;
        while ((p = txt.find("<team id=", p)) != string::npos) {
            size_t q = txt.find('"', p + 9);
            mx = max(mx, stoi(txt.substr(q + 1)));
            p = q;
        }
        nTeams = mx + 1;
        p = 0; mx = -1;
        while ((p = txt.find("<slot id=", p)) != string::npos) {
            size_t q = txt.find('"', p + 9);
            mx = max(mx, stoi(txt.substr(q + 1)));
            p = q;
        }
        nSlots = mx + 1;
    }
    // constraints
    for (string tag : {"CA1","CA2","CA3","CA4","GA1","BR1","BR2","FA2","SE1"}) {
        string needle = "<" + tag;
        size_t p = 0;
        while ((p = txt.find(needle, p)) != string::npos) {
            char next = txt[p + needle.size()];
            if (next != ' ' && next != '\t' && next != '/' && next != '>') { p += needle.size(); continue; }
            size_t q = txt.find('>', p);
            parseAttrs(tag, txt.substr(p + needle.size(), q - p - needle.size()));
            p = q;
        }
    }
    // meetings: every ordered pair once
    for (int i = 0; i < nTeams; i++)
        for (int j = i + 1; j < nTeams; j++) {
            meetIdx[{i, j}] = mHome.size();
            mHome.push_back(i); mAway.push_back(j);
            meetIdx[{j, i}] = mHome.size();
            mHome.push_back(j); mAway.push_back(i);
        }
    nMeet = mHome.size();
}

// ---------------------------------------------------------------------------
// Evaluation (exact port of RobinX Validator 2.0 semantics)
// ---------------------------------------------------------------------------

// state: slot per meeting; opp[t][s] = opponent, homeT[t][s] = t is home
vector<int> slotOf;
vector<vector<int>> opp;      // [nTeams][nSlots]
vector<vector<char>> homeT;   // [nTeams][nSlots]

static void buildSchedule() {
    opp.assign(nTeams, vector<int>(nSlots, -1));
    homeT.assign(nTeams, vector<char>(nSlots, 0));
    for (int g = 0; g < nMeet; g++) {
        int s = slotOf[g], h = mHome[g], a = mAway[g];
        opp[h][s] = a; homeT[h][s] = 1;
        opp[a][s] = h; homeT[a][s] = 0;
    }
}

// returns {hard, soft}
static vector<pair<string,long long>> g_classCost;
static vector<int> g_slotConf;   // per-slot hard deviation weight (repair focus)
static pair<long long, long long> evaluate() {
    buildSchedule();
    long long hard = 0, soft = 0;
    g_classCost.clear();
    if (!g_slotConf.empty()) fill(g_slotConf.begin(), g_slotConf.end(), 0);
    for (auto& c : cons) {
        long long cost = 0;
        if (c.type == "CA1") {
            for (int t = 0; t < nTeams; t++) {
                if (!(c.t1 >> t & 1)) continue;
                int cnt = 0;
                for (int s : c.slots) {
                    if (opp[t][s] < 0) continue;
                    bool h = homeT[t][s];
                    if (c.mode == 'H' && h) cnt++;
                    else if (c.mode == 'A' && !h) cnt++;
                    else if (c.mode == 'M') cnt++; // HA
                }
                cost += max(0, cnt - c.mx) + max(0, c.mn - cnt);
            }
        } else if (c.type == "CA2") { // mode2 always GLOBAL in ITC2021
            for (int t = 0; t < nTeams; t++) {
                if (!(c.t1 >> t & 1)) continue;
                int cnt = 0;
                for (int s : c.slots) {
                    int o = opp[t][s];
                    if (o < 0 || !(c.t2 >> o & 1)) continue;
                    bool h = homeT[t][s];
                    if (c.mode == 'H' && !h) continue;
                    if (c.mode == 'A' && h) continue;
                    cnt++;
                }
                cost += max(0, cnt - c.mx) + max(0, c.mn - cnt);
            }
        } else if (c.type == "CA3") { // windows of intp consecutive slots
            for (int t = 0; t < nTeams; t++) {
                if (!(c.t1 >> t & 1)) continue;
                for (int w = 0; w + c.intp <= nSlots; w++) {
                    int cnt = 0;
                    for (int s = w; s < w + c.intp; s++) {
                        int o = opp[t][s];
                        if (o < 0 || !(c.t2 >> o & 1)) continue;
                        bool h = homeT[t][s];
                        if (c.mode == 'H' && !h) continue;
                        if (c.mode == 'A' && h) continue;
                        cnt++;
                    }
                    cost += max(0, cnt - c.mx) + max(0, c.mn - cnt);
                }
            }
        } else if (c.type == "CA4") {
            if (c.mode2 == 'G') {
                int cnt = 0;
                for (int s : c.slots)
                    for (int t = 0; t < nTeams; t++) {
                        if (!(c.t1 >> t & 1)) continue;
                        int o = opp[t][s];
                        if (o < 0 || !(c.t2 >> o & 1)) continue;
                        bool h = homeT[t][s];
                        if (c.mode == 'H' && !h) continue;
                        if (c.mode == 'A' && h) continue;
                        cnt++;
                    }
                cost += max(0LL, max((long long)cnt - c.mx, (long long)c.mn - cnt));
            } else { // EVERY: deviation per slot
                for (int s : c.slots) {
                    int cnt = 0;
                    for (int t = 0; t < nTeams; t++) {
                        if (!(c.t1 >> t & 1)) continue;
                        int o = opp[t][s];
                        if (o < 0 || !(c.t2 >> o & 1)) continue;
                        bool h = homeT[t][s];
                        if (c.mode == 'H' && !h) continue;
                        if (c.mode == 'A' && h) continue;
                        cnt++;
                    }
                    cost += max(0LL, max((long long)cnt - c.mx, (long long)c.mn - cnt));
                }
            }
        } else if (c.type == "GA1") {
            // slots of this constraint as boolean list
            static thread_local vector<char> inS;
            inS.assign(nSlots, 0);
            for (int s : c.slots) inS[s] = 1;
            int cnt = 0;
            for (auto& g : c.games) {
                auto it = meetIdx.find(g);
                if (it != meetIdx.end() && inS[slotOf[it->second]]) cnt++;
            }
            cost += max(0LL, max((long long)cnt - c.mx, (long long)c.mn - cnt));
        } else if (c.type == "BR1") { // LEQ, HA
            for (int t = 0; t < nTeams; t++) {
                if (!(c.t1 >> t & 1)) continue;
                static thread_local vector<char> inS;
                inS.assign(nSlots, 0);
                for (int s : c.slots) inS[s] = 1;
                int br = 0, prev = -1;
                for (int s = 0; s < nSlots; s++) {
                    if (opp[t][s] < 0) continue;
                    int v = homeT[t][s] ? 1 : 0;
                    if (prev >= 0 && v == prev && inS[s]) br++;
                    prev = v;
                }
                cost += max(0, br - c.intp);
            }
        } else if (c.type == "BR2") { // LEQ, HA, total over teams
            static thread_local vector<char> inS;
            inS.assign(nSlots, 0);
            for (int s : c.slots) inS[s] = 1;
            int total = 0;
            for (int t = 0; t < nTeams; t++) {
                if (!(c.t1 >> t & 1)) continue;
                int prev = -1;
                for (int s = 0; s < nSlots; s++) {
                    if (opp[t][s] < 0) continue;
                    int v = homeT[t][s] ? 1 : 0;
                    if (prev >= 0 && v == prev && inS[s]) total++;
                    prev = v;
                }
            }
            cost += max(0, total - c.intp);
        } else if (c.type == "FA2") { // cumulative games played (mode H: home games)
            // cumulative per team over ALL slots (validator fills every slot)
            static thread_local vector<array<int, 40>> cum;
            cum.assign(nTeams, {});
            for (int t = 0; t < nTeams; t++) {
                int csum = 0;
                for (int s = 0; s < nSlots; s++) {
                    if (opp[t][s] >= 0 && (c.mode != 'H' || homeT[t][s])) csum++;
                    cum[t][s] = csum;
                }
            }
            vector<int> ts;
            for (int t = 0; t < nTeams; t++) if (c.t1 >> t & 1) ts.push_back(t);
            for (size_t i = 0; i < ts.size(); i++)
                for (size_t j = i + 1; j < ts.size(); j++) {
                    int maxDiff = 0;
                    for (int s : c.slots)
                        maxDiff = max(maxDiff, abs(cum[ts[i]][s] - cum[ts[j]][s]));
                    cost += max(0, maxDiff - c.intp);
                }
        } else if (c.type == "SE1") {
            vector<int> ts;
            for (int t = 0; t < nTeams; t++) if (c.t1 >> t & 1) ts.push_back(t);
            for (size_t i = 0; i < ts.size(); i++)
                for (size_t j = i + 1; j < ts.size(); j++) {
                    int g1 = meetIdx[{ts[i], ts[j]}];
                    int g2 = meetIdx[{ts[j], ts[i]}];
                    int s1 = min(slotOf[g1], slotOf[g2]);
                    int s2 = max(slotOf[g1], slotOf[g2]);
                    cost += max(0, c.mn - (s2 - s1 - 1));
                }
        }
        g_classCost.push_back({c.type + (c.hard ? ":H" : ":S"), c.penalty * cost});
        if (c.hard) {
            hard += c.penalty * cost;
            if (cost > 0 && !g_slotConf.empty()) {
                int w = (int)min<long long>(cost, 1000);
                if (!c.slots.empty()) {
                    for (int s : c.slots) g_slotConf[s] += w;
                } else if (c.type == "CA3") {
                    for (int s = 0; s + c.intp <= nSlots; s++)
                        for (int k = s; k < s + c.intp; k++) g_slotConf[k] += w;
                } else if (c.type == "SE1") {
                    // slots of the offending pair meetings handled cheaply: skip
                }
            }
        }
        else soft += c.penalty * cost;
    }
    // built-in phased check (gameMode P, hard, penalty 1 per ordered pair):
    // each pair must meet exactly once in each phase (slots [0, halfP))
    if (phasedMode) {
        int halfP = nSlots / 2;
        for (int t1 = 0; t1 < nTeams; t1++)
            for (int t2 = t1 + 1; t2 < nTeams; t2++) {
                int cnt = 0;
                int ga = meetIdx[{t1, t2}], gb = meetIdx[{t2, t1}];
                if (slotOf[ga] < halfP) cnt++;
                if (slotOf[gb] < halfP) cnt++;
                if (cnt != 1) hard += 2; // validator counts both orders
            }
    }
    return {hard, soft};
}

// ---------------------------------------------------------------------------
// Construction + simulated annealing
// ---------------------------------------------------------------------------

static mt19937 rng(12345);

// circle method: round r pairings over teams; mirrored second half
static void construct() {
    slotOf.assign(nMeet, -1);
    int half = nSlots / 2;
    vector<int> pos(nTeams - 1);
    iota(pos.begin(), pos.end(), 0);
    for (int r = 0; r < half; r++) {
        // pair fixed team n-1 with pos[r]
        int a = nTeams - 1, b = pos[r];
        if (rng() & 1) swap(a, b);
        slotOf[meetIdx[{a, b}]] = r;
        slotOf[meetIdx[{b, a}]] = r + half;
        for (int i = 1; i <= (nTeams - 2) / 2; i++) {
            int t1 = pos[(r + i) % (nTeams - 1)];
            int t2 = pos[(r + nTeams - 1 - i) % (nTeams - 1)];
            a = t1; b = t2;
            if (rng() & 1) swap(a, b);
            slotOf[meetIdx[{a, b}]] = r;
            slotOf[meetIdx[{b, a}]] = r + half;
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    stringstream ss;
    ss << cin.rdbuf();
    string txt = ss.str();
    parseInstance(txt);

    double pool = 1e9;
    if (const char* e = getenv("ITC2021_TIME_POOL")) pool = atof(e);

    if (const char* ef = getenv("ITC_EVAL_ONLY")) {
        stringstream ss2;
        { ifstream f(ef); ss2 << f.rdbuf(); }
        string soltxt = ss2.str();
        // instance was already parsed from stdin above
        slotOf.assign(nMeet, -1);
        size_t p = 0;
        while ((p = soltxt.find("<ScheduledMatch", p)) != string::npos) {
            size_t q = soltxt.find('>', p);
            string body = soltxt.substr(p + 15, q - p - 15);
            map<string,int> at;
            size_t r = 0;
            while ((r = body.find('=', r)) != string::npos) {
                string key = body.substr(body.rfind(' ', r) + 1, r - body.rfind(' ', r) - 1);
                size_t q1 = body.find('"', r), q2 = body.find('"', q1 + 1);
                at[key] = stoi(body.substr(q1 + 1, q2 - q1 - 1));
                r = q2 + 1;
            }
            slotOf[meetIdx[{at["home"], at["away"]}]] = at["slot"];
            p = q;
        }
        auto res = evaluate();
        map<string,long long> agg;
        for (auto& kv : g_classCost) agg[kv.first] += kv.second;
        for (auto& kv : agg) fprintf(stderr, "MYCLASS %s %lld\n", kv.first.c_str(), kv.second);
        fprintf(stderr, "MYTOTAL hard=%lld soft=%lld\n", res.first, res.second);
        return 0;
    }

    construct();
    auto objOf = [](pair<long long, long long> hs) {
        return hs.first * 100000000LL + hs.second;
    };

    g_slotConf.assign(nSlots, 0);
    // Fixed iteration budget (deterministic anchor): from env ITC_ITERS,
    // which the build.sh wrapper pins per instance via budgets.tsv. The
    // default below only covers instances without a pinned budget (e.g. the
    // user's own test files).
    construct();
    auto cur = evaluate();
    long long curObj = objOf(cur);
    long long curHard = cur.first;
    vector<int> bestSlot = slotOf;
    pair<long long, long long> best = cur;
    long long iters = 4000000;
    if (const char* e = getenv("ITC_ITERS")) iters = atoll(e);
    iters = max(200000LL, iters);
    auto t0 = chrono::steady_clock::now();

    // simple LCG for speed in the hot loop
    uint64_t st = 88172645463325252ULL;
    auto nextr = [&]() { st ^= st << 13; st ^= st >> 7; st ^= st << 17; return st; };
    int restarts = 1;
    if (const char* e = getenv("ITC_RESTARTS")) restarts = max(1, atoi(e));
    int SIDeways = 10;
    if (const char* e = getenv("ITC_SIDEWAYS")) SIDeways = atoi(e);
    long long kickThresh = 100000;
    if (const char* e = getenv("ITC_KICK")) kickThresh = atoll(e);

    double T0 = 30.0, T1 = 0.3;
    const double logT1T0 = det_log(T1 / T0);   // hoisted; per-iteration
    // T = T0 * det_exp(frac * logT1T0) reproduces pow(T1/T0, frac) exactly
    // enough for the schedule while staying bit-identical across machines.
    long long report = 0;
    long long sinceImp = 0;
    bool g_confReady = false;
    if (getenv("ITC_NO_SA")) iters = 0;
    long long perRestart = iters / restarts;
    long long mainItersDone = 0;
    for (long long it = 0; it < iters; it++) {
        mainItersDone = it + 1;
        if (restarts > 1 && it > 0 && it % perRestart == 0) {
            construct();
            cur = evaluate();
            curHard = cur.first;
            curObj = objOf(cur);
            if (cur.first < best.first ||
                (cur.first == best.first && cur.second < best.second)) {
                best = cur; bestSlot = slotOf;
            }
        }
        double frac = (double)it / iters;
        double T = T0 * det_exp(frac * logT1T0);
        // two-phase search: first minimize hard violations, then anneal
        // the full lexicographic objective
        bool repairPhase = ((double)it / iters < 0.45 || getenv("ITC_REPAIR_UNTIL_FEAS")) && best.first > 0;
        // pick move; both move types preserve compactness (one game per
        // team per slot) by construction
        long long newObj;
        static thread_local vector<pair<int,int>> undo; // (meeting, old slot)
        undo.clear();
        // move type: 40% mirrored-pair swap; during repair, also a
        // conflict-guided variant that flips the venue of a random team
        // playing in a violating slot
        int moveKind = nextr() % 5;
        bool flip = moveKind < 2;
        if (repairPhase && g_confReady && moveKind == 4) {
            long long tot = 0; for (int v : g_slotConf) tot += v;
            if (tot > 0) {
                buildSchedule();
                long long r = nextr() % tot;
                int s = 0; while ((r -= g_slotConf[s]) >= 0) s++;
                // pick a random team playing in s, flip its venue there via
                // a mirrored-pair swap of its pair in s
                int a = nextr() % nTeams;
                if (opp[a][s] >= 0) {
                    int o = opp[a][s];
                    int g1 = meetIdx[{a, o}], g2 = meetIdx[{o, a}];
                    if (slotOf[g1] != slotOf[g2]) {
                        undo.push_back({g1, slotOf[g1]});
                        undo.push_back({g2, slotOf[g2]});
                        swap(slotOf[g1], slotOf[g2]);
                    }
                }
            }
        } else if (flip) {
            int g1 = nextr() % nMeet;
            int h = mHome[g1], a = mAway[g1];
            int g2 = meetIdx[{a, h}];
            if (slotOf[g1] == slotOf[g2]) continue;
            undo.push_back({g1, slotOf[g1]});
            undo.push_back({g2, slotOf[g2]});
            swap(slotOf[g1], slotOf[g2]);
        } else {
            // cycle flip: the games of two slots form even cycles over the
            // teams (each team has one game in each slot); flipping the slot
            // of every game on one cycle yields another compact schedule
            int halfP = nSlots / 2;
            int s1;
            if (repairPhase && g_confReady) {
                // focus on slots that participate in hard violations
                long long tot = 0; for (int v : g_slotConf) tot += v;
                if (tot > 0) {
                    long long r = nextr() % tot;
                    s1 = 0; while ((r -= g_slotConf[s1]) >= 0) s1++;
                } else s1 = nextr() % nSlots;
            } else s1 = nextr() % nSlots;
            int s2 = nextr() % nSlots;
            if (phasedMode) {
                // keep both slots inside the same phase: phased (gameMode P)
                // is then preserved by construction
                int lo = (s1 < halfP) ? 0 : halfP;
                s2 = lo + nextr() % halfP;
            }
            if (s1 == s2) continue;
            buildSchedule();
            int t0 = nextr() % nTeams;
            int cur = t0, curSlot = s1;
            static thread_local vector<int> glist;
            glist.clear();
            do {
                int o = opp[cur][curSlot];
                if (o < 0) break; // not compact (should not happen)
                int h = cur, a = o;
                if (homeT[cur][curSlot] == 0) { h = o; a = cur; }
                glist.push_back(meetIdx[{h, a}]);
                cur = o;
                curSlot = (curSlot == s1) ? s2 : s1;
            } while (cur != t0);
            if (cur != t0) continue; // safety
            for (int g : glist) {
                undo.push_back({g, slotOf[g]});
                slotOf[g] = (slotOf[g] == s1) ? s2 : s1;
            }
        }
        bool accept;
        auto nv = evaluate();
        if (repairPhase) {
            if (nv.first < curHard) { accept = true; sinceImp = 0; }
            else if (nv.first == curHard) { accept = (nextr() % 100) < SIDeways; sinceImp++; }
            else { accept = (nextr() % 10000) < 5; sinceImp++; }
        } else {
            curObj = objOf(cur);
            newObj = objOf(nv);
            accept = newObj <= curObj;
            if (!accept) {
                double d = (double)(newObj - curObj);
                double Teff = curHard > 0 ? T * 1.0e7 : T;
                double p = det_exp(-d / Teff);
                accept = (nextr() % 1000000) < p * 1000000;
            }
        }
        if (accept) {
            curHard = nv.first;
            cur = nv;
            if (cur.first < best.first ||
                (cur.first == best.first && cur.second < best.second)) {
                best = cur;
                bestSlot = slotOf;
            }
        } else {
            for (auto it2 = undo.rbegin(); it2 != undo.rend(); ++it2)
                slotOf[it2->first] = it2->second;
        }
        if (repairPhase) g_confReady = true;
        if (repairPhase && sinceImp > kickThresh) {
            // kick: apply a batch of random moves regardless of cost
            sinceImp = 0;
            for (int k = 0; k < 12; k++) {
                if ((nextr() & 1) && !phasedMode) {
                    int g1 = nextr() % nMeet;
                    int h = mHome[g1], a = mAway[g1];
                    int g2 = meetIdx[{a, h}];
                    if (slotOf[g1] != slotOf[g2]) swap(slotOf[g1], slotOf[g2]);
                } else {
                    int s1 = nextr() % nSlots, s2 = nextr() % nSlots;
                    if (phasedMode) { int lo = (s1 < nSlots/2) ? 0 : nSlots/2; s2 = lo + nextr() % (nSlots/2); }
                    if (s1 == s2) continue;
                    buildSchedule();
                    int t0 = nextr() % nTeams, cur2 = t0, curSlot = s1;
                    static thread_local vector<int> g2list;
                    g2list.clear();
                    bool ok = true;
                    do {
                        int o = opp[cur2][curSlot];
                        if (o < 0) { ok = false; break; }
                        int h = cur2, a = o;
                        if (homeT[cur2][curSlot] == 0) { h = o; a = cur2; }
                        g2list.push_back(meetIdx[{h, a}]);
                        cur2 = o;
                        curSlot = (curSlot == s1) ? s2 : s1;
                    } while (cur2 != t0);
                    if (!ok) continue;
                    for (int g : g2list) slotOf[g] = (slotOf[g] == s1) ? s2 : s1;
                }
            }
            cur = evaluate();
            curHard = cur.first;
        }
        if ((++report & 0x1FFFF) == 0) {
            double el = chrono::duration<double>(chrono::steady_clock::now() - t0).count();
            if (el > pool - 3.0) break;   // wall-clock backstop only
            if (best.first == 0 && best.second == 0) break;
            if (getenv("ITC_DEBUG")) {
                vector<int> cnt(nTeams * nSlots, 0);
                for (int g = 0; g < nMeet; g++) {
                    cnt[mHome[g] * nSlots + slotOf[g]]++;
                    cnt[mAway[g] * nSlots + slotOf[g]]++;
                }
                int ov = 0; for (int v : cnt) ov += max(0, v - 1);
                fprintf(stderr, "it=%lld overlap=%d cur=(%lld,%lld) best=(%lld,%lld)\n",
                        it, ov, cur.first, cur.second, best.first, best.second);
            }
        }
    }

    // calibration aid: main-loop wall time, captured before endgame/polish
    const double mainSaSeconds =
        chrono::duration<double>(chrono::steady_clock::now() - t0).count();

    // focused endgame: if only a few hard violations remain, run a short
    // anneal that accepts sideways soft moves (the main SA freezes near the
    // end and cannot escape the last few coordinated violations)
    if (best.first > 0 && best.first <= 12) {
        slotOf = bestSlot;
        cur = evaluate();
        curHard = cur.first;
        curObj = objOf(cur);
        const long long endIters = 300000;   // pinned, no wall-clock sizing
        const double logEnd = det_log(0.2 / 3.0);
        for (long long it = 0; it < endIters && cur.first > 0; it++) {
            double frac = (double)it / endIters;
            double T = 3.0 * det_exp(frac * logEnd);   // soft-scale temperature
            static thread_local vector<pair<int,int>> undo;
            undo.clear();
            // 50% guided venue flip on a violating slot, else cycle flip
            bool flip = (nextr() % 2) == 0;
            if (flip) {
                long long tot = 0; for (int v : g_slotConf) tot += v;
                int s = nextr() % nSlots;
                if (tot > 0 && (nextr() % 2)) {
                    long long r = nextr() % tot;
                    s = 0; while ((r -= g_slotConf[s]) >= 0) s++;
                }
                buildSchedule();
                int a = nextr() % nTeams;
                if (opp[a][s] >= 0) {
                    int o = opp[a][s];
                    int g1 = meetIdx[{a, o}], g2 = meetIdx[{o, a}];
                    if (slotOf[g1] != slotOf[g2]) {
                        undo.push_back({g1, slotOf[g1]});
                        undo.push_back({g2, slotOf[g2]});
                        swap(slotOf[g1], slotOf[g2]);
                    }
                }
            } else {
                int halfP = nSlots / 2;
                int s1 = nextr() % nSlots;
                int s2 = nextr() % nSlots;
                if (phasedMode) {
                    int lo = (s1 < halfP) ? 0 : halfP;
                    s2 = lo + nextr() % halfP;
                }
                if (s1 != s2) {
                    buildSchedule();
                    int t0 = nextr() % nTeams;
                    int cur2 = t0, curSlot = s1;
                    static thread_local vector<int> glist;
                    glist.clear();
                    bool ok = true;
                    do {
                        int o = opp[cur2][curSlot];
                        if (o < 0) { ok = false; break; }
                        int h = cur2, a = o;
                        if (homeT[cur2][curSlot] == 0) { h = o; a = cur2; }
                        glist.push_back(meetIdx[{h, a}]);
                        cur2 = o;
                        curSlot = (curSlot == s1) ? s2 : s1;
                    } while (cur2 != t0);
                    if (ok) {
                        for (int g : glist) {
                            undo.push_back({g, slotOf[g]});
                            slotOf[g] = (slotOf[g] == s1) ? s2 : s1;
                        }
                    }
                }
            }
            if (undo.empty()) continue;
            auto nv = evaluate();
            bool accept;
            if (nv.first < curHard) accept = true;
            else if (nv.first == curHard)
                accept = nv.second <= cur.second ||
                         (nextr() % 1000000) < det_exp(-(double)(nv.second - cur.second) / T) * 1000000;
            else accept = false;
            if (accept) {
                curHard = nv.first;
                cur = nv;
                if (cur.first < best.first ||
                    (cur.first == best.first && cur.second < best.second)) {
                    best = cur;
                    bestSlot = slotOf;
                }
            } else {
                for (auto it2 = undo.rbegin(); it2 != undo.rend(); ++it2)
                    slotOf[it2->first] = it2->second;
            }
        }
    }

    // final polish: while infeasible, exhaustively try every mirrored-pair
    // swap and keep the first hard improvement (deterministic). Skipped
    // when the shared pool is nearly exhausted so the solver always
    // terminates inside its budget.
    double elapsedTotal = chrono::duration<double>(
        chrono::steady_clock::now() - t0).count();
    if (elapsedTotal > pool - 8.0) {
        fprintf(stderr, "polish skipped: pool nearly exhausted\n");
    } else {
    slotOf = bestSlot;
    cur = evaluate();
    auto tryFlip = [&](int g1, int g2) -> bool {
        if (slotOf[g1] == slotOf[g2]) return false;
        swap(slotOf[g1], slotOf[g2]);
        auto nv2 = evaluate();
        if (nv2.first < cur.first ||
            (nv2.first == cur.first && nv2.second < cur.second)) {
            cur = nv2;
            return true;
        }
        swap(slotOf[g1], slotOf[g2]);
        return false;
    };
    auto tryCycleFlip = [&](int s1, int s2, int t0) -> bool {
        buildSchedule();
        int cur2 = t0, curSlot = s1;
        static thread_local vector<int> gl;
        gl.clear();
        bool ok = true;
        do {
            int o = opp[cur2][curSlot];
            if (o < 0) { ok = false; break; }
            int h = cur2, a = o;
            if (homeT[cur2][curSlot] == 0) { h = o; a = cur2; }
            gl.push_back(meetIdx[{h, a}]);
            cur2 = o;
            curSlot = (curSlot == s1) ? s2 : s1;
        } while (cur2 != t0);
        if (!ok) return false;
        for (int g : gl) slotOf[g] = (slotOf[g] == s1) ? s2 : s1;
        auto nv2 = evaluate();
        if (nv2.first < cur.first ||
            (nv2.first == cur.first && nv2.second < cur.second)) {
            cur = nv2;
            return true;
        }
        for (int g : gl) slotOf[g] = (slotOf[g] == s1) ? s2 : s1;
        return false;
    };
    for (int pass = 0; pass < 30 && cur.first > 0; pass++) {
        bool improved = false;
        // mirrored-pair swaps
        for (int g1 = 0; g1 < nMeet && !improved; g1++) {
            int h = mHome[g1], a = mAway[g1];
            int g2 = meetIdx[{a, h}];
            if (g2 <= g1) continue;
            improved = tryFlip(g1, g2);
        }
        // all cycle flips across all slot pairs (all cycles)
        for (int s1 = 0; s1 < nSlots && !improved; s1++)
            for (int s2 = s1 + 1; s2 < nSlots && !improved; s2++) {
                vector<char> seen(nTeams, 0);
                for (int t0 = 0; t0 < nTeams && !improved; t0++) {
                    if (seen[t0]) continue;
                    // mark the whole cycle before trying? flip then undo marks
                    improved = tryCycleFlip(s1, s2, t0);
                    // mark cycle teams visited regardless of acceptance:
                    buildSchedule();
                    int cur2 = t0, curSlot = s1;
                    do {
                        seen[cur2] = 1;
                        int o = opp[cur2][curSlot];
                        cur2 = o;
                        curSlot = (curSlot == s1) ? s2 : s1;
                    } while (cur2 != t0);
                }
            }
        if (!improved) break;
    }
    if (cur.first < best.first ||
        (cur.first == best.first && cur.second < best.second)) {
        best = cur;
        bestSlot = slotOf;
    }
    }

    // output the lexicographic best state seen
    vector<int>& out = bestSlot;
    fprintf(stderr, "internal hard=%lld soft=%lld\n", best.first, best.second);
    fprintf(stderr, "itc_stats main_iters=%lld sa_seconds=%.3f\n",
            mainItersDone, mainSaSeconds);
    cout << "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n";
    cout << "<Solution>\n  <MetaData>\n    <InstanceName>" << instanceName
         << "</InstanceName>\n    <Contributor>baseline</Contributor>\n  </MetaData>\n  <Games>\n";
    for (int g = 0; g < nMeet; g++)
        cout << "    <ScheduledMatch home=\"" << mHome[g] << "\" away=\"" << mAway[g]
             << "\" slot=\"" << out[g] << "\"/>\n";
    cout << "  </Games>\n</Solution>\n";
    return 0;
}
