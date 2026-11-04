import Task.Basic

namespace AaronsonAmbainis


/-! ## Auxiliary lemmas (helper layer) -/

lemma pmOne_not (b : Bool) : pmOne (!b) = -pmOne b := by
  cases b <;> simp [pmOne]

lemma pmOne_sq (b : Bool) : (pmOne b) ^ 2 = 1 := by
  cases b <;> simp [pmOne]

lemma pmOne_eq (b : Bool) : pmOne b = 1 ∨ pmOne b = -1 := by
  cases b <;> simp [pmOne]

lemma flipAt_self {n : ℕ} (x : Fin n → Bool) (i : Fin n) : flipAt x i i = !(x i) := by
  simp [flipAt, Function.update]

lemma flipAt_of_ne {n : ℕ} (x : Fin n → Bool) {i j : Fin n} (h : j ≠ i) :
    flipAt x i j = x j := by
  simp [flipAt, Function.update, h]

lemma flipAt_flipAt {n : ℕ} (x : Fin n → Bool) (i : Fin n) :
    flipAt (flipAt x i) i = x := by
  funext j
  by_cases h : j = i
  · subst h; rw [flipAt_self, flipAt_self, Bool.not_not]
  · rw [flipAt_of_ne _ h, flipAt_of_ne _ h]

lemma flipAt_ne_self {n : ℕ} (x : Fin n → Bool) (i : Fin n) : flipAt x i ≠ x := by
  intro h
  have hi := congrFun h i
  rw [flipAt_self] at hi
  exact (Bool.not_ne_self (x i)) hi

/-- Flipping bit `i` negates a character whose support contains `i`. -/
lemma char_flip_neg {n : ℕ} (s : Finset (Fin n)) (i : Fin n) (hi : i ∈ s)
    (x : Fin n → Bool) :
    (∏ j ∈ s, pmOne (flipAt x i j)) = -(∏ j ∈ s, pmOne (x j)) := by
  rw [← Finset.prod_erase_mul s (fun j => pmOne (x j)) hi,
    ← Finset.prod_erase_mul s (fun j => pmOne (flipAt x i j)) hi,
    Finset.prod_congr rfl (fun j hj => by rw [flipAt_of_ne x (Finset.ne_of_mem_erase hj)]),
    flipAt_self, pmOne_not]
  ring

lemma cubeAvg_char_ne_empty {n : ℕ} (s : Finset (Fin n)) (i : Fin n) (hi : i ∈ s) :
    cubeAvg (fun x => ∏ j ∈ s, pmOne (x j)) = 0 := by
  unfold cubeAvg
  rw [Finset.sum_involution (fun x _ => flipAt x i)
    (fun x _ => by rw [char_flip_neg s i hi x]; exact add_neg_cancel _)
    (fun x _ _ => flipAt_ne_self x i)
    (fun x _ => Finset.mem_univ _)
    (fun x _ => flipAt_flipAt x i)]
  exact zero_div _

lemma cubeAvg_congr {n : ℕ} {f g : (Fin n → Bool) → ℝ} (h : ∀ x, f x = g x) :
    cubeAvg f = cubeAvg g := by
  unfold cubeAvg
  rw [Finset.sum_congr rfl (fun x _ => h x)]

lemma cubeAvg_add {n : ℕ} (f g : (Fin n → Bool) → ℝ) :
    cubeAvg (fun x => f x + g x) = cubeAvg f + cubeAvg g := by
  unfold cubeAvg
  rw [Finset.sum_add_distrib, add_div]

lemma cubeAvg_smul {n : ℕ} (c : ℝ) (f : (Fin n → Bool) → ℝ) :
    cubeAvg (fun x => c * f x) = c * cubeAvg f := by
  unfold cubeAvg
  rw [← Finset.mul_sum, mul_div_assoc]

lemma card_cube {n : ℕ} : (Finset.univ : Finset (Fin n → Bool)).card = 2 ^ n := by
  rw [Finset.card_univ, Fintype.card_fun, Fintype.card_bool, Fintype.card_fin]

lemma cubeAvg_const {n : ℕ} (c : ℝ) : cubeAvg (fun _ : Fin n → Bool => c) = c := by
  unfold cubeAvg
  rw [Finset.sum_const, card_cube, nsmul_eq_mul]
  push_cast
  exact mul_div_cancel_left₀ c (pow_ne_zero n (two_ne_zero : (2 : ℝ) ≠ 0))

