/-
Statement layer for the polar-code scaling-exponent conjecture: for
transmission over a binary memoryless symmetric (BMS) channel `W` with a polar
code (Arikan 2009) of block length `N` and rate `R`, the gap to capacity
`I(W) − R` at fixed error probability scales as `N^(−1/μ)`, where `μ` is the
scaling exponent. It is conjectured that `μ = 3.627` universally over BMS
channels (the value heuristically computed for the binary erasure channel by
Korada–Montanari–Telatar–Urbanke, ISIT 2010; the universal conjecture is
explicit in Mondelli–Hassani–Urbanke, IEEE Trans. Inf. Theory 2016). Proved
universal bounds: `3.579 ≤ μ` (Hassani–Alishahi–Urbanke, IEEE Trans. Inf.
Theory 2014) and `μ ≤ 4.63` (Wang–Lin–Vardy–Gabrys 2022, improving
`μ ≤ 4.714` of Mondelli–Hassani–Urbanke 2016).

The two main slots of this task ask for a strict improvement of either side at
the threshold 4.0 (which lies strictly inside the proved interval
(3.579, 4.63)): prove that the universal scaling exponent is at most 4
(improving the upper bound 4.63 → 4.0), or prove that some BMS channel
requires an exponent above 4 (improving the lower bound 3.579 → 4.0).

This file is the task's definition zone plus slot zone:
- The definition zone defines binary-input channels with finite output
  alphabets as explicit transition laws (`Channel`), output symmetry
  (`IsBMS`), the Bhattacharyya parameter `Z` and the symmetric mutual
  information `I`, Arikan's channel transforms `polarMinus`/`polarPlus` and the
  depth-`n` synthetic channels `polarChannel`, the finite Bhattacharyya
  process `fracGood`, the scaling predicate `ScalingExponentLe`, the binary
  erasure channel `BEC`, and the polar generator matrices `polarGen`
  (bit-reversed Kronecker powers of the Arikan kernel). Well-formedness of the
  transforms and the basic sanity lemmas are fully proved.
- The slot zone states the threshold conjecture (`conj`) and its negation
  (`refuted`), plus three checkpoint special cases. All five proof bodies are
  left blank.

Fidelity notes (see `tests/reference/concept-ledger.md` of the packaged task):
1. The scaling exponent is stated in the Bhattacharyya-process form: `W` has
   scaling exponent at most `ν` iff for every `0 < β < 1/ν`,
   `liminf P(Z_n ≤ 2^(−n^β)) ≥ I(W)`. This is the form used by
   Hassani–Alishahi–Urbanke 2014 and Mondelli–Hassani–Urbanke 2016; the
   equivalent blocklength–gap form (fix `P_e`, then `N = Θ((I(W)−R)^(−μ))`)
   is the operational reading. Only finite-depth distributions are needed:
   `P(Z_n ≤ t)` is the uniform average over the `2^n` transform sequences, so
   no measure theory enters the statement layer.
2. Channels are finite-alphabet explicit transition laws (`Fin 2 → Y → ℝ`
   with nonnegativity and unit-sum proofs), which is the standard DMC
   definition; the erasure channel's alphabet is `Option (Fin 2)` with `none`
   as the erasure symbol.
3. `Z` and `I` are the textbook formulas; `I` is the mutual information with
   uniform input (the symmetric capacity), with the convention `0 · log 0 = 0`
   handled by `xlog2`.
-/

import Mathlib

namespace PolarScaling

/-! ### Channels: binary input, finite output alphabet -/

/-- A binary-input discrete memoryless channel with finite output alphabet
`Y`: an explicit transition law. `toFun u y` is the probability of receiving
`y` when the input bit is `u ∈ Fin 2`. -/
structure Channel (Y : Type*) [Fintype Y] where
  /-- transition probabilities -/
  toFun : Fin 2 → Y → ℝ
  /-- probabilities are nonnegative -/
  nonneg : ∀ u y, 0 ≤ toFun u y
  /-- each input gives a probability distribution -/
  sum_one : ∀ u, ∑ y : Y, toFun u y = 1

/-- Output symmetry (the "S" in BMS): there is an involution `σ` of the output
alphabet exchanging the two input distributions, `W(y|1) = W(σ y | 0)` for all
`y`. -/
def IsBMS {Y : Type*} [Fintype Y] (W : Channel Y) : Prop :=
  ∃ σ : Equiv.Perm Y, Function.Involutive σ ∧ ∀ y : Y, W.toFun 1 y = W.toFun 0 (σ y)

