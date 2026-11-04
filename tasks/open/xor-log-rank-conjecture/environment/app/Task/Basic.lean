/-
Statement layer for the XOR log-rank conjecture (Montanaro–Osborne, *On the
communication complexity of XOR functions*, arXiv:0909.3392, 2009; parity
decision tree form and best known bounds: Tsang–Wong–Xie–Zhang, *Fourier
sparsity, spectral norm, and the Log-rank conjecture*, FOCS 2013,
arXiv:1304.1245):

There is a universal constant `c` such that every Boolean function
`f : {±1}ⁿ → {±1}` has parity decision tree depth (each query asks for the
parity of an arbitrary subset of the coordinates) at most `(log sp(f))^c`,
where `sp(f)` is the Fourier sparsity of `f` — the number of its nonzero
Fourier coefficients. Equivalently, the XOR communication problem
`f⊕(x, y) = f(x ⊕ y)` satisfies the log-rank conjecture, since the rank of
its communication matrix equals `sp(f)`. Best known upper bound:
`PDT(f) = O(√sp(f))` (Tsang–Wong–Xie–Zhang 2013). For the
communication form, Sudakov–Tomon 2023 (arXiv:2311.18524, *Matrix
discrepancy and the log-rank conjecture*) modestly improved Lovett's
bound to `D^CC = O(√rank)`. Status: open.

This file is the task's definition zone plus slot zone:
- The definition zone fixes the Boolean cube `Fin n → Bool` with the ±1
  embedding `pmOne`, the Fourier–Walsh characters `chi S`, Fourier
  coefficients `fourierCoeff` over ℚ (with a parallel kernel-computable ℤ
  layer `fourierNum`), the Fourier sparsity `sparsity f`, parity queries and
  parity decision trees (`ParityTree`) with their depth measure
  `ComputesInDepth`, and the conjecture predicate `Conjecture`. The API
  lemmas (character orthonormality, Fourier inversion, Parseval, the
  query–character bridge `pmOne_parityQuery`, the ℤ/ℚ sparsity bridge
  `sparsity_eq_filter_num`) are fully proved.
- The slot zone states the conjecture (`conj`) and its negation (`refuted`).
  Both proof bodies are left blank.

Fidelity notes (see `tests/reference/concept-ledger.md` of the packaged task):
1. Following TWXZ (arXiv:1304.1245), the conjecture is stated for the parity
   decision tree model (their results hold for it, and it is at least as
   strong as the communication version up to a factor of 2). Points of the
   cube are `Fin n → Bool` with `true ↦ +1`, `false ↦ -1` under `pmOne`; a
   parity query on `S` reports whether `χ_S(x) = +1`.
2. The literature writes `PDT(f) = log^{O(1)} sp(f)` (equivalently `O(log^c
   sp(f))`). We render this as `(d : ℝ) ≤ (1 + Real.logb 2 (sparsity f))^c`:
   the `1 +` guards the degenerate case `sp(f) = 1` where `log sp = 0` (such
   functions are exactly `±χ_S`, of depth ≤ 1), and for `sp ≥ 2` the two
   forms differ only by the constant factor absorbed by the big-O. The
   exponent `c` is a natural number, which is equivalent to allowing a real
   exponent (round up); the base-2 logarithm is immaterial for the same
   reason.
3. `PDT(f) ≤ B` is rendered existentially as `∃ d ≤ B, ComputesInDepth f d`
   (a parity tree of depth ≤ d computing `f`), avoiding a minimum over the
   infinite tree type.
-/

import Mathlib

namespace XorLogRank

open scoped symmDiff

/-! ## The ±1 embedding and Fourier–Walsh characters -/

/-- The ±1 embedding of a Boolean into ℚ: `true ↦ 1`, `false ↦ −1`. -/
def pmOne (b : Bool) : ℚ := if b then 1 else -1

@[simp] theorem pmOne_true : pmOne true = 1 := rfl

@[simp] theorem pmOne_false : pmOne false = -1 := rfl

