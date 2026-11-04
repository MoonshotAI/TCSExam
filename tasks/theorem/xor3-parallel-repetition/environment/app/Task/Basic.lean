/-
Self-contained statement layer for a theorem in game theory: exponential
decay of the parallel-repetition value of 3-player XOR games of value
`< 1` whose question distribution has no `ℤ`-embeddings, conditional on
the packaged additive-combinatorics input `FreimanAssumption`.

The fixed part (everything above the end-of-fixed-part marker line) is
the definition layer the main theorem's statement needs: finite
distributions as mass functions with supports, the `n`-fold product
distribution on triples of function tuples, the winning probability and
the value of a 3-player XOR game, embeddings into an abelian group and
the no-`ℤ`-embeddings condition, the uniform sum-zero distribution,
Freiman homomorphisms, and the packaged inverse input.
Fidelity notes live in `tests/reference/`.
-/

import Mathlib

namespace XOR3PR

/-! ## Finite distributions -/

/-- A probability distribution on a finite type, as a mass function. -/
structure Dist (α : Type*) [Fintype α] where
  pmf : α → ℝ
  nonneg : ∀ a, 0 ≤ pmf a
  sum_one : ∑ a, pmf a = 1

namespace Dist

variable {α : Type*} [Fintype α]

/-- The support of a distribution: the atoms of positive mass. -/
noncomputable def supp (μ : Dist α) : Finset α :=
  letI : ∀ Q : Prop, Decidable Q := Classical.propDecidable
  Finset.univ.filter fun a => μ.pmf a ≠ 0

/-- The sum of a coordinatewise product over the function type
`Fin n → β` factors: `∑ u, ∏ i, μ.pmf (u i) = ∏ i, ∑ b, μ.pmf b = 1`. -/
lemma prod_pi_sum {β : Type*} [Fintype β] (μ : Dist β) (n : ℕ) :
    ∑ u : Fin n → β, ∏ i : Fin n, μ.pmf (u i) = 1 := by
  have key : (∑ u : Fin n → β, ∏ i : Fin n, μ.pmf (u i)) =
      ∏ _i : Fin n, ∑ b : β, μ.pmf b := by
    rw [Finset.prod_univ_sum, Fintype.piFinset_univ]
  rw [key, Finset.prod_congr rfl (fun i _ => μ.sum_one), Finset.prod_const_one]

end Dist

/-- The `n`-fold product distribution of a distribution on triples, seen
on triples of function tuples (the transpose of `(X × Y × Z)^n`). -/
noncomputable def Dist.pi3 {X Y Z : Type*} [Fintype X] [Fintype Y] [Fintype Z]
    [DecidableEq X] (μ : Dist (X × Y × Z)) (n : ℕ) :
    Dist ((Fin n → X) × (Fin n → Y) × (Fin n → Z)) where
  pmf ω := ∏ i : Fin n, μ.pmf (ω.1 i, ω.2.1 i, ω.2.2 i)
  nonneg ω := Finset.prod_nonneg fun i _ => μ.nonneg (ω.1 i, ω.2.1 i, ω.2.2 i)
  sum_one := by
    let e : (Fin n → X) × (Fin n → Y) × (Fin n → Z) ≃ (Fin n → X × Y × Z) :=
      { toFun := fun ω i => (ω.1 i, ω.2.1 i, ω.2.2 i)
        invFun := fun u => (fun i => (u i).1, fun i => (u i).2.1, fun i => (u i).2.2)
        left_inv := fun ω => rfl
        right_inv := fun u => rfl }
    have h : (∑ ω : (Fin n → X) × (Fin n → Y) × (Fin n → Z),
          ∏ i : Fin n, μ.pmf (ω.1 i, ω.2.1 i, ω.2.2 i))
        = ∑ u : Fin n → X × Y × Z, ∏ i : Fin n, μ.pmf (u i) :=
      Equiv.sum_comp e (fun u => ∏ i : Fin n, μ.pmf (u i))
    rw [h, Dist.prod_pi_sum]

/-! ## 3-player XOR games -/

variable {X Y Z : Type*} [Fintype X] [Fintype Y] [Fintype Z]
  [DecidableEq X] [DecidableEq Y] [DecidableEq Z]

