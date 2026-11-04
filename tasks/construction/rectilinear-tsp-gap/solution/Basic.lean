import Mathlib

set_option maxRecDepth 2000000
set_option maxHeartbeats 0
set_option synthInstance.maxSize 2048

/-!
# Rectilinear TSP subtour-LP integrality gap — certificate definition layer (open task)

This file defines, inside Lean 4 + mathlib, the machine-checkable certificate
format for **lower bounds on the integrality gap of the subtour-elimination LP**
(Held–Karp relaxation) of the **rectilinear (L1 / Manhattan) traveling salesman
problem** on an explicit finite point set:

* **instance**: `n` distinct integer points in the plane (`PointsDistinct`).
  Rational point sets scale to integer ones (multiply all coordinates by a
  common denominator) without changing any distance ratio, hence without
  changing the gap. The cost matrix is the exact L1 distance `l1Cost`; the
  triangle inequality comes for free (`metricCost_l1`, proved in this layer),
  so the instance is pinned down by the raw points alone — exactly as in the
  solver sibling task `rectilinear-tsp-gap`, whose checker parses the points
  as exact rationals (`fractions.Fraction`) and builds the same L1 distance
  matrix with exact arithmetic;
* **LP side**: a rational feasible point `x = y/D` of the subtour LP certifies
  `OPT_LP ≤ c·x` (the LP is a minimization problem; feasibility is checked
  constraint by constraint: degree `2` per vertex, one cut per nonempty proper
  subset, `0 ≤ x ≤ 1`);
* **tour side**: a Held–Karp *potential table* `W` (the dual of the usual DP)
  certifies `OPT_tour ≥ T`: every tour costs at least `T`;
* **assembly**: `gap = OPT_tour / OPT_LP ≥ T / (c·x) ≥ α`, packaged as
  `GapBound n px py α` together with the size range and the point-set premise.

Everything is computed over `ℕ`/`ℤ`/`ℚ` (no floats), and the certificate
checks are finite computations: `decide` for the small ones, `native_decide`
for the large finite enumerations (its trust axioms `Lean.ofReduceBool` /
`Lean.trustCompiler` are whitelisted by the verifier). The tour/LP/potential
machinery is adapted from the metric-TSP certificate layer of
`tsp-gap-lean-open`; on the L1 metric of the point set the two problems
coincide.

The definition layer ends at `-- END OF FIXED PART`; below it the solver
provides its own instance, witnesses and proofs behind the fixed interface
names `certN`, `certPX`, `certPY`, `claimedAlpha`, `main`.
-/
namespace RectTSPGap

variable {n : ℕ} [NeZero n]

/-! ## Basic definitions -/

/-- Lookup in a matrix stored as a list of rows. -/
def matGet (M : List (List ℕ)) (i j : ℕ) : ℕ := (M.getD i []).getD j 0

/-- A tour is an ordering of all vertices starting at vertex `0`
(every cyclic permutation has a unique representative of this form). -/
def IsTour (l : List (Fin n)) : Prop := l.Nodup ∧ l.length = n ∧ l.head? = some 0

/-- Cost of walking from `a` along the list (arc costs of consecutive pairs). -/
def segCost (cost : Fin n → Fin n → ℕ) (a : Fin n) : List (Fin n) → ℕ
  | [] => 0
  | b :: l => cost a b + segCost cost b l

/-- The last vertex of `a :: p`. -/
def lastOf (a : Fin n) (p : List (Fin n)) : Fin n := (a :: p).getLast (by simp)

/-- Total cost of the cyclic tour described by a list. -/
def tourCost (cost : Fin n → Fin n → ℕ) : List (Fin n) → ℕ
  | [] => 0
  | a :: t => segCost cost a t + cost (lastOf a t) 0

/-- The visited-set bitmask of a list of vertices. -/
def maskOfList (l : List (Fin n)) : ℕ := l.foldl (fun m v => m ||| 2 ^ v.val) 0

/-! ## Bitmask lemmas -/

