// mc_check — validator/evaluator for the maxcut-mqlib task.
//
// Usage: mc_check INSTANCE SOLUTION
//   INSTANCE: MQLib MaxCut format ('#' comments; header "n m"; m lines
//             "u v w", 1-indexed, each edge at most once, no self-loops).
//   SOLUTION: exactly n whitespace-separated tokens, each 0 or 1 — the side
//             of each vertex (as printed by /app/solver).
// On success prints "OK <cut weight>" (cut = sum of w over lines whose
// endpoints differ) and exits 0. On any problem prints "INVALID <reason>"
// and exits 1. Objective semantics deliberately mirror MQLib's (each data
// line contributes once), so values are directly comparable to the MQLib
// results tables; the spot-check record in the measurement package
// verifies this equivalence on sampled instances end to end.

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

static int die(const std::string& msg) {
  std::cout << "INVALID " << msg << "\n";
  return 1;
}

int main(int argc, char** argv) {
  if (argc != 3) {
    std::cerr << "usage: mc_check INSTANCE SOLUTION\n";
    return 2;
  }
  std::ifstream in(argv[1]);
  if (!in) return die("cannot open instance");
  long long n = -1, m = -1;
  std::vector<std::pair<std::pair<int, int>, double> > edges;
  std::string line;
  while (std::getline(in, line)) {
    // trim leading whitespace before comment test
    size_t b = line.find_first_not_of(" \t\r\n");
    if (b == std::string::npos || line[b] == '#') continue;
    std::istringstream ss(line);
    if (n < 0) {
      if (!(ss >> n >> m)) return die("bad header line");
      if (n <= 0 || m < 0) return die("bad header values");
      edges.reserve(m);
      continue;
    }
    long long a, bnode;
    double w;
    if (!(ss >> a >> bnode >> w)) return die("bad data line: " + line);
    if (a < 1 || a > n || bnode < 1 || bnode > n)
      return die("node out of range: " + line);
    if (a == bnode) return die("self-loop in instance: " + line);
    edges.push_back({{(int)a - 1, (int)bnode - 1}, w});
  }
  if (n < 0) return die("empty instance");
  if ((long long)edges.size() != m)
    return die("edge count mismatch: header says " + std::to_string(m) +
               ", file has " + std::to_string(edges.size()));

  std::ifstream sf(argv[2]);
  if (!sf) return die("cannot open solution");
  std::vector<char> x;
  x.reserve(n);
  std::string tok;
  while (sf >> tok) {
    if (tok != "0" && tok != "1")
      return die("bad token in solution: " + tok);
    x.push_back(tok[0] == '1' ? 1 : 0);
    if ((long long)x.size() > n) return die("too many entries in solution");
  }
  if ((long long)x.size() != n)
    return die("solution has " + std::to_string(x.size()) +
               " entries, instance has " + std::to_string(n) + " vertices");

  double cut = 0.0;
  for (const auto& e : edges)
    if (x[e.first.first] != x[e.first.second]) cut += e.second;

  printf("OK %.12g\n", cut);
  return 0;
}
