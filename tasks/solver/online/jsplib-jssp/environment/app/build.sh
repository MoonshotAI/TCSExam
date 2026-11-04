#!/bin/bash
# Build the solver. The judge runs exactly this script and then requires an
# executable at <this script's directory>/solver (i.e. /app/solver in the
# container) honoring the contract:
#     solver INSTANCE_FILE OUTPUT_FILE LIMIT_SECONDS
# It must keep a valid best-so-far schedule in OUTPUT_FILE at all times
# (atomic rewrite on every improvement) and exit 0 on its own before
# LIMIT_SECONDS elapse (the baseline stops its search at 0.92 * LIMIT).
#
# You may edit this script (or the sources) as you like — e.g. compile more
# files, or produce a wrapper that calls python3 / CP-SAT — as long as the
# solver ends up as an executable honoring the I/O contract. Note: all
# top-level /app/*.cpp files are compiled together; keep extra sources in
# subdirectories if you add many files (jssp_check.cpp has its own main()
# and is excluded explicitly).
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC=$(ls "$ROOT"/*.cpp | grep -v 'jssp_check.cpp')
g++ -O2 -std=c++17 -o "$ROOT/solver" $SRC
