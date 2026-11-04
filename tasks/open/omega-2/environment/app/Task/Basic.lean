/-
Statement layer for the matrix multiplication exponent problem (is ω = 2?):
whether the exponent ω of square matrix multiplication — the infimum of all
real τ such that two n×n matrices can be multiplied within O(n^τ) arithmetic
operations — equals 2. Current frontier: ω < 2.371177 (Dupont et al. 2026,
arXiv:2608.16884; previously 2.371339, Alman et al. 2025, and 2.371552,
Vassilevska Williams–Xu–Xu–Zhou 2024 before that),
and the only lower bound on ω itself is the trivial ω ≥ 2; barrier results
(Alman–Vassilevska Williams, FOCS 2018) show the present laser-method
framework cannot prove ω = 2. Survey: Alman–Vassilevska Williams, SODA 2021.

This file is the task's definition zone plus slot zone:
- The definition zone defines 3-tensors (functional encoding, not the
  quotient tensor-product type), tensor rank, the matrix multiplication
  tensor `⟨m,n,p⟩` (third leg in the `Tr(ABC)` convention), and the exponent
  `matMulOmega F` as an `sInf` over achievable exponents. The tensor-rank
  layer (simple tensors, `tensorRank` as an `sInf` over decomposition
  lengths, the standard-basis decomposition lemma, subadditivity) is adapted
  from the repository
  `spectra-research/asymptotic-tensor-rank-semicontinuity`
  (Christandl–Hoeberechts–Nieuwboer–Vrana–Zuiddam, arXiv:2411.15789),
  file `TensorRank.lean`, which is released under the Apache-2.0 license
  (Copyright (c) 2026 Jeroen Zuiddam). The adaptation specializes to order-3
  tensors and generalizes the leg index types to arbitrary finite types.
- The slot zone states the conjecture (`conj`: ω ≤ 2, which together with
  the trivial lower bound ω ≥ 2 is the statement ω = 2) and its negation
  (`refuted`). Both proof bodies are left blank.

Fidelity notes (see `tests/reference/concept-ledger.md` of the packaged task):
1. The field is pinned to `ℚ`. The literature usually does not fix the base
   field (all known upper-bound constructions have integer coefficients and
   work over every field; all known lower bounds hold over every field); `ℚ`
   is the canonical characteristic-0 choice for the arithmetic model.
2. `ω` is defined through the tensor rank of the matrix multiplication
   tensors: `ω = inf {τ : ℝ | R(⟨n,n,n⟩) = O(n^τ)}`. This is the standard
   bilinear-complexity definition (Bürgisser–Clausen–Shokrollahi, Ch. 15).
3. The `sInf` over the exponent set is well defined only because the set is
   nonempty and bounded below: the naive algorithm puts `τ = 3` in the set
   (`omegaSet_nonempty`, proved via the explicit decomposition
   `tensorRank_matMulTensor_le`), and every exponent in the set is `≥ 0`
   because `R(⟨n,n,n⟩) ≥ 1` for `n ≥ 1` (`omegaSet_nonneg_of_mem`,
   `omegaSet_bddBelow`). Without nonemptiness, Lean's convention
   `sInf ∅ = 0` would silently trivialize `matMulOmega`.
-/

import Mathlib

namespace MatMulOmega

/-! ### 3-tensors and tensor rank

Adapted from `spectra-research/asymptotic-tensor-rank-semicontinuity`
(Apache-2.0, Copyright (c) 2026 Jeroen Zuiddam), file `TensorRank.lean`:
the two-layer definition (simple tensors, then rank as the minimum number of
simple summands), the standard-basis decomposition witnessing that every
tensor has finite rank, and subadditivity. Here specialized to order 3 and
with leg indices ranging over arbitrary finite types. -/

section TensorRank

variable {F : Type*} [Field F] {ι₁ ι₂ ι₃ : Type*}

/-- A 3-tensor over `F` with legs indexed by `ι₁`, `ι₂`, `ι₃`: a function
from multi-indices to `F` (functional encoding of `F^{ι₁} ⊗ F^{ι₂} ⊗ F^{ι₃}`). -/
abbrev Tensor3 (F : Type*) [Field F] (ι₁ ι₂ ι₃ : Type*) : Type _ :=
  (ι₁ × ι₂ × ι₃) → F

