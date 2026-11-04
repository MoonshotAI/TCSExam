/-
Statement layer for the polynomial Freiman–Ruzsa conjecture over the integers
(Marton's conjecture in ℤ; the strengthening of Freiman's theorem proposed by
Ruzsa in the 1990s; parameters as in the convex-progression formulation —
Lovett–Regev, Discrete Analysis 2017:8, Conjecture 1.2; Manners,
arXiv:1709.09738):
every finite nonempty set `A` of integers with `|A+A| ≤ K·|A|` can be covered
by at most `K^{O(1)}` translates of a convex body progression `P` of dimension
`O(log K)` and size at most `K^{O(1)}·|A|`.  Here the size of `P` is the
lattice-point count of its body on the preimage side
(`|{l : Fin dim → ℤ | l ∈ body}|`), the technical notion of size of the
original conjectures (Manners, arXiv:1709.09738, Conjecture 1.2, footnote 1;
Lovett–Regev's `|L ∩ B|`) — not the cardinality of the image set in `ℤ`.

The generalized-arithmetic-progression (GAP) formulation of this conjecture is
FALSE (Lovett–Regev, Discrete Analysis 2017:8); the convex-progression
formulation stated here is the surviving standard form.

This file is the task's definition zone plus slot zone:
- The definition zone defines convex body progressions (a symmetric convex
  bounded body in `ℝ^dim`, its integer points pushed into the group by a
  homomorphism `ℤ^dim →+ G` and translated by a base point), proves that over
  `ℤ` both the lattice point set of the body (`latticeFinset`) and the point
  set in the group (`toFinset`) are finite, and constructs one concrete
  instance (`prog024`, the progression `{0, 2, 4}`).
- The slot zone states the conjecture (`conj`) and its negation (`refuted`).
  Both proof bodies are left blank.

Fidelity notes (see `tests/reference/concept-ledger.md` of the packaged task):
1. A convex body progression is the image of the integer points of a symmetric
   convex bounded body under a homomorphism `ℤ^dim →+ G`, translated by a base
   point. Restricting the lattice to `ℤ^dim` is without loss of generality
   (Lovett–Regev, Conjecture 1.2, footnote 1). Boundedness is part of the
   data so that the point set over `ℤ` is finite and has a cardinality.
2. No properness/injectivity requirement on the homomorphism. Properness is
   not the issue separating the two formulations: the GAP form works with
   the same technical notion of size (improper progressions allowed). What
   the Lovett–Regev counterexample exploits is that a GAP must be aligned
   to a lattice basis — an axis-parallel box in lattice coordinates —
   while the surviving convex-progression form allows an arbitrary
   symmetric convex body (Manners, arXiv:1709.09738, footnote 1 and
   Remark 1.5).
3. The doubling parameter `K` is quantified over `ℕ` (every real bound
   `|A+A| ≤ K·|A|` implies the integer bound with `⌈K⌉`); `O(log K)` is
   rendered as `C₁ * Nat.log 2 (K + 1)` and `K^{O(1)}` as `(K + 1) ^ C₂`, with
   natural-number constants `C₁ C₂`. The `+1` avoids the `log 1 = 0`
   degeneracy, matching the `log(2 + K)` convention of the literature.
4. The size bound in `conj` counts the lattice points of the body on the
   preimage side (`latticeFinset.card`), exactly the technical notion of
   size in Manners's Conjecture 1.2 (footnote 1) and Lovett–Regev's
   `|L ∩ B|` — not the cardinality of the image set `toFinset` in `ℤ`.
   Since the image set is the image of the lattice set under
   `l ↦ base + map l`, its cardinality is at most the lattice-point count
   (`toFinset_card_le_latticeFinset_card`). With the lattice-point count
   the statement therefore matches the original conjectures in strength;
   the image-set cardinality bound would be a priori weaker (implied by
   the original conjectures, not known to imply them).
-/

import Mathlib

open scoped Pointwise

namespace PFRIntegers

/-! ### Convex body progressions -/

/-- A **convex body progression** in an additive commutative group `G`: the
data of a dimension `dim`, a symmetric convex bounded body in `ℝ^dim`, a base
point of `G`, and a homomorphism from the lattice `ℤ^dim` to `G`. Its points
(see `toSet`) are the images of the integer points of the body, translated by
the base point. This is the structured object of the polynomial
Freiman–Ruzsa conjecture (Lovett–Regev, Conjecture 1.2). -/
structure ConvexProgression (G : Type*) [AddCommGroup G] where
  /-- the dimension (rank) of the progression -/
  dim : ℕ
  /-- the symmetric convex bounded body, as a subset of `ℝ^dim` -/
  body : Set (Fin dim → ℝ)
  convex_body : Convex ℝ body
  symm_body : ∀ x ∈ body, -x ∈ body
  bounded_body : Bornology.IsBounded body
  /-- the translation base point -/
  base : G
  /-- the homomorphism carrying lattice points into the group -/
  map : (Fin dim → ℤ) →+ G

namespace ConvexProgression

variable {G : Type*} [AddCommGroup G]

/-- The point set of a convex body progression: the integer points of the
body, pushed into `G` by `map` and translated by `base`. -/
def toSet (C : ConvexProgression G) : Set G :=
  {g | ∃ l : Fin C.dim → ℤ, (fun i => (l i : ℝ)) ∈ C.body ∧ C.base + C.map l = g}

theorem mem_toSet {C : ConvexProgression G} {g : G} :
    g ∈ C.toSet ↔
      ∃ l : Fin C.dim → ℤ, (fun i => (l i : ℝ)) ∈ C.body ∧ C.base + C.map l = g :=
  Iff.rfl

/-- The lattice points of the body on the preimage side:
`{l : Fin dim → ℤ | (l : ℝ^dim) ∈ body}`.  This is the technical notion of
size in Manners's Conjecture 1.2 (footnote 1) and Lovett–Regev's `|L ∩ B|` —
NOT the point set in the group (see `toSet`). -/
def latticeSet (C : ConvexProgression ℤ) : Set (Fin C.dim → ℤ) :=
  {l | (fun i => (l i : ℝ)) ∈ C.body}

/-- Over `ℤ`, the lattice points of the body are finite: the body is bounded,
so all its integer points have bounded coordinates. -/
theorem finite_latticeSet (C : ConvexProgression ℤ) : C.latticeSet.Finite := by
  obtain ⟨R, hR⟩ := isBounded_iff_forall_norm_le.mp C.bounded_body
  obtain ⟨M, hM⟩ := exists_nat_gt R
  have hcoord : C.latticeSet ⊆ Set.univ.pi fun _ => Set.Icc (-(M : ℤ)) M := by
    intro l hl
    rw [Set.mem_pi]
    intro i _
    have hnorm : ‖(fun j => (l j : ℝ))‖ ≤ R := hR _ hl
    have habs : |(l i : ℝ)| ≤ (M : ℝ) := by
      have h1 : ‖(l i : ℝ)‖ ≤ ‖fun j => (l j : ℝ)‖ :=
        norm_le_pi_norm (fun j => (l j : ℝ)) i
      have h2 : ‖(l i : ℝ)‖ ≤ (M : ℝ) := h1.trans (hnorm.trans hM.le)
      rwa [Real.norm_eq_abs] at h2
    rw [abs_le] at habs
    rw [Set.mem_Icc]
    exact ⟨by exact_mod_cast habs.1, by exact_mod_cast habs.2⟩
  exact (Set.Finite.pi fun _ => Set.finite_Icc _ _).subset hcoord

/-- Over `ℤ`, the point set of a convex body progression is finite: it is
contained in the image of the finite lattice set `latticeSet` under
`l ↦ base + map l`. -/
theorem finite_toSet (C : ConvexProgression ℤ) : C.toSet.Finite := by
  refine (C.finite_latticeSet.image fun l : Fin C.dim → ℤ => C.base + C.map l).subset ?_
  rintro g ⟨l, hl, rfl⟩
  exact ⟨l, hl, rfl⟩

/-- The finite set of points of a convex body progression over `ℤ`. -/
noncomputable def toFinset (C : ConvexProgression ℤ) : Finset ℤ :=
  C.finite_toSet.toFinset

theorem coe_toFinset (C : ConvexProgression ℤ) : (C.toFinset : Set ℤ) = C.toSet :=
  C.finite_toSet.coe_toFinset

theorem mem_toFinset {C : ConvexProgression ℤ} {g : ℤ} :
    g ∈ C.toFinset ↔ g ∈ C.toSet :=
  C.finite_toSet.mem_toFinset

/-- The lattice points of the body on the preimage side, as a finite set:
`{l : Fin dim → ℤ | (l : ℝ^dim) ∈ body}`.  This is the technical notion of
size in Manners's Conjecture 1.2 (footnote 1) and Lovett–Regev's `|L ∩ B|` —
NOT the cardinality of the image set.  The conjecture statement bounds the
size of a progression by `latticeFinset.card`; see
`toFinset_card_le_latticeFinset_card` for the comparison with the image-set
cardinality. -/
noncomputable def latticeFinset (C : ConvexProgression ℤ) : Finset (Fin C.dim → ℤ) :=
  C.finite_latticeSet.toFinset

theorem coe_latticeFinset (C : ConvexProgression ℤ) :
    (C.latticeFinset : Set (Fin C.dim → ℤ)) = C.latticeSet :=
  C.finite_latticeSet.coe_toFinset

theorem mem_latticeFinset {C : ConvexProgression ℤ} {l : Fin C.dim → ℤ} :
    l ∈ C.latticeFinset ↔ l ∈ C.latticeSet :=
  C.finite_latticeSet.mem_toFinset

/-- The image-set cardinality is at most the lattice-point count: `toFinset`
is contained in the image of `latticeFinset` under `l ↦ base + map l`, and
taking images does not increase the cardinality of a finite set.  Hence the
lattice-count size bound used in `conj` implies the a priori weaker
image-set bound, matching the strength of the original conjectures. -/
theorem toFinset_card_le_latticeFinset_card (C : ConvexProgression ℤ) :
    C.toFinset.card ≤ C.latticeFinset.card := by
  have hsub : C.toFinset ⊆
      C.latticeFinset.image fun l : Fin C.dim → ℤ => C.base + C.map l := by
    intro g hg
    rw [mem_toFinset] at hg
    obtain ⟨l, hl, rfl⟩ := hg
    rw [Finset.mem_image]
    exact ⟨l, C.finite_latticeSet.mem_toFinset.mpr hl, rfl⟩
  exact (Finset.card_le_card hsub).trans Finset.card_image_le

end ConvexProgression

/-! ### A concrete one-dimensional convex body progression -/

/-- A concrete one-dimensional convex body progression over `ℤ`: the integer
points of the symmetric interval `[-1, 1]` (viewed in `Fin 1 → ℝ`), scaled by
`2` and translated by `2`. -/
def prog024 : ConvexProgression ℤ where
  dim := 1
  body := {x : Fin 1 → ℝ | |x 0| ≤ 1}
  convex_body := by
    intro x hx y hy a b ha hb hab
    simp only [Set.mem_setOf_eq] at hx hy ⊢
    have hadd : (a • x + b • y) (0 : Fin 1) = a * x 0 + b * y 0 := by
      simp [Pi.smul_apply, smul_eq_mul]
    rw [hadd]
    calc |a * x 0 + b * y 0|
        ≤ |a * x 0| + |b * y 0| := abs_add_le _ _
      _ = a * |x 0| + b * |y 0| := by
          rw [abs_mul, abs_mul, abs_of_nonneg ha, abs_of_nonneg hb]
      _ ≤ a * 1 + b * 1 := by
          apply add_le_add <;> apply mul_le_mul_of_nonneg_left ‹_› ‹_›
      _ = 1 := by linarith
  symm_body := by
    simp only [Set.mem_setOf_eq]
    intro x hx
    have hneg : (-x) (0 : Fin 1) = -(x 0) := rfl
    rw [hneg, abs_neg]
    exact hx
  bounded_body := by
    have hb : Bornology.IsBounded (Metric.closedBall (0 : Fin 1 → ℝ) 1) :=
      Metric.isBounded_closedBall
    apply hb.subset
    intro x hx
    rw [Metric.mem_closedBall, dist_zero_right]
    -- the norm of `x : Fin 1 → ℝ` is `|x 0|`
    have h1 : ‖x‖ ≤ 1 ↔ ∀ i, ‖x i‖ ≤ 1 := pi_norm_le_iff_of_nonneg zero_le_one
    rw [h1]
    intro i
    rw [Real.norm_eq_abs, Fin.eq_zero i]
    exact hx
  base := 2
  map := AddMonoidHom.mk' (fun l : Fin 1 → ℤ => 2 * l 0) fun a b => by
    show 2 * (a + b) 0 = 2 * a 0 + 2 * b 0
    rw [Pi.add_apply]
    ring

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

/-! ## Slot zone: the conjecture and its negation -/

-- @[slot main]
/-- **The polynomial Freiman–Ruzsa conjecture over the integers** (Marton's
conjecture in ℤ): there exist constants `C₁ C₂` such that every finite
nonempty `A ⊆ ℤ` with `|A+A| ≤ K·|A|` is covered by at most `(K+1)^{C₂}`
translates of a convex body progression `P` of dimension at most
`C₁·log₂(K+1)` and size at most `(K+1)^{C₂}·|A|`.  The size of `P` is the
lattice-point count of its body on the preimage side (`P.latticeFinset.card`),
the technical notion of size of the original conjectures (Manners,
arXiv:1709.09738, Conjecture 1.2, footnote 1; Lovett–Regev's `|L ∩ B|`),
which is stronger than the image-set cardinality (`P.toFinset.card`) by
`toFinset_card_le_latticeFinset_card`. -/
theorem conj :
    ∃ C₁ C₂ : ℕ, ∀ A : Finset ℤ, A.Nonempty → ∀ K : ℕ,
      (A + A).card ≤ K * A.card →
      ∃ P : ConvexProgression ℤ,
        P.dim ≤ C₁ * Nat.log 2 (K + 1) ∧
          P.latticeFinset.card ≤ (K + 1) ^ C₂ * A.card ∧
            ∃ X : Finset ℤ, X.card ≤ (K + 1) ^ C₂ ∧ A ⊆ X + P.toFinset := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

-- @[slot main]
/-- The negation of the polynomial Freiman–Ruzsa conjecture over the
integers. -/
theorem refuted :
    ¬∃ C₁ C₂ : ℕ, ∀ A : Finset ℤ, A.Nonempty → ∀ K : ℕ,
        (A + A).card ≤ K * A.card →
        ∃ P : ConvexProgression ℤ,
          P.dim ≤ C₁ * Nat.log 2 (K + 1) ∧
            P.latticeFinset.card ≤ (K + 1) ^ C₂ * A.card ∧
              ∃ X : Finset ℤ, X.card ≤ (K + 1) ^ C₂ ∧ A ⊆ X + P.toFinset := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

end PFRIntegers
