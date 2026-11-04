// Baseline solver for the tcsexam/coloring-dimacs task: a textbook TabuCol
// graph-coloring solver (tabu search for the k-coloring subproblem, Hertz &
// de Werra 1987), written from scratch for this task (no external code).
//
// Pipeline: DSATUR greedy gives an initial proper coloring with UB colors;
// then for k = UB-1, UB-2, ... run TabuCol with a fixed iteration budget per
// k until the total step budget is spent; the best proper coloring found is
// printed.
//
// I/O contract (fixed by the task; do not change):
//   stdin : one graph in DIMACS ASCII format — `c` comment lines, one
//           `p edge n m` header, then `e u v` lines with 1-based endpoints.
//           The edge count m in the header is advisory (some library files
//           count both directions of every edge); the graph is built from the
//           `e` lines.
//   stdout: first token k = number of colors you report, then exactly n
//           tokens: the color of vertex 1..n (1-based color labels). Every
//           edge must join two different colors. Nothing else on stdout.
//           Exit code 0.
//
// Anytime behaviour: the search stops at the first of
//   COLOR_STEP_LIMIT   total tabu iterations across all k levels (default
//                      500000; -1 = unlimited). Being a step count with a
//                      fixed RNG seed, this budget is machine independent:
//                      the baseline reports the same coloring on every
//                      machine.
//   COLOR_SECONDS      wall-clock soft limit in seconds (default 150),
//                      covering the WHOLE run including DIMACS loading — only
//                      a safety net for slow machines.
// and then prints the best proper coloring found so far.

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include <iostream>

// xorshift64; default seed fixed so every run explores the same trajectory.
// COLOR_SEED overrides the seed (used by offline reference-solution mining;
// the judged baseline always runs with the default).
static uint64_t rng_state = 0x9E3779B97F4A7C15ULL;
static inline uint32_t xrand() {
  uint64_t x = rng_state;
  x ^= x << 13; x ^= x >> 7; x ^= x << 17;
  rng_state = x;
  return (uint32_t)(x >> 32);
}

// ------------------------------------------------------------- graph ----
static int n;
static std::vector<std::vector<int>> adj;

static void read_dimacs_stdin() {
  std::vector<std::pair<int,int>> edges;
  std::string line;
  int n_decl = -1, vmax = 0;
  while (std::getline(std::cin, line)) {
    if (line.empty() || line[0] == 'c' || line[0] == '\r') continue;
    if (line[0] == 'p') {
      char kind[32];
      int m_decl;
      if (std::sscanf(line.c_str(), "p %31s %d %d", kind, &n_decl, &m_decl) < 2)
        continue;
    } else if (line[0] == 'e') {
      int u, v;
      if (std::sscanf(line.c_str(), "e %d %d", &u, &v) != 2) continue;
      if (u == v || u < 1 || v < 1) continue;
      if (u > v) std::swap(u, v);
      edges.push_back(std::make_pair(u - 1, v - 1));
      vmax = std::max(vmax, std::max(u, v));
    }
  }
  n = std::max(n_decl, vmax);
  adj.assign(n, {});
  std::sort(edges.begin(), edges.end());
  edges.erase(std::unique(edges.begin(), edges.end()), edges.end());
  for (auto &e : edges) {
    adj[e.first].push_back(e.second);
    adj[e.second].push_back(e.first);
  }
}

// -------------------------------------------------- DSATUR greedy UB ----
// Deterministic: max saturation, tie-break by degree, then by vertex id.
static std::vector<int> dsatur_coloring(int &ncolors) {
  std::vector<int> color(n, -1);
  std::vector<int> sat(n, 0);
  std::vector<char> seen(n, 0);
  int stamped = 0;
  for (int done = 0; done < n; done++) {
    int best = -1;
    for (int v = 0; v < n; v++) {
      if (color[v] != -1) continue;
      if (best == -1 || sat[v] > sat[best] ||
          (sat[v] == sat[best] &&
           (adj[v].size() > adj[best].size() ||
            (adj[v].size() == adj[best].size() && v < best))))
        best = v;
    }
    // smallest color not used by neighbors
    stamped++;
    int lim = 0;
    for (int u : adj[best])
      if (color[u] != -1) { seen[color[u]] = 1; lim = std::max(lim, color[u]); }
    int c = 0;
    while (c <= lim && seen[c]) c++;
    color[best] = c;
    for (int u : adj[best])
      if (color[u] != -1) seen[color[u]] = 0;
    // update saturation of uncolored neighbors
    for (int u : adj[best]) {
      if (color[u] != -1) continue;
      bool fresh = true;
      for (int w : adj[u])
        if (w != best && color[w] == c) { fresh = false; break; }
      if (fresh) sat[u]++;
    }
  }
  ncolors = 0;
  for (int c : color) ncolors = std::max(ncolors, c + 1);
  return color;
}

