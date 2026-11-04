#!/bin/bash
# Build the solver. The judge runs exactly this script and then requires an
# executable at <this script's directory>/solver (i.e. /app/solver in the
# container) that reads an unweighted graph in METIS/DIMACS10 format on
# stdin and prints a k=4 partition (n integers 0..3, token i = block of
# vertex i) on stdout.
#
# You may edit this script (or the solver source) as you like — e.g. add
# more source files, change flags, or produce a wrapper — as long as the
# solver ends up as an executable honoring the I/O contract. Note: all
# top-level /app/*.cpp files are compiled together; keep helper sources in
# subdirectories if you add many files.
#
# /app/kahip/ holds the vendored KaHIP v3.25 static library and its C
# interface header (MIT license); the kaffpa/evaluator/graphchecker
# command-line tools are in /opt/gp/bin/.
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
g++ -O2 -std=c++17 -o "$ROOT/solver" "$ROOT"/*.cpp \
  -I"$ROOT/kahip/include" "$ROOT/kahip/lib/libkahip_static.a" -fopenmp