lemma testBit_foldLor (init : ℕ) (l : List (Fin n)) (j : ℕ) :
    (l.foldl (fun m v => m ||| 2 ^ v.val) init).testBit j =
      (init.testBit j || l.any (fun v => decide (v.val = j))) := by
  induction l generalizing init with
  | nil => simp
  | cons a l ih =>
    simp only [List.foldl_cons, List.any_cons]
    rw [ih, Nat.testBit_or, Nat.testBit_two_pow, Bool.or_assoc]

@[simp] lemma testBit_maskOfList (l : List (Fin n)) (j : ℕ) :
    (maskOfList l).testBit j = l.any (fun v => decide (v.val = j)) := by
  simp [maskOfList, testBit_foldLor]

lemma testBit_maskOfList_mem {v : Fin n} {l : List (Fin n)} (h : v ∈ l) :
    (maskOfList l).testBit v.val = true := by
  rw [testBit_maskOfList, List.any_eq_true]
  exact ⟨v, h, by simp⟩

lemma mem_of_testBit_maskOfList {l : List (Fin n)} {v : Fin n}
    (h : (maskOfList l).testBit v.val = true) : v ∈ l := by
  rw [testBit_maskOfList, List.any_eq_true] at h
  obtain ⟨w, hw, hww⟩ := h
  rw [decide_eq_true_eq] at hww
  exact Fin.ext hww ▸ hw

lemma lt_of_testBit_maskOfList {l : List (Fin n)} {j : ℕ}
    (h : (maskOfList l).testBit j = true) : j < n := by
  rw [testBit_maskOfList, List.any_eq_true] at h
  obtain ⟨v, -, hv⟩ := h
  rw [decide_eq_true_eq] at hv
  exact hv ▸ v.isLt

lemma maskOfList_lt (l : List (Fin n)) : maskOfList l < 2 ^ n := by
  by_cases h : maskOfList l = 0
  · simp [h]
  · rw [← Nat.log2_lt h]
    exact lt_of_testBit_maskOfList (Nat.testBit_log2 h)

lemma xor_lor_two_pow {m : ℕ} {j : ℕ} (h : m.testBit j = false) :
    (m ||| 2 ^ j) ^^^ 2 ^ j = m := by
  apply Nat.eq_of_testBit_eq
  intro i
  by_cases hij : i = j
  · subst hij
    simp [Nat.testBit_xor, Nat.testBit_two_pow, h]
  · have hji : j ≠ i := fun e => hij e.symm
    simp [Nat.testBit_xor, Nat.testBit_or, Nat.testBit_two_pow, hji]

/-! ## Path-cost lemmas -/

@[simp] lemma lastOf_nil (a : Fin n) : lastOf a [] = a := by simp [lastOf]

lemma lastOf_cons (a b : Fin n) (p : List (Fin n)) : lastOf a (b :: p) = lastOf b p := by
  simp [lastOf, List.getLast_cons_cons]

lemma segCost_append (cost : Fin n → Fin n → ℕ) (a : Fin n) (p q : List (Fin n)) :
    segCost cost a (p ++ q) = segCost cost a p + segCost cost (lastOf a p) q := by
  induction p generalizing a with
  | nil => simp [segCost]
  | cons b p ih =>
    simp only [List.cons_append, segCost, ih, lastOf_cons, Nat.add_assoc]

/-! ## The potential (dual Held–Karp) certificate -/

