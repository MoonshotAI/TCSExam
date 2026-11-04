/-
Statement layer for the optimal asymptotic competitive ratio R* of
one-dimensional online bin packing (open problem: the true value of R* is
bracketed in [1.54278, 1.57829] since 2018).

Items of sizes in (0, 1] arrive one by one and each must be assigned
irrevocably to a bin of capacity 1 before the next item arrives; the goal
is to minimize the number of bins. An online algorithm A has asymptotic
competitive ratio at most r if A(I) ≤ r·OPT(I) + C for some constant C and
every instance I; R* is the infimum of r over all online algorithms.

  - Upper bound (best known algorithm): Balogh–Békési–Dósa–Epstein–Levin,
    *A New and Improved Algorithm for Online Bin Packing*, ESA 2018
    (LIPIcs 112, 5:1–5:14, DOI 10.4230/LIPIcs.ESA.2018.5): R* ≤ 1.57829.
  - Lower bound (best known impossibility): the same authors, *A New Lower
    Bound for Classic Online Bin Packing*, Algorithmica 83(7):2047–2062
    (2021), DOI 10.1007/s00453-021-00818-7: 1.54278 < R*.

This file is the task's definition zone plus slot zone:
- The definition zone defines valid instances (real item-size lists with
  sizes in (0, 1]), feasible packings and the offline optimum
  `optNumber` (a `Nat` infimum, attained on valid instances), online
  algorithms `OnlineAlg` (prefix-consistent, always-feasible bin
  assignments), the asymptotic ratio bound `AsympBound`, the achievable
  ratio set `ratioSet` and `RStar : ℝ := sInf ratioSet`, the concrete
  algorithms Next Fit and First Fit as `OnlineAlg` instances (with their
  invariants fully proved), and the concrete instances `ones k` and
  `instFFR`. All API lemmas are proved; nothing here is left open.
- The slot zone states the two threshold directions (`conj`: R* ≤ 1.56,
  an upper-bound improvement; `refuted`: ¬ R* ≤ 1.56, a lower-bound
  improvement). Both proof bodies are left blank.

Fidelity notes (see `tests/reference/concept-ledger.md` of the packaged
task):
1. Online algorithms are modeled as prefix-consistent assignment functions
   (`assign : List ℝ → List ℕ` with `prefix_consistent` and `feasible`
   fields), which is equivalent to the decision-function view of the
   literature (past decisions are determined by the item history).
2. The cost of an assignment is the number of bins *opened* (largest bin
   index + 1); for Next Fit / First Fit / harmonic-type algorithms the bin
   indices are contiguous, so this agrees with the used-bin count of the
   literature, and adversary lower bounds are only stronger under this
   accounting.
3. `optNumber` is a `sInf` over natural numbers; on valid instances the
   candidate set is nonempty (`packsIn_self`), so it is the true minimum
   (`optNumber_spec`).
-/

import Mathlib

namespace OnlineBinPacking

/-! ## Instances, packings, and the offline optimum -/

/-- A bin packing instance is valid when every item size lies in `(0, 1]`
(the bin capacity is normalized to 1, as in the literature). -/
def ValidInstance (l : List ℝ) : Prop := ∀ x ∈ l, 0 < x ∧ x ≤ 1