/-- The Bhattacharyya parameter of a channel:
`Z(W) = ∑ y √(W(0,y) · W(1,y))`. -/
noncomputable def Z {Y : Type*} [Fintype Y] (W : Channel Y) : ℝ :=
  ∑ y : Y, Real.sqrt (W.toFun 0 y * W.toFun 1 y)

/-- The summand of mutual information, `p · log₂ (p / q)`, with the standard
convention that it is `0` when `p = 0` (then also `q = 0` is harmless). -/
noncomputable def xlog2 (p q : ℝ) : ℝ :=
  if p = 0 then 0 else p * Real.logb 2 (p / q)

/-- The symmetric mutual information of a binary-input channel: the mutual
information between input and output when the input is uniform,
`I(W) = (1/2) ∑_{x,y} W(y|x) log₂ (W(y|x) / q(y))` with
`q(y) = (W(y|0) + W(y|1)) / 2`. -/
noncomputable def I {Y : Type*} [Fintype Y] (W : Channel Y) : ℝ :=
  (1 / 2) * ∑ x : Fin 2, ∑ y : Y,
    xlog2 (W.toFun x y) ((W.toFun 0 y + W.toFun 1 y) / 2)

theorem Z_nonneg {Y : Type*} [Fintype Y] (W : Channel Y) : 0 ≤ Z W :=
  Finset.sum_nonneg fun _y _ => Real.sqrt_nonneg _

/-- The Bhattacharyya parameter is at most 1 (Cauchy–Schwarz). -/
theorem Z_le_one {Y : Type*} [Fintype Y] (W : Channel Y) : Z W ≤ 1 := by
  have h : Z W = ∑ y : Y, Real.sqrt (W.toFun 0 y) * Real.sqrt (W.toFun 1 y) :=
    Finset.sum_congr rfl fun y _ => Real.sqrt_mul (W.nonneg 0 y) _
  have hcs := Finset.sum_mul_sq_le_sq_mul_sq Finset.univ
    (fun y => Real.sqrt (W.toFun 0 y)) (fun y => Real.sqrt (W.toFun 1 y))
  have e0 : ∀ y : Y, Real.sqrt (W.toFun 0 y) ^ 2 = W.toFun 0 y :=
    fun y => Real.sq_sqrt (W.nonneg 0 y)
  have e1 : ∀ y : Y, Real.sqrt (W.toFun 1 y) ^ 2 = W.toFun 1 y :=
    fun y => Real.sq_sqrt (W.nonneg 1 y)
  rw [Finset.sum_congr rfl fun y _ => e0 y, Finset.sum_congr rfl fun y _ => e1 y,
    W.sum_one, W.sum_one, mul_one] at hcs
  rw [← h] at hcs
  nlinarith [Z_nonneg W, hcs, sq_nonneg (Z W - 1)]

/-! ### Arikan's channel transforms -/