/-- The key induction: any path starting at `0` through distinct vertices costs at
least the potential of its visited set. -/
lemma pot_inv (cost : Fin n → Fin n → ℕ) (W : ℕ → Fin n → ℕ)
    (hbase : W 1 0 = 0)
    (hstep : ∀ mask : ℕ, mask < 2 ^ n → mask.testBit 0 = true →
      ∀ j i : Fin n, j ≠ 0 → i ≠ j → mask.testBit j.val = true →
        mask.testBit i.val = true →
        W mask j ≤ W (mask ^^^ (2 ^ j.val)) i + cost i j)
    (t : List (Fin n)) (hnd : (0 :: t).Nodup) :
    W (maskOfList (0 :: t)) (lastOf 0 t) ≤ segCost cost 0 t := by
  induction t using List.reverseRecOn with
  | nil =>
    have h : maskOfList (0 :: ([] : List (Fin n))) = 1 := by simp [maskOfList]
    simp [h, segCost, hbase]
  | append_singleton p u ih =>
    rw [← List.cons_append] at hnd ⊢
    have hnd' : (0 :: p).Nodup := (List.nodup_append.mp hnd).1
    have hu_notin : u ∉ (0 :: p) := by
      have hdis := (List.nodup_append.mp hnd).2.2
      intro hu
      exact hdis u hu u (List.mem_singleton_self u) rfl
    have hu0 : u ≠ 0 := fun h => hu_notin (h ▸ by simp)
    have ih' := ih hnd'
    set m := maskOfList (0 :: p) with hm
    have hmask : maskOfList ((0 :: p) ++ [u]) = m ||| 2 ^ u.val := by
      simp [hm, maskOfList, List.foldl_append]
    have hmu : m.testBit u.val = false := by
      rw [Bool.eq_false_iff]
      exact fun h => hu_notin (mem_of_testBit_maskOfList h)
    have hxor : (m ||| 2 ^ u.val) ^^^ 2 ^ u.val = m :=
      xor_lor_two_pow hmu
    have hm0 : m.testBit 0 = true := by
      have h := testBit_maskOfList_mem (show (0 : Fin n) ∈ (0 :: p) by simp)
      simpa using h
    have hilt : m ||| 2 ^ u.val < 2 ^ n := by
      rw [← hmask]; exact maskOfList_lt _
    have hlast_mem : lastOf 0 p ∈ (0 :: p) := by
      simp [lastOf, List.getLast_mem]
    have hstep' := hstep (m ||| 2 ^ u.val) hilt
      (by rw [Nat.testBit_or]; simp [hm0])
      u (lastOf 0 p) hu0
      (fun h => hu_notin (h ▸ hlast_mem))
      (by rw [Nat.testBit_or, Nat.testBit_two_pow_self]; simp)
      (by rw [Nat.testBit_or, hm, testBit_maskOfList_mem hlast_mem]; simp)
    rw [hxor] at hstep'
    have hlast : lastOf 0 (p ++ [u]) = u := by
      simp [lastOf, List.cons_append]
    rw [hmask, hlast, segCost_append]
    have hseg : segCost cost (lastOf 0 p) [u] = cost (lastOf 0 p) u := by simp [segCost]
    rw [hseg]
    exact le_trans hstep' (Nat.add_le_add_right ih' _)

/-- A potential table satisfying the Held–Karp inequalities lower-bounds every tour. -/
theorem tour_lb_of_potOk (hn : 2 ≤ n) (cost : Fin n → Fin n → ℕ) (W : ℕ → Fin n → ℕ)
    (T : ℕ)
    (hbase : W 1 0 = 0)
    (hstep : ∀ mask : ℕ, mask < 2 ^ n → mask.testBit 0 = true →
      ∀ j i : Fin n, j ≠ 0 → i ≠ j → mask.testBit j.val = true →
        mask.testBit i.val = true →
        W mask j ≤ W (mask ^^^ (2 ^ j.val)) i + cost i j)
    (hT : ∀ j : Fin n, j ≠ 0 → T ≤ W (2 ^ n - 1) j + cost j 0)
    (l : List (Fin n)) (hl : IsTour l) : T ≤ tourCost cost l := by
  obtain ⟨hnd, hlen, hhead⟩ := hl
  have hcomplete : ∀ v : Fin n, v ∈ l := by
    intro v
    have hcard : l.toFinset.card = Fintype.card (Fin n) := by
      rw [List.toFinset_card_of_nodup hnd, hlen, Fintype.card_fin]
    have huniv : l.toFinset = Finset.univ := Finset.eq_univ_of_card _ hcard
    have hv : v ∈ l.toFinset := by rw [huniv]; exact Finset.mem_univ v
    exact List.mem_toFinset.mp hv
  have hfull : maskOfList l = 2 ^ n - 1 := by
    apply Nat.eq_of_testBit_eq
    intro i
    rw [Nat.testBit_two_pow_sub_one]
    by_cases hi : i < n
    · rw [decide_eq_true hi]
      exact testBit_maskOfList_mem (hcomplete ⟨i, hi⟩)
    · have hfalse : (maskOfList l).testBit i = false := by
        rw [Bool.eq_false_iff]
        exact fun h => hi (lt_of_testBit_maskOfList h)
      rw [hfalse, decide_eq_false hi]
  have hlne : l ≠ [] := by
    intro h; subst h; simp at hhead
  obtain ⟨a, t, rfl⟩ := List.exists_cons_of_ne_nil hlne
  simp only [List.head?_cons] at hhead
  have ha : a = 0 := Option.some_injective _ hhead
  subst ha
  have htlen : t.length = n - 1 := by
    rw [List.length_cons] at hlen; omega
  have htne : t ≠ [] := by
    intro h; subst h; simp at htlen; omega
  have hlast_ne : lastOf 0 t ≠ 0 := by
    have hmem : lastOf 0 t ∈ t := by
      obtain ⟨b, t', rfl⟩ := List.exists_cons_of_ne_nil htne
      rw [lastOf_cons]
      simp [lastOf, List.getLast_mem]
    have h0notin : (0 : Fin n) ∉ t := (List.nodup_cons.mp hnd).1
    intro h
    exact h0notin (h ▸ hmem)
  have hpot := pot_inv cost W hbase hstep t hnd
  have hT' := hT (lastOf 0 t) hlast_ne
  rw [← hfull] at hT'
  exact le_trans hT' (Nat.add_le_add_right hpot _)

