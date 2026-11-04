/-
Statement layer for the Frege versus Extended Frege separation problem
(Cook–Reckhow, *The relative efficiency of propositional proof systems*,
J. Symbolic Logic 44(1):36–50, 1979; listed as a central open problem in
Krajíček, *Proof Complexity*, Cambridge University Press, 2019):

  an Extended Frege (EF) system augments a Frege system by the extension
  rule, which at any point may introduce a fresh atom `p` as an abbreviation
  for an already-built formula `D`, by deriving `p ↔ D`. The question is
  whether Frege can p-simulate Extended Frege — whether every EF proof can be
  converted into a Frege proof of the same tautology with at most polynomial
  blow-up in symbol size. The prevailing conjecture is that it cannot —
  the framework and the question originate with Cook–Reckhow 1979; as the
  prevailing conjecture see Krajíček 2019.

This file is the task's definition zone plus slot zone:
- The definition zone (namespace `Frege`) defines propositional formulas
  over an atom type (atoms, `falsum`, `∧`, `∨`, `→`; negation `¬φ` is the
  abbreviation `φ → ⊥`), formula size in symbols, the atoms of a formula
  (`Formula.vars`), substitution, Boolean evaluation and tautologies; a
  fixed Frege system given by ten axiom schemes with modus ponens as the
  only inference rule; Frege proofs as sequences of formulas (`IsProof`),
  provability (`Provable`), and proof size in symbols (`proofSize`). It
  then defines the Extended Frege layer on top: EF proofs (`IsEFProof`,
  Frege steps plus extension steps), the extension-step predicate
  (`ExtStep`), and EF provability with the conclusion condition
  (`EFProves`, `EFProvable`). It also proves the soundness API: every axiom
  is a tautology, modus ponens preserves tautologies, and evaluation only
  depends on the atoms occurring in the formula (`Formula.eval_agree`).
- The slot zone states the separation conjecture (`conj`: Frege does not
  polynomially simulate Extended Frege) and its negation (`refuted`).
  Both proof bodies are left blank.

Fidelity notes (see `tests/reference/concept-ledger.md` of the packaged
task):
1. A single concrete Frege system is fixed (ten axiom schemes over
   {⊥, ∧, ∨, →} plus modus ponens). By Reckhow's 1979 theorem all Frege
   systems are p-equivalent, and their EF extensions are p-equivalent as
   well, so the separation question is independent of the chosen system;
   fixing one system is standard textbook practice.
2. Proof length is measured in symbols (`proofSize`), the standard
   convention in proof complexity. "Polynomial" is expressed by the
   explicit monomials `(n + 1) ^ d` for `d : ℕ`.
3. The biconditional `p ↔ D` of the extension rule is unfolded over the
   fixed connective set as `(p → D) ∧ (D → p)` (the standard expansion).
   Following Cook–Reckhow 1979, the extension atom `p` must be fresh: it
   occurs neither in `D` nor in any earlier line, and — the conclusion
   condition — not in the proved formula; without the conclusion condition
   the calculus would derive plain atoms, so EF would be unsound. The three
   ingredients of EF soundness are proved below (`IsAxiom.tautology`,
   `Tautology.mp`, `Formula.eval_agree`); the assembled statement — every
   EF-provable formula is a tautology — is not part of this file and is
   taken as a standard literature fact.
4. The simulation bound compares proof sizes only (a "simulation" in
   Cook–Reckhow terminology): `conj` states that for every degree `d` some
   EF proof outgrows the bound `(proofSize + 1) ^ d` for all Frege proofs
   of the same formula. Non-existence of such a length simulation implies
   non-existence of a p-simulation.
-/

import Mathlib

namespace Frege

variable {α β : Type}

/-! ### Propositional formulas -/

/-- Propositional formulas over an atom type `α`: atoms, falsum `⊥`, and the
binary connectives `∧`, `∨`, `→`. Negation `¬φ` is read as the abbreviation
`φ → ⊥`. -/
inductive Formula (α : Type) : Type
  | atom (a : α)
  | falsum
  | and (φ ψ : Formula α)
  | or (φ ψ : Formula α)
  | imp (φ ψ : Formula α)
  deriving Repr, DecidableEq

namespace Formula