/-- The simple (rank-1) 3-tensor `u ⊗ v ⊗ w`. -/
def simpleTensor (u : ι₁ → F) (v : ι₂ → F) (w : ι₃ → F) : Tensor3 F ι₁ ι₂ ι₃ :=
  fun (i, j, k) => u i * v j * w k

/-- A 3-tensor is **simple** if it is `u ⊗ v ⊗ w` for some leg vectors. -/
def IsSimpleTensor (T : Tensor3 F ι₁ ι₂ ι₃) : Prop :=
  ∃ u v w, T = simpleTensor u v w

/-- The set of decomposition lengths of `T`: those `r` for which `T` is a sum
of `r` simple tensors. -/
def decompSet (T : Tensor3 F ι₁ ι₂ ι₃) : Set ℕ :=
  {r : ℕ | ∃ s : Fin r → Tensor3 F ι₁ ι₂ ι₃,
    (∀ i, IsSimpleTensor (s i)) ∧ T = ∑ i, s i}

/-- **Tensor rank** `R(T)`: the smallest number of simple tensors summing to
`T`. (An `sInf` over the decomposition lengths; see `tensorRank_eq_zero` for
the `T = 0` case.) -/
noncomputable def tensorRank (T : Tensor3 F ι₁ ι₂ ι₃) : ℕ :=
  sInf (decompSet T)

section Finite

variable [Fintype ι₁] [Fintype ι₂] [Fintype ι₃]
  [DecidableEq ι₁] [DecidableEq ι₂] [DecidableEq ι₃]

/-- The indicator (delta) function at `a`, as a leg vector. -/
def delta (a : ι₁) : ι₁ → F :=
  fun i => if i = a then 1 else 0

/-- The standard-basis expansion: every tensor is the sum of its coefficient
times the delta tensor at each multi-index. This witnesses that `decompSet T`
is nonempty. -/
theorem tensor_eq_sum_stdBasis (T : Tensor3 F ι₁ ι₂ ι₃) :
    T = ∑ x : ι₁ × ι₂ × ι₃,
      simpleTensor (T x • delta (F := F) x.1) (delta x.2.1) (delta x.2.2) := by
  funext ⟨i, j, k⟩
  rw [Finset.sum_apply]
  symm
  rw [Finset.sum_eq_single (i, j, k)]
  · simp [simpleTensor, delta]
  · intro x _ hx
    simp only [simpleTensor, delta, Pi.smul_apply, smul_eq_mul]
    by_cases h1 : i = x.1
    · by_cases h2 : j = x.2.1
      · by_cases h3 : k = x.2.2
        · exact (hx (Prod.ext h1.symm (Prod.ext h2.symm h3.symm))).elim
        · simp [h3]
      · simp [h2]
    · simp [h1]
  · simp

/-- Every tensor has a decomposition into simple tensors, of length the
product of the leg sizes (standard-basis expansion, reindexed by `Fin`). -/
theorem tensorRank_decomp_card (T : Tensor3 F ι₁ ι₂ ι₃) :
    ∃ s : Fin (Fintype.card (ι₁ × ι₂ × ι₃)) → Tensor3 F ι₁ ι₂ ι₃,
      (∀ i, IsSimpleTensor (s i)) ∧ T = ∑ i, s i := by
  classical
  set Idx := ι₁ × ι₂ × ι₃
  set e : Fin (Fintype.card Idx) ≃ Idx := (Fintype.equivFin Idx).symm
  refine ⟨fun j => simpleTensor (T (e j) • delta (F := F) (e j).1)
    (delta (e j).2.1) (delta (e j).2.2), ?_, ?_⟩
  · intro j
    exact ⟨_, _, _, rfl⟩
  · conv_lhs => rw [tensor_eq_sum_stdBasis T]
    exact (Equiv.sum_comp e (fun x : ι₁ × ι₂ × ι₃ =>
      simpleTensor (T x • delta (F := F) x.1) (delta x.2.1) (delta x.2.2))).symm

