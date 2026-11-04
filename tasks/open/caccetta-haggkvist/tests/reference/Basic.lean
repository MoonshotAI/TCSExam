/-
Self-contained definition and statement layer for the Caccetta–Häggkvist
conjecture:

  Caccetta, Häggkvist, *On minimal digraphs with given girth*, Proceedings of
  the 9th Southeastern Conference on Combinatorics, Graph Theory and Computing
  (Congressus Numerantium 21), 1978, pp. 181–187.

Conjecture. For every integer k ≥ 1, every loopless digraph D on n vertices
with minimum out-degree at least k contains a directed cycle of length at
most ⌈n/k⌉.  The case k = ⌈n/3⌉ (out-degree n/3 forces a directed triangle)
is the most famous open case; the constant cases k = 1, …, 5 are theorems
(k = 1 trivial; k = 2 by Caccetta–Häggkvist; k = 3 by Hamidoune; k = 4 and
5 by Hoáng–Reed — see B. D. Sullivan's 2006 survey, arXiv:math/0605646).

This file is the task's definition zone plus statement zone:

- The definition zone (FIXED PART) builds a minimal digraph layer against
  mathlib only: loopless digraphs with boolean adjacency, out-degree,
  directed cycles as injective vertex sequences indexed by `Fin ℓ` (indices
  read modulo ℓ, so the last vertex arcs back to the first), the predicate
  "there is a directed cycle of length at most m" with a `Decidable`
  instance, and the circulant family used as tightness witnesses.
- The statement zone contains the conjecture (`conj`) and its negation
  (`refuted`), each with its proof body left blank; proving either one
  scores full marks.

Fidelity notes (see `tests/reference/concept-ledger.md` of the packaged
task):
1. The ceiling ⌈n/k⌉ is written as natural division `(n + k - 1) / k`,
   valid for k ≥ 1; the hypothesis `1 ≤ k` is part of the statements.
2. The digraph is required to be loopless, as in the original paper; the
   vertex set is assumed nonempty (`[Nonempty V]`) — for k ≥ 1 the
   out-degree hypothesis is vacuous on the empty type, which would make the
   bare statement false there.
3. Directed cycles are *simple* (injective sequence), matching the standard
   definition; the conjecture is usually stated with "cycle" meaning simple
   directed cycle.
-/

import Mathlib

namespace CaccettaHaggkvist

/-- A loopless directed graph on a vertex type `V` with boolean adjacency:
`adj v w = true` means the arc `v → w` is present.  Loops are excluded by
`loopless`; 2-cycles (`v → w → v`) are allowed, as in the original
statement of the conjecture. -/
structure Digraph (V : Type*) where
  adj : V → V → Bool
  loopless : ∀ v, adj v v = false

namespace Digraph

variable {V : Type*}

/-- Out-degree of `v`: the number of out-neighbors of `v`. -/
def outDegree (D : Digraph V) [Fintype V] (v : V) : ℕ :=
  (Finset.univ.filter fun w => D.adj v w).card

/-- The successor of `i` in `Fin ℓ`, wrapping around to `0` at the end
(`Fin ℓ` is nonempty because `i` lives in it, so `ℓ ≥ 1`). -/
def cycSucc {ℓ : ℕ} (i : Fin ℓ) : Fin ℓ :=
  ⟨(i.val + 1) % ℓ, Nat.mod_lt _ (Nat.lt_of_le_of_lt (Nat.zero_le i.val) i.isLt)⟩

/-- A directed cycle of length `ℓ`, given as an injective sequence of
vertices `f 0, f 1, …, f (ℓ−1)` with an arc from each vertex to the next
(indices read modulo `ℓ`, so the last vertex arcs back to the first).
Injectivity makes the cycle simple, matching the standard definition of a
directed cycle. -/
def IsCycle (D : Digraph V) {ℓ : ℕ} (f : Fin ℓ → V) : Prop :=
  Function.Injective f ∧ ∀ i, D.adj (f i) (f (cycSucc i)) = true

/-- `IsCycle` is decidable (the definition above is opaque to instance
resolution, so the instance is given explicitly). -/
instance (D : Digraph V) [DecidableEq V] {ℓ : ℕ} (f : Fin ℓ → V) :
    Decidable (D.IsCycle f) :=
  inferInstanceAs (Decidable (Function.Injective f ∧ ∀ i, D.adj (f i) (f (cycSucc i)) = true))

/-- `D` contains a directed cycle of length at most `m`. -/
def HasCycleOfLengthLe (D : Digraph V) (m : ℕ) : Prop :=
  ∃ (ℓ : ℕ) (f : Fin ℓ → V), 1 ≤ ℓ ∧ ℓ ≤ m ∧ D.IsCycle f

/-- Bounded restatement of `HasCycleOfLengthLe`: the length quantifier only
ranges over `Fin (m + 1)`, which is a `Fintype`, so this form is decidable.
It backs the `Decidable` instance below. -/
theorem hasCycleOfLengthLe_iff_bounded (D : Digraph V) (m : ℕ) :
    (∃ ℓ : Fin (m + 1), ∃ f : Fin ℓ.val → V, ℓ.val ≠ 0 ∧ D.IsCycle f) ↔
      D.HasCycleOfLengthLe m := by
  constructor
  · rintro ⟨ℓ, f, h0, hf⟩
    exact ⟨ℓ.val, f, Nat.pos_of_ne_zero h0, Nat.le_of_lt_succ ℓ.isLt, hf⟩
  · rintro ⟨ℓ, f, h1, hm, hf⟩
    exact ⟨⟨ℓ, Nat.lt_succ_of_le hm⟩, f, Nat.ne_zero_of_lt h1, hf⟩

/-- Existence of a short directed cycle is decidable (used by `decide` for
the small tightness witnesses). -/
instance (D : Digraph V) [Fintype V] [DecidableEq V] (m : ℕ) :
    Decidable (D.HasCycleOfLengthLe m) :=
  decidable_of_iff _ (D.hasCycleOfLengthLe_iff_bounded m)

/-- The circulant digraph on `Fin n` with jumps `1, …, k`: an arc `i → j`
is present exactly when `(j − i) mod n ∈ {1, …, k}`.  For `2 * k < n` every
vertex has out-degree exactly `k`, and the family achieves the bound of the
conjecture (its directed girth is `⌈n / k⌉`), which makes it the standard
tightness witness. -/
def circulant (n k : ℕ) : Digraph (Fin n) where
  adj := fun i j =>
    let d := (j.val + n - i.val) % n
    decide (1 ≤ d) && decide (d ≤ k)
  loopless := by
    intro i
    simp

end Digraph

-- Kernel evaluation of the decidable instances in this file (enumeration
-- over all injective sequences on small vertex sets) needs a recursion
-- depth beyond the default.  The limit only affects elaboration;
-- every proof is still fully checked by the kernel.
set_option maxRecDepth 1000000

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

/-- **The Caccetta–Häggkvist conjecture.** Every loopless digraph on a
nonempty finite vertex set with minimum out-degree at least `k ≥ 1` contains
a directed cycle of length at most `⌈n / k⌉` (written as the natural
division `(n + k − 1) / k`).  Prove this slot for full credit. -/
theorem conj : ∀ (V : Type) [Fintype V] [Nonempty V] (D : Digraph V) (k : ℕ),
    1 ≤ k → (∀ v, k ≤ D.outDegree v) →
    D.HasCycleOfLengthLe ((Fintype.card V + k - 1) / k) := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

/-- **Refutation of the conjecture.** The negation of `conj`: there is a
loopless digraph on a nonempty finite vertex set and some `k ≥ 1` with
minimum out-degree at least `k` but no directed cycle of length at most
`⌈n / k⌉`.  Prove this slot for full credit. -/
theorem refuted : ¬ ∀ (V : Type) [Fintype V] [Nonempty V] (D : Digraph V) (k : ℕ),
    1 ≤ k → (∀ v, k ≤ D.outDegree v) →
    D.HasCycleOfLengthLe ((Fintype.card V + k - 1) / k) := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

end CaccettaHaggkvist
