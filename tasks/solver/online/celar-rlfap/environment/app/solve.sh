#!/bin/bash
# Baseline solver entry point for the celar task: a deterministic
# min-conflicts constructor plus CP-SAT at a pinned single-worker
# deterministic budget, emitting the better solution block last (the judge
# scores the LAST complete `f = [...];` block on stdout). See solve.py for
# the pipeline.
#
# Usage: solve.sh INSTANCE_PATH
#
# This is your starting point. Replace it (and build.sh, and the model)
# with anything that honors the same I/O contract. The judging wall-clock
# limit per instance is handed to you in the environment variable
# CELAR_TIME_LIMIT (seconds); the baseline deliberately does NOT use it —
# it stops at its own deterministic budget instead.
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$ROOT/solve.py" "$1"