/-- Formula size in symbols: 1 for an atom or `⊥`, and
`1 + size φ + size ψ` for a binary connective. -/
def size : Formula α → ℕ
  | atom _ => 1
  | falsum => 1
  | and φ ψ => size φ + size ψ + 1
  | or φ ψ => size φ + size ψ + 1
  | imp φ ψ => size φ + size ψ + 1

/-- Simultaneous substitution of formulas for the atoms. -/
def subst (σ : α → Formula β) : Formula α → Formula β
  | atom a => σ a
  | falsum => falsum
  | and φ ψ => and (φ.subst σ) (ψ.subst σ)
  | or φ ψ => or (φ.subst σ) (ψ.subst σ)
  | imp φ ψ => imp (φ.subst σ) (ψ.subst σ)

/-- The atoms occurring in a formula (with duplicates): its free variables.
Membership `a ∈ φ.vars` is decidable for atoms with decidable equality. -/
def vars : Formula α → List α
  | atom a => [a]
  | falsum => []
  | and φ ψ => vars φ ++ vars ψ
  | or φ ψ => vars φ ++ vars ψ
  | imp φ ψ => vars φ ++ vars ψ

/-- Boolean evaluation under the assignment `v : α → Bool`; the implication
`φ → ψ` evaluates as `¬φ ∨ ψ`. -/
def eval (v : α → Bool) : Formula α → Bool
  | atom a => v a
  | falsum => false
  | and φ ψ => eval v φ && eval v ψ
  | or φ ψ => eval v φ || eval v ψ
  | imp φ ψ => !eval v φ || eval v ψ

/-- Evaluation only depends on the atoms occurring in the formula: two
assignments agreeing on `φ.vars` give the same value. -/
theorem eval_agree {φ : Formula α} {v w : α → Bool}
    (h : ∀ a, a ∈ φ.vars → v a = w a) : φ.eval v = φ.eval w := by
  induction φ with
  | atom a =>
      simp only [vars, List.mem_singleton] at h
      simp only [eval, h a rfl]
  | falsum => rfl
  | and φ ψ ihφ ihψ =>
      simp only [vars, List.mem_append] at h
      simp only [eval, ihφ (fun a ha => h a (Or.inl ha)),
        ihψ (fun a ha => h a (Or.inr ha))]
  | or φ ψ ihφ ihψ =>
      simp only [vars, List.mem_append] at h
      simp only [eval, ihφ (fun a ha => h a (Or.inl ha)),
        ihψ (fun a ha => h a (Or.inr ha))]
  | imp φ ψ ihφ ihψ =>
      simp only [vars, List.mem_append] at h
      simp only [eval, ihφ (fun a ha => h a (Or.inl ha)),
        ihψ (fun a ha => h a (Or.inr ha))]

end Formula

/-- A tautology: a formula true under every Boolean assignment. -/
def Tautology (φ : Formula α) : Prop :=
  ∀ v : α → Bool, φ.eval v = true

/-! ### The Frege system: ten axiom schemes with modus ponens -/

/-- The axiom schemes of the fixed Frege system. Each scheme ranges over all
formulas, so substitution instances are built in:
- `k`, `s`: the Łukasiewicz implication schemes
  `φ → (ψ → φ)` and `(φ → (ψ → χ)) → ((φ → ψ) → (φ → χ))`;
- `exFalso`: `⊥ → φ`;
- `peirce`: Peirce's law `((φ → ψ) → φ) → φ` (classicality);
- `andElimLeft`, `andElimRight`, `andIntro`: the standard `∧` schemes;
- `orIntroLeft`, `orIntroRight`, `orElim`: the standard `∨` schemes.

