/-
Self-contained statement layer for a theorem in quantum complexity: a
classical oracle separation between QMA and QCMA (quantum versus classical
witnesses).

The fixed part (everything above the end-of-fixed-part marker line) is the
definition layer the main theorem's statement needs: the spectral
Forrelation value of a pair of oracles and its Rayleigh-quotient matrix,
the quantum query algorithm model with classical or quantum witnesses, the
iterated/cumulative sampler success probabilities, the Strong distribution
with its good lists and Taylor matrix sandwiches, and three external facts
assumed by the main theorem. A separate trace-distance proposition is
defined without being assumed. Fidelity notes live in `tests/reference/`.
-/

import Mathlib

open scoped Matrix
open ComplexOrder

namespace QmaQcmaOracle

/-! ## Bits and signs -/

/-- `n`-bit strings. -/
abbrev Bits (n : ℕ) := Fin n → Bool

/-- The zero string. -/
def zeroBits (n : ℕ) : Bits n := fun _ => false

/-- View a bit string as a `ZMod 2` vector (xor becomes addition). -/
def toZ2 {n : ℕ} (x : Bits n) : Fin n → ZMod 2 := fun i => if x i then 1 else 0

theorem toZ2_injective {n : ℕ} : Function.Injective (@toZ2 n) := by
  intro x y h
  funext i
  have hi := congrFun h i
  unfold toZ2 at hi
  cases hx : x i <;> cases hy : y i <;> simp only [hx, hy, if_false, if_true] at hi
  · rfl
  · exact absurd hi (by decide)
  · exact absurd hi (by decide)
  · rfl

theorem toZ2_add {n : ℕ} (x y : Bits n) (i : Fin n) :
    toZ2 x i + toZ2 y i = toZ2 (fun j => Bool.xor (x j) (y j)) i := by
  cases hxi : x i <;> cases hyi : y i <;> simp [toZ2, hxi, hyi] <;> decide

/-- The mod-2 inner product of two bit strings. -/
def dotZ2 {n : ℕ} (x y : Bits n) : ZMod 2 := ∑ i, toZ2 x i * toZ2 y i

theorem dotZ2_comm {n : ℕ} (x y : Bits n) : dotZ2 x y = dotZ2 y x := by
  unfold dotZ2
  apply Finset.sum_congr rfl
  intro i _
  rw [mul_comm]

theorem dotZ2_add {n : ℕ} (x y z : Bits n) :
    dotZ2 (fun i => Bool.xor (x i) (y i)) z = dotZ2 x z + dotZ2 y z := by
  unfold dotZ2
  rw [← Finset.sum_add_distrib]
  apply Finset.sum_congr rfl
  intro i _
  rw [← toZ2_add, add_mul]

/-- The ±1 sign of a `ZMod 2` value, as a real number: 0 ↦ 1, 1 ↦ −1. -/
def signR : ZMod 2 → ℝ := fun a => if a = 0 then 1 else -1

/-- The ±1 sign of a `ZMod 2` value, as a complex number. -/
def signC : ZMod 2 → ℂ := fun a => if a = 0 then 1 else -1

theorem zmod2_eq_zero_or_one (a : ZMod 2) : a = 0 ∨ a = 1 := by decide +revert

theorem signR_add (a b : ZMod 2) : signR (a + b) = signR a * signR b := by
  rcases zmod2_eq_zero_or_one a with ha | ha <;> rcases zmod2_eq_zero_or_one b with hb | hb <;>
    subst ha <;> subst hb <;> simp [signR] <;> decide

theorem signC_add (a b : ZMod 2) : signC (a + b) = signC a * signC b := by
  rcases zmod2_eq_zero_or_one a with ha | ha <;> rcases zmod2_eq_zero_or_one b with hb | hb <;>
    subst ha <;> subst hb <;> simp [signC] <;> decide

theorem signC_ofReal (a : ZMod 2) : signC a = (signR a : ℂ) := by
  rcases zmod2_eq_zero_or_one a with ha | ha <;> subst ha <;> simp [signC, signR]

theorem signR_sq (a : ZMod 2) : signR a ^ 2 = 1 := by
  rcases zmod2_eq_zero_or_one a with ha | ha <;> subst ha <;> simp [signR] <;> decide

/-- The character `(−1)^{x·z}` as a complex number. -/
noncomputable def bitsSignC {n : ℕ} (x z : Bits n) : ℂ := signC (dotZ2 x z)

/-- The character `(−1)^{x·z}` as a real number. -/
noncomputable def bitsSignR {n : ℕ} (x z : Bits n) : ℝ := signR (dotZ2 x z)

theorem bitsSignC_ofReal {n : ℕ} (x z : Bits n) :
    bitsSignC x z = (bitsSignR x z : ℂ) := signC_ofReal _

/-- Orthogonality of the hypercube characters: `∑_z (−1)^{x·z} = 0` for `x ≠ 0`. -/
theorem sum_bitsSignC_eq_zero {n : ℕ} {x : Bits n} (hx : x ≠ zeroBits n) :
    ∑ z : Bits n, bitsSignC x z = 0 := by
  obtain ⟨i, hi⟩ : ∃ i, x i ≠ false := by
    by_contra h
    push_neg at h
    exact hx (funext h)
  have hxi : x i = true := Bool.eq_true_of_not_eq_false hi
  -- pair up z with z flipped at i
  let flip : Bits n → Bits n := fun z => fun j => if j = i then !(z j) else z j
  have hsign : ∀ z, bitsSignC x (flip z) = -bitsSignC x z := by
    intro z
    unfold bitsSignC
    have hdot : dotZ2 x (flip z) = dotZ2 x z + 1 := by
      unfold dotZ2
      rw [← Finset.add_sum_erase _ _ (Finset.mem_univ i),
        ← Finset.add_sum_erase _ _ (Finset.mem_univ i)]
      have hrest : ∀ j ∈ Finset.univ.erase i,
          toZ2 x j * toZ2 (flip z) j = toZ2 x j * toZ2 z j := by
        intro j hj
        have hj2 : j ≠ i := by
          simp only [Finset.mem_erase, ne_eq] at hj
          exact hj.1
        have hthis : toZ2 (flip z) j = toZ2 z j := by
          have hjj : flip z j = z j := by
            show (if j = i then !(z j) else z j) = z j
            rw [if_neg hj2]
          simp only [toZ2, hjj]
        rw [hthis]
      rw [Finset.sum_congr rfl hrest]
      have hi_at : toZ2 x i = 1 := by simp [toZ2, hxi]
      have hflip : toZ2 (flip z) i = toZ2 z i + 1 := by
        simp only [flip, ite_true]
        unfold toZ2
        cases hzi : z i <;> simp [hzi]
        · decide
      rw [hi_at, hflip]
      rcases zmod2_eq_zero_or_one (toZ2 z i) with hzi | hzi <;> simp only [hzi] <;> ring
    rw [hdot, signC_add]
    simp [signC]
  have hfix : ∀ z, flip z ≠ z := by
    intro z hz
    have hcon := congrFun hz i
    simp only [flip, ite_true] at hcon
    exact Bool.not_ne_self (z i) hcon
  have hinv : Function.Involutive flip := by
    intro z
    funext j
    simp only [flip]
    by_cases hj : j = i <;> simp [hj]
  apply Finset.sum_involution (fun z _ => flip z)
  · intro z _
    rw [hsign z]
    simp
  · intro z _ _
    exact hfix z
  · intro z _
    exact Finset.mem_univ _
  · intro z _
    exact hinv z

theorem sum_bitsSignC {n : ℕ} (x : Bits n) :
    ∑ z : Bits n, bitsSignC x z = if x = zeroBits n then (2 : ℂ) ^ n else 0 := by
  by_cases hx : x = zeroBits n
  · subst hx
    simp only [ite_true]
    have hone : ∀ z : Bits n, bitsSignC (zeroBits n) z = 1 := by
      intro z
      unfold bitsSignC dotZ2 zeroBits toZ2
      simp [signC]
    have hcard : Fintype.card (Bits n) = 2 ^ n := by
      rw [Fintype.card_fun, Fintype.card_bool, Fintype.card_fin]
    rw [Finset.sum_congr rfl (fun z _ => hone z), Finset.sum_const, Finset.card_univ, hcard,
      nsmul_eq_mul, mul_one]
    push_cast
    rfl
  · rw [if_neg hx]
    exact sum_bitsSignC_eq_zero hx

theorem sum_bitsSignR {n : ℕ} (x : Bits n) :
    ∑ z : Bits n, bitsSignR x z = if x = zeroBits n then (2 : ℝ) ^ n else 0 := by
  apply Complex.ofReal_injective
  rw [Complex.ofReal_sum]
  simp_rw [← bitsSignC_ofReal]
  rw [sum_bitsSignC]
  split_ifs <;> simp

/-! ## State vectors, norms and inner products -/

/-- Squared ℓ² norm of a coefficient vector. -/
noncomputable def normSq {ι : Type*} [Fintype ι] (ψ : ι → ℂ) : ℝ :=
  ∑ x, Complex.normSq (ψ x)

/-- The inner product `⟨ψ, φ⟩ = ∑_x conj (ψ x) * φ x`. -/
noncomputable def inner {ι : Type*} [Fintype ι] (ψ φ : ι → ℂ) : ℂ :=
  ∑ x, star (ψ x) * φ x

/-- A unit vector. -/
def IsUnitVec {ι : Type*} [Fintype ι] (ψ : ι → ℂ) : Prop := normSq ψ = 1

theorem normSq_nonneg {ι : Type*} [Fintype ι] (ψ : ι → ℂ) : 0 ≤ normSq ψ :=
  Finset.sum_nonneg (fun x _ => Complex.normSq_nonneg _)

theorem inner_self_eq_normSq {ι : Type*} [Fintype ι] (ψ : ι → ℂ) :
    (inner ψ ψ).re = normSq ψ := by
  unfold inner normSq
  rw [Complex.re_sum]
  apply Finset.sum_congr rfl
  intro x _
  rw [RCLike.star_def, Complex.conj_mul', ← Complex.ofReal_pow, Complex.ofReal_re,
    Complex.normSq_eq_norm_sq]

