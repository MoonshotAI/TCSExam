/-
Statement layer for the KRW composition conjecture (Karchmer–Raz–Wigderson,
"Super-logarithmic depth lower bounds via the direct sum in communication
complexity", computational complexity 5:191–204, 1995), in the
**reciprocal-share form** used by the current literature (Gavinsky–Meir–
Weinstein–Wigderson, ECCC TR13-190 rev. 11 (2017), Conjecture 1.3 and
footnote 3(ii)): there is a universal `k ≥ 2` such that for all non-constant
Boolean functions `f` (outer) and `g` (inner), the block composition
`(f ⋄ g)(x₁, …, xₘ) = f(g(x₁), …, g(xₘ))` — each input bit of `f` replaced
by `g` on a fresh block of variables — has formula depth

    D(f ⋄ g) ≥ D(f) + D(g)/k.

Iterated on a growing function family, this would give super-logarithmic
formula-depth lower bounds and hence separate NC¹ from P (KRW 1995, Thm
5.2); it is a proposed route towards NC¹ ≠ P that appears to require only
combinatorial techniques.

Warning on the form: the stronger "universal additive constant" version
`D(f ⋄ g) ≥ D(f) + D(g) − c` is NOT the open conjecture. Pudlák's example
(recorded in KRW 1995, p. 196, with `f = g = thresholdTwo`) makes the
additive gap grow like `log log n`, so that form was known false from the
start; this package previously stated that form and was corrected on
as demonstrated by the cited Pudlák counterexample.

The conjecture is open: recent progress covers restricted cases only — a
strong-composition variant with outer function XOR and a random inner
function (Chukhin–Kulikov–Mihajlin, STACS 2025, arXiv:2410.10189) and
compositions with the universal relation in place of one factor
(Gavinsky–Meir–Weinstein–Wigderson 2017).

This file is the task's definition zone plus slot zone:
- The definition zone defines De Morgan formulas over a finite index set
  (`KRW.BFormula`), their depth and evaluation, what it means for a formula
  to compute a Boolean function (`BFormula.Computes`), the formula-depth
  complexity `KRW.depthOf` of a Boolean function (the minimum depth over all
  formulas computing it), the block composition `KRW.blockComp f g`, and the
  supporting API: variable renaming (`BFormula.rename`), negation by duality
  (`BFormula.dual`), substitution (`BFormula.subst`), the composed formula
  `BFormula.compFormula` with its depth bound, a DNF construction
  (`KRW.dnfOf`) witnessing that every Boolean function is computed by some
  formula, the finite enumeration `BFormula.upTo` of all formulas of bounded
  depth, and an exhaustion principle (`not_computes_of_exhaust`, over the
  explicit assignment list `assignments4`) for kernel-checkable lower bounds
  on four variables. Every API lemma is fully proved. `depthOf` is kernel
  computable on small instances: a claim `depthOf f = k` for concrete tiny
  `f` is proved by an explicit formula (upper bound, `depthOf_le`) plus a
  `decide` exhaust over `upTo` (lower bound, `le_depthOf`); see
  `tests/reference/small-examples.md` of the packaged task.
- The slot zone states the conjecture (`conj`) and its negation (`refuted`).
  Both proof bodies are left blank.

Fidelity notes (see `tests/reference/concept-ledger.md` of the packaged task):
1. Formulas are De Morgan formulas (binary AND/OR; leaves are constants and
   signed literals), the standard basis of the KRW literature; a leaf has
   depth 0. Negations are free (pushed to the leaves), matching the
   literature convention that NOT gates do not count towards depth.
2. `depthOf f` is the minimum depth over *all* formulas computing `f`
   (`sInf` over a set of natural numbers; attained because every Boolean
   function has a DNF). Allowing constant leaves does not change `depthOf f`
   for non-constant `f` (constants can be eliminated without increasing
   depth), and keeps the notion total on zero-variable and constant
   functions.
3. The conjecture's reciprocal-share form lands as `∃ k : ℕ, 2 ≤ k, ∀ f g
   non-constant, k·D(f) + D(g) ≤ k·D(f ⋄ g)` in natural multiplication (no
   division, no truncated subtraction; equivalently, the inner depth enters
   at a ceiling share `⌈D(g)/k⌉`); the non-constancy hypothesis is essential
   (with `g` constant, `f ⋄ g` is constant while `D(g) = 0` and `D(f)` is
   arbitrary). The earlier `∃ c` additive-constant landing was removed on
   Pudlák counterexample, KRW 1995 p. 196.
-/

import Mathlib

/- The section-variable linter flags theorems whose instance arguments are only
used through other declarations in this file (e.g. `depthOf_le` via `depthOf`);
the variables are genuinely needed. Part of the fixed zone. -/
set_option linter.unusedSectionVars false

namespace KRW

/-! ### De Morgan formulas over a finite variable index set -/

/-- Boolean formulas over the De Morgan basis with variables indexed by `ι`:
leaves are Boolean constants (`const`) and signed literals (`lit i b`, the
variable `xᵢ` when `b = true`, its negation `¬xᵢ` when `b = false`); internal
nodes are binary AND/OR. -/
inductive BFormula (ι : Type*) where
  | const (b : Bool)
  | lit (i : ι) (b : Bool)
  | and (φ ψ : BFormula ι)
  | or (φ ψ : BFormula ι)
deriving DecidableEq

namespace BFormula

section EvalDepth

variable {ι : Type*}

/-- The depth of a formula: leaves have depth 0; an AND/OR node adds 1 to the
maximum of its subformula depths. -/
def depth : BFormula ι → ℕ
  | const _ => 0
  | lit _ _ => 0
  | and φ ψ => max φ.depth ψ.depth + 1
  | or φ ψ => max φ.depth ψ.depth + 1

/-- Evaluation of a formula at an assignment `x : ι → Bool`. -/
def eval : BFormula ι → (ι → Bool) → Bool
  | const b, _ => b
  | lit i b, x => x i == b
  | and φ ψ, x => φ.eval x && ψ.eval x
  | or φ ψ, x => φ.eval x || ψ.eval x

/-- `φ.Computes f`: the formula `φ` computes the Boolean function `f` (agrees
with `f` on every assignment). -/
def Computes (φ : BFormula ι) (f : (ι → Bool) → Bool) : Prop :=
  ∀ x, φ.eval x = f x

/-- Rename the variables of a formula along `r : ι → κ`. -/
def rename {κ : Type*} (r : ι → κ) : BFormula ι → BFormula κ
  | const b => const b
  | lit i b => lit (r i) b
  | and φ ψ => and (φ.rename r) (ψ.rename r)
  | or φ ψ => or (φ.rename r) (ψ.rename r)

theorem depth_rename {κ : Type*} (r : ι → κ) (φ : BFormula ι) :
    (φ.rename r).depth = φ.depth := by
  induction φ <;> simp [rename, depth, *]

theorem eval_rename {κ : Type*} (r : ι → κ) (φ : BFormula ι) (x : κ → Bool) :
    (φ.rename r).eval x = φ.eval (x ∘ r) := by
  induction φ <;> simp [rename, eval, Function.comp_apply, *]

/-- Negation by duality: the De Morgan dual of a formula computes the negation
of the original function, at the same depth. -/
def dual : BFormula ι → BFormula ι
  | const b => const !b
  | lit i b => lit i !b
  | and φ ψ => or φ.dual ψ.dual
  | or φ ψ => and φ.dual ψ.dual

theorem depth_dual (φ : BFormula ι) : φ.dual.depth = φ.depth := by
  induction φ <;> simp [dual, depth, *]

theorem eval_dual (φ : BFormula ι) (x : ι → Bool) : φ.dual.eval x = !(φ.eval x) := by
  induction φ with
  | const b => rfl
  | lit i b =>
      have h : ∀ v b : Bool, (v == !b) = !(v == b) := by decide
      exact h _ _
  | and φ ψ ihφ ihψ => simp [dual, eval, ihφ, ihψ, Bool.not_and]
  | or φ ψ ihφ ihψ => simp [dual, eval, ihφ, ihψ, Bool.not_or]

/-- Substitution: replace every literal leaf `lit i b` by `σ i` when
`b = true` and by the dual of `σ i` when `b = false`. -/
def subst {κ : Type*} (σ : ι → BFormula κ) : BFormula ι → BFormula κ
  | const b => const b
  | lit i true => σ i
  | lit i false => (σ i).dual
  | and φ ψ => and (φ.subst σ) (ψ.subst σ)
  | or φ ψ => or (φ.subst σ) (ψ.subst σ)

theorem eval_subst {κ : Type*} (σ : ι → BFormula κ) (φ : BFormula ι) (x : κ → Bool) :
    (φ.subst σ).eval x = φ.eval (fun i => (σ i).eval x) := by
  induction φ with
  | const b => rfl
  | lit i b =>
      have h1 : ∀ v : Bool, v = (v == true) := by decide
      have h2 : ∀ v : Bool, (!v) = (v == false) := by decide
      cases b
      · simp only [subst, eval, eval_dual]
        exact h2 _
      · simp only [subst, eval]
        exact h1 _
  | and φ ψ ihφ ihψ => simp [subst, eval, ihφ, ihψ]
  | or φ ψ ihφ ihψ => simp [subst, eval, ihφ, ihψ]

theorem depth_subst_le {κ : Type*} [Fintype ι] (σ : ι → BFormula κ) (φ : BFormula ι) :
    (φ.subst σ).depth ≤ φ.depth + Finset.univ.sup (fun i => (σ i).depth) := by
  induction φ with
  | const b => exact Nat.zero_le _
  | lit i b =>
      have h : (σ i).depth ≤ Finset.univ.sup (fun i => (σ i).depth) :=
        Finset.le_sup (f := fun i => (σ i).depth) (Finset.mem_univ i)
      cases b <;> simp only [subst, depth_dual, depth, Nat.zero_add] <;> exact h
  | and φ ψ ihφ ihψ =>
      simp only [subst, depth]
      have h1 := Nat.add_le_add_right (max_le_max ihφ ihψ) 1
      have h2 : max (φ.depth + Finset.univ.sup (fun i => (σ i).depth))
          (ψ.depth + Finset.univ.sup (fun i => (σ i).depth)) =
          max φ.depth ψ.depth + Finset.univ.sup (fun i => (σ i).depth) := by
        omega
      omega
  | or φ ψ ihφ ihψ =>
      simp only [subst, depth]
      have h1 := Nat.add_le_add_right (max_le_max ihφ ihψ) 1
      have h2 : max (φ.depth + Finset.univ.sup (fun i => (σ i).depth))
          (ψ.depth + Finset.univ.sup (fun i => (σ i).depth)) =
          max φ.depth ψ.depth + Finset.univ.sup (fun i => (σ i).depth) := by
        omega
      omega

end EvalDepth

section ComputesDec

variable {ι : Type*} [Fintype ι] [DecidableEq ι]

instance {φ : BFormula ι} {f : (ι → Bool) → Bool} : Decidable (φ.Computes f) :=
  inferInstanceAs (Decidable (∀ x, φ.eval x = f x))

end ComputesDec

end BFormula

/-! ### Block composition of Boolean functions -/

/-- The block composition of `f` on `m` variables and `g` on `n` variables:
the function on the `m × n` variables indexed by pairs `(i, j)` that applies
`g` to each block `xᵢ,·` and then `f` to the `m` results. -/
def blockComp {m n : ℕ} (f : (Fin m → Bool) → Bool) (g : (Fin n → Bool) → Bool) :
    (Fin m × Fin n → Bool) → Bool :=
  fun x => f (fun i => g (fun j => x (i, j)))

namespace BFormula

variable {m n : ℕ}

/-- The composed formula: substitute into `φ` (over the `m` outer variables)
the formula `ψ` renamed onto the `i`-th variable block, for each outer
variable `i`. -/
def compFormula (φ : BFormula (Fin m)) (ψ : BFormula (Fin n)) :
    BFormula (Fin m × Fin n) :=
  φ.subst (fun i => ψ.rename fun j => (i, j))

theorem compFormula_computes {f : (Fin m → Bool) → Bool} {g : (Fin n → Bool) → Bool}
    {φ : BFormula (Fin m)} {ψ : BFormula (Fin n)}
    (hφ : φ.Computes f) (hψ : ψ.Computes g) :
    (compFormula φ ψ).Computes (blockComp f g) := by
  intro x
  show (φ.subst fun i => ψ.rename fun j => (i, j)).eval x =
    f (fun i => g (fun j => x (i, j)))
  rw [eval_subst]
  have e1 : (fun i => (ψ.rename fun j => (i, j)).eval x) =
      (fun i => ψ.eval fun j => x (i, j)) :=
    funext fun i => eval_rename _ _ _
  rw [e1]
  have e2 : (fun i => ψ.eval fun j => x (i, j)) = (fun i => g fun j => x (i, j)) :=
    funext fun i => hψ _
  rw [e2]
  exact hφ _

theorem depth_compFormula_le (φ : BFormula (Fin m)) (ψ : BFormula (Fin n)) :
    (compFormula φ ψ).depth ≤ φ.depth + ψ.depth := by
  refine Nat.le_trans (depth_subst_le (fun i => ψ.rename fun j => (i, j)) φ) ?_
  have h : Finset.univ.sup (fun i : Fin m => (ψ.rename fun j => (i, j)).depth) ≤ ψ.depth := by
    apply Finset.sup_le
    intro i _
    rw [depth_rename]
  exact Nat.add_le_add_left h φ.depth

end BFormula

/-! ### Every Boolean function is computed by some formula (DNF) -/

section DNF

variable {ι : Type*} [Fintype ι] [DecidableEq ι]

/-- The characteristic term of an assignment `x`: the conjunction of the
literals pinning every coordinate to its value in `x`; true exactly at `x`. -/
noncomputable def BFormula.termOf (x : ι → Bool) : BFormula ι :=
  Finset.univ.toList.foldl (fun acc i => BFormula.and acc (BFormula.lit i (x i)))
    (BFormula.const true)

theorem eval_foldl_and_term (x y : ι → Bool) (l : List ι) (init : BFormula ι) :
    ((l.foldl (fun acc i => BFormula.and acc (BFormula.lit i (x i))) init).eval y = true) ↔
      (init.eval y = true ∧ ∀ i ∈ l, y i = x i) := by
  induction l generalizing init with
  | nil => simp
  | cons a l ih =>
      simp only [List.foldl_cons, ih, BFormula.eval, Bool.and_eq_true, beq_iff_eq,
        List.forall_mem_cons]
      tauto

theorem BFormula.eval_termOf (x y : ι → Bool) : ((BFormula.termOf x).eval y = true) ↔ y = x := by
  rw [BFormula.termOf, eval_foldl_and_term]
  constructor
  · rintro ⟨_, h⟩
    funext i
    exact h i (Finset.mem_toList.mpr (Finset.mem_univ i))
  · intro h
    refine ⟨rfl, fun i _ => ?_⟩
    exact congrFun h i

/-- The full DNF of `f`: the disjunction of the characteristic terms of all
assignments mapped to `true`. Witnesses that every Boolean function is
computed by some formula. -/
noncomputable def BFormula.dnfOf (f : (ι → Bool) → Bool) : BFormula ι :=
  (Finset.univ.filter fun x => f x = true).toList.foldl
    (fun acc x => BFormula.or acc (BFormula.termOf x)) (BFormula.const false)

theorem eval_foldl_or_term (y : ι → Bool) (l : List (ι → Bool)) (init : BFormula ι) :
    ((l.foldl (fun acc x => BFormula.or acc (BFormula.termOf x)) init).eval y = true) ↔
      (init.eval y = true ∨ ∃ x ∈ l, (BFormula.termOf x).eval y = true) := by
  induction l generalizing init with
  | nil => simp
  | cons a l ih =>
      rw [List.foldl_cons, ih]
      simp only [BFormula.eval, Bool.or_eq_true, List.mem_cons]
      constructor
      · rintro ((h | h) | ⟨x, hx, hxe⟩)
        · exact Or.inl h
        · exact Or.inr ⟨a, Or.inl rfl, h⟩
        · exact Or.inr ⟨x, Or.inr hx, hxe⟩
      · rintro (h | ⟨x, rfl | hx, hxe⟩)
        · exact Or.inl (Or.inl h)
        · exact Or.inl (Or.inr hxe)
        · exact Or.inr ⟨x, hx, hxe⟩

theorem BFormula.eval_dnfOf (f : (ι → Bool) → Bool) (y : ι → Bool) :
    (BFormula.dnfOf f).eval y = f y := by
  have key : ((BFormula.dnfOf f).eval y = true) ↔ (f y = true) := by
    show (((Finset.univ.filter fun x => f x = true).toList.foldl
        (fun acc x => BFormula.or acc (BFormula.termOf x)) (BFormula.const false)).eval y =
          true) ↔ (f y = true)
    rw [eval_foldl_or_term]
    constructor
    · rintro (h | ⟨x, hx, hxe⟩)
      · simp [BFormula.eval] at h
      · have hxf : f x = true := by
          have hx' : x ∈ Finset.univ.filter (fun x => f x = true) := Finset.mem_toList.mp hx
          exact (Finset.mem_filter.mp hx').2
        rw [BFormula.eval_termOf] at hxe
        rw [hxe]
        exact hxf
    · intro hfy
      exact Or.inr ⟨y,
        Finset.mem_toList.mpr (Finset.mem_filter.mpr ⟨Finset.mem_univ y, hfy⟩),
        (BFormula.eval_termOf y y).mpr rfl⟩
  cases he : (BFormula.dnfOf f).eval y <;> cases hf : f y <;> simp_all

/-- Every Boolean function is computed by some formula (its full DNF). -/
theorem exists_computes (f : (ι → Bool) → Bool) : ∃ φ : BFormula ι, φ.Computes f :=
  ⟨BFormula.dnfOf f, fun y => BFormula.eval_dnfOf f y⟩

end DNF

/-! ### Formula-depth complexity -/

section DepthOf

variable {ι : Type*} [Fintype ι] [DecidableEq ι]

/-- `depthOf f`: the formula-depth complexity of `f` — the minimum depth over
all De Morgan formulas computing `f`. Total on every finite index set,
because every Boolean function has a DNF (`exists_computes`). -/
noncomputable def depthOf (f : (ι → Bool) → Bool) : ℕ :=
  sInf {d | ∃ φ : BFormula ι, φ.depth = d ∧ φ.Computes f}

/-- Any formula computing `f` gives an upper bound on `depthOf f`. -/
theorem depthOf_le {f : (ι → Bool) → Bool} {φ : BFormula ι} (h : φ.Computes f) :
    depthOf f ≤ φ.depth :=
  Nat.sInf_le ⟨φ, rfl, h⟩

/-- The minimum is attained: some formula computing `f` has depth exactly
`depthOf f`. -/
theorem exists_computes_depth_eq (f : (ι → Bool) → Bool) :
    ∃ φ : BFormula ι, φ.depth = depthOf f ∧ φ.Computes f := by
  have hne : {d : ℕ | ∃ φ : BFormula ι, φ.depth = d ∧ φ.Computes f}.Nonempty := by
    obtain ⟨φ, hφ⟩ := exists_computes f
    exact ⟨φ.depth, φ, rfl, hφ⟩
  exact Nat.sInf_mem hne

/-- A lower bound on the depth of every formula computing `f` gives a lower
bound on `depthOf f`. -/
theorem le_depthOf {f : (ι → Bool) → Bool} {k : ℕ}
    (h : ∀ φ : BFormula ι, φ.Computes f → k ≤ φ.depth) : k ≤ depthOf f := by
  obtain ⟨φ, hφdepth, hφcomp⟩ := exists_computes_depth_eq f
  rw [← hφdepth]
  exact h φ hφcomp

end DepthOf

namespace BFormula

variable {ι : Type*} [Fintype ι] [DecidableEq ι]

/-- All formulas of depth at most `d`, as a finite set: the basis for
kernel-checkable exhaustive statements about small instances. -/
def upTo : (d : ℕ) → Finset (BFormula ι)
  | 0 =>
      {const false, const true} ∪
        Finset.univ.biUnion fun i => ({lit i false, lit i true} : Finset (BFormula ι))
  | d + 1 =>
      upTo d ∪ (upTo d ×ˢ upTo d).image (fun p => and p.1 p.2) ∪
        (upTo d ×ˢ upTo d).image (fun p => or p.1 p.2)

theorem upTo_mono {d₁ d₂ : ℕ} (h : d₁ ≤ d₂) : upTo (ι := ι) d₁ ⊆ upTo (ι := ι) d₂ := by
  induction h with
  | refl => exact Finset.Subset.refl _
  | step _ ih =>
      intro x hx
      exact Finset.mem_union_left _ (Finset.mem_union_left _ (ih hx))

theorem mem_upTo {d : ℕ} {φ : BFormula ι} : φ ∈ upTo d ↔ φ.depth ≤ d := by
  induction d generalizing φ with
  | zero =>
      constructor
      · intro h
        simp only [upTo, Finset.mem_union, Finset.mem_insert, Finset.mem_singleton,
          Finset.mem_biUnion, Finset.mem_univ, true_and] at h
        rcases h with (rfl | rfl) | ⟨i, rfl | rfl⟩ <;> rfl
      · intro h
        cases φ with
        | const b =>
            simp only [upTo, Finset.mem_union, Finset.mem_insert, Finset.mem_singleton]
            cases b <;> simp
        | lit i b =>
            simp only [upTo, Finset.mem_union, Finset.mem_insert, Finset.mem_singleton,
              Finset.mem_biUnion, Finset.mem_univ, true_and]
            exact Or.inr ⟨i, by cases b <;> simp⟩
        | and φ ψ => simp [depth] at h
        | or φ ψ => simp [depth] at h
  | succ d ih =>
      constructor
      · intro h
        simp only [upTo, Finset.mem_union, Finset.mem_image, Finset.mem_product] at h
        rcases h with (h | ⟨a, ⟨ha, hb⟩, rfl⟩) | ⟨a, ⟨ha, hb⟩, rfl⟩
        · exact Nat.le_trans (ih.mp h) (Nat.le_succ d)
        · simp only [depth]
          have := ih.mp ha; have := ih.mp hb
          omega
        · simp only [depth]
          have := ih.mp ha; have := ih.mp hb
          omega
      · intro h
        cases φ with
        | const b =>
            apply upTo_mono (Nat.zero_le _)
            cases b <;> simp [upTo]
        | lit i b =>
            apply upTo_mono (Nat.zero_le _)
            cases b <;> simp [upTo]
        | and φ ψ =>
            simp only [depth] at h
            have hφ : φ.depth ≤ d := by omega
            have hψ : ψ.depth ≤ d := by omega
            simp only [upTo, Finset.mem_union, Finset.mem_image, Finset.mem_product]
            exact Or.inl (Or.inr ⟨(φ, ψ), ⟨ih.mpr hφ, ih.mpr hψ⟩, rfl⟩)
        | or φ ψ =>
            simp only [depth] at h
            have hφ : φ.depth ≤ d := by omega
            have hψ : ψ.depth ≤ d := by omega
            simp only [upTo, Finset.mem_union, Finset.mem_image, Finset.mem_product]
            exact Or.inr ⟨(φ, ψ), ⟨ih.mpr hφ, ih.mpr hψ⟩, rfl⟩

end BFormula

/-! ### Non-constancy and concrete small functions -/

/-- A Boolean function is non-constant: it takes both values. This hypothesis
in the conjecture is essential — with `g` constant, `f ⋄ g` is constant while
`D(g) = 0` and `D(f)` is arbitrary. (An `abbrev` so that decidability and
automation see through it.) -/
abbrev NonConst {ι : Type*} (f : (ι → Bool) → Bool) : Prop :=
  ∃ x y, f x ≠ f y

/-- Parity on two variables (XOR). Parity was the inner function of the
strongest early partial results on the conjecture (implicit in Håstad 1998;
Dinur–Meir 2018); in the current strongest result (Chukhin–Kulikov–Mihajlin,
STACS 2025) XOR instead serves as the outer function, composed with a random
inner function. `xor2` is the smallest non-constant member of the parity
family. -/
def xor2 : (Fin 2 → Bool) → Bool := fun x => x 0 ^^ x 1

/-- Conjunction on two variables. -/
def and2 : (Fin 2 → Bool) → Bool := fun x => x 0 && x 1

/-! ### Kernel-checkable exhaustion over the 2 × 2 block variables -/

/-- All 16 assignments of the `2 × 2` block variables, as an explicit list.
Used with `not_computes_of_exhaust` for kernel-checkable exhaustion on four
variables: re-enumerating the function type `Fin 2 × Fin 2 → Bool` once per
candidate formula (the naive `∀ x, …` form) is beyond kernel reach at this
size, while checking each formula against one shared explicit list is a flat
computation (see `tests/reference/small-examples.md` of the packaged task). -/
def assignments4 : List (Fin 2 × Fin 2 → Bool) :=
  [fun p => ![![false, false], ![false, false]] p.1 p.2,
   fun p => ![![false, false], ![false, true]] p.1 p.2,
   fun p => ![![false, true], ![false, false]] p.1 p.2,
   fun p => ![![false, true], ![false, true]] p.1 p.2,
   fun p => ![![true, false], ![false, false]] p.1 p.2,
   fun p => ![![true, false], ![false, true]] p.1 p.2,
   fun p => ![![true, true], ![false, false]] p.1 p.2,
   fun p => ![![true, true], ![false, true]] p.1 p.2,
   fun p => ![![false, false], ![true, false]] p.1 p.2,
   fun p => ![![false, false], ![true, true]] p.1 p.2,
   fun p => ![![false, true], ![true, false]] p.1 p.2,
   fun p => ![![false, true], ![true, true]] p.1 p.2,
   fun p => ![![true, false], ![true, false]] p.1 p.2,
   fun p => ![![true, false], ![true, true]] p.1 p.2,
   fun p => ![![true, true], ![true, false]] p.1 p.2,
   fun p => ![![true, true], ![true, true]] p.1 p.2]

/-- The explicit list is complete (single enumeration of the 16 assignments). -/
theorem mem_assignments4 : ∀ x : Fin 2 × Fin 2 → Bool, x ∈ assignments4 := by
  decide

/-- Exhaustion principle for `depthOf` lower bounds: if every formula of
depth ≤ `d` disagrees with `f` somewhere on the assignment list `L`, then
every formula computing `f` has depth > `d` (a formula computing `f` agrees
with `f` on every assignment, in particular on all of `L`). The kernel
evaluates the hypothesis as one flat computation (all formulas × all
assignments) instead of re-enumerating the function type per formula.
Completeness of `L` is not needed for soundness; for `assignments4` it is
verified separately as `mem_assignments4`. -/
theorem not_computes_of_exhaust {ι : Type*} [Fintype ι] [DecidableEq ι]
    (f : (ι → Bool) → Bool) (L : List (ι → Bool)) (_hL : ∀ x, x ∈ L) {d : ℕ}
    (h : ∀ ψ ∈ BFormula.upTo (ι := ι) d, (L.all fun x => ψ.eval x == f x) = false) :
    ∀ φ : BFormula ι, φ.depth ≤ d → ¬φ.Computes f := by
  intro φ hφd hcomp
  have h1 := h φ (BFormula.mem_upTo.mpr hφd)
  have h2 : (L.all fun x => φ.eval x == f x) = true := by
    rw [List.all_eq_true]
    intro x _
    rw [hcomp x]
    exact beq_self_eq_true (f x)
  rw [h2] at h1
  simp at h1

/- The kernel recursion limit and the elaboration heartbeat limit are raised
so that `decide` can evaluate the bounded-depth enumerations
(`BFormula.upTo`) behind the small concrete instances (the nested
construction exceeds the default limits; the pin values were set by
measurement, see `tests/reference/small-examples.md` of the packaged task).
These lines are part of the fixed zone; the grader variants inherit them. -/
set_option maxRecDepth 8192
set_option maxHeartbeats 800000

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

/-! ## Slot zone: the conjecture and its negation -/

namespace KRWConjecture

-- @[slot main]
/-- **The KRW composition conjecture, reciprocal-share form** (Karchmer–Raz–Wigderson 1995; form as in Gavinsky–Meir–Weinstein–Wigderson, ECCC TR13-190 rev. 11 (2017), Conjecture 1.3 and footnote 3(ii)): there is a universal `k ≥ 2` such that for all non-constant Boolean functions `f` (outer) and `g` (inner), the block composition satisfies `D(f ⋄ g) ≥ D(f) + D(g)/k` — stated as `k·D(f) + D(g) ≤ k·D(f ⋄ g)` in natural-number multiplication, avoiding division and truncated subtraction (equivalently, inner depth at a ceiling share `⌈D(g)/k⌉`). The universal-additive-constant form `D(f ⋄ g) ≥ D(f) + D(g) − c` is NOT the open conjecture: Pudlák's example (recorded in KRW 1995, p. 196) makes the additive gap grow like `log log n`, so that form was known false from the start. -/
theorem conj :
    ∃ k : ℕ, 2 ≤ k ∧
      ∀ (m n : ℕ) (f : (Fin m → Bool) → Bool) (g : (Fin n → Bool) → Bool),
        KRW.NonConst f → KRW.NonConst g →
          k * KRW.depthOf f + KRW.depthOf g ≤
            k * KRW.depthOf (KRW.blockComp f g) := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

-- @[slot main]
/-- The negation of the KRW composition conjecture: for every `k ≥ 2` there
are non-constant `f`, `g` with `k·D(f ⋄ g) < k·D(f) + D(g)` (the witnesses may
depend on `k`). -/
theorem refuted :
    ∀ k : ℕ, 2 ≤ k →
      ∃ (m n : ℕ) (f : (Fin m → Bool) → Bool) (g : (Fin n → Bool) → Bool),
        KRW.NonConst f ∧ KRW.NonConst g ∧
          k * KRW.depthOf (KRW.blockComp f g) <
            k * KRW.depthOf f + KRW.depthOf g := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

end KRWConjecture

end KRW
