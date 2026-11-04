#!/bin/bash
# Oracle: install the 10x10-grid proof — centers ((2i+1)/20, (2j+1)/20) in
# the unit square with radius exactly 1/20 = 0.05 — the same construction
# as the solver sibling task circles-in-square-n100's oracle, proving
# submission_lower at r = 0.05 by native_decide.
# Expected reward: exactly 0.0 (the baseline anchor of the cubic
# interpolation), milestone "baseline", certificate valid — identical
# construction and score to the solver edition's oracle, cross-validating
# predicate alignment between editions.
set -e
cp "$(dirname "$0")/Basic.lean" /app/Task/Basic.lean
