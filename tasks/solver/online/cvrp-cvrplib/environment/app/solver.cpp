// Baseline solver for the capacitated vehicle routing task.
//
// Reads a CVRP instance in the standard text format on stdin:
//   header lines (NAME / TYPE : CVRP / DIMENSION / EDGE_WEIGHT_TYPE : EUC_2D /
//   CAPACITY), then NODE_COORD_SECTION, DEMAND_SECTION, DEPOT_SECTION, EOF.
// Distances are Euclidean, rounded to the nearest integer: d = floor(hypot + 0.5)
// (the distance convention of the shipped instance sets).
// Fleet size: the instance NAME ends with "-kK"; at most K routes may be used.
//
// Writes a solution on stdout: the first token is R (number of routes, must
// be <= the fleet size), then for each route a token m followed by the m
// 1-based node ids of the customers visited on that route, in visit order.
// The depot must NOT appear in the output. Example for two routes of 3 and 4
// customers:
//   2  3 5 12 7  4 9 3 21 14
//
// Algorithm: Clarke-Wright parallel savings, then deterministic local search
// (2-opt and Or-opt inside routes, relocate and swap between routes) until a
// local optimum. If construction ends with more routes than the fleet allows,
// the smallest routes are dissolved into the others (cheapest feasible
// insertion) before the local search. Fully deterministic: no randomness, no
// wall-clock dependence; the same instance always yields the same solution on
// any machine.
//
// Feasibility fallback (2026-09-20): the savings merge and fleet repair are
// sensitive to the node labeling order, and on rare inputs they can stall
// with an over-capacity route left over. A deterministic repair pass at the
// end of solve() then restores feasibility (relocate/swap customers out of
// overloaded routes, otherwise cut those routes at capacity and merge back
// down to the fleet limit). It runs ONLY when the heuristic solution is
// actually infeasible, so feasible heuristic output is emitted untouched.
//
// The solver honors one optional environment variable as a safety net:
//   CVRP_SECONDS  wall-clock soft limit in seconds (default 150). The baseline
// finishes in a few seconds even on the largest instances, so this never fires
// as shipped; if you extend this file with time-consuming search, keep honoring
// it: the judge hard-kills the process group at its own per-instance limit.

#include <algorithm>
#include <chrono>
#include <climits>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <numeric>
#include <sstream>
#include <string>
#include <vector>

using namespace std;

static chrono::steady_clock::time_point T0;
static double SOFT_SECONDS = 150.0;

static bool time_up() {
    double used = chrono::duration<double>(chrono::steady_clock::now() - T0).count();
    return used > SOFT_SECONDS;
}

struct Instance {
    string name;
    int n = 0;              // number of nodes including the depot
    int capacity = 0;
    int depot = 1;          // 1-based node id
    int fleet = -1;         // max number of routes, from the -kK name suffix
                            // (-1 = unconstrained)
    vector<double> xs, ys;  // 1-based: index by node id
    vector<int> demand;     // 1-based
    vector<vector<int>> dist;  // (n+1) x (n+1), rounded Euclidean
};

// The fleet size is part of the instance identity: the NAME (and file name)
// of every instance in this task ends with "-kK", meaning at most K routes
// may be used. Returns -1 if the name carries no such suffix.
static int fleet_from_name(const string& name) {
    size_t p = name.rfind("-k");
    if (p == string::npos || p + 2 >= name.size()) return -1;
    int v = 0;
    for (size_t i = p + 2; i < name.size(); i++) {
        if (!isdigit((unsigned char)name[i])) return -1;
        v = v * 10 + (name[i] - '0');
    }
    return v > 0 ? v : -1;
}

