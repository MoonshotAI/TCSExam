/-
Statement layer for the **Fourier Entropy–Influence conjecture** (FEI):
there is a universal constant `C` such that every Boolean function
`f : {±1}ⁿ → {±1}` satisfies

    H(f̂²) ≤ C · I(f),

where `H(f̂²) = ∑_S f̂(S)² · log(1 / f̂(S)²)` is the Shannon entropy of the
squared Fourier spectrum (a probability distribution by Parseval) and
`I(f) = ∑ᵢ Infᵢ[f]` is the total influence, `Infᵢ[f]` being the probability
that flipping the `i`-th input bit changes the value of `f`.

Provenance. The conjecture was first raised by Friedgut–Kalai 1996 (*Every
monotone graph property has a sharp threshold*, Proc. Amer. Math. Soc.
124(10):2993–3002) in the study of monotone graph properties; it was
standardized under its present name by O'Donnell–Wright–Zhou (ICALP 2011,
*The Fourier Entropy–Influence Conjecture for certain classes of Boolean
functions*), who proved it for several function classes. It does not appear
in O'Donnell's textbook *Analysis of Boolean Functions*. Still open:
Xiao Han 2024 (*A New Bound for the Fourier-Entropy-Influence Conjecture*,
Combinatorica 45(1); arXiv:2312.08271) proves `H ≤ O(I(f) + ∑ₖ Iₖ(f)·log(1/Iₖ(f)))`
while treating FEI itself as unresolved, and arXiv:2511.07739 (2025) still
frames its p-biased results as progress towards FEI.

This file is the task's definition zone plus slot zone:
- The definition zone fixes the cube (`Cube n := Fin n → Bool`), the ±1
  embedding `pmOne`, characters `charFn`, Fourier coefficients `fourierCoeff`,
  the Fourier entropy `fourierEntropy`, influences `influence` /
  `totalInfluence`, and the predicate `IsBoolean`, together with a fully
  proved API: character orthogonality (`sum_charFn`, `sum_charFn_pointwise`),
  coefficient extraction (`fourierCoeff_charFn`), the Fourier expansion
  (`fourier_expansion`), Parseval (`sum_sq_fourierCoeff`,
  `sum_sq_fourierCoeff_isBoolean`), the probability form of influence
  (`influence_eq_card`), cube enumeration (`sum_cube_succ`, `sum_cube_zero`),
  and three concrete example functions (`dictator`, `parityFun`, `andTwo`)
  with their `IsBoolean` lemmas.
- The slot zone states the conjecture (`conj`) and its negation (`refuted`).
  Both proof bodies are left blank; proving either one scores full marks.

