/-
Self-contained statement layer for a theorem in PCP combinatorics: a
counting bound on maximal zoom-out function pairs behind a near-optimal
alphabet-soundness tradeoff.

The fixed part (everything above the end-of-fixed-part marker line) is the
definition layer the main theorem's statement needs: the Grassmann domain,
zoom restrictions and their uniform measures, tables and agreement,
codimension notions, `(C, ζ)`-maximal zoom-out function pairs, the
parameters ξ and t, and the two packaged power sources
`ManyZoomoutsRefinement` and `GenericZoomSampling`.  Fidelity notes live in
`tests/reference/`.
-/

import Mathlib

namespace PCPAlphabetSoundness

variable {F : Type*} [Field F] [Fintype F] [DecidableEq F]

/-! ## Fintype infrastructure (noncomputable, via finiteness of `F^n`) -/

noncomputable instance submoduleElemFintype {n : ℕ} (S : Submodule F (Fin n → F)) :
    Fintype S :=
  Fintype.ofFinite _

noncomputable instance submoduleFinite {n : ℕ} : Finite (Submodule F (Fin n → F)) :=
  Finite.of_injective (fun S : Submodule F (Fin n → F) => (S : Set (Fin n → F)))
    SetLike.coe_injective

noncomputable instance submoduleFintype {n : ℕ} : Fintype (Submodule F (Fin n → F)) :=
  Fintype.ofFinite _

noncomputable instance linearMapFinite {n : ℕ} (W : Submodule F (Fin n → F)) :
    Finite (W →ₗ[F] F) :=
  Finite.of_injective (fun f : W →ₗ[F] F => (f : W → F))
    (fun f g h => DFunLike.ext f g (fun x => congrFun h x))

noncomputable instance linearMapFintype {n : ℕ} (W : Submodule F (Fin n → F)) :
    Fintype (W →ₗ[F] F) :=
  Fintype.ofFinite _

noncomputable instance zoomPairFintype {n : ℕ} :
    Fintype (Σ W : Submodule F (Fin n → F), (W →ₗ[F] F)) :=
  Fintype.ofFinite _


/-! ## The Grassmann domain, zoom restrictions, and zoom measures -/

/-- The Grassmann domain `Grass_q(n, ℓ)`: all `ℓ`-dimensional subspaces
of `F^n`. -/
noncomputable def grass (F : Type*) [Field F] [Fintype F] [DecidableEq F] (n ℓ : ℕ) :
    Finset (Submodule F (Fin n → F)) :=
  Finset.univ.filter fun S => Module.finrank F S = ℓ

/-- The zoom restriction `Zoom_ℓ[Q, W]`: the `ℓ`-dimensional subspaces
`L` with `Q ⊆ L ⊆ W`. `Q` is the zoom-in and `W` the zoom-out. -/
noncomputable def zoom (F : Type*) [Field F] [Fintype F] [DecidableEq F] (n ℓ : ℕ)
    (Q W : Submodule F (Fin n → F)) : Finset (Submodule F (Fin n → F)) := by
  classical
  exact (grass F n ℓ).filter fun L => Q ≤ L ∧ L ≤ W

/-- The measure of a predicate under the zoom-in/zoom-out pair `(Q, W)` — the
`μ_{Q,W}`: the fraction of `L ∈ Zoom_ℓ[Q, W]`
satisfying the predicate, as a rational number (0 if the zoom is empty). -/
noncomputable def zoomProb (F : Type*) [Field F] [Fintype F] [DecidableEq F] (n ℓ : ℕ)
    (Q W : Submodule F (Fin n → F)) (P : Submodule F (Fin n → F) → Prop) : ℚ := by
  classical
  exact (((zoom F n ℓ Q W).filter P).card : ℚ) / ((zoom F n ℓ Q W).card : ℚ)

/-! ## Tables and agreement -/

