// Baseline solver for the tcsexam/maxclique-dimacs task: the MaxCliqueDyn
// exact branch-and-bound (Konc & Janezic 2007, mcqd by Janez Konc, GPL-3.0),
// wrapped as an anytime solver. See mcqd_anytime.h for the (minimal)
// modifications relative to upstream mcqd.
//
// I/O contract (fixed by the task; do not change):
//   stdin : one graph in DIMACS ASCII format — `c` comment lines, one
//           `p edge n m` header, then `e u v` lines with 1-based endpoints.
//           The edge count m in the header is advisory (some library files
//           count both directions); the graph is built from the `e` lines.
//   stdout: first token k = the clique size you report, then exactly k tokens
//           with the 1-based vertex numbers of the clique (each vertex at
//           most once). Nothing else on stdout. Exit code 0.
//
// Anytime behaviour: the search stops at the first of
//   MCQ_STEP_LIMIT     node budget (search steps; default 5000000;
//                      -1 = unlimited). Being a step count, this budget is
//                      machine independent: the baseline reports the same
//                      clique on every machine.
//   MAXCLIQUE_SECONDS  wall-clock soft limit in seconds (default 150). This is
//                      only a safety net for slow machines — on any reasonably
//                      fast machine the node budget fires first (the default
//                      node budget costs well under 150 s on every judged
//                      instance except the two largest MANN graphs).
// and then prints the best clique found so far. If neither limit is hit, the
// search ran to completion and the printed clique is provably maximum.

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <chrono>
#include <iostream>
#include <string>
#include <utility>
#include <vector>
#include "mcqd_anytime.h"

static void read_dimacs_stdin(bool** &conn, int &n) {
  // Vertices are 1-based in the file; n comes from the `p` line (fallback:
  // the largest vertex index seen).
  std::vector<std::pair<int,int>> edges;
  std::string line;
  n = -1;
  int vmax = 0;
  while (std::getline(std::cin, line)) {
    if (line.empty() || line[0] == 'c' || line[0] == '\r') continue;
    if (line[0] == 'p') {
      char kind[32];
      int m_decl;
      if (std::sscanf(line.c_str(), "p %31s %d %d", kind, &n, &m_decl) < 2)
        continue;
    } else if (line[0] == 'e') {
      int u, v;
      if (std::sscanf(line.c_str(), "e %d %d", &u, &v) != 2) continue;
      if (u == v) continue;               // defensive: ignore loops
      if (u < 1 || v < 1) continue;       // defensive: ignore bad endpoints
      edges.push_back(std::make_pair(u - 1, v - 1));
      if (u > vmax) vmax = u;
      if (v > vmax) vmax = v;
    }
  }
  if (n < 0) n = vmax;                    // no p line: fall back to max index
  if (n < vmax) n = vmax;                 // defensive: header smaller than data
  conn = new bool*[n];
  for (int i = 0; i < n; i++) {
    conn[i] = new bool[n];
    std::memset(conn[i], 0, n * sizeof(bool));
  }
  for (size_t i = 0; i < edges.size(); i++) {
    conn[edges[i].first][edges[i].second] = true;
    conn[edges[i].second][edges[i].first] = true;
  }
}

int main() {
  // The wall-clock soft limit covers the WHOLE run (including DIMACS loading):
  // the judge's hard limit is wall clock too, so loading time must come out of
  // the same budget.
  const auto t_start = std::chrono::steady_clock::now();
  bool **conn;
  int n;
  read_dimacs_stdin(conn, n);

  const char* sl = std::getenv("MCQ_STEP_LIMIT");
  long step_limit = sl ? std::atol(sl) : 5000000;
  const char* tl = std::getenv("MAXCLIQUE_SECONDS");
  double seconds = tl ? std::atof(tl) : 150.0;
  double elapsed = std::chrono::duration<double>(
      std::chrono::steady_clock::now() - t_start).count();
  double remaining = seconds - elapsed;
  if (remaining < 0.0) remaining = 0.0;

  Maxclique m(conn, n, 0.025, step_limit, remaining);
  int *qmax;
  int qsize;
  m.mcqdyn(qmax, qsize);

  // The reported clique: size first, then the 1-based vertex numbers.
  std::printf("%d", qsize);
  for (int i = 0; i < qsize; i++) std::printf(" %d", qmax[i] + 1);
  std::printf("\n");
  std::fflush(stdout);
  std::fprintf(stderr, "[baseline] n=%d clique=%d steps=%d proven=%d\n",
               n, qsize, m.steps(), m.proven_optimal() ? 1 : 0);

  delete [] qmax;
  for (int i = 0; i < n; i++) delete [] conn[i];
  delete [] conn;
  return 0;
}
