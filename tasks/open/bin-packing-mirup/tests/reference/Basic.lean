/-
Self-contained statement layer for the bin packing MIRUP conjecture
(modified integer round-up property).

The conjecture (Scheithauer–Terno 1995): for every instance I of the
one-dimensional bin packing problem (item sizes l₁,…,lₙ and bin capacity L,
positive integers with lᵢ ≤ L), the integer optimum OPT(I) and the value
LP(I) of the Gilmore–Gomory configuration LP relaxation satisfy

    OPT(I) ≤ ⌈LP(I)⌉ + 1.

The unmodified integer round-up property (OPT = ⌈LP⌉) is false: Kartak,
Kurz, Ripatti and Scheithauer (Discrete Applied Mathematics, 2015,
arXiv:1405.5988) proved computationally that every instance with at most 9
items has IRUP and exhibited non-IRUP instances with 10 items — e.g. the
sizes (4,6,6,9,16,29,32,37,40,62) with capacity 81, with LP = 3 but OPT = 4.
No instance with OPT ≥ ⌈LP⌉ + 2 is known, and MIRUP itself remains open
(cf. Borges et al., arXiv:2305.15291, 2023: "It is conjectured that MIRUP
holds for all instances of the CSP and BPP").

This file is the task's definition zone plus proof-slot zone:
- Definition zone (fixed): patterns (configurations), fractional covers and
  the LP value `lpVal`, packings and the integer optimum `optNumber`, the
  basic bounds connecting them (rational primal/dual LP certificates, their
  decidable natural-number versions, LP ≤ OPT, a pairwise-incompatibility
  lower bound), and several concrete instances from the literature.
- Proof-slot zone: the two main slots `conj` (the conjecture) and `refuted`
  (its negation); proving either one scores full marks.

Fidelity notes (see `tests/reference/concept-ledger.md` of the packaged
task):
1. An instance is a list of item sizes `l : Fin n → ℕ` with `0 < l i ≤ L`
   and integer bin capacity `L` — the integer input form of the literature
   (e.g. Kartak et al. write instances as (n, L, l)). This is equivalent to
   the (0,1]-normalized form: divide sizes and capacity by L.
2. Patterns are item sets with total size ≤ L (each item used at most once
   per bin); the configuration LP covers every item at least once, so
   `lpVal` is the Gilmore–Gomory LP value of the literature (scale
   invariant: it depends only on the pattern set, not on the capacity
   scale).
3. `lpVal` is a real number defined as an infimum over rational fractional
   covers; the infimum is attained (finite LP), so it is the LP optimum.
   The rational certificates are never evaluated by the kernel: the
   decidable work is done by the natural-number certificate bridges
   `lpVal_le_of_natCover` / `le_lpVal_of_natDual`.
-/

import Mathlib

namespace BinPackingMIRUP

variable {n : ℕ} (l : Fin n → ℕ) (L : ℕ)

/-! ## Patterns, fractional covers, and the configuration LP value -/

/-- A pattern (configuration) of the instance: a set of items that fits into
one bin (total size at most the capacity `L`). -/
def IsPattern (p : Finset (Fin n)) : Prop := ∑ i ∈ p, l i ≤ L

instance (p : Finset (Fin n)) : Decidable (IsPattern l L p) :=
  inferInstanceAs (Decidable (∑ i ∈ p, l i ≤ L))

/-- All patterns of the instance. -/
def patterns : Finset (Finset (Fin n)) := Finset.univ.powerset.filter (IsPattern l L)

/-- A fractional cover: nonnegative rational weights on the patterns such
that every item is covered with total weight at least 1. (Values of `x`
outside `patterns l L` are irrelevant.) -/
def IsFracCover (x : Finset (Fin n) → ℚ) : Prop :=
  (∀ p ∈ patterns l L, 0 ≤ x p) ∧ ∀ i, 1 ≤ ∑ p ∈ patterns l L, if i ∈ p then x p else 0

instance (x : Finset (Fin n) → ℚ) : Decidable (IsFracCover l L x) := by
  unfold IsFracCover
  infer_instance

/-- The Gilmore–Gomory configuration LP value: the infimum of the total
weight over all fractional covers. The infimum ranges over a nonempty set
bounded below by 0 and is attained (a finite LP with rational data), so this
is the usual LP optimum. -/
noncomputable def lpVal : ℝ :=
  sInf {t : ℝ | ∃ x : Finset (Fin n) → ℚ, IsFracCover l L x ∧ t = ∑ p ∈ patterns l L, (x p : ℝ)}

/-- Primal certificate: any fractional cover upper-bounds the LP value. -/
theorem lpVal_le_of_feasible {x : Finset (Fin n) → ℚ} (hx : IsFracCover l L x) :
    lpVal l L ≤ ∑ p ∈ patterns l L, (x p : ℝ) := by
  apply csInf_le
  · refine ⟨0, ?_⟩
    rintro t ⟨y, hy, rfl⟩
    exact Finset.sum_nonneg fun p hp => by exact_mod_cast hy.1 p hp
  · exact ⟨x, hx, rfl⟩

/-- Dual certificate: item weights `w` with total at most 1 on every pattern
lower-bound the LP value (weak duality). -/
theorem le_lpVal_of_dual (hle : ∀ i, l i ≤ L) (w : Fin n → ℚ) (hw0 : ∀ i, 0 ≤ w i)
    (hwp : ∀ p ∈ patterns l L, ∑ i ∈ p, w i ≤ 1) :
    ((∑ i, w i : ℚ) : ℝ) ≤ lpVal l L := by
  apply le_csInf
  · -- the feasible set is nonempty: cover every item by its singleton pattern
    have hsing : ∀ i : Fin n, ({i} : Finset (Fin n)) ∈ patterns l L := by
      intro i
      simp [patterns, IsPattern, hle i]
    refine ⟨∑ p ∈ patterns l L, ((if ∃ i, p = {i} then (1 : ℚ) else 0 : ℚ) : ℝ),
      fun p => if ∃ i, p = {i} then 1 else 0, ⟨fun p _ => ?_, fun i => ?_⟩, rfl⟩
    · show (0 : ℚ) ≤ if ∃ i, p = {i} then 1 else 0
      split_ifs <;> norm_num
    · show (1 : ℚ) ≤ ∑ p ∈ patterns l L,
        if i ∈ p then (if ∃ j, p = {j} then (1 : ℚ) else 0) else 0
      calc (1 : ℚ) = if i ∈ ({i} : Finset (Fin n)) then
              (if ∃ j, ({i} : Finset (Fin n)) = {j} then 1 else 0) else 0 := by simp
        _ ≤ ∑ p ∈ patterns l L, if i ∈ p then (if ∃ j, p = {j} then (1 : ℚ) else 0) else 0 := by
              apply Finset.single_le_sum
                (s := patterns l L)
                (f := fun p => if i ∈ p then (if ∃ j, p = {j} then (1 : ℚ) else 0) else 0)
                _ (hsing i)
              intro p _
              split_ifs <;> norm_num
  · rintro t ⟨x, hx, rfl⟩
    have key : (∑ i, w i : ℚ) ≤ ∑ p ∈ patterns l L, x p := by
      calc ∑ i, w i ≤ ∑ i, w i * (∑ p ∈ patterns l L, if i ∈ p then x p else 0) := by
            refine Finset.sum_le_sum fun i _ => ?_
            nth_rewrite 1 [← mul_one (w i)]
            exact mul_le_mul_of_nonneg_left (hx.2 i) (hw0 i)
        _ = ∑ p ∈ patterns l L, ∑ i, (if i ∈ p then w i * x p else 0) := by
            have step : ∀ i, w i * (∑ p ∈ patterns l L, if i ∈ p then x p else 0)
                = ∑ p ∈ patterns l L, (if i ∈ p then w i * x p else 0) := by
              intro i
              rw [Finset.mul_sum]
              refine Finset.sum_congr rfl fun p _ => ?_
              by_cases h : i ∈ p <;> simp [h]
            rw [Finset.sum_congr rfl (fun i _ => step i), Finset.sum_comm]
        _ = ∑ p ∈ patterns l L, x p * (∑ i ∈ p, w i) := by
            refine Finset.sum_congr rfl fun p _ => ?_
            rw [← Finset.sum_filter (s := Finset.univ) (p := fun i => i ∈ p),
              Finset.filter_mem_eq_inter, Finset.univ_inter, mul_comm (x p),
              Finset.sum_mul]
        _ ≤ ∑ p ∈ patterns l L, x p * 1 := by
            refine Finset.sum_le_sum fun p hp => ?_
            exact mul_le_mul_of_nonneg_left (hwp p hp) (hx.1 p hp)
        _ = ∑ p ∈ patterns l L, x p := by simp
    exact_mod_cast key

/-- Summing a family of rationals divided by a common denominator. -/
theorem sum_div_rat {α : Type*} (s : Finset α) (F : α → ℚ) (D : ℕ) :
    (∑ p ∈ s, F p / D) = (∑ p ∈ s, F p) / D := by
  simp_rw [div_eq_mul_inv, ← Finset.sum_mul]

/-- Natural-number primal certificate over a common denominator `D`: if
every item is covered at least `D` times by the natural pattern weights
`X`, then `x p = X p / D` is a fractional cover, so the LP value is at most
`(∑ X p) / D`. The hypothesis `hcov` is decidable by kernel computation
(unlike the rational version, since all arithmetic is in `ℕ`). -/
theorem lpVal_le_of_natCover (D : ℕ) (hD : 0 < D) (X : Finset (Fin n) → ℕ)
    (hcov : ∀ i, D ≤ ∑ p ∈ patterns l L, if i ∈ p then X p else 0) :
    lpVal l L ≤ (((∑ p ∈ patterns l L, X p : ℚ) / D : ℚ) : ℝ) := by
  have hfc : IsFracCover l L fun p => (X p : ℚ) / D := by
    refine ⟨fun p _ => by positivity, fun i => ?_⟩
    show (1 : ℚ) ≤ ∑ p ∈ patterns l L, if i ∈ p then (X p : ℚ) / D else 0
    have h1 : (D : ℚ) ≤ ∑ p ∈ patterns l L, if i ∈ p then (X p : ℚ) else 0 := by
      exact_mod_cast hcov i
    have e : ∀ p, (if i ∈ p then (X p : ℚ) / D else 0)
        = (if i ∈ p then (X p : ℚ) else 0) / D := by
      intro p
      split_ifs <;> simp
    rw [Finset.sum_congr rfl (fun p _ => e p), sum_div_rat]
    rwa [one_le_div (show (0 : ℚ) < D by exact_mod_cast hD)]
  have e2 : (∑ p ∈ patterns l L, (((X p : ℚ) / D : ℚ) : ℝ))
      = (((∑ p ∈ patterns l L, X p : ℚ) / D : ℚ) : ℝ) := by
    rw [← Rat.cast_sum, sum_div_rat]
  calc lpVal l L ≤ ∑ p ∈ patterns l L, (((X p : ℚ) / D : ℚ) : ℝ) :=
        lpVal_le_of_feasible _ _ hfc
    _ = (((∑ p ∈ patterns l L, X p : ℚ) / D : ℚ) : ℝ) := e2

/-- Natural-number dual certificate over a common denominator `D`: if the
natural item weights `W` sum to at most `D` on every pattern, then
`w i = W i / D` is a dual solution and the LP value is at least
`(∑ W i) / D`. The hypothesis `hW` is decidable by kernel computation. -/
theorem le_lpVal_of_natDual (hle : ∀ i, l i ≤ L) (D : ℕ) (hD : 0 < D) (W : Fin n → ℕ)
    (hW : ∀ p ∈ patterns l L, ∑ i ∈ p, W i ≤ D) :
    (((∑ i, W i : ℚ) / D : ℚ) : ℝ) ≤ lpVal l L := by
  have h := le_lpVal_of_dual l L hle (fun i => (W i : ℚ) / D)
    (fun i => by positivity) ?_
  · have h2 : ((∑ i, (fun i => (W i : ℚ) / D) i : ℚ) : ℝ)
        = (((∑ i, W i : ℚ) / D : ℚ) : ℝ) := by
      rw [show (∑ i, (fun i => (W i : ℚ) / D) i) = ∑ i, (W i : ℚ) / D from rfl,
        sum_div_rat]
    rwa [h2] at h
  · intro p hp
    rw [show (∑ i ∈ p, (fun i => (W i : ℚ) / D) i) = (∑ i ∈ p, (W i : ℚ)) / D from
      sum_div_rat _ _ _]
    rw [div_le_one (show (0 : ℚ) < D by exact_mod_cast hD)]
    exact_mod_cast hW p hp

/-! ## Packings and the integer optimum -/

/-- A packing of the instance into `k` bins: an assignment of every item to
one of `k` bins such that the total size in every bin is at most `L`. -/
def PacksIn (k : ℕ) : Prop :=
  ∃ f : Fin n → Fin k, ∀ b, ∑ i ∈ Finset.univ.filter (fun i => f i = b), l i ≤ L

instance (k : ℕ) : Decidable (PacksIn l L k) :=
  inferInstanceAs (Decidable
    (∃ f : Fin n → Fin k, ∀ b, ∑ i ∈ Finset.univ.filter (fun i => f i = b), l i ≤ L))

/-- Every item fits alone in its own bin, so `n` bins always suffice. -/
theorem packsIn_self (hle : ∀ i, l i ≤ L) : PacksIn l L n := by
  refine ⟨id, fun b => ?_⟩
  have : (Finset.univ.filter fun i => id i = b) = {b} := by
    ext i
    simp
  rw [this, Finset.sum_singleton]
  exact hle b

/-- A packing into `k` bins is also a packing into any larger number of bins. -/
theorem PacksIn.mono {k k' : ℕ} (hle : k ≤ k') (h : PacksIn l L k) : PacksIn l L k' := by
  obtain ⟨f, hf⟩ := h
  refine ⟨fun i => Fin.castLE hle (f i), fun b => ?_⟩
  by_cases hb : (b : ℕ) < k
  · have hset : (Finset.univ.filter fun i => Fin.castLE hle (f i) = b)
        = Finset.univ.filter fun i => f i = ⟨b, hb⟩ := by
      refine Finset.filter_congr fun i _ => ?_
      constructor
      · intro h1
        have h2 := congrArg Fin.val h1
        simp only [Fin.val_castLE] at h2
        exact Fin.ext h2
      · intro h1
        rw [h1]
        exact Fin.ext rfl
    rw [hset]
    exact hf ⟨b, hb⟩
  · have hset : (Finset.univ.filter fun i => Fin.castLE hle (f i) = b) = ∅ := by
      apply Finset.filter_false_of_mem
      intro i _ h1
      have h2 := congrArg Fin.val h1
      simp only [Fin.val_castLE] at h2
      have h3 := (f i).isLt
      omega
    rw [hset]
    simp

/-- The integer optimum: the least number of bins the instance packs into.
Well-defined because `n` bins always suffice (`packsIn_self`). -/
def optNumber (hle : ∀ i, l i ≤ L) : ℕ :=
  ((Finset.range (n + 1)).filter (PacksIn l L)).min'
    ⟨n, Finset.mem_filter.mpr ⟨Finset.mem_range_succ_iff.mpr le_rfl, packsIn_self l L hle⟩⟩

/-- The optimum is attained: the instance packs into `optNumber` bins. -/
theorem optNumber_spec (hle : ∀ i, l i ≤ L) : PacksIn l L (optNumber l L hle) :=
  (Finset.mem_filter.mp (Finset.min'_mem _ _)).2

/-- Any packing upper-bounds the optimum. -/
theorem optNumber_le_of_packsIn (hle : ∀ i, l i ≤ L) {k : ℕ} (hk : k ≤ n)
    (h : PacksIn l L k) :
    optNumber l L hle ≤ k :=
  Finset.min'_le _ _ (Finset.mem_filter.mpr ⟨Finset.mem_range_succ_iff.mpr hk, h⟩)

/-- If `k` bins do not suffice, the optimum is at least `k + 1`. -/
theorem le_optNumber_of_not_packsIn (hle : ∀ i, l i ≤ L) {k : ℕ} (h : ¬ PacksIn l L k) :
    k + 1 ≤ optNumber l L hle := by
  by_contra hc
  exact h (PacksIn.mono l L (Nat.le_of_lt_succ (Nat.lt_of_not_ge hc))
    (optNumber_spec l L hle))

/-- The LP value lower-bounds the integer optimum: a packing into `k` bins
is a fractional cover of total weight `k`. -/
theorem lpVal_le_optNumber (hle : ∀ i, l i ≤ L) :
    lpVal l L ≤ (optNumber l L hle : ℝ) := by
  obtain ⟨f, hf⟩ := optNumber_spec l L hle
  have hpat : ∀ b : Fin (optNumber l L hle),
      (Finset.univ.filter (fun i => f i = b)) ∈ patterns l L := by
    intro b
    have hb : IsPattern l L (Finset.univ.filter (fun i => f i = b)) := by
      show ∑ i ∈ Finset.univ.filter (fun i => f i = b), l i ≤ L
      exact hf b
    rw [patterns, Finset.mem_filter]
    exact ⟨Finset.mem_powerset.mpr (Finset.subset_univ _), hb⟩
  set x : Finset (Fin n) → ℚ := fun p =>
    ((Finset.univ.filter (fun b => (Finset.univ.filter (fun i => f i = b)) = p)).card : ℚ)
    with hx_def
  have hcover : IsFracCover l L x := by
    refine ⟨fun p _ => by simp [hx_def], fun i => ?_⟩
    have h1 : (Finset.univ.filter (fun i' => f i' = f i)) ∈ patterns l L := hpat (f i)
    have h2 : i ∈ Finset.univ.filter (fun i' => f i' = f i) := by
      rw [Finset.mem_filter]
      exact ⟨Finset.mem_univ _, rfl⟩
    have h3 : (1 : ℚ) ≤ x (Finset.univ.filter (fun i' => f i' = f i)) := by
      simp only [hx_def, Nat.one_le_cast]
      rw [Finset.one_le_card]
      exact ⟨f i, Finset.mem_filter.mpr ⟨Finset.mem_univ _, rfl⟩⟩
    have h4 : x (Finset.univ.filter (fun i' => f i' = f i))
        ≤ ∑ p ∈ patterns l L, (if i ∈ p then x p else 0) := by
      have h5 : ∀ p ∈ patterns l L, 0 ≤ (if i ∈ p then x p else 0 : ℚ) := by
        intro p _
        split_ifs
        · simp [hx_def]
        · norm_num
      calc x (Finset.univ.filter (fun i' => f i' = f i))
          = if i ∈ Finset.univ.filter (fun i' => f i' = f i)
            then x (Finset.univ.filter (fun i' => f i' = f i)) else 0 := by simp [h2]
        _ ≤ ∑ p ∈ patterns l L, (if i ∈ p then x p else 0) :=
            Finset.single_le_sum h5 h1
    exact h3.trans h4
  have htotal : (∑ p ∈ patterns l L, x p) = (optNumber l L hle : ℚ) := by
    have h := Finset.sum_card_fiberwise_eq_card_filter
      (Finset.univ : Finset (Fin (optNumber l L hle)))
      (patterns l L) (fun b => Finset.univ.filter (fun i => f i = b))
    rw [Finset.filter_true_of_mem (fun b _ => hpat b), Finset.card_univ,
      Fintype.card_fin] at h
    show (∑ p ∈ patterns l L,
      ((Finset.univ.filter (fun b => (Finset.univ.filter (fun i => f i = b)) = p)).card : ℚ))
        = (optNumber l L hle : ℚ)
    exact_mod_cast h
  calc lpVal l L ≤ ∑ p ∈ patterns l L, (x p : ℝ) := lpVal_le_of_feasible _ _ hcover
    _ = (optNumber l L hle : ℝ) := by exact_mod_cast htotal

/-- Lower bound from pairwise incompatibility: items that pairwise do not
fit into one bin must go to distinct bins. -/
theorem le_optNumber_of_pairwise_incompatible (hle : ∀ i, l i ≤ L)
    (T : Finset (Fin n)) (hT : ∀ i ∈ T, ∀ j ∈ T, i ≠ j → L < l i + l j) :
    T.card ≤ optNumber l L hle := by
  obtain ⟨f, hf⟩ := optNumber_spec l L hle
  have hinj : Set.InjOn f T := by
    intro i hi j hj hij
    by_contra hne
    have h1 : L < l i + l j := hT i hi j hj hne
    have hsub : ({i, j} : Finset (Fin n)) ⊆ Finset.univ.filter (fun l' => f l' = f i) := by
      intro l' hl'
      simp only [Finset.mem_insert, Finset.mem_singleton] at hl'
      rcases hl' with rfl | rfl
      · exact Finset.mem_filter.mpr ⟨Finset.mem_univ _, rfl⟩
      · exact Finset.mem_filter.mpr ⟨Finset.mem_univ _, hij.symm⟩
    have h2 : l i + l j ≤ ∑ l' ∈ Finset.univ.filter (fun l' => f l' = f i), l l' := by
      calc l i + l j = ∑ l' ∈ ({i, j} : Finset (Fin n)), l l' := by
            rw [Finset.sum_insert (by simp [hne]), Finset.sum_singleton]
        _ ≤ ∑ l' ∈ Finset.univ.filter (fun l' => f l' = f i), l l' :=
            Finset.sum_le_sum_of_subset_of_nonneg hsub fun _ _ _ => Nat.zero_le _
    have h3 := hf (f i)
    omega
  calc T.card ≤ (Finset.univ : Finset (Fin (optNumber l L hle))).card :=
        Finset.card_le_card_of_injOn f (fun i _ => Finset.mem_univ _) hinj
    _ = optNumber l L hle := by rw [Finset.card_univ, Fintype.card_fin]

/-! ## Concrete instances for the checkpoints -/

/-- Checkpoint (b), instance I₁: sizes (6,4,4,3,3) with capacity 12 — in
(0,1]-normalized form (1/2, 1/3, 1/3, 1/4, 1/4). The LP value 9/5 lies
strictly between the volume 5/3 and the integer optimum 2. -/
def instB1 : Fin 5 → ℕ := fun i => ([6, 4, 4, 3, 3] : List ℕ).getD i 0

theorem instB1_le : ∀ i, instB1 i ≤ 12 := by decide

/-- Checkpoint (b), instance I₂: four items of size 7 with capacity 12 —
normalized (7/12 ×4). No two items share a bin, so every nonempty pattern
is a singleton and LP = OPT = 4, although the total volume is only 7/3. -/
def instB2 : Fin 4 → ℕ := fun i => ([7, 7, 7, 7] : List ℕ).getD i 0

theorem instB2_le : ∀ i, instB2 i ≤ 12 := by decide

/-- Checkpoint (b), instance I₃: sizes (3,3,2,2,2) with capacity 6 —
normalized (1/2, 1/2, 1/3, 1/3, 1/3). The two obvious bins are both exactly
full and LP = OPT = 2. -/
def instB3 : Fin 5 → ℕ := fun i => ([3, 3, 2, 2, 2] : List ℕ).getD i 0

theorem instB3_le : ∀ i, instB3 i ≤ 6 := by decide

/-- Checkpoint (c): a smallest-known non-IRUP instance, from
Kartak–Kurz–Ripatti–Scheithauer (2015), Table 1 — item sizes
(4,6,6,9,16,29,32,37,40,62) with capacity 81. The configuration LP has value
exactly 3, but no 3-bin packing exists, so OPT = 4 = ⌈LP⌉ + 1: the modified
round-up bound is tight on this instance (and every instance with at most 9
items is known to have IRUP). -/
def instC : Fin 10 → ℕ := fun i => ([4, 6, 6, 9, 16, 29, 32, 37, 40, 62] : List ℕ).getD i 0

theorem instC_le : ∀ i, instC i ≤ 81 := by decide

/- The kernel recursion limit and elaborator heartbeat limit are raised so
that `decide` can enumerate the assignments and patterns of the checkpoint
instances (the `¬ PacksIn instC 81 3` check enumerates 3^10 assignments).
These lines are part of the fixed zone. -/
set_option maxRecDepth 1000000
set_option maxHeartbeats 8000000

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

/-! ## Checkpoint zone: the conjecture, its negation, and three special cases -/

/-- **The MIRUP conjecture.** A complete proof of this theorem scores full
credit: for every bin packing instance (positive integer item sizes not
exceeding the integer bin capacity), the integer optimum is at most the
ceiling of the configuration LP value plus 1. -/
theorem conj : ∀ {n : ℕ} (l : Fin n → ℕ) (L : ℕ) (hpos : ∀ i, 0 < l i)
    (hle : ∀ i, l i ≤ L), optNumber l L hle ≤ Nat.ceil (lpVal l L) + 1 := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

/-- **The negated conjecture.** A complete proof of this theorem also scores
full credit: exhibiting an instance that needs ⌈LP⌉ + 2 bins resolves the
conjecture in the negative. -/
theorem refuted : ¬ ∀ {n : ℕ} (l : Fin n → ℕ) (L : ℕ) (hpos : ∀ i, 0 < l i)
    (hle : ∀ i, l i ≤ L), optNumber l L hle ≤ Nat.ceil (lpVal l L) + 1 := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

end BinPackingMIRUP
