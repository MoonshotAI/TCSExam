/-
Statement layer for the permanent-vs-determinant problem (Valiant 1979,
*The complexity of computing the permanent*, Theoret. Comput. Sci. 8,
189–201): the n×n permanent perm_n cannot be written as the determinant of a
matrix of polynomial size (n^{O(1)}) whose entries are affine linear forms in
the original variables — the determinantal complexity dc(perm_n) grows
superpolynomially. Best known bounds: dc(perm_n) ≥ n²/2 (Mignon–Ressayre
2004) and dc(perm_n) ≤ 2^n − 1 (Grenet 2011); already dc(perm_4) is unknown
(9 ≤ dc(perm_4) ≤ 15; the lower bound is due to Alper–Bogart–Velasco 2015).

This file is the task's definition zone plus slot zone:
- The definition zone defines the permanent as a polynomial (`permPoly n`,
  via mathlib's `Matrix.permanent` of the generic variable matrix),
  determinantal representations (`IsDetRepr`: a matrix of affine linear
  forms, i.e. entries of total degree ≤ 1, whose determinant is the target
  polynomial), determinantal complexity (`detComp`: the least representation
  size), and the conjecture predicate (`SuperpolyDc`). It also proves the
  API lemmas: the permanent's total degree is n, the degree bound for
  determinants of affine matrices, and the explicit small-n expansions.
- The slot zone states the conjecture (`conj`) and its negation (`refuted`).
  Both proof bodies are left blank.

Fidelity notes (see `tests/reference/concept-ledger.md` of the packaged
task):
1. The base field is ℝ (characteristic 0), the standard setting of the
   Mignon–Ressayre lower bound.
2. "Affine linear form" is formalized as `totalDegree ≤ 1`, which over ℝ is
   exactly "a constant plus a linear combination of the variables".
3. `detComp` is `Nat.sInf` of the representation sizes; the conjecture only
   makes superpolynomial lower-bound claims about it, so the empty case
   (no representation) cannot make the conjecture vacuously true: a
   polynomial with no representation has dc = 0, and 0 is never > n^c.
-/

import Mathlib

open MvPolynomial

namespace PermVsDet

/-! ### The permanent as a polynomial -/

/-- The generic n×n variable matrix: entry (i, j) is the variable X_{(i,j)}. -/
noncomputable def varMatrix (n : ℕ) : Matrix (Fin n) (Fin n) (MvPolynomial (Fin n × Fin n) ℝ) :=
  Matrix.of fun i j => X (i, j)

/-- The n×n permanent as a polynomial in its n² variables over ℝ:
the permanent (mathlib `Matrix.permanent`) of the generic variable matrix. -/
noncomputable def permPoly (n : ℕ) : MvPolynomial (Fin n × Fin n) ℝ :=
  (varMatrix n).permanent

/-! ### Determinantal representations and determinantal complexity -/

/-- An m×m determinantal representation of the polynomial `f`: a matrix
whose entries are affine linear forms (polynomials of total degree ≤ 1) in
the variables of `f`, and whose determinant equals `f`. -/
def IsDetRepr {σ : Type*} (f : MvPolynomial σ ℝ) (m : ℕ) : Prop :=
  ∃ A : Matrix (Fin m) (Fin m) (MvPolynomial σ ℝ),
    (∀ i j, (A i j).totalDegree ≤ 1) ∧ A.det = f

/-- The determinantal complexity dc(f): the least size of a determinantal
representation of `f` (with the convention 0 when no representation exists;
the conjecture only claims lower bounds, which this convention never
satisfies spuriously — a polynomial with no representation has dc = 0, and
0 is never > n^c). -/
noncomputable def detComp {σ : Type*} (f : MvPolynomial σ ℝ) : ℕ :=
  sInf {m | IsDetRepr f m}

/-! ### The conjecture -/

/-- **The permanent-vs-determinant conjecture** (Valiant 1979): the
determinantal complexity of the permanent is not bounded by any polynomial —
for every exponent c there are arbitrarily large n with
dc(perm_n) > n^c. -/
def SuperpolyDc : Prop :=
  ∀ c N : ℕ, ∃ n : ℕ, N ≤ n ∧ n ^ c < detComp (permPoly n)

/-! ### API: the permanent's total degree -/

/-- Each permutation summand of the permanent has total degree at most n. -/
theorem totalDegree_permPoly_le (n : ℕ) : (permPoly n).totalDegree ≤ n := by
  rw [permPoly, Matrix.permanent]
  refine MvPolynomial.totalDegree_finsetSum_le fun σ _ => ?_
  calc (∏ i, varMatrix n (σ i) i).totalDegree
      ≤ ∑ i, (varMatrix n (σ i) i).totalDegree :=
        MvPolynomial.totalDegree_finsetProd _ _
    _ = ∑ _i : Fin n, 1 := by
        refine Finset.sum_congr rfl fun i _ => ?_
        simp [varMatrix, MvPolynomial.totalDegree_X]
    _ = n := by simp

/-- The product of the variables picked by a permutation is the corresponding
monomial with coefficient 1. -/
theorem prod_varMatrix_eq_monomial {n : ℕ} (σ : Equiv.Perm (Fin n)) (s : Finset (Fin n)) :
    ∏ i ∈ s, varMatrix n (σ i) i =
      MvPolynomial.monomial (∑ i ∈ s, Finsupp.single (σ i, i) 1) 1 := by
  induction s using Finset.induction with
  | empty => simp
  | insert a s ha ih =>
    rw [Finset.prod_insert ha, ih]
    simp only [varMatrix, Matrix.of_apply]
    rw [← pow_one (X (σ a, a)), MvPolynomial.X_pow_eq_monomial, MvPolynomial.monomial_mul,
      mul_one, Finset.sum_insert ha]

/-- Two permutation monomials coincide with the diagonal one only for the
identity permutation. -/
theorem diag_sum_eq_iff {n : ℕ} (σ : Equiv.Perm (Fin n)) :
    (∑ i : Fin n, Finsupp.single (σ i, i) 1) = (∑ i : Fin n, Finsupp.single (i, i) 1) ↔
      σ = 1 := by
  constructor
  · intro h
    apply Equiv.ext
    intro i
    show σ i = i
    by_contra hi
    have h1 : (1 : ℕ) ≤ (∑ j : Fin n, Finsupp.single (σ j, j) 1) (σ i, i) := by
      rw [Finsupp.finsetSum_apply]
      have hle := Finset.single_le_sum (s := Finset.univ)
        (f := fun j => Finsupp.single (σ j, j) 1 (σ i, i)) (fun j _ => zero_le)
        (Finset.mem_univ i)
      rwa [Finsupp.single_eq_same] at hle
    rw [h, Finsupp.finsetSum_apply] at h1
    have hz : ∑ j : Fin n, Finsupp.single (j, j) 1 (σ i, i) = 0 := by
      apply Finset.sum_eq_zero
      intro j _
      rw [Finsupp.single_apply]
      split_ifs with hp
      · obtain ⟨hjl, hjr⟩ := Prod.mk.inj hp
        exact (hi (hjl.symm.trans hjr)).elim
      · rfl
    rw [hz] at h1
    exact (Nat.not_succ_le_zero 0 h1).elim
  · intro h
    rw [h]
    rfl

/-- The diagonal monomial `∏ i X_{(i,i)}` has coefficient 1 in the permanent;
in particular the permanent is nonzero (the permutation monomials do not
cancel). -/
theorem coeff_permPoly_diag (n : ℕ) :
    (permPoly n).coeff (∑ i : Fin n, Finsupp.single (i, i) 1) = 1 := by
  classical
  rw [permPoly, Matrix.permanent, MvPolynomial.coeff_sum]
  simp only [prod_varMatrix_eq_monomial, MvPolynomial.coeff_monomial, diag_sum_eq_iff,
    Finset.sum_ite_eq', Finset.mem_univ, if_true]

/-- The permanent of the n×n variable matrix has total degree n. -/
theorem totalDegree_permPoly (n : ℕ) : (permPoly n).totalDegree = n := by
  apply le_antisymm (totalDegree_permPoly_le n)
  have hmem : (∑ i : Fin n, Finsupp.single (i, i) 1) ∈ (permPoly n).support := by
    rw [MvPolynomial.mem_support_iff, coeff_permPoly_diag]
    exact one_ne_zero
  have hsum : ((∑ i : Fin n, Finsupp.single (i, i) 1).sum fun _ e => e) = n := by
    rw [Finsupp.sum_fintype _ _ (fun _ => rfl)]
    simp only [Finsupp.finsetSum_apply, Finsupp.single_apply]
    rw [Finset.sum_comm]
    simp
  have hle := MvPolynomial.le_totalDegree hmem
  rwa [hsum] at hle

/-! ### API: degree bound for determinants with affine entries -/

/-- The determinant of an m×m matrix of affine linear forms has total degree
at most m. -/
theorem totalDegree_det_le {σ : Type*} {m : ℕ}
    {A : Matrix (Fin m) (Fin m) (MvPolynomial σ ℝ)}
    (hA : ∀ i j, (A i j).totalDegree ≤ 1) : A.det.totalDegree ≤ m := by
  rw [Matrix.det_apply]
  refine MvPolynomial.totalDegree_finsetSum_le fun τ _ => ?_
  calc ((Equiv.Perm.sign τ) • ∏ i, A (τ i) i).totalDegree
      ≤ (∏ i, A (τ i) i).totalDegree := MvPolynomial.totalDegree_smul_le _ _
    _ ≤ ∑ i, (A (τ i) i).totalDegree := MvPolynomial.totalDegree_finsetProd _ _
    _ ≤ ∑ _i : Fin m, 1 := Finset.sum_le_sum fun i _ => hA (τ i) i
    _ = m := by simp

/-! ### API: explicit small-n expansions of the permanent -/

/-- The 2×2 permanent as an explicit polynomial: X₀₀X₁₁ + X₁₀X₀₁. -/
theorem permPoly_two :
    permPoly 2 = X ((0 : Fin 2), (0 : Fin 2)) * X (1, 1) + X (1, 0) * X (0, 1) := by
  rw [permPoly, Matrix.permanent, Finset.univ_perm_fin_succ, Finset.sum_map,
    Fintype.sum_prod_type]
  simp [Fin.sum_univ_two, Fin.prod_univ_two, varMatrix]

/-- The 3×3 permanent as an explicit polynomial (six monomials). -/
theorem permPoly_three :
    permPoly 3 = X ((0 : Fin 3), (0 : Fin 3)) * X (1, 1) * X (2, 2)
      + X (0, 1) * X (1, 0) * X (2, 2)
      + X (0, 0) * X (1, 2) * X (2, 1)
      + X (0, 2) * X (1, 0) * X (2, 1)
      + X (0, 1) * X (1, 2) * X (2, 0)
      + X (0, 2) * X (1, 1) * X (2, 0) := by
  rw [permPoly, Matrix.permanent, Finset.univ_perm_fin_succ, Finset.sum_map,
    Fintype.sum_prod_type]
  simp_rw [Finset.univ_perm_fin_succ, Finset.sum_map, Fintype.sum_prod_type]
  have h2 : ∀ (e : Equiv.Perm (Fin 2)) (p : Fin 3),
      Equiv.Perm.decomposeFin.symm (p, e) 2 = Equiv.swap 0 p (e 1).succ := by
    intro e p
    rw [← Fin.succ_one_eq_two]
    exact Equiv.Perm.decomposeFin_symm_apply_succ e p 1
  simp [Fin.sum_univ_three, Fin.sum_univ_two, Fin.prod_univ_three, h2, Equiv.swap_apply_def,
    varMatrix]
  ring

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

/-! ## Slot zone: the conjecture and its negation -/

-- @[slot main]
/-- **The permanent-vs-determinant conjecture** (Valiant 1979): dc(perm_n) is
not polynomially bounded. -/
theorem conj : SuperpolyDc := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

-- @[slot main]
/-- The negation of the conjecture: dc(perm_n) is eventually bounded by some
monomial n^c. -/
theorem refuted : ¬SuperpolyDc := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

end PermVsDet
