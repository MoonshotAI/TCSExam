#!/bin/bash
# Oracle for quantum-code-25-7-lean-open: the published record [[25,7,5]]
# (cyclic [[21,7,5]] over GF(4) extended by 4 positions; parsed from the
# codetables.de detail page n=25, k=7, entry standing since 2005-06-24),
# packed as 18 literal Pauli25 generators, proving submission at d = 5 by
# native_decide (premises + exact distance in the N(S) \ S semantics).
# Expected reward: 1.0 (accepted, milestone = record_matched).
set -e
cp "$(dirname "$0")/Basic.lean" /app/Task/Basic.lean
