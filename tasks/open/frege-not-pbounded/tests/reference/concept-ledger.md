# Statement and sources: Frege Systems Are Not Polynomially Bounded

This note describes the current mathematical statement and its literature sources. It is for readers comparing the task with the Lean formalization.

The conjecture is that **Frege systems are not polynomially bounded**
(Cook–Reckhow programme, *The relative efficiency of propositional proof
systems*, J. Symbolic Logic 44(1):36–50, 1979; as a concrete open
conjecture see Krajíček, *Proof Complexity*, Cambridge University Press,
2019).

A *Frege system* is the usual
axiom-and-rule calculus of propositional logic: finitely many axiom schemes
and modus ponens, where a proof is a finite sequence of formulas, each line
an axiom instance or obtained from two earlier lines by modus ponens. The
*size* of a proof is the total number of symbols in it. A proof system is
*polynomially bounded* if every tautology has a proof whose size is
polynomial in the size of the tautology. The conjecture claims that Frege
systems are **not** polynomially bounded: for every degree `k` there is a
tautology whose shortest Frege proof has more than `(size + 1) ^ k`
symbols. It is a necessary condition for NP ≠ coNP — by the Cook–Reckhow
theorem, *some* propositional proof system is polynomially bounded iff
NP = coNP — but a Frege lower bound alone would not separate NP from coNP
(a stronger system, e.g. Extended Frege, could still be polynomially
bounded). After fifty years the conjecture is open; the best known lower
bounds on Frege proof size are quadratic.

By Reckhow's 1979 theorem all Frege systems are p-equivalent, so the
conjecture does not depend on which concrete Frege system is used. The
development fixes one standard system: ten axiom schemes over the
connectives `{⊥, ∧, ∨, →}` with modus ponens as the only rule.

The exact definition layer and quantified statements are in `environment/app/Task/Basic.lean`, with the scoring copy in `tests/reference/Basic.lean`. The `conj` and `refuted` statements are exact negations; proving either earns full credit. Finite illustrative checks are documented in `small-examples.md`.
