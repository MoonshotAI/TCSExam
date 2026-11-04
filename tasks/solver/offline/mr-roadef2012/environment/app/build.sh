#!/bin/bash
# Build the solver. The judge runs exactly this script and then requires an
# executable at <this script's directory>/solver (i.e. /app/solver in the
# container) that is invoked as:
#
#   solver MODEL_FILE INITIAL_ASSIGNMENT_FILE OUTPUT_FILE
#
# with the per-instance budget (seconds) in env MR_INSTANCE_SECONDS (legacy
# name MR_TIME_POOL is set to the same value), and writes one
# machine id per process (whitespace-separated) to OUTPUT_FILE.
#
# You may edit this script (or the solver source) as you like — e.g. add more
# source files, change flags, or produce a wrapper — as long as the solver
# ends up as an executable honoring the I/O contract. Note: all top-level
# /app/*.cpp files are compiled together; keep helper sources in subdirs.
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
g++ -O2 -std=c++17 -o "$ROOT/solver" "$ROOT"/*.cpp
