/-
Self-contained statement layer for a theorem about error-correcting codes:
an exponential blocklength lower bound for linear 3-query locally
correctable codes, in its binary normal-form version.

The fixed part (everything above the end-of-fixed-part marker line) is the
definition layer the main theorem's statement needs: linear 3-LCCs in normal
form and the linear 2-LDC lower bound, which is packaged as a hypothesis.
Fidelity notes live in `tests/reference/`.
-/

import Mathlib

namespace LCCExpLB

open Finset

/-! ## Linear 3-LCCs in normal form -/

/-- A linear code `F₂ᵏ → F₂ⁿ` in normal form: systematic on the first `k`
coordinates, and for each coordinate `u` a 3-uniform hypergraph matching of
`d0` hyperedges giving the correction relations `x_u = ∑_{v ∈ C} x_v`
(the F₂ form of `x_C · x_u = 1`; over F₂ all coefficients are 1). -/
structure NormalFormCode (n k d0 : ℕ) (hkn : k ≤ n) where
  /-- The encoding map. -/
  enc : (Fin k → ZMod 2) →ₗ[ZMod 2] (Fin n → ZMod 2)
  /-- The code is systematic: coordinate `i ∈ [k]` of `ℒ(b)` is `b i`. -/
  systematic : ∀ (b : Fin k → ZMod 2) (i : Fin k), enc b (Fin.castLE hkn i) = b i
  /-- The query matchings. -/
  H : Fin n → Finset (Finset (Fin n))
  /-- Each matching has exactly `d0` hyperedges (the source text's `δn`). -/
  card_H : ∀ u, (H u).card = d0
  /-- Each matching is 3-uniform. -/
  uniform3 : ∀ u, ∀ C ∈ H u, C.card = 3
  /-- Each `H u` is a matching: hyperedges sharing a vertex coincide. -/
  matching : ∀ u, ∀ C₁ ∈ H u, ∀ C₂ ∈ H u, ∀ v, v ∈ C₁ → v ∈ C₂ → C₁ = C₂
  /-- The correction relations. -/
  corrects : ∀ (b : Fin k → ZMod 2) (u : Fin n), ∀ C ∈ H u,
    enc b u = ∑ v ∈ C, enc b v

/-! ## The linear 2-LDC lower bound, packaged as a hypothesis -/

/-- The linear 2-LDC lower bound in the F₂ form:
matchings `G_i` on `n' ≥ 1` vertices with `x_u + x_v = b_i` on every edge and
average size at least `δ' · n'` force `δ' k' ≤ 2 log₂ n'`. -/
def twoLDCLowerBoundProp : Prop :=
  ∀ (k' n' : ℕ) (ℒ' : (Fin k' → ZMod 2) →ₗ[ZMod 2] (Fin n' → ZMod 2))
    (G : Fin k' → Finset (Fin n' × Fin n')) (δ' : ℝ),
    (∀ i : Fin k', ∀ e ∈ G i, e.1 ≠ e.2) →
    (∀ i : Fin k', ∀ e₁ ∈ G i, ∀ e₂ ∈ G i,
      (e₁.1 = e₂.1 ∨ e₁.1 = e₂.2 ∨ e₁.2 = e₂.1 ∨ e₁.2 = e₂.2) → e₁ = e₂) →
    (∀ b : Fin k' → ZMod 2, ∀ i : Fin k', ∀ e ∈ G i, ℒ' b e.1 + ℒ' b e.2 = b i) →
    0 < k' →
    0 < n' →
    δ' * n' ≤ (1 / (k' : ℝ)) * ∑ i : Fin k', ((G i).card : ℝ) →
    δ' * k' ≤ 2 * Real.logb 2 n'

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- but the fixed part above and the main-theorem statement must not be modified.

/-- The main theorem, in its binary normal-form version: the blocklength of a
linear 3-query locally correctable code grows exponentially with the message
length — there is an absolute constant `C > 0` such that every normal-form
code satisfies `k ≤ C · (log₂ n)⁸ / δ²`, i.e. `n ≥ 2^{(δ² k / C)^{1/8}}`.
The linear 2-LDC lower bound is taken as a hypothesis. -/
theorem linear_3lcc_exp_lower_bound (h2ldc : twoLDCLowerBoundProp) :
    ∃ C : ℝ, 0 < C ∧ ∀ (n k d0 : ℕ) (δ : ℝ) (hkn : k ≤ n)
      (_ : NormalFormCode n k d0 hkn),
      2 ≤ n → 0 < δ → (d0 : ℝ) ≥ δ * n →
      (k : ℝ) ≤ C * (Real.logb 2 (n : ℝ)) ^ 8 / δ ^ 2 := by
  -- CHECKPOINT linear_3lcc_exp_lower_bound BEGIN
  sorry
  -- CHECKPOINT linear_3lcc_exp_lower_bound END


end LCCExpLB
