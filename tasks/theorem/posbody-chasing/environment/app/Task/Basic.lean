/-
Self-contained statement layer for a theorem in online algorithms:
an explicit competitive bound for chasing positive bodies in ℓ1.

The fixed part (everything above the end-of-fixed-part marker line) is the
definition layer the main theorem's statement needs: the weighted KL term
and its basic inequalities, the instance data (weight vector,
covering/packing constraint sequence, sparsity bound d, augmentation ε),
the additive offset ε/(4·d^t·c^t_i) of the algorithm's covering update,
the response bundle `ChaseRun` (the trajectory x together with the KKT
multipliers y, z of the two projection programs, with the KKT conditions,
the monotonicity and frozenness properties, and the boundary conventions
y⁰ = z⁰ = x⁰ = 0), the auxiliary linear program (P) through its primal
feasibility predicate and upward-recourse objective, the dual program (D)
through its feasibility predicate and objective, and the dual construction
objects (the segment sum, the constant A = log(1 + 40d²/ε²), and the
scaled dual (ȳ, z̄, r̄)). Fidelity notes live in `tests/reference/`.
-/

import Mathlib

namespace PosBodyChasing

/-! ## Generic inequalities for the weighted KL term -/

/-- Term-by-term nonnegativity of the KL divergence: for `y > 0`,
`x·log(x/y) − x + y ≥ 0` (from `log(y/x) ≤ y/x − 1`). -/
theorem kl_term_nonneg {x y : ℝ} (hx : 0 ≤ x) (hy : 0 < y) :
    0 ≤ x * Real.log (x / y) - x + y := by
  rcases hx.eq_or_lt with rfl | hx
  · simp [hy.le]
  have h1 : Real.log (y / x) ≤ y / x - 1 :=
    Real.log_le_sub_one_of_pos (by positivity)
  have h2 : Real.log (y / x) = Real.log y - Real.log x :=
    Real.log_div (ne_of_gt hy) (ne_of_gt hx)
  have h3 : Real.log (x / y) = Real.log x - Real.log y :=
    Real.log_div (ne_of_gt hx) (ne_of_gt hy)
  have h4 : x - y ≤ x * Real.log (x / y) := by
    have h5 : 1 - y / x ≤ Real.log (x / y) := by linarith
    have h6 := mul_le_mul_of_nonneg_left h5 hx.le
    have h7 : x * (1 - y / x) = x - y := by field_simp
    linarith
  linarith