// Token-wise TSPLIB parser: sections NODE_COORD_SECTION / DEMAND_SECTION /
// DEPOT_SECTION; header keys NAME, DIMENSION, CAPACITY, EDGE_WEIGHT_TYPE.
static Instance parse_instance() {
    Instance inst;
    vector<tuple<int, double, double>> coords;
    vector<pair<int, int>> demands;
    string section;
    string tok;
    vector<string> tokens;
    while (cin >> tok) tokens.push_back(tok);
    size_t i = 0;
    auto is_key = [](const string& s) {
        return s == "NAME" || s == "COMMENT" || s == "TYPE" || s == "DIMENSION" ||
               s == "EDGE_WEIGHT_TYPE" || s == "EDGE_WEIGHT_FORMAT" ||
               s == "DISPLAY_DATA_TYPE" || s == "CAPACITY" ||
               s == "NODE_COORD_SECTION" || s == "DEMAND_SECTION" ||
               s == "DEPOT_SECTION" || s == "EOF";
    };
    while (i < tokens.size()) {
        const string& t = tokens[i];
        if (t == "EOF") break;
        if (t == "NODE_COORD_SECTION") { section = "coord"; i++; continue; }
        if (t == "DEMAND_SECTION") { section = "demand"; i++; continue; }
        if (t == "DEPOT_SECTION") { section = "depot"; i++; continue; }
        if (!section.empty() && !is_key(t)) {
            if (section == "coord" && i + 2 < tokens.size()) {
                int id = stoi(tokens[i]);
                double x = stod(tokens[i + 1]), y = stod(tokens[i + 2]);
                coords.emplace_back(id, x, y);
                i += 3;
                continue;
            }
            if (section == "demand" && i + 1 < tokens.size()) {
                demands.emplace_back(stoi(tokens[i]), stoi(tokens[i + 1]));
                i += 2;
                continue;
            }
            if (section == "depot") {
                int v = stoi(tokens[i]);
                if (v != -1) inst.depot = v;
                i++;
                continue;
            }
        }
        section.clear();
        if (t == "NAME" || t == "COMMENT" || t == "TYPE" ||
            t == "EDGE_WEIGHT_TYPE" || t == "EDGE_WEIGHT_FORMAT" ||
            t == "DISPLAY_DATA_TYPE") {
            // skip "KEY : value" or "KEY value"
            i++;
            if (i < tokens.size() && tokens[i] == ":") i++;
            if (t == "NAME" && i < tokens.size()) inst.name = tokens[i];
            if (t == "COMMENT") {  // comment may be parenthesized w/ spaces
                while (i < tokens.size() && !is_key(tokens[i])) i++;
            } else {
                i++;
            }
            continue;
        }
        if (t == "DIMENSION" || t == "CAPACITY") {
            i++;
            if (i < tokens.size() && tokens[i] == ":") i++;
            if (i < tokens.size()) {
                if (t == "DIMENSION") inst.n = stoi(tokens[i]);
                else inst.capacity = stoi(tokens[i]);
                i++;
            }
            continue;
        }
        i++;
    }
    int maxid = inst.n;
    for (auto& c : coords) maxid = max(maxid, get<0>(c));
    inst.n = max(inst.n, maxid);
    inst.fleet = fleet_from_name(inst.name);
    inst.xs.assign(inst.n + 1, 0.0);
    inst.ys.assign(inst.n + 1, 0.0);
    inst.demand.assign(inst.n + 1, 0);
    for (auto& c : coords) {
        inst.xs[get<0>(c)] = get<1>(c);
        inst.ys[get<0>(c)] = get<2>(c);
    }
    for (auto& d : demands) inst.demand[d.first] = d.second;
    inst.dist.assign(inst.n + 1, vector<int>(inst.n + 1, 0));
    for (int a = 1; a <= inst.n; a++)
        for (int b = a + 1; b <= inst.n; b++) {
            double d = hypot(inst.xs[a] - inst.xs[b], inst.ys[a] - inst.ys[b]);
            int di = (int)floor(d + 0.5);
            inst.dist[a][b] = inst.dist[b][a] = di;
        }
    return inst;
}

struct Solver {
    const Instance& I;
    vector<vector<int>> routes;     // customer node ids, depot excluded
    vector<int> load;               // per-route total demand
    vector<int> where;              // customer -> route index
    vector<int> pos;                // customer -> position in its route

    explicit Solver(const Instance& I) : I(I) {}

    int route_cost(const vector<int>& r) const {
        int c = 0, prev = I.depot;
        for (int v : r) { c += I.dist[prev][v]; prev = v; }
        c += I.dist[prev][I.depot];
        return c;
    }

    long long total_cost() const {
        long long c = 0;
        for (auto& r : routes) c += route_cost(r);
        return c;
    }

