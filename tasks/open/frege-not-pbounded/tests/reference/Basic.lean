/-
Statement layer for the conjecture that Frege systems are not polynomially
bounded (Cook–Reckhow programme, *The relative efficiency of propositional
proof systems*, J. Symbolic Logic 44(1):36–50, 1979; as a concrete open
conjecture see Krajíček, *Proof Complexity*, Cambridge University Press,
2019):

  for every degree k there is a tautology φ whose shortest Frege proof has
  more than (|φ| + 1)^k symbols — the direct negation of Krajíček's
  definition of a polynomially bounded proof system.

By the Cook–Reckhow theorem, a polynomially bounded propositional proof
system exists iff NP = coNP; hence NP ≠ coNP implies that Frege systems are
not polynomially bounded (the conjecture is a necessary condition for
NP ≠ coNP), while a Frege lower bound alone would not yield NP ≠ coNP
(a stronger system, e.g. Extended Frege, could still be polynomially
bounded).

This file is the task's definition zone plus slot zone:
- The definition zone (namespace `Frege`) defines propositional formulas
  over an atom type (atoms, `falsum`, `∧`, `∨`, `→`; negation `¬φ` is the
  abbreviation `φ → ⊥`), formula size in symbols, substitution, Boolean
  evaluation and tautologies; a fixed Frege system given by ten axiom
  schemes with modus ponens as the only inference rule; proofs as sequences
  of formulas (`IsProof`), provability (`Provable`), and proof size in
  symbols (`proofSize`). It also proves the soundness API: every axiom is a
  tautology and modus ponens preserves tautologies.
- The slot zone states the conjecture (`conj`) and its negation (`refuted`).
  Both proof bodies are left blank.

Fidelity notes (see `tests/reference/concept-ledger.md` of the packaged task):
1. A single concrete Frege system is fixed (ten axiom schemes over
   {⊥, ∧, ∨, →} plus modus ponens — a standard complete Hilbert-style
   axiomatization of classical propositional logic). By Reckhow's 1979
   theorem all Frege systems are p-equivalent, so "Frege systems are not
   polynomially bounded" is independent of the chosen system; fixing one
   system is standard textbook practice.
2. Proof length is measured in symbols (`proofSize`), the standard
   convention in proof complexity.
3. "Polynomially bounded" is expressed by the explicit monomials
   `(φ.size + 1) ^ k` for `k : ℕ`: every polynomial p is eventually
   dominated by some `(m+1)^k`, and the finitely many small m are absorbed
   by raising k further, so "some `(m+1)^k` bounds the shortest proof of
   every tautology of size m" coincides with the textbook definition; the
   negation then quantifies over tautologies directly, with no index
   family and no auxiliary size bound.
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

/-- Boolean evaluation under the assignment `v : α → Bool`; the implication
`φ → ψ` evaluates as `¬φ ∨ ψ`. -/
def eval (v : α → Bool) : Formula α → Bool
  | atom a => v a
  | falsum => false
  | and φ ψ => eval v φ && eval v ψ
  | or φ ψ => eval v φ || eval v ψ
  | imp φ ψ => !eval v φ || eval v ψ

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

/-! ### Proofs and proof size -/

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

end Frege

namespace FregeNotPbounded

open Frege

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

/-! ## Slot zone: the conjecture and its negation -/

-- @[slot main]
/-- **The conjecture** (Cook–Reckhow programme 1979; Krajíček 2019): Frege
systems are not polynomially bounded — for every degree `k` there is a
tautology `φ` all of whose Frege proofs have symbol size greater than
`(φ.size + 1) ^ k`. -/
theorem conj :
    ∀ k : ℕ, ∃ φ : Formula ℕ, Tautology φ ∧
      ∀ π : List (Formula ℕ), IsProof π → π.getLast? = some φ →
        (φ.size + 1) ^ k < proofSize π := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

-- @[slot main]
/-- The negation of the conjecture: Frege systems are polynomially bounded —
some degree `k` bounds the shortest proof size of every tautology. -/
theorem refuted :
    ¬∀ k : ℕ, ∃ φ : Formula ℕ, Tautology φ ∧
      ∀ π : List (Formula ℕ), IsProof π → π.getLast? = some φ →
        (φ.size + 1) ^ k < proofSize π := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

end FregeNotPbounded
