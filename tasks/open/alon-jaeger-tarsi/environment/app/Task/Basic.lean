/-
Self-contained statement layer for the Alon–Jaeger–Tarsi conjecture
(prime-field form).

The conjecture (Alon–Jaeger–Tarsi, first proposed by Jaeger in 1981;
statement as in arXiv:math/0510025): for every finite field `F` with `|F| ≥ 4` and every
nonsingular square matrix `A` over `F`, there exists a vector `x` such that
`x` and `A x` are both nowhere-zero (every component nonzero). The non-prime
finite fields were settled by Alon–Tarsi (1989) via the polynomial method,
and the prime fields with `p > 61`, `p ≠ 79` by Nagy–Pach
(arXiv:2107.03956, 2021); the remaining open case is exactly the prime-field
statement packaged below as `AJTConjecture`. The statement is false over
`ZMod 2` and `ZMod 3` — known counterexamples — which is why the threshold
is `p ≥ 5`.

This file is the task's definition zone plus proof-slot zone:
- Definition zone (fixed): `NowhereZero`, `HasAJTVector`, `AJTConjecture`,
  and the supporting decidability instances.
- Proof-slot zone: the two main slots `conj` (the conjecture) and `refuted`
  (its negation); proving either one scores full marks.
-/

import Mathlib

namespace AlonJaegerTarsi

open Matrix

/-! ## Definition zone (fixed) -/

/-- A vector is nowhere-zero when every component is nonzero. -/
def NowhereZero {α F : Type*} [Zero F] (x : α → F) : Prop :=
  ∀ i, x i ≠ 0

/-- The Alon–Jaeger–Tarsi property of a square matrix: some nowhere-zero
vector `x` has a nowhere-zero image `A *ᵥ x`.  The property makes sense over
any commutative ring; the conjecture itself restricts to prime fields. -/
def HasAJTVector {n : ℕ} {F : Type*} [CommRing F] (A : Matrix (Fin n) (Fin n) F) : Prop :=
  ∃ x : Fin n → F, NowhereZero x ∧ NowhereZero (A *ᵥ x)

/-- The Alon–Jaeger–Tarsi conjecture, remaining prime-field form: for every
prime `p ≥ 5`, every dimension `n` and every nonsingular matrix `A` over
`ZMod p` (`A.det ≠ 0`), some vector `x` is nowhere-zero together with its
image `A *ᵥ x`.  (Over a field, `A.det ≠ 0` is exactly nonsingularity, see
`Matrix.isUnit_iff_isUnit_det`.) -/
def AJTConjecture : Prop :=
  ∀ (p : ℕ) [Fact p.Prime], 5 ≤ p → ∀ (n : ℕ) (A : Matrix (Fin n) (Fin n) (ZMod p)),
    A.det ≠ 0 → HasAJTVector A

/-- Decidability of nowhere-zero vectors over finite index and value types
(backs `decide` proofs of the enumeration checkpoints). -/
instance decNowhereZero {α F : Type*} [Zero F] [Fintype α] [DecidableEq F] (x : α → F) :
    Decidable (NowhereZero x) :=
  inferInstanceAs (Decidable (∀ i, x i ≠ 0))

/-- Decidability of the Alon–Jaeger–Tarsi property over a finite commutative
ring (backs `decide` proofs of the enumeration checkpoints). -/
instance decHasAJTVector {n : ℕ} {F : Type*} [CommRing F] [Fintype F] [DecidableEq F]
    (A : Matrix (Fin n) (Fin n) F) :
    Decidable (HasAJTVector A) :=
  inferInstanceAs (Decidable (∃ x : Fin n → F, NowhereZero x ∧ NowhereZero (A *ᵥ x)))

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below, outside the CHECKPOINT slots.

/-- **The conjecture.** A complete proof of this theorem scores full credit. -/
theorem conj : AJTConjecture := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

/-- **The negated conjecture.** A complete proof of this theorem also scores
full credit: resolving the conjecture in either direction is a full solution. -/
theorem refuted : ¬ AJTConjecture := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

end AlonJaegerTarsi
