#!/bin/bash
# Sanity oracle: the even-weight code (512 words, the trivial baseline,
# score 0 by design), with coverage and cardinality proved by
# `native_decide` (allowed: the judge's axiom whitelist includes
# `Lean.ofReduceBool`). The proof file ships inside solution/ because the
# task package layout is not visible to the oracle on the platform.
set -e
cp "$(dirname "$0")/Basic.lean" /app/Task/Basic.lean
