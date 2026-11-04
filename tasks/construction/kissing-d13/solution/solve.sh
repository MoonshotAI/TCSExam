#!/bin/bash
# Oracle: install the D13-root-system proof — all +-e_i +- e_j (i < j) in Z^13
# (the 312 minimal vectors of the D13 lattice), the same construction as the
# solver sibling task kissing-d13's oracle, proving submission_lower at
# n = 312 by native_decide.
# Expected reward: ((312 - 26) / 1128)^3 = (143/564)^3 = 2924207/179406144
# ~= 0.0163, milestone "progress" — identical construction and score to the
# solver edition's oracle, cross-validating predicate alignment between
# editions.
set -e
cp "$(dirname "$0")/Basic.lean" /app/Task/Basic.lean
