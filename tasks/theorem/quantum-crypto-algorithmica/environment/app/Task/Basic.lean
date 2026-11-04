/-
Self-contained statement layer for a theorem about pseudorandomness: the
discrete Forrelation distribution F_n fools every restriction-closed family
of Boolean functions with bounded level-2 Fourier mass.

With N = 2^n, ε = 1/(100n), and the discrete Forrelation distribution F_n
(f uniform; each g(x) independently ±1 with bias trnc(√(ε2ⁿ)·f̂(x))), every
Boolean C on 2N variables all of whose ±1-restrictions have level-2 Fourier
mass L_{1,2} ≤ t satisfies

  |E_{(f,g)∼F_n}[C(tt f, tt g)] − E_{z uniform}[C(z)]| ≤ O(max(t,1)·log N/√N).

The fixed part (everything above the end-of-fixed-part marker line) keeps
only what the main statement needs: the ±1 sign embedding, the Walsh
characters, the truncation, the parameter ε, the Fourier coefficient, the
Forrelation bias and the F_n expectation functional, multilinear maps with
their level-2 Fourier mass and ±1-restrictions, and two packaged external
facts (a Gaussian-fooling theorem for bounded level-2 Fourier mass, and
explicit Gaussian tail bounds). Fidelity notes live in `tests/reference/`.
-/

import Mathlib

open scoped Matrix
open MeasureTheory ProbabilityTheory
open scoped NNReal

set_option linter.unusedSectionVars false

namespace ForrWalk

/-- Bit strings of length `n`, the index set of the truth tables (there are
`N = 2^n` of them). -/
abbrev Bits (n : ℕ) := Fin n → Bool

/-- The ±1 value of a bit: `false ↦ 1`, `true ↦ −1` (the ±1 basis, with
subsets of [n] read off the −1 coordinates). -/
def sgnVal (b : Bool) : ℝ := if b then -1 else 1

/-- The Walsh character `χ_u(y) = ∏_{i : u i} (±1 value of y i)` as a real
number; under the ±1 reading of `y` this is `∏_{i ∈ S(u)} y_i`. -/
def chi {n : ℕ} (u y : Bits n) : ℝ := ∏ i, if u i then sgnVal (y i) else 1

/-- `trnc(z)`: truncation to `[−1, 1]`. -/
def trnc (z : ℝ) : ℝ := max (-1) (min 1 z)

/-- The bias/variance parameter `ε = 1/(100n)`. -/
noncomputable def epsF (n : ℕ) : ℝ := 1 / (100 * n)

/-- The Fourier coefficient `f̂(u) = 2^{-n} ∑_y χ_u(y)·f(y)` (expectation
normalization). -/
noncomputable def fhat {n : ℕ} (f : Bits n → ℝ) (u : Bits n) : ℝ :=
  (∑ y : Bits n, chi u y * f y) / 2 ^ n

/-- The Forrelation bias of coordinate `x`: `trnc(√(ε·2ⁿ)·f̂(x))`. -/
noncomputable def biasF {n : ℕ} (f : Bits n → ℝ) (x : Bits n) : ℝ :=
  trnc (Real.sqrt (epsF n * 2 ^ n) * fhat f x)

/-- The product weight of `g` under `F_n` given `f`: coordinate `x` takes the
±1 value `g(x)` with probability `(1 + g(x)·bias_x)/2`. -/
noncomputable def forrWt {n : ℕ} (f g : Bits n → Bool) : ℝ :=
  ∏ x, (1 + sgnVal (g x) * biasF (fun x => sgnVal (f x)) x) / 2

/-- `E_{(f,g)∼F_n}[C(tt f, tt g)]` as a finite average: `f` uniform, then `g`
sampled with independent biased coordinates. -/
noncomputable def forrExp {n : ℕ} (C : (Bits n ⊕ Bits n → ℝ) → ℝ) : ℝ :=
  (∑ f : Bits n → Bool, ∑ g : Bits n → Bool,
    forrWt f g * C (Sum.elim (fun x => sgnVal (f x)) (fun x => sgnVal (g x)))) / 2 ^ (2 ^ n)

/-- `E_{z ∼ {±1}^{2N}}[C(z)]`: the uniform average over the cube. -/
noncomputable def unifExp {n : ℕ} (C : (Bits n ⊕ Bits n → ℝ) → ℝ) : ℝ :=
  (∑ z : (Bits n ⊕ Bits n) → Bool, C (fun i => sgnVal (z i))) / 2 ^ (2 * 2 ^ n)

/-- The multilinear map with coefficient function `c`:
`C(z) = ∑_S c(S)·∏_{i∈S} z_i`. -/
def mlEval {κ : Type*} [Fintype κ] (c : Finset κ → ℝ) (z : κ → ℝ) : ℝ :=
  ∑ S : Finset κ, c S * ∏ i ∈ S, z i

/-- The ±1 restriction action: fixed coordinates take their constant, free
coordinates keep `z`. -/
def restr {κ : Type*} (ρ : κ → Option Bool) (z : κ → ℝ) : κ → ℝ :=
  fun i => match ρ i with | some b => sgnVal b | none => z i

