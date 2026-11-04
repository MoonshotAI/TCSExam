#!/bin/bash
# Oracle: install the Petersen sanity proof (same shape as an agent submission:
# Task/Basic.lean with the certificate filled in).
# Expected reward: 0 — the 11/10 Petersen value is exactly the baseline of
# the scoring curve (the claim is proven and valid; 0 is by design).
cp /solution/Basic.lean /app/Task/Basic.lean
echo "oracle proof installed"