/-- The "poor man's Pinsker" inequality: for `0 < b ≤ a`,
`a − b ≤ a·log(a/b)` (from `1 + u ≤ exp u` at
`u = log(b/a)`). -/
theorem sub_le_mul_log {a b : ℝ} (hb : 0 < b) (hba : b ≤ a) :
    a - b ≤ a * Real.log (a / b) := by
  have ha : 0 < a := lt_of_lt_of_le hb hba
  have hba' : 0 < b / a := by positivity
  have h1 : Real.log (b / a) + 1 ≤ Real.exp (Real.log (b / a)) :=
    Real.add_one_le_exp _
  rw [Real.exp_log hba'] at h1
  have h2 : Real.log (b / a) = Real.log b - Real.log a :=
    Real.log_div (ne_of_gt hb) (ne_of_gt ha)
  have h3 : Real.log (a / b) = Real.log a - Real.log b :=
    Real.log_div (ne_of_gt ha) (ne_of_gt hb)
  have h4 : a - b ≤ a * Real.log (a / b) := by
    have h5 : 1 - b / a ≤ Real.log (a / b) := by linarith
    have h6 := mul_le_mul_of_nonneg_left h5 ha.le
    have h7 : a * (1 - b / a) = a - b := by field_simp
    linarith
  exact h4

/-- Adding a larger constant to numerator and denominator decreases a ratio
that is at least `1`: for `0 ≤ v ≤ u` and `0 < A ≤ B`,
`(u + B)/(v + B) ≤ (u + A)/(v + A)`. -/
theorem ratio_add_le_ratio_add {u v A B : ℝ} (hv : 0 ≤ v) (hvu : v ≤ u)
    (hA : 0 < A) (hAB : A ≤ B) : (u + B) / (v + B) ≤ (u + A) / (v + A) := by
  have h1 : 0 < v + A := by linarith
  have h2 : 0 < v + B := by linarith
  rw [div_le_iff₀ h2, div_mul_eq_mul_div, le_div_iff₀ h1]
  nlinarith [mul_nonneg (sub_nonneg.2 hvu) (sub_nonneg.2 hAB)]

/-- Adding a positive constant to numerator and denominator increases a ratio
that is at most `1`: for `0 ≤ u ≤ v`, `v > 0` and `A > 0`,
`u/v ≤ (u + A)/(v + A)`. -/
theorem ratio_le_ratio_add {u v A : ℝ} (hv : 0 < v) (huv : u ≤ v) (hA : 0 < A) :
    u / v ≤ (u + A) / (v + A) := by
  have h1 : 0 < v + A := by linarith
  rw [div_le_iff₀ hv, div_mul_eq_mul_div, le_div_iff₀ h1]
  nlinarith [mul_le_mul_of_nonneg_right huv hA.le]

/-- Monotonicity of the real logarithm, in `≤` form. -/
theorem log_le_log' {x y : ℝ} (hx : 0 < x) (hxy : x ≤ y) :
    Real.log x ≤ Real.log y := by
  rcases hxy.eq_or_lt with rfl | h
  · exact le_refl _
  · exact le_of_lt (Real.log_lt_log hx h)

/-- Telescoping sums over `Icc 1 T`: `∑_{t=1}^{T} (f t − f (t−1)) = f T − f 0`. -/
theorem sum_Icc_one_sub (f : ℕ → ℝ) (T : ℕ) :
    ∑ t ∈ Finset.Icc 1 T, (f t - f (t - 1)) = f T - f 0 := by
  induction T with
  | zero =>
    rw [Finset.Icc_eq_empty (by omega : ¬ 1 ≤ 0)]
    simp
  | succ k ih =>
    rw [Finset.sum_Icc_succ_top (by omega : 1 ≤ k + 1), ih]
    simp [Nat.add_sub_cancel]

/-! ## Instance data -/

/-- The data of a positive-halfspace chasing instance: the ambient dimension
`n`, the horizon `T`, the augmentation parameter `ε ∈ (0, 1]`, the positive
weight vector `w`, the constraint sequence (at each time `t ∈ [1, T]` either
a covering constraint `⟨a t, x⟩ ≥ 1` or a packing constraint
`⟨a t, x⟩ ≤ 1 + ε`, flagged by `isCov`) with nonnegative coefficients, and
the bound `d ≥ 1` on the row sparsity of every covering constraint. -/
structure ChaseData where
  n : ℕ
  T : ℕ
  ε : ℝ
  hε0 : 0 < ε
  hε1 : ε ≤ 1
  w : Fin n → ℝ
  hw : ∀ i, 0 < w i
  isCov : ℕ → Bool
  a : ℕ → Fin n → ℝ
  ha : ∀ t i, 0 ≤ a t i
  d : ℕ
  hd : 0 < d
  hsp : ∀ t, isCov t = true →
    (Finset.univ.filter fun i => a t i ≠ 0).card ≤ d

namespace ChaseData

/-- The support of the constraint at time `t`. -/
noncomputable def supp (D : ChaseData) (t : ℕ) : Finset (Fin D.n) :=
  Finset.univ.filter fun i => D.a t i ≠ 0

/-- The sparsity `d^t` of the constraint at time `t`. -/
noncomputable def dCov (D : ChaseData) (t : ℕ) : ℕ := (D.supp t).card

/-- The additive offset `ε/(4·d^t·c^t_i)` of the covering update (with the
convention that at time `t` both shifted points use the time-`t` offset). -/
noncomputable def off (D : ChaseData) (t : ℕ) (i : Fin D.n) : ℝ :=
  D.ε / (4 * (D.dCov t : ℝ) * D.a t i)

/-- The constant `A = log(1 + 40d²/ε²)` of the dual construction. -/
noncomputable def Aconst (D : ChaseData) : ℝ :=
  Real.log (1 + 40 * (D.d : ℝ)^2 / D.ε^2)

/-- `A > 0` (since `d ≥ 1` and `ε > 0`). -/
theorem Aconst_pos (D : ChaseData) : 0 < D.Aconst := by
  unfold Aconst
  apply Real.log_pos
  have hd : (0:ℝ) < (D.d : ℝ) := by exact_mod_cast D.hd
  have hε := D.hε0
  have hpos : (0:ℝ) < 40 * (D.d : ℝ)^2 / D.ε^2 := by positivity
  linarith

end ChaseData

/-- The shifted point `x̂`: the point at time `u` with the time-`t` offset
(`x̂^t_i = x^t_i + ε/(4·d^t·c^t_i)` and likewise for `x̂^{t-1}` at the same
time `t`). -/
noncomputable def xhat (D : ChaseData) (x : ℕ → Fin D.n → ℝ) (t u : ℕ)
    (i : Fin D.n) : ℝ :=
  x u i + D.off t i

/-- The segment sum `∑_{τ ∈ C ∩ [s,t]} c^τ_i·y^τ − ∑_{τ ∈ P ∩ [s,t]}
p^τ_i·z^τ` of the dual construction. -/
noncomputable def segSum (D : ChaseData) (yt z : ℕ → ℝ) (i : Fin D.n)
    (s t : ℕ) : ℝ :=
  (∑ τ ∈ (Finset.Icc s t).filter (fun τ => D.isCov τ = true), D.a τ i * yt τ) -
    ∑ τ ∈ (Finset.Icc s t).filter (fun τ => D.isCov τ = false), D.a τ i * z τ

/-- `cmax_i(S) = max_{τ ∈ S} c^τ_i`, with value `0` for empty `S`. -/
noncomputable def cmaxS (D : ChaseData) (S : Finset ℕ) (i : Fin D.n) : ℝ :=
  if h : S.Nonempty then S.sup' h (fun τ => D.a τ i) else 0

/-- The scaled covering dual `ȳ = ỹ/A`. -/
noncomputable def ybar (D : ChaseData) (yt : ℕ → ℝ) (s : ℕ) : ℝ :=
  yt s / D.Aconst

/-- The scaled packing dual `z̄ = z/A`. -/
noncomputable def zbar (D : ChaseData) (z : ℕ → ℝ) (s : ℕ) : ℝ :=
  z s / D.Aconst

/-- The dual variable `r̄`: `r̄^s_i = (1/A)·max(0, max_{t ∈
[s, T]} (segment sum over [s, t]))`, and `0` for `s > T` (in particular
`r̄^{T+1} = 0`). -/
noncomputable def rbar (D : ChaseData) (yt z : ℕ → ℝ) (s : ℕ)
    (i : Fin D.n) : ℝ :=
  if h : s ≤ D.T then
    (D.Aconst)⁻¹ * max 0 ((Finset.Icc s D.T).sup'
      ⟨s, Finset.left_mem_Icc.2 h⟩ (fun t => segSum D yt z i s t))
  else 0

/-- The upward recourse of a trajectory: `∑_{t=1}^{T} ∑_i w_i·(x^t_i −
x^{t-1}_i)⁺`. -/
noncomputable def upwardRec (D : ChaseData) (x : ℕ → Fin D.n → ℝ) : ℝ :=
  ∑ t ∈ Finset.Icc 1 D.T, ∑ i, D.w i * max (x t i - x (t - 1) i) 0

/-- Primal feasibility of a benchmark trajectory for the auxiliary program
(P): starts at `0`, stays nonnegative, and satisfies every constraint exactly
(covering `≥ 1`, packing `≤ 1`, without augmentation). -/
def PrimalFeas (D : ChaseData) (x' : ℕ → Fin D.n → ℝ) : Prop :=
  (∀ i, x' 0 i = 0) ∧ (∀ t i, 0 ≤ x' t i) ∧
    (∀ t ∈ Finset.Icc 1 D.T, D.isCov t = true → 1 ≤ ∑ i, D.a t i * x' t i) ∧
    (∀ t ∈ Finset.Icc 1 D.T, D.isCov t = false → ∑ i, D.a t i * x' t i ≤ 1)

/-- Feasibility of a dual solution `(y', z', r')` for the dual program (D):
nonnegativity, the type conventions, the boundary `r'^{T+1} =
0`, the box `0 ≤ r' ≤ w`, and the two constraint families
`c^t_i·y'^t ≤ r'^t_i − r'^{t+1}_i` (covering) and
`−p^t_i·z'^t ≤ r'^t_i − r'^{t+1}_i` (packing). -/
def DualFeas (D : ChaseData) (y' z' : ℕ → ℝ) (r' : ℕ → Fin D.n → ℝ) : Prop :=
  (∀ t, 0 ≤ y' t) ∧ (∀ t, 0 ≤ z' t) ∧
    (∀ t, D.isCov t = false → y' t = 0) ∧
    (∀ t, D.isCov t = true → z' t = 0) ∧
    (∀ i, r' (D.T + 1) i = 0) ∧ (∀ t i, 0 ≤ r' t i) ∧
    (∀ t ∈ Finset.Icc 1 D.T, ∀ i, r' t i ≤ D.w i) ∧
    (∀ t ∈ Finset.Icc 1 D.T, D.isCov t = true → ∀ i,
      D.a t i * y' t ≤ r' t i - r' (t + 1) i) ∧
    (∀ t ∈ Finset.Icc 1 D.T, D.isCov t = false → ∀ i,
      -(D.a t i * z' t) ≤ r' t i - r' (t + 1) i)

/-- The dual objective `∑_{t ∈ C} y'^t − ∑_{t ∈ P} z'^t`, written over
`[1, T]` (the off-type values are `0` for any feasible dual). -/
noncomputable def dualObj (D : ChaseData) (y' z' : ℕ → ℝ) : ℝ :=
  ∑ t ∈ Finset.Icc 1 D.T, (y' t - z' t)

/-- A response of the algorithm, packaged through the
properties the analysis uses: the trajectory `x` with `x⁰ = 0`, the KKT
multipliers `y, z` (nonnegative, vanishing off their constraint type and at
time `0`), and at every time `t ∈ [1, T]`:
- covering: `x` increases coordinatewise, is frozen outside the support,
  satisfies the tightness condition `⟨c^t, x^t⟩ = 1`, and the multiplier
  condition `w_i·log(x̂^t_i/x̂^{t-1}_i) = c^t_i·y^t` on the support;
- packing: `x` decreases coordinatewise, is frozen outside the support,
  satisfies the tightness condition `⟨p^t, x^t⟩ = 1 + ε`, and the
  multiplier condition `w_i·log(x^t_i/x^{t-1}_i) = −p^t_i·z^t` on the
  support wherever `x^{t-1}_i > 0`. -/
structure ChaseRun (D : ChaseData) where
  x : ℕ → Fin D.n → ℝ
  y : ℕ → ℝ
  z : ℕ → ℝ
  hx0 : ∀ i, x 0 i = 0
  hxnn : ∀ t i, 0 ≤ x t i
  hy0 : y 0 = 0
  hz0 : z 0 = 0
  hynn : ∀ t, 0 ≤ y t
  hznn : ∀ t, 0 ≤ z t
  hy_off : ∀ t, D.isCov t = false → y t = 0
  hz_off : ∀ t, D.isCov t = true → z t = 0
  cov_mono : ∀ t ∈ Finset.Icc 1 D.T, D.isCov t = true → ∀ i,
    x (t - 1) i ≤ x t i
  cov_frozen : ∀ t ∈ Finset.Icc 1 D.T, D.isCov t = true → ∀ i,
    D.a t i = 0 → x t i = x (t - 1) i
  cov_tight : ∀ t ∈ Finset.Icc 1 D.T, D.isCov t = true →
    ∑ i, D.a t i * x t i = 1
  cov_kkt : ∀ t ∈ Finset.Icc 1 D.T, D.isCov t = true → ∀ i, D.a t i ≠ 0 →
    D.w i * Real.log (xhat D x t t i / xhat D x t (t - 1) i) = D.a t i * y t
  pack_mono : ∀ t ∈ Finset.Icc 1 D.T, D.isCov t = false → ∀ i,
    x t i ≤ x (t - 1) i
  pack_frozen : ∀ t ∈ Finset.Icc 1 D.T, D.isCov t = false → ∀ i,
    D.a t i = 0 → x t i = x (t - 1) i
  pack_tight : ∀ t ∈ Finset.Icc 1 D.T, D.isCov t = false →
    ∑ i, D.a t i * x t i = 1 + D.ε
  pack_kkt : ∀ t ∈ Finset.Icc 1 D.T, D.isCov t = false → ∀ i, D.a t i ≠ 0 →
    0 < x (t - 1) i →
    D.w i * Real.log (x t i / x (t - 1) i) = -(D.a t i * z t)
  pack_pos : ∀ t ∈ Finset.Icc 1 D.T, D.isCov t = false → ∀ i,
    D.a t i ≠ 0 → 0 < x (t - 1) i → 0 < x t i

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.



-- @[checkpoint c8 difficulty=hard]
/-- The main theorem: the algorithm is
`K`-competitive with `K = (2 + ε)(1 + ε)·log(1 + 40d²/ε²)/ε =
O((1/ε)·log(d/ε))`: its upward recourse is at most `K` times the upward
recourse of every exactly-feasible benchmark trajectory. -/
theorem chasing_positive_bodies_competitive (D : ChaseData) (R : ChaseRun D) :
    ∀ x' : ℕ → Fin D.n → ℝ, PrimalFeas D x' →
      upwardRec D R.x ≤
        (2 + D.ε) * (1 + D.ε) / D.ε * D.Aconst * upwardRec D x' := by
  -- CHECKPOINT chasing_positive_bodies_competitive BEGIN
  sorry
  -- CHECKPOINT chasing_positive_bodies_competitive END

end PosBodyChasing
