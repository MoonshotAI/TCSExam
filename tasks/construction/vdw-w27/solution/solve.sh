#!/bin/bash
# Oracle: install the baseline sanity proof — the solver edition's n=400
# baseline coloring (min-conflicts, seed 7) as an Array table, proving
# submission at N = 400 by native_decide.
# Expected reward: 0.0 — N = 400 sits exactly on the scoring baseline
# (valid = 1, milestone = baseline).
set -e
cp "$(dirname "$0")/Basic.lean" /app/Task/Basic.lean
