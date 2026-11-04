#!/bin/bash
# Build the solver. The judge runs exactly this script and then requires an
# executable at <this script's directory>/solver (i.e. /app/solver in the
# container) honoring the I/O contract:
#   solver <instance_prefix> <output_csv>
# where <instance_prefix>_batch.csv / <instance_prefix>_defects.csv describe
# the instance, global_param.csv sits next to them, and the solver writes a
# solution in the solution CSV format to <output_csv>.
#
# The shipped baseline is /app/naive_shelf.py — a simple constructive
# shelf-packing heuristic (see its module docstring). You may edit this
# script (or any source) as you like — replace the baseline entirely if you
# wish — as long as the produced /app/solver honors the contract.
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 -m py_compile "$ROOT/naive_shelf.py"
cp "$ROOT/naive_shelf.py" "$ROOT/solver"
chmod +x "$ROOT/solver"
