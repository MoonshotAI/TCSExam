#!/bin/bash
# Build the solver. The judge runs exactly this script and then requires an
# executable at <this script's directory>/solver (i.e. /app/solver in the
# container). The solver is invoked as
#
#     /app/solver INSTANCE_PATH
#
# with the instance file path as its only argument, and must print its
# answer to stdout: solution blocks in the format
#
#     N = [<bt_max integers>];
#     Q = array3d(<rows>, <cols>, <btimes>, [<m*n*bt_max integers>]);
#
# (exactly what the shipped radiation.mzn output statement produces). The
# judge scores the LAST complete block on stdout, so a solver that prints
# improving solutions as it finds them is safe against the wall-clock kill.
#
# You may edit this script (or the solver sources) as you like — e.g.
# compile C++/Rust code, install a different wrapper, run several MiniZinc
# configurations in parallel — as long as the result is an executable
# honoring the I/O contract above.
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$ROOT/solve.sh" "$ROOT/solver"
chmod +x "$ROOT/solver"