lemma cubeAvg_pmOne_coord {n : ℕ} (i : Fin n) :
    cubeAvg (fun x => pmOne (x i)) = 0 := by
  have hs : ∀ x : Fin n → Bool, pmOne (x i) = ∏ j ∈ {i}, pmOne (x j) :=
    fun x => (Finset.prod_singleton _ _).symm
  rw [cubeAvg_congr hs]
  exact cubeAvg_char_ne_empty {i} i (Finset.mem_singleton_self i)

/-! ## Dictator evaluation -/

lemma eval_dictator {n : ℕ} (hn : 0 < n) (x : Fin n → Bool) :
    MvPolynomial.eval (cubeEmbed x) (dictatorPoly hn) =
      (1 / 2 : ℝ) * (1 + pmOne (x ⟨0, hn⟩)) := by
  simp [dictatorPoly, cubeEmbed]

lemma cubeExpect_dictator {n : ℕ} (hn : 0 < n) :
    cubeExpect (dictatorPoly hn) = 1 / 2 := by
  have hexp : ∀ x : Fin n → Bool, (1 / 2 : ℝ) * (1 + pmOne (x ⟨0, hn⟩)) =
      1 / 2 + (1 / 2) * pmOne (x ⟨0, hn⟩) := fun x => by ring
  unfold cubeExpect
  rw [cubeAvg_congr (fun x => eval_dictator hn x), cubeAvg_congr hexp,
    cubeAvg_add, cubeAvg_const, cubeAvg_smul, cubeAvg_pmOne_coord]
  ring

lemma cubeVariance_dictator {n : ℕ} (hn : 0 < n) :
    cubeVariance (dictatorPoly hn) = 1 / 4 := by
  unfold cubeVariance
  rw [cubeExpect_dictator hn, ← cubeAvg_const (n := n) (1 / 4 : ℝ)]
  apply cubeAvg_congr
  intro x
  rw [eval_dictator hn x]
  have hs := pmOne_sq (x ⟨0, hn⟩)
  nlinarith [hs]

lemma cubeInfluence_dictator_self {n : ℕ} (hn : 0 < n) :
    cubeInfluence (dictatorPoly hn) ⟨0, hn⟩ = 1 := by
  unfold cubeInfluence
  rw [← cubeAvg_const (n := n) (1 : ℝ)]
  apply cubeAvg_congr
  intro x
  rw [eval_dictator hn x, eval_dictator hn (flipAt x ⟨0, hn⟩), flipAt_self, pmOne_not]
  have hs := pmOne_sq (x ⟨0, hn⟩)
  nlinarith [hs]

lemma cubeInfluence_dictator_other {n : ℕ} (hn : 0 < n) {i : Fin n} (hi : i ≠ ⟨0, hn⟩) :
    cubeInfluence (dictatorPoly hn) i = 0 := by
  unfold cubeInfluence
  rw [← cubeAvg_const (n := n) (0 : ℝ)]
  apply cubeAvg_congr
  intro x
  rw [eval_dictator hn x, eval_dictator hn (flipAt x i), flipAt_of_ne x (Ne.symm hi)]
  ring

lemma totalDegree_dictator {n : ℕ} (hn : 0 < n) :
    (dictatorPoly hn).totalDegree ≤ 1 := by
  unfold dictatorPoly
  refine le_trans (MvPolynomial.totalDegree_mul _ _) ?_
  rw [MvPolynomial.totalDegree_C, zero_add]
  refine le_trans (MvPolynomial.totalDegree_add _ _) ?_
  refine max_le ?_ ?_
  · rw [MvPolynomial.totalDegree_one]; exact Nat.zero_le 1
  · rw [MvPolynomial.totalDegree_X]

lemma bounded_dictator {n : ℕ} (hn : 0 < n) : BoundedOnCube (dictatorPoly hn) := by
  intro x
  rw [eval_dictator hn x]
  rcases pmOne_eq (x ⟨0, hn⟩) with h | h <;> rw [h] <;> constructor <;> norm_num


/-! ## Coordinate shorthands for the concrete examples -/

def c20 : Fin 2 := ⟨0, by norm_num⟩
def c21 : Fin 2 := ⟨1, by norm_num⟩
def c30 : Fin 3 := ⟨0, by norm_num⟩
def c31 : Fin 3 := ⟨1, by norm_num⟩
def c32 : Fin 3 := ⟨2, by norm_num⟩

lemma c21_ne_c20 : c21 ≠ c20 := by decide
lemma c20_ne_c21 : c20 ≠ c21 := by decide
lemma c31_ne_c30 : c31 ≠ c30 := by decide
lemma c32_ne_c30 : c32 ≠ c30 := by decide
lemma c31_ne_c32 : c31 ≠ c32 := by decide

