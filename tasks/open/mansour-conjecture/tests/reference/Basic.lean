/-
Statement layer for Mansour's conjecture (Yishay Mansour, *An O(n^{log log n})
learning algorithm for DNF under the uniform distribution*, COLT 1992;
J. Comput. System Sci. 50(3):543–550, 1995; statement as in the Simons
Institute open-problem collection *Real Analysis in Computer Science: A
Collection of Open Problems* and O'Donnell, *Analysis of Boolean Functions*,
§4.4):

Let f : {±1}ⁿ → {±1} be computable by a DNF of size s > 1 and let
ε ∈ (0, 1/2]. Then the Fourier spectrum of f is ε-concentrated on a
collection ℱ with |ℱ| ≤ s^{O(log(1/ε))}.

Status: open. Lecomte–Tan 2021 (arXiv:2109.04525) still
lists "the obvious open problem is to prove Mansour's conjecture"; the best
bound for general DNFs is ε-concentration on
(s/ε)^{O(log log(s/ε) · log(1/ε))} coefficients (Mansour 1995; Lecomte–Tan
2021 sharpens the dependence to the read number). Proved for random DNFs
and constant-read DNFs (Klivans–Lee–Wan, COLT 2010), and for read up to
Θ̃(log log s) (Lecomte–Tan 2021);
the weak form s^{O(1/ε)} follows from the Fourier Entropy–Influence
conjecture.

This file is the task's definition zone plus slot zone:
- The definition zone fixes the Boolean cube `Fin n → Bool`, the Fourier–
  Walsh characters `chi S`, Fourier coefficients `fourierCoeff f S` (over ℚ,
  so that small instances are kernel-computable by `decide`; ε-concentration
  for the conjecture itself is stated over ℝ via coercion), DNF syntax
  (`Term`/`dnfFun`), decision trees (`DTree`), and the exact-concentration
  predicates `SpectralConcQ`/`SpectralConc`. The API lemmas (character
  orthonormality, Fourier inversion, Parseval, linearity/shift rules, the
  single-term Fourier expansion) are fully proved.
- The slot zone states the conjecture (`conj`) and its negation (`refuted`).
  Both proof bodies are left blank.

Fidelity notes (see `tests/reference/concept-ledger.md` of the packaged task):
1. Following the Simons collection, a DNF of *size s* means *s terms*; the
   conjecture is quantified directly over DNF syntax (`D : List (Term n)`)
   rather than over functions f admitting a size-s representation — the two
   quantifications are equivalent.
2. The big-O in `s^{O(log(1/ε))}` is rendered as a universal natural exponent
   C with |ℱ| ≤ s^(C·log(1/ε)); the hidden multiplicative constant absorbs
   into C because s > 1, and the choice of logarithm base is immaterial for
   the same reason.
3. Everything spectral is over ℚ (all functions in sight are ±1-valued); the
   conjecture's concentration and cardinality bound use ℝ only through
   coercions. Because the kernel does not evaluate `Rat` arithmetic, a
   parallel ℤ layer (`fourierNum`, the integer numerators `2^n·f̂(S)`)
   carries the kernel-decidable computations, with cast lemmas bridging the
   two (`fourierCoeff_dnfFun_eq_num`).
-/

import Mathlib

namespace MansourConjecture

open scoped symmDiff

/-! ## Cube points, characters, and Fourier coefficients -/

/-- The ±1 embedding of a Boolean into ℚ: `true ↦ 1`, `false ↦ −1`. -/
def pmOne (b : Bool) : ℚ := if b then 1 else -1

@[simp] theorem pmOne_true : pmOne true = 1 := rfl

@[simp] theorem pmOne_false : pmOne false = -1 := rfl

theorem pmOne_sq (b : Bool) : pmOne b ^ 2 = 1 := by cases b <;> simp [pmOne]

theorem pmOne_not (b : Bool) : pmOne (!b) = -pmOne b := by cases b <;> simp [pmOne]

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