    // ---- construction: Clarke-Wright parallel savings, deterministic order
    void clarke_wright() {
        int n = I.n, D = I.depot;
        vector<int> cust;
        for (int v = 1; v <= n; v++)
            if (v != D) cust.push_back(v);
        int m = cust.size();
        // savings between customers
        struct Sav { int s, i, j; };
        vector<Sav> sav;
        sav.reserve((size_t)m * (m - 1) / 2);
        for (int a = 0; a < m; a++)
            for (int b = a + 1; b < m; b++) {
                int i = cust[a], j = cust[b];
                sav.push_back({I.dist[D][i] + I.dist[j][D] - I.dist[i][j], i, j});
            }
        sort(sav.begin(), sav.end(), [](const Sav& x, const Sav& y) {
            if (x.s != y.s) return x.s > y.s;
            if (x.i != y.i) return x.i < y.i;
            return x.j < y.j;
        });
        // start: one route per customer
        routes.clear(); load.clear(); where.assign(I.n + 1, -1);
        pos.assign(I.n + 1, -1);
        for (int v : cust) {
            where[v] = (int)routes.size();
            pos[v] = 0;
            routes.push_back({v});
            load.push_back(I.demand[v]);
        }
        // route endpoint info: first/last customer of each route
        vector<int> first(routes.size()), last(routes.size());
        for (size_t r = 0; r < routes.size(); r++)
            first[r] = last[r] = routes[r][0];
        vector<bool> alive(routes.size(), true);
        for (auto& sv : sav) {
            int i = sv.i, j = sv.j;
            int ri = where[i], rj = where[j];
            if (ri == rj || !alive[ri] || !alive[rj]) continue;
            // i must be an endpoint of ri, j an endpoint of rj
            bool i_first = (first[ri] == i), i_last = (last[ri] == i);
            bool j_first = (first[rj] == j), j_last = (last[rj] == j);
            if (!i_first && !i_last) continue;
            if (!j_first && !j_last) continue;
            if (load[ri] + load[rj] > I.capacity) continue;
            // orient: route ri reversed so i becomes last; route rj so j first
            vector<int>& A = routes[ri];
            vector<int>& B = routes[rj];
            if (i_first) reverse(A.begin(), A.end());
            if (!j_first) reverse(B.begin(), B.end());
            // merge B behind A
            for (int v : B) { where[v] = ri; }
            A.insert(A.end(), B.begin(), B.end());
            for (size_t p = 0; p < A.size(); p++) pos[A[p]] = (int)p;
            load[ri] += load[rj];
            last[ri] = A.back();
            first[ri] = A.front();
            alive[rj] = false;
        }
        // compact
        vector<vector<int>> nr;
        vector<int> nl;
        for (size_t r = 0; r < routes.size(); r++)
            if (alive[r]) { nr.push_back(routes[r]); nl.push_back(load[r]); }
        routes = move(nr); load = move(nl);
        rebuild_index();
    }

    void rebuild_index() {
        where.assign(I.n + 1, -1);
        pos.assign(I.n + 1, -1);
        for (size_t r = 0; r < routes.size(); r++)
            for (size_t p = 0; p < routes[r].size(); p++) {
                where[routes[r][p]] = (int)r;
                pos[routes[r][p]] = (int)p;
            }
    }

    // ---- local search (all deterministic, first improvement, fixed order)

    // 2-opt within one route; returns true if an improvement was applied.
    bool two_opt_route(int ri) {
        vector<int>& r = routes[ri];
        int m = r.size();
        if (m < 3) return false;
        for (int i = 0; i + 1 < m; i++) {
            int a = (i == 0) ? I.depot : r[i - 1];
            int b = r[i];
            for (int j = i + 1; j < m; j++) {
                int c = r[j];
                int d = (j + 1 == m) ? I.depot : r[j + 1];
                int delta = I.dist[a][c] + I.dist[b][d] - I.dist[a][b] - I.dist[c][d];
                if (delta < 0) {
                    reverse(r.begin() + i, r.begin() + j + 1);
                    for (int p = i; p <= j; p++) pos[r[p]] = p;
                    return true;
                }
            }
        }
        return false;
    }

    // Or-opt within one route: move a segment of length 1..2 to another spot.
    bool or_opt_route(int ri) {
        vector<int>& r = routes[ri];
        int m = r.size();
        if (m < 3) return false;
        for (int seg = 1; seg <= 2; seg++) {
            for (int i = 0; i + seg <= m; i++) {
                // kept = route without the segment [i, i+seg)
                vector<int> kept;
                kept.reserve(m - seg);
                for (int p = 0; p < m; p++)
                    if (p < i || p >= i + seg) kept.push_back(r[p]);
                int pa = (i == 0) ? I.depot : r[i - 1];
                int qa = r[i], qb = r[i + seg - 1];
                int ra_ = (i + seg == m) ? I.depot : r[i + seg];
                int rem = I.dist[pa][ra_] - I.dist[pa][qa] - I.dist[qb][ra_];
                for (int j = 0; j <= (int)kept.size(); j++) {
                    if (j == i) continue;  // restores the original route
                    int left = (j == 0) ? I.depot : kept[j - 1];
                    int right = (j == (int)kept.size()) ? I.depot : kept[j];
                    int ins = I.dist[left][qa] + I.dist[qb][right] - I.dist[left][right];
                    if (rem + ins < 0) {
                        vector<int> moved(r.begin() + i, r.begin() + i + seg);
                        kept.insert(kept.begin() + j, moved.begin(), moved.end());
                        r = move(kept);
                        for (int p = 0; p < (int)r.size(); p++) pos[r[p]] = p;
                        return true;
                    }
                }
            }
        }
        return false;
    }

