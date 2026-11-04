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
  ∀ x ∈ S, ∀ y ∈ S, x ≠ y → - (x + y) ∉ S

-- END OF FIXED PART — everything above this line is frozen.
-- Write your theorem `capset_d7_main` (and any auxiliary definitions or
-- lemmas it needs) below this line.

/-- The cube `{0,1}⁷` embedded in `(ZMod 3)^7`: the image of all
`Fin 2`-valued vectors under the coordinatewise `Fin.val` cast. -/
def cube : Finset (Fin 7 → ZMod 3) :=
  Finset.univ.image fun v : Fin 7 → Fin 2 => fun i => ((v i).val : ZMod 3)

lemma cube_card : cube.card = 128 := by
  have hinj : Function.Injective
      (fun v : Fin 7 → Fin 2 => fun i => ((v i).val : ZMod 3)) := by
    intro v w h
    funext i
    have hi : ((v i).val : ZMod 3) = ((w i).val : ZMod 3) := congrFun h i
    have hv3 : (v i).val < 3 := Nat.lt_of_lt_of_le (v i).isLt (by norm_num)
    have hw3 : (w i).val < 3 := Nat.lt_of_lt_of_le (w i).isLt (by norm_num)
    have h2 : (v i).val % 3 = (w i).val % 3 := (ZMod.natCast_eq_natCast_iff _ _ _).mp hi
    have hval : (v i).val = (w i).val := by omega
    exact Fin.ext hval
  unfold cube
  rw [Finset.card_image_of_injective _ hinj, Finset.card_univ, Fintype.card_fun]
  norm_num [Fintype.card_fin]

lemma cube_isCap : IsCap cube := by
  intro x hx y hy hne hmem
  simp only [cube, Finset.mem_image] at hx hy hmem
  obtain ⟨v, -, hvx⟩ := hx
  obtain ⟨w, -, hwy⟩ := hy
  obtain ⟨u, -, hu⟩ := hmem
  have hvw : v ≠ w := fun h => hne (by rw [← hvx, ← hwy, h])
  obtain ⟨i, hi⟩ := Function.ne_iff.mp hvw
  have hxi : x i = ((v i).val : ZMod 3) := (congrFun hvx i).symm
  have hyi : y i = ((w i).val : ZMod 3) := (congrFun hwy i).symm
  have hui : (-(x + y)) i = ((u i).val : ZMod 3) := (congrFun hu i).symm
  have hne2 : (v i).val ≠ (w i).val := fun h => hi (Fin.ext h)
  have hab : (v i).val + (w i).val = 1 := by
    have ha := (v i).isLt
    have hb := (w i).isLt
    omega
  have hmid : (-(x + y)) i = ((2 : ℕ) : ZMod 3) := by
    rw [Pi.neg_apply, Pi.add_apply, hxi, hyi, ← Nat.cast_add, hab, Nat.cast_one]
    decide
  rw [hmid] at hui
  have hc := (u i).isLt
  have h2 : (2 : ℕ) % 3 = (u i).val % 3 := (ZMod.natCast_eq_natCast_iff _ _ _).mp hui
  omega

theorem capset_d7_main : ∃ S : Finset (Fin 7 → ZMod 3), IsCap S ∧ S.card ≥ 128 := by
  exact ⟨cube, cube_isCap, by rw [cube_card]⟩

