/-
Self-contained statement layer for a theorem in online algorithms:
a constant-competitive deterministic algorithm for the 3-taxi problem on
general metric spaces.

This file is the task's definition zone plus checkpoint zone:
- The definition zone re-implements, against mathlib only, the objects of the
  statement layer: the metric layer with bridges and tripods (the
  branching-point length formula and the virtual-point hypotheses), the
  constants of the speed/potential hierarchy, the distorted
  minimum-matching potential M and the interval-spacing potential Σ with
  Φ = αM + βΣ, the algorithm TripodTracker itself (the movement phase as
  an explicit piecewise-affine function, the reorganization, and the free
  relocation), the per-request transition (offline movement, online
  movement, reorganization, relocation), and the trajectory semantics
  with its cost accounting.
- The checkpoint zone states the main theorem, with its proof body left
  blank.

Packaging notes: the speed/potential constants are instantiated numerically
(a = 10⁻⁴, b = 10⁻², ψ = 10⁻¹, β = 10², α = 10⁵) and every checkpoint
statement is self-contained (no external facts are packaged as hypotheses).
Fidelity deviations from the source text are documented in
`tests/reference/concept-ledger.md` of the packaged task.
-/

import Mathlib

namespace ThreeTaxi

/-! ## The metric layer: distances, bridges, tripods -/

/-- The branching-point length formula: for the tripod
`B(x, y, z)` with center `e`, `tripodC (d x y) (d x z) (d y z)` is the length
of the `x`-edge, `(xy + xz − yz)/2`. -/
noncomputable def tripodC (dxy dxz dyz : ℝ) : ℝ := (dxy + dxz - dyz) / 2

/-- A metric layer with bridges and tripods: a distance function satisfying
the metric axioms, such that between any two points there is a point at every
intermediate distance along a shortest path (the bridge hypothesis), and such
that any three points admit a branching point with edge lengths given by the
branching-point formula (the tripod hypothesis). -/
class TaxiMetric (S : Type) where
  dist : S → S → ℝ
  dist_self : ∀ x : S, dist x x = 0
  dist_comm : ∀ x y : S, dist x y = dist y x
  dist_triangle : ∀ x y z : S, dist x z ≤ dist x y + dist y z
  bridge : ∀ x y : S, ∀ t : ℝ, 0 ≤ t → t ≤ dist x y →
    ∃ p : S, dist x p = t ∧ dist p y = dist x y - t
  tripod : ∀ x y z : S, ∃ e : S,
    dist x e = tripodC (dist x y) (dist x z) (dist y z) ∧
    dist y e = tripodC (dist x y) (dist y z) (dist x z) ∧
    dist z e = tripodC (dist x z) (dist y z) (dist x y)

section

variable {S : Type} [TaxiMetric S]

open TaxiMetric

theorem dist_nonneg (x y : S) : 0 ≤ dist x y := by
  have h := TaxiMetric.dist_triangle x y x
  rw [TaxiMetric.dist_self x, TaxiMetric.dist_comm y x] at h
  linarith

/-- The triangle inequality in difference form. -/
theorem abs_dist_sub_le (x y z : S) : |dist x z - dist y z| ≤ dist x y := by
  rw [abs_le]
  constructor
  · have h := TaxiMetric.dist_triangle y x z
    rw [TaxiMetric.dist_comm y x] at h
    linarith
  · have h := TaxiMetric.dist_triangle x y z
    linarith

/-- The `x`-edge length of a tripod is nonnegative (the branching-point
formula and the triangle inequality). -/
theorem tripodC_nonneg (x y z : S) :
    0 ≤ tripodC (dist x y) (dist x z) (dist y z) := by
  have h := TaxiMetric.dist_triangle y x z
  rw [TaxiMetric.dist_comm y x] at h
  unfold tripodC
  linarith

/-- A symmetric variant: `(xy + yz − xz)/2 ≥ 0`. -/
theorem tripodC_nonneg' (x y z : S) :
    0 ≤ tripodC (dist x y) (dist y z) (dist x z) := by
  have h := TaxiMetric.dist_triangle x y z
  unfold tripodC
  linarith

/-- The two passive-side edge lengths sum to the base: `x2e + x3e = x2x3`. -/
theorem tripodC_add (dd d2 d3 : ℝ) :
    tripodC dd d2 d3 + tripodC dd d3 d2 = dd := by
  unfold tripodC; ring

/-- The `x`-edge and `y`-edge of a tripod sum to `xy`: `xe + ye = xy`. -/
theorem tripodC_edge_sum (dxy dxz dyz : ℝ) :
    tripodC dxy dxz dyz + tripodC dxy dyz dxz = dxy := by
  unfold tripodC; ring

/-- The endpoints' edge lengths sum to the path length through the center:
`xe + er = xr` when `u = xe` and `er` are computed from the same triple. -/
theorem tripodC_path (dd d2 d3 : ℝ) :
    tripodC dd d2 d3 + tripodC d2 d3 dd = d2 := by
  unfold tripodC; ring

end

/-! ## The constants of the speed/potential hierarchy -/

/-- The active-taxi speed `a = ε⁴` at `ε = 1/10`. -/
noncomputable def cA : ℝ := 1 / 10000

/-- The fast-passive speed boost `b = ε²`: fast movement is at speed `1 + b`. -/
noncomputable def cB : ℝ := 1 / 100

/-- The discount factor `ψ = ε`. -/
noncomputable def cPsi : ℝ := 1 / 10

/-- The coefficient `β = ε⁻²` of the spacing potential Σ. -/
noncomputable def cBeta : ℝ := 100

/-- The coefficient `α = ε⁻⁵` of the matching potential M. -/
noncomputable def cAlpha : ℝ := 100000

theorem cA_pos : 0 < cA := by unfold cA; norm_num

theorem cB_pos : 0 < cB := by unfold cB; norm_num

theorem cPsi_pos : 0 < cPsi := by unfold cPsi; norm_num

theorem cPsi_lt_one : cPsi < 1 := by unfold cPsi; norm_num

theorem cBeta_pos : 0 < cBeta := by unfold cBeta; norm_num

theorem cAlpha_pos : 0 < cAlpha := by unfold cAlpha; norm_num

/-- The reciprocal `1/(1+b)` of the fast speed (used to state the case-B
arrival time multiplicatively). -/
noncomputable def cB1 : ℝ := 1 / (1 + cB)

theorem cB1_val : cB1 = 100 / 101 := by unfold cB1 cB; norm_num

theorem cB1_mul : (1 + cB) * cB1 = 1 := by unfold cB1 cB; norm_num

theorem cB1_pos : 0 < cB1 := by unfold cB1 cB; norm_num

/-! ## The distorted matching potential M and the spacing potential Σ -/

/-- The discounted contribution of the passive-online/offline pair `(xi, y)`
to the matching potential: `d(xi,y) − ψ·(min(ℓi, xi·g) + y·g)`, where `g` is
the branching point of `B(x2, x3, y)`. Here `dd = d(x2,x3)`, `dxy = d(xi,y)`,
`djy = d(xj,y)` for the other passive taxi `xj`, and `ℓi` is `xi`'s interval
length; `tripodC dd dxy djy = xi·g` and `tripodC dxy djy dd = y·g` by the
branching-point formula. This is the path integral `∫_{P_i} f_i dz`: portions
within `xi`'s own interval and on the `y`-edge are discounted at `1 − ψ`. -/
noncomputable def distContrib (dd dxy djy ℓi : ℝ) : ℝ :=
  dxy - cPsi * (min ℓi (tripodC dd dxy djy) + tripodC dxy djy dd)

/-- The weight of the matching that pairs `x2` with `yA` and `x3` with `yB`:
the two passive contributions. Arguments: the base distance `dd`, the four
endpoint distances, and the interval lengths. -/
noncomputable def matchSum (dd d2yA d3yA d3yB d2yB ℓ2 ℓ3 : ℝ) : ℝ :=
  distContrib dd d2yA d3yA ℓ2 + distContrib dd d3yB d2yB ℓ3

/-- The distorted matching potential `M`: the active pair contributes its
undistorted distance, the passive pairs are matched to minimize the total
discounted weight. Arguments: `x1y1`, the passive base `dd`,
the four passive-offline distances, and the interval lengths. -/
noncomputable def Mpot (x1y1 dd d2y2 d3y2 d2y3 d3y3 ℓ2 ℓ3 : ℝ) : ℝ :=
  x1y1 + min (matchSum dd d2y2 d3y2 d3y3 d2y3 ℓ2 ℓ3)
    (matchSum dd d2y3 d3y3 d3y2 d2y2 ℓ2 ℓ3)

/-- The spacing potential `Σ = max(0, min(ℓ2, ℓ3) − q2q3)` with
`q2q3 = x2x3 − ℓ2 − ℓ3`. -/
noncomputable def SigmaPot (dd ℓ2 ℓ3 : ℝ) : ℝ := max 0 (min ℓ2 ℓ3 - (dd - ℓ2 - ℓ3))

/-- The total potential `Φ = αM + βΣ`. -/
noncomputable def Phi (x1y1 dd d2y2 d3y2 d2y3 d3y3 ℓ2 ℓ3 : ℝ) : ℝ :=
  cAlpha * Mpot x1y1 dd d2y2 d3y2 d2y3 d3y3 ℓ2 ℓ3 + cBeta * SigmaPot dd ℓ2 ℓ3

/-! ## Configurations -/

/-- An online configuration: the active taxi `x1`, the passive taxis
`x2, x3`, and the interval lengths `ℓ2, ℓ3`. -/
structure OState (S : Type) [TaxiMetric S] where
  x1 : S
  x2 : S
  x3 : S
  ℓ2 : ℝ
  ℓ3 : ℝ

/-- A full configuration: the online configuration together with the offline
taxi locations `y1` (active), `y2, y3` (passive). -/
structure FState (S : Type) [TaxiMetric S] where
  x1 : S
  x2 : S
  x3 : S
  ℓ2 : ℝ
  ℓ3 : ℝ
  y1 : S
  y2 : S
  y3 : S

section

variable {S : Type} [TaxiMetric S]

open TaxiMetric

/-- The potential of a full configuration. -/
noncomputable def FState.phi (st : FState S) : ℝ :=
  Phi (dist st.x1 st.y1) (dist st.x2 st.x3) (dist st.x2 st.y2) (dist st.x3 st.y2)
    (dist st.x2 st.y3) (dist st.x3 st.y3) st.ℓ2 st.ℓ3