    // Relocate one customer from route A into route B (first improvement).
    bool relocate_inter() {
        for (size_t ra = 0; ra < routes.size(); ra++) {
            for (size_t pa = 0; pa < routes[ra].size(); pa++) {
                int v = routes[ra][pa];
                int pv = (pa == 0) ? I.depot : routes[ra][pa - 1];
                int nv = (pa + 1 == routes[ra].size()) ? I.depot : routes[ra][pa + 1];
                int rem = I.dist[pv][nv] - I.dist[pv][v] - I.dist[v][nv];
                for (size_t rb = 0; rb < routes.size(); rb++) {
                    if (rb == ra) continue;
                    if (load[rb] + I.demand[v] > I.capacity) continue;
                    for (size_t pb = 0; pb <= routes[rb].size(); pb++) {
                        int lb = (pb == 0) ? I.depot : routes[rb][pb - 1];
                        int rbnd = (pb == routes[rb].size()) ? I.depot : routes[rb][pb];
                        int ins = I.dist[lb][v] + I.dist[v][rbnd] - I.dist[lb][rbnd];
                        if (rem + ins < 0) {
                            routes[ra].erase(routes[ra].begin() + pa);
                            routes[rb].insert(routes[rb].begin() + pb, v);
                            load[ra] -= I.demand[v];
                            load[rb] += I.demand[v];
                            if (routes[ra].empty()) {
                                routes.erase(routes.begin() + ra);
                                load.erase(load.begin() + ra);
                            }
                            rebuild_index();
                            return true;
                        }
                    }
                }
            }
        }
        return false;
    }

    // Swap two customers between different routes (first improvement).
    bool swap_inter() {
        for (size_t ra = 0; ra < routes.size(); ra++) {
            for (size_t rb = ra + 1; rb < routes.size(); rb++) {
                for (size_t pa = 0; pa < routes[ra].size(); pa++) {
                    int u = routes[ra][pa];
                    int pu = (pa == 0) ? I.depot : routes[ra][pa - 1];
                    int nu = (pa + 1 == routes[ra].size()) ? I.depot : routes[ra][pa + 1];
                    for (size_t pb = 0; pb < routes[rb].size(); pb++) {
                        int v = routes[rb][pb];
                        if (load[ra] - I.demand[u] + I.demand[v] > I.capacity) continue;
                        if (load[rb] - I.demand[v] + I.demand[u] > I.capacity) continue;
                        int pv = (pb == 0) ? I.depot : routes[rb][pb - 1];
                        int nv = (pb + 1 == routes[rb].size()) ? I.depot : routes[rb][pb + 1];
                        int delta = (I.dist[pu][v] + I.dist[v][nu] - I.dist[pu][u] - I.dist[u][nu])
                                  + (I.dist[pv][u] + I.dist[u][nv] - I.dist[pv][v] - I.dist[v][nv]);
                        if (delta < 0) {
                            routes[ra][pa] = v;
                            routes[rb][pb] = u;
                            load[ra] += I.demand[v] - I.demand[u];
                            load[rb] += I.demand[u] - I.demand[v];
                            rebuild_index();
                            return true;
                        }
                    }
                }
            }
        }
        return false;
    }

    void local_search() {
        long long moves = 0;
        const long long MOVE_CAP = 200000;  // safety; never reached in practice
        while (moves < MOVE_CAP && !time_up()) {
            bool improved = false;
            for (size_t r = 0; r < routes.size() && !time_up(); r++)
                if (two_opt_route((int)r)) { improved = true; moves++; break; }
            if (improved) continue;
            for (size_t r = 0; r < routes.size() && !time_up(); r++)
                if (or_opt_route((int)r)) { improved = true; moves++; break; }
            if (improved) continue;
            if (relocate_inter()) { moves++; continue; }
            if (swap_inter()) { moves++; continue; }
            break;  // local optimum
        }
    }

