/-
Self-contained statement layer for a theorem in discrepancy theory:
every {0,±1} matrix with at most k non-zero entries per column and
k = Ω(log² n) has a ±1 coloring with ‖Ax‖∞ = O(√k).

The fixed part (everything above the end-of-fixed-part marker line) is the
definition layer the main theorem's statement needs. Fidelity notes live
in `tests/reference/`.
-/

import Mathlib

namespace SparseDiscrepancy

/-! ## Colorings and discrepancy -/

/-- A (fractional) coloring (`x_t ∈ [−1, 1]^n`). -/
abbrev Coloring (n : ℕ) := Fin n → ℝ

/-- A ±1 coloring (`x : U → {−1, 1}`). -/
def IsSign {n : ℕ} (x : Coloring n) : Prop := ∀ j, x j = 1 ∨ x j = -1

/-- `discLe A b` is `disc(A) ≤ b`: some ±1 coloring achieves `‖Ax‖∞ ≤ b`
(`disc(A) := min_{x ∈ {−1,1}^n} ‖Ax‖∞`). -/
def discLe {m n : ℕ} (A : Matrix (Fin m) (Fin n) ℝ) (b : ℝ) : Prop :=
  ∃ x : Coloring n, IsSign x ∧ ∀ i, |∑ j, A i j * x j| ≤ b

open Classical in
/-- Column sparsity at most `k` ("each column has at most `k`
non-zeros"). -/
def ColSparse {m n : ℕ} (A : Matrix (Fin m) (Fin n) ℝ) (k : ℕ) : Prop :=
  ∀ j, ((Finset.univ.filter fun i => A i j ≠ 0).card : ℕ) ≤ k

/-- Entries in `{0, ±1}` (`A ∈ {0, ±1}^{m×n}`). -/
def EntriesPM {m n : ℕ} (A : Matrix (Fin m) (Fin n) ℝ) : Prop :=
  ∀ i j, A i j = 0 ∨ A i j = 1 ∨ A i j = -1

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- but the fixed part above and the main-theorem statement must not be
-- modified.

/-- The main theorem: there are constants
`c, C > 0` such that every `{0, ±1}` matrix with at most `k` non-zero
entries per column and `k ≥ c (log n)²` has a ±1 coloring with
`‖Ax‖∞ ≤ C √k` — the conjectured `O(√k)` bound holds for `k = Ω(log² n)`. -/
theorem sparse_column_discrepancy_large_k :
    ∃ c C : ℝ, 0 < c ∧ 0 < C ∧
      ∀ (m n k : ℕ) (A : Matrix (Fin m) (Fin n) ℝ),
        2 ≤ n →
        EntriesPM A →
        ColSparse A k →
        c * (Real.log (n : ℝ)) ^ 2 ≤ (k : ℝ) →
        discLe A (C * Real.sqrt (k : ℝ)) := by
  -- CHECKPOINT sparse_column_discrepancy_large_k BEGIN
  sorry
  -- CHECKPOINT sparse_column_discrepancy_large_k END

end SparseDiscrepancy
