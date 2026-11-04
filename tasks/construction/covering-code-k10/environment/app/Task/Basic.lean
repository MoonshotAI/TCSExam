import Mathlib

/-!
# Binary covering codes of length 10 and radius 1 — fixed definition layer

A **binary covering code** of length 10 and radius 1 is a set `S` of
10-bit words such that every word of the cube `{0,1}^10` is within Hamming
distance 1 of some codeword — equivalently, a dominating set of the
10-dimensional hypercube graph. The smallest possible size is `K(10,1)`,
known only to lie in `107 ≤ K(10,1) ≤ 120` (see `instruction.md` for
references).

Words are functions `Fin 10 → Fin 2`; `hammingDist x y` (mathlib) counts
the coordinates on which `x` and `y` differ. `Covers S` below says the
radius-1 Hamming balls around the codewords of `S` cover the whole cube.
-/

/-- `Covers S` says that `S ⊆ {0,1}^10` is a **covering code of radius 1**:
every 10-bit word `w` agrees with some codeword `c ∈ S` in all but at most
one coordinate (`hammingDist w c ≤ 1`).

A proof of `Covers S` together with `S.card ≤ N` certifies
`K(10,1) ≤ N`.

Marked `@[reducible]` so that decidable instances for concrete codes are
found by typeclass resolution (`by native_decide` can check concrete
codes directly). -/
@[reducible]
def Covers (S : Finset (Fin 10 → Fin 2)) : Prop :=
  ∀ w : Fin 10 → Fin 2, ∃ c ∈ S, hammingDist w c ≤ 1

-- END OF FIXED PART — everything above this line is frozen.
-- Write your theorem `covering_code_k10_main` (and any auxiliary
-- definitions or lemmas it needs) below this line.