/-! ## The metric premise -/

/-- A finite integer metric: symmetric, zero diagonal, positive off-diagonal,
and the triangle inequality. These are exactly the shortest-path cost matrices
of connected integer-weighted graphs (in particular of unweighted support
graphs) — the "metric closure" premise of the gap literature. Rational
metrics scale to integer ones without changing the gap. -/
def MetricCost (cost : Fin n → Fin n → ℕ) : Prop :=
  (∀ u, cost u u = 0) ∧
  (∀ u v, cost u v = cost v u) ∧
  (∀ u v, u ≠ v → 0 < cost u v) ∧
  (∀ u v w, cost u w ≤ cost u v + cost v w)

/-! ## The rectilinear instance layer (integer point sets) -/

/-- The point-set premise: all `n` points are pairwise distinct. This is the
only mathematical premise the solver sibling checks on the raw points (its
`|x|, |y| ≤ 10^6` bound is an input-format bound: the gap is scale-invariant,
so it can be—and is here—dropped without changing the problem). The triangle
inequality comes for free for the L1 metric (`metricCost_l1` below), exactly
as in the sibling's checker ("submit raw points, not a distance matrix"). -/
@[reducible] def PointsDistinct (px py : Fin n → ℤ) : Prop :=
  ∀ u v : Fin n, px u = px v → py u = py v → u = v

/-- The exact L1 (Manhattan) distance between two integer points,
`|x_u − x_v| + |y_u − y_v|` as a natural number. -/
def l1Cost (px py : Fin n → ℤ) (u v : Fin n) : ℕ :=
  (px u - px v).natAbs + (py u - py v).natAbs

theorem l1Cost_diag (px py : Fin n → ℤ) (u : Fin n) : l1Cost px py u u = 0 := by
  simp [l1Cost]

theorem l1Cost_symm (px py : Fin n → ℤ) (u v : Fin n) :
    l1Cost px py u v = l1Cost px py v u := by
  have hx : px u - px v = -(px v - px u) := by ring
  have hy : py u - py v = -(py v - py u) := by ring
  simp only [l1Cost, hx, hy, Int.natAbs_neg]

theorem l1Cost_triangle (px py : Fin n → ℤ) (u v w : Fin n) :
    l1Cost px py u w ≤ l1Cost px py u v + l1Cost px py v w := by
  have hx : px u - px w = (px u - px v) + (px v - px w) := by ring
  have hy : py u - py w = (py u - py v) + (py v - py w) := by ring
  have h1 := Int.natAbs_add_le (px u - px v) (px v - px w)
  have h2 := Int.natAbs_add_le (py u - py v) (py v - py w)
  unfold l1Cost
  rw [hx, hy]
  omega

theorem l1Cost_pos (px py : Fin n → ℤ) (hd : PointsDistinct px py)
    (u v : Fin n) (huv : u ≠ v) : 0 < l1Cost px py u v := by
  have hne : px u ≠ px v ∨ py u ≠ py v := by
    by_contra h
    push_neg at h
    exact huv (hd u v h.1 h.2)
  unfold l1Cost
  rcases hne with h | h
  · have hx : 0 < (px u - px v).natAbs := Int.natAbs_pos.mpr (sub_ne_zero.mpr h)
    omega
  · have hy : 0 < (py u - py v).natAbs := Int.natAbs_pos.mpr (sub_ne_zero.mpr h)
    omega