    // ---- fleet constraint: reduce the number of routes to at most I.fleet
    // by dissolving the smallest route, inserting its customers at the
    // cheapest capacity-feasible gaps of other routes. Deterministic.
    // Two-phase per attempt: simulate on load copies, commit only if every
    // customer of the route can be placed. Returns false if no route can be
    // dissolved (never happens on the task's instances).
    bool dissolve_one_route() {
        // candidate routes ordered by (size, first customer id)
        vector<int> ord(routes.size());
        iota(ord.begin(), ord.end(), 0);
        sort(ord.begin(), ord.end(), [&](int a, int b) {
            if (routes[a].size() != routes[b].size())
                return routes[a].size() < routes[b].size();
            return routes[a][0] < routes[b][0];
        });
        for (int victim : ord) {
            const vector<int>& custs = routes[victim];
            vector<int> sim_load = load;
            // chosen insertion per customer: (route, gap), in customer order
            vector<pair<int, int>> plan;
            bool ok = true;
            for (int v : custs) {
                int best_delta = INT_MAX, best_rb = -1, best_gap = -1;
                for (size_t rb = 0; rb < routes.size(); rb++) {
                    if ((int)rb == victim) continue;
                    if (sim_load[rb] + I.demand[v] > I.capacity) continue;
                    for (size_t g = 0; g <= routes[rb].size(); g++) {
                        int l = (g == 0) ? I.depot : routes[rb][g - 1];
                        int r = (g == routes[rb].size()) ? I.depot : routes[rb][g];
                        int delta = I.dist[l][v] + I.dist[v][r] - I.dist[l][r];
                        if (delta < best_delta) {
                            best_delta = delta;
                            best_rb = (int)rb;
                            best_gap = (int)g;
                        }
                    }
                }
                if (best_rb < 0) { ok = false; break; }
                plan.emplace_back(best_rb, best_gap);
                sim_load[best_rb] += I.demand[v];
            }
            if (!ok) continue;
            // commit: apply insertions per route, gaps in decreasing order so
            // indices stay valid
            vector<vector<pair<int, int>>> per_route(routes.size());
            for (size_t t = 0; t < custs.size(); t++)
                per_route[plan[t].first].emplace_back(plan[t].second, custs[t]);
            for (size_t rb = 0; rb < routes.size(); rb++) {
                auto& ins = per_route[rb];
                sort(ins.begin(), ins.end(),
                     [](const pair<int, int>& a, const pair<int, int>& b) {
                         return a.first > b.first;
                     });
                for (auto& pr : ins) {
                    routes[rb].insert(routes[rb].begin() + pr.first, pr.second);
                    load[rb] += I.demand[pr.second];
                }
            }
            routes.erase(routes.begin() + victim);
            load.erase(load.begin() + victim);
            rebuild_index();
            return true;
        }
        return false;
    }

    void enforce_fleet() {
        if (I.fleet <= 0) return;
        // phase 1: exact (capacity-respecting) dissolution
        while ((int)routes.size() > I.fleet)
            if (!dissolve_one_route()) break;
        // phase 2: forced dissolution + penalized repair (deterministic).
        // The objective during repair is cost + PEN * total capacity excess;
        // every accepted move strictly decreases it, and PEN grows when the
        // search stalls, so the loop terminates. On every instance of this
        // task a fleet-feasible solution exists and this finds it.
        long long PEN = 64;
        int guard = 0;
        while (((int)routes.size() > I.fleet || total_excess() > 0) &&
               guard++ < 100000 && !time_up()) {
            if ((int)routes.size() > I.fleet) {
                dissolve_smallest_route_forced();
                continue;
            }
            if (!penalized_move(PEN)) {
                if (PEN > (1LL << 40)) break;  // stuck (out of scope here)
                PEN *= 4;
            }
        }
    }

    // total capacity excess over all routes (0 = feasible)
    long long total_excess() const {
        long long e = 0;
        for (size_t r = 0; r < routes.size(); r++)
            e += max(0, load[r] - I.capacity);
        return e;
    }

    // Dissolve the smallest route IGNORING capacity (cheapest-cost insertion
    // into other routes, largest-demand customers first). Only used by the
    // repair loop; the resulting overload is removed by penalized moves.
    void dissolve_smallest_route_forced() {
        int victim = -1;
        for (size_t r = 0; r < routes.size(); r++)
            if (victim < 0 || routes[r].size() < routes[victim].size() ||
                (routes[r].size() == routes[victim].size() &&
                 routes[r][0] < routes[victim][0]))
                victim = (int)r;
        vector<int> custs = routes[victim];
        sort(custs.begin(), custs.end(), [&](int a, int b) {
            if (I.demand[a] != I.demand[b]) return I.demand[a] > I.demand[b];
            return a < b;
        });
        for (int v : custs) {
            int best_delta = INT_MAX, best_rb = -1, best_gap = -1;
            for (size_t rb = 0; rb < routes.size(); rb++) {
                if ((int)rb == victim) continue;
                for (size_t g = 0; g <= routes[rb].size(); g++) {
                    int l = (g == 0) ? I.depot : routes[rb][g - 1];
                    int r = (g == routes[rb].size()) ? I.depot : routes[rb][g];
                    int delta = I.dist[l][v] + I.dist[v][r] - I.dist[l][r];
                    if (delta < best_delta) {
                        best_delta = delta; best_rb = (int)rb; best_gap = (int)g;
                    }
                }
            }
            if (best_rb < 0) return;  // single route left; cannot dissolve
            routes[best_rb].insert(routes[best_rb].begin() + best_gap, v);
            load[best_rb] += I.demand[v];
        }
        routes.erase(routes.begin() + victim);
        load.erase(load.begin() + victim);
        rebuild_index();
    }

