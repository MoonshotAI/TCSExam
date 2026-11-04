/-
Self-contained statement layer for a theorem in coding theory: mutual
correlated agreement for subspace-design codes.

The fixed part (everything above the end-of-fixed-part marker line) is
the definition layer the main theorem's statement needs: relative Hamming
distance, parametric curves of words, mutual correlated agreement (MCA),
the subspace-design property, and two packaged external power sources
(a pruning guarantee and a list-size bound). Fidelity notes live in
`tests/reference/`.
-/

import Mathlib

namespace ProximityGaps

variable {F : Type*} [Field F] [Fintype F] [DecidableEq F]
variable {V : Type*} [AddCommGroup V] [Module F V] [Fintype V] [DecidableEq V]
  [FiniteDimensional F V]
variable {n : ℕ}

/-! ## Words, distance, and curves of words -/

/-- Relative (fractional) Hamming distance between two words, as a
rational number. -/
def relDist (x y : Fin n → V) : ℚ :=
  ((Finset.univ.filter fun i => x i ≠ y i).card : ℚ) / n

/-- The value at `α` of the degree-`ℓ` parametric curve with coefficient
words `u 0, …, u ℓ`. -/
def curveEval {ℓ : ℕ} (u : Fin (ℓ + 1) → Fin n → V) (α : F) : Fin n → V :=
  ∑ j : Fin (ℓ + 1), (α ^ (j : ℕ)) • u j

/-! ## Mutual correlated agreement -/

/-- Mutual correlated agreement for degree-`ℓ` curves: if the curve of
words is within distance `δ'` of the attached
codewords `f(α)` with probability above `err`, then there is a curve of
codewords whose coefficient words agree with the `uⱼ` on all but
`δ'n/(1−γ)` coordinates, passing through `f(β)` for some `β`. -/
def MCA (C : Submodule F (Fin n → V)) (ℓ : ℕ) (δ err γ : ℚ) : Prop :=
  ∀ (u : Fin (ℓ + 1) → Fin n → V) (δ' : ℚ), δ' ≤ δ → ∀ (f : F → C),
    err < ((Finset.univ.filter fun α : F =>
        relDist (curveEval u α) (f α : Fin n → V) ≤ δ').card : ℚ) /
      (Fintype.card F : ℚ) →
    ∃ c : Fin (ℓ + 1) → C,
      ((Finset.univ.filter fun i =>
          ∃ j : Fin (ℓ + 1), u j i ≠ (c j : Fin n → V) i).card : ℚ)
        ≤ δ' * (n : ℚ) / (1 - γ) ∧
      ∃ β : F, (f β : Fin n → V) = curveEval (fun j => (c j : Fin n → V)) β

/-! ## Subspace-design codes -/

/-- The subspace of words vanishing at coordinate `i`. -/
def coordKer (i : Fin n) : Submodule F (Fin n → V) := (LinearMap.proj i).ker

/-- The `τ`-subspace-design property: for every `r` and every subspace
`A` of the code of dimension at most `r`, the pinned
subspaces `Aᵢ = {a ∈ A | aᵢ = 0}` have average dimension at most
`(dim A)·τ(r)`. -/
def IsSubspaceDesign (C : Submodule F (Fin n → V)) (τ : ℕ → ℚ) : Prop :=
  ∀ (r : ℕ) (A : Submodule F (Fin n → V)),
    A ≤ C → Module.finrank F ↥A ≤ r →
      (∑ i : Fin n, (Module.finrank F ↥(A ⊓ coordKer i) : ℚ)) / (n : ℚ)
        ≤ (Module.finrank F ↥A : ℚ) * τ r

/-! ## Packaged external power sources -/

/-- The pruning guarantee, packaged as a hypothesis-level definition:
for every subspace `H` of the code of
dimension at most `r` and every finite family of pairs `(y α, c α)` with
`c α ∈ H` within distance `1 − τ(r) − ε` of `y α`, there is a coordinate
set `S` that pins `H` to zero while at least an `ε/(r + ε)` fraction of
the pairs agree on all of `S`. -/
def PruningGuarantee (C : Submodule F (Fin n → V)) (τ : ℕ → ℚ) (r : ℕ)
    (ε : ℚ) : Prop :=
  ∀ {ι : Type} [DecidableEq ι] (H : Submodule F (Fin n → V)),
    H ≤ C → Module.finrank F H ≤ r →
    ∀ (A : Finset ι) (y c : ι → Fin n → V),
      (∀ α ∈ A, c α ∈ H) →
      (∀ α ∈ A, relDist (y α) (c α) ≤ 1 - τ r - ε) →
      ∃ S : Finset (Fin n),
        (∀ h ∈ H, (∀ i ∈ S, h i = 0) → h = 0) ∧
        ((A.card : ℚ) * ε / ((r : ℚ) + ε)) ≤
          ((A.filter fun α => ∀ i ∈ S, y α i = c α i).card : ℚ)

open Classical in
/-- The list-size bound, packaged as a hypothesis-level definition: for
every `k ≥ 1`, every open ball of radius
`1 − τ(k) − 1/k` contains at most `(1 − τ(k))·k` codewords. -/
noncomputable def ListSizeBound (C : Submodule F (Fin n → V)) (τ : ℕ → ℚ) : Prop :=
  ∀ (k : ℕ), 0 < k → ∀ y : Fin n → V,
    ((Finset.univ.filter fun c : Fin n → V =>
        c ∈ C ∧ relDist y c < 1 - τ k - (k : ℚ)⁻¹).card : ℚ) ≤ (1 - τ k) * k

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- but the fixed part above and the main-theorem statement must not be
-- modified.

/-- The main theorem: every `τ`-subspace-design code has mutual
correlated agreement with proximity `1 − τ((ℓ+1)t) − 3/(2t)`,
error `t·ℓ·(ℓ+1)·(m·(1−τ((ℓ+1)t)) + 2t²)/|F|`, and slack `1/m`, for
`2 ≤ m ≤ 4t` and under the stated field-size and boundary hypotheses
(deviations from the printed statement documented in
`tests/reference/concept-ledger.md`). -/
theorem mca_of_subspace_design
    (C : Submodule F (Fin n → V)) {τ : ℕ → ℚ} (hτ : IsSubspaceDesign C τ)
    (hlb : ListSizeBound C τ)
    (t m ℓ : ℕ) (ht : 1 ≤ t) (hm : 2 ≤ m) (hmt : m ≤ 4 * t) (hℓ : 1 ≤ ℓ)
    (hτr : 0 ≤ τ ((ℓ + 1) * t)) (hτ1 : τ ((ℓ + 1) * t) ≤ 1)
    (hp : PruningGuarantee C τ ((ℓ + 1) * t) (3 / (2 * (t : ℚ))))
    (hq : ((((ℓ + 1) * t : ℕ) : ℚ) * (1 - τ ((ℓ + 1) * t)) + 1) ^ 2 * (ℓ : ℚ)
      < (Fintype.card F : ℚ)) :
    MCA C ℓ (1 - τ ((ℓ + 1) * t) - 3 / (2 * (t : ℚ)))
      (((t : ℚ) * (ℓ : ℚ) * ((ℓ : ℚ) + 1)) *
        ((m : ℚ) * (1 - τ ((ℓ + 1) * t)) + 2 * (t : ℚ) ^ 2) / (Fintype.card F : ℚ))
      (1 / (m : ℚ)) := by
  -- CHECKPOINT mca_of_subspace_design BEGIN
  sorry
  -- CHECKPOINT mca_of_subspace_design END

end ProximityGaps
