#!/bin/bash
# Oracle: install the theta(7,7,7) certificate proof (same shape as an agent
# submission: Task/Basic.lean with the certificate filled in). The instance is
# the Desjardins 2017 family member at n = 20 (three paths of length 7
# between two endpoints) — the same construction as the solver sibling's
# oracle — with OPT_LP = 21, OPT_tour = 26, gap exactly 26/21.
# Expected reward: 1.0 — the 26/21 standing record anchor is exactly matched
# (the claim is proven and valid; record_broken stays false because the
# family value is tied, not beaten).
cp /solution/Basic.lean /app/Task/Basic.lean
echo "oracle proof installed"
