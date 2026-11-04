/-
Self-contained statement layer for the open conjecture on deterministic vs.
randomized decision-tree complexity of total Boolean functions ("D vs R"):

  **Conjecture (open).** There is a universal constant `C` such that every
  total Boolean function `f : {0,1}ⁿ → {0,1}` satisfies
  `D(f) ≤ C · R(f)²`, where `D(f)` is the deterministic decision-tree
  complexity of `f` and `R(f)` its randomized (two-sided error `1/3`)
  decision-tree complexity.

  Status: Nisan 1991 (*CREW PRAMs and decision trees*, SICOMP 20(6)) proved
  `D(f) = O(R(f)³)`; the best separation known is quadratic — total
  functions with `D(f) = Ω̃(R(f)²)` (pointer-function constructions,
  Ambainis–Balodis–Belovs–Lee–Santha–Smotrovs, JACM 2017).  Whether the
  optimal exponent is 2 or 3 is open (Hamoudi 2025 survey, arXiv 2508.08852,
  Proposition 9, still records `D(f) = O(R(f)³)` as the best known relation).

This file is the task's definition zone plus statement zone:
- The definition zone (everything above the end-of-fixed-part marker line)
  defines decision trees and their cost, the deterministic complexity `D f`,
  randomized decision trees as finite weighted families of deterministic
  trees with their expected cost and per-input error probability, the
  randomized complexity `Rc f`, and auxiliary notions (Hamming weight,
  symmetric and non-constant functions, strict majority, function
  composition).
- The statement zone (below the marker) carries two conjecture slots —
  `conj` (the conjecture itself) and `refuted` (its negation) — each with
  its proof body left blank; proving either one scores full marks.

Fidelity notes (deviations from the informal literature, all documented in
`tests/reference/concept-ledger.md`):
1. A randomized decision tree is formalized as a *finite weighted family*
   of deterministic trees (a finite-support distribution), with cost =
   worst-case *expected* number of queries over inputs and error = worst-case
   per-input error probability ≤ 1/3.  Up to constant factors (Markov +
   amplification) this is the standard `R(f)` of the literature, and the
   conjecture — a single polynomial relation with a free constant `C` — is
   invariant under such factor changes.
2. `D f` and `Rc f` are defined as `sInf` over the feasible depth/cost sets,
   so they are total on every `f` (constant functions included: `D = Rc = 0`);
   the conjecture statement holds trivially on those degenerate cases.
3. `majFn n` is *strict* majority (`weight > n/2`); only `majFn 3` is used.
4. Composition `comp f g` acts on `Fin (m * n) → Bool` via the canonical
   equivalence `finProdFinEquiv : Fin m × Fin n ≃ Fin (m * n)`.
-/
import Mathlib

open Classical

namespace DVR

/-! ## Deterministic decision trees and `D f` -/

/-- A deterministic decision tree on `n` Boolean variables: a leaf outputs a
bit; an internal node queries one variable and branches on its value. -/
inductive DTree (n : ℕ) : Type where
  | leaf : Bool → DTree n
  | node : Fin n → DTree n → DTree n → DTree n

/-- The output of the tree on input `x`: at a node querying `i`, take the
left child when `x i` is false and the right child when it is true. -/
def DTree.eval {n : ℕ} : DTree n → (Fin n → Bool) → Bool
  | leaf b, _ => b
  | node i l r, x => if x i then eval r x else eval l x

/-- The number of queries the tree makes on input `x` (the depth of the path
it takes). -/
def DTree.cost {n : ℕ} : DTree n → (Fin n → Bool) → ℕ
  | leaf _, _ => 0
  | node i l r, x => 1 + (if x i then cost r x else cost l x)

/-- The tree computes `f`: it is correct on every input. -/
def DTree.Computes {n : ℕ} (T : DTree n) (f : (Fin n → Bool) → Bool) : Prop :=
  ∀ x, T.eval x = f x

/-- Deterministic decision-tree complexity `D(f)`: the least worst-case
number of queries of a tree computing `f`.  Defined as `sInf` of the
feasible depths; the set is nonempty (the full-query tree witnesses depth
`n`), so `sInf` is the genuine minimum. -/
noncomputable def D {n : ℕ} (f : (Fin n → Bool) → Bool) : ℕ :=
  sInf {d : ℕ | ∃ T : DTree n, T.Computes f ∧ ∀ x, T.cost x ≤ d}

