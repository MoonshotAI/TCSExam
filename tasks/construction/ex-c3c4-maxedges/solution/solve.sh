#!/bin/bash
# Oracle for ex-c3c4-maxedges-lean-open: install the n=124 record-graph
# certificate — the published 629-edge girth-5 construction (Goedgebeur,
# Jooken, Joret, Van den Eede 2025, arXiv:2508.05562; AGT-Kulak/
# searchMaxSizeMinGirth, resultGraphs/iter2UpXtra_150.zip n124.g6 #0),
# proving submission_lower at m = 629 by native_decide. This is the same
# graph as the solver sibling's oracle (solution/record_n124.json), so the
# two editions score the same construction at the same value.
# Expected reward: 1.0 exactly, milestone "record_matched".
set -e
cp "$(dirname "$0")/Basic.lean" /app/Task/Basic.lean
