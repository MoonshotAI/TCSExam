/-
Self-contained statement layer for a theorem in quantum query complexity:
a one-query lower bound for unitary synthesis — the expected
distinguishing advantage of any one-query adversary `(M, V, Π)` against a
uniformly random function family is at most `C·√(ln M / K)` for an
absolute constant `C`.

The fixed part (everything above the end-of-fixed-part marker line) is the
definition layer the main theorem's statement needs: a one-query adversary
is a triple `(M, V, Π)` with `V : ℂ^N → ℂ^M` an isometry and `Π` an
`M × M` projection; the oracle `f` acts as a diagonal sign matrix `O_f`;
`|ψ_h⟩ = (1/√N) Σ_x h(x)|x⟩` is a binary phase state; `adv` is the
distinguishing advantage (one-query form). The oracle-circuit and game
layer and the cryptographic corollaries are not formalized. Fidelity
notes live in `tests/reference/`.
-/

import Mathlib

open scoped Matrix

namespace UnitarySynthesisLB

/-! ## Phase states, the adversary model, and the distinguishing advantage -/

/-- A Boolean value as a sign in `{±1} ⊂ ℂ`. -/
def phase (b : Bool) : ℂ := if b then 1 else -1

/-- A function family `R : [K] × [N] → {±1}`, in Boolean form. -/
abbrev Fam (K N : ℕ) := Fin K → Fin N → Bool

/-- Sesquilinear inner product on `Fin M → ℂ`:
`cinner u v = ∑ i, conj (u i) * v i`. -/
noncomputable def cinner {M : ℕ} (u v : Fin M → ℂ) : ℂ := ∑ i, star (u i) * v i

/-- Uniform expectation over a finite sample space. -/
noncomputable def unifExp {α : Type*} [Fintype α] (g : α → ℝ) : ℝ :=
  (∑ a : α, g a) / (Fintype.card α : ℝ)

/-- The binary phase state of `h`:
`|ψ_h⟩ = (1/√N) Σ_x h(x)|x⟩`, as a vector of `ℂ^N`. -/
noncomputable def psi {N : ℕ} (h : Fin N → Bool) : Fin N → ℂ :=
  fun x => (↑(Real.sqrt (N : ℝ)))⁻¹ * phase (h x)

/-- The isometry weights:
`wt_{V,i} = (1/N)·⟨v_i|v_i⟩`, where `|v_i⟩` is the conjugate of the
`i`-th row of `V`. For an isometry `V` with `1 ≤ N` these are
non-negative and sum to one; rows with `wt_i = 0` are exactly the zero
rows of `V`. -/
noncomputable def wt {M N : ℕ} (V : Matrix (Fin M) (Fin N) ℂ) (i : Fin M) : ℝ :=
  (1 / (N : ℝ)) * ∑ x : Fin N, Complex.normSq (V i x)

/-- The diagonal sign matrix of `f` (the oracle action `O_f`). -/
noncomputable def oracleMat {M : ℕ} (f : Fin M → Bool) :
    Matrix (Fin M) (Fin M) ℂ :=
  Matrix.diagonal fun i => phase (f i)

/-- `Π` is an (orthogonal) projection: Hermitian and idempotent. -/
def IsProj {M : ℕ} (P : Matrix (Fin M) (Fin M) ℂ) : Prop :=
  P.IsHermitian ∧ P * P = P

/-- The acceptance probability `p_A(h | f)` of the one-query adversary,
as the real quadratic form `Re ⟨Vψ_h, O_f Π O_f Vψ_h⟩`. -/
noncomputable def pA {M N : ℕ} (V : Matrix (Fin M) (Fin N) ℂ)
    (Pj : Matrix (Fin M) (Fin M) ℂ) (f : Fin M → Bool) (h : Fin N → Bool) : ℝ :=
  Complex.re (cinner (V *ᵥ psi h) (oracleMat f *ᵥ (Pj *ᵥ (oracleMat f *ᵥ (V *ᵥ psi h)))))

/-- The distinguishing advantage of the adversary `(M, V, Π)` on the
function family `R` (one-query form):
`max_f [ E_k p_A(R_k | f) − E_h p_A(h | f) ]`. -/
noncomputable def adv {M N K : ℕ} (V : Matrix (Fin M) (Fin N) ℂ)
    (Pj : Matrix (Fin M) (Fin M) ℂ) (R : Fam K N) : ℝ :=
  (Finset.univ : Finset (Fin M → Bool)).sup' Finset.univ_nonempty fun f =>
    (1 / (K : ℝ)) * ∑ k : Fin K, pA V Pj f (R k) -
      unifExp fun h : Fin N → Bool => pA V Pj f h

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- but the fixed part above and the main-theorem statement must not be
-- modified.

/-- The main theorem: there is an absolute constant
`C > 0` such that for every one-query adversary `(M, V, Π)` with
`1 ≤ M` and `1 ≤ K`, the expected distinguishing advantage over a uniform
function family is at most `C·√(ln M / K)`. (The zero-weight-row premise
is packaged as a hypothesis.) -/
theorem advantage_expectation_bound :
    ∃ C : ℝ, 0 < C ∧ ∀ {M N K : ℕ} (_ : 1 ≤ M) (_ : 1 ≤ K)
      (V : Matrix (Fin M) (Fin N) ℂ) (_ : Vᴴ * V = 1)
      (Pj : Matrix (Fin M) (Fin M) ℂ) (_ : IsProj Pj) (_ : ∀ i, 0 < wt V i),
        unifExp (fun R : Fam K N => adv V Pj R) ≤
          C * Real.sqrt (Real.log (M : ℝ) / (K : ℝ)) := by
  -- CHECKPOINT advantage_expectation_bound BEGIN
  sorry
  -- CHECKPOINT advantage_expectation_bound END

end UnitarySynthesisLB
