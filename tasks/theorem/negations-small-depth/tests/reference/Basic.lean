/-
Self-contained statement layer for a theorem in arithmetic complexity:
an explicit polynomial with a polynomial-size arithmetic formula but
only exponential-size monotone arithmetic formulas.

The fixed part (everything above the end-of-fixed-part marker line) is
the definition layer the main theorem's statement needs: arithmetic
formulas (`ACirc`) with size, computed polynomial and monotonicity, the
graph polynomial `graphPoly G` on the variable set `Fin n × Bool`,
set-multilinearity, the Boolean function `fG`, the spectral expander
predicate `IsExpander`, balanced rectangles and balanced monotone pairs,
and a random-matching existence statement packaged as the hypothesis
`expanderMatchingProp` (per-degree constants). Fidelity notes live in
`tests/reference/`.
-/

import Mathlib

set_option linter.unusedSectionVars false

namespace NegationsSmallDepth

open Finset

/-! ## Part 1: arithmetic formulas -/

/-- An arithmetic formula on variable set `σ`: variables, real constants,
and `+` / `-` / `×` gates (tree-shaped). -/
inductive ACirc (σ : Type*) where
  | var : σ → ACirc σ
  | const : ℝ → ACirc σ
  | add : ACirc σ → ACirc σ → ACirc σ
  | sub : ACirc σ → ACirc σ → ACirc σ
  | mul : ACirc σ → ACirc σ → ACirc σ

namespace ACirc

/-- The size of a formula: the number of gates, with duplicated
subformulas counted repeatedly. -/
def size {σ : Type*} : ACirc σ → ℕ
  | .var _ => 1
  | .const _ => 1
  | .add l r => l.size + r.size + 1
  | .sub l r => l.size + r.size + 1
  | .mul l r => l.size + r.size + 1

/-- The polynomial computed by a formula. -/
noncomputable def toPoly {σ : Type*} : ACirc σ → MvPolynomial σ ℝ
  | .var s => MvPolynomial.X s
  | .const r => MvPolynomial.C r
  | .add l r => l.toPoly + r.toPoly
  | .sub l r => l.toPoly - r.toPoly
  | .mul l r => l.toPoly * r.toPoly

/-- Monotonicity: no subtraction gate, and every constant is
non-negative. -/
inductive IsMonotone {σ : Type*} : ACirc σ → Prop
  | var (s : σ) : IsMonotone (.var s)
  | const {r : ℝ} (hr : 0 ≤ r) : IsMonotone (.const r)
  | add {l r : ACirc σ} : IsMonotone l → IsMonotone r → IsMonotone (.add l r)
  | mul {l r : ACirc σ} : IsMonotone l → IsMonotone r → IsMonotone (.mul l r)

/-- A monotone formula computes a polynomial with non-negative
coefficients. -/
theorem coeff_nonneg_of_monotone {σ : Type*} [DecidableEq σ] {C : ACirc σ}
    (h : C.IsMonotone) (m : σ →₀ ℕ) : 0 ≤ (C.toPoly).coeff m := by
  induction h generalizing m with
  | var s =>
      simp only [toPoly]
      rw [MvPolynomial.coeff_X]
      split_ifs <;> norm_num
  | const hr =>
      simp only [toPoly]
      rw [MvPolynomial.coeff_C]
      split_ifs
      · exact hr
      · norm_num
  | add _ _ ihl ihr =>
      simp only [toPoly]
      rw [MvPolynomial.coeff_add]
      exact add_nonneg (ihl m) (ihr m)
  | mul _ _ ihl ihr =>
      simp only [toPoly]
      rw [MvPolynomial.coeff_mul]
      exact Finset.sum_nonneg fun x _ => mul_nonneg (ihl x.1) (ihr x.2)

/-- Folding a family of formulas into one sum formula: the computed
polynomial is the sum, and the size is bounded by the sum of the sizes
plus the number of summands and the base constant. -/
theorem sumOver_exists {ι σ : Type*} (s : Finset ι) (f : ι → ACirc σ) :
    ∃ F : ACirc σ, F.toPoly = ∑ i ∈ s, (f i).toPoly ∧
      F.size ≤ (∑ i ∈ s, (f i).size) + s.card + 1 ∧
      ((∀ i ∈ s, (f i).IsMonotone) → F.IsMonotone) := by
  classical
  refine s.induction_on ?_ ?_
  · exact ⟨.const 0, by simp [toPoly], by simp [size], fun _ => IsMonotone.const le_rfl⟩
  · rintro i s hi ⟨F, hF, hsz, hmono⟩
    refine ⟨.add (f i) F, ?_, ?_, ?_⟩
    · simp only [toPoly, hF, Finset.sum_insert hi]
    · simp only [size]
      rw [Finset.sum_insert hi, Finset.card_insert_of_notMem hi]
      omega
    · intro hm
      exact IsMonotone.add (hm i (Finset.mem_insert_self i s))
        (hmono fun j hj => hm j (Finset.mem_insert_of_mem hj))