/-- `PacksIn l k`: the items of `l` can be assigned to `k` bins of
capacity 1 (every bin's total size is at most 1). -/
def PacksIn (l : List ℝ) (k : ℕ) : Prop :=
  ∃ f : Fin l.length → Fin k, ∀ b : Fin k,
    ∑ i ∈ Finset.univ.filter (fun i => f i = b), l.get i ≤ 1

/-- The offline optimum `OPT(l)`: the least number of bins the instance
packs into. (`sInf` of a set of natural numbers; for a valid instance the
set is nonempty — `packsIn_self` — so this is the true minimum, see
`optNumber_spec`.) -/
noncomputable def optNumber (l : List ℝ) : ℕ := sInf {k | PacksIn l k}

/-- Every item fits alone in its own bin, so `l.length` bins always
suffice (for a valid instance). -/
theorem packsIn_self {l : List ℝ} (hv : ValidInstance l) : PacksIn l l.length := by
  refine ⟨id, fun b => ?_⟩
  have hset : Finset.univ.filter (fun i => id i = b) = {b} := by
    ext i
    simp
  rw [hset, Finset.sum_singleton]
  exact (hv (l.get b) (List.get_mem _ _)).2

theorem PacksIn.mono {l : List ℝ} {k k' : ℕ} (hle : k ≤ k') (h : PacksIn l k) :
    PacksIn l k' := by
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

/-- The optimum is attained: the instance packs into `optNumber l` bins. -/
theorem optNumber_spec {l : List ℝ} (hv : ValidInstance l) : PacksIn l (optNumber l) :=
  Nat.sInf_mem (s := {k | PacksIn l k}) ⟨l.length, packsIn_self hv⟩

/-- Any packing upper-bounds the optimum. -/
theorem optNumber_le_of_packsIn {l : List ℝ} {k : ℕ} (h : PacksIn l k) :
    optNumber l ≤ k :=
  Nat.sInf_le (s := {k | PacksIn l k}) h

theorem optNumber_le_length {l : List ℝ} (hv : ValidInstance l) :
    optNumber l ≤ l.length :=
  optNumber_le_of_packsIn (packsIn_self hv)

/-- The total item volume lower-bounds every packing. -/
theorem list_sum_le_of_packsIn {l : List ℝ} {k : ℕ} (h : PacksIn l k) :
    l.sum ≤ k := by
  obtain ⟨f, hf⟩ := h
  have h1 : l.sum = ∑ i : Fin l.length, l.get i := by
    conv_lhs => rw [← List.ofFn_get l, List.sum_ofFn]
  rw [h1]
  calc ∑ i : Fin l.length, l.get i
      = ∑ b : Fin k, ∑ i ∈ Finset.univ.filter (fun i => f i = b), l.get i := by
        rw [Finset.sum_fiberwise_eq_sum_filter Finset.univ Finset.univ f (fun i => l.get i)]
        simp
    _ ≤ ∑ _b : Fin k, (1 : ℝ) := Finset.sum_le_sum fun b _ => hf b
    _ = k := by simp

/-- The total item volume lower-bounds the optimum. -/
theorem list_sum_le_optNumber {l : List ℝ} (hv : ValidInstance l) :
    l.sum ≤ optNumber l :=
  list_sum_le_of_packsIn (optNumber_spec hv)

theorem le_optNumber_of_pairwise_incompatible {l : List ℝ} (hv : ValidInstance l)
    (T : Finset (Fin l.length))
    (hT : ∀ i ∈ T, ∀ j ∈ T, i ≠ j → 1 < l.get i + l.get j) :
    T.card ≤ optNumber l := by
  obtain ⟨f, hf⟩ := optNumber_spec hv
  have hinj : Set.InjOn f T := by
    intro i hi j hj hij
    by_contra hne
    have h1 : (1 : ℝ) < l.get i + l.get j := hT i hi j hj hne
    have hsub : ({i, j} : Finset (Fin l.length)) ⊆
        Finset.univ.filter (fun i' => f i' = f i) := by
      intro i' hi'
      simp only [Finset.mem_insert, Finset.mem_singleton] at hi'
      rcases hi' with rfl | rfl
      · exact Finset.mem_filter.mpr ⟨Finset.mem_univ _, rfl⟩
      · exact Finset.mem_filter.mpr ⟨Finset.mem_univ _, hij.symm⟩
    have h2 : l.get i + l.get j ≤ ∑ i' ∈ Finset.univ.filter (fun i' => f i' = f i),
        l.get i' := by
      calc l.get i + l.get j
          = ∑ i' ∈ ({i, j} : Finset (Fin l.length)), l.get i' := by
            rw [Finset.sum_insert (by simp [hne]), Finset.sum_singleton]
        _ ≤ ∑ i' ∈ Finset.univ.filter (fun i' => f i' = f i), l.get i' :=
            Finset.sum_le_sum_of_subset_of_nonneg hsub fun i'' _ _ =>
              (hv _ (List.get_mem _ _)).1.le
    have h3 := hf (f i)
    linarith
  calc T.card ≤ (Finset.univ : Finset (Fin (optNumber l))).card :=
        Finset.card_le_card_of_injOn f (fun _ _ => Finset.mem_univ _) hinj
    _ = optNumber l := by rw [Finset.card_univ, Fintype.card_fin]

/-! ## Online algorithms and the asymptotic competitive ratio -/

structure OnlineAlg where
  assign : List ℝ → List ℕ
  length_eq : ∀ l : List ℝ, (assign l).length = l.length
  prefix_consistent : ∀ {l₁ l₂ : List ℝ}, l₁ <+: l₂ →
    (assign l₂).take l₁.length = assign l₁
  feasible : ∀ l : List ℝ, ValidInstance l → ∀ b : ℕ,
    (∑ i ∈ Finset.univ.filter
      (fun i : Fin l.length => (assign l).get (i.cast (length_eq l).symm) = b), l.get i) ≤ 1

def binOf (A : OnlineAlg) (l : List ℝ) (i : Fin l.length) : ℕ :=
  (A.assign l).get (i.cast (A.length_eq l).symm)

def costOf (asg : List ℕ) : ℕ := asg.toFinset.sup (· + 1)

def algCost (A : OnlineAlg) (l : List ℝ) : ℕ := costOf (A.assign l)

theorem add_one_le_costOf {asg : List ℕ} {x : ℕ} (hx : x ∈ asg) : x + 1 ≤ costOf asg :=
  Finset.le_sup (List.mem_toFinset.mpr hx)

theorem costOf_le {asg : List ℕ} {m : ℕ} (h : ∀ x ∈ asg, x + 1 ≤ m) : costOf asg ≤ m :=
  Finset.sup_le_iff.mpr fun x hx => h x (List.mem_toFinset.mp hx)

theorem card_le_costOf (asg : List ℕ) : asg.toFinset.card ≤ costOf asg := by
  have h2 : asg.toFinset ⊆ Finset.range (costOf asg) := by
    intro x hx
    exact Finset.mem_range.mpr (Nat.lt_of_succ_le (add_one_le_costOf (List.mem_toFinset.mp hx)))
  calc asg.toFinset.card ≤ (Finset.range (costOf asg)).card := Finset.card_le_card h2
    _ = costOf asg := Finset.card_range (costOf asg)

theorem binOf_lt_costOf (A : OnlineAlg) (l : List ℝ) (i : Fin l.length) :
    binOf A l i < costOf (A.assign l) :=
  Nat.lt_of_succ_le (add_one_le_costOf (List.get_mem _ _))

/-- The fiber sums of an assignment, in the two index styles. -/
theorem fiber_sum_univ_eq_range (l : List ℝ) (asg : List ℕ) (hlen : asg.length = l.length)
    (b : ℕ) :
    (∑ i ∈ Finset.univ.filter (fun i : Fin l.length => asg.get (i.cast hlen.symm) = b),
        l.get i)
    = ∑ j ∈ (Finset.range l.length).filter (fun j => asg.getD j 0 = b), l.getD j 0 := by
  apply Finset.sum_bij (fun i _ => i.val)
  · intro i hi
    rw [Finset.mem_filter] at hi
    rw [Finset.mem_filter, Finset.mem_range]
    refine ⟨i.isLt, ?_⟩
    rw [← hi.2]
    exact List.getD_eq_get asg 0 (i.cast hlen.symm)
  · intro i _ j _ hij
    exact Fin.ext hij
  · intro j hj
    rw [Finset.mem_filter, Finset.mem_range] at hj
    obtain ⟨hjl, hjb⟩ := hj
    refine ⟨⟨j, hjl⟩, Finset.mem_filter.mpr ⟨Finset.mem_univ _, ?_⟩, rfl⟩
    have e1 : (⟨j, hjl⟩ : Fin l.length).cast hlen.symm = ⟨j, hlen.symm ▸ hjl⟩ := Fin.ext rfl
    rw [e1, ← hjb]
    exact (List.getD_eq_get asg 0 ⟨j, hlen.symm ▸ hjl⟩).symm
  · intro i _
    exact (List.getD_eq_get l 0 i).symm

theorem packsIn_of_feasible (A : OnlineAlg) (l : List ℝ) (hv : ValidInstance l) :
    PacksIn l (algCost A l) := by
  refine ⟨fun i => ⟨binOf A l i, binOf_lt_costOf A l i⟩, fun b => ?_⟩
  have hcongr : ∀ i : Fin l.length,
      ((⟨binOf A l i, binOf_lt_costOf A l i⟩ : Fin (algCost A l)) = b) ↔ binOf A l i = b.val := by
    intro i
    constructor
    · intro h
      exact congrArg Fin.val h
    · intro h
      exact Fin.ext h
  rw [Finset.filter_congr fun i _ => hcongr i]
  exact A.feasible l hv b.val

theorem optNumber_le_algCost (A : OnlineAlg) (l : List ℝ) (hv : ValidInstance l) :
    optNumber l ≤ algCost A l :=
  optNumber_le_of_packsIn (packsIn_of_feasible A l hv)

/-- `AsympBound A r`: algorithm `A` has asymptotic competitive ratio at
most `r` — there is an additive constant `C` with `A(l) ≤ r · OPT(l) + C`
for every valid instance `l`. This is the standard asymptotic notion of the
literature. -/
def AsympBound (A : OnlineAlg) (r : ℝ) : Prop :=
  ∃ C : ℝ, ∀ l : List ℝ, ValidInstance l → (algCost A l : ℝ) ≤ r * (optNumber l : ℝ) + C

/-- The set of asymptotic competitive ratios achievable by online
algorithms. -/
def ratioSet : Set ℝ := {r : ℝ | ∃ A : OnlineAlg, AsympBound A r}

/-- The optimal asymptotic competitive ratio `R*` of one-dimensional
online bin packing: the infimum of the ratios achievable by online
algorithms. The literature pins it to the interval [1.54278, 1.57829]. -/
noncomputable def RStar : ℝ := sInf ratioSet

/-! ## Next Fit -/

noncomputable def nfStep : List (List ℝ) × List ℕ → ℝ → List (List ℝ) × List ℕ
  | ([], asg), x => ([[x]], asg ++ [0])
  | (bin :: rest, asg), x =>
    if bin.sum + x ≤ 1 then ((bin ++ [x]) :: rest, asg ++ [rest.length])
    else ([x] :: bin :: rest, asg ++ [(bin :: rest).length])

noncomputable def nfAssign (l : List ℝ) : List ℕ := (l.foldl nfStep ([], [])).2

def NFSpec (l : List ℝ) (s : List (List ℝ) × List ℕ) : Prop :=
  s.2.length = l.length
  ∧ (s.1.map List.sum).sum = l.sum
  ∧ (∀ bin ∈ s.1, 0 < bin.sum ∧ bin.sum ≤ 1)
  ∧ (∀ i : ℕ, ∀ h : i + 1 < s.1.length,
      (s.1[i]'(Nat.lt_of_succ_lt h)).sum + (s.1[i+1]'h).sum > 1)
  ∧ (∀ b : ℕ, b < s.1.length →
      (∑ j ∈ (Finset.range l.length).filter (fun j => s.2.getD j 0 = b), l.getD j 0)
        = (s.1.getD (s.1.length - 1 - b) []).sum)
  ∧ (∀ j : ℕ, j < l.length → s.2.getD j 0 < s.1.length)
  ∧ (∀ h : s.2 ≠ [], s.2.getLast h = s.1.length - 1)

theorem nfSpec_nil : NFSpec [] ([], []) := by
  refine ⟨rfl, rfl, ?_, ?_, ?_, ?_, ?_⟩
  · intro bin hbin
    simp at hbin
  · intro i h
    exact absurd h (Nat.not_lt_zero _)
  · intro b hb
    exact absurd hb (Nat.not_lt_zero _)
  · intro j hj
    exact absurd hj (Nat.not_lt_zero _)
  · intro h
    exact absurd rfl h

theorem nfSpec_step {l : List ℝ} {s : List (List ℝ) × List ℕ}
    (hs : NFSpec l s) (hx0 : 0 < x) (hx1 : x ≤ 1) :
    NFSpec (l ++ [x]) (nfStep s x) := by
  obtain ⟨h1, h2, h3, h4, h5, h6, h7⟩ := hs
  cases s with
  | mk bins asg =>
    cases bins with
    | nil =>
      have hl : l = [] := by
        cases l with
        | nil => rfl
        | cons a rest =>
          exfalso
          have h60 := h6 0 (by simp)
          simp at h60
      subst hl
      have hasg : asg = [] := by
        cases asg with
        | nil => rfl
        | cons a rest =>
          exfalso
          simp at h1
      subst hasg
      have e : nfStep (([] : List (List ℝ)), ([] : List ℕ)) x = ([[x]], [0]) := rfl
      rw [e]
      refine ⟨rfl, by simp, ?_, ?_, ?_, ?_, ?_⟩
      · intro bin hbin
        rw [List.mem_singleton] at hbin
        subst hbin
        exact ⟨by simpa using hx0, by simpa using hx1⟩
      · intro i h
        exfalso
        have h' : i + 1 < 1 := h
        omega
      · intro b hb
        have hb0 : b = 0 := by
          have h' : b < 1 := hb
          omega
        subst hb0
        simp only [List.nil_append]
        have hfilter : (Finset.range ([x] : List ℝ).length).filter
            (fun j => ([0] : List ℕ).getD j 0 = 0) = {0} := by
          have hlen : ([x] : List ℝ).length = 1 := rfl
          rw [hlen]
          ext j
          simp only [Finset.mem_filter, Finset.mem_range, Finset.mem_singleton]
          constructor
          · intro hj
            omega
          · intro hj
            rw [hj]
            exact ⟨by norm_num, rfl⟩
        rw [hfilter, Finset.sum_singleton]
        show ([x]).getD 0 0 = (([[x]] : List (List ℝ)).getD 0 []).sum
        rw [List.getD_cons_zero, List.getD_cons_zero]
        simp
      · intro j hj
        have hj0 : j = 0 := by
          have h' : j < 1 := hj
          omega
        subst hj0
        show ([0] : List ℕ).getD 0 0 < ([[x]] : List (List ℝ)).length
        rw [List.getD_cons_zero]
        exact Nat.one_pos
      · intro h
        rfl
    | cons bin rest =>
      by_cases hfit : bin.sum + x ≤ 1
      · have e : nfStep (bin :: rest, asg) x = ((bin ++ [x]) :: rest, asg ++ [rest.length]) := by
          simp only [nfStep, if_pos hfit]
        rw [e]
        have hlen1 : (l ++ [x]).length = l.length + 1 := by simp
        have hnew1 : (asg ++ [rest.length]).getD l.length 0 = rest.length := by
          rw [List.getD_append_right asg [rest.length] 0 l.length (by rw [h1]),
            show l.length - asg.length = 0 from by simp [h1], List.getD_cons_zero]
        have hnew2 : (l ++ [x]).getD l.length 0 = x := by
          rw [List.getD_append_right l [x] 0 l.length le_rfl, Nat.sub_self, List.getD_cons_zero]
        refine ⟨?_, ?_, ?_, ?_, ?_, ?_, ?_⟩
        · show (asg ++ [rest.length]).length = (l ++ [x]).length
          rw [List.length_append, List.length_singleton, hlen1, h1]
        · show (((bin ++ [x]) :: rest).map List.sum).sum = (l ++ [x]).sum
          have h2' : (bin.sum + (rest.map List.sum).sum) = l.sum := h2
          simp only [List.map_cons, List.sum_cons, List.sum_append, List.sum_nil, add_zero]
          linarith
        · intro b' hb'
          rw [List.mem_cons] at hb'
          rcases hb' with rfl | hb'
          · rw [List.sum_append, List.sum_singleton]
            exact ⟨(h3 bin (by simp)).1.trans_le (by linarith : bin.sum ≤ bin.sum + x), hfit⟩
          · exact h3 b' (List.mem_cons_of_mem _ hb')
        · intro i hi
          cases i with
          | zero =>
            have hrest : rest ≠ [] := by
              simp only [List.length_cons] at hi
              by_contra hc
              rw [hc, List.length_nil] at hi
              omega
            rw [List.getElem_cons_zero, List.getElem_cons_succ, List.sum_append,
              List.sum_singleton]
            have h40 := h4 0 (by
              have : 0 + 1 < (bin :: rest).length := by
                simp only [List.length_cons]
                have : 0 < rest.length := by
                  cases rest with
                  | nil => exact absurd rfl hrest
                  | cons b r => simp
                omega
              exact this)
            rw [List.getElem_cons_zero, List.getElem_cons_succ] at h40
            have hx0' : (0:ℝ) < x := hx0
            linarith
          | succ i =>
            rw [List.getElem_cons_succ, List.getElem_cons_succ]
            exact h4 (i + 1) (by
              show i + 1 + 1 < (bin :: rest).length
              have hi2 : i + 1 + 1 < ((bin ++ [x]) :: rest).length := hi
              simp only [List.length_cons] at hi2 ⊢
              omega)
        · intro b hb
          by_cases hbb : b = rest.length
          · subst hbb
            have hidx : ((bin ++ [x]) :: rest).length - 1 - rest.length = 0 := by
              simp only [List.length_cons]
              omega
            rw [hidx, List.getD_cons_zero, List.sum_append, List.sum_singleton]
            have hagree : ∀ j ∈ Finset.range l.length,
                (if (asg ++ [rest.length]).getD j 0 = rest.length then (l ++ [x]).getD j 0
                  else (0:ℝ))
                = if asg.getD j 0 = rest.length then l.getD j 0 else 0 := by
              intro j hj
              rw [Finset.mem_range] at hj
              rw [List.getD_append asg [rest.length] 0 j (by rwa [h1]),
                List.getD_append l [x] 0 j hj]
            have h5' := h5 rest.length (by simp)
            have hidx0 : (bin :: rest).length - 1 - rest.length = 0 := by simp
            rw [hidx0, List.getD_cons_zero] at h5'
            have hsplit : (∑ j ∈ (Finset.range ((l ++ [x]).length)).filter
                  (fun j => (asg ++ [rest.length]).getD j 0 = rest.length), (l ++ [x]).getD j 0)
                = (∑ j ∈ (Finset.range l.length).filter (fun j => asg.getD j 0 = rest.length),
                    l.getD j 0) + x := by
              rw [hlen1, Finset.sum_filter, Finset.sum_range_succ, Finset.sum_congr rfl hagree,
                ← Finset.sum_filter, hnew1, hnew2]
              simp
            rw [hsplit, h5']
          · have hb' : b < (bin :: rest).length := hb
            have hagree : ∀ j ∈ Finset.range l.length,
                (if (asg ++ [rest.length]).getD j 0 = b then (l ++ [x]).getD j 0 else (0:ℝ))
                = if asg.getD j 0 = b then l.getD j 0 else 0 := by
              intro j hj
              rw [Finset.mem_range] at hj
              rw [List.getD_append asg [rest.length] 0 j (by rwa [h1]),
                List.getD_append l [x] 0 j hj]
            have hsplit : (∑ j ∈ (Finset.range ((l ++ [x]).length)).filter
                  (fun j => (asg ++ [rest.length]).getD j 0 = b), (l ++ [x]).getD j 0)
                = ∑ j ∈ (Finset.range l.length).filter (fun j => asg.getD j 0 = b), l.getD j 0 := by
              rw [hlen1, Finset.sum_filter, Finset.sum_range_succ, Finset.sum_congr rfl hagree,
                ← Finset.sum_filter, hnew1, if_neg (show ¬ rest.length = b from fun h => hbb h.symm),
                add_zero]
            rw [hsplit, h5 b hb']
            show ((bin :: rest).getD ((bin :: rest).length - 1 - b) []).sum
              = (((bin ++ [x]) :: rest).getD (((bin ++ [x]) :: rest).length - 1 - b) []).sum
            have hge : (bin :: rest).length - 1 - b ≠ 0 := by
              simp only [List.length_cons] at hb' ⊢
              omega
            obtain ⟨n, hn⟩ := Nat.exists_eq_succ_of_ne_zero hge
            have hidx : ((bin ++ [x]) :: rest).length - 1 - b = (bin :: rest).length - 1 - b := rfl
            rw [hidx, hn, List.getD_cons_succ, List.getD_cons_succ]
        · intro j hj
          rw [hlen1] at hj
          by_cases hjj : j < l.length
          · rw [List.getD_append asg [rest.length] 0 j (by rwa [h1])]
            exact h6 j hjj
          · have hjj2 : j = l.length := by omega
            subst hjj2
            rw [hnew1]
            simp only [List.length_cons]
            omega
        · intro h
          rw [List.getLast_concat, List.length_cons, Nat.add_sub_cancel]
      · have e : nfStep (bin :: rest, asg) x = ([x] :: bin :: rest, asg ++ [(bin :: rest).length]) := by
          simp only [nfStep, if_neg hfit]
        rw [e]
        have hlen1 : (l ++ [x]).length = l.length + 1 := by simp
        have hnew1 : (asg ++ [(bin :: rest).length]).getD l.length 0 = (bin :: rest).length := by
          rw [List.getD_append_right asg [(bin :: rest).length] 0 l.length (by rw [h1]),
            show l.length - asg.length = 0 from by simp [h1], List.getD_cons_zero]
        have hnew2 : (l ++ [x]).getD l.length 0 = x := by
          rw [List.getD_append_right l [x] 0 l.length le_rfl, Nat.sub_self, List.getD_cons_zero]
        refine ⟨?_, ?_, ?_, ?_, ?_, ?_, ?_⟩
        · show (asg ++ [(bin :: rest).length]).length = (l ++ [x]).length
          rw [List.length_append, List.length_singleton, hlen1, h1]
        · show (([x] :: bin :: rest).map List.sum).sum = (l ++ [x]).sum
          have h2' : (bin.sum + (rest.map List.sum).sum) = l.sum := h2
          simp only [List.map_cons, List.sum_cons, List.sum_nil, List.sum_append]
          linarith
        · intro b' hb'
          rw [List.mem_cons] at hb'
          rcases hb' with rfl | hb'
          · exact ⟨by simpa using hx0, by simpa using hx1⟩
          · exact h3 b' hb'
        · intro i hi
          cases i with
          | zero =>
            rw [List.getElem_cons_zero, List.getElem_cons_succ, List.getElem_cons_zero,
              List.sum_singleton]
            have h1f : (1:ℝ) < bin.sum + x := not_le.mp hfit
            linarith
          | succ i =>
            rw [List.getElem_cons_succ, List.getElem_cons_succ]
            exact h4 i (by
              show i + 1 < (bin :: rest).length
              have hi2 : i + 1 + 1 < ([x] :: bin :: rest).length := hi
              simp only [List.length_cons] at hi2 ⊢
              omega)
        · intro b hb
          by_cases hbb : b = (bin :: rest).length
          · subst hbb
            have hidx : ([x] :: bin :: rest).length - 1 - (bin :: rest).length = 0 := by
              simp only [List.length_cons]
              omega
            rw [hidx, List.getD_cons_zero, List.sum_singleton]
            have hset : (Finset.range l.length).filter
                (fun j => asg.getD j 0 = (bin :: rest).length) = ∅ := by
              apply Finset.filter_false_of_mem
              intro j hj
              rw [Finset.mem_range] at hj
              have h6j : asg.getD j 0 < (bin :: rest).length := h6 j hj
              omega
            have hempty : (∑ j ∈ (Finset.range l.length).filter
                (fun j => asg.getD j 0 = (bin :: rest).length), l.getD j 0) = 0 := by
              rw [hset]
              simp
            have hagree : ∀ j ∈ Finset.range l.length,
                (if (asg ++ [(bin :: rest).length]).getD j 0 = (bin :: rest).length
                  then (l ++ [x]).getD j 0 else (0:ℝ))
                = if asg.getD j 0 = (bin :: rest).length then l.getD j 0 else 0 := by
              intro j hj
              rw [Finset.mem_range] at hj
              rw [List.getD_append asg [(bin :: rest).length] 0 j (by rwa [h1]),
                List.getD_append l [x] 0 j hj]
            have hsplit : (∑ j ∈ (Finset.range ((l ++ [x]).length)).filter
                  (fun j => (asg ++ [(bin :: rest).length]).getD j 0 = (bin :: rest).length),
                  (l ++ [x]).getD j 0)
                = (∑ j ∈ (Finset.range l.length).filter
                    (fun j => asg.getD j 0 = (bin :: rest).length), l.getD j 0) + x := by
              rw [hlen1, Finset.sum_filter, Finset.sum_range_succ, Finset.sum_congr rfl hagree,
                ← Finset.sum_filter, hnew1, hnew2]
              simp
            rw [hsplit, hempty]
            simp
          · have hb' : b < (bin :: rest).length := by
              have hb2 : b < (bin :: rest).length + 1 := hb
              simp only [List.length_cons] at hb2 hbb ⊢
              omega
            have hagree : ∀ j ∈ Finset.range l.length,
                (if (asg ++ [(bin :: rest).length]).getD j 0 = b then (l ++ [x]).getD j 0
                  else (0:ℝ))
                = if asg.getD j 0 = b then l.getD j 0 else 0 := by
              intro j hj
              rw [Finset.mem_range] at hj
              rw [List.getD_append asg [(bin :: rest).length] 0 j (by rwa [h1]),
                List.getD_append l [x] 0 j hj]
            have hsplit : (∑ j ∈ (Finset.range ((l ++ [x]).length)).filter
                  (fun j => (asg ++ [(bin :: rest).length]).getD j 0 = b), (l ++ [x]).getD j 0)
                = ∑ j ∈ (Finset.range l.length).filter (fun j => asg.getD j 0 = b), l.getD j 0 := by
              rw [hlen1, Finset.sum_filter, Finset.sum_range_succ, Finset.sum_congr rfl hagree,
                ← Finset.sum_filter, hnew1,
                if_neg (show ¬ (bin :: rest).length = b from fun h => hbb h.symm), add_zero]
            rw [hsplit, h5 b hb']
            show ((bin :: rest).getD ((bin :: rest).length - 1 - b) []).sum
              = (([x] :: bin :: rest).getD (([x] :: bin :: rest).length - 1 - b) []).sum
            have hidx2 : ([x] :: bin :: rest).length - 1 - b
                = ((bin :: rest).length - 1 - b) + 1 := by
              have hb'' : b < rest.length + 1 := by
                simpa only [List.length_cons] using hb'
              simp only [List.length_cons]
              omega
            rw [hidx2, List.getD_cons_succ]
        · intro j hj
          rw [hlen1] at hj
          by_cases hjj : j < l.length
          · rw [List.getD_append asg [(bin :: rest).length] 0 j (by rwa [h1])]
            have h6j : asg.getD j 0 < (bin :: rest).length := h6 j hjj
            simp only [List.length_cons] at h6j ⊢
            omega
          · have hjj2 : j = l.length := by omega
            subst hjj2
            rw [hnew1]
            simp only [List.length_cons]
            omega
        · intro h
          rw [List.getLast_concat]
          show (bin :: rest).length = ([x] :: bin :: rest).length - 1
          conv_rhs => rw [List.length_cons, Nat.add_sub_cancel]

theorem nfSpec_fold : ∀ (l : List ℝ), ValidInstance l → NFSpec l (l.foldl nfStep ([], [])) := by
  intro l
  induction l using List.reverseRecOn with
  | nil => intro _; exact nfSpec_nil
  | append_singleton l x ih =>
    intro hv
    rw [List.foldl_append, List.foldl_cons, List.foldl_nil]
    apply nfSpec_step (ih fun x hx => hv x (List.mem_append.mpr (Or.inl hx)))
    · exact (hv x (by simp)).1
    · exact (hv x (by simp)).2

theorem nfStep_snd_prefix (s : List (List ℝ) × List ℕ) (x : ℝ) :
    s.2 <+: (nfStep s x).2 := by
  cases s with
  | mk bins asg =>
    cases bins with
    | nil => exact ⟨[0], rfl⟩
    | cons bin rest =>
      by_cases h : bin.sum + x ≤ 1
      · exact ⟨[rest.length], by simp [nfStep, h]⟩
      · exact ⟨[(bin :: rest).length], by simp [nfStep, h]⟩

theorem nfStep_snd_length (s : List (List ℝ) × List ℕ) (x : ℝ) :
    (nfStep s x).2.length = s.2.length + 1 := by
  cases s with
  | mk bins asg =>
    cases bins with
    | nil => simp [nfStep]
    | cons bin rest =>
      by_cases h : bin.sum + x ≤ 1 <;> simp [nfStep, h]

theorem nfAssign_length (l : List ℝ) : (nfAssign l).length = l.length := by
  suffices h : ∀ (l : List ℝ) (s : List (List ℝ) × List ℕ),
      ((l.foldl nfStep s).2).length = s.2.length + l.length by
    have := h l ([], [])
    simp at this
    exact this
  intro l
  induction l using List.reverseRecOn with
  | nil => intro s; simp
  | append_singleton l x ih =>
    intro s
    rw [List.foldl_append, List.foldl_cons, List.foldl_nil, nfStep_snd_length, ih s]
    rw [List.length_append, List.length_singleton]
    omega

theorem nfAssign_prefix_aux : ∀ (l₂ : List ℝ) (s : List (List ℝ) × List ℕ),
    s.2 <+: ((l₂.foldl nfStep s).2) := by
  intro l₂
  induction l₂ using List.reverseRecOn with
  | nil => intro s; simp
  | append_singleton l x ih =>
    intro s
    rw [List.foldl_append, List.foldl_cons, List.foldl_nil]
    obtain ⟨t1, ht1⟩ := ih s
    obtain ⟨t2, ht2⟩ := nfStep_snd_prefix _ x
    exact ⟨t1 ++ t2, by rw [← ht2, ← ht1, List.append_assoc]⟩

theorem nfAssign_prefix_consistent {l₁ l₂ : List ℝ} (h : l₁ <+: l₂) :
    (nfAssign l₂).take l₁.length = nfAssign l₁ := by
  obtain ⟨rest, rfl⟩ := h
  have hpre : (l₁.foldl nfStep ([], [])).2 <+: ((l₁ ++ rest).foldl nfStep ([], [])).2 := by
    rw [List.foldl_append]
    exact nfAssign_prefix_aux rest _
  obtain ⟨t, ht⟩ := hpre
  show (((l₁ ++ rest).foldl nfStep ([], [])).2).take l₁.length = (l₁.foldl nfStep ([], [])).2
  rw [← ht]
  have hlen : ((l₁.foldl nfStep ([], [])).2).length = l₁.length := nfAssign_length l₁
  rw [List.take_append_of_le_length (le_of_eq hlen.symm), ← hlen, List.take_length]

theorem nextFit_feasible (l : List ℝ) (hv : ValidInstance l) (b : ℕ) :
    (∑ i ∈ Finset.univ.filter
      (fun i : Fin l.length => (nfAssign l).get (i.cast (nfAssign_length l).symm) = b),
        l.get i) ≤ 1 := by
  obtain ⟨h1, h2, h3, h4, h5, h6, h7⟩ := nfSpec_fold l hv
  have h5' : ∀ b : ℕ, b < ((l.foldl nfStep ([], [])).1).length →
      (∑ j ∈ (Finset.range l.length).filter (fun j => (nfAssign l).getD j 0 = b), l.getD j 0)
        = (((l.foldl nfStep ([], [])).1).getD (((l.foldl nfStep ([], [])).1).length - 1 - b) []).sum :=
    h5
  have h6' : ∀ j : ℕ, j < l.length →
      (nfAssign l).getD j 0 < ((l.foldl nfStep ([], [])).1).length := h6
  rw [fiber_sum_univ_eq_range l (nfAssign l) (nfAssign_length l) b]
  by_cases hb : b < ((l.foldl nfStep ([], [])).1).length
  · rw [h5' b hb]
    have hlt : ((l.foldl nfStep ([], [])).1).length - 1 - b
        < ((l.foldl nfStep ([], [])).1).length := by omega
    have hmem : ((l.foldl nfStep ([], [])).1).getD (((l.foldl nfStep ([], [])).1).length - 1 - b) []
        ∈ ((l.foldl nfStep ([], [])).1) := by
      rw [List.getD_eq_get _ _ ⟨_, hlt⟩]
      exact List.get_mem _ _
    exact (h3 _ hmem).2
  · have hempty : (Finset.range l.length).filter (fun j => (nfAssign l).getD j 0 = b) = ∅ := by
      apply Finset.filter_false_of_mem
      intro j hj
      rw [Finset.mem_range] at hj
      have := h6' j hj
      omega
    rw [hempty]
    simp

noncomputable def nextFit : OnlineAlg where
  assign := nfAssign
  length_eq := nfAssign_length
  prefix_consistent := @nfAssign_prefix_consistent
  feasible := nextFit_feasible

/-! ## First Fit -/

noncomputable def ffFind : List ℝ → ℝ → Option ℕ
  | [], _ => none
  | b :: rest, x => if b + x ≤ 1 then some 0 else (ffFind rest x).map (· + 1)

theorem ffFind_eq_some_lt {loads : List ℝ} {x : ℝ} {i : ℕ} (h : ffFind loads x = some i) :
    i < loads.length := by
  induction loads generalizing i with
  | nil =>
    have e : ffFind [] x = none := rfl
    rw [e] at h
    cases h
  | cons b rest ih =>
    unfold ffFind at h
    by_cases hb : b + x ≤ 1
    · rw [if_pos hb] at h
      cases h
      exact Nat.succ_pos _
    · rw [if_neg hb] at h
      cases hr : ffFind rest x with
      | none => rw [hr] at h; simp at h
      | some j =>
        rw [hr] at h
        simp only [Option.map_some, Option.some.injEq] at h
        obtain rfl : i = j + 1 := h.symm
        have := ih hr
        simp only [List.length_cons]
        omega

theorem ffFind_eq_some_le {loads : List ℝ} {x : ℝ} {i : ℕ} (h : ffFind loads x = some i) :
    loads[i]'(ffFind_eq_some_lt h) + x ≤ 1 := by
  induction loads generalizing i with
  | nil =>
    have e : ffFind [] x = none := rfl
    rw [e] at h
    cases h
  | cons b rest ih =>
    unfold ffFind at h
    by_cases hb : b + x ≤ 1
    · rw [if_pos hb] at h
      cases h
      exact hb
    · rw [if_neg hb] at h
      cases hr : ffFind rest x with
      | none => rw [hr] at h; simp at h
      | some j =>
        rw [hr] at h
        simp only [Option.map_some, Option.some.injEq] at h
        obtain rfl : i = j + 1 := h.symm
        exact ih hr

noncomputable def ffStep (s : List ℝ × List ℕ) (x : ℝ) : List ℝ × List ℕ :=
  match h : ffFind s.1 x with
  | some i => (s.1.set i (s.1[i]'(ffFind_eq_some_lt h) + x), s.2 ++ [i])
  | none => (s.1 ++ [x], s.2 ++ [s.1.length])

noncomputable def ffAssign (l : List ℝ) : List ℕ := (l.foldl ffStep ([], [])).2

theorem ffStep_none {s : List ℝ × List ℕ} {x : ℝ} (h : ffFind s.1 x = none) :
    ffStep s x = (s.1 ++ [x], s.2 ++ [s.1.length]) := by
  unfold ffStep
  split
  · rename_i i h2
    rw [h2] at h
    cases h
  · rfl

theorem ffStep_some {s : List ℝ × List ℕ} {x : ℝ} {i : ℕ} (h : ffFind s.1 x = some i) :
    ffStep s x = (s.1.set i (s.1[i]'(ffFind_eq_some_lt h) + x), s.2 ++ [i]) := by
  unfold ffStep
  split
  · rename_i i' h2
    rw [h2] at h
    cases h
    rfl
  · rename_i h2
    rw [h2] at h
    cases h

def FFSpec (l : List ℝ) (s : List ℝ × List ℕ) : Prop :=
  s.2.length = l.length
  ∧ (∀ i : Fin s.1.length, s.1.get i ≤ 1)
  ∧ (∀ b : ℕ, b < s.1.length →
      (∑ j ∈ (Finset.range l.length).filter (fun j => s.2.getD j 0 = b), l.getD j 0)
        = s.1.getD b 0)
  ∧ (∀ j : ℕ, j < l.length → s.2.getD j 0 < s.1.length)

theorem ffSpec_nil : FFSpec [] ([], []) := by
  refine ⟨rfl, ?_, ?_, ?_⟩
  · intro i
    exact Fin.elim0 i
  · intro b hb
    exact absurd hb (Nat.not_lt_zero _)
  · intro j hj
    exact absurd hj (Nat.not_lt_zero _)

theorem ffSpec_step {l : List ℝ} {s : List ℝ × List ℕ}
    (hs : FFSpec l s) (hx1 : x ≤ 1) :
    FFSpec (l ++ [x]) (ffStep s x) := by
  obtain ⟨h1, h2, h3, h4⟩ := hs
  have hlen1 : (l ++ [x]).length = l.length + 1 := by simp
  cases hf : ffFind s.1 x with
  | none =>
    rw [ffStep_none hf]
    have hnew1 : (s.2 ++ [s.1.length]).getD l.length 0 = s.1.length := by
      rw [List.getD_append_right s.2 [s.1.length] 0 l.length (by rw [h1]),
        show l.length - s.2.length = 0 from by simp [h1], List.getD_cons_zero]
    have hnew2 : (l ++ [x]).getD l.length 0 = x := by
      rw [List.getD_append_right l [x] 0 l.length le_rfl, Nat.sub_self, List.getD_cons_zero]
    refine ⟨?_, ?_, ?_, ?_⟩
    · show (s.2 ++ [s.1.length]).length = (l ++ [x]).length
      rw [List.length_append, List.length_singleton, hlen1, h1]
    · intro i'
      by_cases hi : i'.val < s.1.length
      · show (s.1 ++ [x])[i'.val]'(i'.isLt) ≤ 1
        rw [List.getElem_append_left hi]
        exact h2 ⟨i'.val, hi⟩
      · have hge : s.1.length ≤ i'.val := by omega
        have hle2 : i'.val ≤ s.1.length := by
          have hlen2 : ((s.1 ++ [x], s.2 ++ [s.1.length]).1).length = s.1.length + 1 := by
            rw [List.length_append, List.length_singleton]
          have h0 : i'.val < s.1.length + 1 := lt_of_lt_of_eq i'.isLt hlen2
          exact Nat.lt_succ_iff.mp h0
        have hi2 : i'.val = s.1.length := by omega
        have e1 : (s.1 ++ [x]).get i' = (s.1 ++ [x]).getD i'.val 0 :=
          (List.getD_eq_get _ _ i').symm
        rw [e1, List.getD_append_right s.1 [x] 0 i'.val hge, hi2, Nat.sub_self,
          List.getD_cons_zero]
        exact hx1
    · intro b hb
      by_cases hbb : b < s.1.length
      · have hagree : ∀ j ∈ Finset.range l.length,
            (if (s.2 ++ [s.1.length]).getD j 0 = b then (l ++ [x]).getD j 0 else (0:ℝ))
            = if s.2.getD j 0 = b then l.getD j 0 else 0 := by
          intro j hj
          rw [Finset.mem_range] at hj
          rw [List.getD_append s.2 [s.1.length] 0 j (by rwa [h1]),
            List.getD_append l [x] 0 j hj]
        have hsplit : (∑ j ∈ (Finset.range ((l ++ [x]).length)).filter
            (fun j => (s.2 ++ [s.1.length]).getD j 0 = b), (l ++ [x]).getD j 0)
            = ∑ j ∈ (Finset.range l.length).filter (fun j => s.2.getD j 0 = b), l.getD j 0 := by
          rw [hlen1, Finset.sum_filter, Finset.sum_range_succ, Finset.sum_congr rfl hagree,
            ← Finset.sum_filter, hnew1, if_neg (show ¬ s.1.length = b from by omega), add_zero]
        rw [hsplit, h3 b hbb, List.getD_append s.1 [x] 0 b hbb]
      · have hb2 : b = s.1.length := by
          have hbl : b < (s.1 ++ [x]).length := hb
          rw [List.length_append, List.length_singleton] at hbl
          omega
        subst hb2
        have hempty : (∑ j ∈ (Finset.range l.length).filter
            (fun j => s.2.getD j 0 = s.1.length), l.getD j 0) = 0 := by
          have hset : (Finset.range l.length).filter (fun j => s.2.getD j 0 = s.1.length) = ∅ := by
            apply Finset.filter_false_of_mem
            intro j hj
            rw [Finset.mem_range] at hj
            have := h4 j hj
            omega
          rw [hset]
          simp
        have hagree : ∀ j ∈ Finset.range l.length,
            (if (s.2 ++ [s.1.length]).getD j 0 = s.1.length then (l ++ [x]).getD j 0 else (0:ℝ))
            = if s.2.getD j 0 = s.1.length then l.getD j 0 else 0 := by
          intro j hj
          rw [Finset.mem_range] at hj
          rw [List.getD_append s.2 [s.1.length] 0 j (by rwa [h1]),
            List.getD_append l [x] 0 j hj]
        have hsplit : (∑ j ∈ (Finset.range ((l ++ [x]).length)).filter
              (fun j => (s.2 ++ [s.1.length]).getD j 0 = s.1.length), (l ++ [x]).getD j 0)
            = (∑ j ∈ (Finset.range l.length).filter (fun j => s.2.getD j 0 = s.1.length),
                l.getD j 0) + x := by
          rw [hlen1, Finset.sum_filter, Finset.sum_range_succ, Finset.sum_congr rfl hagree,
            ← Finset.sum_filter, hnew1, hnew2]
          simp
        rw [hsplit, hempty, List.getD_append_right s.1 [x] 0 s.1.length le_rfl, Nat.sub_self,
          List.getD_cons_zero, zero_add]
    · intro j hj
      rw [hlen1] at hj
      by_cases hjj : j < l.length
      · rw [List.getD_append s.2 [s.1.length] 0 j (by rwa [h1])]
        have := h4 j hjj
        rw [List.length_append, List.length_singleton]
        omega
      · have hjj2 : j = l.length := by omega
        subst hjj2
        rw [hnew1]
        rw [List.length_append, List.length_singleton]
        omega
  | some i =>
    rw [ffStep_some hf]
    have hlt : i < s.1.length := ffFind_eq_some_lt hf
    have hle : s.1[i] + x ≤ 1 := ffFind_eq_some_le hf
    have hnew1 : (s.2 ++ [i]).getD l.length 0 = i := by
      rw [List.getD_append_right s.2 [i] 0 l.length (by rw [h1]),
        show l.length - s.2.length = 0 from by simp [h1], List.getD_cons_zero]
    have hnew2 : (l ++ [x]).getD l.length 0 = x := by
      rw [List.getD_append_right l [x] 0 l.length le_rfl, Nat.sub_self, List.getD_cons_zero]
    refine ⟨?_, ?_, ?_, ?_⟩
    · show (s.2 ++ [i]).length = (l ++ [x]).length
      rw [List.length_append, List.length_singleton, hlen1, h1]
    · intro i'
      have hlen : ((s.1.set i (s.1[i] + x), s.2 ++ [i]).1).length = s.1.length := List.length_set
      have hi' : i'.val < s.1.length := lt_of_lt_of_eq i'.isLt hlen
      by_cases hii : i'.val = i
      · have e2 : ((s.1.set i (s.1[i] + x), s.2 ++ [i]).1).get i'
            = (s.1.set i (s.1[i] + x)).getD i'.val 0 := (List.getD_eq_get _ _ i').symm
        rw [e2, hii, List.getD_eq_get _ _ ⟨i, lt_of_lt_of_eq hlt hlen.symm⟩]
        exact (List.getElem_set_self _).trans_le hle
      · have e2 : ((s.1.set i (s.1[i] + x), s.2 ++ [i]).1).get i'
            = (s.1.set i (s.1[i] + x)).getD i'.val 0 := (List.getD_eq_get _ _ i').symm
        have e3 : (s.1.set i (s.1[i] + x)).getD i'.val 0 = s.1.getD i'.val 0 := by
          rw [List.getD_eq_get _ _ ⟨i'.val, lt_of_lt_of_eq hi' hlen.symm⟩,
            List.getD_eq_get _ _ ⟨i'.val, hi'⟩]
          exact List.getElem_set_ne (Ne.symm hii) _
        rw [e2, e3, List.getD_eq_get s.1 0 ⟨i'.val, hi'⟩]
        exact h2 ⟨i'.val, hi'⟩
    · intro b hb
      have hb' : b < s.1.length := by
        rwa [List.length_set] at hb
      by_cases hbb : b = i
      · subst b
        have hagree : ∀ j ∈ Finset.range l.length,
            (if (s.2 ++ [i]).getD j 0 = i then (l ++ [x]).getD j 0 else (0:ℝ))
            = if s.2.getD j 0 = i then l.getD j 0 else 0 := by
          intro j hj
          rw [Finset.mem_range] at hj
          rw [List.getD_append s.2 [i] 0 j (by rwa [h1]),
            List.getD_append l [x] 0 j hj]
        have hsplit : (∑ j ∈ (Finset.range ((l ++ [x]).length)).filter
              (fun j => (s.2 ++ [i]).getD j 0 = i), (l ++ [x]).getD j 0)
            = (∑ j ∈ (Finset.range l.length).filter (fun j => s.2.getD j 0 = i), l.getD j 0) + x := by
          rw [hlen1, Finset.sum_filter, Finset.sum_range_succ, Finset.sum_congr rfl hagree,
            ← Finset.sum_filter, hnew1, hnew2]
          simp
        rw [hsplit, h3 i hlt]
        have hset : (s.1.set i (s.1[i] + x)).getD i 0 = s.1[i] + x := by
          rw [List.getD_eq_get _ _ ⟨i, by rwa [List.length_set]⟩]
          exact List.getElem_set_self _
        rw [hset]
        congr 1
        exact List.getD_eq_get s.1 0 ⟨i, hlt⟩
      · have hagree : ∀ j ∈ Finset.range l.length,
            (if (s.2 ++ [i]).getD j 0 = b then (l ++ [x]).getD j 0 else (0:ℝ))
            = if s.2.getD j 0 = b then l.getD j 0 else 0 := by
          intro j hj
          rw [Finset.mem_range] at hj
          rw [List.getD_append s.2 [i] 0 j (by rwa [h1]),
            List.getD_append l [x] 0 j hj]
        have hsplit : (∑ j ∈ (Finset.range ((l ++ [x]).length)).filter
            (fun j => (s.2 ++ [i]).getD j 0 = b), (l ++ [x]).getD j 0)
            = ∑ j ∈ (Finset.range l.length).filter (fun j => s.2.getD j 0 = b), l.getD j 0 := by
          rw [hlen1, Finset.sum_filter, Finset.sum_range_succ, Finset.sum_congr rfl hagree,
            ← Finset.sum_filter, hnew1, if_neg (show ¬ i = b from fun h => hbb h.symm), add_zero]
        rw [hsplit, h3 b hb']
        have hset : (s.1.set i (s.1[i] + x)).getD b 0 = s.1.getD b 0 := by
          rw [List.getD_eq_get _ _ ⟨b, by rwa [List.length_set]⟩,
            List.getD_eq_get _ _ ⟨b, hb'⟩]
          exact List.getElem_set_ne (Ne.symm hbb) _
        rw [hset]
    · intro j hj
      rw [hlen1] at hj
      by_cases hjj : j < l.length
      · rw [List.getD_append s.2 [i] 0 j (by rwa [h1])]
        have := h4 j hjj
        rwa [List.length_set]
      · have hjj2 : j = l.length := by omega
        subst hjj2
        rw [hnew1]
        rwa [List.length_set]

theorem ffSpec_fold : ∀ (l : List ℝ), ValidInstance l → FFSpec l (l.foldl ffStep ([], [])) := by
  intro l
  induction l using List.reverseRecOn with
  | nil => intro _; exact ffSpec_nil
  | append_singleton l x ih =>
    intro hv
    rw [List.foldl_append, List.foldl_cons, List.foldl_nil]
    apply ffSpec_step (ih fun x hx => hv x (List.mem_append.mpr (Or.inl hx)))
    exact (hv x (by simp)).2

theorem ffStep_snd_prefix (s : List ℝ × List ℕ) (x : ℝ) :
    s.2 <+: (ffStep s x).2 := by
  cases h : ffFind s.1 x with
  | none => exact ⟨[s.1.length], by rw [ffStep_none h]⟩
  | some i => exact ⟨[i], by rw [ffStep_some h]⟩

theorem ffStep_snd_length (s : List ℝ × List ℕ) (x : ℝ) :
    (ffStep s x).2.length = s.2.length + 1 := by
  cases h : ffFind s.1 x with
  | none => rw [ffStep_none h]; simp
  | some i => rw [ffStep_some h]; simp

theorem ffAssign_length (l : List ℝ) : (ffAssign l).length = l.length := by
  suffices h : ∀ (l : List ℝ) (s : List ℝ × List ℕ),
      ((l.foldl ffStep s).2).length = s.2.length + l.length by
    have := h l ([], [])
    simp at this
    exact this
  intro l
  induction l using List.reverseRecOn with
  | nil => intro s; simp
  | append_singleton l x ih =>
    intro s
    rw [List.foldl_append, List.foldl_cons, List.foldl_nil, ffStep_snd_length, ih s]
    rw [List.length_append, List.length_singleton]
    omega

theorem ffAssign_prefix_aux : ∀ (l₂ : List ℝ) (s : List ℝ × List ℕ),
    s.2 <+: ((l₂.foldl ffStep s).2) := by
  intro l₂
  induction l₂ using List.reverseRecOn with
  | nil => intro s; simp
  | append_singleton l x ih =>
    intro s
    rw [List.foldl_append, List.foldl_cons, List.foldl_nil]
    obtain ⟨t1, ht1⟩ := ih s
    obtain ⟨t2, ht2⟩ := ffStep_snd_prefix _ x
    exact ⟨t1 ++ t2, by rw [← ht2, ← ht1, List.append_assoc]⟩

theorem ffAssign_prefix_consistent {l₁ l₂ : List ℝ} (h : l₁ <+: l₂) :
    (ffAssign l₂).take l₁.length = ffAssign l₁ := by
  obtain ⟨rest, rfl⟩ := h
  have hpre : (l₁.foldl ffStep ([], [])).2 <+: ((l₁ ++ rest).foldl ffStep ([], [])).2 := by
    rw [List.foldl_append]
    exact ffAssign_prefix_aux rest _
  obtain ⟨t, ht⟩ := hpre
  show (((l₁ ++ rest).foldl ffStep ([], [])).2).take l₁.length = (l₁.foldl ffStep ([], [])).2
  rw [← ht]
  have hlen : ((l₁.foldl ffStep ([], [])).2).length = l₁.length := ffAssign_length l₁
  rw [List.take_append_of_le_length (le_of_eq hlen.symm), ← hlen, List.take_length]

theorem firstFit_feasible (l : List ℝ) (hv : ValidInstance l) (b : ℕ) :
    (∑ i ∈ Finset.univ.filter
      (fun i : Fin l.length => (ffAssign l).get (i.cast (ffAssign_length l).symm) = b),
        l.get i) ≤ 1 := by
  obtain ⟨h1, h2, h3, h4⟩ := ffSpec_fold l hv
  have h3' : ∀ b : ℕ, b < ((l.foldl ffStep ([], [])).1).length →
      (∑ j ∈ (Finset.range l.length).filter (fun j => (ffAssign l).getD j 0 = b), l.getD j 0)
        = ((l.foldl ffStep ([], [])).1).getD b 0 := h3
  have h4' : ∀ j : ℕ, j < l.length →
      (ffAssign l).getD j 0 < ((l.foldl ffStep ([], [])).1).length := h4
  rw [fiber_sum_univ_eq_range l (ffAssign l) (ffAssign_length l) b]
  by_cases hb : b < ((l.foldl ffStep ([], [])).1).length
  · rw [h3' b hb, List.getD_eq_get _ _ ⟨b, hb⟩]
    exact h2 ⟨b, hb⟩
  · have hempty : (Finset.range l.length).filter (fun j => (ffAssign l).getD j 0 = b) = ∅ := by
      apply Finset.filter_false_of_mem
      intro j hj
      rw [Finset.mem_range] at hj
      have := h4' j hj
      omega
    rw [hempty]
    simp

noncomputable def firstFit : OnlineAlg where
  assign := ffAssign
  length_eq := ffAssign_length
  prefix_consistent := @ffAssign_prefix_consistent
  feasible := firstFit_feasible

/-! ## Concrete instances -/

def ones (k : ℕ) : List ℝ := List.replicate k 1

theorem valid_ones (k : ℕ) : ValidInstance (ones k) := by
  intro x hx
  simp only [ones, List.mem_replicate] at hx
  obtain ⟨_, rfl⟩ := hx
  exact ⟨by norm_num, le_refl 1⟩

theorem ones_get (k : ℕ) (i : Fin (ones k).length) : (ones k).get i = 1 :=
  List.getElem_replicate _

theorem optNumber_ones (k : ℕ) : optNumber (ones k) = k := by
  apply le_antisymm
  · calc optNumber (ones k) ≤ (ones k).length :=
        optNumber_le_of_packsIn (packsIn_self (valid_ones k))
      _ = k := List.length_replicate
  · have hT : (Finset.univ : Finset (Fin (ones k).length)).card ≤ optNumber (ones k) := by
      apply le_optNumber_of_pairwise_incompatible (valid_ones k)
      intro i _ j _ hij
      rw [ones_get, ones_get]
      norm_num
    have e : (ones k).length = k := List.length_replicate
    rwa [Finset.card_univ, Fintype.card_fin, e] at hT

def instFFN : List ℕ := [6, 6, 6, 6, 6, 6, 14, 14, 14, 14, 14, 14, 21, 21, 21, 21, 21, 21]

noncomputable def instFFR : List ℝ := instFFN.map fun n => ((n : ℝ) / (41 : ℕ))

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

/-! ## Slot zone: the two threshold statements -/

-- @[slot main]
/-- **The upper-bound direction.** The optimal asymptotic competitive ratio
R* of online bin packing is at most 1.56. Proving this improves the best
known upper bound 1.57829 (Balogh–Békési–Dósa–Epstein–Levin, ESA 2018). -/
theorem conj : RStar ≤ (1.56 : ℝ) := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

-- @[slot main]
/-- **The lower-bound direction.** The optimal asymptotic competitive ratio
R* is strictly above 1.56. Proving this improves the best known lower bound
1.54278 (Balogh–Békési–Dósa–Epstein–Levin, Algorithmica 2021). -/
theorem refuted : ¬ RStar ≤ (1.56 : ℝ) := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

end OnlineBinPacking