/-! ## E1: the constant polynomial `1` has variance 0 (n = 2) -/

lemma eval_one_cube {n : ℕ} (x : Fin n → Bool) :
    MvPolynomial.eval (cubeEmbed x) (1 : MvPolynomial (Fin n) ℝ) = 1 := by
  simp

theorem ex1_variance_const :
    cubeVariance (1 : MvPolynomial (Fin 2) ℝ) = 0 := by
  have hE : cubeExpect (1 : MvPolynomial (Fin 2) ℝ) = 1 := by
    unfold cubeExpect
    rw [cubeAvg_congr (fun x => eval_one_cube x)]
    exact cubeAvg_const 1
  unfold cubeVariance
  rw [hE, ← cubeAvg_const (n := 2) (0 : ℝ)]
  apply cubeAvg_congr
  intro x
  rw [eval_one_cube x]
  ring

/-! ## E2: the ±1 dictator `X₀` has variance 1 (n = 2) -/

noncomputable def xdict (i : Fin 2) : MvPolynomial (Fin 2) ℝ := MvPolynomial.X i

lemma eval_xdict (x : Fin 2 → Bool) (i : Fin 2) :
    MvPolynomial.eval (cubeEmbed x) (xdict i) = pmOne (x i) := by
  simp [xdict, cubeEmbed]

theorem ex2_variance_xdict :
    cubeVariance (xdict c20) = 1 := by
  have hE : cubeExpect (xdict c20) = 0 := by
    unfold cubeExpect
    rw [cubeAvg_congr (fun x => eval_xdict x c20)]
    exact cubeAvg_pmOne_coord c20
  unfold cubeVariance
  rw [hE, ← cubeAvg_const (n := 2) (1 : ℝ)]
  apply cubeAvg_congr
  intro x
  rw [eval_xdict x]
  have hs := pmOne_sq (x c20)
  nlinarith [hs]

/-! ## E3: the ±1 dictator `X₀` has influence 4 on its own coordinate,
   0 on the other (n = 2) -/

theorem ex3_influence_xdict_self :
    cubeInfluence (xdict c20) c20 = 4 := by
  unfold cubeInfluence
  rw [← cubeAvg_const (n := 2) (4 : ℝ)]
  apply cubeAvg_congr
  intro x
  rw [eval_xdict x, eval_xdict (flipAt x c20), flipAt_self, pmOne_not]
  have hs := pmOne_sq (x c20)
  nlinarith [hs]

theorem ex3_influence_xdict_other :
    cubeInfluence (xdict c20) c21 = 0 := by
  unfold cubeInfluence
  rw [← cubeAvg_const (n := 2) (0 : ℝ)]
  apply cubeAvg_congr
  intro x
  rw [eval_xdict x, eval_xdict (flipAt x c21), flipAt_of_ne x c20_ne_c21]
  ring

/-! ## E4: the 0/1 dictator `(1+X₀)/2` at n = 2: variance 1/4, influence 1 on
   its coordinate, 0 on the other (instances of the general dictator lemmas) -/

theorem ex4_variance_dictator :
    cubeVariance (dictatorPoly (n := 2) (by norm_num)) = 1 / 4 :=
  cubeVariance_dictator _

theorem ex4_influence_dictator_self :
    cubeInfluence (dictatorPoly (n := 2) (by norm_num)) c20 = 1 :=
  cubeInfluence_dictator_self _

theorem ex4_influence_dictator_other :
    cubeInfluence (dictatorPoly (n := 2) (by norm_num)) c21 = 0 := by
  apply cubeInfluence_dictator_other
  decide

/-! ## E5: `(1 + X₀X₁)/2` (degree 2, equality of the two bits): variance 1/4,
   influence 1 on BOTH coordinates (n = 2) -/

noncomputable def pairPoly : MvPolynomial (Fin 2) ℝ :=
  MvPolynomial.C (1 / 2 : ℝ) * (1 + MvPolynomial.X c20 * MvPolynomial.X c21)

lemma eval_pair (x : Fin 2 → Bool) :
    MvPolynomial.eval (cubeEmbed x) pairPoly =
      (1 / 2 : ℝ) * (1 + pmOne (x c20) * pmOne (x c21)) := by
  simp [pairPoly, cubeEmbed]

