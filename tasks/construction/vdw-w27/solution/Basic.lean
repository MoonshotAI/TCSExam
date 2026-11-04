set_option maxRecDepth 100000
set_option maxHeartbeats 0

/-!
# W(2,7): 2-colorings of {1..N} with no monochromatic 7-term AP

Fixed definition layer for the task `vdw-w27-lean-open`. Everything from the
top of this file down to the line `-- END OF FIXED PART` is part of the
problem statement. The judge checks it verbatim; do not edit, move, or
delete it. Your work (auxiliary definitions, lemmas, the coloring table,
and the proof of the claim) goes below the mark.
-/

namespace W27

/-- `hasMonoAP c a d` is the computable predicate "the seven values
`c a, c (a+d), ..., c (a+6d)` are all equal" — a monochromatic 7-term
arithmetic progression starting at `a` with step `d > 0`.

It is deliberately phrased on the total function `c : Nat → Fin 2` so that
concrete colorings can be checked by kernel/native computation without any
fin-index proof obligations: the `d != 0` guard makes `d = 0` trivially
not a violation, and `i * d` is plain `Nat` arithmetic. -/
def hasMonoAP (c : Nat → Fin 2) (a d : Nat) : Bool :=
  d != 0 && ((List.range 7).all fun i => c (a + i * d) == c a)

/-- `isAPFree c N` is the computable predicate "the integers `1 .. N` (read
off the total function `c`, whose values outside `0 .. N-1` are ignored)
carry **no** monochromatic 7-term arithmetic progression". It scans every
start `a < N` and step `d < N`, skipping the cases that fall outside the
range (`a + 6 * d >= N`).

A computable `isAPFree c N = true` (here packaged as the proposition
`APFree c N`) is a machine-checkable certificate for `W(2,7) > N`, i.e.
`W(2,7) >= N + 1`.

Marked `@[reducible]` so that decidable instances for concrete colorings
are found by typeclass resolution (e.g. `by native_decide` can check
colorings directly). -/
def isAPFree (c : Nat → Fin 2) (N : Nat) : Bool :=
  (List.range N).all fun a =>
    (List.range N).all fun d =>
      (a + 6 * d >= N) || !(hasMonoAP c a d)

@[reducible]
def APFree (c : Nat → Fin 2) (N : Nat) : Prop := isAPFree c N = true

-- END OF FIXED PART

/- Your work goes below. Prove the claim.

Rules (machine-checked):
- You may change only the numeral `N` in the claim statement; every other
  token of the claim lines must remain exactly as written, and the claim
  body must stay between its `-- CLAIM submission BEGIN/END` markers.
- No `sorry` / `admit` outside the claim body (a claim whose body still
  contains one simply does not score), no `axiom` / `sorryAx`, and the
  fixed part above must stay verbatim. `native_decide` is allowed (the
  judge whitelists `Lean.ofReduceBool` and `Lean.trustCompiler`).
- Auxiliary definitions and lemmas between the fixed part and the claim
  (or after it) are free. Do not close `namespace W27`.
- Representation hint: an `Array (Fin 2)` table gives O(1) lookups; a long
  `List` costs one traversal per lookup and will not scale to the record
  region (N ≈ 3700 has ~1.1 million arithmetic progressions to scan). -/

/-- The baseline coloring from the solver edition `vdw-w27`
(min-conflicts local search, seed 7; valid 2-coloring of 1..400). -/
def sanity400Table : Array (Fin 2) := #[1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1, 1, 0, 1, 1, 1, 1, 0, 0, 1, 0, 1, 1, 1, 1, 0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0]

def sanity400 : Nat → Fin 2 := fun i => sanity400Table.getD i 0

theorem submission : ∃ c : Nat → Fin 2, APFree c 400 := by
-- CLAIM submission BEGIN
  exact ⟨sanity400, by native_decide⟩
-- CLAIM submission END

end W27