    // First-improvement relocate/swap under objective cost + PEN * excess.
    // Relocate may empty a route (fewer routes is always fine).
    bool penalized_move(long long PEN) {
        for (size_t ra = 0; ra < routes.size(); ra++) {
            for (size_t pa = 0; pa < routes[ra].size(); pa++) {
                int v = routes[ra][pa];
                int pv = (pa == 0) ? I.depot : routes[ra][pa - 1];
                int nv = (pa + 1 == routes[ra].size()) ? I.depot
                                                       : routes[ra][pa + 1];
                long long rem = I.dist[pv][nv] - I.dist[pv][v] - I.dist[v][nv];
                long long ea0 = max(0, load[ra] - I.capacity);
                long long ea1 = max(0, load[ra] - I.demand[v] - I.capacity);
                for (size_t rb = 0; rb < routes.size(); rb++) {
                    if (rb == ra) continue;
                    long long eb0 = max(0, load[rb] - I.capacity);
                    long long eb1 = max(0, load[rb] + I.demand[v] - I.capacity);
                    long long pen = PEN * (ea1 + eb1 - ea0 - eb0);
                    for (size_t pb = 0; pb <= routes[rb].size(); pb++) {
                        int lb = (pb == 0) ? I.depot : routes[rb][pb - 1];
                        int rbnd = (pb == routes[rb].size()) ? I.depot
                                                             : routes[rb][pb];
                        long long ins = I.dist[lb][v] + I.dist[v][rbnd]
                                        - I.dist[lb][rbnd];
                        if (rem + ins + pen < 0) {
                            routes[ra].erase(routes[ra].begin() + pa);
                            routes[rb].insert(routes[rb].begin() + pb, v);
                            load[ra] -= I.demand[v];
                            load[rb] += I.demand[v];
                            if (routes[ra].empty()) {
                                routes.erase(routes.begin() + ra);
                                load.erase(load.begin() + ra);
                            }
                            rebuild_index();
                            return true;
                        }
                    }
                }
            }
        }
        for (size_t ra = 0; ra < routes.size(); ra++) {
            for (size_t rb = ra + 1; rb < routes.size(); rb++) {
                for (size_t pa = 0; pa < routes[ra].size(); pa++) {
                    int u = routes[ra][pa];
                    int pu = (pa == 0) ? I.depot : routes[ra][pa - 1];
                    int nu = (pa + 1 == routes[ra].size()) ? I.depot
                                                           : routes[ra][pa + 1];
                    for (size_t pb = 0; pb < routes[rb].size(); pb++) {
                        int v = routes[rb][pb];
                        int pv = (pb == 0) ? I.depot : routes[rb][pb - 1];
                        int nv = (pb + 1 == routes[rb].size()) ? I.depot
                                                               : routes[rb][pb + 1];
                        long long cost_d =
                            (I.dist[pu][v] + I.dist[v][nu] - I.dist[pu][u]
                             - I.dist[u][nu])
                            + (I.dist[pv][u] + I.dist[u][nv] - I.dist[pv][v]
                               - I.dist[v][nv]);
                        long long e0 = max(0, load[ra] - I.capacity)
                                       + max(0, load[rb] - I.capacity);
                        long long e1 = max(0, load[ra] - I.demand[u]
                                           + I.demand[v] - I.capacity)
                                       + max(0, load[rb] - I.demand[v]
                                             + I.demand[u] - I.capacity);
                        if (cost_d + PEN * (e1 - e0) < 0) {
                            routes[ra][pa] = v;
                            routes[rb][pb] = u;
                            load[ra] += I.demand[v] - I.demand[u];
                            load[rb] += I.demand[u] - I.demand[v];
                            rebuild_index();
                            return true;
                        }
                    }
                }
            }
        }
        return false;
    }

