import Mathlib

set_option maxRecDepth 100000
set_option maxHeartbeats 0

-- Instance synthesis for `MinDist10Code` on a concrete code needs more
-- than the default `synthInstance.maxSize` (128): the zipped pair loop
-- nests `List` and `Nat` instance trees. 512 gives comfortable headroom
-- so that `decide` / `native_decide` work on `MinDist10Code S` directly.
set_option synthInstance.maxSize 512

/-!
# Binary codes of length 22 and minimum distance 10 — fixed definition layer

A **binary error-correcting code** of length 22 and minimum Hamming
distance 10 is a set `S` of 22-bit words such that every two distinct
codewords differ in at least 10 positions. The largest possible size is
`A(22,10)`, known only to lie in `64 ≤ A(22,10) ≤ 84` (see
`instruction.md` for references).

Words are functions `Fin 22 → Fin 2`; `hammingDist x y` (mathlib) counts
the coordinates on which `x` and `y` differ. A code is presented as a
**list** of words; `isMinDist10Code S` below checks computably that `S`
has minimum distance at least 10, and `MinDist10Code S` packages the
check as a proposition.

Everything from the top of this file down to the line
`-- END OF FIXED PART` is part of the problem statement. The judge checks
it verbatim; do not edit, move, or delete it. Your work (auxiliary
definitions, lemmas, and the proofs of the claims) goes below the mark.
-/

/-- `isMinDist10Code S` is the computable predicate "the list `S` of
22-bit words is a binary code of length 22 and minimum Hamming distance
10":

1. `S` is nonempty;
2. for every pair of positions `i ≠ j` in `S`, the words at those
   positions differ in at least 10 coordinates (`hammingDist x y ≥ 10`).

This matches the checker of the solver sibling task `binary-code-a22-10`
clause by clause:

- **duplicate words** need no clause of their own: two positions carrying
  the same word have Hamming distance `0 < 10`, so clause 2 already
  rejects every list with duplicates, exactly as the checker rejects
  them;
- clause 2 quantifies over **positions** (via `List.zipIdx`), so the
  diagonal cases `i = j` (where the distance would be 0) are excluded,
  while every pair of distinct positions is checked — the checker's
  pairwise `d < 10` rejection, read contrapositively;
- an **empty** list is rejected by clause 1, exactly as the checker
  requires a nonempty codeword list.

All clauses live inside a single computable `Bool` function, so `decide` /
`native_decide` check concrete codes directly and no per-clause
`Decidable` instance synthesis is involved. Quantifying over positions
with `Bool`-valued comparisons also keeps equality of words (`x = y` on
`Fin 22 → Fin 2`) out of the decision procedure entirely.

A computable `isMinDist10Code S = true` (packaged as `MinDist10Code S`)
together with `k ≤ S.length` certifies `A(22,10) ≥ k`; a proof that
`MinDist10Code S` implies `S.length ≤ m` for every `S` certifies
`A(22,10) ≤ m` (every valid list has pairwise distinct words, so its
length is the cardinality of its set of words). -/
def isMinDist10Code (S : List (Fin 22 → Fin 2)) : Bool :=
  decide (0 < S.length) &&
    S.zipIdx.all fun (x, i) =>
      S.zipIdx.all fun (y, j) =>
        i == j || decide (hammingDist x y ≥ 10)

/-- `MinDist10Code S` packages the computable predicate as the proposition
`isMinDist10Code S = true`.

Marked `@[reducible]` so that decidable instances for concrete codes are
found by typeclass resolution (`by native_decide` can check concrete
codes directly). -/
@[reducible]
def MinDist10Code (S : List (Fin 22 → Fin 2)) : Prop := isMinDist10Code S = true

-- END OF FIXED PART

/- Your work goes below. Prove at least one of the two claims.

Rules (machine-checked):
- You may change only the numeral in each claim statement; every other
  token of the claim lines must remain exactly as written, and each claim
  body must stay between its `-- CLAIM ... BEGIN/END` markers.
- No `sorry` / `admit` outside the claim bodies (a claim whose body still
  contains one simply does not score); no `axiom` / `sorryAx`; no
  redefinition tricks (`notation`, `macro`, `syntax`, `elab`, `opaque`,
  `unsafe`, `extern`, `implemented_by`, `initialize`, `skipKernelTC`);
  and the fixed part above must stay verbatim. `native_decide` is allowed
  (the judge whitelists `Lean.ofReduceBool` and `Lean.trustCompiler`).
- Auxiliary definitions and lemmas between the fixed part and the claims
  (or after them) are free. Do not wrap the claims in a `namespace`. -/

/-- Lower-bound (construction) claim: there exists a binary code of length
22 and minimum distance 10 on at least `k` words, certifying
`A(22,10) ≥ k`. `k = 64` ties the published record (Östergård 2005);
`k = 65` is a literature-level new result. Pick your `k`. -/
theorem submission_lower :
    ∃ S : List (Fin 22 → Fin 2), MinDist10Code S ∧ 2 ≤ S.length :=
-- CLAIM submission_lower BEGIN
by
  sorry
-- CLAIM submission_lower END

/-- Upper-bound claim: every binary code of length 22 and minimum distance
10 has at most `m` words, certifying `A(22,10) ≤ m`. `m = 84` matches the
published upper bound (Gijswijt–Mittelmann–Schrijver 2012); `m = 83` is a
literature-level new result. There is currently no mass-production route
for this direction — the published bound comes from a semidefinite-programming
computation, not from a verifiable certificate scheme. Pick your `m`. -/
theorem submission_upper :
    ∀ S : List (Fin 22 → Fin 2), MinDist10Code S → S.length ≤ 460 :=
-- CLAIM submission_upper BEGIN
by
  sorry
-- CLAIM submission_upper END