/-- The decomposition set is nonempty. -/
theorem decompSet_nonempty (T : Tensor3 F ι₁ ι₂ ι₃) : (decompSet T).Nonempty :=
  let ⟨s, hs, hT⟩ := tensorRank_decomp_card T
  ⟨_, s, hs, hT⟩

/-- The standard-basis upper bound: `R(T)` is at most the product of the leg
sizes. -/
theorem tensorRank_le_card (T : Tensor3 F ι₁ ι₂ ι₃) :
    tensorRank T ≤ Fintype.card ι₁ * Fintype.card ι₂ * Fintype.card ι₃ := by
  obtain ⟨s, hs, hT⟩ := tensorRank_decomp_card T
  have hmem : Fintype.card (ι₁ × ι₂ × ι₃) ∈ decompSet T := ⟨s, hs, hT⟩
  rw [Fintype.card_prod, Fintype.card_prod] at hmem
  rw [mul_assoc]
  exact Nat.sInf_le hmem

/-- `R(0) = 0`: the empty sum realizes rank 0. -/
@[simp]
theorem tensorRank_zero : tensorRank (0 : Tensor3 F ι₁ ι₂ ι₃) = 0 := by
  apply Nat.sInf_eq_zero.mpr
  left
  exact ⟨Fin.elim0, fun i => i.elim0, by simp⟩

/-- `R(T) = 0` iff `T = 0`. (Forward: the decomposition set is nonempty, so
`sInf` is attained; a length-0 decomposition sums to the zero tensor.) -/
theorem tensorRank_eq_zero {T : Tensor3 F ι₁ ι₂ ι₃} : tensorRank T = 0 ↔ T = 0 := by
  constructor
  · intro h
    have hmem : tensorRank T ∈ decompSet T := Nat.sInf_mem (decompSet_nonempty T)
    rw [h] at hmem
    obtain ⟨s, -, hT⟩ := hmem
    rw [hT]
    simp
  · intro h
    rw [h]
    exact tensorRank_zero

/-- A simple tensor has rank at most 1. -/
theorem tensorRank_le_one_of_isSimple {T : Tensor3 F ι₁ ι₂ ι₃}
    (h : IsSimpleTensor T) : tensorRank T ≤ 1 := by
  apply Nat.sInf_le
  refine ⟨fun _ => T, fun _ => h, ?_⟩
  simp

/-- **Subadditivity** of tensor rank: `R(T + S) ≤ R(T) + R(S)`, by
concatenating decompositions. -/
theorem tensorRank_add_le (T S : Tensor3 F ι₁ ι₂ ι₃) :
    tensorRank (T + S) ≤ tensorRank T + tensorRank S := by
  classical
  have hT_mem : tensorRank T ∈ decompSet T := Nat.sInf_mem (decompSet_nonempty T)
  have hS_mem : tensorRank S ∈ decompSet S := Nat.sInf_mem (decompSet_nonempty S)
  obtain ⟨sT, hsT, hT⟩ := hT_mem
  obtain ⟨sS, hsS, hS⟩ := hS_mem
  apply Nat.sInf_le
  refine ⟨Fin.append sT sS, ?_, ?_⟩
  · intro i
    refine Fin.addCases ?_ ?_ i
    · intro j
      rw [Fin.append_left]
      exact hsT j
    · intro j
      rw [Fin.append_right]
      exact hsS j
  · have hsplit : (∑ i, Fin.append sT sS i)
        = (∑ i : Fin (tensorRank T), sT i) + ∑ i : Fin (tensorRank S), sS i := by
      rw [Fin.sum_univ_add]
      congr 1
      · exact Finset.sum_congr rfl fun j _ => by rw [Fin.append_left]
      · exact Finset.sum_congr rfl fun j _ => by rw [Fin.append_right]
    rw [hsplit, ← hT, ← hS]

end Finite

end TensorRank

/-! ### The matrix multiplication tensor -/