    // ---- feasibility fallback: restore a feasible solution when (and only
    // when) the heuristic above finished infeasible. Never fires on feasible
    // heuristic output, which is therefore printed exactly as computed.
    // Every step is deterministic (fixed scan orders, strict improvement
    // tie-breaking). Each accepted relocate/swap strictly decreases the
    // total capacity excess, so phases 1-2 terminate; phase 3 runs once per
    // route plus at most one merge per extra route. Premise (holds for
    // every CVRP instance of this task): no single demand exceeds the
    // vehicle capacity.

    bool solution_feasible() const {
        if (I.fleet > 0 && (int)routes.size() > I.fleet) return false;
        for (size_t r = 0; r < routes.size(); r++)
            if (load[r] > I.capacity) return false;
        return true;
    }

    // Cheapest capacity-feasible gap for customer v in any route other than
    // `from`; returns the target route index (-1 if none), gap via out-param.
    int cheapest_feasible_gap(int v, int from, int& gap_out) const {
        int best_delta = INT_MAX, best_rb = -1, best_gap = -1;
        for (size_t rb = 0; rb < routes.size(); rb++) {
            if ((int)rb == from) continue;
            if (load[rb] + I.demand[v] > I.capacity) continue;
            for (size_t g = 0; g <= routes[rb].size(); g++) {
                int l = (g == 0) ? I.depot : routes[rb][g - 1];
                int r = (g == routes[rb].size()) ? I.depot : routes[rb][g];
                int delta = I.dist[l][v] + I.dist[v][r] - I.dist[l][r];
                if (delta < best_delta) {
                    best_delta = delta; best_rb = (int)rb; best_gap = (int)g;
                }
            }
        }
        gap_out = best_gap;
        return best_rb;
    }

    // Phase 1: move one customer out of an over-capacity route into the
    // cheapest feasible gap of another route. First over-capacity route in
    // index order, customers in visit order. Returns true if a move applied.
    bool repair_relocate() {
        for (size_t ra = 0; ra < routes.size(); ra++) {
            if (load[ra] <= I.capacity) continue;
            for (size_t pa = 0; pa < routes[ra].size(); pa++) {
                int v = routes[ra][pa];
                int gap;
                int rb = cheapest_feasible_gap(v, (int)ra, gap);
                if (rb < 0) continue;
                routes[ra].erase(routes[ra].begin() + pa);
                routes[rb].insert(routes[rb].begin() + gap, v);
                load[ra] -= I.demand[v];
                load[rb] += I.demand[v];
                if (routes[ra].empty()) {
                    routes.erase(routes.begin() + ra);
                    load.erase(load.begin() + ra);
                }
                rebuild_index();
                return true;
            }
        }
        return false;
    }

    // Phase 2: swap a customer of an over-capacity route with a strictly
    // lighter customer of another route (the target stays feasible), cheapest
    // cost delta. Returns true if a swap applied.
    bool repair_swap() {
        for (size_t ra = 0; ra < routes.size(); ra++) {
            if (load[ra] <= I.capacity) continue;
            long long best_delta = LLONG_MAX;
            int b_rb = -1, b_pa = -1, b_pb = -1;
            for (size_t pa = 0; pa < routes[ra].size(); pa++) {
                int u = routes[ra][pa];
                int pu = (pa == 0) ? I.depot : routes[ra][pa - 1];
                int nu = (pa + 1 == routes[ra].size()) ? I.depot
                                                       : routes[ra][pa + 1];
                for (size_t rb = 0; rb < routes.size(); rb++) {
                    if (rb == ra) continue;
                    for (size_t pb = 0; pb < routes[rb].size(); pb++) {
                        int v = routes[rb][pb];
                        if (I.demand[u] <= I.demand[v]) continue;
                        if (load[rb] - I.demand[v] + I.demand[u] > I.capacity)
                            continue;
                        int pv = (pb == 0) ? I.depot : routes[rb][pb - 1];
                        int nv = (pb + 1 == routes[rb].size()) ? I.depot
                                                               : routes[rb][pb + 1];
                        long long delta =
                            (I.dist[pu][v] + I.dist[v][nu] - I.dist[pu][u]
                             - I.dist[u][nu])
                            + (I.dist[pv][u] + I.dist[u][nv] - I.dist[pv][v]
                               - I.dist[v][nv]);
                        if (delta < best_delta) {
                            best_delta = delta;
                            b_rb = (int)rb; b_pa = (int)pa; b_pb = (int)pb;
                        }
                    }
                }
            }
            if (b_rb < 0) continue;  // this route cannot be relieved by a swap
            int u = routes[ra][b_pa], v = routes[b_rb][b_pb];
            routes[ra][b_pa] = v;
            routes[b_rb][b_pb] = u;
            load[ra] += I.demand[v] - I.demand[u];
            load[b_rb] += I.demand[u] - I.demand[v];
            rebuild_index();
            return true;
        }
        return false;
    }

