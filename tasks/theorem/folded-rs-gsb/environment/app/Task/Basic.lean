/-
Self-contained statement layer for a theorem in coding theory: explicit
folded Reed–Solomon codes achieve list-decoding capacity with optimal
list size.

The fixed part (everything above the end-of-fixed-part marker line) is
the definition layer the main theorem's statement needs: relative
Hamming distance, list-decodability, generators of `Fˣ`, appropriate
evaluation points, folded evaluation blocks, and the folded
Reed–Solomon code as a submodule of words. Fidelity notes live in
`tests/reference/`.
-/

import Mathlib

namespace FoldedRSGSB

variable {F : Type*} [Field F] [Fintype F] [DecidableEq F]

/-! ## Words, distance, and list-decodability -/

/-- Relative (fractional) Hamming distance between two words over the
block alphabet `Fˢ`, as a rational number. -/
def relDist {n s : ℕ} (x y : Fin n → Fin s → F) : ℚ :=
  ((Finset.univ.filter fun i => x i ≠ y i).card : ℚ) / n

open Classical in
/-- List-decodability with radius `ρ` and list size `L`: every radius-`ρ`
Hamming ball contains at most `L` codewords. -/
noncomputable def ListDecodable {n s : ℕ} (C : Submodule F (Fin n → Fin s → F))
    (ρ : ℚ) (L : ℚ) : Prop :=
  ∀ y : Fin n → Fin s → F,
    ((Finset.univ.filter fun c : Fin n → Fin s → F =>
        c ∈ C ∧ relDist y c ≤ ρ).card : ℚ) ≤ L

/-! ## The field, its generator, and appropriate evaluation points -/

/-- `γ` generates the multiplicative group `Fˣ`. -/
def IsGenerator (γ : F) : Prop := ∀ x : F, x ≠ 0 → ∃ i : ℕ, γ ^ i = x

/-- Appropriate evaluation points: the `s·n` shifted points
`γ^j · αᵢ` (`j ∈ {0, …, s−1}`, `i ∈ {1, …, n}`) are pairwise distinct. -/
def Appropriate (γ : F) (s : ℕ) {n : ℕ} (α : Fin n → F) : Prop :=
  Function.Injective fun ij : Fin s × Fin n => γ ^ (ij.1 : ℕ) * α ij.2

/-! ## Folded Reed–Solomon codes -/

/-- The folded evaluation block of `f` at `a`: the `s` values
`f(a), f(γ·a), …, f(γ^{s−1}·a)`. -/
def foldEval (γ : F) (s : ℕ) (f : Polynomial F) (a : F) : Fin s → F :=
  fun j => f.eval (γ ^ (j : ℕ) * a)

/-- The folded Reed–Solomon encoding linear map: a message polynomial is
sent to the word of its folded evaluation blocks at `α₁, …, αₙ`. -/
def frsEncodeLM (γ : F) (s : ℕ) {n : ℕ} (α : Fin n → F) :
    Polynomial F →ₗ[F] (Fin n → Fin s → F) where
  toFun f := fun i => foldEval γ s f (α i)
  map_add' f g := by
    funext i j
    simp [foldEval, Polynomial.eval_add, Pi.add_apply]
  map_smul' c f := by
    funext i j
    simp [foldEval, Polynomial.eval_smul, Pi.smul_apply, smul_eq_mul]

/-- The `(s, γ)`-folded Reed–Solomon code of dimension `k` at `α`: the
image of the polynomials of degree `< k` under the encoding map. -/
noncomputable def frsCode (γ : F) (s : ℕ) {n : ℕ} (α : Fin n → F) (k : ℕ) :
    Submodule F (Fin n → Fin s → F) :=
  (Polynomial.degreeLT F k).map (frsEncodeLM γ s α)

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- but the fixed part above and the main-theorem statement must not be
-- modified.

/-- The main theorem: for `ε > 0`, `1 ≤ k < N`, `s ∣ N`, `n = N / s`,
`q > n`, `R = k/N`, and any `L > (1−R−ε)/ε` and
`s > L·(L−1)·R/(εL−(1−R−ε)) + L − 1`, the folded RS code
`FRS^{(s,γ)}_{n,k}(α)` at appropriate evaluation points is
`(1 − R − ε, L)` list-decodable (deviations from the printed statement
documented in `tests/reference/concept-ledger.md`). -/
theorem frs_list_decodable_capacity
    (γ : F) (hγ : IsGenerator γ) {N k s L n : ℕ} (ε : ℚ) (hε : 0 < ε)
    (hk : 1 ≤ k) (hkN : k < N) (hsN : s ∣ N) (hn : n = N / s)
    (hqn : n < Fintype.card F)
    (hL : (1 - (k : ℚ) / (N : ℚ) - ε) / ε < (L : ℚ))
    (hs : (L : ℚ) * ((L : ℚ) - 1) * ((k : ℚ) / (N : ℚ)) /
          (ε * (L : ℚ) - (1 - (k : ℚ) / (N : ℚ) - ε)) + ((L : ℚ) - 1) <
        (s : ℚ))
    {α : Fin n → F} (hα : Appropriate γ s α) :
    ListDecodable (frsCode γ s α k) (1 - (k : ℚ) / (N : ℚ) - ε) (L : ℚ) := by
  -- CHECKPOINT frs_list_decodable_capacity BEGIN
  sorry
  -- CHECKPOINT frs_list_decodable_capacity END

end FoldedRSGSB