theorem pmOne_sq (b : Bool) : pmOne b ^ 2 = 1 := by cases b <;> simp [pmOne]

theorem pmOne_not (b : Bool) : pmOne (!b) = -pmOne b := by cases b <;> simp [pmOne]

theorem pmOne_ne_zero (b : Bool) : pmOne b ≠ 0 := by cases b <;> simp [pmOne]

theorem pmOne_inj {a b : Bool} (h : pmOne a = pmOne b) : a = b := by
  cases a <;> cases b <;> first | rfl | norm_num [pmOne] at h

/-- `Bool.xor` in the ±1 encoding carries a sign: with `true ↦ +1`, xor is the
negated product. -/
theorem pmOne_xor (a b : Bool) : pmOne (a ^^ b) = -(pmOne a * pmOne b) := by
  cases a <;> cases b <;> simp [pmOne]

theorem pmOne_decide (P : Prop) [Decidable P] :
    pmOne (decide P) = if P then (1 : ℚ) else -1 := by
  by_cases h : P
  · have hd : decide P = true := by simp [h]
    rw [hd, if_pos h]
    rfl
  · have hd : decide P = false := by simp [h]
    rw [hd, if_neg h]
    rfl

/-- The Fourier–Walsh character `χ_S` on the Boolean cube:
`χ_S(x) = ∏_{i ∈ S} (±1 of x i)`. -/
def chi {n : ℕ} (S : Finset (Fin n)) (x : Fin n → Bool) : ℚ :=
  ∏ i ∈ S, pmOne (x i)

@[simp] theorem chi_empty {n : ℕ} (x : Fin n → Bool) : chi ∅ x = 1 := by simp [chi]

theorem chi_singleton {n : ℕ} (i : Fin n) (x : Fin n → Bool) :
    chi {i} x = pmOne (x i) := by simp [chi]

/-- `χ_S` is the product of the singleton characters. -/
theorem chi_eq_prod_singleton {n : ℕ} (U : Finset (Fin n)) (x : Fin n → Bool) :
    chi U x = ∏ i ∈ U, chi {i} x := by
  refine Finset.prod_congr rfl fun i _ => ?_
  rw [chi_singleton]

/-- Character multiplication: `χ_S · χ_T = χ_{S △ T}`. -/
theorem chi_mul {n : ℕ} (S T : Finset (Fin n)) (x : Fin n → Bool) :
    chi S x * chi T x = chi (S ∆ T) x := by
  have hS : S = (S \ T) ∪ (S ∩ T) := (Finset.sdiff_union_inter S T).symm
  have hT : T = (T \ S) ∪ (S ∩ T) := by
    rw [Finset.inter_comm]; exact (Finset.sdiff_union_inter T S).symm
  have hd₁ : Disjoint (S \ T) (S ∩ T) :=
    Finset.sdiff_disjoint.mono_right Finset.inter_subset_right
  have hd₂ : Disjoint (T \ S) (S ∩ T) :=
    Finset.sdiff_disjoint.mono_right Finset.inter_subset_left
  have hd₃ : Disjoint (S \ T) (T \ S) :=
    Finset.disjoint_sdiff.mono_left Finset.sdiff_subset
  have eS : chi S x = (∏ i ∈ S \ T, pmOne (x i)) * (∏ i ∈ S ∩ T, pmOne (x i)) := by
    show (∏ i ∈ S, pmOne (x i)) = _
    rw [← Finset.prod_union hd₁, ← hS]
  have eT : chi T x = (∏ i ∈ T \ S, pmOne (x i)) * (∏ i ∈ S ∩ T, pmOne (x i)) := by
    show (∏ i ∈ T, pmOne (x i)) = _
    rw [← Finset.prod_union hd₂, ← hT]
  calc chi S x * chi T x
      = (∏ i ∈ S \ T, pmOne (x i)) * (∏ i ∈ T \ S, pmOne (x i)) *
          ((∏ i ∈ S ∩ T, pmOne (x i)) * (∏ i ∈ S ∩ T, pmOne (x i))) := by
        rw [eS, eT]; ring
    _ = (∏ i ∈ S \ T, pmOne (x i)) * (∏ i ∈ T \ S, pmOne (x i)) := by
        rw [← Finset.prod_mul_distrib]
        simp only [← pow_two, pmOne_sq, Finset.prod_const_one, mul_one]
    _ = chi (S ∆ T) x := by
        show (∏ i ∈ S \ T, pmOne (x i)) * (∏ i ∈ T \ S, pmOne (x i)) =
          ∏ i ∈ S ∆ T, pmOne (x i)
        rw [← Finset.prod_union hd₃, Finset.symmDiff_def]

