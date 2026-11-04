#!/bin/bash
# radiation-mznchallenge verifier (form 1): the run is over — submit the final /app solver tree
# to the TCSExam judging service for its single hidden-set judging, pull
# the archived per-instance records, and recompute the score locally with the
# metric engine (tests/metric/).
set -Eeuo pipefail
mkdir -p /logs/verifier /logs/artifacts
python3 /tests/fetch_final.py