/-- The L1 cost of any distinct integer point set is a finite metric: the
"metric closure" premise of the gap literature comes for free for rectilinear
instances (the solver sibling relies on the same fact when it submits raw
points instead of a distance matrix). -/
theorem metricCost_l1 (px py : Fin n → ℤ) (hd : PointsDistinct px py) :
    MetricCost (l1Cost px py) :=
  ⟨l1Cost_diag px py, l1Cost_symm px py, l1Cost_pos px py hd, l1Cost_triangle px py⟩

/-! ## The LP side (symmetric / metric subtour-elimination LP) -/

/-- A feasible point of the subtour-elimination LP for the metric TSP, with
edge variables written as a symmetric matrix over ordered pairs: degree
exactly `2` at every vertex, every proper nonempty cut carries at least `2`,
entries in `[0, 1]`, no self-loops. Cuts are indexed by bitmasks. -/
def LPFeasible (x : Fin n → Fin n → ℚ) : Prop :=
  (∀ v, ∑ u, x v u = 2) ∧
  (∀ u v, 0 ≤ x u v) ∧
  (∀ u v, x u v ≤ 1) ∧
  (∀ u v, x u v = x v u) ∧
  (∀ u, x u u = 0) ∧
  ∀ mask : ℕ, mask < 2 ^ n → mask ≠ 0 → mask ≠ 2 ^ n - 1 →
    2 ≤ ∑ u : Fin n, ∑ v : Fin n,
      if mask.testBit u.val ∧ ¬ mask.testBit v.val then x u v else 0

/-- The LP objective value of a point: each undirected edge is counted once,
which in the ordered-pair representation is half of the ordered sum. -/
def LPValue (cost : Fin n → Fin n → ℕ) (x : Fin n → Fin n → ℚ) : ℚ :=
  (∑ u, ∑ v, (cost u v : ℚ) * x u v) / 2

/-- The packaged gap lower bound: an LP-feasible point of value `U` and a tour
lower bound `T` with `α * U ≤ T` certify `OPT_tour / OPT_LP ≥ α`, because
`OPT_LP ≤ U` (feasible point of a minimization LP) and `OPT_tour ≥ T`. -/
def GapLB (cost : Fin n → Fin n → ℕ) (α : ℚ) : Prop :=
  ∃ x : Fin n → Fin n → ℚ, LPFeasible x ∧ ∃ T : ℕ,
    (∀ l, IsTour l → T ≤ tourCost cost l) ∧ α * LPValue cost x ≤ (T : ℚ)

/-- The full certificate statement for this task: an instance of `m` distinct
integer points in the plane (rational point sets scale to integers without
changing the gap), in the admitted size range, whose rectilinear subtour-LP
integrality gap is at least `α`. Only `11 ≤ m ≤ 16` counts for the milestones;
smaller instances serve as sanity checks (collinear equispaced points have gap
exactly `1`, the scoring baseline). `metricCost_l1` turns the distinctness
premise into the metric premise of the gap literature. -/
def GapBound (m : ℕ) [NeZero m] (px py : Fin m → ℤ) (α : ℚ) : Prop :=
  2 ≤ m ∧ m ≤ 16 ∧ PointsDistinct px py ∧ GapLB (l1Cost px py) α