/-- A table assigning to each subspace of `F^n` a linear function on it
(only the values on subspaces of the relevant dimension are ever read). -/
def Tab (F : Type*) [Field F] [Fintype F] [DecidableEq F] (n : ℕ) :=
  ∀ L : Submodule F (Fin n → F), (L →ₗ[F] F)

/-- The agreement predicate "`g|_L ≡ T[L]`": the table value at `L`
equals the restriction of the linear function `g : W → F` to `L ⊆ W`. -/
def agreeOnZoom {n : ℕ} (T : Tab F n) {W : Submodule F (Fin n → F)} (g : W →ₗ[F] F)
    (L : Submodule F (Fin n → F)) : Prop :=
  ∀ h : L ≤ W, T L = g.comp (Submodule.inclusion h)


/-! ## Codimension notions -/

/-- The codimension of `W` inside `Wamb` (nat subtraction; meaningful when
`W ≤ Wamb`). -/
noncomputable def relCodim {n : ℕ} (Wamb W : Submodule F (Fin n → F)) : ℕ :=
  Module.finrank F Wamb - Module.finrank F W

/-- The codimension of `W` inside the ambient space `F^n`. -/
noncomputable def ambCodim {n : ℕ} (W : Submodule F (Fin n → F)) : ℕ :=
  n - Module.finrank F W

/-! ## (C, ζ)-maximal zoom-out function pairs -/

/-- A zoom-out, function pair `(W, g)` with `Q ⊆ W` is `(C, ζ)`-maximal with
respect to `T` on `Q` if `g` agrees with `T` on at least a `C`-fraction of
`Zoom_ℓ[Q, W]`, and no proper extension `(W'', g'')` with `g''|_W = g`
reaches agreement `ζ·C`. In the case `Q = ⊥` this is simply called
"(C, ζ)-maximal with respect to T". -/
def IsMaximalPair {n : ℕ} (T : Tab F n) (ℓ : ℕ) (Q : Submodule F (Fin n → F)) (C ζ : ℝ)
    (W : Submodule F (Fin n → F)) (g : W →ₗ[F] F) : Prop :=
  Q ≤ W ∧
  C ≤ (zoomProb F n ℓ Q W (agreeOnZoom T g) : ℝ) ∧
  ∀ {W'' : Submodule F (Fin n → F)} (hWW : W ≤ W''), W ≠ W'' →
    ∀ g'' : W'' →ₗ[F] F, g''.comp (Submodule.inclusion hWW) = g →
      (zoomProb F n ℓ Q W'' (agreeOnZoom T g'') : ℝ) < ζ * C

/-! ## The constant parameters -/

/-- The parameter `ξ := δ⁵`. -/
def xiParam (δ : ℝ) : ℝ := δ ^ 5

/-- The parameter `t := (2^{2+10/δ₂})!`, with `δ₂ := ξ/100`; shipped with
a ceiling. -/
noncomputable def tParam (δ : ℝ) : ℕ := (⌈(2 : ℝ) ^ (2 + 10 / (xiParam δ / 100))⌉₊).factorial

/-! ## Packaged power source: the many-zoomouts refinement -/

