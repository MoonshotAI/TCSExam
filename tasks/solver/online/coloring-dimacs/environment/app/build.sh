#!/bin/bash
# Build the solver. The judge runs exactly this script and then requires an
# executable at <this script's directory>/solver (i.e. /app/solver in the
# container) that reads a graph in DIMACS ASCII format on stdin (c/p/e lines)
# and prints a coloring on stdout (first token k = number of colors, then n
# tokens with the 1-based color of each vertex, in vertex order).
#
# You may edit this script (or the solver source) as you like — e.g. add
# more source files, change flags, or produce a wrapper — as long as the
# solver ends up as an executable honoring the I/O contract. Note: all
# top-level /app/*.cpp files are compiled together; keep helper sources in
# subdirectories if you add many files.
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
g++ -O2 -std=c++17 -o "$ROOT/solver" "$ROOT"/*.cpp