theorem inner_conj_symm {ι : Type*} [Fintype ι] (ψ φ : ι → ℂ) :
    inner φ ψ = star (inner ψ φ) := by
  unfold inner
  rw [star_sum]
  apply Finset.sum_congr rfl
  intro x _
  rw [star_mul', star_star]
  ring

/-- The basis vector at `i`. -/
noncomputable def basisVec {ι : Type*} [Fintype ι] [DecidableEq ι] (i : ι) : ι → ℂ :=
  fun j => if j = i then 1 else 0

theorem normSq_basisVec {ι : Type*} [Fintype ι] [DecidableEq ι] (i : ι) :
    normSq (basisVec i) = 1 := by
  unfold normSq basisVec
  rw [Finset.sum_eq_single i]
  · simp
  · intro j _ hji; simp [hji]
  · intro h; exact absurd (Finset.mem_univ i) h

theorem isUnitVec_basisVec {ι : Type*} [Fintype ι] [DecidableEq ι] (i : ι) :
    IsUnitVec (basisVec i) := normSq_basisVec i

/-- Cauchy–Schwarz for the finite-sum inner product. -/
theorem normSq_inner_le {ι : Type*} [Fintype ι] (ψ φ : ι → ℂ) :
    Complex.normSq (inner ψ φ) ≤ normSq ψ * normSq φ := by
  rw [Complex.normSq_eq_norm_sq]
  calc ‖inner ψ φ‖ ^ 2
      ≤ (∑ x, ‖ψ x‖ * ‖φ x‖) ^ 2 := by
        apply pow_le_pow_left₀ (norm_nonneg _)
        calc ‖inner ψ φ‖ ≤ ∑ x, ‖star (ψ x) * φ x‖ := norm_sum_le _ _
          _ = ∑ x, ‖ψ x‖ * ‖φ x‖ := by
              apply Finset.sum_congr rfl
              intro x _
              rw [norm_mul, norm_star]
    _ ≤ (∑ x, ‖ψ x‖ ^ 2) * (∑ x, ‖φ x‖ ^ 2) :=
        Finset.sum_mul_sq_le_sq_mul_sq _ _ _
    _ = normSq ψ * normSq φ := by
        unfold normSq
        congr 1 <;> apply Finset.sum_congr rfl <;> intro x _ <;> rw [Complex.normSq_eq_norm_sq]

/-! ## Operators -/

/-- Conjugating with a matrix moves it to the other side of the inner product:
`⟨Aψ, φ⟩ = ⟨ψ, Aᴴ φ⟩`. -/
theorem inner_mulVec {ι : Type*} [Fintype ι] (A : Matrix ι ι ℂ) (ψ φ : ι → ℂ) :
    inner (A *ᵥ ψ) φ = inner ψ (Aᴴ *ᵥ φ) := by
  unfold inner
  simp_rw [Matrix.mulVec_apply_eq_sum, Finset.mul_sum, star_sum]
  rw [Finset.sum_comm]
  apply Finset.sum_congr rfl
  intro y _
  rw [Finset.sum_mul]
  apply Finset.sum_congr rfl
  intro x _
  rw [Matrix.conjTranspose_apply, star_mul']
  ring

/-- Moving a matrix to the left side of the inner product. -/
theorem inner_mulVec_right {ι : Type*} [Fintype ι] (A : Matrix ι ι ℂ) (ψ φ : ι → ℂ) :
    inner ψ (A *ᵥ φ) = inner (Aᴴ *ᵥ ψ) φ := by
  conv_lhs => rw [← Matrix.conjTranspose_conjTranspose A]
  exact (inner_mulVec (Aᴴ) ψ φ).symm

theorem normSq_mulVec_eq_inner {ι : Type*} [Fintype ι] (A : Matrix ι ι ℂ) (ψ : ι → ℂ) :
    normSq (A *ᵥ ψ) = (inner ψ ((Aᴴ * A) *ᵥ ψ)).re := by
  rw [← inner_self_eq_normSq, inner_mulVec, Matrix.mulVec_mulVec]

/-- A matrix is unitary (one-sided condition, which suffices in finite dimension). -/
def IsUnitaryMat {ι : Type*} [Fintype ι] [DecidableEq ι] (A : Matrix ι ι ℂ) : Prop :=
  Aᴴ * A = 1

theorem IsUnitaryMat.conjTranspose_mul {ι : Type*} [Fintype ι] [DecidableEq ι] {A : Matrix ι ι ℂ}
    (hA : IsUnitaryMat A) : A * Aᴴ = 1 := mul_eq_one_comm.mp hA

theorem isUnitaryMat_one {ι : Type*} [Fintype ι] [DecidableEq ι] :
    IsUnitaryMat (1 : Matrix ι ι ℂ) := by
  simp [IsUnitaryMat]

theorem isUnitaryMat_mul {ι : Type*} [Fintype ι] [DecidableEq ι] {A B : Matrix ι ι ℂ}
    (hA : IsUnitaryMat A) (hB : IsUnitaryMat B) : IsUnitaryMat (A * B) := by
  unfold IsUnitaryMat at *
  rw [Matrix.conjTranspose_mul, Matrix.mul_assoc, ← Matrix.mul_assoc Aᴴ, hA, Matrix.one_mul, hB]

theorem normSq_mulVec_of_unitary {ι : Type*} [Fintype ι] [DecidableEq ι] {A : Matrix ι ι ℂ}
    (hA : IsUnitaryMat A) (ψ : ι → ℂ) : normSq (A *ᵥ ψ) = normSq ψ := by
  rw [normSq_mulVec_eq_inner, hA, Matrix.one_mulVec, inner_self_eq_normSq]

/-- Squared operator norm: `sup_{‖ψ‖=1} ‖Aψ‖²`. -/
noncomputable def opNormSq {ι : Type*} [Fintype ι] (A : Matrix ι ι ℂ) : ℝ :=
  sSup {r : ℝ | ∃ ψ : ι → ℂ, IsUnitVec ψ ∧ r = normSq (A *ᵥ ψ)}

theorem opNormSq_bddAbove {ι : Type*} [Fintype ι] (A : Matrix ι ι ℂ) :
    BddAbove {r : ℝ | ∃ ψ : ι → ℂ, IsUnitVec ψ ∧ r = normSq (A *ᵥ ψ)} := by
  refine ⟨∑ x, ∑ y, Complex.normSq (A x y), ?_⟩
  rintro r ⟨ψ, hψ, rfl⟩
  unfold normSq
  apply Finset.sum_le_sum
  intro x _
  rw [Matrix.mulVec_apply_eq_sum]
  calc Complex.normSq (∑ y, A x y * ψ y)
      ≤ (∑ y, ‖A x y‖ * ‖ψ y‖) ^ 2 := by
        rw [Complex.normSq_eq_norm_sq]
        apply pow_le_pow_left₀ (norm_nonneg _)
        calc ‖∑ y, A x y * ψ y‖ ≤ ∑ y, ‖A x y * ψ y‖ := norm_sum_le _ _
          _ = ∑ y, ‖A x y‖ * ‖ψ y‖ := by
              apply Finset.sum_congr rfl
              intro y _
              rw [norm_mul]
    _ ≤ (∑ y, ‖A x y‖ ^ 2) * (∑ y, ‖ψ y‖ ^ 2) :=
        Finset.sum_mul_sq_le_sq_mul_sq _ _ _
    _ = (∑ y, Complex.normSq (A x y)) * normSq ψ := by
        unfold normSq
        congr 1 <;> apply Finset.sum_congr rfl <;> intro y _ <;> rw [Complex.normSq_eq_norm_sq]
    _ = ∑ y, Complex.normSq (A x y) := by rw [hψ, mul_one]

theorem normSq_mulVec_le_opNormSq {ι : Type*} [Fintype ι] [Nonempty ι] (A : Matrix ι ι ℂ)
    {ψ : ι → ℂ} (hψ : IsUnitVec ψ) : normSq (A *ᵥ ψ) ≤ opNormSq A :=
  le_csSup (opNormSq_bddAbove A) ⟨ψ, hψ, rfl⟩

theorem opNormSq_nonneg {ι : Type*} [Fintype ι] [Nonempty ι] [DecidableEq ι] (A : Matrix ι ι ℂ) :
    0 ≤ opNormSq A := by
  obtain ⟨i⟩ := ‹Nonempty ι›
  exact le_trans (normSq_nonneg _) (normSq_mulVec_le_opNormSq A (isUnitVec_basisVec i))

/-! ## The Hadamard transform and projectors -/

/-- The `n`-qubit Hadamard transform in the computational basis. -/
noncomputable def hadMat (n : ℕ) : Matrix (Bits n) (Bits n) ℂ :=
  fun x y => ((Real.sqrt (2 ^ n))⁻¹ : ℝ) • bitsSignC x y

theorem xor_eq_zeroBits_iff {n : ℕ} (x y : Bits n) :
    (fun i => Bool.xor (x i) (y i)) = zeroBits n ↔ x = y := by
  constructor
  · intro h
    funext i
    have hi := congrFun h i
    simp only [zeroBits] at hi
    cases hx : x i <;> cases hy : y i <;> simp [hx, hy] at hi ⊢
  · intro h
    subst h
    funext i
    simp [zeroBits]

theorem bitsSignC_comm {n : ℕ} (x y : Bits n) : bitsSignC x y = bitsSignC y x := by
  unfold bitsSignC
  rw [dotZ2_comm]

theorem star_bitsSignC {n : ℕ} (x z : Bits n) : star (bitsSignC x z) = bitsSignC x z := by
  unfold bitsSignC
  rcases zmod2_eq_zero_or_one (dotZ2 x z) with h | h <;> rw [h] <;>
    simp [signC, RCLike.star_def]

theorem hadMat_conjTranspose {n : ℕ} : (hadMat n)ᴴ = hadMat n := by
  ext x y
  simp only [Matrix.conjTranspose_apply, hadMat, Complex.real_smul]
  rw [bitsSignC_comm y x, star_mul', star_bitsSignC, RCLike.star_def, Complex.conj_ofReal]

theorem hadMat_scale {n : ℕ} :
    (((Real.sqrt (2 ^ n))⁻¹ : ℝ) : ℂ) * (((Real.sqrt (2 ^ n))⁻¹ : ℝ) : ℂ) = ((2 : ℂ) ^ n)⁻¹ := by
  rw [← Complex.ofReal_mul, ← mul_inv_rev, Real.mul_self_sqrt (by positivity),
    Complex.ofReal_inv, Complex.ofReal_pow]
  norm_num

theorem hadMat_mul_self {n : ℕ} : hadMat n * hadMat n = 1 := by
  ext x y
  rw [Matrix.mul_apply, Matrix.one_apply]
  have hterm : ∀ z : Bits n, hadMat n x z * hadMat n z y =
      ((2 : ℂ) ^ n)⁻¹ * bitsSignC (fun i => Bool.xor (x i) (y i)) z := by
    intro z
    simp only [hadMat, Complex.real_smul]
    rw [show (↑(√(2 ^ n))⁻¹ * bitsSignC x z * (↑(√(2 ^ n))⁻¹ * bitsSignC z y)) =
        (↑(√(2 ^ n))⁻¹ * ↑(√(2 ^ n))⁻¹) * (bitsSignC x z * bitsSignC z y) from by ring]
    rw [hadMat_scale]
    congr 1
    unfold bitsSignC
    rw [← signC_add, dotZ2_comm z y, ← dotZ2_add]
  rw [Finset.sum_congr rfl (fun z _ => hterm z), ← Finset.mul_sum, sum_bitsSignC]
  by_cases hxy : x = y
  · subst hxy
    have hxor : (fun i => Bool.xor (x i) (x i)) = zeroBits n := by
      funext i
      simp [zeroBits]
    rw [hxor, if_pos rfl, if_pos rfl]
    rw [inv_mul_cancel₀ (pow_ne_zero n (by norm_num))]
  · have hxor : ¬(fun i => Bool.xor (x i) (y i)) = zeroBits n := by
      rw [xor_eq_zeroBits_iff]
      exact hxy
    simp [hxor, hxy]

theorem hadMat_unitary {n : ℕ} : IsUnitaryMat (hadMat n) := by
  unfold IsUnitaryMat
  rw [hadMat_conjTranspose]
  exact hadMat_mul_self

/-- The projector onto the basis states in the support of `f`. -/
noncomputable def projOracle {n : ℕ} (f : Bits n → Bool) : Matrix (Bits n) (Bits n) ℂ :=
  Matrix.diagonal fun x => if f x then 1 else 0

theorem projOracle_conjTranspose {n : ℕ} (f : Bits n → Bool) :
    (projOracle f)ᴴ = projOracle f := by
  ext x y
  simp [projOracle, Matrix.conjTranspose_apply, Matrix.diagonal]
  split_ifs with h1 h2 h3 <;> simp_all

theorem projOracle_mul_self {n : ℕ} (f : Bits n → Bool) :
    projOracle f * projOracle f = projOracle f := by
  unfold projOracle
  rw [Matrix.diagonal_mul_diagonal]
  congr 1
  funext x
  split_ifs with h
  · simp [h]
  · simp

theorem projOracle_mulVec_apply {n : ℕ} (f : Bits n → Bool) (ψ : Bits n → ℂ) (x : Bits n) :
    (projOracle f *ᵥ ψ) x = if f x then ψ x else 0 := by
  rw [Matrix.mulVec_apply_eq_sum]
  rw [Finset.sum_eq_single x]
  · unfold projOracle
    rw [Matrix.diagonal_apply]
    simp
  · intro y _ hyx
    unfold projOracle
    rw [Matrix.diagonal_apply]
    simp [hyx.symm]
  · intro h
    exact absurd (Finset.mem_univ x) h

/-! ## Spectral Forrelation -/

/-- The Forrelation operator `Π_g · H^{⊗n} · Π_f`. -/
noncomputable def forrelMat {n : ℕ} (f g : Bits n → Bool) : Matrix (Bits n) (Bits n) ℂ :=
  projOracle g * hadMat n * projOracle f

/-- The spectral Forrelation value `‖Π_g H^{⊗n} Π_f‖²_op`. -/
noncomputable def sfVal {n : ℕ} (f g : Bits n → Bool) : ℝ := opNormSq (forrelMat f g)

/-- The matrix `M^{f,g} = Π_f H^{⊗n} Π_g H^{⊗n} Π_f`. -/
noncomputable def sfMat {n : ℕ} (f g : Bits n → Bool) : Matrix (Bits n) (Bits n) ℂ :=
  projOracle f * hadMat n * projOracle g * hadMat n * projOracle f

theorem sfMat_eq_conjTranspose_mul {n : ℕ} (f g : Bits n → Bool) :
    sfMat f g = (forrelMat f g)ᴴ * forrelMat f g := by
  unfold sfMat forrelMat
  rw [Matrix.conjTranspose_mul, Matrix.conjTranspose_mul, hadMat_conjTranspose,
    projOracle_conjTranspose, projOracle_conjTranspose]
  simp only [Matrix.mul_assoc]
  rw [← Matrix.mul_assoc (projOracle g) (projOracle g), projOracle_mul_self]

theorem normSq_forrelMat_eq_inner {n : ℕ} (f g : Bits n → Bool) (ψ : Bits n → ℂ) :
    normSq (forrelMat f g *ᵥ ψ) = (inner ψ (sfMat f g *ᵥ ψ)).re := by
  rw [normSq_mulVec_eq_inner, sfMat_eq_conjTranspose_mul]

theorem sfMat_posSemidef {n : ℕ} (f g : Bits n → Bool) :
    Matrix.PosSemidef (sfMat f g) := by
  rw [sfMat_eq_conjTranspose_mul]
  exact Matrix.posSemidef_conjTranspose_mul_self _

/-! ## Quantum query algorithms -/

/-- The query-register basis: control/output bit, address bits, work bits. -/
abbrev QReg (n w : ℕ) := Bool × Bits n × Bits w

/-- The phase oracle gate for `f`: `|b,x,z⟩ ↦ (−1)^{b·f(x)} |b,x,z⟩`. -/
noncomputable def phaseOracle {n w : ℕ} (f : Bits n → Bool) : Matrix (QReg n w) (QReg n w) ℂ :=
  Matrix.diagonal fun ⟨b, x, z⟩ => if b && f x then (-1 : ℂ) else 1

/-- A quantum query algorithm: an alternating sequence of arbitrary unitaries
(into which any access to secondary oracles is absorbed) and `T` phase queries to the explicit oracle. -/
structure QueryAlgorithm (n w T : ℕ) where
  /-- The interleaved unitaries. -/
  V : Fin (T + 1) → Matrix (QReg n w) (QReg n w) ℂ
  /-- Each interleaved operator is unitary. -/
  unitary : ∀ j, IsUnitaryMat (V j)

theorem phaseOracle_unitary {n w : ℕ} (f : Bits n → Bool) :
    IsUnitaryMat (phaseOracle (n := n) (w := w) f) := by
  unfold IsUnitaryMat phaseOracle
  rw [Matrix.diagonal_conjTranspose, Matrix.diagonal_mul_diagonal, ← Matrix.diagonal_one]
  congr 1
  funext ⟨b, x, z⟩
  dsimp only
  by_cases h : (b && f x) = true
  · simp_all [RCLike.star_def]
  · simp_all

/-- The state of the algorithm after `j` phase queries (i.e. after the `j`-th
unitary block), starting from `init` with oracle `f`. -/
noncomputable def runState {n w T : ℕ} (alg : QueryAlgorithm n w T) (f : Bits n → Bool)
    (init : QReg n w → ℂ) : Fin (T + 1) → (QReg n w → ℂ) :=
  Fin.induction (motive := fun _ => QReg n w → ℂ)
    (alg.V 0 *ᵥ init)
    (fun j rec => alg.V j.succ *ᵥ (phaseOracle f *ᵥ rec))

theorem runState_zero {n w T : ℕ} (alg : QueryAlgorithm n w T) (f : Bits n → Bool)
    (init : QReg n w → ℂ) : runState alg f init 0 = alg.V 0 *ᵥ init := by
  unfold runState
  rfl

theorem runState_succ {n w T : ℕ} (alg : QueryAlgorithm n w T) (f : Bits n → Bool)
    (init : QReg n w → ℂ) (j : Fin T) :
    runState alg f init j.succ =
      alg.V j.succ *ᵥ (phaseOracle f *ᵥ runState alg f init j.castSucc) := by
  unfold runState
  rfl

theorem normSq_runState {n w T : ℕ} (alg : QueryAlgorithm n w T) (f : Bits n → Bool)
    {init : QReg n w → ℂ} (hinit : IsUnitVec init) (j : Fin (T + 1)) :
    normSq (runState alg f init j) = 1 := by
  induction j using Fin.induction with
  | zero =>
    rw [runState_zero, normSq_mulVec_of_unitary (alg.unitary 0)]
    exact hinit
  | succ j ih =>
    rw [runState_succ, normSq_mulVec_of_unitary (alg.unitary j.succ),
      normSq_mulVec_of_unitary (phaseOracle_unitary f), ih]

/-- The measurement probability of a basis subset. -/
noncomputable def measProb {ι : Type*} [Fintype ι] (ψ : ι → ℂ) (E : Finset ι) : ℝ :=
  ∑ x ∈ E, Complex.normSq (ψ x)

theorem measProb_mono {ι : Type*} [Fintype ι] (ψ : ι → ℂ) {E F : Finset ι} (h : E ⊆ F) :
    measProb ψ E ≤ measProb ψ F := by
  unfold measProb
  apply Finset.sum_le_sum_of_subset_of_nonneg h
  intro x _ _
  exact Complex.normSq_nonneg _

theorem measProb_le_normSq {ι : Type*} [Fintype ι] (ψ : ι → ℂ) (E : Finset ι) :
    measProb ψ E ≤ normSq ψ :=
  measProb_mono ψ (Finset.subset_univ E)

/-- The acceptance probability: measure the final state, accept iff the
control/output bit is `true`. -/
noncomputable def acceptProb {n w T : ℕ} (alg : QueryAlgorithm n w T) (f : Bits n → Bool)
    (init : QReg n w → ℂ) : ℝ :=
  measProb (runState alg f init (Fin.last T)) (Finset.univ.filter fun r : QReg n w => r.1 = true)

/-- The classical-witness initial state `|false, 0, wit⟩`. -/
noncomputable def classicInit {n w : ℕ} (wit : Bits w) : QReg n w → ℂ :=
  basisVec (false, zeroBits n, wit)

theorem isUnitVec_classicInit {n w : ℕ} (wit : Bits w) : IsUnitVec (classicInit (n := n) wit) :=
  isUnitVec_basisVec _

/-- Embed a `q`-bit witness into the first `q` work bits (zeros elsewhere). -/
def embedWit {q w : ℕ} (wit : Bits q) : Bits w :=
  fun i => if h : i.val < q then wit ⟨i.val, h⟩ else false

theorem embedWit_injective {q w : ℕ} (hq : q ≤ w) :
    Function.Injective (embedWit (q := q) (w := w)) := by
  intro z₁ z₂ h
  funext i
  have hi := congrFun h ⟨i.val, lt_of_lt_of_le i.isLt hq⟩
  have he : ∀ (z' : Bits q),
      embedWit (w := w) z' ⟨i.val, lt_of_lt_of_le i.isLt hq⟩ = z' i := by
    intro z'
    show (if h : i.val < q then z' ⟨i.val, h⟩ else false) = z' i
    rw [dif_pos i.isLt]
  rw [he, he] at hi
  exact hi

theorem restr_embedWit {q w : ℕ} (hq : q ≤ w) (z' : Bits q) :
    (fun i : Fin q => embedWit (w := w) z' ⟨i.val, lt_of_lt_of_le i.isLt hq⟩) = z' := by
  funext i
  show (if h : i.val < q then z' ⟨i.val, h⟩ else false) = z' i
  rw [dif_pos i.isLt]

/-- The quantum-witness initial state: the
witness `ψ` occupies the first `q` work qubits and every other qubit (the
control bit, the address bits and the remaining work bits) starts at `|0⟩`,
so the initial state is `|ψ⟩ ⊗ |0…0⟩` and the adversary chooses the witness
register only. -/
noncomputable def qmaInit {n q w : ℕ} (hq : q ≤ w) (ψ : Bits q → ℂ) : QReg n w → ℂ :=
  fun ⟨b, x, z⟩ =>
    if b = false ∧ x = zeroBits n ∧
        z = embedWit (fun i : Fin q => z ⟨i.val, lt_of_lt_of_le i.isLt hq⟩) then
      ψ (fun i : Fin q => z ⟨i.val, lt_of_lt_of_le i.isLt hq⟩)
    else 0

theorem isUnitVec_qmaInit {n q w : ℕ} (hq : q ≤ w) {ψ : Bits q → ℂ}
    (hψ : IsUnitVec ψ) : IsUnitVec (qmaInit (n := n) hq ψ) := by
  classical
  have hpt : ∀ p : QReg n w, Complex.normSq (qmaInit hq ψ p) =
      if p.1 = false ∧ p.2.1 = zeroBits n ∧
          p.2.2 = embedWit (fun i : Fin q => p.2.2 ⟨i.val, lt_of_lt_of_le i.isLt hq⟩)
        then Complex.normSq (ψ (fun i : Fin q => p.2.2 ⟨i.val, lt_of_lt_of_le i.isLt hq⟩))
        else 0 := by
    intro ⟨b, x, z⟩
    show Complex.normSq (if b = false ∧ x = zeroBits n ∧
        z = embedWit (fun i : Fin q => z ⟨i.val, lt_of_lt_of_le i.isLt hq⟩)
      then ψ (fun i : Fin q => z ⟨i.val, lt_of_lt_of_le i.isLt hq⟩) else 0) = _
    split_ifs with h
    · rfl
    · simp
  have hset3 : (Finset.univ.filter fun p : QReg n w =>
        p.1 = false ∧ p.2.1 = zeroBits n ∧
          p.2.2 = embedWit (fun i : Fin q => p.2.2 ⟨i.val, lt_of_lt_of_le i.isLt hq⟩)) =
      Finset.univ.image
        (fun z' : Bits q => (⟨false, zeroBits n, embedWit z'⟩ : QReg n w)) := by
    ext ⟨b, x, z⟩
    simp only [Finset.mem_filter, Finset.mem_univ, true_and]
    constructor
    · intro ⟨hb, hx, hz⟩
      apply Finset.mem_image.mpr
      exact ⟨fun i : Fin q => z ⟨i.val, lt_of_lt_of_le i.isLt hq⟩, Finset.mem_univ _, by
        subst hb; subst hx; rw [← hz]⟩
    · intro h
      rw [Finset.mem_image] at h
      obtain ⟨z', -, hz'⟩ := h
      obtain ⟨hb, hxz⟩ := Prod.ext_iff.mp hz'
      obtain ⟨hx, hz⟩ := Prod.ext_iff.mp hxz
      subst hb; subst hx; subst hz
      exact ⟨rfl, rfl, by rw [restr_embedWit hq]⟩
  unfold IsUnitVec normSq
  rw [Finset.sum_congr rfl (fun p _ => hpt p), ← Finset.sum_filter, hset3,
    Finset.sum_image (fun x _ y _ h =>
      embedWit_injective hq (Prod.ext_iff.mp (Prod.ext_iff.mp h).2).2),
    Finset.sum_congr rfl (fun z' _ => by rw [restr_embedWit hq])]
  exact hψ

/-- The acceptance probability of a query algorithm with the quantum witness
`ψ` on the first `q` work qubits: the run starts from `qmaInit hq ψ`, i.e.
`|ψ⟩` on the witness qubits and `|0⟩` everywhere else. -/
noncomputable def qmaAcceptProb {n w T : ℕ} (alg : QueryAlgorithm n w T) (f : Bits n → Bool)
    {q : ℕ} (hq : q ≤ w) (ψ : Bits q → ℂ) : ℝ :=
  acceptProb alg f (qmaInit hq ψ)

/-- The two-oracle pair `(f, g)` as a single oracle on `n+1` bits: the
first address bit selects between `f` and `g`. -/
def mergeOracle {n : ℕ} (f g : Bits n → Bool) : Bits (n + 1) → Bool :=
  fun y => if y 0 then g (fun i => y i.succ) else f (fun i => y i.succ)

/-! ## The iterated sampler -/

/-- The probability that, running with oracle `f` up to the `(j+1)`-th query
and measuring the query register, the control bit is `true` and the address
equals `x`. -/
noncomputable def hitProb {n w t : ℕ} (alg : QueryAlgorithm n w t) (f : Bits n → Bool)
    (init : QReg n w → ℂ) (j : Fin t) (x : Bits n) : ℝ :=
  measProb (runState alg f init j.castSucc)
    (Finset.univ.filter fun r : QReg n w => r.1 = true ∧ r.2.1 = x)

/-- The probability that the remaining `k` rounds of the iterated sampler all
produce a fresh point of `S`, given the already-sampled set `Δ` and the
classical witness `wit`. -/
noncomputable def chainProb {n w t : ℕ} (alg : QueryAlgorithm n w t) (S : Finset (Bits n))
    (wit : Bits w) (Δ : Finset (Bits n)) : ℕ → ℝ
  | 0 => 1
  | (k + 1) =>
    (1 / (t : ℝ)) * ∑ j : Fin t, ∑ x ∈ S \ Δ,
      hitProb alg (fun y => decide (y ∈ Δ)) (classicInit wit) j x *
        chainProb alg S wit (insert x Δ) k

/-- The success probability of the witness-guessing cumulative sampler: a
uniform `q`-bit witness guess, then `v` iterated rounds. -/
noncomputable def cumulativeSuccessProb {n w t : ℕ} (alg : QueryAlgorithm n w t)
    (S : Finset (Bits n)) (q v : ℕ) : ℝ :=
  (1 / (2 : ℝ) ^ q) * ∑ wit : Bits q,
    chainProb alg S (embedWit wit) (∅ : Finset (Bits n)) v

/-! ## The Strong distribution -/

/-- The quantity `γ_y(S) = (1/ℓ)·(∑_i (−1)^{y·s_i})²`. -/
noncomputable def gamma {n ℓ : ℕ} (S : Fin ℓ → Bits n) (y : Bits n) : ℝ :=
  (∑ i, bitsSignR y (S i)) ^ 2 / ℓ

theorem gamma_nonneg {n ℓ : ℕ} (S : Fin ℓ → Bits n) (y : Bits n) : 0 ≤ gamma S y := by
  unfold gamma
  positivity

theorem gamma_le {n ℓ : ℕ} (hℓ : 1 ≤ ℓ) (S : Fin ℓ → Bits n) (y : Bits n) :
    gamma S y ≤ ℓ := by
  have habs : |∑ i, bitsSignR y (S i)| ≤ ℓ := by
    calc |∑ i, bitsSignR y (S i)| ≤ ∑ i, |bitsSignR y (S i)| := Finset.abs_sum_le_sum_abs _ _
      _ = ∑ _i : Fin ℓ, (1 : ℝ) := by
        apply Finset.sum_congr rfl
        intro i _
        unfold bitsSignR
        rcases zmod2_eq_zero_or_one (dotZ2 y (S i)) with h | h <;> simp [signR, h]
      _ = ℓ := by simp
  have hsq : (∑ i, bitsSignR y (S i)) ^ 2 ≤ (ℓ : ℝ) ^ 2 := by
    rw [← sq_abs, sq_le_sq₀ (abs_nonneg _) (by positivity)]
    exact habs
  unfold gamma
  rw [div_le_iff₀ (by positivity : (0:ℝ) < ℓ)]
  calc (∑ i, bitsSignR y (S i)) ^ 2 ≤ (ℓ : ℝ) ^ 2 := hsq
    _ = ℓ * ℓ := by rw [pow_two]

/-- The inclusion probability `1 − e^{−κγ_y(S)}/2`. -/
noncomputable def inclProb {n ℓ : ℕ} (κ : ℝ) (S : Fin ℓ → Bits n) (y : Bits n) : ℝ :=
  1 - Real.exp (-κ * gamma S y) / 2

/-- The `U`-marginal weight: independent per-point inclusion over `y ≠ 0`;
the point `0` is never included. -/
noncomputable def uWeight {n ℓ : ℕ} (κ : ℝ) (S : Fin ℓ → Bits n) (U : Bits n → Bool) : ℝ :=
  ∏ y : Bits n, if y = zeroBits n then (if U y then 0 else 1)
    else if U y then inclProb κ S y else 1 - inclProb κ S y

/-- The Strong distribution weight of the pair `(S, U)`. -/
noncomputable def strongWeight {n ℓ : ℕ} (κ : ℝ) (S : Fin ℓ → Bits n) (U : Bits n → Bool) : ℝ :=
  ((2 : ℝ) ^ (n * ℓ))⁻¹ * uWeight κ S U

/-- The Strong probability of an event. -/
noncomputable def strongProb (n ℓ : ℕ) (κ : ℝ)
    (E : (Fin ℓ → Bits n) → (Bits n → Bool) → Prop) : ℝ := by
  classical
  exact ∑ S : Fin ℓ → Bits n, ∑ U : Bits n → Bool, if E S U then strongWeight κ S U else 0

/-- The support of a list, as a set. -/
def suppFinset {n ℓ : ℕ} (S : Fin ℓ → Bits n) : Finset (Bits n) := Finset.univ.image S

/-- Even multiplicity of every index in a tuple (the "trivial equation"
predicate of the strong-yes proof). -/
def EvenMultiplicity {ℓ m : ℕ} (idx : Fin m → Fin ℓ) : Prop :=
  ∀ k : Fin ℓ, Even ((Finset.univ.filter fun a => idx a = k).card)

/-- A "good" list: no nontrivial xor equations of two, four or
six terms. -/
def IsGoodList {n ℓ : ℕ} (S : Fin ℓ → Bits n) : Prop :=
  (∀ i j : Fin ℓ, toZ2 (S i) + toZ2 (S j) = 0 → i = j) ∧
  (∀ idx : Fin 4 → Fin ℓ, (∑ a, toZ2 (S (idx a))) = 0 → EvenMultiplicity idx) ∧
  (∀ idx : Fin 6 → Fin ℓ, (∑ a, toZ2 (S (idx a))) = 0 → EvenMultiplicity idx)

/-- Decidability of the good-list predicate (via classical choice). -/
noncomputable instance IsGoodList.decidable {n ℓ : ℕ} :
    DecidablePred (IsGoodList (n := n) (ℓ := ℓ)) :=
  fun S => Classical.propDecidable _

/-- A good list has distinct elements (the `k = 1` clause). -/
theorem IsGoodList.injective {n ℓ : ℕ} {S : Fin ℓ → Bits n} (h : IsGoodList S) :
    Function.Injective S := by
  intro i j hij
  apply h.1
  have hsame : toZ2 (S i) = toZ2 (S j) := by rw [hij]
  rw [hsame]
  funext k
  show toZ2 (S j) k + toZ2 (S j) k = (0 : ZMod 2)
  rcases zmod2_eq_zero_or_one (toZ2 (S j) k) with h0 | h0
  · rw [h0, add_zero]
  · rw [h0]
    decide

/-- The uniform superposition `|S⟩ = (1/√ℓ) Σ_i |s_i⟩`. -/
noncomputable def unifState {n ℓ : ℕ} (S : Fin ℓ → Bits n) : Bits n → ℂ :=
  fun x => ((Real.sqrt ℓ)⁻¹ : ℝ) • ∑ i : Fin ℓ, basisVec (S i) x

theorem unifState_sum_basisVec {n ℓ : ℕ} {S : Fin ℓ → Bits n} (hS : IsGoodList S) (x : Bits n) :
    (∑ i : Fin ℓ, basisVec (S i) x) = if x ∈ suppFinset S then (1 : ℂ) else 0 := by
  have hinj := hS.injective
  by_cases hx : x ∈ suppFinset S
  · obtain ⟨i, _, hi⟩ := Finset.mem_image.mp hx
    rw [if_pos hx, Finset.sum_eq_single i]
    · simp [basisVec, hi]
    · intro j _ hji
      subst hi
      simp only [basisVec]
      rw [if_neg]
      intro h
      exact hji (hinj h).symm
    · intro h
      exact absurd (Finset.mem_univ i) h
  · rw [if_neg hx]
    apply Finset.sum_eq_zero
    intro i _
    simp only [basisVec]
    rw [if_neg]
    intro h
    exact hx (Finset.mem_image.mpr ⟨i, Finset.mem_univ i, h.symm⟩)

theorem normSq_unifState {n ℓ : ℕ} (hℓ : 1 ≤ ℓ) {S : Fin ℓ → Bits n} (hS : IsGoodList S) :
    normSq (unifState S) = 1 := by
  have hinj := hS.injective
  have h1 : (0 : ℝ) < (ℓ : ℝ) := by exact_mod_cast hℓ
  have h2 : ((Real.sqrt (ℓ : ℝ))⁻¹ : ℝ) * ((Real.sqrt (ℓ : ℝ))⁻¹ : ℝ) = (ℓ : ℝ)⁻¹ := by
    rw [← mul_inv_rev, Real.mul_self_sqrt (le_of_lt h1)]
  have hpt : ∀ x : Bits n, Complex.normSq (unifState S x) =
      if x ∈ suppFinset S then (((Real.sqrt ℓ)⁻¹ : ℝ) * ((Real.sqrt ℓ)⁻¹ : ℝ)) else 0 := by
    intro x
    unfold unifState
    rw [unifState_sum_basisVec hS x]
    split_ifs with hx
    · rw [Complex.real_smul, Complex.normSq_mul, Complex.normSq_ofReal, Complex.normSq_one,
        mul_one, ← pow_two]
    · simp
  unfold normSq
  rw [Finset.sum_congr rfl (fun x _ => hpt x)]
  rw [Finset.sum_ite_mem, Finset.univ_inter]
  rw [Finset.sum_const, nsmul_eq_mul]
  have hcard : (suppFinset S).card = ℓ := by
    unfold suppFinset
    rw [Finset.card_image_of_injective _ hinj, Finset.card_univ, Fintype.card_fin]
  rw [hcard, h2]
  exact mul_inv_cancel₀ (ne_of_gt h1)

/-! ## The core matrix and its expectation -/

/-- `H Π_g H`: the matrix whose `S`-supported principal submatrices carry
the analysis. -/
noncomputable def coreMatU {n : ℕ} (g : Bits n → Bool) : Matrix (Bits n) (Bits n) ℂ :=
  hadMat n * projOracle g * hadMat n

/-- The expected core matrix `M^S = 𝔼_g[H Π_g H]` under the Strong
distribution: the diagonal entry at `0` is `0` (the point `0` is never
included), and at `y ≠ 0` it is `inclProb κ S y`. -/
noncomputable def expCoreMat {n ℓ : ℕ} (κ : ℝ) (S : Fin ℓ → Bits n) : Matrix (Bits n) (Bits n) ℂ :=
  hadMat n * Matrix.diagonal
    (fun y => if y = zeroBits n then 0 else ((inclProb κ S y : ℝ) : ℂ)) * hadMat n

/-- The lower Taylor matrix `A^S`. -/
noncomputable def matA {n ℓ : ℕ} (κ : ℝ) (S : Fin ℓ → Bits n) : Matrix (Bits n) (Bits n) ℂ :=
  hadMat n * Matrix.diagonal
    (fun y => (((1 : ℝ) / 2 + κ * gamma S y / 2 - κ ^ 2 * gamma S y ^ 2 / 4 : ℝ) : ℂ)) * hadMat n

/-- The upper Taylor matrix `B^S`. -/
noncomputable def matB {n ℓ : ℕ} (κ : ℝ) (S : Fin ℓ → Bits n) : Matrix (Bits n) (Bits n) ℂ :=
  hadMat n * Matrix.diagonal
    (fun y => (((1 : ℝ) / 2 + κ * gamma S y / 2 : ℝ) : ℂ)) * hadMat n

/-- The maximal Rayleigh quotient over unit vectors supported on `Δ`
(`0` if `Δ` is empty, by the `sSup ∅ = 0` convention). -/
noncomputable def rayleighMax {n : ℕ} (A : Matrix (Bits n) (Bits n) ℂ) (Δ : Finset (Bits n)) : ℝ :=
  sSup {r : ℝ | ∃ ψ : Bits n → ℂ, IsUnitVec ψ ∧ (∀ x, ψ x ≠ 0 → x ∈ Δ) ∧
    r = (inner ψ (A *ᵥ ψ)).re}

theorem normSq_mulVec_le_frob {ι : Type*} [Fintype ι] (A : Matrix ι ι ℂ) {ψ : ι → ℂ}
    (hψ : IsUnitVec ψ) : normSq (A *ᵥ ψ) ≤ ∑ x, ∑ y, Complex.normSq (A x y) := by
  unfold normSq
  apply Finset.sum_le_sum
  intro x _
  rw [Matrix.mulVec_apply_eq_sum]
  calc Complex.normSq (∑ y, A x y * ψ y)
      ≤ (∑ y, ‖A x y‖ * ‖ψ y‖) ^ 2 := by
        rw [Complex.normSq_eq_norm_sq]
        apply pow_le_pow_left₀ (norm_nonneg _)
        calc ‖∑ y, A x y * ψ y‖ ≤ ∑ y, ‖A x y * ψ y‖ := norm_sum_le _ _
          _ = ∑ y, ‖A x y‖ * ‖ψ y‖ := by
              apply Finset.sum_congr rfl
              intro y _
              rw [norm_mul]
    _ ≤ (∑ y, ‖A x y‖ ^ 2) * (∑ y, ‖ψ y‖ ^ 2) :=
        Finset.sum_mul_sq_le_sq_mul_sq _ _ _
    _ = (∑ y, Complex.normSq (A x y)) * normSq ψ := by
        unfold normSq
        congr 1 <;> apply Finset.sum_congr rfl <;> intro y _ <;> rw [Complex.normSq_eq_norm_sq]
    _ = ∑ y, Complex.normSq (A x y) := by rw [hψ, mul_one]

theorem rayleighMax_bddAbove {n : ℕ} (A : Matrix (Bits n) (Bits n) ℂ) (Δ : Finset (Bits n)) :
    BddAbove {r : ℝ | ∃ ψ : Bits n → ℂ, IsUnitVec ψ ∧ (∀ x, ψ x ≠ 0 → x ∈ Δ) ∧
      r = (inner ψ (A *ᵥ ψ)).re} := by
  refine ⟨Real.sqrt (∑ x, ∑ y, Complex.normSq (A x y)), ?_⟩
  rintro r ⟨ψ, hψ, -, rfl⟩
  calc (inner ψ (A *ᵥ ψ)).re
      ≤ ‖inner ψ (A *ᵥ ψ)‖ := Complex.re_le_norm _
    _ = Real.sqrt (Complex.normSq (inner ψ (A *ᵥ ψ))) := Complex.norm_def _
    _ ≤ Real.sqrt (normSq ψ * normSq (A *ᵥ ψ)) :=
        Real.sqrt_le_sqrt (normSq_inner_le _ _)
    _ = Real.sqrt (normSq (A *ᵥ ψ)) := by rw [hψ, one_mul]
    _ ≤ Real.sqrt (∑ x, ∑ y, Complex.normSq (A x y)) :=
        Real.sqrt_le_sqrt (normSq_mulVec_le_frob A hψ)

/-- The operator norm squared equals the maximal Rayleigh quotient of the
associated positive semidefinite matrix. -/
theorem opNormSq_eq_rayleighMax {n : ℕ} (A : Matrix (Bits n) (Bits n) ℂ) :
    opNormSq A = rayleighMax (Aᴴ * A) Finset.univ := by
  unfold opNormSq rayleighMax
  congr 1
  ext r
  constructor
  · rintro ⟨ψ, hψ, rfl⟩
    exact ⟨ψ, hψ, fun _ _ => Finset.mem_univ _, normSq_mulVec_eq_inner A ψ⟩
  · rintro ⟨ψ, hψ, -, rfl⟩
    exact ⟨ψ, hψ, (normSq_mulVec_eq_inner A ψ).symm⟩

/-- The spectral Forrelation value equals the maximal Rayleigh quotient of
`M^{f,g}`. -/
theorem sfVal_eq_rayleighMax {n : ℕ} (f g : Bits n → Bool) :
    sfVal f g = rayleighMax (sfMat f g) Finset.univ := by
  unfold sfVal
  rw [opNormSq_eq_rayleighMax, sfMat_eq_conjTranspose_mul]

/-- The quadratic form of a matrix written with our inner product. -/
theorem inner_eq_star_dotProduct {ι : Type*} [Fintype ι] (X : Matrix ι ι ℂ) (ψ : ι → ℂ) :
    inner ψ (X *ᵥ ψ) = star ψ ⬝ᵥ (X *ᵥ ψ) := by
  unfold inner dotProduct
  apply Finset.sum_congr rfl
  intro x _
  rw [Pi.star_apply]

theorem inner_basisVec_left {ι : Type*} [Fintype ι] [DecidableEq ι] (A : Matrix ι ι ℂ) (i j : ι) :
    inner (basisVec i) (A *ᵥ basisVec j) = A i j := by
  unfold inner
  rw [Finset.sum_eq_single i]
  · rw [Matrix.mulVec_apply_eq_sum, Finset.sum_eq_single j]
    · simp [basisVec]
    · intro k _ hkj
      simp [basisVec, hkj]
    · intro h
      exact absurd (Finset.mem_univ j) h
  · intro y _ hyi
    simp [basisVec, hyi]
  · intro h
    exact absurd (Finset.mem_univ i) h

theorem inner_sub_mulVec {ι : Type*} [Fintype ι] (A B : Matrix ι ι ℂ) (ψ : ι → ℂ) :
    inner ψ ((B - A) *ᵥ ψ) = inner ψ (B *ᵥ ψ) - inner ψ (A *ᵥ ψ) := by
  rw [Matrix.sub_mulVec]
  unfold inner
  simp_rw [Pi.sub_apply, mul_sub]
  rw [Finset.sum_sub_distrib]

/-- The Rayleigh maximum is monotone in the positive-semidefinite order. -/
theorem rayleighMax_le_of_psd {n : ℕ} {A B : Matrix (Bits n) (Bits n) ℂ}
    (h : Matrix.PosSemidef (B - A)) (Δ : Finset (Bits n)) :
    rayleighMax A Δ ≤ rayleighMax B Δ := by
  unfold rayleighMax
  by_cases hΔ : Δ.Nonempty
  · obtain ⟨x, hx⟩ := hΔ
    apply csSup_le
    · refine ⟨(A x x).re, basisVec x, isUnitVec_basisVec x, ?_, ?_⟩
      · intro y hy
        simp only [basisVec] at hy
        split_ifs at hy with hyx
        · exact hyx ▸ hx
        · exact absurd hy (by simp)
      · rw [inner_basisVec_left]
    · rintro r ⟨ψ, hψ, hsupp, rfl⟩
      have hstep : (inner ψ (A *ᵥ ψ)).re ≤ (inner ψ (B *ᵥ ψ)).re := by
        have hpsd := h.dotProduct_mulVec_nonneg ψ
        rw [← inner_eq_star_dotProduct, inner_sub_mulVec] at hpsd
        have hre := (RCLike.le_iff_re_im.mp hpsd).1
        rw [RCLike.zero_re, map_sub] at hre
        exact sub_nonneg.mp hre
      exact hstep.trans (le_csSup (rayleighMax_bddAbove B Δ) ⟨ψ, hψ, hsupp, rfl⟩)
  · rw [Finset.not_nonempty_iff_eq_empty.mp hΔ]
    have hset : ∀ X : Matrix (Bits n) (Bits n) ℂ,
        {r : ℝ | ∃ ψ : Bits n → ℂ, IsUnitVec ψ ∧ (∀ x, ψ x ≠ 0 → x ∈ (∅ : Finset (Bits n))) ∧
          r = (inner ψ (X *ᵥ ψ)).re} = ∅ := by
      intro X
      ext r
      simp only [Set.mem_ofPred_eq, Set.mem_empty_iff_false, iff_false]
      rintro ⟨ψ, hψ, hsupp, -⟩
      have hz : ψ = 0 := by
        funext x
        by_contra hne
        exact absurd (hsupp x hne) (Finset.notMem_empty x)
      rw [hz, IsUnitVec, normSq] at hψ
      simp at hψ
    simp only [rayleighMax, hset, Real.sSup_empty, le_refl]

theorem inner_smul_left {ι : Type*} [Fintype ι] (c : ℂ) (ψ φ : ι → ℂ) :
    inner (c • ψ) φ = star c * inner ψ φ := by
  unfold inner
  simp_rw [Pi.smul_apply, smul_eq_mul, star_mul]
  rw [Finset.mul_sum]
  apply Finset.sum_congr rfl
  intro x _
  ring

theorem inner_smul_right {ι : Type*} [Fintype ι] (c : ℂ) (ψ φ : ι → ℂ) :
    inner ψ (c • φ) = c * inner ψ φ := by
  unfold inner
  simp_rw [Pi.smul_apply, smul_eq_mul]
  rw [Finset.mul_sum]
  apply Finset.sum_congr rfl
  intro x _
  ring

theorem normSq_smul {ι : Type*} [Fintype ι] (c : ℂ) (ψ : ι → ℂ) :
    normSq (c • ψ) = Complex.normSq c * normSq ψ := by
  unfold normSq
  rw [Finset.mul_sum]
  apply Finset.sum_congr rfl
  intro x _
  rw [Pi.smul_apply, smul_eq_mul, Complex.normSq_mul]

/-- The Rayleigh maximum of a positive-semidefinite matrix is non-negative. -/
theorem rayleighMax_nonneg {n : ℕ} {X : Matrix (Bits n) (Bits n) ℂ}
    (hX : Matrix.PosSemidef X) (Δ : Finset (Bits n)) : 0 ≤ rayleighMax X Δ := by
  by_cases hΔ : Δ.Nonempty
  · obtain ⟨x, hx⟩ := hΔ
    have hge : 0 ≤ (inner (basisVec x) (X *ᵥ basisVec x)).re := by
      have h2 := hX.dotProduct_mulVec_nonneg (basisVec x)
      rw [← inner_eq_star_dotProduct] at h2
      have hre := (RCLike.le_iff_re_im.mp h2).1
      simpa using hre
    exact hge.trans (le_csSup (rayleighMax_bddAbove X Δ)
      ⟨basisVec x, isUnitVec_basisVec x, (fun y hy => by
        simp only [basisVec] at hy
        split_ifs at hy with hyx
        · exact hyx ▸ hx
        · exact absurd hy (by simp)), rfl⟩)
  · rw [Finset.not_nonempty_iff_eq_empty.mp hΔ]
    have hset : ∀ X : Matrix (Bits n) (Bits n) ℂ,
        {r : ℝ | ∃ ψ : Bits n → ℂ, IsUnitVec ψ ∧ (∀ x, ψ x ≠ 0 → x ∈ (∅ : Finset (Bits n))) ∧
          r = (inner ψ (X *ᵥ ψ)).re} = ∅ := by
      intro X
      ext r
      simp only [Set.mem_ofPred_eq, Set.mem_empty_iff_false, iff_false]
      rintro ⟨ψ, hψ, hsupp, -⟩
      have hz : ψ = 0 := by
        funext x
        by_contra hne
        exact absurd (hsupp x hne) (Finset.notMem_empty x)
      rw [hz, IsUnitVec, normSq] at hψ
      simp at hψ
    simp only [rayleighMax, hset, Real.sSup_empty, le_refl]

/-- Projecting both sides of a positive-semidefinite matrix restricts its
Rayleigh maximum. -/
theorem rayleighMax_proj_le {n : ℕ} {X : Matrix (Bits n) (Bits n) ℂ}
    (hX : Matrix.PosSemidef X) (Δ : Finset (Bits n)) :
    rayleighMax (projOracle (fun x => decide (x ∈ Δ)) * X *
      projOracle (fun x => decide (x ∈ Δ))) Finset.univ ≤ rayleighMax X Δ := by
  unfold rayleighMax
  apply csSup_le
  · refine ⟨(inner (basisVec (zeroBits n)) ((projOracle (fun x => decide (x ∈ Δ)) * X *
        projOracle (fun x => decide (x ∈ Δ))) *ᵥ basisVec (zeroBits n))).re,
      basisVec (zeroBits n), isUnitVec_basisVec _, fun _ _ => Finset.mem_univ _, rfl⟩
  · rintro r ⟨ψ, hψ, -, rfl⟩
    have hrewrite : inner ψ ((projOracle (fun x => decide (x ∈ Δ)) * X *
        projOracle (fun x => decide (x ∈ Δ))) *ᵥ ψ) =
        inner (projOracle (fun x => decide (x ∈ Δ)) *ᵥ ψ)
          (X *ᵥ (projOracle (fun x => decide (x ∈ Δ)) *ᵥ ψ)) := by
      rw [← Matrix.mulVec_mulVec, ← Matrix.mulVec_mulVec, inner_mulVec_right,
        projOracle_conjTranspose]
    rw [hrewrite]
    set φ := projOracle (fun x => decide (x ∈ Δ)) *ᵥ ψ with hφ
    by_cases hφ0 : φ = 0
    · rw [hφ0]
      have h0 : (inner (0 : Bits n → ℂ) (X *ᵥ (0 : Bits n → ℂ))).re = 0 := by
        simp [inner]
      rw [h0]
      exact rayleighMax_nonneg hX Δ
    · have hsuppφ : ∀ x, φ x ≠ 0 → x ∈ Δ := by
        intro x hx
        by_contra hxΔ
        apply hx
        rw [hφ, projOracle_mulVec_apply]
        simp_all
      have hnormφ : normSq φ ≤ 1 := by
        have hpt : ∀ x : Bits n, Complex.normSq (φ x) =
            if x ∈ Δ then Complex.normSq (ψ x) else 0 := by
          intro x
          rw [hφ, projOracle_mulVec_apply]
          by_cases hx : x ∈ Δ
          · simp [hx]
          · simp [hx]
        unfold normSq
        rw [Finset.sum_congr rfl (fun x _ => hpt x)]
        calc ∑ x, (if x ∈ Δ then Complex.normSq (ψ x) else 0)
            = ∑ x ∈ Δ, Complex.normSq (ψ x) := by
              rw [Finset.sum_ite_mem, Finset.univ_inter]
          _ ≤ ∑ x, Complex.normSq (ψ x) := by
              apply Finset.sum_le_sum_of_subset_of_nonneg (Finset.subset_univ _)
              intro x _ _
              exact Complex.normSq_nonneg _
          _ = 1 := hψ
      have hnz : 0 < normSq φ := by
        unfold normSq
        apply Finset.sum_pos'
        · intro x _; exact Complex.normSq_nonneg _
        · obtain ⟨x, hx⟩ : ∃ x, φ x ≠ 0 := by
            by_contra h
            push_neg at h
            exact hφ0 (funext h)
          exact ⟨x, Finset.mem_univ x, Complex.normSq_pos.mpr hx⟩
      set c : ℂ := ((Real.sqrt (normSq φ) : ℝ)⁻¹ : ℂ) with hc
      have hcsq : c * c = (((normSq φ)⁻¹ : ℝ) : ℂ) := by
        rw [hc, ← Complex.ofReal_inv, ← Complex.ofReal_mul, ← mul_inv_rev,
          Real.mul_self_sqrt (normSq_nonneg _)]
      have hstar : star c = c := by
        rw [hc, RCLike.star_def, ← Complex.ofReal_inv, Complex.conj_ofReal]
      have hdecomp : inner φ (X *ᵥ φ) =
          ((normSq φ : ℝ) : ℂ) * inner (c • φ) (X *ᵥ (c • φ)) := by
        rw [Matrix.mulVec_smul, inner_smul_left, inner_smul_right, hstar]
        rw [show ((normSq φ : ℝ) : ℂ) * (c * (c * inner φ (X *ᵥ φ))) =
              (((normSq φ : ℝ) : ℂ) * (c * c)) * inner φ (X *ᵥ φ) by ring]
        rw [hcsq, ← Complex.ofReal_mul, mul_inv_cancel₀ (ne_of_gt hnz), Complex.ofReal_one,
          one_mul]
      have hunitφ' : IsUnitVec (c • φ) := by
        unfold IsUnitVec
        rw [normSq_smul, hc, ← Complex.ofReal_inv, Complex.normSq_ofReal, ← mul_inv_rev,
          Real.mul_self_sqrt (normSq_nonneg _)]
        exact inv_mul_cancel₀ (ne_of_gt hnz)
      have hle := le_csSup (rayleighMax_bddAbove X Δ)
        ⟨c • φ, hunitφ', fun x hx => hsuppφ x (by
          intro h0
          apply hx
          rw [Pi.smul_apply, smul_eq_mul, h0, mul_zero]), rfl⟩
      have hmain : (inner φ (X *ᵥ φ)).re ≤ normSq φ * rayleighMax X Δ := by
        rw [hdecomp]
        have hre : (((normSq φ : ℝ) : ℂ) * inner (c • φ) (X *ᵥ (c • φ))).re =
            normSq φ * (inner (c • φ) (X *ᵥ (c • φ))).re := by
          simp [Complex.mul_re, Complex.ofReal_re, Complex.ofReal_im]
        rw [hre]
        exact mul_le_mul_of_nonneg_left hle (normSq_nonneg _)
      exact hmain.trans (mul_le_of_le_one_left (rayleighMax_nonneg hX Δ) hnormφ)

/-! ## The Hadamard-sandwich form of the PSD order -/

theorem posSemidef_hadMat_sandwich {n : ℕ} (d : Bits n → ℝ) :
    Matrix.PosSemidef (hadMat n * Matrix.diagonal (fun y => ((d y : ℝ) : ℂ)) * hadMat n) ↔
      ∀ y, 0 ≤ d y := by
  constructor
  · intro h y
    have h2 := h.dotProduct_mulVec_nonneg (hadMat n *ᵥ basisVec y)
    rw [← inner_eq_star_dotProduct] at h2
    have hcalc : inner (hadMat n *ᵥ basisVec y)
        ((hadMat n * Matrix.diagonal (fun y => ((d y : ℝ) : ℂ)) * hadMat n) *ᵥ
          (hadMat n *ᵥ basisVec y)) = (d y : ℂ) := by
      have hH : hadMat n *ᵥ (hadMat n *ᵥ basisVec y) = basisVec y := by
        rw [Matrix.mulVec_mulVec, hadMat_mul_self, Matrix.one_mulVec]
      have hstep : (hadMat n * Matrix.diagonal (fun y => ((d y : ℝ) : ℂ)) * hadMat n) *ᵥ
          (hadMat n *ᵥ basisVec y) =
          hadMat n *ᵥ (Matrix.diagonal (fun y => ((d y : ℝ) : ℂ)) *ᵥ
            (hadMat n *ᵥ (hadMat n *ᵥ basisVec y))) := by
        rw [← Matrix.mulVec_mulVec, ← Matrix.mulVec_mulVec]
      rw [hstep, hH, inner_mulVec_right, hadMat_conjTranspose, hH, inner_basisVec_left]
      simp [Matrix.diagonal]
    rw [hcalc] at h2
    have hre := (RCLike.le_iff_re_im.mp h2).1
    simpa using hre
  · intro hd
    apply Matrix.posSemidef_iff_dotProduct_mulVec.mpr
    refine ⟨?_, ?_⟩
    · have hD : (Matrix.diagonal (fun y => ((d y : ℝ) : ℂ))).IsHermitian := by
        rw [Matrix.IsHermitian, Matrix.diagonal_conjTranspose]
        congr 1
        funext y
        simp [RCLike.star_def, Complex.conj_ofReal]
      rw [show hadMat n * Matrix.diagonal (fun y => ((d y : ℝ) : ℂ)) * hadMat n =
          (hadMat n)ᴴ * Matrix.diagonal (fun y => ((d y : ℝ) : ℂ)) * hadMat n from by
        rw [hadMat_conjTranspose]]
      exact Matrix.isHermitian_conjTranspose_mul_mul _ hD
    · intro ψ
      rw [← inner_eq_star_dotProduct, ← Matrix.mulVec_mulVec, ← Matrix.mulVec_mulVec,
        inner_mulVec_right, hadMat_conjTranspose]
      have hsum : inner (hadMat n *ᵥ ψ)
          (Matrix.diagonal (fun y => ((d y : ℝ) : ℂ)) *ᵥ (hadMat n *ᵥ ψ)) =
          ↑(∑ y, d y * Complex.normSq ((hadMat n *ᵥ ψ) y)) := by
        unfold inner
        rw [Complex.ofReal_sum]
        apply Finset.sum_congr rfl
        intro y _
        rw [Matrix.mulVec_apply_eq_sum (Matrix.diagonal fun y => ((d y : ℝ) : ℂ))
          (hadMat n *ᵥ ψ) y]
        rw [Finset.sum_eq_single y]
        · rw [Matrix.diagonal_apply]
          rw [if_pos rfl]
          have hw : star ((hadMat n *ᵥ ψ) y) * (hadMat n *ᵥ ψ) y =
              ↑(Complex.normSq ((hadMat n *ᵥ ψ) y)) := by
            rw [RCLike.star_def, Complex.conj_mul', Complex.normSq_eq_norm_sq]
            try rw [Complex.ofReal_pow]
          calc star ((hadMat n *ᵥ ψ) y) * (↑(d y) * (hadMat n *ᵥ ψ) y)
              = ↑(d y) * (star ((hadMat n *ᵥ ψ) y) * (hadMat n *ᵥ ψ) y) := by ring
            _ = ↑(d y) * ↑(Complex.normSq ((hadMat n *ᵥ ψ) y)) := by rw [hw]
            _ = _ := by rw [← Complex.ofReal_mul]
        · intro z _ hzy
          rw [Matrix.diagonal_apply]
          simp [hzy.symm]
        · intro h
          exact absurd (Finset.mem_univ y) h
      rw [hsum]
      have hnn : 0 ≤ ∑ y, d y * Complex.normSq ((hadMat n *ᵥ ψ) y) :=
        Finset.sum_nonneg (fun y _ => mul_nonneg (hd y) (Complex.normSq_nonneg _))
      rw [RCLike.le_iff_re_im]
      exact ⟨by simpa using hnn, by simp⟩

/-! ## Packaged hypotheses (proved results from the reviewed literature) -/

/-- The amplification theorem for QMA verifiers with a gap: a `(c, s)`
verifier with a `t`-query algorithm and quantum witnesses on `q` qubits can
be amplified to completeness `2/3` and soundness `1/3` with `O(t/(c−s)²)`
queries, preserving the witness length. Witnesses range over the first `q`
work qubits with all other qubits pinned to `|0⟩` (`qmaAcceptProb`). Packaged as a hypothesis. -/
def mwAmplificationProp : Prop :=
  ∃ C : ℝ, 0 < C ∧ ∀ (n w t : ℕ) (alg : QueryAlgorithm n w t) (q : ℕ) (hq : q ≤ w)
    (c s : ℝ),
    0 ≤ s → s < c → c ≤ 1 →
      ∃ (w' t' : ℕ) (alg' : QueryAlgorithm n w' t') (q' : ℕ) (hq' : q' ≤ w'),
        (t' : ℝ) ≤ C * (t + 1) / (c - s) ^ 2 ∧
        q' = q ∧
        ∀ f : Bits n → Bool,
          ((∃ ψ, IsUnitVec ψ ∧ c ≤ qmaAcceptProb alg f hq ψ) →
            ∃ ψ', IsUnitVec ψ' ∧ (2 : ℝ) / 3 ≤ qmaAcceptProb alg' f hq' ψ') ∧
          ((∀ ψ, IsUnitVec ψ → qmaAcceptProb alg f hq ψ ≤ s) →
            ∀ ψ', IsUnitVec ψ' → qmaAcceptProb alg' f hq' ψ' ≤ (1 : ℝ) / 3)

/-- The trace-distance bound for pure states and a measurement event: the
measurement-probability difference is at most the state distance. This
proposition is defined for reference; the main theorem does not assume it. -/
def traceDistanceProp : Prop :=
  ∀ (ι : Type) [Fintype ι] (ψ φ : ι → ℂ) (E : Finset ι),
    IsUnitVec ψ → IsUnitVec φ →
      measProb ψ E - measProb φ E ≤ (normSq (ψ - φ)).sqrt

/-- The conclusion of the concentration claim: all
supported-on-`Δ` Rayleigh quotients of the sampled core matrix are within
`ρ` of the expectation, and the `|S⟩` quotient is within `ρ` below. -/
def concGood {n ℓ : ℕ} (κ : ℝ) (S : Fin ℓ → Bits n) (ρ : ℝ) (g : Bits n → Bool) : Prop :=
  (∀ Δ : Finset (Bits n), Δ ⊆ suppFinset S → ∀ ψ : Bits n → ℂ,
      IsUnitVec ψ → (∀ x, ψ x ≠ 0 → x ∈ Δ) →
        (inner ψ (coreMatU g *ᵥ ψ)).re ≤ rayleighMax (expCoreMat κ S) Δ + ρ) ∧
    ((inner (unifState S) (expCoreMat κ S *ᵥ unifState S)).re - ρ ≤
      (inner (unifState S) (coreMatU g *ᵥ unifState S)).re)

/-- The entrywise concentration of the random core matrix `H Π_g H` around
its expectation `M^S`: a Hoeffding bound per entry plus a Gershgorin circle
bound, in Rayleigh-quotient form. The rate `κ` and the deviation `ρ` are
restricted to the nonnegative regime in which the strong-yes property is
stated (`κ ∈ [0, 1]`, `ρ ≥ 0`; the Hoeffding deviation bound is claimed for
nonnegative deviations only). Packaged as a hypothesis. -/
def matrixConcentrationProp : Prop := by
  classical
  exact ∀ (n ℓ : ℕ) (S : Fin ℓ → Bits n) (κ ρ : ℝ),
    0 ≤ κ → 0 ≤ ρ →
    (∑ U : Bits n → Bool, uWeight κ S U *
        (if concGood κ S ρ U then 0 else 1)) ≤
      2 * (ℓ : ℝ) ^ 2 * Real.exp (-ρ ^ 2 * 2 ^ n / (2 * (ℓ : ℝ) ^ 2))

/-- The `v` output blocks read from the first `v·n` work bits. -/
noncomputable def readSamples {w : ℕ} (z : Bits w) (v n : ℕ) : Fin v → Bits n :=
  fun k i => if h : k.val * n + i.val < w then z ⟨k.val * n + i.val, h⟩ else false

/-- The sampler success probability over the Strong distribution: the `v`
output blocks read from the work register are distinct and all in the
support of `S` (the left-hand side of the sampling upper bound). -/
noncomputable def samplerSuccess {n ℓ w T : ℕ} (κ : ℝ) (v : ℕ)
    (alg : QueryAlgorithm n w T) (init : QReg n w → ℂ) : ℝ :=
  ∑ S : Fin ℓ → Bits n, ∑ g : Bits n → Bool,
    strongWeight κ S g *
      measProb (runState alg g init (Fin.last T))
        (Finset.univ.filter fun r : QReg n w =>
          (∀ k : Fin v, readSamples r.2.2 v n k ∈ suppFinset S) ∧
            ∀ k₁ k₂ : Fin v, readSamples r.2.2 v n k₁ = readSamples r.2.2 v n k₂ → k₁ = k₂)

/-- The sampling probability upper bound from the bosonic
compressed-oracle analysis (for the parameter choice `κ = 1/10`). The
quantifier structure made explicit here follows the proof's requirements:
`v` a multiple of `4`, `T ≥ n`, and `2cT^13 ≤ ℓ^{1/10}` for the absolute
constant `c`. Packaged as a hypothesis. -/
def samplerUpperBoundProp : Prop :=
  ∃ c : ℝ, ∃ n₀ : ℕ, 0 < c ∧ ∀ (n ℓ w v T : ℕ),
    n₀ ≤ n → 1 ≤ ℓ → 4 ∣ v → (n : ℝ) ≤ T → 2 * c * (T : ℝ) ^ 13 ≤ (ℓ : ℝ) ^ (1 / 10 : ℝ) →
      ∀ (alg : QueryAlgorithm n w T) (init : QReg n w → ℂ), IsUnitVec init →
        samplerSuccess (ℓ := ℓ) (1 / 10) v alg init ≤
          2 * (4 * v * ((T : ℝ) ^ 30 + v * (T : ℝ) ^ 20) * Real.sqrt ℓ /
              (2 : ℝ) ^ ((n : ℝ) / 4)) ^ v +
            (((T : ℝ) ^ 4 / (ℓ : ℝ) ^ (1 / 32 : ℝ)) ^ v + Real.exp (-5 * T)) ^ 2

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.
-- @[checkpoint c8 difficulty=hard]
/-- The main theorem, in property-testing form with the QMA containment:
for every polynomial resource bound `a·n^a` there is a size threshold beyond
which (a) spectral Forrelation at gap `59/100` vs `57/100` has a
constant-query QMA verifier, and (b) every classical-witness query
algorithm within the bound misclassifies some instance. The QMA
amplification theorem, the matrix concentration, and the bosonic
compressed-oracle sampling upper bound are packaged as hypotheses. On the
QMA side the witness has `n` qubits (`qQ = n`), with all other
qubits pinned to `|0⟩` (`qmaAcceptProb`). -/
theorem qma_qcma_oracle_separation
    (hMW : mwAmplificationProp) (hConc : matrixConcentrationProp)
    (hUB : samplerUpperBoundProp) :
    ∃ C : ℝ, 0 < C ∧ ∀ a : ℕ, 0 < a → ∃ n₀ : ℕ, ∀ n : ℕ, n₀ ≤ n →
      ((∃ (wQ tQ : ℕ) (ver : QueryAlgorithm (n + 1) wQ tQ) (qQ : ℕ) (hqQ : qQ ≤ wQ),
          (tQ : ℝ) ≤ C ∧ qQ = n ∧
          (∀ f g : Bits n → Bool,
            ((59 : ℝ) / 100 ≤ sfVal f g →
              ∃ ψ, IsUnitVec ψ ∧ (2 : ℝ) / 3 ≤ qmaAcceptProb ver (mergeOracle f g) hqQ ψ) ∧
            (sfVal f g ≤ (57 : ℝ) / 100 →
              ∀ ψ, IsUnitVec ψ → qmaAcceptProb ver (mergeOracle f g) hqQ ψ ≤ (1 : ℝ) / 3))) ∧
        (∀ w t (alg : QueryAlgorithm (n + 1) w t) (q : ℕ),
          t ≤ a * n ^ a → q ≤ a * n ^ a → q ≤ w →
          ∃ f g : Bits n → Bool,
            ((59 : ℝ) / 100 ≤ sfVal f g ∧
                ∀ wit : Bits q,
                  acceptProb alg (mergeOracle f g) (classicInit (embedWit wit)) < (2 : ℝ) / 3) ∨
              (sfVal f g ≤ (57 : ℝ) / 100 ∧
                ∃ wit : Bits q,
                  (1 : ℝ) / 3 < acceptProb alg (mergeOracle f g) (classicInit (embedWit wit))))) := by
  -- CHECKPOINT qma_qcma_oracle_separation BEGIN
  sorry
  -- CHECKPOINT qma_qcma_oracle_separation END

end QmaQcmaOracle
