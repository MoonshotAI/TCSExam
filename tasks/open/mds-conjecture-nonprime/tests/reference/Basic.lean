/-
Statement layer for the **MDS main conjecture over non-prime finite fields**
(Segre's MDS conjecture for linear codes, the open case): a nontrivial
`k`-dimensional linear MDS code of length `n` over the finite field `F_q`
with `q = p^h`, `h ≥ 2`, satisfies `n ≤ q + 1`, unless `q` is even and
`k = 3` or `k = q − 1`, in which case `n ≤ q + 2`.  The prime-order case
(`h = 1`) was proved by Simeon Ball (*On sets of vectors of a finite vector
space in which every subset of basis size is a basis*, JEMS 14(3):733–748,
2012); for non-prime orders the conjecture is open (partial results for
small `k`: Ball–De Beule, Des. Codes Cryptogr. 65:5–14, 2012; checked
against the cited literature).

This file is the task's definition zone plus slot zone:
- The definition zone defines linear codes as subspaces of the coordinate
  space `F^n`, their dimension (`Module.finrank`), the minimum distance
  (minimum Hamming weight of a nonzero codeword, via mathlib's
  `hammingNorm`), the MDS predicate (equality in the Singleton bound,
  `d = n − k + 1`), and the nontriviality range `2 ≤ k ≤ n − 2`; it also
  constructs the repetition code of arbitrary length, proves it is MDS
  (`[n, 1, n]`) and not nontrivial — the reason the conjecture is only
  quantified over nontrivial codes.
- The slot zone states the conjecture (`conj`) and its negation
  (`refuted`), quantified over fields of non-prime order only
  (`¬ Nat.Prime (Fintype.card F)`).  Both proof bodies are left blank.

Fidelity notes:
1. Nontrivial means `2 ≤ k ≤ n − 2` (the excluded ranges are exactly the
   trivial MDS families: `k ≤ 1` repetition-type codes and `k ≥ n − 1`
   their duals, both of arbitrary length).  This is the standard
   formulation, e.g. MacWilliams–Sloane Ch. 11 and current literature
   usage (arXiv:2512.24292, Conjecture 4: "a nontrivial MDS [n,k,d]_q code
   (2 ≤ k ≤ n−2)").
2. The exception clause is exactly `q` even and `k = 3` or `k = q − 1`,
   where the bound becomes `n ≤ q + 2`; both cases are attained by the
   hyperoval codes and their duals, so the clause cannot be dropped.
3. Quantification is over ALL fields whose cardinality is not prime.  A
   finite field's cardinality is a prime power `p^h`, and `p^h` is not
   prime iff `h ≥ 2`, so this is exactly the open case; the prime case is
   settled by Ball's theorem (JEMS 2012) and is deliberately not claimed
   here — the statement says nothing about prime `q` either way.
4. Minimum distance is defined as the minimum Hamming weight of a nonzero
   codeword; for linear codes this equals the minimum Hamming distance
   between distinct codewords by linearity, so the definition matches the
   standard one.  `sInf` over the empty set (the zero code) is `0`, and
   `0 = n − 0 + 1` never holds, so the zero code is never MDS — no
   degenerate MDS code creeps in through the total function.
-/

import Mathlib

open Classical

namespace MDSConjecture

/-- A **linear code** of length `n` over a field `F`: a subspace of the
coordinate space `F^n` (functions `Fin n → F`). -/
structure LinearCode (F : Type*) [Field F] (n : ℕ) where
  /-- the codewords, as a subspace of `F^n` -/
  carrier : Submodule F (Fin n → F)

namespace LinearCode

/-- The **dimension** of a linear code: the dimension of its underlying
subspace. -/
noncomputable def dim {F : Type*} [Field F] {n : ℕ} (C : LinearCode F n) : ℕ :=
  Module.finrank F C.carrier

/-- The **minimum distance** of a linear code: the minimum Hamming weight
(mathlib's `hammingNorm`, the number of nonzero coordinates) of a nonzero
codeword.  For linear codes this coincides with the minimum Hamming
distance between distinct codewords, by linearity.  Defined as `sInf` of
the set of nonzero-codeword weights; it is `0` when the code has no
nonzero codeword. -/
noncomputable def minDist {F : Type*} [Field F] {n : ℕ} (C : LinearCode F n) : ℕ :=
  sInf {w | ∃ v : Fin n → F, v ∈ C.carrier ∧ v ≠ 0 ∧ hammingNorm v = w}

/-- A linear code is **MDS** (maximum distance separable) when its minimum
distance attains the Singleton bound: `d = n − k + 1`. -/
def IsMDS {F : Type*} [Field F] {n : ℕ} (C : LinearCode F n) : Prop :=
  C.minDist = n - C.dim + 1

/-- A linear code is **nontrivial** when `2 ≤ k ≤ n − 2`.  The excluded
ranges are exactly the trivial MDS families, which exist at arbitrary
length: `k ≤ 1` (repetition-type codes; see `repetitionCode_isMDS`) and
`k ≥ n − 1` (their duals, e.g. the single-parity-check code `[n, n−1, 2]`).
The MDS conjecture is only quantified over nontrivial codes. -/
def NonTrivial {F : Type*} [Field F] {n : ℕ} (C : LinearCode F n) : Prop :=
  2 ≤ C.dim ∧ C.dim + 2 ≤ n

end LinearCode

/-! ### The repetition code: a concrete trivial MDS code of arbitrary length -/

/-- The **repetition code** of length `n` over `F`: the line spanned by the
all-ones vector.  It is MDS (`[n, 1, n]`) for every length `n ≥ 1` — the
reason the conjecture must exclude the trivial range of `k`. -/
def repetitionCode (F : Type*) [Field F] (n : ℕ) : LinearCode F n where
  carrier := Submodule.span F {fun _ => 1}

/-- The all-ones vector is nonzero (in positive length). -/
theorem ones_ne_zero {F : Type*} [Field F] {n : ℕ} (hn : 0 < n) :
    (fun _ : Fin n => (1 : F)) ≠ 0 := by
  intro h
  have h1 := congrFun h ⟨0, hn⟩
  simp at h1

/-- The repetition code has dimension `1`. -/
theorem repetitionCode_dim {F : Type*} [Field F] {n : ℕ} (hn : 0 < n) :
    (repetitionCode F n).dim = 1 :=
  finrank_span_singleton (ones_ne_zero hn)

/-- Unfolding lemma for the carrier of the repetition code. -/
theorem repetitionCode_carrier {F : Type*} [Field F] {n : ℕ} :
    (repetitionCode F n).carrier = Submodule.span F {fun _ => (1 : F)} := rfl

/-- Every nonzero codeword of the repetition code has all coordinates
nonzero, so the minimum distance is the full length `n`. -/
theorem repetitionCode_minDist {F : Type*} [Field F] {n : ℕ} (hn : 0 < n) :
    (repetitionCode F n).minDist = n := by
  have hone : hammingNorm (fun _ : Fin n => (1 : F)) = n := by
    have hfilter : (Finset.univ.filter fun i : Fin n => (fun _ => (1 : F)) i ≠ 0) =
        Finset.univ := by
      ext i
      simp
    unfold hammingNorm
    rw [hfilter, Finset.card_univ, Fintype.card_fin]
  have hset : {w | ∃ v : Fin n → F, v ∈ (repetitionCode F n).carrier ∧ v ≠ 0 ∧
      hammingNorm v = w} = {n} := by
    ext w
    constructor
    · rintro ⟨v, hv, hv0, rfl⟩
      rw [repetitionCode_carrier, Submodule.mem_span_singleton] at hv
      obtain ⟨c, rfl⟩ := hv
      have hc : c ≠ 0 := by
        rintro rfl
        simp at hv0
      rw [Set.mem_singleton_iff]
      have hfilter : (Finset.univ.filter fun i : Fin n =>
          (c • fun _ => (1 : F)) i ≠ 0) = Finset.univ := by
        ext i
        simp [Pi.smul_apply, smul_eq_mul, hc]
      unfold hammingNorm
      rw [hfilter, Finset.card_univ, Fintype.card_fin]
    · intro hw
      rw [Set.mem_singleton_iff] at hw
      subst hw
      exact ⟨fun _ => 1, Submodule.subset_span (Set.mem_singleton _),
        ones_ne_zero hn, hone⟩
  show sInf {w | ∃ v : Fin n → F, v ∈ (repetitionCode F n).carrier ∧ v ≠ 0 ∧
      hammingNorm v = w} = n
  rw [hset]
  have hmem : sInf ({n} : Set ℕ) ∈ ({n} : Set ℕ) :=
    Nat.sInf_mem (Set.singleton_nonempty n)
  rwa [Set.mem_singleton_iff] at hmem

/-- The repetition code is MDS: `d = n = n − 1 + 1`. -/
theorem repetitionCode_isMDS {F : Type*} [Field F] {n : ℕ} (hn : 0 < n) :
    (repetitionCode F n).IsMDS := by
  show (repetitionCode F n).minDist = n - (repetitionCode F n).dim + 1
  rw [repetitionCode_minDist hn, repetitionCode_dim hn]
  exact (Nat.sub_add_cancel hn).symm

/-- ... and it is not nontrivial (`k = 1 < 2`): trivial MDS codes exist at
every length, which is why the conjecture is quantified over the
nontrivial range only. -/
theorem repetitionCode_not_nontrivial {F : Type*} [Field F] {n : ℕ} (hn : 0 < n) :
    ¬ (repetitionCode F n).NonTrivial := by
  intro h
  obtain ⟨h1, _⟩ := h
  rw [repetitionCode_dim hn] at h1
  omega

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

/-! ## Slot zone: the conjecture and its negation -/

-- @[slot main]
/-- **The MDS main conjecture over non-prime finite fields** (Segre's MDS
conjecture, the open case `q = p^h` with `h ≥ 2`): every nontrivial
`k`-dimensional linear MDS code of length `n` over a finite field `F` of
non-prime order `q = |F|` satisfies `n ≤ q + 1`, unless `q` is even and
`k = 3` or `k = q − 1`, in which case `n ≤ q + 2`.  (Over fields of prime
order the same bound is Ball's theorem, JEMS 2012; this statement is only
quantified over non-prime orders and says nothing about the prime case.) -/
theorem conj :
    ∀ {F : Type} [Field F] [Fintype F], ¬ Nat.Prime (Fintype.card F) →
      ∀ {n : ℕ} (C : LinearCode F n), C.NonTrivial → C.IsMDS →
        n ≤ Fintype.card F + 1 ∨
          (Even (Fintype.card F) ∧ (C.dim = 3 ∨ C.dim = Fintype.card F - 1) ∧
            n ≤ Fintype.card F + 2) := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

-- @[slot main]
/-- The negation of the MDS main conjecture over non-prime finite fields. -/
theorem refuted :
    ¬∀ {F : Type} [Field F] [Fintype F], ¬ Nat.Prime (Fintype.card F) →
        ∀ {n : ℕ} (C : LinearCode F n), C.NonTrivial → C.IsMDS →
          n ≤ Fintype.card F + 1 ∨
            (Even (Fintype.card F) ∧ (C.dim = 3 ∨ C.dim = Fintype.card F - 1) ∧
              n ≤ Fintype.card F + 2) := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

end MDSConjecture