// --------------------------------------------------------- TabuCol(k) ----
// Minimize the number of conflicting edges with exactly k colors.
// Returns true (and fills best_col) when a conflict-free k-coloring is found
// within the iteration budget.
struct TabuCol {
  int k;
  std::vector<int> col;            // current color of each vertex
  std::vector<int> best_col;
  std::vector<std::vector<int>> cnt; // cnt[v][c] = #neighbors of v with color c
  std::vector<std::vector<int>> tabu; // tabu-until iteration per (v, c)
  long f;                          // #conflicting edges (vertex-double-count/2)
  long best_f;
  std::vector<int> conf;           // conflicted vertex list
  std::vector<int> conf_pos;       // position in conf, -1 if absent
  int nconf;

  TabuCol(int k_) : k(k_), f(0), best_f(0), nconf(0) {
    col.assign(n, 0);
    cnt.assign(n, std::vector<int>(k, 0));
    tabu.assign(n, std::vector<int>(k, -1));
    conf.assign(n, 0);
    conf_pos.assign(n, -1);
    // uniform random initial assignment (classic TabuCol): the large initial
    // conflict count makes the f-proportional tenure work as intended.
    for (int v = 0; v < n; v++) {
      col[v] = xrand() % k;
      for (int u : adj[v]) cnt[u][col[v]]++;
    }
    for (int v = 0; v < n; v++) f += cnt[v][col[v]];
    f /= 2;
    for (int v = 0; v < n; v++)
      if (cnt[v][col[v]] > 0) conf_add(v);
    best_f = f;
    best_col = col;
  }

  inline void conf_add(int v) {
    if (conf_pos[v] == -1) { conf_pos[v] = nconf; conf[nconf++] = v; }
  }
  inline void conf_del(int v) {
    if (conf_pos[v] != -1) {
      int p = conf_pos[v], w = conf[--nconf];
      conf[p] = w; conf_pos[w] = p; conf_pos[v] = -1;
    }
  }

  // one tabu move; returns new f
  long step(long iter) {
    int bv = -1, bc = -1;
    long bdelta = INT64_MAX;
    int nties = 0;
    // scan conflicted vertices only
    for (int i = 0; i < nconf; i++) {
      int v = conf[i];
      int cv = col[v];
      long cur = cnt[v][cv];
      for (int c = 0; c < k; c++) {
        if (c == cv) continue;
        long delta = (long)cnt[v][c] - cur;
        bool tabu_move = tabu[v][c] > iter;
        // aspiration: improving over the best ever seen overrides tabu
        if (tabu_move && f + delta >= best_f) continue;
        if (delta < bdelta) {
          bdelta = delta; bv = v; bc = c; nties = 1;
        } else if (delta == bdelta) {
          // reservoir-style random tie-break (deterministic via xrand)
          nties++;
          if (xrand() % nties == 0) { bv = v; bc = c; }
        }
      }
    }
    if (bv == -1) return f;  // no admissible move (should not happen)
    int v = bv, cold = col[v], cnew = bc;
    // apply the move: update cnt of neighbors, conflict set, f
    for (int u : adj[v]) {
      cnt[u][cold]--;
      if (col[u] == cold && cnt[u][cold] == 0) conf_del(u);
      cnt[u][cnew]++;
      if (col[u] == cnew && cnt[u][cnew] == 1) conf_add(u);
    }
    f += bdelta;
    col[v] = cnew;
    if (cnt[v][cnew] == 0) conf_del(v); else conf_add(v);
    // tenure: grows with current conflict level, plus a small random part
    long tenure = (long)(0.6 * (double)f) + (long)(xrand() % 10);
    tabu[v][cold] = iter + tenure + 1;
    if (f < best_f) { best_f = f; best_col = col; }
    return f;
  }
};

