#!/bin/bash
# Oracle: install the published-record proof — the orthogonal pair of order 10
# from SageMath's MOLS_10_2() (the Parker 1959 record), proving
# submission_lower at n = 10, k = 2 by native_decide.
# Expected reward: (2 - 1) / (2 - 1) = 1.0, milestone "record_matched" —
# re-certifying the published record at the flagship order, identical
# anchors and cell score to the solver sibling task mols-n10.
set -e
cp "$(dirname "$0")/Basic.lean" /app/Task/Basic.lean
