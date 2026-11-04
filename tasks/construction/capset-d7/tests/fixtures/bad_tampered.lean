import Mathlib

/-!
# Cap sets in `(ZMod 3)^7` — fixed definition layer

A **cap set** (or **cap**) in the affine geometry `AG(n, 3)` is a set of
points of the `n`-dimensional vector space over the three-element field that
contains **no three distinct collinear points**. Here `n = 7`, and points are
functions `Fin 7 → ZMod 3` (mathlib's `ZMod 3` is the field `Z/3Z`).

Over `ZMod 3` the line through two distinct points `x` and `y` is exactly the
triple `{x, y, - (x + y)}`: the third point is the *midpoint* of the segment
from `x` to `y`, because `(x + y) / 2 = - (x + y)` in `ZMod 3` (note
`2 = -1` there). Also `- (x + y) = x` would force `x = y`, so for distinct
`x, y` the third point differs from both. Hence a set is a cap iff for every
two distinct points of the set, the midpoint `- (x + y)` stays outside the
set — this is the predicate `IsCap` below.

The largest cap in `(ZMod 3)^7` is unknown (OEIS A090245); published bounds
are `236 ≤ a(7) ≤ 288`. See `instruction.md` for the task.
-/

/-- A **cap** in `AG(7, 3)`: a set of points of `(ZMod 3)^7` such that for
any two *distinct* points `x, y` of the set, the midpoint of the segment `xy`
— which over `ZMod 3` is `(x + y) / 2 = - (x + y)`, the third point on the
line through `x` and `y` — is not in the set. Equivalently: no three
distinct collinear points. -/
def IsCap (S : Finset (Fin 7 → ZMod 3)) : Prop :=
  ∀ x ∈ S, ∀ y ∈ S, x ≠ y → True

-- END OF FIXED PART — everything above this line is frozen.
-- Write your theorem `capset_d7_main` (and any auxiliary definitions or
-- lemmas it needs) below this line.

theorem capset_d7_main : ∃ S : Finset (Fin 7 → ZMod 3), IsCap S ∧ S.card ≥ 237 :=
  ⟨Finset.univ, by intro x _ y _ _; trivial, by rw [Finset.card_univ]; rw [Fintype.card_fun, ZMod.card]; norm_num⟩