/-- The **matrix multiplication tensor** `⟨m,n,p⟩`: the structure tensor of
`m×n` times `n×p` matrix multiplication, as a 3-tensor with legs
`Fin m × Fin n` (entries of the first factor), `Fin n × Fin p` (entries of
the second factor), and `Fin p × Fin m` (entries of the result, in the
`Tr(ABC)` convention: the trilinear form is `∑ Aᵢⱼ Bⱼₖ Cₖᵢ`). -/
def matMulTensor (F : Type*) [Field F] (m n p : ℕ) :
    Tensor3 F (Fin m × Fin n) (Fin n × Fin p) (Fin p × Fin m) :=
  fun ((i, j), (j', k), (k', i')) =>
    if j = j' ∧ k = k' ∧ i = i' then 1 else 0

section MatMulTensor

variable {F : Type*} [Field F]

/-- **Sanity check**: contracting `⟨m,n,p⟩` against matrices `A` and `B` on
the first two legs yields the entries of the matrix product `A * B`. -/
theorem matMulTensor_contract {m n p : ℕ} (A : Matrix (Fin m) (Fin n) F)
    (B : Matrix (Fin n) (Fin p) F) (i' : Fin m) (k' : Fin p) :
    ∑ x : Fin m × Fin n, ∑ y : Fin n × Fin p,
      matMulTensor F m n p (x, y, (k', i')) * (A x.1 x.2 * B y.1 y.2)
        = (A * B) i' k' := by
  rw [Matrix.mul_apply]
  simp only [matMulTensor]
  have step1 : ∀ x : Fin m × Fin n,
      ∑ y : Fin n × Fin p,
        (if x.2 = y.1 ∧ y.2 = k' ∧ x.1 = i' then (1 : F) else 0) * (A x.1 x.2 * B y.1 y.2)
          = if x.1 = i' then A x.1 x.2 * B x.2 k' else 0 := by
    intro x
    rw [Fintype.sum_prod_type]
    have e1 : ∀ j' : Fin n, ∀ k : Fin p,
        (if x.2 = j' ∧ k = k' ∧ x.1 = i' then (1 : F) else 0) * (A x.1 x.2 * B j' k)
          = if k = k' then (if x.2 = j' ∧ x.1 = i' then 1 else 0) * (A x.1 x.2 * B j' k')
            else 0 := by
      intro j' k
      by_cases hk : k = k' <;> simp [hk]
    rw [Finset.sum_congr rfl (fun j' _ => Finset.sum_congr rfl (fun k _ => e1 j' k))]
    rw [Finset.sum_congr rfl (fun j' _ => Finset.sum_ite_eq' Finset.univ k' _)]
    simp only [Finset.mem_univ, if_true]
    have e2 : ∀ j' : Fin n,
        (if x.2 = j' ∧ x.1 = i' then (1 : F) else 0) * (A x.1 x.2 * B j' k')
          = if j' = x.2 then (if x.1 = i' then A x.1 x.2 * B x.2 k' else 0) else 0 := by
      intro j'
      by_cases hj : x.2 = j'
      · subst hj
        simp
      · rw [if_neg (fun h => hj h.1), if_neg (Ne.symm hj)]
        simp
    rw [Finset.sum_congr rfl (fun j' _ => e2 j'), Finset.sum_ite_eq' Finset.univ x.2 _]
    simp
  rw [Finset.sum_congr rfl (fun x _ => step1 x), Fintype.sum_prod_type]
  have step2 : ∀ i : Fin m,
      (∑ j : Fin n, if i = i' then A i j * B j k' else 0)
        = if i = i' then ∑ j : Fin n, A i j * B j k' else 0 := by
    intro i
    by_cases hi : i = i' <;> simp [hi]
  rw [Finset.sum_congr rfl (fun i _ => step2 i), Finset.sum_ite_eq' Finset.univ i' _]
  simp

/-- The **naive decomposition**: `⟨m,n,p⟩` is the sum of the `m·n·p` delta
tensors at the triples `((i,j),(j,k),(k,i))`. This is the tensor form of the
naive cubic-time algorithm. -/
theorem matMulTensor_eq_sum_delta {m n p : ℕ} :
    matMulTensor F m n p =
      ∑ x : Fin m × Fin n × Fin p,
        simpleTensor (delta (F := F) (x.1, x.2.1)) (delta (x.2.1, x.2.2))
          (delta (x.2.2, x.1)) := by
  funext ⟨⟨i', j'⟩, ⟨j'', k'⟩, ⟨k'', i''⟩⟩
  simp only [matMulTensor]
  rw [Finset.sum_apply]
  by_cases h : j' = j'' ∧ k' = k'' ∧ i' = i''
  · obtain ⟨rfl, rfl, rfl⟩ := h
    rw [if_pos ⟨rfl, rfl, rfl⟩]
    symm
    rw [Finset.sum_eq_single (i', j', k')]
    · simp [simpleTensor, delta]
    · intro x _ hx
      simp only [simpleTensor, delta]
      by_cases a1 : (i', j') = (x.1, x.2.1)
      · by_cases a2 : (j', k') = (x.2.1, x.2.2)
        · by_cases a3 : (k', i') = (x.2.2, x.1)
          · rw [Prod.mk.injEq] at a1 a2 a3
            exact (hx (Prod.ext a1.1.symm (Prod.ext a1.2.symm a2.2.symm))).elim
          · simp [a3]
        · simp [a2]
      · simp [a1]
    · simp
  · rw [if_neg h]
    symm
    apply Finset.sum_eq_zero
    intro x _
    simp only [simpleTensor, delta]
    by_cases a1 : (i', j') = (x.1, x.2.1)
    · by_cases a2 : (j'', k') = (x.2.1, x.2.2)
      · by_cases a3 : (k'', i'') = (x.2.2, x.1)
        · rw [Prod.mk.injEq] at a1 a2 a3
          exact absurd
            ⟨a1.2.trans a2.1.symm, a2.2.trans a3.1.symm, a1.1.trans a3.2.symm⟩ h
        · simp [a3]
      · simp [a2]
    · simp [a1]

/-- The naive upper bound: `R(⟨m,n,p⟩) ≤ m·n·p`. For square sizes this is the
cubic bound that places `τ = 3` in the exponent set. -/
theorem tensorRank_matMulTensor_le (m n p : ℕ) :
    tensorRank (matMulTensor F m n p) ≤ m * n * p := by
  classical
  apply Nat.sInf_le
  set Idx := Fin m × Fin n × Fin p
  have hcard : Fintype.card Idx = m * n * p := by
    simp [Idx, Fintype.card_prod, mul_assoc]
  set e : Fin (m * n * p) ≃ Idx := (Fintype.equivFinOfCardEq hcard).symm
  refine ⟨fun j => simpleTensor (delta (F := F) ((e j).1, (e j).2.1))
    (delta ((e j).2.1, (e j).2.2)) (delta ((e j).2.2, (e j).1)), ?_, ?_⟩
  · intro j
    exact ⟨_, _, _, rfl⟩
  · rw [matMulTensor_eq_sum_delta]
    exact (Equiv.sum_comp e (fun x : Fin m × Fin n × Fin p =>
      simpleTensor (delta (F := F) (x.1, x.2.1)) (delta (x.2.1, x.2.2))
        (delta (x.2.2, x.1)))).symm

/-- `⟨n,n,n⟩` is nonzero for `n ≥ 1`, so its rank is at least 1. -/
theorem one_le_tensorRank_matMulTensor {n : ℕ} (hn : 0 < n) :
    1 ≤ tensorRank (matMulTensor F n n n) := by
  rw [Nat.one_le_iff_ne_zero, ne_eq, tensorRank_eq_zero]
  intro h
  have h0 := congrFun h ((⟨0, hn⟩, ⟨0, hn⟩), (⟨0, hn⟩, ⟨0, hn⟩), (⟨0, hn⟩, ⟨0, hn⟩))
  simp [matMulTensor] at h0

end MatMulTensor

/-! ### The exponent ω -/

/-- The set of exponents achievable by bilinear algorithms over `F`: `τ`
belongs here if `R(⟨n,n,n⟩) = O(n^τ)` with some constant `C`. -/
def omegaSet (F : Type*) [Field F] : Set ℝ :=
  {τ : ℝ | ∃ C : ℝ, ∀ n : ℕ,
    (tensorRank (matMulTensor F n n n) : ℝ) ≤ C * (n : ℝ) ^ τ}

/-- The **matrix multiplication exponent** `ω` over `F`: the infimum of the
achievable exponents. Well defined because `omegaSet F` is nonempty
(`omegaSet_nonempty`, via the naive cubic algorithm) and bounded below by 0
(`omegaSet_bddBelow`, since `R(⟨n,n,n⟩) ≥ 1` for `n ≥ 1`). -/
noncomputable def matMulOmega (F : Type*) [Field F] : ℝ :=
  sInf (omegaSet F)

section Omega

variable {F : Type*} [Field F]

/-- The naive cubic bound on `R(⟨n,n,n⟩)`, cast to the reals (real-exponent
form, matching `omegaSet`). -/
theorem tensorRank_matMulTensor_le_cube_real (n : ℕ) :
    (tensorRank (matMulTensor F n n n) : ℝ) ≤ (n : ℝ) ^ (3 : ℝ) := by
  have h := tensorRank_matMulTensor_le (F := F) n n n
  have h3 : (n : ℝ) ^ (3 : ℝ) = ((n * n * n : ℕ) : ℝ) := by
    rw [show (3 : ℝ) = ((3 : ℕ) : ℝ) by norm_num, Real.rpow_natCast]
    push_cast
    ring
  rw [h3]
  exact Nat.cast_le.mpr h

/-- The naive cubic algorithm puts `τ = 3` in the exponent set: with `C = 1`,
`R(⟨n,n,n⟩) ≤ n³` for every `n`. -/
theorem omegaSet_nonempty : (omegaSet F).Nonempty := by
  refine ⟨3, 1, fun n => ?_⟩
  rw [one_mul]
  exact tensorRank_matMulTensor_le_cube_real (F := F) n

/-- Every achievable exponent is nonnegative: `R(⟨n,n,n⟩) ≥ 1` for `n ≥ 1`,
but for `τ < 0` the bound `C·n^τ` tends to 0. -/
theorem omegaSet_nonneg_of_mem {τ : ℝ} (hτ : τ ∈ omegaSet F) : 0 ≤ τ := by
  by_contra hlt
  push Not at hlt
  obtain ⟨C, hC⟩ := hτ
  have hC1 : 1 ≤ C := by
    have h1 := hC 1
    rw [Nat.cast_one, Real.one_rpow, mul_one] at h1
    have h1le : (1 : ℝ) ≤ (tensorRank (matMulTensor F 1 1 1) : ℝ) := by
      exact_mod_cast one_le_tensorRank_matMulTensor zero_lt_one
    exact le_trans h1le h1
  have hC0 : 0 ≤ C := by linarith
  -- Take `M ≥ max 1 ⌈C⌉` and `k > -1/τ`; then at `N = (M+1)^k` the bound
  -- `C·N^τ ≤ M/(M+1) < 1` contradicts `R(⟨N,N,N⟩) ≥ 1`.
  set M : ℕ := max 1 ⌈C⌉₊ with hM
  set k : ℕ := ⌈(-1)/τ⌉₊ + 1 with hk
  have hkτ : (k : ℝ) * τ ≤ -1 := by
    have hτ' : (0 : ℝ) < -τ := by linarith
    have hk1 : (-1)/τ ≤ (⌈(-1)/τ⌉₊ : ℝ) := Nat.le_ceil _
    have hk2 : (-1)/τ < (k : ℝ) := by
      refine lt_of_le_of_lt hk1 ?_
      rw [hk, Nat.cast_add, Nat.cast_one]
      exact lt_add_one _
    have hτne : τ ≠ 0 := ne_of_lt hlt
    have hmul : (1 : ℝ) < (k : ℝ) * (-τ) := by
      have h := mul_lt_mul_of_pos_right hk2 hτ'
      rw [show (-1)/τ * -τ = (1 : ℝ) by
        rw [div_mul_eq_mul_div, neg_mul_neg, one_mul, div_self hτne]] at h
      exact h
    have : (k : ℝ) * (-τ) = -((k : ℝ) * τ) := by ring
    linarith
  set N : ℕ := (M + 1) ^ k with hN
  have hNpos : 0 < N := pow_pos (Nat.succ_pos M) k
  have h1N : (1 : ℝ) ≤ (tensorRank (matMulTensor F N N N) : ℝ) := by
    exact_mod_cast one_le_tensorRank_matMulTensor hNpos
  have hNC : (tensorRank (matMulTensor F N N N) : ℝ) ≤ C * (N : ℝ) ^ τ := hC N
  have hCM : C ≤ (M : ℝ) := by
    refine le_trans (Nat.le_ceil _) ?_
    exact_mod_cast Nat.le_max_right 1 ⌈C⌉₊
  have hbase : (1 : ℝ) ≤ (M : ℝ) + 1 := by
    have : (1 : ℝ) ≤ (M : ℝ) := by exact_mod_cast Nat.le_max_left 1 ⌈C⌉₊
    linarith
  have hNτ : (N : ℝ) ^ τ ≤ ((M : ℝ) + 1)⁻¹ := by
    have hcast : (N : ℝ) = ((M : ℝ) + 1) ^ k := by
      rw [hN]
      push_cast
      ring
    rw [hcast, ← Real.rpow_natCast (((M : ℝ) + 1)) k, ← Real.rpow_mul (by positivity)]
    refine le_trans (Real.rpow_le_rpow_of_exponent_le hbase hkτ) ?_
    rw [Real.rpow_neg_one]
  have hbound : C * (N : ℝ) ^ τ ≤ (M : ℝ) / ((M : ℝ) + 1) := by
    calc C * (N : ℝ) ^ τ ≤ C * ((M : ℝ) + 1)⁻¹ := mul_le_mul_of_nonneg_left hNτ hC0
      _ ≤ (M : ℝ) * ((M : ℝ) + 1)⁻¹ :=
          mul_le_mul_of_nonneg_right hCM (inv_nonneg.mpr (by positivity))
      _ = (M : ℝ) / ((M : ℝ) + 1) := by rw [div_eq_mul_inv]
  have hlt1 : (M : ℝ) / ((M : ℝ) + 1) < 1 := by
    rw [div_lt_one (by positivity)]
    linarith
  linarith

/-- The exponent set is bounded below by 0. -/
theorem omegaSet_bddBelow : BddBelow (omegaSet F) :=
  ⟨0, fun _τ hτ => omegaSet_nonneg_of_mem hτ⟩

/-- Exhibiting a bilinear algorithm with exponent `τ` upper-bounds `ω`. -/
theorem matMulOmega_le_of_mem {τ : ℝ}
    (h : ∃ C : ℝ, ∀ n : ℕ,
      (tensorRank (matMulTensor F n n n) : ℝ) ≤ C * (n : ℝ) ^ τ) :
    matMulOmega F ≤ τ :=
  csInf_le omegaSet_bddBelow h

/-- A uniform lower bound on all achievable exponents lower-bounds `ω`.
(Note: `b < τ` for every member does NOT imply `b < ω` — the infimum may be a
cluster point; the useful route to `ω > 2` is a uniform `2 + ε` lower bound
on every member, given by this lemma.) -/
theorem le_matMulOmega_of_forall_le {b : ℝ}
    (h : ∀ τ ∈ omegaSet F, b ≤ τ) : b ≤ matMulOmega F :=
  le_csInf omegaSet_nonempty h

/-- Sanity check: `ω ≤ 3` (the naive cubic algorithm). -/
theorem matMulOmega_le_three : matMulOmega F ≤ 3 := by
  apply matMulOmega_le_of_mem
  refine ⟨1, fun n => ?_⟩
  rw [one_mul]
  exact tensorRank_matMulTensor_le_cube_real (F := F) n

end Omega

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

/-! ## Slot zone: the conjecture and its negation -/

-- @[slot main]
/-- **The matrix multiplication exponent equals 2** (Strassen 1969–, the
central open problem of algebraic complexity): `ω ≤ 2`, i.e. for every
`ε > 0` there is a bilinear algorithm multiplying `n×n` matrices within
`O(n^{2+ε})` arithmetic operations. (Together with the trivial lower bound
`ω ≥ 2`, this is the statement `ω = 2`.) -/
theorem conj :
    matMulOmega ℚ ≤ 2 := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

-- @[slot main]
/-- The negation: `ω > 2` — a super-quadratic lower bound on the exponent of
matrix multiplication (equally open). -/
theorem refuted :
    ¬matMulOmega ℚ ≤ 2 := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

end MatMulOmega