/-! ## Randomized decision trees and `Rc f` -/

/-- A randomized decision tree on `n` variables: a finite-support probability
distribution over deterministic trees, given as a finite type `ι` of indices,
one deterministic tree per index, and weights summing to `1`. -/
structure RTree (n : ℕ) where
  ι : Type
  [fin : Fintype ι]
  tree : ι → DTree n
  w : ι → ℝ
  w_nonneg : ∀ i, 0 ≤ w i
  w_sum : ∑ i, w i = 1

attribute [instance] RTree.fin

/-- The expected number of queries of a randomized tree on input `x`. -/
noncomputable def RTree.expCost {n : ℕ} (R : RTree n) (x : Fin n → Bool) : ℝ :=
  ∑ i, R.w i * ((R.tree i).cost x : ℝ)

/-- The error probability of a randomized tree computing `f` on input `x`:
the total weight of trees whose output differs from `f x`. -/
noncomputable def RTree.errProb {n : ℕ} (R : RTree n) (f : (Fin n → Bool) → Bool)
    (x : Fin n → Bool) : ℝ :=
  ∑ i, R.w i * (if (R.tree i).eval x = f x then (0 : ℝ) else 1)

/-- Randomized decision-tree complexity `R(f)` with two-sided error `1/3`:
the infimum, over randomized trees whose per-input error is at most `1/3`,
of the worst-case expected number of queries.  Defined as `sInf` of the
feasible costs; the set is nonempty (any deterministic tree computing `f`,
as a degenerate one-tree distribution, has error `0`) and bounded below by
`0`. -/
noncomputable def Rc {n : ℕ} (f : (Fin n → Bool) → Bool) : ℝ :=
  sInf {c : ℝ | ∃ R : RTree n, (∀ x, R.errProb f x ≤ 1 / 3) ∧ ∀ x, R.expCost x ≤ c}

/-! ## Symmetric functions, majority, composition -/

/-- The Hamming weight of an input. -/
def weight {n : ℕ} (x : Fin n → Bool) : ℕ :=
  ∑ i, (x i).toNat

/-- `f` is symmetric: its value depends only on the Hamming weight of the
input. -/
def Symmetric {n : ℕ} (f : (Fin n → Bool) → Bool) : Prop :=
  ∀ x y, weight x = weight y → f x = f y

/-- `f` is non-constant. -/
def Nonconstant {n : ℕ} (f : (Fin n → Bool) → Bool) : Prop :=
  ∃ x y, f x ≠ f y

/-- Strict majority on `n` bits: true iff more than half the bits are true. -/
def majFn (n : ℕ) : (Fin n → Bool) → Bool :=
  fun x => decide (n < 2 * weight x)

/-- The composed function `f ∘ g` on `m × n` bits: apply `g` to each of the
`m` blocks of `n` bits, then `f` to the `m` results.  Blocks are indexed by
`finProdFinEquiv : Fin m × Fin n ≃ Fin (m * n)`. -/
def comp {m n : ℕ} (f : (Fin m → Bool) → Bool) (g : (Fin n → Bool) → Bool) :
    (Fin (m * n) → Bool) → Bool :=
  fun x => f fun i => g fun j => x (finProdFinEquiv (i, j))

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

/-! ## Slot zone: the conjecture, its negation, and three checkpoints

Prove **either** `conj` (the conjecture) **or** `refuted` (its negation) for
full credit.  Three special-case checkpoints follow, each worth one third of
partial credit. -/

-- @[slot main]
/-- The conjecture slot: deterministic decision-tree complexity is at most a
constant times the square of the randomized complexity, for every total
Boolean function. -/
theorem conj : ∃ C : ℝ, ∀ (n : ℕ) (f : (Fin n → Bool) → Bool),
    (D f : ℝ) ≤ C * (Rc f) ^ 2 := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

-- @[slot main]
/-- The refutation slot: the negation of the conjecture. -/
theorem refuted : ¬ ∃ C : ℝ, ∀ (n : ℕ) (f : (Fin n → Bool) → Bool),
    (D f : ℝ) ≤ C * (Rc f) ^ 2 := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

end DVR
