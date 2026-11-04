#!/bin/bash
# Oracle for cage-girth-lean-open: install the (3,13) record proof — the
# cubic Cayley graph of AGL(1,17) (Hoare's construction, reported in Biggs
# 1989; connection set {(0,16), (1,3), (11,6)}, order 272, girth 13),
# proving submission_lower at cell (3,13), N = 272 = K by native_decide.
# Expected reward: 1.0, milestone "record_matched".
set -e
cp "$(dirname "$0")/Basic.lean" /app/Task/Basic.lean
