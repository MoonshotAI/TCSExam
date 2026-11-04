#!/bin/bash
# Oracle: install the I^2_{2,6,2} n=16 proof (same shape as an agent
# submission: Task/Basic.lean with the certificate filled in).
# Provenance: this certificate was produced by kimi k3 during historical
# evaluation and verified in that environment
# twice against the old anchor (score 1.06061, record_broken). After the
# 2026-09-17 anchor correction (standing moved from 64/55 to 142/121), the
# same certificate sits exactly on the record: expected reward 1.0,
# milestone "record_matched", record_broken = 0, beyond_4_3 = 0.
# (It replaces the previous I^2_{1,8,1} oracle, which scores 33/35 under the
# corrected anchor.)
cp /solution/Basic.lean /app/Task/Basic.lean
echo "oracle proof installed"
