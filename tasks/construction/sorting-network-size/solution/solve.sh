#!/bin/bash
# Oracle: install the record proof — M. W. Green's 1969 network (16 wires,
# 60 comparators, from Dobbelaere's table frozen 2026-09-17) proving
# `submission` at k = 60 by native_decide.
# Expected reward: 1.0 — k = 60 ties the record (milestone record_matched).
set -e
cp "$(dirname "$0")/Basic.lean" /app/Task/Basic.lean
