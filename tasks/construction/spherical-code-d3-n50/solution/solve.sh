#!/bin/bash
# Oracle: install the relaxed-configuration proof — the 50-point
# deterministic Coulomb-relaxation configuration of the solver sibling
# task spherical-code-d3-n50 (coordinates scaled to integers x 10^12; the
# normalized inner product is scale-invariant per point, so it is the same
# certificate), proving submission_upper at T = 877050604932867/10^15 by
# native_decide.
# Expected reward: ((0.9045852811944625 - T) / (0.9045852811944625 -
# 0.868173209126))^3 ~= 0.432418, printed floored to 0.432417, milestone
# "progress" — identical construction and printed score to the solver
# edition's oracle, cross-validating predicate alignment between editions.
set -e
cp "$(dirname "$0")/Basic.lean" /app/Task/Basic.lean