int main() {
  const auto t_start = std::chrono::steady_clock::now();
  const char *sd = std::getenv("COLOR_SEED");
  if (sd) rng_state = std::strtoull(sd, nullptr, 10) | 1ULL;
  read_dimacs_stdin();

  const char *sl = std::getenv("COLOR_STEP_LIMIT");
  long step_limit = sl ? std::atol(sl) : 500000L;
  const char *tl = std::getenv("COLOR_SECONDS");
  double seconds = tl ? std::atof(tl) : 150.0;

  auto time_up = [&]() {
    return std::chrono::duration<double>(std::chrono::steady_clock::now()
                                         - t_start).count() >= seconds;
  };

  int ub;
  std::vector<int> best = dsatur_coloring(ub);
  std::vector<int> greedy = best;
  int best_k = ub;

  long steps_used = 0;
  long iter = 0;
  if (step_limit < 0) step_limit = INT64_MAX / 2;

  // Direct k-coloring mode (COLOR_TARGET_K): attack the k-coloring
  // subproblem directly instead of descending from the greedy UB. Used by
  // the offline reference-solution miner; also handy for debugging ("can my
  // graph be colored with k colors at all?"). Prints the k-coloring if
  // found; exits with code 1 otherwise.
  const char *tk = std::getenv("COLOR_TARGET_K");
  if (tk) {
    int k = std::atoi(tk);
    long budget = step_limit;
    bool found = false;
    std::vector<int> out;
    while (steps_used < budget && !time_up()) {
      TabuCol tc(k);
      long i0 = 0;
      for (i0 = 0; i0 < budget - steps_used; i0++) {
        if ((i0 & 4095) == 0 && time_up()) break;
        if (tc.step(iter++) == 0) { found = true; break; }
      }
      steps_used += i0 + 1;
      if (found) { out = tc.best_col; break; }
    }
    if (!found) {
      std::fprintf(stderr, "[target-k] n=%d k=%d FAILED steps=%ld\n",
                   n, k, steps_used);
      return 1;
    }
    std::printf("%d", k);
    for (int v = 0; v < n; v++) std::printf(" %d", out[v] + 1);
    std::printf("\n");
    std::fflush(stdout);
    std::fprintf(stderr, "[target-k] n=%d k=%d OK steps=%ld\n",
                 n, k, steps_used);
    return 0;
  }

  // Per k level: up to RESTARTS fresh TabuCol runs sharing the level budget.
  const long PER_K = 20000L;      // iteration budget per k level
  const int RESTARTS = 1;         // restarts per level (textbook TabuCol)

  for (int k = ub - 1; k >= 1 && steps_used < step_limit && !time_up(); k--) {
    long budget = std::min(PER_K, step_limit - steps_used);
    bool found = false;
    for (int r = 0; r < RESTARTS && steps_used < step_limit && !time_up();
         r++) {
      TabuCol tc(k);
      long slice = std::min(budget / RESTARTS, step_limit - steps_used);
      long i0 = 0;
      for (i0 = 0; i0 < slice; i0++) {
        if ((i0 & 4095) == 0 && time_up()) break;
        if (tc.step(iter++) == 0) { found = true; break; }
      }
      steps_used += i0 + 1;
      if (found) {
        best = tc.best_col;
        best_k = k;
        break;
      }
    }
    if (!found) break;  // failed at k: k-1 with the same budget is hopeless
  }

  std::printf("%d", best_k);
  for (int v = 0; v < n; v++) std::printf(" %d", best[v] + 1);
  std::printf("\n");
  std::fflush(stdout);
  std::fprintf(stderr,
               "[baseline] n=%d greedy=%d colors=%d steps=%ld wall=%.1f%s\n",
               n, ub, best_k, steps_used,
               std::chrono::duration<double>(std::chrono::steady_clock::now()
                                             - t_start).count(),
               time_up() ? " time-limited" : "");
  return 0;
}