/-- The spacing potential of a configuration (online part only). -/
noncomputable def FState.sigma (st : FState S) : ℝ := SigmaPot (dist st.x2 st.x3) st.ℓ2 st.ℓ3

/-- The matching potential of a full configuration. -/
noncomputable def FState.mpot (st : FState S) : ℝ :=
  Mpot (dist st.x1 st.y1) (dist st.x2 st.x3) (dist st.x2 st.y2) (dist st.x3 st.y2)
    (dist st.x2 st.y3) (dist st.x3 st.y3) st.ℓ2 st.ℓ3

/-- The offline taxi selected by `j` (`0` for the active `y1`). -/
def yjOf (st : FState S) (j : Fin 3) : S :=
  if j = 0 then st.y1 else if j = 1 then st.y2 else st.y3

/-- The matching contribution is nonnegative: the discounted part never
exceeds the distance (`min(ℓ, xi·g) ≤ xi·g` and `xi·g + y·g = xi·y`). -/
theorem distContrib_nonneg (dd dxy djy ℓi : ℝ) (hdxy : 0 ≤ dxy)
    (hg1 : 0 ≤ tripodC dd dxy djy) (hg2 : 0 ≤ tripodC dxy djy dd) :
    0 ≤ distContrib dd dxy djy ℓi := by
  unfold distContrib
  unfold cPsi
  have hsum : tripodC dd dxy djy + tripodC dxy djy dd = dxy := tripodC_path _ _ _
  have hmin : min ℓi (tripodC dd dxy djy) ≤ tripodC dd dxy djy := min_le_right _ _
  linarith

/-- The two passive contributions of a metric configuration are
nonnegative. -/
theorem distContrib_nonneg_of_metric (u v w : S) (ℓ : ℝ) :
    0 ≤ distContrib (dist u v) (dist u w) (dist v w) ℓ ∧
    0 ≤ distContrib (dist u v) (dist v w) (dist u w) ℓ := by
  constructor
  · apply distContrib_nonneg _ _ _ _ (dist_nonneg _ _)
    · exact tripodC_nonneg u v w
    · have h := tripodC_nonneg' u w v
      rwa [TaxiMetric.dist_comm w v] at h
  · apply distContrib_nonneg _ _ _ _ (dist_nonneg _ _)
    · exact tripodC_nonneg' u v w
    · have h := tripodC_nonneg' v w u
      rwa [TaxiMetric.dist_comm w u, TaxiMetric.dist_comm v u] at h

/-- `M ≥ 0`. -/
theorem Mpot_nonneg (x1y1 dd d2y2 d3y2 d2y3 d3y3 ℓ2 ℓ3 : ℝ) (h1 : 0 ≤ x1y1)
    (ha : 0 ≤ distContrib dd d2y2 d3y2 ℓ2) (hb : 0 ≤ distContrib dd d3y3 d2y3 ℓ3)
    (hc : 0 ≤ distContrib dd d2y3 d3y3 ℓ2) (hd : 0 ≤ distContrib dd d3y2 d2y2 ℓ3) :
    0 ≤ Mpot x1y1 dd d2y2 d3y2 d2y3 d3y3 ℓ2 ℓ3 := by
  unfold Mpot matchSum
  have hA : 0 ≤ distContrib dd d2y2 d3y2 ℓ2 + distContrib dd d3y3 d2y3 ℓ3 := by linarith
  have hB : 0 ≤ distContrib dd d2y3 d3y3 ℓ2 + distContrib dd d3y2 d2y2 ℓ3 := by linarith
  have hmin : 0 ≤ min (distContrib dd d2y2 d3y2 ℓ2 + distContrib dd d3y3 d2y3 ℓ3)
      (distContrib dd d2y3 d3y3 ℓ2 + distContrib dd d3y2 d2y2 ℓ3) := by
    rw [min_def]
    split_ifs with h <;> linarith
  linarith

/-- `Σ ≥ 0`. -/
theorem SigmaPot_nonneg (dd ℓ2 ℓ3 : ℝ) : 0 ≤ SigmaPot dd ℓ2 ℓ3 :=
  le_max_left _ _

/-- The potential is nonnegative. -/
theorem phi_nonneg (st : FState S) : 0 ≤ st.phi := by
  unfold FState.phi Phi
  have hM : 0 ≤ Mpot (dist st.x1 st.y1) (dist st.x2 st.x3) (dist st.x2 st.y2)
      (dist st.x3 st.y2) (dist st.x2 st.y3) (dist st.x3 st.y3) st.ℓ2 st.ℓ3 := by
    apply Mpot_nonneg _ _ _ _ _ _ _ _ (dist_nonneg _ _)
    · exact (distContrib_nonneg_of_metric st.x2 st.x3 st.y2 st.ℓ2).1
    · exact (distContrib_nonneg_of_metric st.x2 st.x3 st.y3 st.ℓ3).2
    · exact (distContrib_nonneg_of_metric st.x2 st.x3 st.y3 st.ℓ2).1
    · exact (distContrib_nonneg_of_metric st.x2 st.x3 st.y2 st.ℓ3).2
  have hS : 0 ≤ SigmaPot (dist st.x2 st.x3) st.ℓ2 st.ℓ3 := SigmaPot_nonneg _ _ _
  have e1 : 0 ≤ cAlpha * Mpot (dist st.x1 st.y1) (dist st.x2 st.x3) (dist st.x2 st.y2)
      (dist st.x3 st.y2) (dist st.x2 st.y3) (dist st.x3 st.y3) st.ℓ2 st.ℓ3 :=
    mul_nonneg (le_of_lt cAlpha_pos) hM
  have e2 : 0 ≤ cBeta * SigmaPot (dist st.x2 st.x3) st.ℓ2 st.ℓ3 :=
    mul_nonneg (le_of_lt cBeta_pos) hS
  linarith

end



/-! ## The movement phase -/

/-- The serving taxi when the movement ends: `0` if the active taxi
arrives in time, otherwise the passive taxi that reached the branching point
(`1` for `x2`, `2` for `x3`). Packaged as a function so that case splits in
proofs do not unfold into the output record. -/
noncomputable def serverCaseA (x2moving : Bool) (ontime : Prop) [Decidable ontime] :
    Fin 3 :=
  if ontime then 0 else (if x2moving then 1 else 2)

theorem serverCaseA_of_pos (x2moving : Bool) (ontime : Prop) [Decidable ontime]
    (h : ontime) : serverCaseA x2moving ontime = 0 := by
  unfold serverCaseA
  rw [if_pos h]

theorem serverCaseA_of_neg (x2moving : Bool) (ontime : Prop) [Decidable ontime]
    (h : ¬ontime) : serverCaseA x2moving ontime = if x2moving then 1 else 2 := by
  unfold serverCaseA
  rw [if_neg h]

/-- The output of the movement phase: the traveled distances `s1 s2 s3` of
the three online taxis, the taxi that reached the pick-up point (`server`:
`0` for the active taxi `x1`, `1` for `x2`, `2` for `x3`), and the updated
interval lengths. -/
structure MoveOut where
  s1 : ℝ
  s2 : ℝ
  s3 : ℝ
  server : Fin 3
  ℓ2' : ℝ
  ℓ3' : ℝ

/-- The state of one passive taxi during the two-unobstructed movement case
(case B), as an explicit piecewise-affine function of time: `u0 = xi·e` (the
initial distance to the branching point of `B(x2, x3, r)`), `L0 = ℓi`, `t`
the elapsed time (at most `timeToEdge u0 L0`). Returns the traveled distance,
the current interval length, and the current distance to the branching point.

Speed rules: the taxi moves at speed `1 + b` if
`ℓi ≥ xi·e > 0` (the branching point lies inside its interval) and at speed
`1` otherwise; `qi` moves towards `e` at speed `1` unless it is at `e`. -/
noncomputable def passiveB (u0 L0 t : ℝ) : ℝ × ℝ × ℝ :=
  if u0 ≤ L0 then
    if u0 * (2 + cB) ≤ L0 * (1 + cB) then
      -- fast throughout; `qi` has not returned to `e` when `xi` arrives
      ((1 + cB) * t, L0 - (2 + cB) * t, u0 - (1 + cB) * t)
    else if t ≤ L0 - u0 then
      -- fast, with `qi` still returning to `e`
      ((1 + cB) * t, L0 - (2 + cB) * t, u0 - (1 + cB) * t)
    else
      -- fast, with `qi` resting at `e`: `ℓi = xi·e` from here on
      ((1 + cB) * t, u0 - (1 + cB) * t, u0 - (1 + cB) * t)
  else if t ≤ u0 - L0 then
    -- unit speed; `qi` moving towards `e` at the same speed, `ℓi` constant
    (t, L0, u0 - t)
  else
    -- `qi` has reached `e`; the taxi accelerates to `1 + b` with `qi` at `e`
    ((u0 - L0) + (1 + cB) * (t - (u0 - L0)), L0 - (1 + cB) * (t - (u0 - L0)),
      L0 - (1 + cB) * (t - (u0 - L0)))

/-- The time at which passive taxi `xi` reaches the branching point `e` in
case B. -/
noncomputable def timeToEdge (u0 L0 : ℝ) : ℝ :=
  if u0 ≤ L0 then u0 * cB1 else (u0 - L0) + L0 * cB1

