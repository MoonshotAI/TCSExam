/-
Self-contained statement layer for the log-rank conjecture of communication
complexity (Lovász–Saks, "Lattices, Möbius functions and communication
complexity", FOCS 1988; journal version JCSS 1993): every two-party Boolean
function `f` with communication matrix `A` satisfies
`D(f) ≤ (log₂ rank A)^{O(1)}`, where `rank` is the rank over the reals and
`D` is the deterministic two-party communication complexity.

The fixed part (everything above the end-of-fixed-part marker line) is the
definition layer the conjecture statement and the three special-case slots
need. Fidelity notes live in `tests/reference/`.
-/

import Mathlib

namespace LogRank

/-! ## The communication matrix -/

/-- The communication matrix of a two-party Boolean function `f`, over the
reals: rows are indexed by Alice's input `x`, columns by Bob's input `y`, and
the `(x, y)` entry is `1` if `f x y` and `0` otherwise. -/
def commMatrix {X Y : Type} (f : X → Y → Bool) : Matrix X Y ℝ :=
  fun x y => if f x y then 1 else 0

@[simp] theorem commMatrix_apply {X Y : Type} (f : X → Y → Bool) (x : X) (y : Y) :
    commMatrix f x y = if f x y then (1 : ℝ) else 0 := rfl

/-! ## Deterministic protocols (two-party decision trees) -/

/-- A deterministic two-party protocol as a binary decision tree whose inner
nodes are labelled by the player who speaks: `alice g l r` branches on the
single bit `g x` (a function of Alice's input alone), `bob g l r` branches on
the single bit `g y`, and `leaf b` halts with output `b`. -/
inductive Protocol (X Y : Type) : Type
  | leaf : Bool → Protocol X Y
  | alice : (X → Bool) → Protocol X Y → Protocol X Y → Protocol X Y
  | bob : (Y → Bool) → Protocol X Y → Protocol X Y → Protocol X Y

namespace Protocol

/-- The depth of a protocol tree: the worst-case number of bits exchanged. -/
def depth {X Y : Type} : Protocol X Y → ℕ
  | leaf _ => 0
  | alice _ l r => 1 + max (depth l) (depth r)
  | bob _ l r => 1 + max (depth l) (depth r)

/-- The output of a protocol on input `(x, y)`. -/
def run {X Y : Type} : Protocol X Y → X → Y → Bool
  | leaf b, _, _ => b
  | alice g l r, x, y => if g x then l.run x y else r.run x y
  | bob g l r, x, y => if g y then l.run x y else r.run x y

/-- A protocol computes `f` if its output agrees with `f` on every input. -/
def Computes {X Y : Type} (p : Protocol X Y) (f : X → Y → Bool) : Prop :=
  ∀ x y, p.run x y = f x y

end Protocol

/-! ## Deterministic communication complexity -/

/-- The trivial "pinpoint" protocol: Alice tests her input `x` against each
element of an enumeration of `X` in turn; as soon as `x = x₀` is identified,
Bob evaluates `f x₀ y` on his own input and answers. -/
def pinpoint {X Y : Type} [DecidableEq X] (f : X → Y → Bool) :
    List X → Protocol X Y
  | [] => Protocol.leaf false
  | x₀ :: rest =>
    Protocol.alice (fun x => decide (x = x₀))
      (Protocol.bob (fun y => f x₀ y) (Protocol.leaf true) (Protocol.leaf false))
      (pinpoint f rest)

/-- `(if b = true then true else false) = b`: the run of a Bob-query leaf pair
returns the queried bit. -/
theorem if_bit_eq_self (b : Bool) : (if b = true then true else false) = b := by
  cases b <;> rfl

/-- The pinpoint protocol is correct on every input listed in `xs`. -/
theorem pinpoint_computes {X Y : Type} [DecidableEq X] (f : X → Y → Bool)
    (xs : List X) {x : X} (hx : x ∈ xs) (y : Y) :
    (pinpoint f xs).run x y = f x y := by
  induction xs with
  | nil => exact absurd hx List.not_mem_nil
  | cons x₀ rest ih =>
    simp only [pinpoint, Protocol.run]
    by_cases h : x = x₀
    · subst h
      simp only [decide_eq_true_eq, if_true]
      exact if_bit_eq_self (f x y)
    · have hd : decide (x = x₀) = false := decide_eq_false h
      simp only [hd, Bool.false_eq_true, if_false]
      exact ih (List.mem_of_ne_of_mem h hx)

/-- The pinpoint protocol over `xs` has depth at most `xs.length + 1`. -/
theorem pinpoint_depth {X Y : Type} [DecidableEq X] (f : X → Y → Bool)
    (xs : List X) : (pinpoint f xs).depth ≤ xs.length + 1 := by
  induction xs with
  | nil => simp [pinpoint, Protocol.depth]
  | cons x₀ rest ih =>
    simp only [pinpoint, Protocol.depth, List.length_cons]
    omega

/-- Every finite-domain Boolean function is computed by some protocol:
exhaustive pinpointing always works. -/
theorem exists_computes {X Y : Type} [Fintype X] [Fintype Y] (f : X → Y → Bool) :
    ∃ p : Protocol X Y, p.Computes f ∧ p.depth ≤ Fintype.card X + 1 := by
  classical
  refine ⟨pinpoint f (Finset.univ.val.toList), fun x y => ?_, ?_⟩
  · exact pinpoint_computes f _ (by simp) y
  · calc (pinpoint f (Finset.univ.val.toList)).depth
        ≤ (Finset.univ.val.toList).length + 1 := pinpoint_depth f _
      _ = Fintype.card X + 1 := by
          rw [Multiset.length_toList, ← Finset.card_univ]; rfl

/-- The deterministic communication complexity of `f`: the least depth of a
protocol computing `f`.  The set of achievable depths is nonempty
(`exists_computes`), so the infimum is attained. -/
noncomputable def D {X Y : Type} [Fintype X] [Fintype Y] (f : X → Y → Bool) : ℕ :=
  sInf {d : ℕ | ∃ p : Protocol X Y, p.Computes f ∧ p.depth ≤ d}

/-- Any concrete protocol computing `f` upper-bounds `D f`. -/
theorem D_le {X Y : Type} [Fintype X] [Fintype Y] {f : X → Y → Bool}
    (p : Protocol X Y) (h : p.Computes f) : D f ≤ p.depth :=
  Nat.sInf_le ⟨p, h, le_refl _⟩

/-- The infimum is attained: some protocol computes `f` within depth `D f`. -/
theorem exists_protocol_D {X Y : Type} [Fintype X] [Fintype Y] (f : X → Y → Bool) :
    ∃ p : Protocol X Y, p.Computes f ∧ p.depth ≤ D f := by
  have h := Nat.sInf_mem
    (s := {d : ℕ | ∃ p : Protocol X Y, p.Computes f ∧ p.depth ≤ d})
    ⟨_, exists_computes f⟩
  simpa [D] using h

/-! ## The conjecture -/

/-- The log-rank conjecture (Lovász–Saks 1988): there is a constant `c > 0`
such that every two-party Boolean function `f` over finite domains satisfies
`D(f) ≤ (1 + log₂ rank(M_f)) ^ c`, where `M_f` is the communication matrix
over `ℝ`.

Two degeneracies force the exact shape of this statement:

* A rank-1 Boolean matrix `u ∧ v` with both `u`, `v` nonconstant has
  `log₂ rank = 0` but `D = 2`, so the hypothesis `2 ≤ rank` restricts to
  the nondegenerate case.
* Even at rank `2` the pure power is impossible: equality on one bit has
  `D = 2` but `(log₂ 2)^c = 1` for every `c`.  The conjecture is always
  meant in the big-O sense; we pin it down with `1 + log₂ rank`, which is
  asymptotically equivalent to the textbook form `D ≤ (log₂ rank)^{c'}`
  (the exponents differ by an arbitrarily small amount). -/
def LogRankConjecture : Prop :=
  ∃ c : ℝ, 0 < c ∧ ∀ {X Y : Type} [Fintype X] [Fintype Y] (f : X → Y → Bool),
    2 ≤ (commMatrix f).rank →
      (D f : ℝ) ≤ (1 + Real.logb 2 ((commMatrix f).rank : ℝ)) ^ c

/-! ## The inner-product function on two-bit strings (special case (b)) -/

/-- The mod-2 inner product on `2`-bit strings: `ip2 x y = x₀·y₀ ⊕ x₁·y₁`,
computed in `ZMod 2`.  Its `4 × 4` communication matrix has rank `3`. -/
def ip2 : (Fin 2 → Fin 2) → (Fin 2 → Fin 2) → Bool :=
  fun x y => decide ((x 0 * y 0 + x 1 * y 1 : ZMod 2) = 1)

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- but the fixed part above and the five slot statements must not be modified.

/-- The log-rank conjecture. Prove it for full credit. -/
theorem conj : LogRankConjecture := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

/-- The negation of the log-rank conjecture. Prove it for full credit. -/
theorem refuted : ¬ LogRankConjecture := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

/-- Special case (a): the equality function on `Fin 4`. Its communication
matrix is the `4 × 4` identity (rank `4 = 2²`), and a `3`-bit protocol
(Alice sends her two bits, Bob compares) witnesses `D ≤ 3 ≤ (log₂ 4)²`. -/
theorem eq4_rank_and_bound :
    (commMatrix (fun x y : Fin 4 => decide (x = y))).rank = 4 ∧
      (D (fun x y : Fin 4 => decide (x = y)) : ℝ) ≤
        Real.logb 2 ((commMatrix (fun x y : Fin 4 => decide (x = y))).rank : ℝ)
          ^ (2 : ℝ) := by
  -- CHECKPOINT eq4_rank_and_bound BEGIN
  have hm : commMatrix (fun x y : Fin 4 => decide (x = y)) =
      (1 : Matrix (Fin 4) (Fin 4) ℝ) := by
    ext i j
    by_cases h : i = j
    · subst h; simp [commMatrix, Matrix.one_apply_eq]
    · simp [commMatrix, h, Matrix.one_apply_ne h]
  have hrank : (commMatrix (fun x y : Fin 4 => decide (x = y))).rank = 4 := by
    rw [hm, Matrix.rank_one]; rfl
  refine ⟨hrank, ?_⟩
  rw [hrank]
  -- the 3-bit protocol: Alice sends her two bits, Bob compares
  let p : Protocol (Fin 4) (Fin 4) :=
    Protocol.alice (fun x => x.val.testBit 0)
      (Protocol.alice (fun x => x.val.testBit 1)
        (Protocol.bob (fun y => decide (y = 3)) (Protocol.leaf true) (Protocol.leaf false))
        (Protocol.bob (fun y => decide (y = 1)) (Protocol.leaf true) (Protocol.leaf false)))
      (Protocol.alice (fun x => x.val.testBit 1)
        (Protocol.bob (fun y => decide (y = 2)) (Protocol.leaf true) (Protocol.leaf false))
        (Protocol.bob (fun y => decide (y = 0)) (Protocol.leaf true) (Protocol.leaf false)))
  have hp : p.Computes (fun x y : Fin 4 => decide (x = y)) := by
    intro x y
    fin_cases x <;> fin_cases y <;> rfl
  have hD : D (fun x y : Fin 4 => decide (x = y)) ≤ 3 := D_le p hp
  have hlog : Real.logb 2 (4 : ℝ) = 2 := by
    have h : (4 : ℝ) = 2 ^ (2 : ℝ) := by norm_num
    rw [h, Real.logb_rpow (by norm_num) (by norm_num)]
  show ((D fun x y : Fin 4 => decide (x = y)) : ℝ) ≤ Real.logb 2 (4 : ℝ) ^ (2 : ℝ)
  rw [hlog]
  have h4 : (2 : ℝ) ^ (2 : ℝ) = 4 := by norm_num [Real.rpow_natCast]
  calc ((D fun x y : Fin 4 => decide (x = y)) : ℝ) ≤ 3 := by exact_mod_cast hD
    _ ≤ (2 : ℝ) ^ (2 : ℝ) := by rw [h4]; norm_num
  -- CHECKPOINT eq4_rank_and_bound END

/-- Special case (b): the two-bit inner product `ip2`. Its communication
matrix (a `4 × 4` matrix with one zero row) has rank `3`, and a `3`-bit
protocol witnesses `D ≤ 3 ≤ (log₂ 3)³`. -/
theorem ip2_rank_and_bound :
    (commMatrix ip2).rank = 3 ∧
      (D ip2 : ℝ) ≤ Real.logb 2 ((commMatrix ip2).rank : ℝ) ^ (3 : ℝ) := by
  -- CHECKPOINT ip2_rank_and_bound BEGIN
  -- the three nonzero columns of the communication matrix
  let c1 : (Fin 2 → Fin 2) → ℝ := fun x => if ip2 x ![0,1] then 1 else 0
  let c2 : (Fin 2 → Fin 2) → ℝ := fun x => if ip2 x ![1,0] then 1 else 0
  let c3 : (Fin 2 → Fin 2) → ℝ := fun x => if ip2 x ![1,1] then 1 else 0
  have hlin : LinearIndependent ℝ ![c1, c2, c3] := by
    rw [Fintype.linearIndependent_iff]
    intro g hg j
    have e1 := congrFun hg ![0,1]
    have e2 := congrFun hg ![1,0]
    have e3 := congrFun hg ![1,1]
    simp only [Fin.sum_univ_three, Finset.sum_apply, Pi.smul_apply, smul_eq_mul,
      Matrix.cons_val_zero, Matrix.cons_val_one, Matrix.head_cons, Pi.zero_apply]
      at e1 e2 e3
    have w2 : (![c1, c2, c3] : Fin 3 → (Fin 2 → Fin 2) → ℝ) 2 = c3 := rfl
    rw [w2] at e1 e2 e3
    have v11 : c1 ![0,1] = 1 := by rfl
    have v12 : c2 ![0,1] = 0 := by rfl
    have v13 : c3 ![0,1] = 1 := by rfl
    have v21 : c1 ![1,0] = 0 := by rfl
    have v22 : c2 ![1,0] = 1 := by rfl
    have v23 : c3 ![1,0] = 1 := by rfl
    have v31 : c1 ![1,1] = 1 := by rfl
    have v32 : c2 ![1,1] = 1 := by rfl
    have v33 : c3 ![1,1] = 0 := by rfl
    rw [v11, v12, v13] at e1
    rw [v21, v22, v23] at e2
    rw [v31, v32, v33] at e3
    -- e1 : g 0 + g 2 = 0 ; e2 : g 1 + g 2 = 0 ; e3 : g 0 + g 1 = 0
    have h3v : ∀ k : Fin 3, k = 0 ∨ k = 1 ∨ k = 2 := fun k => by fin_cases k <;> simp
    rcases h3v j with hj | hj | hj <;> subst hj <;> linarith
  have hcol : ∀ y : Fin 2 → Fin 2,
      (commMatrix ip2).col y ∈
        Submodule.span ℝ ({c1, c2, c3} : Set ((Fin 2 → Fin 2) → ℝ)) := by
    have h2 : ∀ i : Fin 2, i = 0 ∨ i = 1 := fun i => by fin_cases i <;> simp
    intro y
    have hy : y = ![y 0, y 1] := by ext i; fin_cases i <;> rfl
    rcases h2 (y 0) with h0 | h0 <;> rcases h2 (y 1) with h1 | h1 <;>
      rw [h0, h1] at hy
    · -- y = ![0,0]: the zero column
      have hz : (commMatrix ip2).col y = 0 := by rw [hy]; ext x; rfl
      rw [hz]; exact Submodule.zero_mem _
    · have hz : (commMatrix ip2).col y = c1 := by rw [hy]; rfl
      rw [hz]; exact Submodule.subset_span (by simp)
    · have hz : (commMatrix ip2).col y = c2 := by rw [hy]; rfl
      rw [hz]; exact Submodule.subset_span (by simp)
    · have hz : (commMatrix ip2).col y = c3 := by rw [hy]; rfl
      rw [hz]; exact Submodule.subset_span (by simp)
  have hle : (commMatrix ip2).rank ≤ 3 := by
    rw [Matrix.rank_eq_finrank_span_cols]
    have hsub : Submodule.span ℝ (Set.range (commMatrix ip2).col) ≤
        Submodule.span ℝ ({c1, c2, c3} : Set ((Fin 2 → Fin 2) → ℝ)) :=
      Submodule.span_le.2 (Set.range_subset_iff.2 hcol)
    refine (Submodule.finrank_mono hsub).trans ?_
    refine (finrank_span_le_card _).trans ?_
    simp only [Set.toFinset_insert, Set.toFinset_singleton]
    have h1 := Finset.card_insert_le c1 (insert c2 ({c3} : Finset ((Fin 2 → Fin 2) → ℝ)))
    have h2 := Finset.card_insert_le c2 ({c3} : Finset ((Fin 2 → Fin 2) → ℝ))
    rw [Finset.card_singleton] at h2
    omega
  have hge : 3 ≤ (commMatrix ip2).rank := by
    rw [Matrix.rank_eq_finrank_span_cols]
    have hsub : Set.range ![c1, c2, c3] ⊆ Set.range (commMatrix ip2).col := by
      rintro v ⟨j, rfl⟩
      fin_cases j
      · exact ⟨![0,1], rfl⟩
      · exact ⟨![1,0], rfl⟩
      · exact ⟨![1,1], rfl⟩
    have hcard := finrank_span_eq_card hlin
    rw [show Fintype.card (Fin 3) = 3 from rfl] at hcard
    rw [← hcard]
    exact Submodule.finrank_mono (Submodule.span_mono hsub)
  have hrank : (commMatrix ip2).rank = 3 := le_antisymm hle hge
  refine ⟨hrank, ?_⟩
  rw [hrank]
  -- a 3-bit protocol: Alice sends her two coordinates, Bob evaluates ip2
  let p : Protocol (Fin 2 → Fin 2) (Fin 2 → Fin 2) :=
    Protocol.alice (fun x => decide (x 0 = 1))
      (Protocol.alice (fun x => decide (x 1 = 1))
        (Protocol.bob (fun y => ip2 ![1,1] y) (Protocol.leaf true) (Protocol.leaf false))
        (Protocol.bob (fun y => ip2 ![1,0] y) (Protocol.leaf true) (Protocol.leaf false)))
      (Protocol.alice (fun x => decide (x 1 = 1))
        (Protocol.bob (fun y => ip2 ![0,1] y) (Protocol.leaf true) (Protocol.leaf false))
        (Protocol.bob (fun y => ip2 ![0,0] y) (Protocol.leaf true) (Protocol.leaf false)))
  have hp : p.Computes ip2 := by
    intro x y
    fin_cases x <;> fin_cases y <;> rfl
  have hD : D ip2 ≤ 3 := D_le p hp
  -- (log₂ 3)³ ≥ (3/2)³ = 27/8 ≥ 3
  have hlog : (3:ℝ)/2 ≤ Real.logb 2 3 := by
    have h1 : Real.logb 2 (2 ^ (3/2 : ℝ)) = 3/2 :=
      Real.logb_rpow (by norm_num) (by norm_num)
    rw [← h1]
    have h2 : (2:ℝ) ^ (3/2 : ℝ) = 2 * Real.sqrt 2 := by
      rw [show (3/2 : ℝ) = 1 + 1/2 by norm_num, Real.rpow_add (by norm_num),
        Real.rpow_one, ← Real.sqrt_eq_rpow]
    have hle32 : (2:ℝ) ^ (3/2 : ℝ) ≤ 3 := by
      rw [h2]
      have h3 : Real.sqrt 2 ≤ 3/2 := by
        nlinarith [Real.sq_sqrt (show (0:ℝ) ≤ 2 by norm_num), Real.sqrt_nonneg 2]
      linarith
    exact Real.logb_le_logb_of_le (by norm_num) (by positivity) hle32
  have h3 : (3:ℝ) ≤ Real.logb 2 3 ^ (3:ℝ) := by
    have hmono : (3/2:ℝ)^(3:ℝ) ≤ Real.logb 2 3 ^ (3:ℝ) :=
      Real.rpow_le_rpow (by norm_num) hlog (by norm_num)
    have h27 : ((3/2:ℝ)^(3:ℝ)) = 27/8 := by
      rw [show (3:ℝ) = ((3:ℕ):ℝ) by norm_num, Real.rpow_natCast]
      norm_num
    rw [h27] at hmono
    linarith
  show ((D ip2) : ℝ) ≤ Real.logb 2 (3:ℝ) ^ (3:ℝ)
  exact ((by exact_mod_cast hD) : ((D ip2):ℝ) ≤ 3).trans h3
  -- CHECKPOINT ip2_rank_and_bound END

/-- Special case (c): rank-1 block structure. Every pointwise conjunction
`u ∧ v` (whose communication matrix `u vᵀ` has rank at most `1`) is computed
by a `2`-bit protocol: Alice sends `u x`, and if it holds Bob sends `v y`.
This family is also why the conjecture needs the `2 ≤ rank` hypothesis:
when both `u` and `v` are nonconstant the matrix has rank exactly `1`, so
`log₂ rank = 0`, while `D = 2`. -/
theorem rank1_le_two {X Y : Type} [Fintype X] [Fintype Y]
    (u : X → Bool) (v : Y → Bool) :
    D (fun x y => u x && v y) ≤ 2 := by
  -- CHECKPOINT rank1_le_two BEGIN
  let p : Protocol X Y :=
    Protocol.alice u
      (Protocol.bob v (Protocol.leaf true) (Protocol.leaf false))
      (Protocol.leaf false)
  have hp : p.Computes (fun x y => u x && v y) := by
    intro x y
    show (if u x = true then (if v y = true then true else false) else false) = (u x && v y)
    by_cases hu : u x = true
    · simp [hu, if_bit_eq_self]
    · have hu' : u x = false := Bool.not_eq_true _ ▸ hu
      simp [hu']
  exact D_le p hp
  -- CHECKPOINT rank1_le_two END

end LogRank
