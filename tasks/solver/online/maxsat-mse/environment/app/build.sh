#!/bin/bash
# Build the solver. The judge runs exactly this script and then requires an
# executable at <this script's directory>/solver (i.e. /app/solver in the
# container) that reads a weighted MaxSAT instance in classic WCNF format on
# stdin (c/p lines, then "<weight> <lits...> 0" clause lines; weight >= top
# marks a hard clause) and prints the answer on stdout: "o <cost>" and
# "s <STATUS>" lines plus one "v <bitstring>" assignment line (the i-th
# character is the value of variable i).
#
# You may edit this script (or the solver source in ./openwbo) as you like —
# e.g. add more source files, change flags, or produce a wrapper — as long as
# the solver ends up as an executable honoring the I/O contract.
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT/openwbo"
make -j4 r
cp "$ROOT/openwbo/open-wbo_release" "$ROOT/solver"
chmod +x "$ROOT/solver"