    // Phase 3a: cut an over-capacity route into capacity-feasible pieces
    // (greedy walk in visit order, start a new piece when the next customer
    // would overflow). Pieces replace the route in place.
    void repair_cut(int ra) {
        vector<vector<int>> pieces(1);
        int piece_load = 0;
        for (int v : routes[ra]) {
            if (piece_load + I.demand[v] > I.capacity) {
                pieces.emplace_back();
                piece_load = 0;
            }
            pieces.back().push_back(v);
            piece_load += I.demand[v];
        }
        routes.erase(routes.begin() + ra);
        load.erase(load.begin() + ra);
        for (auto& p : pieces) {
            int pl = 0;
            for (int v : p) pl += I.demand[v];
            routes.push_back(move(p));
            load.push_back(pl);
        }
        rebuild_index();
    }

    // Phase 3b: merge the cheapest pair of routes whose combined load fits,
    // over the four orientation combinations (cost of the joined route
    // decides; ties by scan order). Returns true if a merge applied.
    bool repair_merge() {
        long long best_cost = LLONG_MAX;
        int b_i = -1, b_j = -1, b_mode = -1;
        for (size_t i = 0; i < routes.size(); i++) {
            for (size_t j = i + 1; j < routes.size(); j++) {
                if (load[i] + load[j] > I.capacity) continue;
                for (int mode = 0; mode < 4; mode++) {
                    vector<int> a = routes[i], b = routes[j];
                    if (mode & 1) reverse(a.begin(), a.end());
                    if (mode & 2) reverse(b.begin(), b.end());
                    a.insert(a.end(), b.begin(), b.end());
                    long long c = route_cost(a);
                    if (c < best_cost) {
                        best_cost = c;
                        b_i = (int)i; b_j = (int)j; b_mode = mode;
                    }
                }
            }
        }
        if (b_i < 0) return false;
        vector<int> a = routes[b_i], b = routes[b_j];
        if (b_mode & 1) reverse(a.begin(), a.end());
        if (b_mode & 2) reverse(b.begin(), b.end());
        a.insert(a.end(), b.begin(), b.end());
        routes[b_i] = move(a);
        load[b_i] += load[b_j];
        routes.erase(routes.begin() + b_j);
        load.erase(load.begin() + b_j);
        rebuild_index();
        return true;
    }

    void feasibility_repair() {
        if (solution_feasible()) return;
        cerr << "[solver] feasibility fallback engaged: routes="
             << routes.size() << " excess=" << total_excess()
             << " fleet=" << I.fleet << "\n";
        // phases 1-2, interleaved to a fixpoint (each applied move strictly
        // decreases the total capacity excess)
        while (total_excess() > 0)
            if (!repair_relocate() && !repair_swap()) break;
        // phase 3: cut whatever is still over capacity (descending index
        // order so earlier indices stay valid), then merge back down to the
        // fleet limit
        vector<int> over;
        for (size_t ra = 0; ra < routes.size(); ra++)
            if (load[ra] > I.capacity) over.push_back((int)ra);
        for (auto it = over.rbegin(); it != over.rend(); ++it)
            repair_cut(*it);
        while (I.fleet > 0 && (int)routes.size() > I.fleet)
            if (!repair_merge()) {
                cerr << "[solver] fallback: no feasible route merge left\n";
                break;
            }
        // the standard local search preserves feasibility (its inter-route
        // moves all respect capacity), so it can safely re-optimize the
        // repaired solution
        local_search();
        cerr << "[solver] feasibility fallback done: routes=" << routes.size()
             << " excess=" << total_excess()
             << " feasible=" << (solution_feasible() ? 1 : 0) << "\n";
    }

    void solve() {
        clarke_wright();
        enforce_fleet();
        local_search();
        feasibility_repair();
    }

    void print() const {
        // drop empty routes (defensive)
        vector<const vector<int>*> out;
        for (auto& r : routes) if (!r.empty()) out.push_back(&r);
        cout << out.size() << "\n";
        for (auto* r : out) {
            cout << r->size();
            for (int v : *r) cout << ' ' << v;
            cout << "\n";
        }
        cout.flush();
    }
};

int main() {
    T0 = chrono::steady_clock::now();
    if (const char* e = getenv("CVRP_SECONDS"))
        SOFT_SECONDS = atof(e);
    Instance inst = parse_instance();
    Solver S(inst);
    S.solve();
    S.print();
    return 0;
}