lemma cubeExpect_pair : cubeExpect pairPoly = 1 / 2 := by
  have hexp : ∀ x : Fin 2 → Bool,
      (1 / 2 : ℝ) * (1 + pmOne (x c20) * pmOne (x c21)) =
        1 / 2 + (1 / 2) * (pmOne (x c20) * pmOne (x c21)) :=
    fun x => by ring
  have hchar : cubeAvg (fun x => pmOne (x c20) * pmOne (x c21)) = 0 := by
    have hs : ∀ x : Fin 2 → Bool,
        pmOne (x c20) * pmOne (x c21) = ∏ j ∈ {c20, c21}, pmOne (x j) := fun x => by
      rw [Finset.prod_pair c20_ne_c21]
    rw [cubeAvg_congr hs]
    exact cubeAvg_char_ne_empty _ c20 (by decide)
  unfold cubeExpect
  rw [cubeAvg_congr (fun x => eval_pair x), cubeAvg_congr hexp,
    cubeAvg_add, cubeAvg_const, cubeAvg_smul, hchar]
  ring

theorem ex5_variance_pair : cubeVariance pairPoly = 1 / 4 := by
  unfold cubeVariance
  rw [cubeExpect_pair, ← cubeAvg_const (n := 2) (1 / 4 : ℝ)]
  apply cubeAvg_congr
  intro x
  rw [eval_pair x]
  have hs0 := pmOne_sq (x c20)
  have hs1 := pmOne_sq (x c21)
  nlinarith [hs0, hs1]

theorem ex5_influence_pair_zero :
    cubeInfluence pairPoly c20 = 1 := by
  unfold cubeInfluence
  rw [← cubeAvg_const (n := 2) (1 : ℝ)]
  apply cubeAvg_congr
  intro x
  rw [eval_pair x, eval_pair (flipAt x c20), flipAt_self,
    flipAt_of_ne x c21_ne_c20, pmOne_not]
  have hs0 := pmOne_sq (x c20)
  have hs1 := pmOne_sq (x c21)
  nlinarith [hs0, hs1]

theorem ex5_influence_pair_one :
    cubeInfluence pairPoly c21 = 1 := by
  unfold cubeInfluence
  rw [← cubeAvg_const (n := 2) (1 : ℝ)]
  apply cubeAvg_congr
  intro x
  rw [eval_pair x, eval_pair (flipAt x c21), flipAt_of_ne x c20_ne_c21,
    flipAt_self, pmOne_not]
  have hs0 := pmOne_sq (x c20)
  have hs1 := pmOne_sq (x c21)
  nlinarith [hs0, hs1]

/-! ## E6: `(1 + maj₃)/2` where `maj₃ = (X₀+X₁+X₂−X₀X₁X₂)/2` is the majority of
   three ±1 bits: variance 1/4, influence 1/2 on coordinate 0 (n = 3) — the
   influence of a balanced symmetric function is below 1. -/

noncomputable def maj3Poly : MvPolynomial (Fin 3) ℝ :=
  MvPolynomial.C (1 / 2 : ℝ) *
    (1 + MvPolynomial.C (1 / 2 : ℝ) *
      (MvPolynomial.X c30 + MvPolynomial.X c31 + MvPolynomial.X c32 -
        MvPolynomial.X c30 * MvPolynomial.X c31 * MvPolynomial.X c32))

lemma eval_maj3 (x : Fin 3 → Bool) :
    MvPolynomial.eval (cubeEmbed x) maj3Poly =
      (1 / 2 : ℝ) * (1 + (1 / 2) *
        (pmOne (x c30) + pmOne (x c31) + pmOne (x c32) -
          pmOne (x c30) * pmOne (x c31) * pmOne (x c32))) := by
  simp [maj3Poly, cubeEmbed]

/-- The majority part `m(x) = (u₀+u₁+u₂−u₀u₁u₂)/2` squares to 1 pointwise. -/
lemma maj3_sq (x : Fin 3 → Bool) :
    ((1 / 2 : ℝ) * (pmOne (x c30) + pmOne (x c31) + pmOne (x c32) -
        pmOne (x c30) * pmOne (x c31) * pmOne (x c32))) ^ 2 = 1 := by
  rcases pmOne_eq (x c30) with h0 | h0 <;>
    rcases pmOne_eq (x c31) with h1 | h1 <;>
    rcases pmOne_eq (x c32) with h2 | h2 <;>
    rw [h0, h1, h2] <;> norm_num