theorem chi_ne_zero {n : ℕ} (S : Finset (Fin n)) (x : Fin n → Bool) : chi S x ≠ 0 := by
  rw [chi, Finset.prod_ne_zero_iff]
  exact fun i _ => pmOne_ne_zero (x i)

/-- Uniform expectation over the Boolean cube. -/
def cubeAvg {n : ℕ} (f : (Fin n → Bool) → ℚ) : ℚ :=
  (∑ x : Fin n → Bool, f x) / 2 ^ n

theorem cubeAvg_add {n : ℕ} (f g : (Fin n → Bool) → ℚ) :
    cubeAvg (fun x => f x + g x) = cubeAvg f + cubeAvg g := by
  unfold cubeAvg
  rw [← add_div]
  congr 1
  exact Finset.sum_add_distrib

theorem cubeAvg_neg {n : ℕ} (f : (Fin n → Bool) → ℚ) :
    cubeAvg (fun x => -f x) = -cubeAvg f := by
  show (∑ x : Fin n → Bool, -f x) / 2 ^ n = -((∑ x : Fin n → Bool, f x) / 2 ^ n)
  rw [Finset.sum_neg_distrib, neg_div]

theorem cubeAvg_smul {n : ℕ} (c : ℚ) (f : (Fin n → Bool) → ℚ) :
    cubeAvg (fun x => c * f x) = c * cubeAvg f := by
  show (∑ x : Fin n → Bool, c * f x) / 2 ^ n =
    c * ((∑ x : Fin n → Bool, f x) / 2 ^ n)
  rw [mul_div_assoc', Finset.mul_sum]

/-- The constant-1 function averages to 1. -/
theorem cubeAvg_one {n : ℕ} : cubeAvg (fun (_ : Fin n → Bool) => (1 : ℚ)) = 1 := by
  show (∑ _x : Fin n → Bool, (1 : ℚ)) / 2 ^ n = 1
  rw [Finset.sum_const, Finset.card_univ, nsmul_eq_mul, mul_one,
    Fintype.card_fun, Fintype.card_bool, Fintype.card_fin, Nat.cast_pow, Nat.cast_ofNat]
  exact div_self (pow_ne_zero _ (by norm_num : (2 : ℚ) ≠ 0))

/-- Character orthonormality, first form: `E[χ_U] = [U = ∅]`. -/
theorem cubeAvg_chi {n : ℕ} (U : Finset (Fin n)) :
    cubeAvg (chi U) = if U = ∅ then 1 else 0 := by
  by_cases hU : U = ∅
  · rw [if_pos hU, hU]
    simp [cubeAvg, chi]
  · rw [if_neg hU]
    obtain ⟨i₀, hi₀⟩ := Finset.nonempty_of_ne_empty hU
    have hsplit : ∀ y : Fin n → Bool,
        chi U y = pmOne (y i₀) * ∏ i ∈ U.erase i₀, pmOne (y i) := by
      intro y
      unfold chi
      conv_lhs => rw [← Finset.insert_erase hi₀]
      rw [Finset.prod_insert (Finset.notMem_erase _ _)]
    have hsum : ∑ x : Fin n → Bool, chi U x = 0 := by
      apply Finset.sum_involution (fun (x : Fin n → Bool) _ => Function.update x i₀ (!x i₀))
      · intro x _
        rw [hsplit x, hsplit (Function.update x i₀ (!x i₀))]
        have hprod : (∏ i ∈ U.erase i₀, pmOne ((Function.update x i₀ (!x i₀)) i)) =
            ∏ i ∈ U.erase i₀, pmOne (x i) := by
          refine Finset.prod_congr rfl fun i hi => ?_
          rw [Function.update_apply, if_neg (Finset.ne_of_mem_erase hi)]
        rw [hprod, Function.update_apply, if_pos rfl, pmOne_not]
        ring
      · intro x _ _ hEq
        have hne : (!x i₀) ≠ x i₀ := by cases x i₀ <;> decide
        have h1 := congrFun hEq i₀
        simp only [Function.update_apply, if_true] at h1
        exact hne h1
      · intro x _
        exact Finset.mem_univ _
      · intro x _
        funext j
        simp only [Function.update_apply]
        by_cases hj : j = i₀
        · subst hj
          simp [Bool.not_not]
        · simp [hj]
    rw [cubeAvg, hsum, zero_div]

/-- Character orthonormality: `E[χ_S · χ_T] = [S = T]`. -/
theorem cubeAvg_chi_mul {n : ℕ} (S T : Finset (Fin n)) :
    cubeAvg (fun x => chi S x * chi T x) = if S = T then 1 else 0 := by
  have h : (fun x => chi S x * chi T x) = fun x => chi (S ∆ T) x :=
    funext fun x => chi_mul S T x
  rw [h, cubeAvg_chi]
  simp only [Finset.symmDiff_eq_empty]

/-- The Fourier coefficient `f̂(S) = E[f · χ_S]` (over ℚ). -/
def fourierCoeff {n : ℕ} (f : (Fin n → Bool) → ℚ) (S : Finset (Fin n)) : ℚ :=
  cubeAvg fun x => f x * chi S x

theorem fourierCoeff_add {n : ℕ} (f g : (Fin n → Bool) → ℚ) (S : Finset (Fin n)) :
    fourierCoeff (fun x => f x + g x) S = fourierCoeff f S + fourierCoeff g S := by
  show cubeAvg (fun x => (f x + g x) * chi S x) =
    cubeAvg (fun x => f x * chi S x) + cubeAvg (fun x => g x * chi S x)
  rw [show (fun x => (f x + g x) * chi S x) = fun x => f x * chi S x + g x * chi S x
      from funext fun x => add_mul _ _ _, cubeAvg_add]

theorem fourierCoeff_neg {n : ℕ} (f : (Fin n → Bool) → ℚ) (S : Finset (Fin n)) :
    fourierCoeff (fun x => -f x) S = -fourierCoeff f S := by
  show cubeAvg (fun x => -f x * chi S x) = -cubeAvg (fun x => f x * chi S x)
  rw [show (fun x => -f x * chi S x) = fun x => -(f x * chi S x)
      from funext fun x => neg_mul _ _, cubeAvg_neg]

theorem fourierCoeff_smul {n : ℕ} (c : ℚ) (f : (Fin n → Bool) → ℚ) (S : Finset (Fin n)) :
    fourierCoeff (fun x => c * f x) S = c * fourierCoeff f S := by
  show cubeAvg (fun x => (c * f x) * chi S x) = c * cubeAvg (fun x => f x * chi S x)
  rw [show (fun x => (c * f x) * chi S x) = fun x => c * (f x * chi S x)
      from funext fun x => mul_assoc _ _ _, cubeAvg_smul]

/-- Diagonal of the character kernel: `∑_S χ_S(x)·χ_S(y) = 2^n·[x = y]`. -/
theorem sum_chi_eq {n : ℕ} (x y : Fin n → Bool) :
    ∑ S : Finset (Fin n), chi S x * chi S y = if x = y then 2 ^ n else 0 := by
  have hp1 : ∀ a b : Bool, pmOne a * pmOne b = pmOne (decide (a = b)) := by
    intro a b
    by_cases h : a = b
    · subst h
      rw [decide_eq_true rfl]
      cases a <;> simp [pmOne]
    · rw [decide_eq_false h]
      cases a <;> cases b <;> simp_all [pmOne]
  have hprod : ∀ S : Finset (Fin n),
      chi S x * chi S y = chi S (fun i => decide (x i = y i)) := by
    intro S
    unfold chi
    rw [← Finset.prod_mul_distrib]
    refine Finset.prod_congr rfl fun i _ => ?_
    exact hp1 (x i) (y i)
  have hsum : ∑ S : Finset (Fin n), chi S (fun i => decide (x i = y i)) =
      ∏ i : Fin n, (pmOne (decide (x i = y i)) + 1) := by
    rw [← Finset.powerset_univ, Finset.prod_add]
    refine Finset.sum_congr rfl fun t _ => ?_
    rw [Finset.prod_const_one, mul_one]
    rfl
  have hfactor : ∀ i : Fin n,
      pmOne (decide (x i = y i)) + 1 = if x i = y i then (2 : ℚ) else 0 := by
    intro i
    rw [pmOne_decide]
    by_cases h : x i = y i
    · simp [h]
      norm_num
    · simp [h]
  rw [Finset.sum_congr rfl fun S _ => hprod S, hsum,
    Finset.prod_congr rfl fun i _ => hfactor i]
  by_cases hxy : x = y
  · rw [if_pos hxy]
    rw [Finset.prod_congr rfl (g := fun _ => (2 : ℚ)) fun i _ => if_pos (congrFun hxy i),
      Finset.prod_const, Finset.card_univ, Fintype.card_fin]
  · rw [if_neg hxy]
    rw [funext_iff] at hxy
    push Not at hxy
    obtain ⟨i₀, hi₀⟩ := hxy
    exact Finset.prod_eq_zero (Finset.mem_univ i₀) (if_neg hi₀)

/-- Fourier inversion: `f(x) = ∑_S f̂(S)·χ_S(x)`. -/
theorem fourier_inversion {n : ℕ} (f : (Fin n → Bool) → ℚ) (x : Fin n → Bool) :
    ∑ S : Finset (Fin n), fourierCoeff f S * chi S x = f x := by
  simp_rw [fourierCoeff, cubeAvg, div_mul_eq_mul_div, ← Finset.sum_div, Finset.sum_mul]
  rw [Finset.sum_comm]
  simp_rw [mul_assoc, ← Finset.mul_sum]
  rw [Finset.sum_congr rfl (g := fun y => f y * (if y = x then 2 ^ n else 0))
    fun y _ => by rw [sum_chi_eq]]
  simp_rw [mul_ite, mul_zero]
  rw [Finset.sum_ite_eq' Finset.univ x fun y => f y * 2 ^ n, if_pos (Finset.mem_univ x)]
  rw [mul_div_assoc, div_self (by positivity : (2 : ℚ) ^ n ≠ 0), mul_one]

/-- Parseval's identity: `∑_S f̂(S)² = E[f²]`. -/
theorem parseval {n : ℕ} (f : (Fin n → Bool) → ℚ) :
    ∑ S : Finset (Fin n), fourierCoeff f S ^ 2 = cubeAvg fun x => f x ^ 2 := by
  simp_rw [pow_two]
  have h1 : ∀ S : Finset (Fin n), fourierCoeff f S * fourierCoeff f S =
      (∑ y : Fin n → Bool, f y * (fourierCoeff f S * chi S y)) / 2 ^ n := by
    intro S
    nth_rewrite 2 [fourierCoeff]
    rw [cubeAvg, mul_div_assoc', Finset.mul_sum]
    congr 1
    refine Finset.sum_congr rfl fun y _ => ?_
    ring
  simp_rw [h1, ← Finset.sum_div]
  rw [Finset.sum_comm]
  simp_rw [← Finset.mul_sum]
  rw [Finset.sum_congr rfl (g := fun x => f x * f x)
    fun x _ => by rw [fourier_inversion]]
  rfl

/-! ## The computable ℤ layer

The kernel cannot evaluate rational arithmetic, so concrete spectral
computations are also stated over ℤ: for a ±1-valued function,
`fourierNum fZ S = 2^n · f̂(S)` is an integer. The bridge lemmas connect the
two layers. -/

/-- The ±1 embedding of a Boolean into ℤ (computable counterpart of `pmOne`). -/
def pmOneZ (b : Bool) : ℤ := if b then 1 else -1

/-- The Fourier–Walsh character over ℤ (computable counterpart of `chi`). -/
def chiZ {n : ℕ} (S : Finset (Fin n)) (x : Fin n → Bool) : ℤ :=
  ∏ i ∈ S, pmOneZ (x i)

/-- The ±1-valued function represented by a Boolean function, over ℤ. -/
def boolSignZ {n : ℕ} (f : (Fin n → Bool) → Bool) (x : Fin n → Bool) : ℤ :=
  pmOneZ (f x)

/-- Integer numerator of a Fourier coefficient: `∑_x f(x)·χ_S(x)` over ℤ.
For a ±1-valued `f`, the Fourier coefficient `f̂(S)` equals
`fourierNum fZ S / 2^n`. -/
def fourierNum {n : ℕ} (f : (Fin n → Bool) → ℤ) (S : Finset (Fin n)) : ℤ :=
  ∑ x : Fin n → Bool, f x * chiZ S x

theorem pmOne_cast_pmOneZ (b : Bool) : pmOne b = ((pmOneZ b : ℤ) : ℚ) := by
  cases b <;> simp [pmOne, pmOneZ]

theorem chi_eq_cast_chiZ {n : ℕ} (S : Finset (Fin n)) (x : Fin n → Bool) :
    chi S x = ((chiZ S x : ℤ) : ℚ) := by
  rw [chi, chiZ, Int.cast_prod]
  refine Finset.prod_congr rfl fun i _ => ?_
  rw [pmOne_cast_pmOneZ]

/-- The ±1-valued function represented by a Boolean function, over ℚ. -/
def boolSign {n : ℕ} (f : (Fin n → Bool) → Bool) (x : Fin n → Bool) : ℚ :=
  pmOne (f x)

theorem boolSign_eq_cast_boolSignZ {n : ℕ} (f : (Fin n → Bool) → Bool) (x : Fin n → Bool) :
    boolSign f x = ((boolSignZ f x : ℤ) : ℚ) := by
  rw [boolSign, boolSignZ, pmOne_cast_pmOneZ]

/-- Bridge: a Boolean function's Fourier coefficient is its integer numerator
over `2^n`. -/
theorem fourierCoeff_boolSign_eq_num {n : ℕ} (f : (Fin n → Bool) → Bool) (S : Finset (Fin n)) :
    fourierCoeff (boolSign f) S = ((fourierNum (boolSignZ f) S : ℤ) : ℚ) / 2 ^ n := by
  rw [fourierCoeff, cubeAvg, fourierNum, Int.cast_sum]
  congr 1
  refine Finset.sum_congr rfl fun x _ => ?_
  rw [boolSign_eq_cast_boolSignZ, chi_eq_cast_chiZ, ← Int.cast_mul]

/-! ## Fourier sparsity -/

/-- The Fourier sparsity of a Boolean function: the number of its nonzero
Fourier coefficients (equivalently, the rank of the communication matrix of
the XOR function `f(x ⊕ y)` over ℝ; this equality is the starting point of
TWXZ 2013 and is not needed for the statements here). -/
def sparsity {n : ℕ} (f : (Fin n → Bool) → Bool) : ℕ :=
  (Finset.univ.filter fun S : Finset (Fin n) => fourierCoeff (boolSign f) S ≠ 0).card

/-- The sparsity counted through the integer layer: the same number, but
kernel-computable on concrete instances (the kernel does not evaluate ℚ
arithmetic). -/
theorem sparsity_eq_filter_num {n : ℕ} (f : (Fin n → Bool) → Bool) :
    sparsity f =
      (Finset.univ.filter fun S : Finset (Fin n) => fourierNum (boolSignZ f) S ≠ 0).card := by
  rw [sparsity]
  congr 1
  refine Finset.filter_congr fun S _ => ?_
  rw [fourierCoeff_boolSign_eq_num]
  constructor
  · intro h hk
    rw [hk, Int.cast_zero, zero_div] at h
    exact h rfl
  · intro h hd
    rw [div_eq_zero_iff] at hd
    rcases hd with h1 | h2
    · exact h (Int.cast_eq_zero.mp h1)
    · exact absurd h2 (pow_ne_zero _ (by norm_num : (2 : ℚ) ≠ 0))

/-- The Fourier support is nonempty: a ±1-valued function is not identically
zero, so by Fourier inversion some coefficient is nonzero. -/
theorem sparsity_pos {n : ℕ} (f : (Fin n → Bool) → Bool) : 0 < sparsity f := by
  by_contra h
  push Not at h
  have hzero : ∀ S : Finset (Fin n), fourierCoeff (boolSign f) S = 0 := by
    intro S
    by_contra hS
    have hmem : S ∈ Finset.univ.filter (fun S => fourierCoeff (boolSign f) S ≠ 0) := by
      rw [Finset.mem_filter]
      exact ⟨Finset.mem_univ S, hS⟩
    rw [sparsity, Nat.le_zero] at h
    rw [Finset.card_eq_zero.mp h] at hmem
    exact (Finset.notMem_empty S) hmem
  have : ∀ x : Fin n → Bool, boolSign f x = 0 := by
    intro x
    rw [← fourier_inversion (boolSign f) x]
    apply Finset.sum_eq_zero
    intro S _
    rw [hzero S, zero_mul]
  -- contradiction: a ±1 value is never zero (the cube is inhabited)
  have hne : boolSign f (fun _ => true) ≠ 0 := pmOne_ne_zero _
  exact hne (this _)

/-! ## Parity queries and parity decision trees -/

/-- The parity query on coordinate set `S`, in the ±1 encoding: `true` iff the
product `∏_{i ∈ S} y_i` of the ±1-encoded coordinates `y_i = pmOne (x i)` is
`+1`, i.e. iff `χ_S(x) = 1` (even parity of the `-1` coordinates). This is
the query model of TWXZ 2013: each query asks for the parity of an arbitrary
subset of the coordinates. -/
def parityQuery {n : ℕ} (S : Finset (Fin n)) (x : Fin n → Bool) : Bool :=
  decide ((S.filter fun i => x i = false).card % 2 = 0)

/-- The query–character bridge: the ±1 value of the parity query on `S` is
exactly the character `χ_S(x)`. -/
theorem pmOne_parityQuery {n : ℕ} (S : Finset (Fin n)) (x : Fin n → Bool) :
    pmOne (parityQuery S x) = chi S x := by
  rw [parityQuery, pmOne_decide]
  rw [chi, show (∏ i ∈ S, pmOne (x i)) = ∏ i ∈ S, (if x i then (1 : ℚ) else -1) from
    Finset.prod_congr rfl fun i _ => rfl]
  rw [Finset.prod_ite, Finset.prod_const_one, one_mul, Finset.prod_const]
  have hfilter : (S.filter fun i => x i = false) = S.filter (fun i => ¬x i) := by
    refine Finset.filter_congr fun i _ => ?_
    cases x i <;> simp
  rw [hfilter]
  by_cases h : (S.filter fun i => ¬x i).card % 2 = 0
  · rw [if_pos h]
    have he : Even (S.filter fun i => ¬x i).card := by
      rw [Nat.even_iff]; exact h
    exact (Even.neg_one_pow (α := ℚ) he).symm
  · rw [if_neg h]
    have ho : Odd (S.filter fun i => ¬x i).card := by
      rw [Nat.odd_iff]; omega
    exact (Odd.neg_one_pow (α := ℚ) ho).symm

/-- A parity decision tree over `n` variables: each inner node queries the
parity of an arbitrary coordinate subset `S` (see `parityQuery`), going to
`hi` on answer `true` and to `lo` on `false`; leaves output the answer bit. -/
inductive ParityTree (n : ℕ) where
  | leaf (b : Bool) : ParityTree n
  | node (S : Finset (Fin n)) (lo hi : ParityTree n) : ParityTree n

namespace ParityTree

/-- Evaluation of a parity decision tree at a cube point. -/
def eval {n : ℕ} : ParityTree n → (Fin n → Bool) → Bool
  | leaf b, _ => b
  | node S lo hi, x => if parityQuery S x then eval hi x else eval lo x

/-- Depth: leaves have depth `0`; a node adds one query. -/
def depth {n : ℕ} : ParityTree n → ℕ
  | leaf _ => 0
  | node _ lo hi => max lo.depth hi.depth + 1

/-- A parity decision tree computes `f` if it agrees with `f` on every cube
point. -/
def Computes {n : ℕ} (t : ParityTree n) (f : (Fin n → Bool) → Bool) : Prop :=
  ∀ x, t.eval x = f x

end ParityTree

/-- `f` is computable in depth `d`: some parity decision tree of depth at most
`d` computes it. The parity decision tree complexity `PDT(f)` of the
literature is the least such `d`; the existential form avoids taking a
minimum over the infinite tree type. -/
def ComputesInDepth {n : ℕ} (f : (Fin n → Bool) → Bool) (d : ℕ) : Prop :=
  ∃ t : ParityTree n, t.depth ≤ d ∧ t.Computes f

/-- Monotonicity in the depth bound. -/
theorem ComputesInDepth.mono {n : ℕ} {f : (Fin n → Bool) → Bool} {d d' : ℕ}
    (h : d ≤ d') : ComputesInDepth f d → ComputesInDepth f d' := by
  rintro ⟨t, ht, hc⟩
  exact ⟨t, ht.trans h, hc⟩

/-! ## The running small instance: the two-bit parity function -/

/-- The two-bit parity function on `Fin 2`: `x₀ ⊕ x₁` as a Boolean xor. Its
±1 form is `-χ_{0,1}` (see `pmOne_xor`), so its Fourier sparsity is 1 and its
parity decision tree depth is exactly 1 — the smallest non-constant
instance. -/
def fpar2 : (Fin 2 → Bool) → Bool := fun x => x 0 ^^ x 1

/-! ## The conjecture -/

/-- **The XOR log-rank conjecture** (Montanaro–Osborne 2009, arXiv:0909.3392;
parity decision tree form of Tsang–Wong–Xie–Zhang, FOCS 2013,
arXiv:1304.1245): there is a universal constant `c` such that every Boolean
function `f` on every cube is computable by a parity decision tree of depth
at most `(1 + log₂ sp(f))^c`. See the header fidelity notes for the `1 +`
guard and the choice of natural exponent. -/
def Conjecture : Prop :=
  ∃ c : ℕ, ∀ {n : ℕ} (f : (Fin n → Bool) → Bool),
    ∃ d : ℕ, ComputesInDepth f d ∧
      (d : ℝ) ≤ (1 + Real.logb 2 (sparsity f : ℝ)) ^ c

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

/-! ## Slot zone: the conjecture and its negation -/

-- @[slot main]
/-- **The XOR log-rank conjecture**: parity decision tree depth is bounded by
a fixed power of the logarithm of the Fourier sparsity, uniformly over all
Boolean functions on all cubes. -/
theorem conj : Conjecture := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

-- @[slot main]
/-- The negation of the XOR log-rank conjecture: no universal constant `c`
works — for every `c` there is a Boolean function whose parity decision tree
depth exceeds `(1 + log₂ sp(f))^c`. -/
theorem refuted : ¬Conjecture := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

end XorLogRank