/-- Assembly: from a scaled integer LP certificate `y/D` (symmetric), a
potential table `W` and the integer arithmetic `p * (c·y) ≤ q * (2 * (T * D))`
(where `α = p/q` and `c·y` is the ordered-pair sum), conclude the gap lower
bound: `α · (c·x) = (p/q) · ((c·y)/(2D)) ≤ T ≤ OPT_tour`. -/
theorem gapLB_of_cert (hn : 2 ≤ n) (cost : Fin n → Fin n → ℕ) (W : ℕ → Fin n → ℕ)
    (y : Fin n → Fin n → ℕ) (D T : ℕ) (hD : 0 < D) (α : ℚ)
    (p q : ℕ) (hq : 0 < q) (hαpq : α = (p : ℚ) / q)
    (hbase : W 1 0 = 0)
    (hstep : ∀ mask : ℕ, mask < 2 ^ n → mask.testBit 0 = true →
      ∀ j i : Fin n, j ≠ 0 → i ≠ j → mask.testBit j.val = true →
        mask.testBit i.val = true →
        W mask j ≤ W (mask ^^^ (2 ^ j.val)) i + cost i j)
    (hT : ∀ j : Fin n, j ≠ 0 → T ≤ W (2 ^ n - 1) j + cost j 0)
    (hysym : ∀ u v : Fin n, y u v = y v u)
    (hydiag : ∀ u : Fin n, y u u = 0)
    (hy1 : ∀ u v : Fin n, y u v ≤ D)
    (hdeg : ∀ v : Fin n, ∑ u : Fin n, y v u = 2 * D)
    (hcut : ∀ mask : ℕ, mask < 2 ^ n → mask ≠ 0 → mask ≠ 2 ^ n - 1 →
      2 * D ≤ ∑ u : Fin n, ∑ v : Fin n,
        if mask.testBit u.val ∧ ¬ mask.testBit v.val then y u v else 0)
    (hα : p * (∑ u : Fin n, ∑ v : Fin n, cost u v * y u v) ≤ q * (2 * (T * D))) :
    GapLB cost α := by
  refine ⟨fun u v => (y u v : ℚ) / D, ⟨?_, ?_, ?_, ?_, ?_, ?_⟩, T, ?_, ?_⟩
  · intro v
    show (∑ u : Fin n, (y v u : ℚ) / D) = 2
    rw [← Finset.sum_div, ← Nat.cast_sum, hdeg v]
    have hDq : (D : ℚ) ≠ 0 := by exact_mod_cast hD.ne'
    rw [Nat.cast_mul, Nat.cast_two]
    exact mul_div_cancel_right₀ 2 hDq
  · intro u v
    exact div_nonneg (Nat.cast_nonneg _) (Nat.cast_nonneg _)
  · intro u v
    have hD0 : (0 : ℚ) < D := by exact_mod_cast hD
    rw [div_le_one hD0]
    exact_mod_cast hy1 u v
  · intro u v
    show (y u v : ℚ) / (D : ℚ) = (y v u : ℚ) / D
    rw [hysym u v]
  · intro u
    show (y u u : ℚ) / (D : ℚ) = 0
    rw [hydiag u, Nat.cast_zero, zero_div]
  · intro mask hmask h0 hfull
    have h1 : (∑ u : Fin n, ∑ v : Fin n,
          if mask.testBit u.val ∧ ¬ mask.testBit v.val then (y u v : ℚ) / D else 0)
        = (∑ u : Fin n, ∑ v : Fin n,
          if mask.testBit u.val ∧ ¬ mask.testBit v.val then (y u v : ℚ) else 0) / D := by
      rw [Finset.sum_div]
      apply Finset.sum_congr rfl; intro u _
      rw [Finset.sum_div]
      apply Finset.sum_congr rfl; intro v _
      rw [apply_ite (· / (D : ℚ)), zero_div]
    have h2 : (∑ u : Fin n, ∑ v : Fin n,
          if mask.testBit u.val ∧ ¬ mask.testBit v.val then (y u v : ℚ) else 0)
        = ((∑ u : Fin n, ∑ v : Fin n,
          if mask.testBit u.val ∧ ¬ mask.testBit v.val then y u v else 0 : ℕ) : ℚ) := by
      rw [Nat.cast_sum]
      apply Finset.sum_congr rfl; intro u _
      rw [Nat.cast_sum]
      apply Finset.sum_congr rfl; intro v _
      split <;> simp
    rw [h1, h2]
    have hcut' := hcut mask hmask h0 hfull
    have hDq : (0 : ℚ) < D := by exact_mod_cast hD
    rw [le_div_iff₀ hDq]
    exact_mod_cast hcut'
  · intro l hl
    exact tour_lb_of_potOk hn cost W T hbase hstep hT l hl
  · have hcast : (∑ u : Fin n, ∑ v : Fin n, (cost u v : ℚ) * (y u v : ℚ))
        = ((∑ u : Fin n, ∑ v : Fin n, cost u v * y u v : ℕ) : ℚ) := by
      rw [Nat.cast_sum]; apply Finset.sum_congr rfl; intro u _
      rw [Nat.cast_sum]; apply Finset.sum_congr rfl; intro v _
      rw [Nat.cast_mul]
    have hval : LPValue cost (fun u v => (y u v : ℚ) / D)
        = (((∑ u : Fin n, ∑ v : Fin n, cost u v * y u v : ℕ) : ℚ) / D) / 2 := by
      unfold LPValue
      congr 1
      rw [← hcast, Finset.sum_div]
      apply Finset.sum_congr rfl; intro u _
      rw [Finset.sum_div]
      apply Finset.sum_congr rfl; intro v _
      rw [← mul_div_assoc]
    rw [hval, hαpq, div_div, div_mul_div_comm]
    have hpos : (0 : ℚ) < q * (D * 2) := by
      have hq' : (0 : ℚ) < q := by exact_mod_cast hq
      have hD' : (0 : ℚ) < D := by exact_mod_cast hD
      positivity
    rw [div_le_iff₀ hpos]
    have hα' : (p : ℚ) * ((∑ u : Fin n, ∑ v : Fin n, cost u v * y u v : ℕ) : ℚ)
        ≤ (q : ℚ) * (2 * (T * D)) := by exact_mod_cast hα
    linear_combination hα'