/-- Uniform expectation over the Boolean cube. -/
def cubeAvg {n : ℕ} (f : (Fin n → Bool) → ℚ) : ℚ :=
  (∑ x : Fin n → Bool, f x) / 2 ^ n

theorem cubeAvg_add {n : ℕ} (f g : (Fin n → Bool) → ℚ) :
    cubeAvg (fun x => f x + g x) = cubeAvg f + cubeAvg g := by
  unfold cubeAvg
  rw [← add_div]
  congr 1
  exact Finset.sum_add_distrib

theorem cubeAvg_sub {n : ℕ} (f g : (Fin n → Bool) → ℚ) :
    cubeAvg (fun x => f x - g x) = cubeAvg f - cubeAvg g := by
  unfold cubeAvg
  rw [← sub_div]
  congr 1
  exact Finset.sum_sub_distrib (f := f) (g := g)

theorem cubeAvg_smul {n : ℕ} (c : ℚ) (f : (Fin n → Bool) → ℚ) :
    cubeAvg (fun x => c * f x) = c * cubeAvg f := by
  show (∑ x : Fin n → Bool, c * f x) / 2 ^ n =
    c * ((∑ x : Fin n → Bool, f x) / 2 ^ n)
  rw [mul_div_assoc', Finset.mul_sum]

theorem cubeAvg_sum {n : ℕ} {ι : Type*} [DecidableEq ι] (P : Finset ι)
    (g : ι → (Fin n → Bool) → ℚ) :
    cubeAvg (fun x => ∑ U ∈ P, g U x) = ∑ U ∈ P, cubeAvg (g U) := by
  unfold cubeAvg
  rw [Finset.sum_comm, Finset.sum_div]

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

theorem fourierCoeff_sub {n : ℕ} (f g : (Fin n → Bool) → ℚ) (S : Finset (Fin n)) :
    fourierCoeff (fun x => f x - g x) S = fourierCoeff f S - fourierCoeff g S := by
  show cubeAvg (fun x => (f x - g x) * chi S x) =
    cubeAvg (fun x => f x * chi S x) - cubeAvg (fun x => g x * chi S x)
  rw [show (fun x => (f x - g x) * chi S x) = fun x => f x * chi S x - g x * chi S x
      from funext fun x => sub_mul _ _ _, cubeAvg_sub]

theorem fourierCoeff_smul {n : ℕ} (c : ℚ) (f : (Fin n → Bool) → ℚ) (S : Finset (Fin n)) :
    fourierCoeff (fun x => c * f x) S = c * fourierCoeff f S := by
  show cubeAvg (fun x => (c * f x) * chi S x) = c * cubeAvg (fun x => f x * chi S x)
  rw [show (fun x => (c * f x) * chi S x) = fun x => c * (f x * chi S x)
      from funext fun x => mul_assoc _ _ _, cubeAvg_smul]

theorem fourierCoeff_const {n : ℕ} (c : ℚ) (S : Finset (Fin n)) :
    fourierCoeff (fun _ => c) S = c * cubeAvg (chi S) := by
  show (∑ x : Fin n → Bool, c * chi S x) / 2 ^ n =
    c * ((∑ x : Fin n → Bool, chi S x) / 2 ^ n)
  rw [mul_div_assoc', Finset.mul_sum]

/-- Shift rule: multiplying by the character `χ_{i}` shifts the spectrum. -/
theorem fourierCoeff_chi_singleton_mul {n : ℕ} (f : (Fin n → Bool) → ℚ) (i : Fin n)
    (S : Finset (Fin n)) :
    fourierCoeff (fun x => chi {i} x * f x) S = fourierCoeff f (S ∆ {i}) := by
  show (∑ x : Fin n → Bool, (chi {i} x * f x) * chi S x) / 2 ^ n =
    (∑ x : Fin n → Bool, f x * chi (S ∆ {i}) x) / 2 ^ n
  congr 1
  refine Finset.sum_congr rfl fun x _ => ?_
  rw [mul_comm (chi {i} x) (f x), mul_assoc, chi_mul, symmDiff_comm]

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

/-! ## DNF syntax and the computed function -/

/-- A DNF term over `n` variables: positive literals `pos` and negative
literals `neg`. The term is the conjunction of `x i` for `i ∈ pos` and
`¬x i` for `i ∈ neg`. -/
structure Term (n : ℕ) where
  pos : Finset (Fin n)
  neg : Finset (Fin n)

namespace Term

/-- Satisfaction of a term at a cube point. -/
def Sat {n : ℕ} (T : Term n) (x : Fin n → Bool) : Prop :=
  (∀ i ∈ T.pos, x i = true) ∧ (∀ i ∈ T.neg, x i = false)

instance {n : ℕ} (T : Term n) (x : Fin n → Bool) : Decidable (T.Sat x) := by
  unfold Sat; infer_instance

/-- The variables mentioned by the term. -/
def vars {n : ℕ} (T : Term n) : Finset (Fin n) := T.pos ∪ T.neg

/-- Consistency: no variable appears with both signs (otherwise the term is
unsatisfiable). -/
def Consistent {n : ℕ} (T : Term n) : Prop := Disjoint T.pos T.neg

/-- Indicator of term satisfaction: `1` if satisfied, else `0`. -/
def ind {n : ℕ} (T : Term n) (x : Fin n → Bool) : ℚ :=
  if T.Sat x then 1 else 0

/-- The satisfaction indicator of a consistent term as a product of
per-variable indicators. -/
theorem ind_eq_prod {n : ℕ} (T : Term n) (hT : T.Consistent) (x : Fin n → Bool) :
    T.ind x =
      ∏ i ∈ T.vars, (1 + (if i ∈ T.neg then -1 else 1) * chi {i} x) / 2 := by
  by_cases h : T.Sat x
  · rw [ind, if_pos h]
    apply Eq.symm
    apply Finset.prod_eq_one
    intro i hi
    have hi' : i ∈ T.pos ∪ T.neg := hi
    rcases Finset.mem_union.mp hi' with hip | hin
    · rw [if_neg (Finset.disjoint_left.mp hT hip), chi_singleton, h.1 i hip, pmOne_true]
      norm_num
    · rw [if_pos hin, chi_singleton, h.2 i hin, pmOne_false]
      norm_num
  · rw [ind, if_neg h]
    apply Eq.symm
    rcases em (∀ i ∈ T.pos, x i = true) with hp | hp
    · have hn : ¬∀ i ∈ T.neg, x i = false := fun hn => h ⟨hp, hn⟩
      push Not at hn
      obtain ⟨j, hjT, hj⟩ := hn
      apply Finset.prod_eq_zero (Finset.mem_union.mpr (Or.inr hjT))
      rw [if_pos hjT, chi_singleton]
      have hjx : x j = true := by cases hjc : x j <;> simp_all
      rw [hjx, pmOne_true]
      norm_num
    · push Not at hp
      obtain ⟨j, hjT, hj⟩ := hp
      apply Finset.prod_eq_zero (Finset.mem_union.mpr (Or.inl hjT))
      rw [if_neg (Finset.disjoint_left.mp hT hjT), chi_singleton]
      have hjx : x j = false := by cases hjc : x j <;> simp_all
      rw [hjx, pmOne_false]
      norm_num

/-- The satisfaction indicator of a consistent term in the Fourier basis:
`ind T = 2^{-|vars|} · ∑_{U ⊆ vars} (-1)^{|U ∩ neg|} · χ_U`. -/
theorem ind_eq_sum {n : ℕ} (T : Term n) (hT : T.Consistent) (x : Fin n → Bool) :
    T.ind x =
      (1 / 2 ^ T.vars.card) *
        ∑ U ∈ T.vars.powerset, (-1) ^ (U ∩ T.neg).card * chi U x := by
  have hσ : ∀ U : Finset (Fin n),
      (∏ i ∈ U, (if i ∈ T.neg then (-1 : ℚ) else 1)) = (-1) ^ (U ∩ T.neg).card := by
    intro U
    rw [Finset.prod_ite, Finset.prod_const, Finset.prod_const_one, mul_one,
      Finset.filter_mem_eq_inter]
  have hχ : ∀ U : Finset (Fin n), (∏ i ∈ U, chi {i} x) = chi U x := by
    intro U
    exact (chi_eq_prod_singleton U x).symm
  have hexp : (∏ i ∈ T.vars, (1 + (if i ∈ T.neg then -1 else 1) * chi {i} x)) =
      ∑ U ∈ T.vars.powerset, (-1) ^ (U ∩ T.neg).card * chi U x := by
    simp_rw [add_comm (1 : ℚ)]
    rw [Finset.prod_add]
    refine Finset.sum_congr rfl fun U _ => ?_
    rw [Finset.prod_const_one, mul_one, Finset.prod_mul_distrib, hσ U, hχ U]
  rw [ind_eq_prod T hT x, Finset.prod_div_distrib, Finset.prod_const, hexp,
    div_eq_mul_one_div, mul_comm]

/-- The Fourier coefficient of a consistent term's satisfaction indicator:
`Î(S) = 2^{-|vars|}·(−1)^{|S ∩ neg|}` for `S ⊆ vars`, else `0`. This is the
per-term formula behind `single_term_spectrum` and the selector example. -/
theorem ind_coeff {n : ℕ} (T : Term n) (hT : T.Consistent) (S : Finset (Fin n)) :
    cubeAvg (fun x => T.ind x * chi S x) =
      if S ⊆ T.vars then (1 / 2 ^ T.vars.card) * (-1) ^ (S ∩ T.neg).card else 0 := by
  have hexp : (fun x => T.ind x * chi S x) = fun x =>
      (1 / 2 ^ T.vars.card) *
        ∑ U ∈ T.vars.powerset, (-1) ^ (U ∩ T.neg).card * (chi U x * chi S x) := by
    funext x
    rw [T.ind_eq_sum hT x, mul_assoc, Finset.sum_mul]
    congr 1
    refine Finset.sum_congr rfl fun U _ => ?_
    ring
  rw [hexp, cubeAvg_smul, cubeAvg_sum]
  rw [Finset.sum_congr rfl (g := fun U => (-1) ^ (U ∩ T.neg).card *
    (if U = S then (1 : ℚ) else 0)) fun U _ => by rw [cubeAvg_smul, cubeAvg_chi_mul]]
  simp_rw [mul_ite, mul_one, mul_zero]
  rw [Finset.sum_ite_eq' T.vars.powerset S fun U => (-1) ^ (U ∩ T.neg).card]
  by_cases hS : S ⊆ T.vars
  · rw [if_pos hS, if_pos (Finset.mem_powerset.mpr hS)]
  · rw [if_neg hS, if_neg (Finset.mem_powerset.not.mpr hS)]
    ring

end Term

/-- DNF satisfaction: some term of the list is satisfied. A DNF *is* a list of
terms; its *size* is the number of terms (the list length). -/
def DNFSat {n : ℕ} (D : List (Term n)) (x : Fin n → Bool) : Prop :=
  ∃ T ∈ D, T.Sat x

instance {n : ℕ} (D : List (Term n)) (x : Fin n → Bool) : Decidable (DNFSat D x) := by
  unfold DNFSat
  exact List.decidableBEx _ _

/-- The ±1-valued function computed by a DNF: `1` on satisfying assignments,
`−1` elsewhere. -/
def dnfFun {n : ℕ} (D : List (Term n)) (x : Fin n → Bool) : ℚ :=
  pmOne (decide (DNFSat D x))

/-- The function of a single-term DNF is `2·ind − 1`. -/
theorem dnfFun_single {n : ℕ} (T : Term n) (x : Fin n → Bool) :
    dnfFun [T] x = 2 * T.ind x - 1 := by
  unfold dnfFun Term.ind
  rw [pmOne_decide]
  by_cases h : T.Sat x
  · rw [if_pos h, if_pos (show DNFSat [T] x from ⟨T, by simp, h⟩)]
    norm_num
  · rw [if_neg h, if_neg (show ¬DNFSat [T] x from fun ⟨T', hT', hsat⟩ => by
      simp at hT'; subst hT'; exact h hsat)]
    norm_num

/-- The Fourier expansion of the function computed by a single-term DNF:
`f = 2^{1-|vars|} · ∑_{U ⊆ vars} (-1)^{|U ∩ neg|} · χ_U − 1`. -/
theorem dnfFun_single_expansion {n : ℕ} (T : Term n) (hT : T.Consistent)
    (x : Fin n → Bool) :
    dnfFun [T] x =
      (2 / 2 ^ T.vars.card) *
          ∑ U ∈ T.vars.powerset, (-1) ^ (U ∩ T.neg).card * chi U x - 1 := by
  rw [dnfFun_single, T.ind_eq_sum hT x]
  ring

/-! ## The computable ℤ layer: integer numerators of Fourier coefficients

The kernel cannot evaluate rational arithmetic (`decide` does not reduce
`Rat` operations), so concrete spectral computations are stated over ℤ: for a
±1-valued function, `fourierNum f S = 2^n · f̂(S)` is an integer. The bridge
lemmas below connect the two layers. -/

/-- The ±1 embedding of a Boolean into ℤ (computable counterpart of `pmOne`). -/
def pmOneZ (b : Bool) : ℤ := if b then 1 else -1

/-- The Fourier–Walsh character over ℤ (computable counterpart of `chi`). -/
def chiZ {n : ℕ} (S : Finset (Fin n)) (x : Fin n → Bool) : ℤ :=
  ∏ i ∈ S, pmOneZ (x i)

/-- The ±1-valued function computed by a DNF, over ℤ. -/
def dnfFunZ {n : ℕ} (D : List (Term n)) (x : Fin n → Bool) : ℤ :=
  pmOneZ (decide (DNFSat D x))

/-- Integer numerator of a Fourier coefficient: `∑_x f(x)·χ_S(x)` over ℤ.
For ±1-valued `f`, the Fourier coefficient `f̂(S)` equals
`fourierNum f S / 2^n`. -/
def fourierNum {n : ℕ} (f : (Fin n → Bool) → ℤ) (S : Finset (Fin n)) : ℤ :=
  ∑ x : Fin n → Bool, f x * chiZ S x

theorem pmOne_cast_pmOneZ (b : Bool) : pmOne b = ((pmOneZ b : ℤ) : ℚ) := by
  cases b <;> simp [pmOne, pmOneZ]

theorem chi_eq_cast_chiZ {n : ℕ} (S : Finset (Fin n)) (x : Fin n → Bool) :
    chi S x = ((chiZ S x : ℤ) : ℚ) := by
  rw [chi, chiZ, Int.cast_prod]
  refine Finset.prod_congr rfl fun i _ => ?_
  rw [pmOne_cast_pmOneZ]

theorem dnfFun_eq_cast_dnfFunZ {n : ℕ} (D : List (Term n)) (x : Fin n → Bool) :
    dnfFun D x = ((dnfFunZ D x : ℤ) : ℚ) := by
  rw [dnfFun, dnfFunZ, pmOne_cast_pmOneZ]

/-- Bridge: the Fourier coefficient of a DNF's function is its integer
numerator over `2^n`. -/
theorem fourierCoeff_dnfFun_eq_num {n : ℕ} (D : List (Term n)) (S : Finset (Fin n)) :
    fourierCoeff (dnfFun D) S = ((fourierNum (dnfFunZ D) S : ℤ) : ℚ) / 2 ^ n := by
  rw [fourierCoeff, cubeAvg, fourierNum, Int.cast_sum]
  congr 1
  refine Finset.sum_congr rfl fun x _ => ?_
  rw [dnfFun_eq_cast_dnfFunZ, chi_eq_cast_chiZ, ← Int.cast_mul]

/-! ## Spectral concentration -/

/-- ε-concentration of the Fourier spectrum over ℚ: the mass outside `ℱ` is
at most `ε`. The conjecture itself uses the ℝ form below. (For kernel-decidable computations see the ℤ layer `fourierNum`.) -/
def SpectralConcQ {n : ℕ} (f : (Fin n → Bool) → ℚ) (ε : ℚ)
    (ℱ : Finset (Finset (Fin n))) : Prop :=
  ∑ S ∈ ℱᶜ, fourierCoeff f S ^ 2 ≤ ε

/-- ε-concentration of the Fourier spectrum over ℝ (the conjecture's form). -/
def SpectralConc {n : ℕ} (f : (Fin n → Bool) → ℚ) (ε : ℝ)
    (ℱ : Finset (Finset (Fin n))) : Prop :=
  ((∑ S ∈ ℱᶜ, fourierCoeff f S ^ 2 : ℚ) : ℝ) ≤ ε

/-- The ℚ-form implies the ℝ-form. -/
theorem SpectralConcQ.toReal {n : ℕ} {f : (Fin n → Bool) → ℚ} {ε : ℚ}
    {ℱ : Finset (Finset (Fin n))} :
    SpectralConcQ f ε ℱ → SpectralConc f (ε : ℝ) ℱ := by
  intro h
  have h' : (∑ S ∈ ℱᶜ, fourierCoeff f S ^ 2 : ℚ) ≤ ε := h
  show ((∑ S ∈ ℱᶜ, fourierCoeff f S ^ 2 : ℚ) : ℝ) ≤ (ε : ℝ)
  exact_mod_cast h'

/-! ## Decision trees -/

/-- A Boolean decision tree over `n` variables: query coordinate `i`, go to
`lo` on `false` and to `hi` on `true`. -/
inductive DTree (n : ℕ) where
  | leaf (b : Bool) : DTree n
  | node (i : Fin n) (lo hi : DTree n) : DTree n

namespace DTree

/-- Evaluation of a decision tree at a cube point. -/
def eval {n : ℕ} : DTree n → (Fin n → Bool) → Bool
  | leaf b, _ => b
  | node i lo hi, x => if x i then eval hi x else eval lo x

/-- Depth: leaves have depth `0`; a node adds one query. -/
def depth {n : ℕ} : DTree n → ℕ
  | leaf _ => 0
  | node _ lo hi => max lo.depth hi.depth + 1

/-- The ±1-valued function computed by a decision tree. -/
def evalFun {n : ℕ} (t : DTree n) (x : Fin n → Bool) : ℚ :=
  pmOne (t.eval x)

/-- A node computes `(1+χᵢ)/2 · hi + (1−χᵢ)/2 · lo`. -/
theorem evalFun_node {n : ℕ} (i : Fin n) (lo hi : DTree n) (x : Fin n → Bool) :
    (node i lo hi).evalFun x =
      ((1 + chi {i} x) / 2) * hi.evalFun x + ((1 - chi {i} x) / 2) * lo.evalFun x := by
  cases hx : x i <;> simp [evalFun, eval, hx, chi_singleton, pmOne]

end DTree

/-- The low-degree coefficient collection: sets of at most `d` variables. -/
def lowDegree {n : ℕ} (d : ℕ) : Finset (Finset (Fin n)) :=
  Finset.univ.filter fun S => S.card ≤ d

/-- The cardinality of `S △ {i}`: removing `i` when present, adding it when
absent. -/
theorem card_symmDiff_singleton {n : ℕ} (S : Finset (Fin n)) (i : Fin n) :
    (S ∆ {i}).card = if i ∈ S then S.card - 1 else S.card + 1 := by
  by_cases hi : i ∈ S
  · rw [if_pos hi]
    have h : S ∆ {i} = S \ {i} := by
      ext a
      simp only [Finset.mem_symmDiff, Finset.mem_sdiff, Finset.mem_singleton]
      constructor
      · rintro (⟨h1, h2⟩ | ⟨h1, h2⟩)
        · exact ⟨h1, h2⟩
        · subst h1; exact absurd hi h2
      · rintro ⟨h1, h2⟩
        exact Or.inl ⟨h1, h2⟩
    rw [h, Finset.card_sdiff,
      Finset.inter_eq_left.mpr (Finset.singleton_subset_iff.mpr hi), Finset.card_singleton]
  · rw [if_neg hi]
    have h : S ∆ {i} = insert i S := by
      ext a
      simp only [Finset.mem_symmDiff, Finset.mem_singleton, Finset.mem_insert]
      constructor
      · rintro (⟨h1, h2⟩ | ⟨h1, h2⟩)
        · exact Or.inr h1
        · exact Or.inl h1
      · rintro (rfl | h1)
        · exact Or.inr ⟨rfl, hi⟩
        · exact Or.inl ⟨h1, by rintro rfl; exact hi h1⟩
    rw [h, Finset.card_insert_of_notMem hi]

/-! ## The running example: the selector `x₀x₁ ∨ ¬x₀x₂` on `Fin 3` -/

/-- The selector DNF on `Fin 3`: `x₀x₁ ∨ ¬x₀x₂` ("if x₀ then x₁ else x₂"),
a 2-term DNF. -/
def selectorDnf : List (Term 3) := [⟨{0, 1}, ∅⟩, ⟨{2}, {0}⟩]

/-- The Fourier support of `dnfFun selectorDnf`: the four coefficient sets
`{1}`, `{2}`, `{0,1}`, `{0,2}` (each with |coefficient| = 1/2, see
`selector_spectrum`). -/
def selectorSupport : Finset (Finset (Fin 3)) := {{1}, {2}, {0, 1}, {0, 2}}

/-- The integer numerators of `dnfFun selectorDnf`'s Fourier coefficients:
`4` on `{1}`, `{2}`, `{0,1}`; `-4` on `{0,2}`; `0` elsewhere. The coefficient
itself is the numerator divided by `2^3 = 8`, so these are `±1/2` and `0`. -/
def selectorNum : Finset (Fin 3) → ℤ := fun S =>
  if S = {1} then 4
  else if S = {2} then 4
  else if S = {0, 1} then 4
  else if S = {0, 2} then -4
  else 0

/-! ## The conjecture -/

/-- **Mansour's conjecture** (Mansour 1992/1995): there is a universal
constant `C` such that for every DNF `D` with `s > 1` terms and every
`ε ∈ (0, 1/2]`, the Fourier spectrum of the ±1-valued function computed by
`D` is `ε`-concentrated on some collection of at most `s^{C·log(1/ε)}`
coefficients. -/
def Conjecture : Prop :=
  ∃ C : ℕ, ∀ {n : ℕ} (D : List (Term n)),
    1 < D.length → ∀ ε : ℝ, 0 < ε → ε ≤ 1 / 2 →
      ∃ ℱ : Finset (Finset (Fin n)),
        SpectralConc (dnfFun D) ε ℱ ∧
          (ℱ.card : ℝ) ≤ (D.length : ℝ) ^ ((C : ℝ) * Real.log (1 / ε))

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

/-! ## Slot zone: the conjecture and its negation -/

-- @[slot main]
/-- **Mansour's conjecture**: every DNF with `s > 1` terms has its Fourier
spectrum `ε`-concentrated on at most `s^{C·log(1/ε)}` coefficients, for a
universal constant `C`. -/
theorem conj : Conjecture := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

-- @[slot main]
/-- The negation of Mansour's conjecture: no universal constant `C` works —
for every `C` there is a DNF whose spectrum needs more than `s^{C·log(1/ε)}`
coefficients to `ε`-concentrate. -/
theorem refuted : ¬Conjecture := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

end MansourConjecture
