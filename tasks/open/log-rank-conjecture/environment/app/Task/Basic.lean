/-
Self-contained statement layer for the log-rank conjecture of communication
complexity (Lovász–Saks, "Lattices, Möbius functions and communication
complexity", FOCS 1988; journal version JCSS 1993): every two-party Boolean
function `f` with communication matrix `A` satisfies
`D(f) ≤ (log₂ rank A)^{O(1)}`, where `rank` is the rank over the reals and
`D` is the deterministic two-party communication complexity.

The fixed part (everything above the end-of-fixed-part marker line) is the
definition layer the conjecture statement needs. Fidelity notes live in
`tests/reference/`.
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

/-! ## The inner-product function on two-bit strings -/

/-- The mod-2 inner product on `2`-bit strings: `ip2 x y = x₀·y₀ ⊕ x₁·y₁`,
computed in `ZMod 2`.  Its `4 × 4` communication matrix has rank `3`. -/
def ip2 : (Fin 2 → Fin 2) → (Fin 2 → Fin 2) → Bool :=
  fun x y => decide ((x 0 * y 0 + x 1 * y 1 : ZMod 2) = 1)

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- but the fixed part above and the two slot statements must not be modified.

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

end LogRank