Fidelity notes (see `tests/reference/concept-ledger.md` of the packaged task):
1. Functions are `f : Cube n → ℝ` with the predicate `IsBoolean f` (values
  ±1); `pmOne` embeds `true ↦ 1`, `false ↦ −1` (convention shared with the
  open line's aaronson-ambainis package).
2. `fourierCoeff f S = 2⁻ⁿ ∑ₓ f(x)χ_S(x)` is the standard normalized
   coefficient; the entropy uses the natural logarithm — the universal
   constant `C` absorbs any change of log base. Zero-weight entropy terms
   vanish by the mathlib conventions `0⁻¹ = 0` and `log 0 = 0`.
3. `influence f i = 2⁻ⁿ ∑ₓ (f(x) − f(x^{⊕i}))² / 4` works for all real-valued
   `f`; for ±1-valued `f` it equals `Pr[f(x) ≠ f(x^{⊕i})]`
   (`influence_eq_card`), the paper's definition.
-/

import Mathlib

namespace FourierEntropyInfluence

/-! ## Cube points, the ±1 embedding, bit flips -/

/-- A point of the Boolean cube `{±1}ⁿ`, represented by its sign pattern. -/
abbrev Cube (n : ℕ) := Fin n → Bool

/-- The ±1 embedding of a Boolean: `true ↦ 1`, `false ↦ −1`. -/
def pmOne (b : Bool) : ℝ := if b then 1 else -1

theorem pmOne_mul_self (b : Bool) : pmOne b * pmOne b = 1 := by
  cases b <;> norm_num [pmOne]

theorem pmOne_ne_zero (b : Bool) : pmOne b ≠ 0 := by
  cases b <;> norm_num [pmOne]

theorem pmOne_not (b : Bool) : pmOne (!b) = -pmOne b := by
  cases b <;> norm_num [pmOne]

/-- The embedding of an equality test: `pmOne a · pmOne b = pmOne (a == b)`. -/
theorem pmOne_mul_pmOne (a b : Bool) : pmOne a * pmOne b = pmOne (a == b) := by
  cases a <;> cases b <;> norm_num [pmOne]

/-- Flip the `i`-th bit of a cube point (the paper's `x ↦ x^{⊕i}`). -/
def flipAt {n : ℕ} (x : Cube n) (i : Fin n) : Cube n :=
  Function.update x i (!(x i))

@[simp]
theorem flipAt_same {n : ℕ} (x : Cube n) (i : Fin n) : flipAt x i i = !(x i) := by
  simp [flipAt]

theorem flipAt_ne {n : ℕ} (x : Cube n) {i j : Fin n} (h : j ≠ i) :
    flipAt x i j = x j := by
  simp [flipAt, Function.update_of_ne h]

theorem flipAt_flipAt {n : ℕ} (x : Cube n) (i : Fin n) : flipAt (flipAt x i) i = x := by
  funext j
  by_cases h : j = i
  · subst h
    simp
  · simp [flipAt_ne _ h]

theorem flipAt_ne_self {n : ℕ} (x : Cube n) (i : Fin n) : flipAt x i ≠ x := by
  intro h
  have h2 := congrFun h i
  simp at h2

/-- The number of cube points, as a real: `|{±1}ⁿ| = 2ⁿ`. -/
theorem card_cube (n : ℕ) : (Fintype.card (Cube n) : ℝ) = (2 : ℝ) ^ n := by
  have h : Fintype.card (Cube n) = 2 ^ n := by
    rw [Fintype.card_pi, Fintype.card_bool, Finset.prod_const, Finset.card_univ,
      Fintype.card_fin]
  rw [h]
  push_cast
  ring

/-- The equivalence between the `(n+1)`-cube and `Bool ×` the `n`-cube,
splitting off the first bit. -/
def cubeSuccEquiv {n : ℕ} : Cube (n + 1) ≃ Bool × Cube n where
  toFun x := (x 0, Fin.tail x)
  invFun p := Fin.cons p.1 p.2
  left_inv x := Fin.cons_self_tail x
  right_inv p := by
    show ((Fin.cons p.1 p.2 : Cube (n + 1)) 0, (Fin.tail (Fin.cons p.1 p.2 : Cube (n + 1)) :
      Cube n)) = p
    rw [Fin.cons_zero, Fin.tail_cons]

/-- Summing over the cube splits off the first bit. Useful for computations
on concrete small cubes. -/
theorem sum_cube_succ {n : ℕ} (g : Cube (n + 1) → ℝ) :
    (∑ x : Cube (n + 1), g x) =
      (∑ x : Cube n, g (Fin.cons false x)) + (∑ x : Cube n, g (Fin.cons true x)) := by
  rw [← Equiv.sum_comp cubeSuccEquiv.symm g, Fintype.sum_prod_type, Fintype.sum_bool,
    add_comm]
  simp [cubeSuccEquiv]

/-- The 0-dimensional cube has a single point. -/
theorem sum_cube_zero (g : Cube 0 → ℝ) :
    (∑ x : Cube 0, g x) = g (fun i => i.elim0) := by
  apply Finset.sum_eq_single
  · intro b _ hb
    exact absurd (funext fun i => i.elim0) hb
  · intro h
    exact absurd (Finset.mem_univ _) h

/-! ## Characters and their orthogonality -/

/-- The Fourier character `χ_S(x) = ∏_{i ∈ S} xᵢ`. -/
def charFn {n : ℕ} (S : Finset (Fin n)) (x : Cube n) : ℝ :=
  ∏ i ∈ S, pmOne (x i)

@[simp]
theorem charFn_empty {n : ℕ} (x : Cube n) : charFn ∅ x = 1 := by
  simp [charFn]

theorem charFn_singleton {n : ℕ} (i : Fin n) (x : Cube n) :
    charFn {i} x = pmOne (x i) := by
  simp [charFn]

theorem charFn_pair {n : ℕ} {i j : Fin n} (h : i ≠ j) (x : Cube n) :
    charFn {i, j} x = pmOne (x i) * pmOne (x j) := by
  simp [charFn, Finset.prod_insert (Finset.mem_singleton.not.mpr h)]

theorem charFn_sq {n : ℕ} (S : Finset (Fin n)) (x : Cube n) : (charFn S x) ^ 2 = 1 := by
  rw [sq, charFn, ← Finset.prod_mul_distrib]
  exact Finset.prod_eq_one fun i _ => pmOne_mul_self (x i)

theorem charFn_union {n : ℕ} {S T : Finset (Fin n)} (h : Disjoint S T) (x : Cube n) :
    charFn (S ∪ T) x = charFn S x * charFn T x := by
  simp [charFn, Finset.prod_union h]

/-- Characters multiply to the character of the symmetric difference
`(S \ T) ∪ (T \ S)`. -/
theorem charFn_mul {n : ℕ} (S T : Finset (Fin n)) (x : Cube n) :
    charFn S x * charFn T x = charFn ((S \ T) ∪ (T \ S)) x := by
  have hS : S = (S \ T) ∪ (S ∩ T) := (Finset.sdiff_union_inter S T).symm
  have hT : T = (T \ S) ∪ (S ∩ T) := by
    rw [Finset.inter_comm S T]
    exact (Finset.sdiff_union_inter T S).symm
  have hd1 : Disjoint (S \ T) (S ∩ T) := Finset.disjoint_sdiff_inter _ _
  have hd2 : Disjoint (T \ S) (S ∩ T) := by
    rw [Finset.inter_comm S T]
    exact Finset.disjoint_sdiff_inter _ _
  have hd3 : Disjoint (S \ T) (T \ S) := by
    rw [Finset.disjoint_left]
    intro i hi hj
    exact (Finset.mem_sdiff.mp hi).2 (Finset.mem_sdiff.mp hj).1
  have eS : charFn S x = charFn (S \ T) x * charFn (S ∩ T) x := by
    conv_lhs => rw [hS]
    rw [charFn_union hd1]
  have eT : charFn T x = charFn (T \ S) x * charFn (S ∩ T) x := by
    conv_lhs => rw [hT]
    rw [charFn_union hd2]
  calc charFn S x * charFn T x
      = (charFn (S \ T) x * charFn (S ∩ T) x) * (charFn (T \ S) x * charFn (S ∩ T) x) := by
        rw [eS, eT]
    _ = charFn (S \ T) x * charFn (T \ S) x * (charFn (S ∩ T) x) ^ 2 := by ring
    _ = charFn (S \ T) x * charFn (T \ S) x := by rw [charFn_sq, mul_one]
    _ = charFn ((S \ T) ∪ (T \ S)) x := (charFn_union hd3 x).symm

/-- Flipping a bit of `S` negates the character. -/
theorem charFn_flipAt {n : ℕ} {S : Finset (Fin n)} {i : Fin n} (hi : i ∈ S) (x : Cube n) :
    charFn S (flipAt x i) = -charFn S x := by
  have h1 : charFn S (flipAt x i) =
      pmOne (flipAt x i i) * ∏ j ∈ S.erase i, pmOne (flipAt x i j) :=
    (Finset.mul_prod_erase S (fun j => pmOne (flipAt x i j)) hi).symm
  have h2 : charFn S x = pmOne (x i) * ∏ j ∈ S.erase i, pmOne (x j) :=
    (Finset.mul_prod_erase S (fun j => pmOne (x j)) hi).symm
  rw [h1, h2, flipAt_same, pmOne_not, neg_mul]
  congr 1
  congr 1
  apply Finset.prod_congr rfl
  intro j hj
  rw [flipAt_ne x (Finset.ne_of_mem_erase hj)]

/-- Character orthogonality: the average of `χ_S` over the cube is `1` for
`S = ∅` and `0` otherwise. -/
theorem sum_charFn {n : ℕ} (S : Finset (Fin n)) :
    (∑ x : Cube n, charFn S x) = if S = ∅ then (2 : ℝ) ^ n else 0 := by
  by_cases hS : S = ∅
  · subst hS
    rw [if_pos rfl]
    simp [charFn_empty, Finset.sum_const, nsmul_eq_mul]
  · rw [if_neg hS]
    obtain ⟨i, hi⟩ := Finset.nonempty_of_ne_empty hS
    apply Finset.sum_involution (fun x _ => flipAt x i)
    · intro x _
      rw [charFn_flipAt hi x, add_neg_cancel]
    · intro x _ _
      exact flipAt_ne_self x i
    · intro x _
      exact Finset.mem_univ _
    · intro x _
      exact flipAt_flipAt x i

/-- Pointwise product of one character at two points is a character of the
equality pattern. -/
theorem charFn_mul_charFn {n : ℕ} (S : Finset (Fin n)) (x y : Cube n) :
    charFn S x * charFn S y = charFn S (fun i => (x i == y i)) := by
  rw [charFn, charFn, charFn, ← Finset.prod_mul_distrib]
  exact Finset.prod_congr rfl fun i _ => pmOne_mul_pmOne (x i) (y i)

/-- The dual orthogonality: summing `χ_S(z)` over all `S` gives `2ⁿ` when `z`
is all-true and `0` otherwise. -/
theorem sum_charFn_pointwise {n : ℕ} (z : Cube n) :
    ∑ S : Finset (Fin n), charFn S z = if (∀ i, z i) then (2 : ℝ) ^ n else 0 := by
  have key : (∑ S : Finset (Fin n), charFn S z) = ∏ i : Fin n, (pmOne (z i) + 1) := by
    rw [Finset.prod_add, ← Finset.powerset_univ]
    apply Finset.sum_congr rfl
    intro t _
    rw [Finset.prod_const_one, mul_one]
    rfl
  rw [key]
  by_cases hz : ∀ i, z i
  · rw [if_pos hz]
    have h2 : ∀ i : Fin n, pmOne (z i) + 1 = 2 := by
      intro i
      rw [hz i]
      norm_num [pmOne]
    rw [Finset.prod_congr rfl (fun i _ => h2 i), Finset.prod_const, Finset.card_univ,
      Fintype.card_fin]
  · rw [if_neg hz]
    obtain ⟨i, hi⟩ := not_forall.mp hz
    apply Finset.prod_eq_zero (Finset.mem_univ i)
    cases h : z i
    · norm_num [pmOne]
    · exact absurd h hi

/-! ## Fourier coefficients -/

/-- The Fourier coefficient `f̂(S) = 2⁻ⁿ ∑ₓ f(x)χ_S(x)`. -/
noncomputable def fourierCoeff {n : ℕ} (f : Cube n → ℝ) (S : Finset (Fin n)) : ℝ :=
  (∑ x : Cube n, f x * charFn S x) / 2 ^ n

/-- Coefficient extraction: the spectrum of a character is a point mass. -/
theorem fourierCoeff_charFn {n : ℕ} (S T : Finset (Fin n)) :
    fourierCoeff (charFn S) T = if S = T then 1 else 0 := by
  have hiff : (S \ T) ∪ (T \ S) = ∅ ↔ S = T := by
    constructor
    · intro he
      ext i
      constructor
      · intro hiS
        by_contra hiT
        exact Finset.notMem_empty i
          (he ▸ Finset.mem_union_left _ (Finset.mem_sdiff.mpr ⟨hiS, hiT⟩))
      · intro hiT
        by_contra hiS
        exact Finset.notMem_empty i
          (he ▸ Finset.mem_union_right _ (Finset.mem_sdiff.mpr ⟨hiT, hiS⟩))
    · intro h
      rw [h, Finset.sdiff_self, Finset.union_empty]
  rw [fourierCoeff]
  rw [Finset.sum_congr rfl (fun x _ => charFn_mul S T x), sum_charFn]
  by_cases h : S = T
  · rw [if_pos (hiff.mpr h), if_pos h]
    exact div_self (pow_ne_zero _ (by norm_num : (2 : ℝ) ≠ 0))
  · rw [if_neg (fun he => h (hiff.mp he)), if_neg h, zero_div]

theorem fourierCoeff_add {n : ℕ} (f g : Cube n → ℝ) (S : Finset (Fin n)) :
    fourierCoeff (fun x => f x + g x) S = fourierCoeff f S + fourierCoeff g S := by
  rw [fourierCoeff, fourierCoeff, fourierCoeff, ← add_div, ← Finset.sum_add_distrib]
  congr 1
  apply Finset.sum_congr rfl
  intro x _
  ring

theorem fourierCoeff_smul {n : ℕ} (c : ℝ) (f : Cube n → ℝ) (S : Finset (Fin n)) :
    fourierCoeff (fun x => c * f x) S = c * fourierCoeff f S := by
  rw [fourierCoeff, fourierCoeff, ← mul_div_assoc, Finset.mul_sum]
  congr 1
  apply Finset.sum_congr rfl
  intro x _
  ring

theorem fourierCoeff_neg {n : ℕ} (f : Cube n → ℝ) (S : Finset (Fin n)) :
    fourierCoeff (fun x => -f x) S = -fourierCoeff f S := by
  have h : (fun x : Cube n => -f x) = fun x => (-1 : ℝ) * f x := by
    funext x
    simp
  rw [h, fourierCoeff_smul]
  simp

/-- The Fourier expansion: `f` is the sum of its coefficients times the
characters. -/
theorem fourier_expansion {n : ℕ} (f : Cube n → ℝ) (x : Cube n) :
    f x = ∑ S : Finset (Fin n), fourierCoeff f S * charFn S x := by
  have step : ∀ S : Finset (Fin n), fourierCoeff f S * charFn S x =
      (∑ y : Cube n, f y * (charFn S y * charFn S x)) / 2 ^ n := by
    intro S
    rw [fourierCoeff, div_mul_eq_mul_div, Finset.sum_mul]
    congr 1
    apply Finset.sum_congr rfl
    intro y _
    rw [mul_assoc]
  rw [Finset.sum_congr rfl (fun S _ => step S), ← Finset.sum_div, Finset.sum_comm]
  have inner : ∀ y : Cube n,
      (∑ S : Finset (Fin n), f y * (charFn S y * charFn S x)) =
        f y * (if y = x then (2 : ℝ) ^ n else 0) := by
    intro y
    rw [← Finset.mul_sum]
    congr 1
    rw [Finset.sum_congr rfl (fun S _ => charFn_mul_charFn S y x), sum_charFn_pointwise]
    have hcond : (∀ i, (y i == x i)) ↔ y = x := by
      rw [funext_iff]
      exact forall_congr' fun i => beq_iff_eq
    by_cases hyx : y = x
    · rw [if_pos hyx, if_pos (hcond.mpr hyx)]
    · rw [if_neg hyx, if_neg (fun h => hyx (hcond.mp h))]
  rw [Finset.sum_congr rfl (fun y _ => inner y)]
  rw [Finset.sum_eq_single x]
  · rw [if_pos rfl, mul_div_cancel_right₀ _ (pow_ne_zero _ (by norm_num : (2 : ℝ) ≠ 0))]
  · intro y _ hyx
    rw [if_neg hyx, mul_zero]
  · intro h
    exact absurd (Finset.mem_univ x) h

/-- Parseval: the spectrum has the same energy as the function. -/
theorem sum_sq_fourierCoeff {n : ℕ} (f : Cube n → ℝ) :
    ∑ S : Finset (Fin n), (fourierCoeff f S) ^ 2 = (∑ x : Cube n, (f x) ^ 2) / 2 ^ n := by
  suffices h : (∑ x : Cube n, (f x) ^ 2) =
      2 ^ n * ∑ S : Finset (Fin n), (fourierCoeff f S) ^ 2 by
    rw [h, mul_div_cancel_left₀ _ (pow_ne_zero _ (by norm_num : (2 : ℝ) ≠ 0))]
  calc (∑ x : Cube n, (f x) ^ 2)
      = ∑ x : Cube n, f x * f x := by
        apply Finset.sum_congr rfl
        intro x _
        rw [sq]
    _ = ∑ x : Cube n, (∑ S : Finset (Fin n), fourierCoeff f S * charFn S x) * f x := by
        apply Finset.sum_congr rfl
        intro x _
        rw [← fourier_expansion f x]
    _ = ∑ x : Cube n, ∑ S : Finset (Fin n), fourierCoeff f S * charFn S x * f x := by
        apply Finset.sum_congr rfl
        intro x _
        rw [Finset.sum_mul]
    _ = ∑ S : Finset (Fin n), ∑ x : Cube n, fourierCoeff f S * charFn S x * f x :=
        Finset.sum_comm
    _ = ∑ S : Finset (Fin n), fourierCoeff f S * (∑ x : Cube n, f x * charFn S x) := by
        apply Finset.sum_congr rfl
        intro S _
        rw [Finset.mul_sum]
        apply Finset.sum_congr rfl
        intro x _
        ring
    _ = ∑ S : Finset (Fin n), fourierCoeff f S * (2 ^ n * fourierCoeff f S) := by
        apply Finset.sum_congr rfl
        intro S _
        congr 1
        rw [fourierCoeff, mul_comm (2 ^ n : ℝ) _,
          div_mul_cancel₀ _ (pow_ne_zero _ (by norm_num : (2 : ℝ) ≠ 0))]
    _ = 2 ^ n * ∑ S : Finset (Fin n), (fourierCoeff f S) ^ 2 := by
        rw [Finset.mul_sum]
        apply Finset.sum_congr rfl
        intro S _
        ring

/-! ## Boolean-valued functions, entropy, influence -/

/-- `f` is Boolean-valued: every value is `±1`. -/
def IsBoolean {n : ℕ} (f : Cube n → ℝ) : Prop := ∀ x, f x = 1 ∨ f x = -1

/-- One term of the Shannon entropy: `p · log(1/p)`. Vanishes at `p = 0` by
the mathlib conventions `0⁻¹ = 0`, `log 0 = 0`. -/
noncomputable def entropyTerm (p : ℝ) : ℝ := p * Real.log p⁻¹

/-- The Fourier entropy `H(f̂²) = ∑_S f̂(S)² · log(1 / f̂(S)²)` (natural log;
the universal constant of the conjecture absorbs any base change). -/
noncomputable def fourierEntropy {n : ℕ} (f : Cube n → ℝ) : ℝ :=
  ∑ S : Finset (Fin n), entropyTerm ((fourierCoeff f S) ^ 2)

/-- Influence of coordinate `i`: `Infᵢ[f] = 2⁻ⁿ ∑ₓ (f(x) − f(x^{⊕i}))² / 4`.
For ±1-valued `f` this is `Prₓ[f(x) ≠ f(x^{⊕i})]` (`influence_eq_card`). -/
noncomputable def influence {n : ℕ} (f : Cube n → ℝ) (i : Fin n) : ℝ :=
  (∑ x : Cube n, (f x - f (flipAt x i)) ^ 2) / (4 * 2 ^ n)

/-- Total influence `I(f) = ∑ᵢ Infᵢ[f]`. -/
noncomputable def totalInfluence {n : ℕ} (f : Cube n → ℝ) : ℝ :=
  ∑ i : Fin n, influence f i

/-- Parseval for Boolean functions: `f̂²` is a probability distribution. -/
theorem sum_sq_fourierCoeff_isBoolean {n : ℕ} {f : Cube n → ℝ} (hf : IsBoolean f) :
    ∑ S : Finset (Fin n), (fourierCoeff f S) ^ 2 = 1 := by
  rw [sum_sq_fourierCoeff]
  have h : ∀ x : Cube n, (f x) ^ 2 = 1 := by
    intro x
    rcases hf x with hx | hx <;> rw [hx] <;> norm_num
  rw [Finset.sum_congr rfl (fun x _ => h x), Finset.sum_const, nsmul_eq_mul,
    Finset.card_univ, card_cube, mul_one]
  exact div_self (pow_ne_zero _ (by norm_num : (2 : ℝ) ≠ 0))

-- The probability form of influence for Boolean functions:
-- `Infᵢ[f] = Prₓ[f(x) ≠ f(x^{⊕i})]`.
open Classical in
theorem influence_eq_card {n : ℕ} {f : Cube n → ℝ} (hf : IsBoolean f) (i : Fin n) :
    influence f i =
      ((Finset.univ.filter fun x : Cube n => f x ≠ f (flipAt x i)).card : ℝ) / 2 ^ n := by
  rw [influence]
  have hterm : ∀ x : Cube n, (f x - f (flipAt x i)) ^ 2 =
      if f x ≠ f (flipAt x i) then (4 : ℝ) else 0 := by
    intro x
    rcases hf x with hx | hx <;> rcases hf (flipAt x i) with hy | hy <;>
      simp [hx, hy] <;> norm_num
  rw [Finset.sum_congr rfl (fun x _ => hterm x), Finset.sum_ite, Finset.sum_const_zero,
    add_zero, Finset.sum_const, nsmul_eq_mul]
  field_simp

/-! ## The conjecture -/

/-- The Fourier Entropy–Influence conjecture: some universal constant `C`
bounds the Fourier entropy of every Boolean function by `C` times its total
influence. -/
def FeiConjecture : Prop :=
  ∃ C : ℝ, 0 < C ∧ ∀ {n : ℕ} (f : Cube n → ℝ), IsBoolean f →
    fourierEntropy f ≤ C * totalInfluence f

/-! ## Checkpoint instances -/

/-- The dictator on coordinate `i`: `x ↦ xᵢ` in ±1. -/
def dictator {n : ℕ} (i : Fin n) : Cube n → ℝ := fun x => pmOne (x i)

theorem dictator_isBoolean {n : ℕ} (i : Fin n) : IsBoolean (dictator i) := by
  intro x
  cases hx : x i <;> simp [dictator, pmOne, hx]

/-- The parity function: the product of all coordinates, `χ_[n]`. -/
def parityFun (n : ℕ) : Cube n → ℝ := charFn Finset.univ

theorem parityFun_isBoolean (n : ℕ) : IsBoolean (parityFun n) := by
  intro x
  have h := charFn_sq (Finset.univ : Finset (Fin n)) x
  exact sq_eq_one_iff.mp h

/-- `AND` of two bits, in ±1: `1` iff both bits are true. -/
def andTwo : Cube 2 → ℝ := fun x => if x 0 ∧ x 1 then 1 else -1

theorem andTwo_isBoolean : IsBoolean andTwo := by
  intro x
  cases h0 : x 0 <;> cases h1 : x 1 <;> simp [andTwo, h0, h1]

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

/-! ## Slot zone: the conjecture and its negation

Prove **either** `conj` (the conjecture) **or** `refuted` (its negation) for
full credit.  There is no partial credit: auxiliary results are welcome but
do not affect the score. -/

-- @[slot main]
/-- **The Fourier Entropy–Influence conjecture**: there is a universal
constant `C` such that `H(f̂²) ≤ C · I(f)` for every Boolean function `f`. -/
theorem conj : FeiConjecture := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

-- @[slot main]
/-- The negation of the FEI conjecture: no universal constant works — for
every `C > 0` some Boolean function has `H(f̂²) > C · I(f)`. -/
theorem refuted : ¬ FeiConjecture := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

end FourierEntropyInfluence
