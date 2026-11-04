import Mathlib

/-!
# Binary error-correcting codes of length 24 and minimum distance 10 — fixed definition layer

A **binary error-correcting code** of length 24 and minimum Hamming
distance 10 is a set `S` of 24-bit words such that every two distinct
codewords differ in at least 10 coordinates. The largest possible size is
`A(24,10)`, known only to lie in `136 ≤ A(24,10) ≤ 268` (see
`instruction.md` for references).

Words are functions `Fin 24 → Fin 2`; `hammingDist x y` (mathlib) counts
the coordinates on which `x` and `y` differ. `MinDist10 S` below says the
code `S` has minimum distance at least 10.

Everything from the top of this file down to the line
`-- END OF FIXED PART` is part of the problem statement. The judge checks
it verbatim; do not edit, move, or delete it. Your work (auxiliary
definitions, lemmas, the codeword table, and the proofs of the claims)
goes below the mark.
-/

/-- `MinDist10 S` says that `S ⊆ {0,1}^24` is a **binary code of length 24
and minimum distance 10**: any two distinct codewords `x y ∈ S` differ in
at least 10 coordinates (`10 ≤ hammingDist x y`).

A proof of `MinDist10 S` together with `m ≤ S.card` certifies
`A(24,10) ≥ m`; a proof that every `S` with `MinDist10 S` has
`S.card ≤ k` certifies `A(24,10) ≤ k`.

Marked `@[reducible]` so that decidable instances for concrete codes are
found by typeclass resolution (`by native_decide` can check concrete
codes directly). -/
@[reducible]
def MinDist10 (S : Finset (Fin 24 → Fin 2)) : Prop :=
  ∀ x ∈ S, ∀ y ∈ S, x ≠ y → 10 ≤ hammingDist x y

-- END OF FIXED PART

/- Your work goes below. Prove at least one of the two claims.

Rules (machine-checked):
- You may change only the numeral in each claim statement; every other
  token of the claim lines must remain exactly as written, and each claim
  body must stay between its `-- CLAIM ... BEGIN/END` markers.
- No `sorry` / `admit` outside the claim bodies (a claim whose body still
  contains one simply does not score), no `axiom` / `sorryAx`, and no
  redefinition tricks: `notation`, `macro`, `syntax`, `elab`, `opaque`,
  `unsafe`, `extern`, `implemented_by`, `initialize` and the option
  `skipKernelTC` are forbidden everywhere in the file. The fixed part
  above must stay verbatim, and the claims must stay at the top level of
  the file (not inside a `namespace`).
- `native_decide` is allowed: the judge's axiom whitelist is `propext`,
  `Classical.choice`, `Quot.sound`, `Lean.ofReduceBool` and
  `Lean.trustCompiler`.
- Auxiliary definitions and lemmas between the fixed part and the claims
  (or after them) are free. -/

/-- Construction claim: there exists a binary code of length 24 and
minimum distance 10 on at least `m` words, certifying `A(24,10) ≥ m`.
`m = 136` ties the published record construction (Laaksonen–Östergård
2016); `m ≥ 137` is a literature-level new result. Pick your `m`. -/
theorem submission_construction :
    ∃ S : Finset (Fin 24 → Fin 2), MinDist10 S ∧ 2 ≤ S.card :=
-- CLAIM submission_construction BEGIN
by
  sorry
-- CLAIM submission_construction END

/-- Upper-bound claim: every binary code of length 24 and minimum
distance 10 has at most `k` words, certifying `A(24,10) ≤ k`. `k = 268`
reproduces the published upper bound (Gijswijt–Mittelmann–Schrijver 2012,
semidefinite programming); `k ≤ 267` is a literature-level new result.
There is currently no mass-production route for this direction — the
published bound is a semidefinite-programming computation, not a
verifiable certificate scheme. The placeholder `1295` is the trivial
sphere-packing (Hamming) bound. Pick your `k`. -/
theorem submission_upper :
    ∀ S : Finset (Fin 24 → Fin 2), MinDist10 S → S.card ≤ 1295 :=
-- CLAIM submission_upper BEGIN
by
  sorry
-- CLAIM submission_upper END
