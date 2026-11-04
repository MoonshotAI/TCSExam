#!/bin/bash
# Sanity oracle: the published record code — Laaksonen–Östergård's 136-word
# construction (arXiv:1604.06022, section "Lower Bound A_2(24,10) >= 136"):
# the orbit expansion of the six published orbit representatives under the
# published two-generator group, encoded as integers (bit i = coordinate i).
# The identical 136 words pass the solver sibling task binary-code-a24-10's
# checker end-to-end at reward 1.0 (valid=1, milestone=record_tied,
# min_distance=10), so the two versions agree on the same construction —
# a cross-check that the predicates are aligned. Minimum distance and
# cardinality are proved by `native_decide` (allowed: the judge's axiom
# whitelist includes `Lean.ofReduceBool`). The upper-bound claim keeps its
# sorry and is simply not scored (one-sided sorry does not sink the other
# claim). The proof file ships inside solution/ because the task package
# layout is not visible to the oracle on the platform.
# Expected reward: 1.0 (accepted=true, construction claim proven at m=136,
# milestone=record_matched, record_broken=false).
set -e
cp "$(dirname "$0")/Basic.lean" /app/Task/Basic.lean
