#!/bin/bash
# Oracle for ramsey-r3-10-lean-open: install the sanity proof — the
# 18-cycle circulant coloring of K_18 (edge {i,j} red iff (i-j) mod 18 in
# {1,17}), proving submission_lower at N = 18 (R(3,10) >= 19) by
# native_decide; submission_upper keeps its sorry.
# Expected reward: 0.0 under the default solver_cubic mode (N = 18 <= 35
# is below the scoring baseline, milestone "baseline") with valid = 1 —
# the claim is proven, parsed, compiled, and passes the axiom whitelist
# (native_decide is allowed in this task). The same C_18 construction
# scores 0 in the solver sibling ramsey-r3-10 as well (N = 18 <= 35).
set -e
cp "$(dirname "$0")/Basic.lean" /app/Task/Basic.lean