/-- The many-zoomouts refinement — the formal version of the source
proof's main technical component — packaged as a hypothesis (its proof uses
an optimal level-d inequality and a linearity test, both far outside this
task's scope). Statement transcribed from the source text, including the
standing assumption that the ambient dimension `n` is at least
`2^{100}·q^ℓ`. The side condition `1 ≤ r` is added, and the first
conclusion item is shipped in the uniform-codimension form the source proof
delivers and consumes (a single `s` with `1 ≤ s ≤ r`, every member strictly
contained in `A` of codimension `s` inside `A`, pairwise intersections of
codimension `2s` inside `A`), in place of the printed per-member
"codimension r' < r with respect to A". -/
def ManyZoomoutsRefinement (F : Type*) [Field F] [Fintype F] [DecidableEq F] : Prop :=
  ∀ {δ : ℝ} (_ : 0 < δ), ∃ ℓ₀ : ℕ, ∀ {ℓ : ℕ}, ℓ₀ ≤ ℓ →
    ∀ {n : ℕ} (_ : (2 : ℝ) ^ 100 * (Fintype.card F : ℝ) ^ ℓ ≤ (n : ℝ))
    (T : Tab F n) {r : ℕ} (_ : 1 ≤ r) (_ : (r : ℝ) ≤ 10 / δ) {C : ℝ}
    (_ : (Fintype.card F : ℝ) ^ (-2 * (1 - δ ^ 5) * (ℓ : ℝ)) ≤ C)
    {N : ℕ} (pairs : Fin N → (Σ W : Submodule F (Fin n → F), (W →ₗ[F] F)))
    (_ : (Fintype.card F : ℝ) ^
          (100 * ((tParam δ - 1).factorial : ℝ) * (r : ℝ) ^ 2 * (ℓ : ℝ) / xiParam δ) ≤ (N : ℝ))
    (_ : ∀ i, ambCodim (pairs i).1 = r)
    (_ : Function.Injective fun i => (pairs i).1)
    (_ : ∀ i, C ≤ (zoomProb F n (2 * ℓ) ⊥ (pairs i).1 (agreeOnZoom T (pairs i).2) : ℝ)),
    ∃ (A : Submodule F (Fin n → F)) (h' : A →ₗ[F] F) (sub : Finset (Fin N)) (s : ℕ),
      1 ≤ s ∧ s ≤ r ∧
      (Fintype.card F : ℝ) ^ (50 * (r : ℝ) * (ℓ : ℝ) / xiParam δ) ≤ (sub.card : ℝ) ∧
      (∀ i ∈ sub, (pairs i).1 < A ∧ relCodim A (pairs i).1 = s) ∧
      (∀ i ∈ sub, ∀ j ∈ sub, i ≠ j →
        relCodim A ((pairs i).1 ⊓ (pairs j).1) = 2 * s) ∧
      ∀ i ∈ sub, ∃ hle : (pairs i).1 ≤ A, h'.comp (Submodule.inclusion hle) = (pairs i).2

/-! ## Packaged power source: sampling over a generic family -/

/-- The measure `ν_S`: pick `W ∈ S` uniformly, then
`L ∈ Zoom_j[Q, W]` uniformly; the value on `ℒ` as a real number (0 if `S` is
empty). -/
noncomputable def nuMeas (F : Type*) [Field F] [Fintype F] [DecidableEq F] {n : ℕ}
    (S : Finset (Submodule F (Fin n → F))) (j : ℕ) (Q : Submodule F (Fin n → F))
    (ℒ : Finset (Submodule F (Fin n → F))) : ℝ := by
  classical
  exact (∑ W ∈ S, ((((zoom F n j Q W).filter (· ∈ ℒ)).card : ℝ) /
      ((zoom F n j Q W).card : ℝ))) / (S.card : ℝ)

/-- The generic-family sampling bound, packaged as a hypothesis (its
proof is a Chebyshev argument over subspace-counting asymptotics): over a
2-generic family `S` of codimension-`r` subspaces of `Wamb`,
all containing the `a`-dimensional `Q`, the measures `ν_S` and the uniform
measure on `Zoom_j[Q, Wamb]` are `3·q^{(r/2)(j-a)}/√|S|`-close on every set
`ℒ ⊆ Zoom_j[Q, Wamb]`, provided `j ≥ 2^{100·r²·a²}` and
`dim(Wamb) ≥ 2^{100}·j`. -/
def GenericZoomSampling (F : Type*) [Field F] [Fintype F] [DecidableEq F] : Prop :=
  ∀ {n : ℕ} (Wamb : Submodule F (Fin n → F)) {a r j : ℕ}
    (_ : 2 ^ (100 * r ^ 2 * a ^ 2) ≤ j) (_ : 2 ^ 100 * j ≤ Module.finrank F Wamb)
    {Q : Submodule F (Fin n → F)} (_ : Q ≤ Wamb) (_ : Module.finrank F Q = a)
    {S : Finset (Submodule F (Fin n → F))} (_ : S.Nonempty)
    (_ : ∀ W ∈ S, W ≤ Wamb ∧ relCodim Wamb W = r ∧ Q ≤ W)
    (_ : ∀ T₂ : Finset (Submodule F (Fin n → F)), T₂ ⊆ S → T₂.card = 2 →
      relCodim Wamb (T₂.inf id) = 2 * r)
    (ℒ : Finset (Submodule F (Fin n → F))) (_ : ℒ ⊆ zoom F n j Q Wamb),
    |nuMeas F S j Q ℒ - (zoomProb F n j Q Wamb (· ∈ ℒ) : ℝ)| ≤
      3 * (Fintype.card F : ℝ) ^ ((r : ℝ) / 2 * ((j : ℝ) - (a : ℝ))) / Real.sqrt (S.card : ℝ)

/-- The finite set of `(C, ζ)`-maximal zoom-out function pairs with respect
to `T` on `Q` whose codimension in the ambient space is at most `rmax` —
the set whose size the main theorem bounds. -/
noncomputable def maximalPairFinset {n : ℕ} (T : Tab F n) (ℓ : ℕ)
    (Q : Submodule F (Fin n → F)) (C ζ rmax : ℝ) :
    Finset (Σ W : Submodule F (Fin n → F), (W →ₗ[F] F)) := by
  classical
  exact Finset.univ.filter fun p =>
    IsMaximalPair T ℓ Q C ζ p.1 p.2 ∧ (ambCodim p.1 : ℝ) ≤ rmax

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

/-! ## Checkpoint zone: the main theorem -/

-- @[checkpoint main difficulty=hard]
/-- The main theorem of this task (an upper bound on the number of maximal
zoom-outs), under the packaged refinement (`ManyZoomoutsRefinement`) and
sampling (`GenericZoomSampling`) hypotheses: for every `δ > 0` there is
`ℓ₀` such that for all `ℓ ≥ ℓ₀` and all ambient dimensions
`n ≥ 2^{100}·q^ℓ`, for every table `T` on `F^n`, every zoom-in `Q` of
dimension `r₁ ≤ 10/δ`, and every `C ≥ q^{-2(1-δ³)ℓ}`, the number of
`(C, 1/5)`-maximal zoom-out function pairs with respect to `T` on `Q` of
ambient codimension at most `10/δ` is at most
`(160/δ)·C^{-2}·q^{100·(t−1)!·(10/δ)²·ℓ/ξ}`, with `ξ = δ⁵` and
`t = ⌈2^{2+10/δ₂}⌉!`, `δ₂ = ξ/100`. -/
theorem maximal_zoomout_count
    (hRefine : ManyZoomoutsRefinement F) (hSample : GenericZoomSampling F)
    {δ : ℝ} (hδ : 0 < δ) :
    ∃ ℓ₀ : ℕ, ∀ ℓ : ℕ, ℓ₀ ≤ ℓ → ∀ {n : ℕ},
      (2 : ℝ) ^ 100 * (Fintype.card F : ℝ) ^ ℓ ≤ (n : ℝ) →
      ∀ (T : Tab F n) (Q : Submodule F (Fin n → F)),
        (Module.finrank F Q : ℝ) ≤ 10 / δ →
        ∀ C : ℝ, (Fintype.card F : ℝ) ^ (-2 * (1 - δ ^ 3) * (ℓ : ℝ)) ≤ C →
          ((maximalPairFinset T (2 * ℓ) Q C (1 / 5) (10 / δ)).card : ℝ) ≤
            (160 / δ) * C ^ (-2 : ℤ) *
              (Fintype.card F : ℝ) ^
                (100 * ((tParam δ - 1).factorial : ℝ) * (10 / δ) ^ 2 * (ℓ : ℝ) / xiParam δ) := by
  -- CHECKPOINT maximal_zoomout_count BEGIN
  sorry
  -- CHECKPOINT maximal_zoomout_count END

end PCPAlphabetSoundness
