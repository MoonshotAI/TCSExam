#!/bin/bash
# Sanity oracle: the 48-word punctured Paley-Hadamard code (rows of a
# Hadamard matrix of order 24 from Paley's construction on GF(23), plus
# complements, punctured on the last two coordinates), the same
# construction as the solver sibling's
# environment/examples/example_hadamard48.json (passes the solver checker
# at score 0.408412). The minimum-distance condition and the length bound
# are proved by `native_decide` (allowed: the judge's axiom whitelist
# includes `Lean.ofReduceBool` / `Lean.trustCompiler`); the upper-bound
# claim is left unproven (sorry) and does not score. The proof file ships
# inside solution/ because the task package layout is not visible to the
# oracle on the platform.
# Expected reward: ((48 - 2) / 62)^3 = 0.408412...
# (milestone=progress, record_broken=false).
set -e
cp "$(dirname "$0")/Basic.lean" /app/Task/Basic.lean
