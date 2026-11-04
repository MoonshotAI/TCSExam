import Mathlib
import Task.Basic

/-!
# Executable small examples for the PCPAlphabetSoundness statement layer

Fidelity archive piece 2 (executable small examples): run the shipped
definitions on tiny concrete instances and record the results in
`small-examples.md`. Field: `ZMod 2`; ambient dimensions 2 and 3.

The shipped `grass`/`zoom`/`zoomProb` are noncomputable (they rest on a
classical `Fintype (Submodule …)` instance), so the checks come in two
kinds:

- **Shadow computations** (`native_decide` on a computable shadow model
  where a subspace is represented by its carrier finset): the combinatorial
  counts the shipped definitions are supposed to compute — the number of
  subspaces (Gaussian binomial values), zoom counts, the number of linear
  functions on a subspace, and the per-pair accepted-fraction of the
  inclusion test (the content of checkpoint c2's averaging argument).
- **Proof-style official checks**: the shipped definitions evaluated by
  proof on concrete instances (membership, agreement, and the cardinal
  bridge `(grass (ZMod 2) 2 1).card = 3`).

Not part of the graded task.
-/

namespace PCPAlphabetSoundness

abbrev F2 := ZMod 2

instance : Fact (Nat.Prime 2) := ⟨by norm_num⟩

/-! ## Part A: the computable shadow model -/

/-- Shadow subspace test: a finset of vectors closed under the F2-module
structure (over F2 only `0 ∈ S` and closure under `+` are needed, scalars
are 0 and 1). -/
def isSubspace2 {n : ℕ} (S : Finset (Fin n → F2)) : Bool :=
  decide (0 ∈ S) && decide (∀ x ∈ S, ∀ y ∈ S, x + y ∈ S)

/-- Shadow Grassmann domain: carrier finsets of `ℓ`-dimensional subspaces of
`F2^n` (over F2, `dim = ℓ` iff the carrier has `2^ℓ` elements). -/
def shadowGrass (n ℓ : ℕ) : Finset (Finset (Fin n → F2)) :=
  (Finset.univ : Finset (Fin n → F2)).powerset.filter
    (fun S => isSubspace2 S && decide (S.card = 2 ^ ℓ))

/-- Shadow zoom: `ℓ`-dimensional shadow subspaces between carriers `Q` and
`W`. -/
def shadowZoom (n ℓ : ℕ) (Q W : Finset (Fin n → F2)) : Finset (Finset (Fin n → F2)) :=
  (shadowGrass n ℓ).filter (fun L => decide (Q ⊆ L) && decide (L ⊆ W))

-- A1: |Grass_2(3, 1)| = 7 and |Grass_2(3, 2)| = 7 (Gaussian binomials)
example : (shadowGrass 3 1).card = 7 := by native_decide

example : (shadowGrass 3 2).card = 7 := by native_decide

-- A2: |Grass_2(2, 1)| = 3 (the official-side bridge E6 below proves the
-- same count for the shipped `grass`)
example : (shadowGrass 2 1).card = 3 := by native_decide

-- A3: zoom counts over F2^3: |Zoom_1[⊥, ⊤]| = 7, |Zoom_2[⊥, ⊤]| = 7,
-- and inside a 2-dimensional W: |Zoom_1[⊥, W]| = 3, |Zoom_2[⊥, W]| = 1
example : (shadowZoom 3 1 ∅ Finset.univ).card = 7 := by native_decide

example : (shadowZoom 3 2 ∅ Finset.univ).card = 7 := by native_decide

example :
    let W : Finset (Fin 3 → F2) := {![0,0,0], ![1,0,0], ![0,1,0], ![1,1,0]}
    (shadowZoom 3 1 ∅ W).card = 3 ∧ (shadowZoom 3 2 ∅ W).card = 1 := by
  native_decide

/-- All functions `F2^3 → F2` (256 of them) — the enumeration space for
shadow linear maps. -/
def allFuns : Finset ((Fin 3 → F2) → F2) := Finset.univ

/-- Shadow linear maps on a carrier `L`: total functions that vanish off
`L` and are linear on `L`. -/
def linMapsOn (L : Finset (Fin 3 → F2)) : Finset ((Fin 3 → F2) → F2) :=
  allFuns.filter (fun f =>
    decide (f 0 = 0) &&
    decide (∀ x ∈ L, ∀ y ∈ L, f (x + y) = f x + f y) &&
    decide (∀ x, x ∉ L → f x = 0))

-- A4: the number of linear functions on an `ℓ`-dimensional subspace is
-- `q^ℓ` (the alphabet of the subspace encoding): 2 on a line, 4 on a
-- plane, 8 on all of F2^3
example :
    let L : Finset (Fin 3 → F2) := {![0,0,0], ![1,0,0]}
    (linMapsOn L).card = 2 := by native_decide

example :
    let L : Finset (Fin 3 → F2) := {![0,0,0], ![1,0,0], ![0,1,0], ![1,1,0]}
    (linMapsOn L).card = 4 := by native_decide

example : (linMapsOn Finset.univ).card = 8 := by native_decide

/-- The shadow inclusion-test randomness space at `(ℓ₁, ℓ₂)`: pairs of
carriers `(L₁, L₂)` with `L₂ ⊆ L₁`. -/
def shadowIncPairs (ℓ₁ ℓ₂ : ℕ) :
    Finset (Finset (Fin 3 → F2) × Finset (Fin 3 → F2)) :=
  ((shadowGrass 3 ℓ₁) ×ˢ (shadowGrass 3 ℓ₂)).filter (fun p => decide (p.2 ⊆ p.1))

-- A5: at (ℓ₁, ℓ₂) = (2, 1) over F2^3 there are 7·3 = 21 test pairs
example : (shadowIncPairs 2 1).card = 21 := by native_decide

/-- Per test pair `(L₁, L₂)`: the number of accepted pairs of shadow linear
maps `(g₁, g₂)` with `g₁|_{L₂} = g₂` — the content of checkpoint c2's
averaging argument is that this is exactly `|Hom(L₁)|·|Hom(L₂)|/q^{ℓ₂}`
(4 out of 8 here), uniformly over all 21 pairs. -/
def shadowAcceptedCount (p : Finset (Fin 3 → F2) × Finset (Fin 3 → F2)) : ℕ :=
  (((linMapsOn p.1) ×ˢ (linMapsOn p.2)).filter (fun gg =>
    decide (∀ x ∈ p.2, gg.1 x = gg.2 x))).card

example : ∀ p ∈ shadowIncPairs 2 1, shadowAcceptedCount p = 4 := by
  native_decide

example : ∀ p ∈ shadowIncPairs 2 1,
    2 * shadowAcceptedCount p = (linMapsOn p.1).card * (linMapsOn p.2).card := by
  native_decide

-- A6: honesty at the shadow level — a global linear f restricts
-- consistently, so every test pair accepts
example :
    let f : (Fin 3 → F2) → F2 := fun x => x 0 + x 1
    let T : Finset (Fin 3 → F2) → (Fin 3 → F2) → F2 := fun _L => f
    ∀ p ∈ shadowIncPairs 2 1, ∀ x ∈ p.2, T p.1 x = T p.2 x := by
  native_decide

/-! ## Part B: proof-style checks on the shipped definitions -/

/-- The whole plane is a 2-dimensional member of the shipped Grassmann
domain. -/
example : (⊤ : Submodule F2 (Fin 2 → F2)) ∈ grass F2 2 2 := by
  simp only [grass, Finset.mem_filter, Finset.mem_univ, true_and]
  rw [finrank_top, Module.finrank_fintype_fun_eq_card, Fintype.card_fin]

/-- The zero subspace is a 0-dimensional member. -/
example : (⊥ : Submodule F2 (Fin 2 → F2)) ∈ grass F2 2 0 := by
  simp [grass]

/-- The zero subspace is not a 1-dimensional member. -/
example : (⊥ : Submodule F2 (Fin 2 → F2)) ∉ grass F2 2 1 := by
  simp [grass]

/-- Zoom membership of the top subspace. -/
example : (⊤ : Submodule F2 (Fin 2 → F2)) ∈ zoom F2 2 2 ⊥ ⊤ := by
  simp [zoom, grass, finrank_top, Module.finrank_fintype_fun_eq_card]

/-- The shipped agreement predicate holds for the honest table
(`globalTab f`) against the restriction of `f`, on any `L ≤ W`. -/
example (f : (Fin 2 → F2) →ₗ[F2] F2) (W L : Submodule F2 (Fin 2 → F2)) (_h : L ≤ W) :
    agreeOnZoom (globalTab f) (f.comp (Submodule.subtype W)) L := by
  intro _h'
  rfl

/-- The shipped inclusion-test acceptance condition holds for honest
tables. -/
example (f : (Fin 2 → F2) →ₗ[F2] F2)
    (p : Submodule F2 (Fin 2 → F2) × Submodule F2 (Fin 2 → F2)) (_h : p.2 ≤ p.1) :
    incAccepts (globalTab f) (globalTab f) p := by
  intro _h''
  rfl

/-- Bridge: the shipped Grassmann domain at (n, ℓ) = (2, 1) over F2 has
exactly 3 members — the same count as the shadow model's A2. The proof
exhibits the three 1-dimensional subspaces as spans of the three nonzero
vectors and shows every 1-dimensional subspace is one of them. -/
example : (grass F2 2 1).card = 3 := by
  classical
  have hspan : ∀ v : Fin 2 → F2, v ≠ 0 → Module.finrank F2 (F2 ∙ v) = 1 :=
    fun v hv => finrank_span_singleton hv
  have hmem : ∀ S : Submodule F2 (Fin 2 → F2),
      Module.finrank F2 S = 1 → ∃ v : Fin 2 → F2, v ≠ 0 ∧ S = F2 ∙ v := by
    intro S hS
    haveI : Module.Finite F2 ↥S := Module.finite_of_finrank_eq_succ (n := 0) hS
    let b := Module.finBasis F2 ↥S
    have hpos : 0 < Module.finrank F2 ↥S := by rw [hS]; norm_num
    let i0 : Fin (Module.finrank F2 ↥S) := ⟨0, hpos⟩
    have hv0 : (b i0).1 ≠ 0 := by
      intro hz
      exact b.linearIndependent.ne_zero i0 (Subtype.ext_iff.mpr (by simpa using hz))
    refine ⟨(b i0).1, hv0, ?_⟩
    symm
    apply Submodule.eq_of_le_of_finrank_eq
    · rw [Submodule.span_singleton_le_iff_mem]
      exact (b i0).2
    · rw [hspan _ hv0, hS]
  have hne : ∀ v : Fin 2 → F2, v ≠ 0 → v = ![1, 0] ∨ v = ![0, 1] ∨ v = ![1, 1] := by
    decide
  have hset : grass F2 2 1 =
      {F2 ∙ (![1, 0] : Fin 2 → F2), F2 ∙ (![0, 1] : Fin 2 → F2),
        F2 ∙ (![1, 1] : Fin 2 → F2)} := by
    ext S
    simp only [grass, Finset.mem_filter, Finset.mem_univ, true_and, Finset.mem_insert,
      Finset.mem_singleton]
    constructor
    · intro hS
      obtain ⟨v, hv, rfl⟩ := hmem S hS
      rcases hne v hv with rfl | rfl | rfl
      · exact Or.inl rfl
      · exact Or.inr (Or.inl rfl)
      · exact Or.inr (Or.inr rfl)
    · rintro (rfl | rfl | rfl)
      · exact hspan _ (by decide)
      · exact hspan _ (by decide)
      · exact hspan _ (by decide)
  rw [hset]
  have hu12 : (F2 ∙ (![1, 0] : Fin 2 → F2) : Submodule F2 (Fin 2 → F2)) ≠
      F2 ∙ (![0, 1] : Fin 2 → F2) := by
    intro h
    have hm : (![0, 1] : Fin 2 → F2) ∈
        (F2 ∙ (![1, 0] : Fin 2 → F2) : Submodule F2 (Fin 2 → F2)) :=
      h ▸ Submodule.mem_span_singleton_self _
    obtain ⟨c, hc⟩ := Submodule.mem_span_singleton.mp hm
    have h1 := congrFun hc 1
    simp [Matrix.cons_val_zero, Matrix.cons_val_one, Matrix.head_cons] at h1
  have hu13 : (F2 ∙ (![1, 0] : Fin 2 → F2) : Submodule F2 (Fin 2 → F2)) ≠
      F2 ∙ (![1, 1] : Fin 2 → F2) := by
    intro h
    have hm : (![1, 1] : Fin 2 → F2) ∈
        (F2 ∙ (![1, 0] : Fin 2 → F2) : Submodule F2 (Fin 2 → F2)) :=
      h ▸ Submodule.mem_span_singleton_self _
    obtain ⟨c, hc⟩ := Submodule.mem_span_singleton.mp hm
    have h1 := congrFun hc 1
    simp [Matrix.cons_val_zero, Matrix.cons_val_one, Matrix.head_cons] at h1
  have hu23 : (F2 ∙ (![0, 1] : Fin 2 → F2) : Submodule F2 (Fin 2 → F2)) ≠
      F2 ∙ (![1, 1] : Fin 2 → F2) := by
    intro h
    have hm : (![1, 1] : Fin 2 → F2) ∈
        (F2 ∙ (![0, 1] : Fin 2 → F2) : Submodule F2 (Fin 2 → F2)) :=
      h ▸ Submodule.mem_span_singleton_self _
    obtain ⟨c, hc⟩ := Submodule.mem_span_singleton.mp hm
    have h0 := congrFun hc 0
    simp [Matrix.cons_val_zero, Matrix.cons_val_one, Matrix.head_cons] at h0
  rw [Finset.card_insert_of_notMem (by simp [hu12, hu13]),
    Finset.card_insert_of_notMem (by simp [hu23]), Finset.card_singleton]

end PCPAlphabetSoundness
