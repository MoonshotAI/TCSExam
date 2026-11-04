/-
Statement layer for Valiant's matrix-rigidity problem (Valiant 1977,
"Graph-theoretic arguments in low-level complexity", MFCS), instantiated to a
concrete candidate family: the Hilbert matrices over the rationals.

The rigidity `R_A(r)` of an `n × n` matrix `A` is the minimum number of entries
one must modify to bring the rank down to at most `r`. Valiant's question asks
for an *explicit* family `{A_n}` and fixed constants `ε, δ > 0` with
`R_{A_n}(ε·n) ≥ n^{1+δ}` for all `n`; such a family would yield the first
super-linear explicit circuit lower bound (linear circuits of linear size and
logarithmic depth cannot compute `x ↦ A x`). Almost all matrices are rigid,
but no explicit family is known; the previously favored candidates
(Walsh–Hadamard, Fourier, circulant) were proved *not* rigid in the required
parameter regime (Alman–Williams 2017; Dvir–Liu 2020). The Hilbert matrix
(a Cauchy matrix, entry `1/(i+j+1)`, hence totally regular) belongs to the
candidate class for which the best known lower bound `Ω((n²/r)·log(n/r))`
applies (Shokrollahi–Spielman–Stemann 1997) and no non-rigidity result is
known; see `tests/reference/concept-ledger.md` for the fidelity discussion,
including why the conjecture is stated for one concrete candidate family
rather than as an existential over "explicit" families.

The fixed part (everything above the end-of-fixed-part marker line) is the
definition layer the statements need. Fidelity notes and small-case numerical
evidence live in `tests/reference/`.
-/

import Mathlib

namespace ExplicitRigidMatrix

open Matrix

/-! ## The rigidity predicate -/

variable {K : Type*} [Field K]

/-- The number of positions where two `n × n` matrices differ: the "number of
entries to modify" in the definition of rigidity. -/
def diffCount {n : ℕ} [DecidableEq K] (A B : Matrix (Fin n) (Fin n) K) : ℕ :=
  (Finset.univ.filter fun ij : Fin n × Fin n => A ij.1 ij.2 ≠ B ij.1 ij.2).card

/-- `A` is `(r, s)`-rigid iff every matrix of rank at most `r` differs from `A`
in at least `s` entries. Equivalently: Valiant's rigidity value satisfies
`R_A(r) ≥ s`. -/
def IsRigidAt {n : ℕ} [DecidableEq K] (A : Matrix (Fin n) (Fin n) K) (r s : ℕ) : Prop :=
  ∀ B : Matrix (Fin n) (Fin n) K, B.rank ≤ r → s ≤ diffCount A B

/-! ## The candidate explicit family: Hilbert matrices over `ℚ` -/

/-- The `n × n` Hilbert matrix over `ℚ`: entry `(i, j)` is `1 / (i + j + 1)`.
Entries are given by a closed formula, so the family is explicit in Valiant's
sense. -/
def hilbert (n : ℕ) : Matrix (Fin n) (Fin n) ℚ :=
  of fun i j => ((i : ℚ) + (j : ℚ) + 1)⁻¹

/-- The rigidity conjecture for the Hilbert family: there exist fixed rational
constants `ε, δ > 0` such that for every `n`, reducing the rank of the `n × n`
Hilbert matrix to at most `ε·n` requires modifying at least `n^{1+δ}` entries
(`⌊ε·n⌋` and `⌈n^{1+δ}⌉` are the natural-number readings of the thresholds). -/
def HilbertRigid : Prop :=
  ∃ ε δ : ℚ, 0 < ε ∧ 0 < δ ∧ ∀ n : ℕ,
    IsRigidAt (hilbert n) ⌊ε * (n : ℚ)⌋₊ ⌈(n : ℝ) ^ (1 + (δ : ℝ))⌉₊

/-! ## A sampled `{0,1}`-valued matrix (special case (c)) -/

/-- An explicit `{0,1}`-valued `4 × 4` matrix over `ℚ`, drawn uniformly at
random (sampling script, seed and log: `tests/reference/small-examples.md`);
all its sixteen `3 × 3` minors are nonzero. -/
def sampleMatrix4 : Matrix (Fin 4) (Fin 4) ℚ :=
  of ![![1, 1, 1, 0], ![0, 0, 1, 1], ![0, 1, 0, 1], ![1, 0, 0, 1]]

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

/-! ## Slot zone: the conjecture, its negation, and three special cases -/

-- @[slot main]
/-- The conjecture `P`: the Hilbert family is rigid in Valiant's sense.
Proving this resolves Valiant's 1977 problem in the affirmative (the Hilbert
family is explicit), and implies super-linear lower bounds for linear
circuits. -/
theorem conj : HilbertRigid := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

-- @[slot main]
/-- The refutation `¬P`: the Hilbert family is not rigid in Valiant's sense.
Proving this rules out the Hilbert/Cauchy candidate, in the spirit of the
Alman–Williams (Hadamard) and Dvir–Liu (Fourier, circulant) non-rigidity
theorems. -/
theorem refuted : ¬ HilbertRigid := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

end ExplicitRigidMatrix
