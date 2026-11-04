#!/bin/bash
# Build the solver. The judge runs exactly this script and then requires an
# executable at <this script's directory>/solver (i.e. /app/solver in the
# container) that reads a graph in MQLib MaxCut format on stdin and prints a
# cut (n lines of 0/1) on stdout.
#
# You may edit this script (or the solver source) as you like — e.g. add more
# source files, change flags, or produce a wrapper — as long as the solver
# ends up as an executable honoring the I/O contract. The MQLib library in
# /app/mqlib is rebuilt incrementally (make caches its objects in
# /app/mqlib/.build); keep helper sources in subdirectories.
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
make -C "$ROOT/mqlib" -j"$(nproc)" bin/MQLib.a
g++ -O2 -std=c++0x -I"$ROOT/mqlib/include" -o "$ROOT/solver" \
    "$ROOT"/*.cpp "$ROOT/mqlib/bin/MQLib.a" -lm
