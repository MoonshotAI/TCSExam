#!/bin/bash
# hs-pace2025 verifier: compile agent solver, run on the 100 hidden
# plaintext instances from /opt/hs100-private under the official 300 s
# per-instance limit, validate with the official PACE 2025 HS verifier,
# and compute (B-A)/(B-K) clipped. No instance key is required. The work
# dir sits on the disk-backed /logs volume so large intermediate files
# do not consume the tmpfs memory allocation.
mkdir -p /logs/verifier/.work
SCORE_WORK_DIR=/logs/verifier/.work python3 /tests/checker.py
