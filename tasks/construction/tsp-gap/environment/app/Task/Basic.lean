import Mathlib

set_option maxRecDepth 2000000
set_option maxHeartbeats 0
set_option synthInstance.maxSize 2048

/-!
# Metric TSP subtour-LP integrality gap — certificate definition layer (open task)

This file defines, inside Lean 4 + mathlib, the machine-checkable certificate
format for **lower bounds on the integrality gap of the subtour-elimination LP**
(Held–Karp relaxation) of the **metric traveling salesman problem** on an
explicit finite instance:

* **instance**: a symmetric integer cost matrix `cost` satisfying the triangle
  inequality (`MetricCost`) — i.e. the shortest-path **metric closure** of some
  integer-weighted support graph (rational metrics scale to integer ones
  without changing the gap);
* **LP side**: a rational feasible point `x = y/D` of the subtour LP certifies
  `OPT_LP ≤ c·x` (the LP is a minimization problem; feasibility is checked
  constraint by constraint: degree `2` per vertex, one cut per nonempty proper
  subset, `0 ≤ x ≤ 1`);
* **tour side**: a Held–Karp *potential table* `W` (the dual of the usual DP)
  certifies `OPT_tour ≥ T`: every tour costs at least `T`;
* **assembly**: `gap = OPT_tour / OPT_LP ≥ T / (c·x) ≥ α`, packaged as
  `GapBound n cost α` together with the size range and the metric premise.

Everything is computed over `ℕ`/`ℚ` (no floats), and the certificate checks
are finite `decide` computations. This layer is adapted from the ATSP
certificate layer of `c5-small-gap-lean` to the symmetric (metric) case.

The definition layer ends at `-- END OF FIXED PART`; below it the solver
provides its own instance, witnesses and proofs behind the fixed interface
names `certN`, `certCost`, `claimedAlpha`, `main`.
-/
namespace TSPGap

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

/-- The full certificate statement for this task: an instance on `m` vertices
in the admitted size range, satisfying the metric premise, whose subtour-LP
integrality gap is at least `α`. Only `15 ≤ m ≤ 20` is evaluated;
smaller instances serve as sanity checks (e.g. the Petersen graph at
`m = 10`, gap exactly `11/10`). -/
def GapBound (m : ℕ) [NeZero m] (cost : Fin m → Fin m → ℕ) (α : ℚ) : Prop :=
  2 ≤ m ∧ m ≤ 20 ∧ MetricCost cost ∧ GapLB cost α

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
-- tables, and all proofs. Keep the interface names `certN`, `certCost`,
-- `claimedAlpha` and `main` intact (the verifier reads them); the shapes of
-- the other `cert*` definitions may be changed freely (or dropped) as long as
-- `certCost : Fin certN → Fin certN → ℕ` and `main` still typecheck.

/-! ## Certificate interface (REPLACE the data, PROVE the theorem) -/

/-- Number of vertices of your instance (the theorem requires `2 ≤ certN ≤ 20`;
only `15 ≤ certN ≤ 20` is evaluated). -/
def certN : ℕ := 3

instance : NeZero certN := ⟨by decide⟩

/-- Cost matrix of the instance: a symmetric integer metric — the
shortest-path metric closure of your support graph. Row `i`, column `j`.
The placeholder is the unit triangle on 3 vertices. -/
def certCostM : List (List ℕ) :=
  [[0, 1, 1],
   [1, 0, 1],
   [1, 1, 0]]

/-- The cost function. -/
def certCost : Fin certN → Fin certN → ℕ := fun u v => matGet certCostM u.val v.val

/-- LP certificate numerator: the rational point is `x = certY / certD`.
The placeholder puts `x = 1` on every edge of the triangle. -/
def certYM : List (List ℕ) :=
  [[0, 1, 1],
   [1, 0, 1],
   [1, 1, 0]]

/-- The LP numerator as a function. -/
def certY : Fin certN → Fin certN → ℕ := fun u v => matGet certYM u.val v.val

/-- The LP denominator. -/
def certD : ℕ := 1

/-- Held–Karp potential table, one row of `certN` entries per mask in
`[0, 2 ^ certN)`; entries at states never used by the potential inequalities
are set to a large sentinel. The placeholder certifies `OPT_tour ≥ 3` on the
unit triangle. -/
def certWM : List (List ℕ) :=
  [[1000000, 1000000, 1000000],
   [0, 1000000, 1000000],
   [1000000, 1000000, 1000000],
   [1000000, 1, 1000000],
   [1000000, 1000000, 1000000],
   [1000000, 1000000, 1],
   [1000000, 1000000, 1000000],
   [1000000, 2, 2]]

/-- The potential table as a function. -/
def certW : ℕ → Fin certN → ℕ := fun mask j => matGet certWM mask j.val

/-- The certified tour lower bound. -/
def certT : ℕ := 3

/-- The gap lower bound you claim to prove for your instance. The verifier
evaluates this constant against the published literature frontier; it is sound
only because `main` proves `GapBound certN certCost claimedAlpha`. -/
def claimedAlpha : ℚ := 1

/-- Main theorem: the instance `certCost` on `certN` vertices is a metric
instance in the admitted size range whose subtour-LP integrality gap is at
least `claimedAlpha`. Replace the `sorry` by your certificate assembly
(typically via `gapLB_of_cert` and finite `decide` checks). -/
theorem main : GapBound certN certCost claimedAlpha := by
  sorry

end TSPGap