lemma cubeAvg_maj3_part :
    cubeAvg (fun x => (1 / 2 : ℝ) *
      (pmOne (x c30) + pmOne (x c31) + pmOne (x c32) -
        pmOne (x c30) * pmOne (x c31) * pmOne (x c32))) = 0 := by
  have hexp : ∀ x : Fin 3 → Bool,
      (1 / 2 : ℝ) * (pmOne (x c30) + pmOne (x c31) + pmOne (x c32) -
          pmOne (x c30) * pmOne (x c31) * pmOne (x c32)) =
        (1 / 2) * pmOne (x c30) + (1 / 2) * pmOne (x c31) +
          (1 / 2) * pmOne (x c32) +
          (-1 / 2) * (pmOne (x c30) * pmOne (x c31) * pmOne (x c32)) :=
    fun x => by ring
  have htriple : cubeAvg (fun x =>
      pmOne (x c30) * pmOne (x c31) * pmOne (x c32)) = 0 := by
    have hs : ∀ x : Fin 3 → Bool,
        pmOne (x c30) * pmOne (x c31) * pmOne (x c32) =
          ∏ j ∈ {c30, c31, c32}, pmOne (x j) := fun x => by
      rw [Finset.prod_insert (by decide), Finset.prod_pair (by decide), mul_assoc]
    rw [cubeAvg_congr hs]
    exact cubeAvg_char_ne_empty _ c30 (by decide)
  rw [cubeAvg_congr hexp, cubeAvg_add, cubeAvg_add, cubeAvg_add,
    cubeAvg_smul, cubeAvg_smul, cubeAvg_smul, cubeAvg_smul,
    cubeAvg_pmOne_coord c30, cubeAvg_pmOne_coord c31, cubeAvg_pmOne_coord c32, htriple]
  ring

lemma cubeExpect_maj3 : cubeExpect maj3Poly = 1 / 2 := by
  have hexp : ∀ x : Fin 3 → Bool,
      (1 / 2 : ℝ) * (1 + (1 / 2) *
          (pmOne (x c30) + pmOne (x c31) + pmOne (x c32) -
            pmOne (x c30) * pmOne (x c31) * pmOne (x c32))) =
        1 / 2 + (1 / 2) * ((1 / 2) *
          (pmOne (x c30) + pmOne (x c31) + pmOne (x c32) -
            pmOne (x c30) * pmOne (x c31) * pmOne (x c32))) :=
    fun x => by ring
  unfold cubeExpect
  rw [cubeAvg_congr (fun x => eval_maj3 x), cubeAvg_congr hexp,
    cubeAvg_add, cubeAvg_const, cubeAvg_smul, cubeAvg_maj3_part]
  ring

theorem ex6_variance_maj3 : cubeVariance maj3Poly = 1 / 4 := by
  unfold cubeVariance
  rw [cubeExpect_maj3, ← cubeAvg_const (n := 3) (1 / 4 : ℝ)]
  apply cubeAvg_congr
  intro x
  rw [eval_maj3 x]
  have hs := maj3_sq x
  nlinarith [hs]

theorem ex6_influence_maj3_zero :
    cubeInfluence maj3Poly c30 = 1 / 2 := by
  have hpt : ∀ x : Fin 3 → Bool,
      (MvPolynomial.eval (cubeEmbed x) maj3Poly -
        MvPolynomial.eval (cubeEmbed (flipAt x c30)) maj3Poly) ^ 2 =
        (1 - pmOne (x c31) * pmOne (x c32)) / 2 := by
    intro x
    rw [eval_maj3 x, eval_maj3 (flipAt x c30), flipAt_self,
      flipAt_of_ne x c31_ne_c30, flipAt_of_ne x c32_ne_c30, pmOne_not]
    rcases pmOne_eq (x c30) with h0 | h0 <;>
      rcases pmOne_eq (x c31) with h1 | h1 <;>
      rcases pmOne_eq (x c32) with h2 | h2 <;>
      rw [h0, h1, h2] <;> norm_num
  have hexp : ∀ x : Fin 3 → Bool, (1 - pmOne (x c31) * pmOne (x c32)) / 2 =
      1 / 2 + (-1 / 2) * (pmOne (x c31) * pmOne (x c32)) := fun x => by ring
  have hchar : cubeAvg (fun x => pmOne (x c31) * pmOne (x c32)) = 0 := by
    have hs : ∀ x : Fin 3 → Bool,
        pmOne (x c31) * pmOne (x c32) = ∏ j ∈ {c31, c32}, pmOne (x j) := fun x => by
      rw [Finset.prod_pair c31_ne_c32]
    rw [cubeAvg_congr hs]
    exact cubeAvg_char_ne_empty _ c31 (by decide)
  unfold cubeInfluence
  rw [cubeAvg_congr hpt, cubeAvg_congr hexp, cubeAvg_add, cubeAvg_const,
    cubeAvg_smul, hchar]
  ring

end AaronsonAmbainis