-- END OF FIXED PART — everything below is yours: instance data, certificate
-- tables, and all proofs. Keep the interface names `certN`, `certPX`,
-- `certPY`, `claimedAlpha` and `main` intact (the verifier reads them); the
-- shapes of the other `cert*` definitions may be changed freely (or dropped)
-- as long as `certPX certPY : Fin certN → ℤ` and `main` still typecheck.

/-! ## Certificate: Zhong-family-shaped instance `I²_{2,6,2}` at `n = 16`, scaled by 27 -/

/-- Number of points of the instance. -/
def certN : ℕ := 16

instance : NeZero certN := ⟨by decide⟩

/-- x-coordinates of the point set. -/
def certPXA : Array ℤ :=
  #[0, 10, 17, 27, 3, 6, 9, 12, 15, 18, 21, 24, 0, 10, 17, 27]

/-- y-coordinates of the point set. -/
def certPYA : Array ℤ :=
  #[0, 0, 0, 0, 10, 10, 10, 10, 10, 10, 10, 10, 20, 20, 20, 20]

/-- The x-coordinate function. -/
def certPX (u : Fin certN) : ℤ := certPXA.getD u.val 0

/-- The y-coordinate function. -/
def certPY (u : Fin certN) : ℤ := certPYA.getD u.val 0

/-- LP numerator matrix: the rational LP point is `x = certY / certD`. -/
def certYA : Array (Array ℕ) :=
  #[#[0, 2, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
    #[2, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    #[0, 2, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    #[0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1],
    #[1, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
    #[0, 0, 0, 0, 2, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    #[0, 0, 0, 0, 0, 2, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0],
    #[0, 0, 0, 0, 0, 0, 2, 0, 2, 0, 0, 0, 0, 0, 0, 0],
    #[0, 0, 0, 0, 0, 0, 0, 2, 0, 2, 0, 0, 0, 0, 0, 0],
    #[0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 2, 0, 0, 0, 0, 0],
    #[0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 2, 0, 0, 0, 0],
    #[0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 1],
    #[1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0],
    #[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 2, 0],
    #[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 2],
    #[0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 2, 0]]