/-- The winning probability of strategies `f, g, h` in the 3-player XOR
game with question distribution `μ` and target `t`: the verifier samples
`(x, y, z) ~ μ` and accepts iff `f(x) + g(y) + h(z) = t(x, y, z)`. -/
noncomputable def winProb {Ans : Type*} [DecidableEq Ans] [AddCommGroup Ans]
    (μ : Dist (X × Y × Z)) (t : X → Y → Z → Ans)
    (f : X → Ans) (g : Y → Ans) (h : Z → Ans) : ℝ :=
  ∑ ω : X × Y × Z, μ.pmf ω *
    (if f ω.1 + g ω.2.1 + h ω.2.2 = t ω.1 ω.2.1 ω.2.2 then (1 : ℝ) else 0)

/-- The value of the game: the maximum winning probability over all
strategies. -/
noncomputable def gameVal {Ans : Type*} [Fintype Ans] [DecidableEq Ans]
    [AddCommGroup Ans] (μ : Dist (X × Y × Z)) (t : X → Y → Z → Ans) : ℝ :=
  letI : DecidableEq ℝ := Classical.decEq ℝ
  letI : Nonempty Ans := ⟨0⟩
  (Finset.univ.image fun σ : (X → Ans) × (Y → Ans) × (Z → Ans) =>
    winProb μ t σ.1 σ.2.1 σ.2.2).max' (Finset.Nonempty.image Finset.univ_nonempty _)

/-- The target function of the `n`-fold parallel repetition: the verifier
samples `n` independent challenges `(x, y, z) ~ μ^⊗n` and the players win
iff they win every coordinate. -/
def repT {Ans : Type*} (t : X → Y → Z → Ans) (n : ℕ) :
    (Fin n → X) → (Fin n → Y) → (Fin n → Z) → (Fin n → Ans) :=
  fun x y z i => t (x i) (y i) (z i)

/-! ## Embeddings and the no-`ℤ`-embeddings condition -/

/-- An embedding of the question distribution into an abelian group:
three maps whose sum vanishes on the support of `μ`. -/
def IsEmbedding {A : Type*} [AddCommGroup A] (μ : Dist (X × Y × Z))
    (σ : X → A) (γ : Y → A) (ϕ : Z → A) : Prop :=
  ∀ x y z, (x, y, z) ∈ μ.supp → σ x + γ y + ϕ z = 0

/-- "`μ` has no `ℤ`-embeddings": every embedding into `(ℤ, +)` is
trivial, i.e. all three maps are constant. -/
def NoZEmbedding (μ : Dist (X × Y × Z)) : Prop :=
  ∀ (σ : X → ℤ) (γ : Y → ℤ) (ϕ : Z → ℤ), IsEmbedding μ σ γ ϕ →
    (∃ a, ∀ x, σ x = a) ∧ (∃ b, ∀ y, γ y = b) ∧ ∃ c, ∀ z, ϕ z = c

/-! ## The uniform sum-zero distribution -/