/-- Folding a family of formulas into one product formula. -/
theorem prodOver_exists {ι σ : Type*} (s : Finset ι) (f : ι → ACirc σ) :
    ∃ F : ACirc σ, F.toPoly = ∏ i ∈ s, (f i).toPoly ∧
      F.size ≤ (∑ i ∈ s, (f i).size) + s.card + 1 ∧
      ((∀ i ∈ s, (f i).IsMonotone) → F.IsMonotone) := by
  classical
  refine s.induction_on ?_ ?_
  · exact ⟨.const 1, by simp [toPoly], by simp [size], fun _ => IsMonotone.const zero_le_one⟩
  · rintro i s hi ⟨F, hF, hsz, hmono⟩
    refine ⟨.mul (f i) F, ?_, ?_, ?_⟩
    · simp only [toPoly, hF, Finset.prod_insert hi]
    · simp only [size]
      rw [Finset.sum_insert hi, Finset.card_insert_of_notMem hi]
      omega
    · intro hm
      exact IsMonotone.mul (hm i (Finset.mem_insert_self i s))
        (hmono fun j hj => hm j (Finset.mem_insert_of_mem hj))

end ACirc

/-! ## Part 2: the graph polynomial and its support -/

/-- The number of edges of `G` with both endpoints in `S` (the edge count
of the induced subgraph `G[S]`), realized by ordered pairs `u < v`. -/
def edgeCount {n : ℕ} (G : SimpleGraph (Fin n)) [DecidableRel G.Adj]
    (S : Finset (Fin n)) : ℕ :=
  ((Finset.univ : Finset (Fin n × Fin n)).filter fun e =>
    e.1 < e.2 ∧ G.Adj e.1 e.2 ∧ e.1 ∈ S ∧ e.2 ∈ S).card

/-- The support of a Boolean assignment, as a subset of the indices. -/
def suppOf {n : ℕ} (a : Fin n → Bool) : Finset (Fin n) :=
  Finset.univ.filter fun i => a i = true

/-- The exponent vector of the set-multilinear monomial `∏ᵢ x_{i,aᵢ}`. -/
noncomputable def expVec {n : ℕ} (a : Fin n → Bool) : (Fin n × Bool) →₀ ℕ :=
  ∑ i : Fin n, Finsupp.single (i, a i) 1

/-- The coordinates of `expVec a`: it is `1` exactly at `(i, a i)`. -/
theorem expVec_apply {n : ℕ} (a : Fin n → Bool) (j : Fin n) (b : Bool) :
    expVec a (j, b) = (if a j = b then 1 else 0) := by
  classical
  show (∑ i : Fin n, Finsupp.single (i, a i) 1) (j, b) = _
  rw [Finsupp.finsetSum_apply, Finset.sum_eq_single j]
  · rw [Finsupp.single_apply]
    by_cases h : a j = b <;> simp [h, Prod.ext_iff]
  · intro i _ hij
    rw [Finsupp.single_apply,
      if_neg (fun h => hij (congrArg Prod.fst h))]
  · intro h; simp at h

/-- `expVec` is injective: the monomial determines the assignment. -/
theorem expVec_injective {n : ℕ} : Function.Injective (expVec : (Fin n → Bool) → _) := by
  intro a b hab
  funext j
  have ht : expVec a (j, true) = expVec b (j, true) := Finsupp.ext_iff.1 hab _
  rw [expVec_apply, expVec_apply] at ht
  cases ha : a j <;> cases hb : b j <;> simp [ha, hb] at ht ⊢