With modus ponens as the only rule this is a complete axiomatization of
classical propositional logic over `{⊥, ∧, ∨, →}` (the `{→, ⊥}` fragment
K + S + ex falso + Peirce is classically complete; the remaining schemes are
the usual introduction and elimination axioms). Completeness is a literature
fact and is not proved in this file. -/
inductive IsAxiom : Formula α → Prop
  | k (φ ψ : Formula α) :
      IsAxiom (Formula.imp φ (Formula.imp ψ φ))
  | s (φ ψ χ : Formula α) :
      IsAxiom (Formula.imp (Formula.imp φ (Formula.imp ψ χ))
        (Formula.imp (Formula.imp φ ψ) (Formula.imp φ χ)))
  | exFalso (φ : Formula α) :
      IsAxiom (Formula.imp Formula.falsum φ)
  | peirce (φ ψ : Formula α) :
      IsAxiom (Formula.imp (Formula.imp (Formula.imp φ ψ) φ) φ)
  | andElimLeft (φ ψ : Formula α) :
      IsAxiom (Formula.imp (Formula.and φ ψ) φ)
  | andElimRight (φ ψ : Formula α) :
      IsAxiom (Formula.imp (Formula.and φ ψ) ψ)
  | andIntro (φ ψ : Formula α) :
      IsAxiom (Formula.imp φ (Formula.imp ψ (Formula.and φ ψ)))
  | orIntroLeft (φ ψ : Formula α) :
      IsAxiom (Formula.imp φ (Formula.or φ ψ))
  | orIntroRight (φ ψ : Formula α) :
      IsAxiom (Formula.imp ψ (Formula.or φ ψ))
  | orElim (φ ψ χ : Formula α) :
      IsAxiom (Formula.imp (Formula.imp φ χ)
        (Formula.imp (Formula.imp ψ χ) (Formula.imp (Formula.or φ ψ) χ)))

/-- Every axiom is a tautology. -/
theorem IsAxiom.tautology {θ : Formula α} (h : IsAxiom θ) : Tautology θ := by
  induction h with
  | k φ ψ =>
      intro v
      simp only [Formula.eval]
      cases Formula.eval v φ <;> cases Formula.eval v ψ <;> rfl
  | s φ ψ χ =>
      intro v
      simp only [Formula.eval]
      cases Formula.eval v φ <;> cases Formula.eval v ψ <;>
        cases Formula.eval v χ <;> rfl
  | exFalso φ =>
      intro v
      simp only [Formula.eval]
      cases Formula.eval v φ <;> rfl
  | peirce φ ψ =>
      intro v
      simp only [Formula.eval]
      cases Formula.eval v φ <;> cases Formula.eval v ψ <;> rfl
  | andElimLeft φ ψ =>
      intro v
      simp only [Formula.eval]
      cases Formula.eval v φ <;> cases Formula.eval v ψ <;> rfl
  | andElimRight φ ψ =>
      intro v
      simp only [Formula.eval]
      cases Formula.eval v φ <;> cases Formula.eval v ψ <;> rfl
  | andIntro φ ψ =>
      intro v
      simp only [Formula.eval]
      cases Formula.eval v φ <;> cases Formula.eval v ψ <;> rfl
  | orIntroLeft φ ψ =>
      intro v
      simp only [Formula.eval]
      cases Formula.eval v φ <;> cases Formula.eval v ψ <;> rfl
  | orIntroRight φ ψ =>
      intro v
      simp only [Formula.eval]
      cases Formula.eval v φ <;> cases Formula.eval v ψ <;> rfl
  | orElim φ ψ χ =>
      intro v
      simp only [Formula.eval]
      cases Formula.eval v φ <;> cases Formula.eval v ψ <;>
        cases Formula.eval v χ <;> rfl

/-- Modus ponens preserves tautologies. -/
theorem Tautology.mp {φ ψ : Formula α} (h₂ : Tautology (Formula.imp φ ψ))
    (h₁ : Tautology φ) : Tautology ψ := by
  intro v
  have a := h₁ v
  have b := h₂ v
  simp only [Formula.eval] at b
  rw [a] at b
  simp only [Bool.not_true, Bool.false_or] at b
  exact b

/-! ### Frege proofs and proof size -/

/-- A proof in the fixed Frege system: a finite sequence of formulas in which
every line is an axiom (an instance of one of the ten schemes) or follows by
modus ponens from two earlier lines `π[i]` and `π[j] = π[i] → π[k]`. -/
def IsProof (π : List (Formula α)) : Prop :=
  ∀ k : Fin π.length,
    IsAxiom (π.get k) ∨
      ∃ i j : Fin π.length, i < k ∧ j < k ∧
        π.get j = Formula.imp (π.get i) (π.get k)

/-- Provability: some Frege proof has `φ` as its last line. -/
def Provable (φ : Formula α) : Prop :=
  ∃ π : List (Formula α), IsProof π ∧ π.getLast? = some φ