/-- The one-unobstructed movement case (case A) with `x2` moving: `x2`,
initially at the branching point, moves towards `r` at unit speed while the
active taxi moves at speed `a`; the endpoint `q2` returns to the moving
branching point at relative rate `2`, so the interval length is
`max 0 (Le − 2t)`. Inputs: `d1 = x1·r` (remaining), `dir = e·r`, `Le` the
moving taxi's interval length, `Lo` the other taxi's interval length
(frozen). -/
noncomputable def moveA2 (d1 dir Le Lo : ℝ) : MoveOut :=
  { s1 := cA * min (d1 / cA) dir
    s2 := min (d1 / cA) dir
    s3 := 0
    server := serverCaseA true (d1 / cA ≤ dir)
    ℓ2' := max 0 (Le - 2 * min (d1 / cA) dir)
    ℓ3' := Lo }

/-- The same case with `x3` moving. -/
noncomputable def moveA3 (d1 dir Le Lo : ℝ) : MoveOut :=
  { s1 := cA * min (d1 / cA) dir
    s2 := 0
    s3 := min (d1 / cA) dir
    server := serverCaseA false (d1 / cA ≤ dir)
    ℓ2' := Lo
    ℓ3' := max 0 (Le - 2 * min (d1 / cA) dir) }

/-- The movement phase of TripodTracker as an
explicit piecewise-affine function of the distances `d1 = x1·r`, `d2 = x2·r`,
`d3 = x3·r`, `dd = x2·x3` and the interval lengths. Both taxis unobstructed
(case B): the two passive taxis evolve independently until the first of
`{d1/a, U2, U3}`; then either the active taxi has arrived, or the phase
continues as case A with the taxi that reached the branching point. -/
noncomputable def movePhase (d1 d2 d3 dd ℓ2 ℓ3 : ℝ) : MoveOut :=
  if tripodC dd d2 d3 ≤ 0 then
    moveA2 d1 (tripodC d2 d3 dd) ℓ2 ℓ3
  else if tripodC dd d3 d2 ≤ 0 then
    moveA3 d1 (tripodC d2 d3 dd) ℓ3 ℓ2
  else
    if d1 / cA ≤ timeToEdge (tripodC dd d2 d3) ℓ2 ∧
        d1 / cA ≤ timeToEdge (tripodC dd d3 d2) ℓ3 then
      -- the active taxi reaches `r` first
      { s1 := d1
        s2 := (passiveB (tripodC dd d2 d3) ℓ2 (d1 / cA)).1
        s3 := (passiveB (tripodC dd d3 d2) ℓ3 (d1 / cA)).1
        server := 0
        ℓ2' := (passiveB (tripodC dd d2 d3) ℓ2 (d1 / cA)).2.1
        ℓ3' := (passiveB (tripodC dd d3 d2) ℓ3 (d1 / cA)).2.1 }
    else if timeToEdge (tripodC dd d2 d3) ℓ2 ≤ timeToEdge (tripodC dd d3 d2) ℓ3 then
      -- `x2` reaches the branching point first; case A with `x2` follows
      { s1 := cA * (timeToEdge (tripodC dd d2 d3) ℓ2 +
          min ((d1 - cA * timeToEdge (tripodC dd d2 d3) ℓ2) / cA) (tripodC d2 d3 dd))
        s2 := tripodC dd d2 d3 +
          min ((d1 - cA * timeToEdge (tripodC dd d2 d3) ℓ2) / cA) (tripodC d2 d3 dd)
        s3 := (passiveB (tripodC dd d3 d2) ℓ3 (timeToEdge (tripodC dd d2 d3) ℓ2)).1
        server := serverCaseA true
          ((d1 - cA * timeToEdge (tripodC dd d2 d3) ℓ2) / cA ≤ tripodC d2 d3 dd)
        ℓ2' := max 0 ((passiveB (tripodC dd d2 d3) ℓ2 (timeToEdge (tripodC dd d2 d3) ℓ2)).2.1 -
          2 * min ((d1 - cA * timeToEdge (tripodC dd d2 d3) ℓ2) / cA) (tripodC d2 d3 dd))
        ℓ3' := (passiveB (tripodC dd d3 d2) ℓ3 (timeToEdge (tripodC dd d2 d3) ℓ2)).2.1 }
    else
      -- `x3` reaches the branching point first; case A with `x3` follows
      { s1 := cA * (timeToEdge (tripodC dd d3 d2) ℓ3 +
          min ((d1 - cA * timeToEdge (tripodC dd d3 d2) ℓ3) / cA) (tripodC d2 d3 dd))
        s2 := (passiveB (tripodC dd d2 d3) ℓ2 (timeToEdge (tripodC dd d3 d2) ℓ3)).1
        s3 := tripodC dd d3 d2 +
          min ((d1 - cA * timeToEdge (tripodC dd d3 d2) ℓ3) / cA) (tripodC d2 d3 dd)
        server := serverCaseA false
          ((d1 - cA * timeToEdge (tripodC dd d3 d2) ℓ3) / cA ≤ tripodC d2 d3 dd)
        ℓ2' := (passiveB (tripodC dd d2 d3) ℓ2 (timeToEdge (tripodC dd d3 d2) ℓ3)).2.1
        ℓ3' := max 0 ((passiveB (tripodC dd d3 d2) ℓ3 (timeToEdge (tripodC dd d3 d2) ℓ3)).2.1 -
          2 * min ((d1 - cA * timeToEdge (tripodC dd d3 d2) ℓ3) / cA) (tripodC d2 d3 dd)) }

/-! ## Numeric support lemmas -/

theorem timeToEdge_nonneg (u0 L0 : ℝ) (hu : 0 ≤ u0) (hL : 0 ≤ L0) :
    0 ≤ timeToEdge u0 L0 := by
  unfold timeToEdge
  rw [cB1_val]
  split_ifs with h1
  · positivity
  · push_neg at h1
    linarith

theorem passiveB_s_nonneg (u0 L0 t : ℝ) (hu : 0 ≤ u0) (ht : 0 ≤ t) :
    0 ≤ (passiveB u0 L0 t).1 := by
  unfold passiveB
  unfold cB
  split_ifs with h1 h2 h3 h4
  · dsimp only; positivity
  · dsimp only; positivity
  · dsimp only; positivity
  · dsimp only; exact ht
  · dsimp only
    have h5 : 0 ≤ u0 - L0 := by linarith
    have h6 : 0 ≤ t - (u0 - L0) := by linarith
    positivity

theorem passiveB_s_le (u0 L0 t : ℝ) (hu : 0 ≤ u0) (hL : 0 ≤ L0) (ht : 0 ≤ t)
    (htU : t ≤ timeToEdge u0 L0) :
    (passiveB u0 L0 t).1 ≤ u0 := by
  have hpos : (0:ℝ) < 1 + 1 / 100 := by norm_num
  unfold passiveB timeToEdge at *
  rw [cB1_val] at *
  unfold cB at *
  split_ifs with h1 h2 h3 h4
  · dsimp only
    rw [if_pos h1] at htU
    have h5 : (1 + 1 / 100) * t ≤ u0 := by
      have h9 : t ≤ u0 * (100 / 101) := htU
      have h10 := mul_le_mul_of_nonneg_left h9 (le_of_lt hpos)
      have h11 : (1 + 1 / 100 : ℝ) * (u0 * (100 / 101)) = u0 := by ring_nf
      linarith
    linarith
  · dsimp only
    rw [if_pos h1] at htU
    have h5 : (1 + 1 / 100) * t ≤ u0 := by
      have h9 : t ≤ u0 * (100 / 101) := htU
      have h10 := mul_le_mul_of_nonneg_left h9 (le_of_lt hpos)
      have h11 : (1 + 1 / 100 : ℝ) * (u0 * (100 / 101)) = u0 := by ring_nf
      linarith
    linarith
  · dsimp only
    rw [if_pos h1] at htU
    have h5 : (1 + 1 / 100) * t ≤ u0 := by
      have h9 : t ≤ u0 * (100 / 101) := htU
      have h10 := mul_le_mul_of_nonneg_left h9 (le_of_lt hpos)
      have h11 : (1 + 1 / 100 : ℝ) * (u0 * (100 / 101)) = u0 := by ring_nf
      linarith
    linarith
  · dsimp only
    rw [if_neg h1] at htU
    push_neg at h1
    linarith
  · dsimp only
    rw [if_neg h1] at htU
    push_neg at h1
    push_neg at h4
    have h5 : (1 + 1 / 100) * (t - (u0 - L0)) ≤ L0 := by
      have h9 : t ≤ (u0 - L0) + L0 * (100 / 101) := htU
      linarith
    linarith

theorem passiveB_u_nonneg (u0 L0 t : ℝ) (hu : 0 ≤ u0) (hL : 0 ≤ L0) (ht : 0 ≤ t)
    (htU : t ≤ timeToEdge u0 L0) :
    0 ≤ (passiveB u0 L0 t).2.2 := by
  have hpos : (0:ℝ) < 1 + 1 / 100 := by norm_num
  unfold passiveB timeToEdge at *
  rw [cB1_val] at *
  unfold cB at *
  split_ifs with h1 h2 h3 h4
  · dsimp only
    rw [if_pos h1] at htU
    have h5 : (1 + 1 / 100) * t ≤ u0 := by
      have h9 : t ≤ u0 * (100 / 101) := htU
      have h10 := mul_le_mul_of_nonneg_left h9 (le_of_lt hpos)
      have h11 : (1 + 1 / 100 : ℝ) * (u0 * (100 / 101)) = u0 := by ring_nf
      linarith
    linarith
  · dsimp only
    rw [if_pos h1] at htU
    have h5 : (1 + 1 / 100) * t ≤ u0 := by
      have h9 : t ≤ u0 * (100 / 101) := htU
      have h10 := mul_le_mul_of_nonneg_left h9 (le_of_lt hpos)
      have h11 : (1 + 1 / 100 : ℝ) * (u0 * (100 / 101)) = u0 := by ring_nf
      linarith
    linarith
  · dsimp only
    rw [if_pos h1] at htU
    have h5 : (1 + 1 / 100) * t ≤ u0 := by
      have h9 : t ≤ u0 * (100 / 101) := htU
      have h10 := mul_le_mul_of_nonneg_left h9 (le_of_lt hpos)
      have h11 : (1 + 1 / 100 : ℝ) * (u0 * (100 / 101)) = u0 := by ring_nf
      linarith
    linarith
  · dsimp only
    rw [if_neg h1] at htU
    push_neg at h1
    linarith
  · dsimp only
    rw [if_neg h1] at htU
    push_neg at h1
    push_neg at h4
    have h5 : (1 + 1 / 100) * (t - (u0 - L0)) ≤ L0 := by
      have h9 : t ≤ (u0 - L0) + L0 * (100 / 101) := htU
      linarith
    linarith

theorem passiveB_ℓ_nonneg (u0 L0 t : ℝ) (hu : 0 ≤ u0) (hL : 0 ≤ L0) (ht : 0 ≤ t)
    (htU : t ≤ timeToEdge u0 L0) :
    0 ≤ (passiveB u0 L0 t).2.1 := by
  have hpos : (0:ℝ) < 1 + 1 / 100 := by norm_num
  unfold passiveB timeToEdge at *
  rw [cB1_val] at *
  unfold cB at *
  split_ifs with h1 h2 h3 h4
  · dsimp only
    rw [if_pos h1] at htU
    have h9 : t ≤ u0 * (100 / 101) := htU
    have h8 : (2 + 1 / 100) * t ≤ L0 := by linarith [h2, h9, hu]
    linarith
  · dsimp only
    rw [if_pos h1] at htU
    push_neg at h2
    have h7 : (2 + 1 / 100) * t ≤ (2 + 1 / 100) * (L0 - u0) :=
      mul_le_mul_of_nonneg_left h3 (by norm_num)
    linarith
  · dsimp only
    rw [if_pos h1] at htU
    have h9 : t ≤ u0 * (100 / 101) := htU
    have h5 : (1 + 1 / 100) * t ≤ u0 := by
      have h10 := mul_le_mul_of_nonneg_left h9 (le_of_lt hpos)
      have h11 : (1 + 1 / 100 : ℝ) * (u0 * (100 / 101)) = u0 := by ring_nf
      linarith
    linarith
  · dsimp only
    rw [if_neg h1] at htU
    exact hL
  · dsimp only
    rw [if_neg h1] at htU
    push_neg at h1
    push_neg at h4
    have h5 : (1 + 1 / 100) * (t - (u0 - L0)) ≤ L0 := by
      have h9 : t ≤ (u0 - L0) + L0 * (100 / 101) := htU
      linarith
    linarith

/-- In case B, when taxi `xi` reaches the branching point its traveled
distance is exactly `u0`. -/
theorem passiveB_s_at_U (u0 L0 : ℝ) (hu : 0 ≤ u0) (hL : 0 ≤ L0) :
    (passiveB u0 L0 (timeToEdge u0 L0)).1 = u0 := by
  unfold passiveB timeToEdge
  rw [cB1_val]
  unfold cB
  split_ifs with h1 h2 h3 h4
  · dsimp only
    have h11 : (1 + 1 / 100 : ℝ) * (u0 * (100 / 101)) = u0 := by ring_nf
    linarith
  · dsimp only
    have h11 : (1 + 1 / 100 : ℝ) * (u0 * (100 / 101)) = u0 := by ring_nf
    linarith
  · dsimp only
    have h11 : (1 + 1 / 100 : ℝ) * (u0 * (100 / 101)) = u0 := by ring_nf
    linarith
  · dsimp only
    linarith
  · dsimp only
    push_neg at h4
    linarith

/-- In case B, when taxi `xi` reaches the branching point its distance to it
is zero. -/
theorem passiveB_u_at_U (u0 L0 : ℝ) (hu : 0 ≤ u0) (hL : 0 ≤ L0) :
    (passiveB u0 L0 (timeToEdge u0 L0)).2.2 = 0 := by
  unfold passiveB timeToEdge
  rw [cB1_val]
  unfold cB
  split_ifs with h1 h2 h3 h4
  · dsimp only
    have h11 : (1 + 1 / 100 : ℝ) * (u0 * (100 / 101)) = u0 := by ring_nf
    linarith
  · dsimp only
    have h11 : (1 + 1 / 100 : ℝ) * (u0 * (100 / 101)) = u0 := by ring_nf
    linarith
  · dsimp only
    have h11 : (1 + 1 / 100 : ℝ) * (u0 * (100 / 101)) = u0 := by ring_nf
    linarith
  · dsimp only
    linarith
  · dsimp only
    push_neg at h4
    linarith

/-- The traveled distances computed by `movePhase` lie in `[0, d1] × [0, d2]
× [0, d3]`. -/
theorem movePhase_s1_mem (d1 d2 d3 dd ℓ2 ℓ3 : ℝ)
    (hd1 : 0 ≤ d1) (hd2 : 0 ≤ d2) (hd3 : 0 ≤ d3)
    (hu2 : 0 ≤ tripodC dd d2 d3) (hu3 : 0 ≤ tripodC dd d3 d2)
    (her : 0 ≤ tripodC d2 d3 dd) (hℓ2 : 0 ≤ ℓ2) (hℓ3 : 0 ≤ ℓ3) :
    0 ≤ (movePhase d1 d2 d3 dd ℓ2 ℓ3).s1 ∧ (movePhase d1 d2 d3 dd ℓ2 ℓ3).s1 ≤ d1 := by
  have hapos : (0:ℝ) < 1 / 10000 := by norm_num
  unfold movePhase
  unfold cA
  split_ifs with h1 h2 h3 h4
  · unfold moveA2
    unfold cA
    dsimp only
    have hT : 0 ≤ min (d1 / (1 / 10000)) (tripodC d2 d3 dd) := le_min (by positivity) her
    constructor
    · linarith [hT]
    · have h5 := min_le_left (d1 / (1 / 10000)) (tripodC d2 d3 dd)
      have h6 := mul_le_mul_of_nonneg_left h5 hapos.le
      linarith
  · unfold moveA3
    unfold cA
    dsimp only
    have hT : 0 ≤ min (d1 / (1 / 10000)) (tripodC d2 d3 dd) := le_min (by positivity) her
    constructor
    · linarith [hT]
    · have h5 := min_le_left (d1 / (1 / 10000)) (tripodC d2 d3 dd)
      have h6 := mul_le_mul_of_nonneg_left h5 hapos.le
      linarith
  · dsimp only
    exact ⟨hd1, le_refl d1⟩
  · dsimp only
    have hU2 : 0 ≤ timeToEdge (tripodC dd d2 d3) ℓ2 := timeToEdge_nonneg _ _ hu2 hℓ2
    have h3' : timeToEdge (tripodC dd d2 d3) ℓ2 < d1 / (1 / 10000) ∨
        timeToEdge (tripodC dd d3 d2) ℓ3 < d1 / (1 / 10000) := by
      by_contra hcon
      push_neg at hcon
      exact h3 ⟨hcon.1, hcon.2⟩
    have hd1r : 0 ≤ d1 - (1 / 10000) * timeToEdge (tripodC dd d2 d3) ℓ2 := by
      rcases h3' with h3' | h3'
      · rw [lt_div_iff₀ hapos] at h3'
        linarith
      · rw [lt_div_iff₀ hapos] at h3'
        linarith
    have hT : 0 ≤ min ((d1 - (1 / 10000) * timeToEdge (tripodC dd d2 d3) ℓ2) / (1 / 10000))
        (tripodC d2 d3 dd) := le_min (by positivity) her
    constructor
    · linarith [hU2, hT]
    · have h5 := min_le_left
        ((d1 - (1 / 10000) * timeToEdge (tripodC dd d2 d3) ℓ2) / (1 / 10000))
        (tripodC d2 d3 dd)
      have h6 := mul_le_mul_of_nonneg_left h5 hapos.le
      linarith
  · dsimp only
    have h4' : timeToEdge (tripodC dd d3 d2) ℓ3 < timeToEdge (tripodC dd d2 d3) ℓ2 := by
      by_contra hcon
      push_neg at hcon
      contradiction
    have hU3 : 0 ≤ timeToEdge (tripodC dd d3 d2) ℓ3 := timeToEdge_nonneg _ _ hu3 hℓ3
    have h3' : timeToEdge (tripodC dd d2 d3) ℓ2 < d1 / (1 / 10000) ∨
        timeToEdge (tripodC dd d3 d2) ℓ3 < d1 / (1 / 10000) := by
      by_contra hcon
      push_neg at hcon
      exact h3 ⟨hcon.1, hcon.2⟩
    have hd1r : 0 ≤ d1 - (1 / 10000) * timeToEdge (tripodC dd d3 d2) ℓ3 := by
      rcases h3' with h3' | h3'
      · rw [lt_div_iff₀ hapos] at h3'
        linarith
      · rw [lt_div_iff₀ hapos] at h3'
        linarith
    have hT : 0 ≤ min ((d1 - (1 / 10000) * timeToEdge (tripodC dd d3 d2) ℓ3) / (1 / 10000))
        (tripodC d2 d3 dd) := le_min (by positivity) her
    constructor
    · linarith [hU3, hT]
    · have h5 := min_le_left
        ((d1 - (1 / 10000) * timeToEdge (tripodC dd d3 d2) ℓ3) / (1 / 10000))
        (tripodC d2 d3 dd)
      have h6 := mul_le_mul_of_nonneg_left h5 hapos.le
      linarith

theorem movePhase_s2_mem (d1 d2 d3 dd ℓ2 ℓ3 : ℝ)
    (hd1 : 0 ≤ d1) (hd2 : 0 ≤ d2) (hd3 : 0 ≤ d3)
    (hu2 : 0 ≤ tripodC dd d2 d3) (hu3 : 0 ≤ tripodC dd d3 d2)
    (her : 0 ≤ tripodC d2 d3 dd) (hℓ2 : 0 ≤ ℓ2) (hℓ3 : 0 ≤ ℓ3) :
    0 ≤ (movePhase d1 d2 d3 dd ℓ2 ℓ3).s2 ∧ (movePhase d1 d2 d3 dd ℓ2 ℓ3).s2 ≤ d2 := by
  have hpath : tripodC dd d2 d3 + tripodC d2 d3 dd = d2 := tripodC_path _ _ _
  have hapos : (0:ℝ) < 1 / 10000 := by norm_num
  unfold movePhase
  unfold cA
  split_ifs with h1 h2 h3 h4
  · unfold moveA2
    unfold cA
    dsimp only
    have hT : 0 ≤ min (d1 / (1 / 10000)) (tripodC d2 d3 dd) := le_min (by positivity) her
    refine ⟨hT, ?_⟩
    have h5 : min (d1 / (1 / 10000)) (tripodC d2 d3 dd) ≤ tripodC d2 d3 dd := min_le_right _ _
    linarith
  · unfold moveA3
    dsimp only
    exact ⟨le_refl 0, hd2⟩
  · dsimp only
    refine ⟨passiveB_s_nonneg _ _ _ hu2 (by positivity), ?_⟩
    have h6 : (passiveB (tripodC dd d2 d3) ℓ2 (d1 / (1 / 10000))).1 ≤ tripodC dd d2 d3 :=
      passiveB_s_le _ _ _ hu2 hℓ2 (by positivity) h3.1
    linarith
  · dsimp only
    have h3' : timeToEdge (tripodC dd d2 d3) ℓ2 < d1 / (1 / 10000) ∨
        timeToEdge (tripodC dd d3 d2) ℓ3 < d1 / (1 / 10000) := by
      by_contra hcon
      push_neg at hcon
      exact h3 ⟨hcon.1, hcon.2⟩
    have hd1r : 0 ≤ d1 - (1 / 10000) * timeToEdge (tripodC dd d2 d3) ℓ2 := by
      rcases h3' with h3' | h3'
      · rw [lt_div_iff₀ hapos] at h3'
        linarith
      · rw [lt_div_iff₀ hapos] at h3'
        linarith
    have hT : 0 ≤ min ((d1 - (1 / 10000) * timeToEdge (tripodC dd d2 d3) ℓ2) / (1 / 10000))
        (tripodC d2 d3 dd) := le_min (by positivity) her
    refine ⟨by linarith, ?_⟩
    have h5 : min ((d1 - (1 / 10000) * timeToEdge (tripodC dd d2 d3) ℓ2) / (1 / 10000))
        (tripodC d2 d3 dd) ≤ tripodC d2 d3 dd := min_le_right _ _
    linarith
  · dsimp only
    refine ⟨passiveB_s_nonneg _ _ _ hu2 (timeToEdge_nonneg _ _ hu3 hℓ3), ?_⟩
    have h4' : timeToEdge (tripodC dd d3 d2) ℓ3 < timeToEdge (tripodC dd d2 d3) ℓ2 := by
      by_contra hcon
      push_neg at hcon
      contradiction
    have h6 : (passiveB (tripodC dd d2 d3) ℓ2 (timeToEdge (tripodC dd d3 d2) ℓ3)).1 ≤
        tripodC dd d2 d3 :=
      passiveB_s_le _ _ _ hu2 hℓ2 (timeToEdge_nonneg _ _ hu3 hℓ3) (le_of_lt h4')
    linarith

theorem movePhase_s3_mem (d1 d2 d3 dd ℓ2 ℓ3 : ℝ)
    (hd1 : 0 ≤ d1) (hd2 : 0 ≤ d2) (hd3 : 0 ≤ d3)
    (hu2 : 0 ≤ tripodC dd d2 d3) (hu3 : 0 ≤ tripodC dd d3 d2)
    (her : 0 ≤ tripodC d2 d3 dd) (hℓ2 : 0 ≤ ℓ2) (hℓ3 : 0 ≤ ℓ3) :
    0 ≤ (movePhase d1 d2 d3 dd ℓ2 ℓ3).s3 ∧ (movePhase d1 d2 d3 dd ℓ2 ℓ3).s3 ≤ d3 := by
  have hpath : tripodC dd d3 d2 + tripodC d3 d2 dd = d3 := tripodC_path _ _ _
  have her' : tripodC d3 d2 dd = tripodC d2 d3 dd := by unfold tripodC; ring
  have hapos : (0:ℝ) < 1 / 10000 := by norm_num
  unfold movePhase
  unfold cA
  split_ifs with h1 h2 h3 h4
  · unfold moveA2
    dsimp only
    exact ⟨le_refl 0, hd3⟩
  · unfold moveA3
    unfold cA
    dsimp only
    have hT : 0 ≤ min (d1 / (1 / 10000)) (tripodC d2 d3 dd) := le_min (by positivity) her
    refine ⟨hT, ?_⟩
    have h5 : min (d1 / (1 / 10000)) (tripodC d2 d3 dd) ≤ tripodC d2 d3 dd := min_le_right _ _
    linarith [hpath, hu3, h5, her']
  · dsimp only
    refine ⟨passiveB_s_nonneg _ _ _ hu3 (by positivity), ?_⟩
    have h6 : (passiveB (tripodC dd d3 d2) ℓ3 (d1 / (1 / 10000))).1 ≤ tripodC dd d3 d2 :=
      passiveB_s_le _ _ _ hu3 hℓ3 (by positivity) h3.2
    have h7 : tripodC dd d3 d2 ≤ d3 := by
      have h9 : 0 ≤ tripodC d3 d2 dd := by rw [her']; exact her
      linarith
    linarith
  · dsimp only
    refine ⟨passiveB_s_nonneg _ _ _ hu3 (timeToEdge_nonneg _ _ hu2 hℓ2), ?_⟩
    have h6 : (passiveB (tripodC dd d3 d2) ℓ3 (timeToEdge (tripodC dd d2 d3) ℓ2)).1 ≤
        tripodC dd d3 d2 :=
      passiveB_s_le _ _ _ hu3 hℓ3 (timeToEdge_nonneg _ _ hu2 hℓ2) h4
    have h7 : tripodC dd d3 d2 ≤ d3 := by
      have h9 : 0 ≤ tripodC d3 d2 dd := by rw [her']; exact her
      linarith
    linarith
  · dsimp only
    have h3' : timeToEdge (tripodC dd d2 d3) ℓ2 < d1 / (1 / 10000) ∨
        timeToEdge (tripodC dd d3 d2) ℓ3 < d1 / (1 / 10000) := by
      by_contra hcon
      push_neg at hcon
      exact h3 ⟨hcon.1, hcon.2⟩
    have hd1r : 0 ≤ d1 - (1 / 10000) * timeToEdge (tripodC dd d3 d2) ℓ3 := by
      rcases h3' with h3' | h3'
      · rw [lt_div_iff₀ hapos] at h3'
        linarith
      · rw [lt_div_iff₀ hapos] at h3'
        linarith
    have hT : 0 ≤ min ((d1 - (1 / 10000) * timeToEdge (tripodC dd d3 d2) ℓ3) / (1 / 10000))
        (tripodC d2 d3 dd) := le_min (by positivity) her
    refine ⟨by linarith [hT], ?_⟩
    have h5 : min ((d1 - (1 / 10000) * timeToEdge (tripodC dd d3 d2) ℓ3) / (1 / 10000))
        (tripodC d2 d3 dd) ≤ tripodC d2 d3 dd := min_le_right _ _
    linarith [hpath, hu3, h5, her']

/-- The interval lengths computed by `movePhase` are nonnegative. -/
theorem movePhase_ℓ_nonneg (d1 d2 d3 dd ℓ2 ℓ3 : ℝ)
    (hd1 : 0 ≤ d1) (hd2 : 0 ≤ d2) (hd3 : 0 ≤ d3)
    (hu2 : 0 ≤ tripodC dd d2 d3) (hu3 : 0 ≤ tripodC dd d3 d2)
    (her : 0 ≤ tripodC d2 d3 dd) (hℓ2 : 0 ≤ ℓ2) (hℓ3 : 0 ≤ ℓ3) :
    0 ≤ (movePhase d1 d2 d3 dd ℓ2 ℓ3).ℓ2' ∧ 0 ≤ (movePhase d1 d2 d3 dd ℓ2 ℓ3).ℓ3' := by
  have hapos : (0:ℝ) < 1 / 10000 := by norm_num
  unfold movePhase
  unfold cA
  split_ifs with h1 h2 h3 h4
  · unfold moveA2
    dsimp only
    exact ⟨le_max_left _ _, hℓ3⟩
  · unfold moveA3
    dsimp only
    exact ⟨hℓ2, le_max_left _ _⟩
  · dsimp only
    exact ⟨passiveB_ℓ_nonneg _ _ _ hu2 hℓ2 (by positivity) h3.1,
      passiveB_ℓ_nonneg _ _ _ hu3 hℓ3 (by positivity) h3.2⟩
  · dsimp only
    exact ⟨le_max_left _ _,
      passiveB_ℓ_nonneg _ _ _ hu3 hℓ3 (timeToEdge_nonneg _ _ hu2 hℓ2) h4⟩
  · dsimp only
    have h4' : timeToEdge (tripodC dd d3 d2) ℓ3 < timeToEdge (tripodC dd d2 d3) ℓ2 := by
      by_contra hcon
      push_neg at hcon
      contradiction
    exact ⟨passiveB_ℓ_nonneg _ _ _ hu2 hℓ2 (timeToEdge_nonneg _ _ hu3 hℓ3) (le_of_lt h4'),
      le_max_left _ _⟩

/-- The serving taxi has traveled exactly its distance to `r`. -/
theorem movePhase_s_eq_of_server (d1 d2 d3 dd ℓ2 ℓ3 : ℝ)
    (hd1 : 0 ≤ d1) (hd2 : 0 ≤ d2) (hd3 : 0 ≤ d3)
    (hu2 : 0 ≤ tripodC dd d2 d3) (hu3 : 0 ≤ tripodC dd d3 d2)
    (her : 0 ≤ tripodC d2 d3 dd) (hℓ2 : 0 ≤ ℓ2) (hℓ3 : 0 ≤ ℓ3) :
    ((movePhase d1 d2 d3 dd ℓ2 ℓ3).server = 0 → (movePhase d1 d2 d3 dd ℓ2 ℓ3).s1 = d1) ∧
    ((movePhase d1 d2 d3 dd ℓ2 ℓ3).server = 1 → (movePhase d1 d2 d3 dd ℓ2 ℓ3).s2 = d2) ∧
    ((movePhase d1 d2 d3 dd ℓ2 ℓ3).server = 2 → (movePhase d1 d2 d3 dd ℓ2 ℓ3).s3 = d3) := by
  have hpath2 : tripodC dd d2 d3 + tripodC d2 d3 dd = d2 := tripodC_path _ _ _
  have hpath3 : tripodC dd d3 d2 + tripodC d3 d2 dd = d3 := tripodC_path _ _ _
  have her' : tripodC d3 d2 dd = tripodC d2 d3 dd := by unfold tripodC; ring
  unfold movePhase
  unfold cA
  split_ifs with h1 h2 h3 h4
  · -- case A with x2 moving (u2 ≤ 0)
    unfold moveA2
    unfold cA
    dsimp only
    by_cases hc : d1 / (1 / 10000) ≤ tripodC d2 d3 dd
    · rw [serverCaseA_of_pos true _ hc]
      refine ⟨?_, ?_, ?_⟩
      · intro _
        rw [min_eq_left hc]
        linarith
      · intro h; exact absurd h (by decide)
      · intro h; exact absurd h (by decide)
    · rw [serverCaseA_of_neg true _ hc]
      refine ⟨?_, ?_, ?_⟩
      · intro h; exact absurd h (by decide)
      · intro _
        have hmin : min (d1 / (1 / 10000)) (tripodC d2 d3 dd) = tripodC d2 d3 dd :=
          min_eq_right (not_le.mp hc).le
        rw [hmin]
        have hu20 : tripodC dd d2 d3 = 0 := by linarith [h1, hu2]
        linarith [hpath2]
      · intro h; exact absurd h (by decide)
  · -- case A with x3 moving (u3 ≤ 0)
    unfold moveA3
    unfold cA
    dsimp only
    by_cases hc : d1 / (1 / 10000) ≤ tripodC d2 d3 dd
    · rw [serverCaseA_of_pos false _ hc]
      refine ⟨?_, ?_, ?_⟩
      · intro _
        rw [min_eq_left hc]
        linarith
      · intro h; exact absurd h (by decide)
      · intro h; exact absurd h (by decide)
    · rw [serverCaseA_of_neg false _ hc]
      refine ⟨?_, ?_, ?_⟩
      · intro h; exact absurd h (by decide)
      · intro h; exact absurd h (by decide)
      · intro _
        have hmin : min (d1 / (1 / 10000)) (tripodC d2 d3 dd) = tripodC d2 d3 dd :=
          min_eq_right (not_le.mp hc).le
        rw [hmin]
        have hu30 : tripodC dd d3 d2 = 0 := by linarith [h2, hu3]
        linarith [hpath3, her']
  · -- the active taxi arrives first
    dsimp only
    refine ⟨?_, ?_, ?_⟩
    · intro _; rfl
    · intro h; exact absurd h (by decide)
    · intro h; exact absurd h (by decide)
  · -- case B, then case A with x2
    dsimp only
    by_cases hc : (d1 - (1 / 10000) * timeToEdge (tripodC dd d2 d3) ℓ2) / (1 / 10000) ≤
        tripodC d2 d3 dd
    · rw [serverCaseA_of_pos true _ hc]
      refine ⟨?_, ?_, ?_⟩
      · intro _
        rw [min_eq_left hc]
        linarith
      · intro h; exact absurd h (by decide)
      · intro h; exact absurd h (by decide)
    · rw [serverCaseA_of_neg true _ hc]
      refine ⟨?_, ?_, ?_⟩
      · intro h; exact absurd h (by decide)
      · intro _
        have hmin : min ((d1 - (1 / 10000) * timeToEdge (tripodC dd d2 d3) ℓ2) / (1 / 10000))
            (tripodC d2 d3 dd) = tripodC d2 d3 dd := min_eq_right (not_le.mp hc).le
        rw [hmin]
        linarith [hpath2]
      · intro h; exact absurd h (by decide)
  · -- case B, then case A with x3
    dsimp only
    by_cases hc : (d1 - (1 / 10000) * timeToEdge (tripodC dd d3 d2) ℓ3) / (1 / 10000) ≤
        tripodC d2 d3 dd
    · rw [serverCaseA_of_pos false _ hc]
      refine ⟨?_, ?_, ?_⟩
      · intro _
        rw [min_eq_left hc]
        linarith
      · intro h; exact absurd h (by decide)
      · intro h; exact absurd h (by decide)
    · rw [serverCaseA_of_neg false _ hc]
      refine ⟨?_, ?_, ?_⟩
      · intro h; exact absurd h (by decide)
      · intro h; exact absurd h (by decide)
      · intro _
        have hmin : min ((d1 - (1 / 10000) * timeToEdge (tripodC dd d3 d2) ℓ3) / (1 / 10000))
            (tripodC d2 d3 dd) = tripodC d2 d3 dd := min_eq_right (not_le.mp hc).le
        rw [hmin]
        linarith [hpath3, her']




section

variable {S : Type} [TaxiMetric S]

open TaxiMetric

/-- A third nonnegativity variant: `(xz + yz − xy)/2 ≥ 0`. -/
theorem tripodC_nonneg'' (x y z : S) :
    0 ≤ tripodC (dist x z) (dist y z) (dist x y) := by
  have h := TaxiMetric.dist_triangle x z y
  rw [TaxiMetric.dist_comm z y] at h
  unfold tripodC
  linarith

/-- A point at distance `t` from `x` along a bridge to `y` (exists by the
bridge hypothesis). -/
noncomputable def alongBridge (x y : S) (t : ℝ) (h : 0 ≤ t ∧ t ≤ dist x y) : S :=
  Classical.choose (TaxiMetric.bridge x y t h.1 h.2)

/-- The chosen bridge point lies on a shortest path at the prescribed
distance. -/
theorem alongBridge_spec (x y : S) (t : ℝ) (h : 0 ≤ t ∧ t ≤ dist x y) :
    dist x (alongBridge x y t h) = t ∧ dist (alongBridge x y t h) y = dist x y - t :=
  Classical.choose_spec (TaxiMetric.bridge x y t h.1 h.2)

/-- The common center of the tripod `B(x, y, r)`. -/
noncomputable def tripodCenter (x y r : S) : S :=
  Classical.choose (TaxiMetric.tripod x y r)

/-- The chosen center has the three edge lengths used by `movePhase`. -/
theorem tripodCenter_spec (x y r : S) :
    dist x (tripodCenter x y r) = tripodC (dist x y) (dist x r) (dist y r) ∧
      dist y (tripodCenter x y r) = tripodC (dist x y) (dist y r) (dist x r) ∧
      dist r (tripodCenter x y r) = tripodC (dist x r) (dist y r) (dist x y) :=
  Classical.choose_spec (TaxiMetric.tripod x y r)

/-- Both passive-to-pickup paths pass through the same center. -/
theorem tripodCenter_paths (x y r : S) :
    dist x (tripodCenter x y r) + dist (tripodCenter x y r) r = dist x r ∧
      dist y (tripodCenter x y r) + dist (tripodCenter x y r) r = dist y r := by
  obtain ⟨hx, hy, hr⟩ := tripodCenter_spec x y r
  rw [TaxiMetric.dist_comm (tripodCenter x y r) r, hx, hy, hr]
  unfold tripodC
  constructor <;> ring

/-- A move of length `t` from `x` toward `r` along the edges through `e`.
The center distance decreases to zero on the `x`-edge and then increases
on the `r`-edge; a shortest path to `r` alone does not enforce this. -/
def alongTripod (x r e p : S) (t : ℝ) : Prop :=
  dist x p = t ∧ dist p r = dist x r - t ∧ dist p e = |dist x e - t|

/-- Bridge points on either side of the center realize every allowed move
along the tripod. -/
theorem alongTripod_exists (x r e : S) (t : ℝ) (h : 0 ≤ t ∧ t ≤ dist x r)
    (he : dist x e + dist e r = dist x r) : ∃ p : S, alongTripod x r e p t := by
  by_cases hxe : t ≤ dist x e
  · obtain ⟨p, hxp, hpe⟩ := TaxiMetric.bridge x e t h.1 hxe
    refine ⟨p, hxp, ?_, ?_⟩
    · have hu := TaxiMetric.dist_triangle p e r
      have hl := TaxiMetric.dist_triangle x p r
      linarith
    · rw [hpe, abs_of_nonneg (sub_nonneg.mpr hxe)]
  · have hxe' : dist x e ≤ t := (not_le.mp hxe).le
    obtain ⟨p, hep, hpr⟩ := TaxiMetric.bridge e r (t - dist x e)
      (sub_nonneg.mpr hxe') (by linarith [h.2])
    refine ⟨p, ?_, ?_, ?_⟩
    · have hu := TaxiMetric.dist_triangle x e p
      have hl := TaxiMetric.dist_triangle x p r
      linarith
    · linarith
    · rw [TaxiMetric.dist_comm p e, hep, abs_of_nonpos (sub_nonpos.mpr hxe')]
      ring

/-- The pickup itself satisfies the tripod constraint at the full distance. -/
theorem alongTripod_end (x r e : S) (he : dist x e + dist e r = dist x r) :
    alongTripod x r e r (dist x r) := by
  refine ⟨rfl, ?_, ?_⟩
  · rw [TaxiMetric.dist_self, sub_self]
  · rw [abs_of_nonpos (by linarith [dist_nonneg e r]), TaxiMetric.dist_comm r e]
    linarith

/-- Choose a movement point subject to the common-tripod constraint. -/
noncomputable def alongTripodPoint (x r e : S) (t : ℝ) (h : 0 ≤ t ∧ t ≤ dist x r)
    (he : dist x e + dist e r = dist x r) : S :=
  Classical.choose (alongTripod_exists x r e t h he)

theorem alongTripodPoint_spec (x r e : S) (t : ℝ) (h : 0 ≤ t ∧ t ≤ dist x r)
    (he : dist x e + dist e r = dist x r) :
    alongTripod x r e (alongTripodPoint x r e t h he) t :=
  Classical.choose_spec (alongTripod_exists x r e t h he)

/-- The online movement phase as a state update: the active taxi follows a
bridge to `r`, and both passive taxis follow the edges through the common
center of `B(x2, x3, r)` (the serving taxi is at `r`). Returns the new online
configuration, the serving taxi, and the movement cost `s1 + s2 + s3`. -/
noncomputable def onlineMove (x1 x2 x3 : S) (ℓ2 ℓ3 : ℝ) (hℓ2 : 0 ≤ ℓ2) (hℓ3 : 0 ≤ ℓ3)
    (r : S) : OState S × Fin 3 × ℝ :=
  let e := tripodCenter x2 x3 r
  (⟨if (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).server = 0 then r
      else alongBridge x1 r
        (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).s1
        (movePhase_s1_mem _ _ _ _ _ _ (dist_nonneg _ _) (dist_nonneg _ _) (dist_nonneg _ _)
          (tripodC_nonneg _ _ _) (tripodC_nonneg' _ _ _) (tripodC_nonneg'' _ _ _) hℓ2 hℓ3),
    if (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).server = 1 then r
      else alongTripodPoint x2 r e
        (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).s2
        (movePhase_s2_mem _ _ _ _ _ _ (dist_nonneg _ _) (dist_nonneg _ _) (dist_nonneg _ _)
          (tripodC_nonneg _ _ _) (tripodC_nonneg' _ _ _) (tripodC_nonneg'' _ _ _) hℓ2 hℓ3)
        (tripodCenter_paths x2 x3 r).1,
    if (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).server = 2 then r
      else alongTripodPoint x3 r e
        (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).s3
        (movePhase_s3_mem _ _ _ _ _ _ (dist_nonneg _ _) (dist_nonneg _ _) (dist_nonneg _ _)
          (tripodC_nonneg _ _ _) (tripodC_nonneg' _ _ _) (tripodC_nonneg'' _ _ _) hℓ2 hℓ3)
        (tripodCenter_paths x2 x3 r).2,
    (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).ℓ2',
    (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).ℓ3'⟩,
    (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).server,
    (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).s1 +
      (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).s2 +
      (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).s3)

/-! ### Interface lemmas for `onlineMove` -/

theorem onlineMove_server (x1 x2 x3 : S) (ℓ2 ℓ3 : ℝ) (hℓ2 : 0 ≤ ℓ2) (hℓ3 : 0 ≤ ℓ3)
    (r : S) :
    (onlineMove x1 x2 x3 ℓ2 ℓ3 hℓ2 hℓ3 r).2.1 =
      (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).server := rfl

theorem onlineMove_ℓ2 (x1 x2 x3 : S) (ℓ2 ℓ3 : ℝ) (hℓ2 : 0 ≤ ℓ2) (hℓ3 : 0 ≤ ℓ3) (r : S) :
    (onlineMove x1 x2 x3 ℓ2 ℓ3 hℓ2 hℓ3 r).1.ℓ2 =
      (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).ℓ2' := rfl

theorem onlineMove_ℓ3 (x1 x2 x3 : S) (ℓ2 ℓ3 : ℝ) (hℓ2 : 0 ≤ ℓ2) (hℓ3 : 0 ≤ ℓ3) (r : S) :
    (onlineMove x1 x2 x3 ℓ2 ℓ3 hℓ2 hℓ3 r).1.ℓ3 =
      (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).ℓ3' := rfl

theorem onlineMove_cost (x1 x2 x3 : S) (ℓ2 ℓ3 : ℝ) (hℓ2 : 0 ≤ ℓ2) (hℓ3 : 0 ≤ ℓ3) (r : S) :
    (onlineMove x1 x2 x3 ℓ2 ℓ3 hℓ2 hℓ3 r).2.2 =
      (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).s1 +
      (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).s2 +
      (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).s3 := rfl

theorem onlineMove_x1_eq (x1 x2 x3 : S) (ℓ2 ℓ3 : ℝ) (hℓ2 : 0 ≤ ℓ2) (hℓ3 : 0 ≤ ℓ3) (r : S)
    (h : (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).server = 0) :
    (onlineMove x1 x2 x3 ℓ2 ℓ3 hℓ2 hℓ3 r).1.x1 = r := by
  unfold onlineMove
  dsimp only
  rw [if_pos h]

theorem onlineMove_x2_eq (x1 x2 x3 : S) (ℓ2 ℓ3 : ℝ) (hℓ2 : 0 ≤ ℓ2) (hℓ3 : 0 ≤ ℓ3) (r : S)
    (h : (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).server = 1) :
    (onlineMove x1 x2 x3 ℓ2 ℓ3 hℓ2 hℓ3 r).1.x2 = r := by
  unfold onlineMove
  dsimp only
  rw [if_pos h]

theorem onlineMove_x3_eq (x1 x2 x3 : S) (ℓ2 ℓ3 : ℝ) (hℓ2 : 0 ≤ ℓ2) (hℓ3 : 0 ≤ ℓ3) (r : S)
    (h : (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).server = 2) :
    (onlineMove x1 x2 x3 ℓ2 ℓ3 hℓ2 hℓ3 r).1.x3 = r := by
  unfold onlineMove
  dsimp only
  rw [if_pos h]

theorem onlineMove_x1_traveled (x1 x2 x3 : S) (ℓ2 ℓ3 : ℝ) (hℓ2 : 0 ≤ ℓ2) (hℓ3 : 0 ≤ ℓ3)
    (r : S) :
    dist x1 (onlineMove x1 x2 x3 ℓ2 ℓ3 hℓ2 hℓ3 r).1.x1 =
        (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).s1 ∧
      dist ((onlineMove x1 x2 x3 ℓ2 ℓ3 hℓ2 hℓ3 r).1.x1) r =
        dist x1 r - (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).s1 := by
  by_cases h : (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).server = 0
  · rw [onlineMove_x1_eq _ _ _ _ _ _ _ _ h]
    have hs1 := (movePhase_s_eq_of_server (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3)
      ℓ2 ℓ3 (dist_nonneg _ _) (dist_nonneg _ _) (dist_nonneg _ _) (tripodC_nonneg _ _ _)
      (tripodC_nonneg' _ _ _) (tripodC_nonneg'' _ _ _) hℓ2 hℓ3).1 h
    constructor
    · exact hs1.symm
    · rw [hs1, TaxiMetric.dist_self]
      ring
  · unfold onlineMove
    dsimp only
    rw [if_neg h]
    exact alongBridge_spec _ _ _ _

theorem onlineMove_x2_traveled (x1 x2 x3 : S) (ℓ2 ℓ3 : ℝ) (hℓ2 : 0 ≤ ℓ2) (hℓ3 : 0 ≤ ℓ3)
    (r : S) :
    dist x2 (onlineMove x1 x2 x3 ℓ2 ℓ3 hℓ2 hℓ3 r).1.x2 =
        (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).s2 ∧
      dist ((onlineMove x1 x2 x3 ℓ2 ℓ3 hℓ2 hℓ3 r).1.x2) r =
        dist x2 r - (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).s2 := by
  by_cases h : (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).server = 1
  · rw [onlineMove_x2_eq _ _ _ _ _ _ _ _ h]
    have hs2 := (movePhase_s_eq_of_server (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3)
      ℓ2 ℓ3 (dist_nonneg _ _) (dist_nonneg _ _) (dist_nonneg _ _) (tripodC_nonneg _ _ _)
      (tripodC_nonneg' _ _ _) (tripodC_nonneg'' _ _ _) hℓ2 hℓ3).2.1 h
    constructor
    · exact hs2.symm
    · rw [hs2, TaxiMetric.dist_self]
      ring
  · unfold onlineMove
    dsimp only
    rw [if_neg h]
    exact ⟨(alongTripodPoint_spec _ _ _ _ _ _).1, (alongTripodPoint_spec _ _ _ _ _ _).2.1⟩

theorem onlineMove_x3_traveled (x1 x2 x3 : S) (ℓ2 ℓ3 : ℝ) (hℓ2 : 0 ≤ ℓ2) (hℓ3 : 0 ≤ ℓ3)
    (r : S) :
    dist x3 (onlineMove x1 x2 x3 ℓ2 ℓ3 hℓ2 hℓ3 r).1.x3 =
        (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).s3 ∧
      dist ((onlineMove x1 x2 x3 ℓ2 ℓ3 hℓ2 hℓ3 r).1.x3) r =
        dist x3 r - (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).s3 := by
  by_cases h : (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).server = 2
  · rw [onlineMove_x3_eq _ _ _ _ _ _ _ _ h]
    have hs3 := (movePhase_s_eq_of_server (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3)
      ℓ2 ℓ3 (dist_nonneg _ _) (dist_nonneg _ _) (dist_nonneg _ _) (tripodC_nonneg _ _ _)
      (tripodC_nonneg' _ _ _) (tripodC_nonneg'' _ _ _) hℓ2 hℓ3).2.2 h
    constructor
    · exact hs3.symm
    · rw [hs3, TaxiMetric.dist_self]
      ring
  · unfold onlineMove
    dsimp only
    rw [if_neg h]
    exact ⟨(alongTripodPoint_spec _ _ _ _ _ _).1, (alongTripodPoint_spec _ _ _ _ _ _).2.1⟩

/-- The first passive taxi follows the chosen common tripod, including when
it serves the request. -/
theorem onlineMove_x2_alongTripod (x1 x2 x3 : S) (ℓ2 ℓ3 : ℝ)
    (hℓ2 : 0 ≤ ℓ2) (hℓ3 : 0 ≤ ℓ3) (r : S) :
    alongTripod x2 r (tripodCenter x2 x3 r)
      (onlineMove x1 x2 x3 ℓ2 ℓ3 hℓ2 hℓ3 r).1.x2
      (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).s2 := by
  by_cases h : (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).server = 1
  · have ht := (onlineMove_x2_traveled x1 x2 x3 ℓ2 ℓ3 hℓ2 hℓ3 r).1
    rw [onlineMove_x2_eq _ _ _ _ _ _ _ _ h] at ht ⊢
    rw [← ht]
    exact alongTripod_end _ _ _ (tripodCenter_paths x2 x3 r).1
  · unfold onlineMove
    dsimp only
    rw [if_neg h]
    exact alongTripodPoint_spec _ _ _ _ _ _

/-- The second passive taxi follows that same chosen center, including when
it serves the request. -/
theorem onlineMove_x3_alongTripod (x1 x2 x3 : S) (ℓ2 ℓ3 : ℝ)
    (hℓ2 : 0 ≤ ℓ2) (hℓ3 : 0 ≤ ℓ3) (r : S) :
    alongTripod x3 r (tripodCenter x2 x3 r)
      (onlineMove x1 x2 x3 ℓ2 ℓ3 hℓ2 hℓ3 r).1.x3
      (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).s3 := by
  by_cases h : (movePhase (dist x1 r) (dist x2 r) (dist x3 r) (dist x2 x3) ℓ2 ℓ3).server = 2
  · have ht := (onlineMove_x3_traveled x1 x2 x3 ℓ2 ℓ3 hℓ2 hℓ3 r).1
    rw [onlineMove_x3_eq _ _ _ _ _ _ _ _ h] at ht ⊢
    rw [← ht]
    exact alongTripod_end _ _ _ (tripodCenter_paths x2 x3 r).2
  · unfold onlineMove
    dsimp only
    rw [if_neg h]
    exact alongTripodPoint_spec _ _ _ _ _ _

/-! ### The four phases of a request -/

/-- Replace offline taxi `j` by the point `y'`. -/
def setY (st : FState S) (j : Fin 3) (y' : S) : FState S :=
  { st with y1 := if j = 0 then y' else st.y1,
            y2 := if j = 1 then y' else st.y2,
            y3 := if j = 2 then y' else st.y3 }

/-- Phase 1: the offline algorithm moves taxi `j` to the pick-up
point. -/
def offlineMove (st : FState S) (r : S) (j : Fin 3) : FState S := setY st j r

/-- Phase 2 as a full-state update: the online taxis after the movement
phase; the offline taxis unchanged. -/
noncomputable def onlineMoveFull (st : FState S) (hℓ2 : 0 ≤ st.ℓ2) (hℓ3 : 0 ≤ st.ℓ3)
    (r : S) : FState S :=
  let om := onlineMove st.x1 st.x2 st.x3 st.ℓ2 st.ℓ3 hℓ2 hℓ3 r
  { st with x1 := om.1.x1, x2 := om.1.x2, x3 := om.1.x3, ℓ2 := om.1.ℓ2, ℓ3 := om.1.ℓ3 }

/-- The reorganization of the online configuration: if a passive taxi
reached `r`, it becomes the new active taxi and the interval lengths are
updated. -/
noncomputable def reorgPhase (om : OState S) (r : S) (server : Fin 3) : OState S :=
  if server = 0 then om
  else if server = 1 then
    { x1 := r, x2 := om.x1, x3 := om.x3,
      ℓ2 := max 0 (om.ℓ2 - dist om.x1 om.x2),
      ℓ3 := min (om.ℓ3 + tripodC (dist om.x1 om.x2) (dist om.x1 om.x3) (dist om.x2 om.x3))
        (dist om.x1 om.x3) }
  else
    { x1 := r, x2 := om.x2, x3 := om.x1,
      ℓ2 := min (om.ℓ2 + tripodC (dist om.x1 om.x2) (dist om.x1 om.x3) (dist om.x2 om.x3))
        (dist om.x1 om.x2),
      ℓ3 := max 0 (om.ℓ3 - dist om.x1 om.x3) }

/-- Phase 3 as a full-state update: the online reorganization together with
the offline reindexing (the offline taxi at `r` becomes the active one). -/
noncomputable def reorgApply (st : FState S) (hℓ2 : 0 ≤ st.ℓ2) (hℓ3 : 0 ≤ st.ℓ3)
    (r : S) (j : Fin 3) : FState S :=
  let om := onlineMove st.x1 st.x2 st.x3 st.ℓ2 st.ℓ3 hℓ2 hℓ3 r
  let orr := reorgPhase om.1 r om.2.1
  { x1 := orr.x1, x2 := orr.x2, x3 := orr.x3, ℓ2 := orr.ℓ2, ℓ3 := orr.ℓ3,
    y1 := r,
    y2 := if j = 0 then st.y2 else st.y1,
    y3 := if j ≤ 1 then st.y3 else st.y2 }

/-- Phase 4: relocation — the active taxis serve the request and move to
the drop-off point (free in the hard k-taxi problem). -/
def serveOnly (st : FState S) (s : S) : FState S := { st with x1 := s, y1 := s }

/-- The full per-request transition: offline movement of taxi `j` to `r`
(offline cost `d(y_j, r)`), online movement (online cost `s1 + s2 + s3`),
reorganization, and relocation to `s`. -/
noncomputable def serveRequest (st : FState S) (hℓ2 : 0 ≤ st.ℓ2) (hℓ3 : 0 ≤ st.ℓ3)
    (r s : S) (j : Fin 3) : FState S × ℝ × ℝ :=
  (serveOnly (reorgApply st hℓ2 hℓ3 r j) s,
    (onlineMove st.x1 st.x2 st.x3 st.ℓ2 st.ℓ3 hℓ2 hℓ3 r).2.2, dist (yjOf st j) r)

/-- The interval lengths stay nonnegative along the per-request
transition. -/
theorem serveRequest_ℓ_nonneg (st : FState S) (hℓ2 : 0 ≤ st.ℓ2) (hℓ3 : 0 ≤ st.ℓ3)
    (r s : S) (j : Fin 3) :
    0 ≤ (serveRequest st hℓ2 hℓ3 r s j).1.ℓ2 ∧
      0 ≤ (serveRequest st hℓ2 hℓ3 r s j).1.ℓ3 := by
  have hnn := movePhase_ℓ_nonneg (dist st.x1 r) (dist st.x2 r) (dist st.x3 r)
    (dist st.x2 st.x3) st.ℓ2 st.ℓ3 (dist_nonneg _ _) (dist_nonneg _ _) (dist_nonneg _ _)
    (tripodC_nonneg _ _ _) (tripodC_nonneg' _ _ _) (tripodC_nonneg'' _ _ _) hℓ2 hℓ3
  have hnn2 : 0 ≤ (onlineMove st.x1 st.x2 st.x3 st.ℓ2 st.ℓ3 hℓ2 hℓ3 r).1.ℓ2 := hnn.1
  have hnn3 : 0 ≤ (onlineMove st.x1 st.x2 st.x3 st.ℓ2 st.ℓ3 hℓ2 hℓ3 r).1.ℓ3 := hnn.2
  have hf := tripodC_nonneg ((onlineMove st.x1 st.x2 st.x3 st.ℓ2 st.ℓ3 hℓ2 hℓ3 r).1.x1)
    ((onlineMove st.x1 st.x2 st.x3 st.ℓ2 st.ℓ3 hℓ2 hℓ3 r).1.x2)
    ((onlineMove st.x1 st.x2 st.x3 st.ℓ2 st.ℓ3 hℓ2 hℓ3 r).1.x3)
  have e2 : (serveRequest st hℓ2 hℓ3 r s j).1.ℓ2 =
      (reorgPhase (onlineMove st.x1 st.x2 st.x3 st.ℓ2 st.ℓ3 hℓ2 hℓ3 r).1 r
        (onlineMove st.x1 st.x2 st.x3 st.ℓ2 st.ℓ3 hℓ2 hℓ3 r).2.1).ℓ2 := rfl
  have e3 : (serveRequest st hℓ2 hℓ3 r s j).1.ℓ3 =
      (reorgPhase (onlineMove st.x1 st.x2 st.x3 st.ℓ2 st.ℓ3 hℓ2 hℓ3 r).1 r
        (onlineMove st.x1 st.x2 st.x3 st.ℓ2 st.ℓ3 hℓ2 hℓ3 r).2.1).ℓ3 := rfl
  rw [e2, e3]
  by_cases h0 : (onlineMove st.x1 st.x2 st.x3 st.ℓ2 st.ℓ3 hℓ2 hℓ3 r).2.1 = 0
  · unfold reorgPhase
    rw [if_pos h0]
    exact ⟨hnn2, hnn3⟩
  · by_cases h1 : (onlineMove st.x1 st.x2 st.x3 st.ℓ2 st.ℓ3 hℓ2 hℓ3 r).2.1 = 1
    · unfold reorgPhase
      rw [if_neg h0, if_pos h1]
      refine ⟨le_max_left _ _, ?_⟩
      exact le_min (by linarith [hnn3, hf]) (dist_nonneg _ _)
    · unfold reorgPhase
      rw [if_neg h0, if_neg h1]
      refine ⟨?_, le_max_left _ _⟩
      exact le_min (by linarith [hnn2, hf]) (dist_nonneg _ _)

/-- The trajectory: fold the per-request transition over the request list.
`reqs` pairs each request `(r, s)` with the offline choice `j`. Returns the
final state, the total online cost, and the total offline cost. -/
noncomputable def runTrj (st : FState S) (hℓ2 : 0 ≤ st.ℓ2) (hℓ3 : 0 ≤ st.ℓ3) :
    List ((S × S) × Fin 3) → FState S × ℝ × ℝ
  | [] => (st, 0, 0)
  | ((r, s), j) :: rest =>
      let out := serveRequest st hℓ2 hℓ3 r s j
      let out' := runTrj out.1 (serveRequest_ℓ_nonneg st hℓ2 hℓ3 r s j).1
        (serveRequest_ℓ_nonneg st hℓ2 hℓ3 r s j).2 rest
      (out'.1, out.2.1 + out'.2.1, out.2.2 + out'.2.2)

/-- The potential at the initial configuration (coinciding configurations,
zero intervals) is zero. -/
theorem phi_init (st : FState S) (h1 : st.x1 = st.y1) (h2 : st.x2 = st.y2)
    (h3 : st.x3 = st.y3) (hℓ2 : st.ℓ2 = 0) (hℓ3 : st.ℓ3 = 0) : st.phi = 0 := by
  have e1 : dist st.x1 st.y1 = 0 := by rw [← h1]; exact TaxiMetric.dist_self _
  have e2 : dist st.x2 st.y2 = 0 := by rw [← h2]; exact TaxiMetric.dist_self _
  have e3 : dist st.x3 st.y3 = 0 := by rw [← h3]; exact TaxiMetric.dist_self _
  have e4 : dist st.x3 st.y2 = dist st.x2 st.x3 := by rw [← h2]; exact TaxiMetric.dist_comm _ _
  have e5 : dist st.x2 st.y3 = dist st.x2 st.x3 := by rw [← h3]
  have hdd : 0 ≤ dist st.x2 st.x3 := dist_nonneg _ _
  simp only [FState.phi, Phi, Mpot, matchSum, distContrib, SigmaPot, tripodC, cPsi, cAlpha,
    cBeta, e1, e2, e3, e4, e5, hℓ2, hℓ3, min_def, max_def]
  split_ifs with ha hb hc hd he hf hg hh <;> linarith

end



section

variable {S : Type} [TaxiMetric S]

open TaxiMetric

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.








-- @[checkpoint c8 difficulty=hard]
/-- The main theorem: TripodTracker is `κ`-competitive for the hard
3-taxi problem for some constant `κ`. Stated for the trajectory semantics
`runTrj`: for every initial state with coinciding online/offline
configurations and zero intervals, and for every request sequence paired
with offline choices, the total online cost is at most `κ` times the total
offline cost (the additive constant is `0`, since `Φ₀ = 0`). -/
theorem tripod_tracker_competitive :
    ∃ κ : ℝ, 0 < κ ∧ ∀ (st : FState S) (hxy1 : st.x1 = st.y1) (hxy2 : st.x2 = st.y2)
        (hxy3 : st.x3 = st.y3) (h2 : st.ℓ2 = 0) (h3 : st.ℓ3 = 0)
        (reqs : List ((S × S) × Fin 3)),
      (runTrj st (le_of_eq h2.symm) (le_of_eq h3.symm) reqs).2.1 ≤
        κ * (runTrj st (le_of_eq h2.symm) (le_of_eq h3.symm) reqs).2.2 := by
  -- CHECKPOINT tripod_tracker_competitive BEGIN
  sorry
  -- CHECKPOINT tripod_tracker_competitive END

end

end ThreeTaxi