/-- The monomial with exponent vector `expVec a` is the product
`∏ᵢ X (i, a i)`. -/
theorem monomial_expVec {n : ℕ} (a : Fin n → Bool) :
    MvPolynomial.monomial (expVec a) (1 : ℝ) = ∏ i : Fin n, MvPolynomial.X (i, a i) := by
  classical
  have hmul : ∀ x y : (Fin n × Bool) →₀ ℕ,
      MvPolynomial.monomial (x + y) (1 : ℝ) =
        MvPolynomial.monomial x 1 * MvPolynomial.monomial y 1 := by
    intro x y
    rw [MvPolynomial.monomial_mul, mul_one]
  have h0 : MvPolynomial.monomial (0 : (Fin n × Bool) →₀ ℕ) (1 : ℝ) = 1 := by
    have h : (MvPolynomial.monomial (0 : (Fin n × Bool) →₀ ℕ)) (1 : ℝ) =
        MvPolynomial.C (1 : ℝ) := congrFun MvPolynomial.monomial_zero' _
    rw [h]; exact map_one _
  have key : ∀ s : Finset (Fin n),
      MvPolynomial.monomial (∑ i ∈ s, Finsupp.single (i, a i) 1) (1 : ℝ) =
        ∏ i ∈ s, MvPolynomial.X (i, a i) := by
    intro s
    induction s using Finset.induction_on with
    | empty => rw [Finset.sum_empty, Finset.prod_empty, h0]
    | insert a₀ s hi ih =>
      rw [Finset.sum_insert hi, hmul, ih, Finset.prod_insert hi]
      try rfl
  exact key Finset.univ

/-- The graph polynomial:
`P_G = Σ_{a ∈ {0,1}ⁿ} (e(G[supp a]) − 1)² · ∏ᵢ x_{i,aᵢ}` (the sum inside
the square is the edge count). -/
noncomputable def graphPoly {n : ℕ} (G : SimpleGraph (Fin n)) [DecidableRel G.Adj] :
    MvPolynomial (Fin n × Bool) ℝ :=
  ∑ a : Fin n → Bool,
    MvPolynomial.monomial (expVec a) (((edgeCount G (suppOf a) : ℝ) - 1) ^ 2)

/-- The Boolean function: `fG a = 1` iff the induced subgraph on the
support of `a` does not have exactly one edge. -/
def fG {n : ℕ} (G : SimpleGraph (Fin n)) [DecidableRel G.Adj] (a : Fin n → Bool) : Bool :=
  decide (edgeCount G (suppOf a) ≠ 1)

/-- Set-multilinearity with respect to the partition into the pairs
`{(i,false), (i,true)}`: every monomial of `P` contains exactly one
variable of each pair, to the first power. -/
def IsSetMultilinear {n : ℕ} (P : MvPolynomial (Fin n × Bool) ℝ) : Prop :=
  ∀ m ∈ P.support, ∀ i : Fin n, m (i, false) + m (i, true) = 1

/-- The graph polynomial is set-multilinear: its support is contained in
the image of `expVec`. -/
theorem graphPoly_isSetMultilinear {n : ℕ} (G : SimpleGraph (Fin n))
    [DecidableRel G.Adj] : IsSetMultilinear (graphPoly G) := by
  classical
  intro m hm i
  have hm' : m ∈ (∑ a : Fin n → Bool, MvPolynomial.monomial (expVec a)
      (((edgeCount G (suppOf a) : ℝ) - 1) ^ 2)).support := hm
  have h1 := MvPolynomial.support_sum
    (s := (Finset.univ : Finset (Fin n → Bool)))
    (f := fun a : Fin n → Bool => MvPolynomial.monomial (expVec a)
      (((edgeCount G (suppOf a) : ℝ) - 1) ^ 2)) hm'
  rw [Finset.mem_biUnion] at h1
  rcases h1 with ⟨a, -, ha⟩
  rw [MvPolynomial.support_monomial] at ha
  split at ha
  · simp at ha
  · rw [Finset.mem_singleton] at ha
    subst ha
    rw [expVec_apply, expVec_apply]
    by_cases h : a i = true <;> simp [h]

/-! ## Part 3: expanders and the packaged matching lemma -/

/-- The adjacency matrix of `G` as a real matrix. -/
def adjMatrix {n : ℕ} (G : SimpleGraph (Fin n)) [DecidableRel G.Adj] :
    Matrix (Fin n) (Fin n) ℝ :=
  fun i j => if G.Adj i j then 1 else 0

/-- The adjacency matrix is Hermitian (symmetric). -/
theorem adjMatrix_isHermitian {n : ℕ} (G : SimpleGraph (Fin n)) [DecidableRel G.Adj] :
    (adjMatrix G).IsHermitian := by
  classical
  rw [Matrix.IsHermitian.ext_iff]
  intro i j
  show star (if G.Adj j i then (1 : ℝ) else 0) = if G.Adj i j then (1 : ℝ) else 0
  by_cases h : G.Adj i j
  · rw [if_pos h, if_pos (G.adj_symm h)]; simp
  · rw [if_neg h, if_neg (mt G.adj_symm h)]; simp