/-- The uniform distribution over `{(x, y, z) ∈ A³ : x + y + z = 0}`:
the mass is `1/|A|²` on the constraint set. -/
noncomputable def sumZeroDist (A : Type*) [AddCommGroup A] [Fintype A]
    [DecidableEq A] : Dist (A × A × A) where
  pmf ω := if ω.1 + ω.2.1 + ω.2.2 = 0 then ((Fintype.card A : ℝ) ^ 2)⁻¹ else 0
  nonneg ω := by
    by_cases h : ω.1 + ω.2.1 + ω.2.2 = 0
    · rw [if_pos h]
      exact inv_nonneg.mpr (pow_nonneg (Nat.cast_nonneg _) 2)
    · rw [if_neg h]
  sum_one := by
    classical
    haveI : Nonempty A := ⟨0⟩
    let e : A × A ≃ {ω : A × A × A // ω.1 + ω.2.1 + ω.2.2 = 0} :=
      { toFun := fun p => ⟨(p.1, p.2, -(p.1 + p.2)), by simp⟩
        invFun := fun ω => (ω.1.1, ω.1.2.1)
        left_inv := fun p => rfl
        right_inv := fun ω => by
          obtain ⟨⟨x, y, z⟩, h⟩ := ω
          apply Subtype.ext
          rw [add_eq_zero_iff_eq_neg] at h
          simp only [Prod.mk.injEq]
          exact ⟨trivial, trivial, by rw [h, neg_neg]⟩ }
    have hcard : (Finset.univ.filter fun ω : A × A × A =>
        ω.1 + ω.2.1 + ω.2.2 = 0).card = Fintype.card A ^ 2 := by
      rw [← Fintype.card_subtype, ← Fintype.card_congr e, Fintype.card_prod, pow_two]
    rw [← Finset.sum_filter, Finset.sum_const, hcard, nsmul_eq_mul, Nat.cast_pow,
      mul_inv_cancel₀]
    exact pow_ne_zero 2 (Nat.cast_ne_zero.mpr
      (ne_of_gt (Fintype.card_pos_iff.mpr ⟨0⟩)))

/-! ## Freiman homomorphisms and the packaged inverse input -/

/-- A Freiman homomorphism of order `s` on `A'`: sums over `s`-term
relations inside `A'` are preserved. -/
def IsFreimanHom {B G : Type*} [AddCommGroup B] [AddCommGroup G] [DecidableEq B]
    (s : ℕ) (f : B → G) (A' : Finset B) : Prop :=
  ∀ xs ys : Fin s → B, (∀ i, xs i ∈ A') → (∀ i, ys i ∈ A') →
    ∑ i, xs i = ∑ i, ys i → ∑ i, f (xs i) = ∑ i, f (ys i)

/-- The packaged additive-combinatorics inverse input.
If a strategy triple wins the `n`-fold sum-zero game over `ZMod (p^k·M)`
with probability at least `ε`, then the first strategy is an
order-`(p^k·M)` Freiman homomorphism on a subset of `(Fin n → A)` of size
at least `ε^{C·p^k·M}·|A|^n / C` for some `C ≥ 1` chosen for the fixed
data `(A, p, k, M)` — before the repetition count `n`, the strategies
and `ε` (the explicit form of the printed `Ω(ε^{O(p^k N)})·|A|^n`,
whose hidden constants do not depend on `n`); the subset `A'` is
chosen per instance. -/
def FreimanAssumption : Prop :=
  ∀ (A : Type) [AddCommGroup A] [Fintype A] [DecidableEq A]
    (p k M : ℕ), Nat.Prime p → 1 ≤ k → 1 < M →
    ∃ (C : ℝ), 1 ≤ C ∧
    ∀ (n : ℕ), 1 ≤ n →
    ∀ (f g h : (Fin n → A) → Fin n → ZMod (p ^ k * M)) (ε : ℝ), 0 < ε →
      ε ≤ winProb (Dist.pi3 (sumZeroDist A) n)
        (repT (fun _ _ _ => (0 : ZMod (p ^ k * M))) n) f g h →
      ∃ (A' : Finset (Fin n → A)),
        ε ^ (C * (p ^ k * M : ℝ)) * (Fintype.card A : ℝ) ^ n / C ≤ (A'.card : ℝ) ∧
        IsFreimanHom (p ^ k * M) f A'

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- but the fixed part above and the main-theorem statement must not be
-- modified.

/-- The main theorem, conditional on the packaged additive-combinatorics
inverse input `FreimanAssumption`: a 3-player XOR game of value `< 1`
whose question distribution has no `ℤ`-embeddings has exponentially
decaying parallel-repetition value. -/
theorem xor3_parallel_repetition
    (hAC : FreimanAssumption)
    {Ans : Type*} [Fintype Ans] [DecidableEq Ans] [AddCommGroup Ans]
    (μ : Dist (X × Y × Z)) (t : X → Y → Z → Ans)
    (hval : gameVal μ t < 1) (hnoZ : NoZEmbedding μ) :
    ∃ c : ℝ, 0 < c ∧ ∀ n : ℕ, 1 ≤ n →
      gameVal (Dist.pi3 μ n) (repT t n) ≤ 2 ^ (-c * (n : ℝ)) := by
  -- CHECKPOINT xor3_parallel_repetition BEGIN
  sorry
  -- CHECKPOINT xor3_parallel_repetition END

end XOR3PR
