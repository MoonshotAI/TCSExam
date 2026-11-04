#!/bin/bash
# Oracle: install the harvested run1 (zip 6227573) proof — the Paley
# quadratic-residue coloring of K_13, proving submission_lower at N = 13
# (R(5,5) >= 14) by `decide`; submission_upper keeps its sorry.
# Run-time verifier gave reward 1.0 under the then-active alpha_milestone
# mode; under the current solver_cubic mode N = 13 <= 30 scores 0
# (milestone "baseline") but the claim is proven (valid = 1).
# Structure checked locally against tests/reference/Basic.lean on 2026-08-11
# (fixed part byte-relevant-identical, markers intact, no sorry in the lower
# claim body); no Lean toolchain on this machine, so no recompile.
set -e
cp "$(dirname "$0")/Basic.lean" /app/Task/Basic.lean
