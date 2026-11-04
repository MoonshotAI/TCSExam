/-
Self-contained statement layer for a theorem in additive combinatorics:
a quasipolynomial upper bound for corner-free sets.

The fixed part (everything above the end-of-fixed-part marker line) is the
definition layer the main theorem's statement needs: the corner-free
predicate on a finite abelian group. Fidelity notes live in
`tests/reference/`.
-/


import Mathlib

namespace CornersQuasipoly

/-! ## The corner-free predicate -/

/-- `A ⊆ G × G` is corner-free: there are no `x, y, d ∈ G` with `d ≠ 0` such
that `(x, y), (x + d, y), (x, y + d) ∈ A` (the hypothesis of the main theorem). -/
def CornerFree {G : Type*} [AddCommGroup G] (A : Finset (G × G)) : Prop :=
 ∀ x y d : G, d ≠ 0 → (x, y) ∈ A → (x + d, y) ∈ A → (x, y + d) ∉ A

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

/-- The main theorem: there is a constant
`c > 0` such that for every finite abelian group `G`, every corner-free
`A ⊆ G × G` (no `x, y, d` with `d ≠ 0` and `(x, y), (x + d, y), (x, y + d)`
in `A`) satisfies `|A| ≤ |G|²·exp(−c·(log|G|)^{1/600})`. -/
theorem corners_quasipoly_bound :
 ∃ c : ℝ, 0 < c ∧
 ∀ G : Type, ∀ [Fintype G] [AddCommGroup G] [DecidableEq G],
 ∀ A : Finset (G × G), CornerFree A →
 (A.card : ℝ) ≤ (Fintype.card G : ℝ) ^ 2 *
 Real.exp (-c * (Real.log (Fintype.card G)) ^ (1 / 600 : ℝ)) := by
 -- CHECKPOINT corners_quasipoly_bound BEGIN
 sorry
 -- CHECKPOINT corners_quasipoly_bound END

end CornersQuasipoly