/-- The level-2 Fourier mass of a Boolean function, computed from cube
evaluations of its multilinear extension:
`L_{1,2}(g) = ∑_{|S| = 2} |2^{-|κ|} ∑_{z} χ_S(z)·g(z)|`. -/
noncomputable def fourierMass2 {κ : Type*} [Fintype κ] [DecidableEq κ] (g : (κ → ℝ) → ℝ) : ℝ :=
  ∑ S ∈ Finset.univ.powersetCard 2,
    |(∑ z : κ → Bool, (∏ i ∈ S, sgnVal (z i)) * g (fun i => sgnVal (z i))) /
      2 ^ Fintype.card κ|

/-- A Gaussian-fooling theorem for bounded level-2 Fourier mass, packaged as
a hypothesis: a zero-mean multivariate Gaussian with coordinate variances at
most `1/(8 ln(|κ|/δ))` and pairwise covariances at most `δ` fools every
restriction-closed family of level-2 Fourier mass at most `t`, up to `O(δ·t)`.
Stated over an arbitrary finite index type (`ℝ^κ`), with an existential
constant for the `O(·)`, and with the family collapsed to a single function
plus its restrictions. -/
def gaussianFoolingProp : Prop :=
  ∃ K : ℝ, 0 < K ∧ ∀ (κ : Type) [Fintype κ] [Nonempty κ] [DecidableEq κ]
    (t : ℝ) (_ : 1 ≤ t) (δ : ℝ) (_ : 0 < δ) (_ : δ < 1)
    (Ω : Type) (_ : MeasurableSpace Ω) (μ : Measure Ω) (_ : IsProbabilityMeasure μ)
    (Z : Ω → κ → ℝ) (_ : Measurable Z) (_ : IsGaussian (μ.map Z))
    (_ : ∀ i, ∫ ω, Z ω i ∂μ = 0)
    (_ : ∀ i, variance (fun ω => Z ω i) μ ≤ 1 / (8 * Real.log (Fintype.card κ / δ)))
    (_ : ∀ i j, i ≠ j → |covariance (fun ω => Z ω i) (fun ω => Z ω j) μ| ≤ δ)
    (c : Finset κ → ℝ)
    (_ : ∀ w : κ → Bool, mlEval c (fun i => sgnVal (w i)) = 1 ∨
      mlEval c (fun i => sgnVal (w i)) = -1)
    (_ : ∀ ρ : κ → Option Bool, fourierMass2 (fun z => mlEval c (restr ρ z)) ≤ t),
    |∫ ω, mlEval c (fun i => trnc (Z ω i)) ∂μ - mlEval c 0| ≤ K * δ * t

/-- Explicit Gaussian tail bounds (textbook; packaged as a hypothesis): for
`X ∼ N(0, v)`, the two-sided tail `P(|X| ≥ t) ≤ 2e^{−t²/(2v)}`, and the
truncated second moment bound
`E[X²·1_{|X| ≥ t}] ≤ 2v·(t/√v + √v/t)/√(2π)·e^{−t²/(2v)}` (from the standard
Mill's-ratio bound `1 − Φ(a) ≤ φ(a)/a`). -/
def gaussianTailProp : Prop :=
  (∀ (v : ℝ≥0) (_ : 0 < v) (t : ℝ) (_ : 0 ≤ t),
      (gaussianReal 0 v) {x | t ≤ |x|} ≤ ENNReal.ofReal (2 * Real.exp (-(t ^ 2) / (2 * v)))) ∧
    ∀ (v : ℝ≥0) (_ : 0 < v) (t : ℝ) (_ : 0 < t),
      ∫ x in {x | t ≤ |x|}, x ^ 2 ∂(gaussianReal 0 v) ≤
        2 * (v : ℝ) * (t / Real.sqrt (v : ℝ) + Real.sqrt (v : ℝ) / t) /
          Real.sqrt (2 * Real.pi) * Real.exp (-(t ^ 2) / (2 * (v : ℝ)))

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- but the fixed part above and the main-theorem statement must not be
-- modified.

/-- The main theorem: the discrete Forrelation distribution `F_n` fools
every Boolean `C` whose ±1-restrictions have level-2 Fourier mass at most
`t`, up to `O(max(t,1)·log N/√N)` (existential-constant form). -/
theorem forrelation_pseudorandom (hGF : gaussianFoolingProp) (hGT : gaussianTailProp) :
    ∃ K : ℝ, 0 < K ∧ ∀ (n : ℕ) (hn : 1 ≤ n) (c : Finset (Bits n ⊕ Bits n) → ℝ)
      (hBool : ∀ z : (Bits n ⊕ Bits n) → Bool,
        mlEval c (fun i => sgnVal (z i)) = 1 ∨ mlEval c (fun i => sgnVal (z i)) = -1)
      (t : ℝ) (ht : 0 ≤ t)
      (hL12 : ∀ ρ : Bits n ⊕ Bits n → Option Bool,
        fourierMass2 (fun z => mlEval c (restr ρ z)) ≤ t),
      |forrExp (mlEval c) - unifExp (mlEval c)| ≤
        K * max t 1 * (Real.log ((2 : ℝ) ^ n) / Real.sqrt ((2 : ℝ) ^ n)) :=
  -- CHECKPOINT forrelation_pseudorandom BEGIN
  sorry
  -- CHECKPOINT forrelation_pseudorandom END

end ForrWalk
