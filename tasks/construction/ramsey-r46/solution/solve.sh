#!/bin/bash
# Oracle for ramsey-r46-lean-open: install the carried-over baseline
# construction — a 14-vertex induced subgraph (vertices 0..13) of the
# solver sibling ramsey-r46's shipped N = 24 baseline graph
# (environment/examples/example_n24.json, deterministic starter
# local_search.py 24 1); any induced subgraph of a (4,6)-free graph is
# again (4,6)-free. Proves submission_lower at N = 14 (R(4,6) >= 15)
# via a powersetCard bridge discharged by native_decide;
# submission_upper keeps its sorry.
# Expected reward: 0.0 under the default solver_cubic mode (N = 14 <= 24
# is below the scoring baseline, milestone "baseline") with valid = 1 —
# the claim is proven, parsed, compiled, and passes the axiom whitelist
# (native_decide is allowed in this task).
# Why not the full N = 24 sibling graph: verifying its C(24,6) = 134,596
# six-subsets exceeded the judge compile budget in the verification
# sandbox (>40 min); at C(14,6) = 3,003 the same check is routine.
# The oracle demonstrates the chain end-to-end; the N = 24 certificate
# in the sibling still scores 0 there as well (N = 24 <= BASELINE_N).
set -e
cp "$(dirname "$0")/Basic.lean" /app/Task/Basic.lean