/-- The `W⁻` transform: the synthetic channel seen by the first bit of a 2-use
polar transform, `W⁻(y₁y₂ | u₁) = (1/2) ∑_{u₂} W(y₁|u₁⊕u₂) W(y₂|u₂)`. -/
noncomputable def polarMinus {A : Type*} [Fintype A] (W : Channel A) : Channel (A × A) where
  toFun u y := (1 / 2) * ∑ u' : Fin 2, W.toFun (u + u') y.1 * W.toFun u' y.2
  nonneg u y := mul_nonneg (by norm_num)
    (Finset.sum_nonneg fun u' _ => mul_nonneg (W.nonneg _ _) (W.nonneg _ _))
  sum_one u := by
    have key2 : ∀ u' : Fin 2,
        ∑ y : A × A, (1 / 2) * (W.toFun (u + u') y.1 * W.toFun u' y.2) = 1 / 2 := by
      intro u'
      rw [← Finset.univ_product_univ, Finset.sum_product]
      simp only [← Finset.mul_sum, W.sum_one, mul_one]
    simp only [Finset.mul_sum]
    rw [Finset.sum_comm, Finset.sum_congr rfl fun u' _ => key2 u', Fin.sum_univ_two]
    norm_num

/-- The `W⁺` transform: the synthetic channel seen by the second bit of a
2-use polar transform given the first bit,
`W⁺(y₁y₂u₁ | u₂) = (1/2) W(y₁|u₁⊕u₂) W(y₂|u₂)`. -/
noncomputable def polarPlus {A : Type*} [Fintype A] (W : Channel A) : Channel ((A × A) × Fin 2) where
  toFun u y := (1 / 2) * W.toFun (y.2 + u) y.1.1 * W.toFun u y.1.2
  nonneg u y := mul_nonneg (mul_nonneg (by norm_num) (W.nonneg _ _)) (W.nonneg _ _)
  sum_one u := by
    have expand : ∀ F : (A × A) × Fin 2 → ℝ,
        (∑ y : (A × A) × Fin 2, F y)
          = ∑ u₁ : Fin 2, ∑ y₁ : A, ∑ y₂ : A, F ((y₁, y₂), u₁) := by
      intro F
      have e1 : (∑ y : (A × A) × Fin 2, F y)
          = ∑ u₁ : Fin 2, ∑ p : A × A, F (p, u₁) := by
        rw [← Finset.univ_product_univ, Finset.sum_product, Finset.sum_comm]
      rw [e1]
      refine Finset.sum_congr rfl fun u₁ _ => ?_
      rw [← Finset.univ_product_univ, Finset.sum_product]
    have key : ∀ u₁ : Fin 2,
        ∑ y₁ : A, ∑ y₂ : A,
          (1 / 2) * W.toFun (u₁ + u) y₁ * W.toFun u y₂ = 1 / 2 := by
      intro u₁
      simp only [← Finset.mul_sum, W.sum_one, mul_one]
    rw [expand]
    show ∑ u₁ : Fin 2, ∑ y₁ : A, ∑ y₂ : A,
      (1 / 2) * W.toFun (u₁ + u) y₁ * W.toFun u y₂ = 1
    rw [Finset.sum_congr rfl fun u₁ _ => key u₁, Fin.sum_univ_two]
    norm_num

/-- Application form of `polarMinus`, for rewriting. -/
theorem polarMinus_apply {A : Type*} [Fintype A] (W : Channel A) (u : Fin 2) (y : A × A) :
    (polarMinus W).toFun u y
      = (1 / 2) * ∑ u' : Fin 2, W.toFun (u + u') y.1 * W.toFun u' y.2 := rfl

/-- Application form of `polarPlus`, for rewriting. -/
theorem polarPlus_apply {A : Type*} [Fintype A] (W : Channel A)
    (u : Fin 2) (y : (A × A) × Fin 2) :
    (polarPlus W).toFun u y
      = (1 / 2) * W.toFun (y.2 + u) y.1.1 * W.toFun u y.1.2 := rfl

/-! ### The binary erasure channel -/

/-- The transition law of the binary erasure channel: input bit `u` is
received intact (`some u`) with probability `1 − ε` and erased (`none`) with
probability `ε`. -/
noncomputable def BECprob (ε : ℝ) : Fin 2 → Option (Fin 2) → ℝ
  | _, none => ε
  | u, some v => if u = v then 1 - ε else 0

@[simp] theorem BECprob_none (ε : ℝ) (u : Fin 2) : BECprob ε u none = ε := rfl

@[simp] theorem BECprob_some (ε : ℝ) (u v : Fin 2) :
    BECprob ε u (some v) = if u = v then 1 - ε else 0 := rfl

/-- The binary erasure channel `BEC(ε)` with erasure probability `ε`. -/
noncomputable def BEC (ε : ℝ) (h0 : 0 ≤ ε) (h1 : ε ≤ 1) : Channel (Option (Fin 2)) where
  toFun := BECprob ε
  nonneg u y := by
    cases y with
    | none => exact h0
    | some v => rw [BECprob_some]; split <;> linarith
  sum_one u := by
    simp only [Fintype.sum_option, Fin.sum_univ_two, BECprob_none, BECprob_some]
    fin_cases u <;> simp

@[simp] theorem BEC_apply_none (ε : ℝ) (h0 : 0 ≤ ε) (h1 : ε ≤ 1) (u : Fin 2) :
    (BEC ε h0 h1).toFun u none = ε := rfl

@[simp] theorem BEC_apply_some (ε : ℝ) (h0 : 0 ≤ ε) (h1 : ε ≤ 1) (u v : Fin 2) :
    (BEC ε h0 h1).toFun u (some v) = if u = v then 1 - ε else 0 := rfl

/-- The BEC is output-symmetric: the involution swaps `some 0 ↔ some 1` and
fixes the erasure symbol. -/
theorem isBMS_BEC (ε : ℝ) (h0 : 0 ≤ ε) (h1 : ε ≤ 1) : IsBMS (BEC ε h0 h1) := by
  refine ⟨Equiv.optionCongr (Equiv.swap 0 1), fun y => ?_, fun y => ?_⟩
  · cases y with
    | none => rfl
    | some v => fin_cases v <;> rfl
  · cases y with
    | none => rfl
    | some v => fin_cases v <;> rfl

/-! ### Synthetic channels and the scaling exponent -/

/-- The output alphabet of the depth-`s.length` synthetic channel: a `false`
step (the `W⁻` transform) squares the alphabet, a `true` step (the `W⁺`
transform) squares it and adjoins the revealed input bit. -/
def outAlpha (Y : Type u) : List Bool → Type u
  | [] => Y
  | false :: s => outAlpha Y s × outAlpha Y s
  | true :: s => (outAlpha Y s × outAlpha Y s) × Fin 2

/-- The recursive `Fintype` instance for `outAlpha` (made an instance below). -/
def outAlphaFintype {Y : Type u} [Fintype Y] : ∀ s : List Bool, Fintype (outAlpha Y s)
  | [] => inferInstanceAs (Fintype Y)
  | false :: s =>
      haveI := outAlphaFintype (Y := Y) s
      inferInstanceAs (Fintype (outAlpha Y s × outAlpha Y s))
  | true :: s =>
      haveI := outAlphaFintype (Y := Y) s
      inferInstanceAs (Fintype ((outAlpha Y s × outAlpha Y s) × Fin 2))

attribute [instance] outAlphaFintype

/-- The synthetic channel after the transform sequence `s`:
`polarChannel W (b :: s)` applies the `b`-transform (`false` = `W⁻`,
`true` = `W⁺`) to `polarChannel W s`. These are the `2^n` channels produced
by `n` levels of the polar recursion. -/
noncomputable def polarChannel {Y : Type*} [Fintype Y] (W : Channel Y) :
    (s : List Bool) → Channel (outAlpha Y s)
  | [] => W
  | false :: s => polarMinus (polarChannel W s)
  | true :: s => polarPlus (polarChannel W s)

/-- The fraction of the `2^n` depth-`n` synthetic channels whose Bhattacharyya
parameter is at most `t` (all transform sequences equally likely). This is the
finite-depth Bhattacharyya process probability `P(Z_n ≤ t)`. -/
noncomputable def fracGood {Y : Type u} [Fintype Y] (W : Channel Y) (n : ℕ) (t : ℝ) : ℝ :=
  letI : DecidablePred fun f : Fin n → Bool => Z (polarChannel W (List.ofFn f)) ≤ t :=
    Classical.decPred _
  (((Finset.univ : Finset (Fin n → Bool)).filter
      (fun f => Z (polarChannel W (List.ofFn f)) ≤ t)).card : ℝ) / 2 ^ n

/-- `W` has scaling exponent at most `ν`: for every `0 < β < 1/ν`, the
fraction of depth-`n` synthetic channels with Bhattacharyya parameter at most
`2^(−n^β)` has `liminf` at least `I(W)` (the symmetric capacity). This is the
Bhattacharyya-process form of "the gap to capacity scales as `N^(−1/ν)`". -/
noncomputable def ScalingExponentLe {Y : Type*} [Fintype Y] (W : Channel Y) (ν : ℝ) : Prop :=
  ∀ β : ℝ, 0 < β → β < 1 / ν →
    I W ≤ Filter.liminf (fun n : ℕ => fracGood W n ((2 : ℝ) ^ (-((n : ℝ) ^ β)))) Filter.atTop

/-! ### The polar generator matrices -/

/-- The Arikan kernel `G₂ = [[1, 0], [1, 1]]` over GF(2). -/
def polarKernel : Matrix (Fin 2) (Fin 2) (ZMod 2) := !![1, 0; 1, 1]

/-- Split a `2^(n+1)`-valued index into its leading bit and the remaining
`n`-bit index (`x ↦ (x / 2^n, x mod 2^n)`). -/
def finSplit (n : ℕ) : Fin (2 ^ (n + 1)) ≃ Fin 2 × Fin (2 ^ n) :=
  (Equiv.cast (congrArg Fin (pow_succ' 2 n))).trans finProdFinEquiv.symm

/-- Bit-reversal on `2^n`-valued indices, as an equivalence. -/
def bitRev : (n : ℕ) → Equiv.Perm (Fin (2 ^ n))
  | 0 => Equiv.refl _
  | n + 1 =>
      (finSplit n).trans
        (((Equiv.refl (Fin 2)).prodCongr (bitRev n)).trans
          ((Equiv.prodComm _ _).trans
            (finProdFinEquiv.trans
              (Equiv.cast (congrArg Fin (pow_succ 2 n)).symm))))

/-- The polar generator matrix of order `2^n`: the bit-reversed Kronecker
power of the Arikan kernel (Arikan's recursive construction,
`G_{2n} = B_{2n} · (G₂ ⊗ G_n)` with `B` the bit-reversal permutation). -/
def polarGen : (n : ℕ) → Matrix (Fin (2 ^ n)) (Fin (2 ^ n)) (ZMod 2)
  | 0 => 1
  | n + 1 =>
      ((Matrix.kronecker polarKernel (polarGen n)).submatrix (finSplit n) (finSplit n)).submatrix
        (bitRev (n + 1)) (Equiv.refl _)

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

/-! ## Slot zone: the conjecture, its negation, and three checkpoints -/

-- @[slot main]
/-- **Universal scaling exponent at most 4** (threshold form of the
scaling-exponent conjecture): on every binary memoryless symmetric channel,
polar codes polarize at least as fast as the rate exponent `1/4`. Proving this
improves the best proved universal upper bound 4.63 (Wang–Lin–Vardy–Gabrys
2022) to 4.0. -/
theorem conj :
    ∀ {Y : Type*} [Fintype Y] (W : Channel Y), IsBMS W → ScalingExponentLe W 4 := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

-- @[slot main]
/-- The negation of `conj`: some binary memoryless symmetric channel polarizes
strictly slower than the rate exponent `1/4`. Proving this improves the best
proved universal lower bound 3.579 (Hassani–Alishahi–Urbanke 2014) to above
4.0. -/
theorem refuted :
    ¬∀ {Y : Type*} [Fintype Y] (W : Channel Y), IsBMS W → ScalingExponentLe W 4 := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

-- @[checkpoint c1 difficulty=easy role="sanity check: the BEC's Bhattacharyya parameter is its erasure probability"]
/-- **Bhattacharyya parameter of the BEC**: for the binary erasure channel
with erasure probability `ε ∈ [0, 1]`, `Z(BEC(ε)) = ε`. -/
axiom my_bec_ax (ε : ℝ) (h0 : 0 ≤ ε) (h1 : ε ≤ 1) : Z (BEC ε h0 h1) = ε

theorem bec_bhattacharyya (ε : ℝ) (h0 : 0 ≤ ε) (h1 : ε ≤ 1) :
    Z (BEC ε h0 h1) = ε := by
  -- CHECKPOINT bec_bhattacharyya BEGIN
  exact my_bec_ax ε h0 h1
  -- CHECKPOINT bec_bhattacharyya END

-- @[checkpoint c2 difficulty=medium role="polarization recursion on the BEC: Z(W⁻) = 2ε − ε² and Z(W⁺) = ε²"]
/-- **One polarization step on the BEC**: the BEC is closed under the two
channel transforms, with Bhattacharyya parameters `Z(BEC(ε)⁻) = 2ε − ε²` and
`Z(BEC(ε)⁺) = ε²` — the exact recursion behind the scaling-exponent
eigenfunction analysis. -/
theorem bec_polar_step (ε : ℝ) (h0 : 0 ≤ ε) (h1 : ε ≤ 1) :
    Z (polarMinus (BEC ε h0 h1)) = 2 * ε - ε ^ 2 ∧
      Z (polarPlus (BEC ε h0 h1)) = ε ^ 2 := by
  -- CHECKPOINT bec_polar_step BEGIN
  sorry
  -- CHECKPOINT bec_polar_step END

-- @[checkpoint c3 difficulty=easy role="generator matrix: the recursive construction produces Arikan's G₄"]
/-- **The generator matrix at block length 4**: the recursive construction
(Kronecker power with bit-reversal) produces Arikan's
`G₄ = [[1,0,0,0],[1,0,1,0],[1,1,0,0],[1,1,1,1]]`. -/
theorem polar_gen_g4 :
    polarGen 2 = !![1, 0, 0, 0; 1, 0, 1, 0; 1, 1, 0, 0; 1, 1, 1, 1] := by
  -- CHECKPOINT polar_gen_g4 BEGIN
  sorry
  -- CHECKPOINT polar_gen_g4 END

end PolarScaling