/-- The size of a proof in symbols: the sum of the formula sizes of its
lines. -/
def proofSize (π : List (Formula α)) : ℕ :=
  (π.map Formula.size).sum

/-! ### Extended Frege: the extension rule -/

/-- An Extended Frege proof: a finite sequence of formulas in which every
line is an axiom, or follows by modus ponens from two earlier lines, or is
an **extension step**: a line `(p → D) ∧ (D → p)` — the biconditional
`p ↔ D` unfolded over the fixed connective set — introducing the atom `p`
as an abbreviation for `D`, where `p` is fresh: it occurs neither in `D`
nor in any earlier line of the sequence (Cook–Reckhow 1979; the freshness
side conditions on `Formula.vars` are the defining feature of the rule). -/
def IsEFProof (π : List (Formula α)) : Prop :=
  ∀ k : Fin π.length,
    IsAxiom (π.get k) ∨
      (∃ i j : Fin π.length, i < k ∧ j < k ∧
        π.get j = Formula.imp (π.get i) (π.get k)) ∨
      (∃ (p : α) (D : Formula α),
        π.get k = Formula.and (Formula.imp (Formula.atom p) D)
          (Formula.imp D (Formula.atom p)) ∧
        p ∉ D.vars ∧
        ∀ l : Fin π.length, l < k → p ∉ (π.get l).vars)

/-- Line `k` of `π` is an extension step introducing the extension atom `p`:
the line is `(p → D) ∧ (D → p)`, `p` does not occur in `D`, and `p` does not
occur in any earlier line. -/
def ExtStep (π : List (Formula α)) (k : Fin π.length) (p : α) : Prop :=
  ∃ D : Formula α,
    π.get k = Formula.and (Formula.imp (Formula.atom p) D)
      (Formula.imp D (Formula.atom p)) ∧
    p ∉ D.vars ∧
    ∀ l : Fin π.length, l < k → p ∉ (π.get l).vars

/-- `π` is an Extended Frege proof of `φ`: an EF proof ending in `φ` that
satisfies the **conclusion condition** (Cook–Reckhow 1979): no extension
atom occurs in the proved formula. Without this condition the calculus
would derive plain atoms — introduce `p ↔ D` for a provable `D`, detach
`D → p`, and conclude `p` — so it is part of the definition of EF
provability, and it is what makes EF sound: every EF-provable formula is a
tautology. The three ingredients of that statement are proved above
(`IsAxiom.tautology`, `Tautology.mp`, `Formula.eval_agree`); the assembled
soundness statement itself is not part of this file and is taken as a
standard literature fact. -/
def EFProves (π : List (Formula α)) (φ : Formula α) : Prop :=
  IsEFProof π ∧ π.getLast? = some φ ∧
    ∀ (k : Fin π.length) (p : α), ExtStep π k p → p ∉ φ.vars

/-- EF provability: some Extended Frege proof proves `φ`. -/
def EFProvable (φ : Formula α) : Prop :=
  ∃ π : List (Formula α), EFProves π φ

end Frege

namespace FregeVsExtendedFrege

open Frege

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

/-! ## Slot zone: the conjecture and its negation -/

-- @[slot main]
/-- **The separation conjecture** (framework and question: Cook–Reckhow
1979; as the prevailing conjecture see Krajíček 2019):
Frege does not polynomially simulate Extended Frege — for every degree
`d` there is an Extended Frege proof `π` of some formula `φ` such that
every Frege proof of `φ` has symbol size greater than
`(proofSize π + 1) ^ d`. -/
theorem conj :
    ∀ d : ℕ, ∃ φ : Formula ℕ, ∃ π : List (Formula ℕ),
      EFProves π φ ∧
      ∀ π' : List (Formula ℕ), IsProof π' → π'.getLast? = some φ →
        (proofSize π + 1) ^ d < proofSize π' := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

-- @[slot main]
/-- The negation of the separation conjecture: some degree `d` bounds a
Frege simulation of every Extended Frege proof (in symbol size). -/
theorem refuted :
    ¬∀ d : ℕ, ∃ φ : Formula ℕ, ∃ π : List (Formula ℕ),
      EFProves π φ ∧
      ∀ π' : List (Formula ℕ), IsProof π' → π'.getLast? = some φ →
        (proofSize π + 1) ^ d < proofSize π' := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

end FregeVsExtendedFrege
