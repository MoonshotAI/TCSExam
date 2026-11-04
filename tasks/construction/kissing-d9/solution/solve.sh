#!/bin/bash
# Oracle: install the D9-root-system proof — all +-e_i +- e_j (i < j) in Z^9
# (the 144 minimal vectors of the D9 lattice), the same construction as the
# solver sibling task kissing-d9's oracle, proving submission_lower at
# n = 144 by native_decide.
# Expected reward: ((144 - 18) / 288)^3 = (7/16)^3 = 343/4096 ~= 0.0837,
# milestone "progress" — identical construction and score to the solver
# edition's oracle, cross-validating predicate alignment between editions.
set -e
cp "$(dirname "$0")/Basic.lean" /app/Task/Basic.lean