/-- The LP numerator as a function. -/
def certY (u v : Fin certN) : ℕ := (certYA.getD u.val #[]).getD v.val 0

/-- The LP denominator. -/
def certD : ℕ := 2

/-- L1 cost on raw indices; agrees with `l1Cost certPX certPY` on `Fin certN`,
used to keep the DP inner loop free of `Fin` bounds proofs. -/
def rawCost (i j : ℕ) : ℕ :=
  (certPXA.getD i 0 - certPXA.getD j 0).natAbs +
    (certPYA.getD i 0 - certPYA.getD j 0).natAbs

/-- The exact Held–Karp DP table, computed inside Lean: for every mask
containing vertex `0` and every `j ≠ 0` in the mask, entry `[mask][j]` is the
minimum cost of a path from `0` visiting exactly `mask` and ending at `j`.
All other entries are set to a large sentinel. -/
def certWArr : Array (Array ℕ) := Id.run do
  let n := certN
  let big := 1000000
  let sz := 2 ^ n
  let mut W : Array (Array ℕ) := Array.replicate sz (Array.replicate n big)
  W := W.set! 1 ((Array.replicate n big).set! 0 0)
  for mask in List.range sz do
    if mask.testBit 0 then
      let mut row := W.getD mask #[]
      for j in List.range n do
        if j != 0 && mask.testBit j then
          let pm := mask ^^^ 2 ^ j
          let prow := W.getD pm #[]
          let mut best := big
          for i in List.range n do
            if pm.testBit i then
              let v := prow.getD i big + rawCost i j
              if v < best then
                best := v
          row := row.set! j best
      W := W.set! mask row
  return W

/-- The potential table as a function. -/
def certW (mask : ℕ) (j : Fin certN) : ℕ := (certWArr.getD mask #[]).getD j.val 1000000

/-- The certified tour lower bound. -/
def certT : ℕ := 142

/-- The claimed gap lower bound. -/
def claimedAlpha : ℚ := 142 / 121

/-- The certificate checks as a single proposition. -/
@[reducible] def certProp : Prop :=
  PointsDistinct certPX certPY ∧
  certW 1 0 = 0 ∧
  (∀ mask : ℕ, mask < 2 ^ certN → mask.testBit 0 = true →
    ∀ j i : Fin certN, j ≠ 0 → i ≠ j → mask.testBit j.val = true →
      mask.testBit i.val = true →
      certW mask j ≤ certW (mask ^^^ 2 ^ j.val) i + l1Cost certPX certPY i j) ∧
  (∀ j : Fin certN, j ≠ 0 → certT ≤ certW (2 ^ certN - 1) j + l1Cost certPX certPY j 0) ∧
  (∀ u v : Fin certN, certY u v = certY v u) ∧
  (∀ u : Fin certN, certY u u = 0) ∧
  (∀ u v : Fin certN, certY u v ≤ certD) ∧
  (∀ v : Fin certN, ∑ u : Fin certN, certY v u = 2 * certD) ∧
  (∀ mask : ℕ, mask < 2 ^ certN → mask ≠ 0 → mask ≠ 2 ^ certN - 1 →
    2 * certD ≤ ∑ u : Fin certN, ∑ v : Fin certN,
      if mask.testBit u.val ∧ ¬ mask.testBit v.val then certY u v else 0) ∧
  142 * (∑ u : Fin certN, ∑ v : Fin certN, l1Cost certPX certPY u v * certY u v) ≤
    121 * (2 * (certT * certD))

/-- The decision procedure for `certProp`, as a constant so the interpreter
can evaluate it (the reflection mechanism behind `native_decide`, used
directly so the trust axioms stay at the whitelisted
`Lean.ofReduceBool`/`Lean.trustCompiler`). -/
def certDec : Bool := decide certProp

set_option linter.deprecated false in
/-- All finite checks of the certificate: distinctness of the points, the
Held–Karp potential inequalities over all masks, the tour lower bound on the
final row, feasibility of the LP point (symmetry, diagonal, bounds, degrees,
all proper cuts) and the closing integer arithmetic. -/
theorem certChecks : certProp :=
  of_decide_eq_true (Lean.ofReduceBool certDec true rfl)

/-- Main theorem: the instance `(certPX, certPY)` on `certN` points has
subtour-LP integrality gap at least `claimedAlpha`. -/
theorem main : GapBound certN certPX certPY claimedAlpha := by
  obtain ⟨hdist, hbase, hstep, hT, hysym, hydiag, hy1, hdeg, hcut, hα⟩ := certChecks
  exact ⟨by decide, by decide, hdist,
    gapLB_of_cert (by decide) _ certW certY certD certT (by decide) _
      142 121 (by decide) (by norm_num [claimedAlpha]) hbase hstep hT hysym hydiag hy1 hdeg hcut hα⟩

end RectTSPGap
