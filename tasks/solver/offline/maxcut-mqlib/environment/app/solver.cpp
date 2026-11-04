// Baseline MaxCut solver for the maxcut-mqlib task.
//
// Reads a weighted undirected graph on stdin in the MQLib instance format:
//   - lines starting with '#' and empty lines are ignored;
//   - the first remaining line is "n m" (vertices are 1..n);
//   - each of the following m lines is one undirected edge "u v w" with
//     (possibly negative, possibly fractional) weight w; each edge appears
//     at most once.
// Prints a cut on stdout: exactly n lines, line i is 0 or 1 — the side of
// vertex i. The cut value is the total weight of edges whose endpoints land
// on different sides.
//
// The shipped baseline runs one MQLib literature heuristic (Beasley 1998
// tabu search, BEASLEY1998TS — a mid-strength entry in the library's
// 37-heuristic evaluation) with a wall-clock budget. Improve it: pick a
// different heuristic from the library (see /app/mqlib), combine several,
// tune restarts, or replace this file entirely — as long as build.sh
// produces /app/solver honoring the I/O contract.
//
// Environment knobs (both optional):
//   MAXCUT_SECONDS    internal wall-clock budget for the heuristic run
//                     (default 540; the judge hard-kills the process at
//                     600 s per instance, so keep this below that)
//   MAXCUT_HEURISTIC  MQLib heuristic code to run (default BEASLEY1998TS);
//                     any code from `bin/MQLib -l` works, e.g. BURER2002
//   MAXCUT_SEED       RNG seed (default 1 — fixed so runs are reproducible)

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include <unistd.h>

#include "heuristics/heuristic_factory.h"
#include "heuristics/maxcut/max_cut_simple_solution.h"
#include "problem/max_cut_instance.h"
#include "problem/qubo_instance.h"

int main() {
  double limit = 540.0;
  if (const char* env = getenv("MAXCUT_SECONDS")) limit = atof(env);
  std::string code = "BEASLEY1998TS";
  if (const char* env = getenv("MAXCUT_HEURISTIC")) code = env;
  int seed = 1;
  if (const char* env = getenv("MAXCUT_SEED")) seed = atoi(env);
  if (limit <= 0.0) {
    std::cerr << "nonpositive MAXCUT_SECONDS\n";
    return 1;
  }

  // MQLib loads instances from a path: spool stdin to a temp file.
  const char* tmpdir = getenv("TMPDIR");
  std::string pattern = std::string(tmpdir && *tmpdir ? tmpdir : "/tmp") +
                        "/maxcut_inst_XXXXXX";
  std::vector<char> temporary(pattern.begin(), pattern.end());
  temporary.push_back('\0');
  char* tmpl = temporary.data();
  int fd = mkstemp(tmpl);
  if (fd < 0) {
    std::cerr << "mkstemp failed\n";
    return 1;
  }
  {
    std::ostringstream buf;
    buf << std::cin.rdbuf();
    std::string data = buf.str();
    if (write(fd, data.data(), data.size()) != (ssize_t)data.size()) {
      std::cerr << "failed to spool instance\n";
      return 1;
    }
    close(fd);
  }

  srand(seed);
  MaxCutInstance mi(tmpl);
  unlink(tmpl);

  HeuristicFactory factory;
  std::vector<int> assign;
  if (factory.ValidMaxCutHeuristicCode(code)) {
    MaxCutHeuristic* h =
        factory.RunMaxCutHeuristic(code, mi, limit, false, NULL);
    if (!h) {
      std::cerr << "heuristic failed to start\n";
      return 1;
    }
    assign = h->get_best_solution().get_assignments();
    delete h;
  } else if (factory.ValidQUBOHeuristicCode(code)) {
    // QUBO-coded heuristic (as in the MQLib paper's MaxCut evaluation):
    // reduce MaxCut -> QUBO, run, convert the solution back.
    QUBOInstance qi(mi);
    QUBOHeuristic* h =
        factory.RunQUBOHeuristic(code, qi, limit, false, NULL);
    if (!h) {
      std::cerr << "heuristic failed to start\n";
      return 1;
    }
    MaxCutSimpleSolution sol(h->get_best_solution(), mi, NULL);
    assign = sol.get_assignments();
    delete h;
  } else {
    std::cerr << "unknown heuristic code: " << code << "\n";
    return 1;
  }

  if ((int)assign.size() != mi.get_size()) {
    std::cerr << "heuristic returned no full assignment\n";
    return 1;
  }
  std::string out;
  out.reserve(assign.size() * 2);
  for (int a : assign) out += (a > 0 ? '1' : '0'), out += '\n';
  fputs(out.c_str(), stdout);
  return 0;
}