/-- The spectral expander predicate: `G` is `d`-regular with `2 ≤ d`,
and at most one eigenvalue of the adjacency matrix exceeds `d^{3/4}` in
absolute value (equivalently the second largest absolute eigenvalue is at
most `d^{3/4}`, the largest being `d`). -/
def IsExpander {n : ℕ} (G : SimpleGraph (Fin n)) [DecidableRel G.Adj] (d : ℕ) : Prop :=
  G.IsRegularOfDegree d ∧ 2 ≤ d ∧
    ((Finset.univ.filter fun i =>
      |(adjMatrix_isHermitian G).eigenvalues i| >
        (d : ℝ) ^ ((3 : ℝ) / 4)).card ≤ 1)

/-- An edge of the complete graph on `Fin n`, as an ordered pair
`u < v` (avoids `Sym2` API). -/
def GraphEdge (n : ℕ) := { e : Fin n × Fin n // e.1 < e.2 }

instance (n : ℕ) : Fintype (GraphEdge n) :=
  Subtype.fintype (fun e : Fin n × Fin n => e.1 < e.2)

/-- `M` is an induced matching of `G`: every edge of `M` is an edge of
`G`, distinct edges of `M` share no endpoint, and there is no `G`-edge
between the endpoints of two different matching edges. -/
def IsInducedMatching {n : ℕ} (G : SimpleGraph (Fin n)) [DecidableRel G.Adj]
    (M : Finset (GraphEdge n)) : Prop :=
  (∀ e ∈ M, G.Adj e.1.1 e.1.2) ∧
  (∀ e₁ ∈ M, ∀ e₂ ∈ M,
    e₁.1.1 = e₂.1.1 ∨ e₁.1.1 = e₂.1.2 ∨ e₁.1.2 = e₂.1.1 ∨ e₁.1.2 = e₂.1.2 →
    e₁ = e₂) ∧
  (∀ e₁ ∈ M, ∀ e₂ ∈ M, e₁ ≠ e₂ →
    ¬ G.Adj e₁.1.1 e₂.1.1 ∧ ¬ G.Adj e₁.1.1 e₂.1.2 ∧
    ¬ G.Adj e₁.1.2 e₂.1.1 ∧ ¬ G.Adj e₁.1.2 e₂.1.2)

/-- The number of matching edges crossing the cut `(Y, Yᶜ)`. -/
def crossingCount {n : ℕ} (G : SimpleGraph (Fin n)) [DecidableRel G.Adj]
    (M : Finset (GraphEdge n)) (Y : Finset (Fin n)) : ℕ :=
  (M.filter fun e =>
    (e.1.1 ∈ Y ∧ e.1.2 ∉ Y) ∨ (e.1.1 ∉ Y ∧ e.1.2 ∈ Y)).card

/-- The random-matching existence lemma, packaged as a hypothesis: for
every degree `d ≥ 2` there are constants `α, γ > 0` such that on every
`n`-vertex `d`-regular expander there is a probability weight on edge
sets which is supported on induced matchings of size `⌈αn⌉`, and for
every balanced partition `Y ⊔ Z = [n]` the mass of the event "at most
`γ⌈αn⌉` crossing edges" is at most `exp(−γ⌈αn⌉)`. The constants are
per-degree. -/
def expanderMatchingProp : Prop :=
  ∀ d : ℕ, 2 ≤ d → ∃ α γ : ℝ, 0 < α ∧ α ≤ 1 ∧ 0 < γ ∧ γ ≤ 1 ∧
    ∀ (n : ℕ) (G : SimpleGraph (Fin n)) [DecidableRel G.Adj], IsExpander G d →
      ∃ μ : Finset (GraphEdge n) → ℝ,
        (∀ M, 0 ≤ μ M) ∧
        (∑ M : Finset (GraphEdge n), μ M) = 1 ∧
        (∀ M, μ M ≠ 0 → IsInducedMatching G M ∧ M.card = ⌈α * n⌉₊) ∧
        ∀ Y Z : Finset (Fin n), Disjoint Y Z → Y ∪ Z = Finset.univ →
          n ≤ 3 * Y.card → 3 * Y.card < 2 * n →
          n ≤ 3 * Z.card → 3 * Z.card < 2 * n →
          (∑ M : Finset (GraphEdge n),
            if (crossingCount G M Y : ℝ) ≤ γ * ⌈α * n⌉₊ then μ M else 0) ≤
            Real.exp (-γ * ⌈α * n⌉₊)

/-! ## Part 4: balanced rectangles -/

/-- A balanced rectangle over the index set `[n]`: a partition
`Y ⊔ Z = [n]` with both sides in `[n/3, 2n/3)`, and families `𝒴 ⊆ P(Y)`,
`𝒵 ⊆ P(Z)`; its elements are the unions `S ∪ T`. -/
structure BalancedRectangle (n : ℕ) where
  Y : Finset (Fin n)
  Z : Finset (Fin n)
  disj : Disjoint Y Z
  cover : Y ∪ Z = Finset.univ
  balY : n ≤ 3 * Y.card ∧ 3 * Y.card < 2 * n
  balZ : n ≤ 3 * Z.card ∧ 3 * Z.card < 2 * n
  memLeft : Finset (Finset (Fin n))
  memRight : Finset (Finset (Fin n))
  memLeftSub : ∀ S ∈ memLeft, S ⊆ Y
  memRightSub : ∀ T ∈ memRight, T ⊆ Z

/-- The set family carried by a rectangle: `{S ∪ T : S ∈ 𝒴, T ∈ 𝒵}`. -/
def BalancedRectangle.mem {n : ℕ} (R : BalancedRectangle n) :
    Finset (Finset (Fin n)) :=
  (R.memLeft ×ˢ R.memRight).image fun p => p.1 ∪ p.2

/-! ## Part 5: balanced monotone pairs -/

/-- A balanced monotone pair of polynomials: `g` and `h` have
non-negative coefficients and depend on the variables of two sides of a
partition of the index set `[n]` whose part counts are balanced
(`|Y|, |Z| ∈ [n/3, 2n/3)`); the variables over part `i` are
`{(i,false), (i,true)}`. -/
structure BalancedPair (n : ℕ) where
  g : MvPolynomial (Fin n × Bool) ℝ
  h : MvPolynomial (Fin n × Bool) ℝ
  gMono : ∀ m, 0 ≤ g.coeff m
  hMono : ∀ m, 0 ≤ h.coeff m
  Y : Finset (Fin n)
  Z : Finset (Fin n)
  disj : Disjoint Y Z
  cover : Y ∪ Z = Finset.univ
  balY : n ≤ 3 * Y.card ∧ 3 * Y.card < 2 * n
  balZ : n ≤ 3 * Z.card ∧ 3 * Z.card < 2 * n
  gVars : ∀ m ∈ g.support, ∀ s : Fin n × Bool, m s ≠ 0 → s.1 ∈ Y
  hVars : ∀ m ∈ h.support, ∀ s : Fin n × Bool, m s ≠ 0 → s.1 ∈ Z

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

-- @[checkpoint c7 difficulty=hard]
/-- The arithmetic separation (main theorem), per-degree form with
explicit constants: for every degree `d ≥ 2` there are a `c > 0` and
threshold `N₀` such that for all `n ≥ N₀` and every `n`-vertex
`d`-regular spectral expander `G`, the graph polynomial `P_G`
(a) is computed by an explicit arithmetic formula of size at most
`35·(e(G)+1)²·n` — `O(n³)` for constant-degree expanders — and (b)
every monotone arithmetic formula computing `P_G` has size at least
`2^{c·n}`. The random-matching lemma is taken as the hypothesis
`expanderMatchingProp`. -/
theorem negations_small_depth_separation (hmatch : expanderMatchingProp) :
    ∀ d : ℕ, 2 ≤ d → ∃ c : ℝ, 0 < c ∧ ∃ N₀ : ℕ, ∀ (n : ℕ) (hN : N₀ ≤ n) (G : SimpleGraph (Fin n))
      [DecidableRel G.Adj], IsExpander G d →
      (∃ F : ACirc (Fin n × Bool), F.toPoly = graphPoly G ∧
          (F.size : ℝ) ≤ 35 * ((edgeCount G Finset.univ : ℝ) + 1) ^ 2 * n) ∧
      ∀ M : ACirc (Fin n × Bool), M.IsMonotone → M.toPoly = graphPoly G →
        (2 : ℝ) ^ (c * n) ≤ M.size := by
  -- CHECKPOINT negations_small_depth_separation BEGIN
  sorry
  -- CHECKPOINT negations_small_depth_separation END

end NegationsSmallDepth
