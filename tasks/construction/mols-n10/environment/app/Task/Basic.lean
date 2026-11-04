set_option maxRecDepth 100000
set_option maxHeartbeats 0
set_option synthInstance.maxSize 512

/-!
# Mutually orthogonal Latin squares: certified lower bounds on N(n)

Fixed definition layer for the task `mols-n10-lean-open`. Everything from
the top of this file down to the line `-- END OF FIXED PART` is part of the
problem statement. The judge checks it verbatim; do not edit, move, or
delete it. Your work (auxiliary definitions, lemmas, the squares, and the
proof of the claim) goes below the mark.

A **Latin square** of order `n` is an `n × n` grid over `n` symbols with
every row and every column containing each symbol exactly once. Two Latin
squares are **orthogonal** if superimposing them produces all `n²` ordered
pairs exactly once. `N(n)` denotes the maximum number of pairwise
orthogonal Latin squares (MOLS) of order `n`; `N(n) ≤ n - 1` always
(pigeonhole). The published records for the ten grid orders of this task
(Handbook of Combinatorial Designs, 2nd ed., chapter III.3, as updated by
Todorov 2012 and Abel 2013):

    N(10) ∈ [2, 6]    N(12) ∈ [5, 11]   N(14) ∈ [4, 12]   N(15) ∈ [4, 14]
    N(18) ∈ [5, 17]   N(20) ∈ [4, 19]   N(21) ∈ [5, 19]   N(22) ∈ [3, 20]
    N(24) ∈ [7, 23]   N(26) ∈ [4, 25]

A family of `k` pairwise orthogonal Latin squares of order `n`, packaged
as the proposition `MolsSet n Ss` together with `Ss.length ≥ k`, is a
machine-checkable certificate for `N(n) ≥ k`. Reaching `k` equal to the
published record at a grid order ties the record; exceeding it is a
literature-level new result — `k = 3` at `n = 10` would settle a problem
open since Parker 1959 (66 years).
-/

namespace MOLS

/-- `isLatin n L` is the computable predicate "the `n × n` table `L` over
`Fin n` is a Latin square": every row and every column contains each symbol
exactly once.  `O(n³)` comparisons.  This matches the solver sibling task
`mols-n10`'s checker clause for the Latin property exactly. -/
def isLatin (n : Nat) (L : Fin n → Fin n → Fin n) : Bool :=
  (List.finRange n).all fun r =>
    (List.finRange n).all fun x =>
      ((List.finRange n).filter fun c => L r c == x).length == 1
  &&
  (List.finRange n).all fun c =>
    (List.finRange n).all fun x =>
      ((List.finRange n).filter fun r => L r c == x).length == 1

/-- `areOrthogonal n L M` is the computable predicate "the Latin squares
`L` and `M` are orthogonal": every ordered pair `(a, b)` of symbols occurs
at some cell — with `n²` cells and `n²` pairs, "every pair occurs" is the
same as "no pair repeats".  Worst case `O(n⁴)` comparisons.  This matches
the solver checker's orthogonality clause exactly. -/
def areOrthogonal (n : Nat) (L M : Fin n → Fin n → Fin n) : Bool :=
  (List.finRange n).all fun a =>
    (List.finRange n).all fun b =>
      (List.finRange n).any fun r =>
        (List.finRange n).any fun c => L r c == a && M r c == b

/-- `List.Pairwise` as a `Bool` test. -/
def pairwiseAll? (R : α → α → Bool) : List α → Bool
  | [] => true
  | x :: xs => xs.all (R x) && pairwiseAll? R xs

/-- `AllMOLS n Ss` is the computable predicate "the list `Ss` of `n × n`
tables is a family of pairwise orthogonal Latin squares of order `n`":
every table is Latin and every two are orthogonal.

Boundary behavior, aligned with the solver sibling task `mols-n10`'s
checker:

- **duplicate squares** need no clause of their own: two copies of the same
  square `L` are never orthogonal for `n ≥ 2` (the pair `(0, 1)` never
  occurs as `(L r c, L r c)`), so `AllMOLS` already rejects them, exactly
  as the checker rejects them via the orthogonality check;
- the **empty list** satisfies the predicate vacuously, exactly as the
  checker accepts no claim with `k = 0`: the claims below require
  `Ss.length ≥ k` with `k ≥ 1`, so an empty witness never counts;
- the checker additionally pre-rejects `k > n - 1` by pigeonhole; here a
  proof of `MolsSet n Ss ∧ Ss.length ≥ n` is mathematically impossible for
  `n ≥ 2`, so any such certificate would mean a predicate bug — the judge
  flags it for mandatory human review. -/
def AllMOLS (n : Nat) (Ss : List (Fin n → Fin n → Fin n)) : Bool :=
  Ss.all (isLatin n) && pairwiseAll? (areOrthogonal n) Ss

/-- `MolsSet n Ss` packages the computable predicate as the proposition
`AllMOLS n Ss = true`.

Marked `@[reducible]` so that decidable instances for concrete families are
found by typeclass resolution (e.g. `by native_decide` can check families
directly). -/
@[reducible] def MolsSet (n : Nat) (Ss : List (Fin n → Fin n → Fin n)) : Prop :=
  AllMOLS n Ss = true

-- END OF FIXED PART

/- Your work goes below. Prove the claim.

Rules (machine-checked):
- You may change only the two numerals `n` (the order, appearing four
  times) and `k` (the family size) in the claim statement; every other
  token of the claim lines must remain exactly as written, and the claim
  body must stay between its `-- CLAIM submission_lower BEGIN/END` markers.
- No `sorry` / `admit` outside the claim body (a claim whose body still
  contains one simply does not score), no `axiom` / `sorryAx`, and the
  fixed part above must stay verbatim. `native_decide` is allowed (the
  judge whitelists `Lean.ofReduceBool` and `Lean.trustCompiler`).
- Auxiliary definitions and lemmas between the fixed part and the claim
  (or after it) are free. Do not close `namespace MOLS`.
- Published records per order `n` (the bar to beat at each order):
  10: 2   12: 5   14: 4   15: 4   18: 5
  20: 4   21: 5   22: 3   24: 7   26: 4
  Claims at orders outside the grid (e.g. the sanity pair at `n = 3`)
  compile and are checked but do not count.  Representation hint: write squares through a small
  helper, e.g.
  `def sq (rows : List (List Nat)) : Fin n → Fin n → Fin n := fun r c =>
    ⟨(rows.getD r.val []).getD c.val 0 % n, by omega⟩`
  with the matrix as literal data, or generate the family programmatically.
-/

theorem submission_lower : ∃ Ss : List (Fin 10 → Fin 10 → Fin 10), MolsSet 10 Ss ∧ Ss.length ≥ 2 := by
-- CLAIM submission_lower BEGIN
  sorry
-- CLAIM submission_lower END

end MOLS
