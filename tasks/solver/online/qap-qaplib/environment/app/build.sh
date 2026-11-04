#!/bin/bash
# Build the solver. The judge runs exactly this script and then requires an
# executable at <this script's directory>/solver (i.e. /app/solver in the
# container) that reads a QAP in the instance text format on stdin and prints a
# permutation (n integers 1..n, token i = location of facility i) on stdout.
#
# You may edit this script (or the solver source) as you like — e.g. add more
# source files, change flags, or produce a wrapper — as long as the solver
# ends up as an executable honoring the I/O contract. Note: all top-level
# /app/*.cpp files are compiled together; keep helper sources in subdirs.
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
g++ -O2 -std=c++17 -o "$ROOT/solver" "$ROOT"/*.cpp
