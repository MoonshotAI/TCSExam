# Task: Frege Systems Are Not Polynomially Bounded — Prove It or Refute It (Lean 4, machine-verified)

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean` contains
a definition layer and two theorems — the conjecture (`conj`) and its
negation (`refuted`) — each "proved" by `sorry` inside a marked slot.
**Prove either one.**

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

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).** In namespace `Frege`: propositional
  formulas `Formula α` over an atom type (constructors `atom`, `falsum`,
  `and`, `or`, `imp`; negation `¬φ` is read as `φ → ⊥`); formula size in
  symbols (`Formula.size`); substitution (`Formula.subst`); Boolean
  evaluation (`Formula.eval`) and tautologies (`Tautology`); the ten axiom
  schemes (`IsAxiom`); proofs as sequences of formulas (`IsProof`, with the
  modus-ponens side condition on earlier lines); provability (`Provable`,
  the proof's last line); and proof size in symbols (`proofSize`). The
  soundness API is fully proved: every axiom is a tautology
  (`IsAxiom.tautology`) and modus ponens preserves tautologies
  (`Tautology.mp`).
- **Slot zone.** Two theorem slots, bodies blank, in this order, in
  namespace `FregeNotPbounded` (with `open Frege`):

  1. `conj` — the conjecture itself: for every `k : ℕ` there is a
     tautology `φ : Formula ℕ` all of whose Frege proofs `π` satisfy
     `proofSize π > (φ.size + 1) ^ k`. This is the direct negation of
     Krajíček's definition of a polynomially bounded proof system, so
     proving it establishes that Frege systems are not polynomially
     bounded — the conjectured direction.
  2. `refuted` — its literal negation: classically equivalent to "there
     is a degree `k` such that every tautology has a Frege proof of size
     at most `(φ.size + 1) ^ k`", i.e. proving it establishes that Frege
     systems are polynomially bounded.

## Rules

- For verifier safety, executable commands `#eval`, `#exec`, `#exit`, and
  `#compile` are not allowed in submitted Lean files, including harmless
  diagnostics. Remove these commands before submission; the verifier rejects
  them before compiling the proof.
- Do not modify anything above the line `-- END OF FIXED PART`, the
  theorem statements, or the `-- CHECKPOINT ...` marker lines, and keep
  the two slots in their original order. The verifier compares the fixed
  part textually against a reference copy; any change scores 0.
- You may add your own auxiliary definitions and lemmas below the
  `-- END OF FIXED PART` line, outside the checkpoint slots, or in new
  files under `/app/Task/`.
- No new `axiom` declarations and no `native_decide`; the verifier
  rejects these lexically. Forbidden tokens anywhere in the file
  (comments are stripped before the scan): `axiom`, `sorryAx`,
  `native_decide`, `admitGoal`, `byAsSorry`, `skipKernelTC`,
  `implemented_by`. No `notation` / `macro` / `syntax` / `elab` /
  `macro_rules` / `initialize` declarations in the writable zone either;
  they are rejected as semantic-layer rewriting.
- `sorry`/`admit` left in a slot scores 0 for that slot. A `sorry` in
  your own auxiliary lemmas is not scanned for, but if a checked proof
  depends on it, the `#print axioms` check fails (`sorryAx` is never
  allowed) and the slot scores 0. A proof that discharges a slot from a
  helper-layer `False` is flagged as ex-falso and scores 0.

## How to work

You have a 12-hour budget and are expected to use it. Reaching "this looks
unprovable" is the beginning of the work, not the end of it. Do not submit
early with only a conclusion.

Work in this order:
1. **Fidelity check.** Verify the formalized statement matches your
   understanding of the literature (quantifiers, constants, degenerate
   cases). Look for exploitable gaps first — if the statement is trivially
   true/false as written, that is itself a finding worth reporting.
2. **Keep pushing approaches.** For each idea, actually push it forward in
   Lean: write lemmas, try compiling, record exactly where it breaks.
   After each failed approach, write down: what you tried, where it got
   stuck, and what mathematical tool is missing. Then look for the next
   angle. Keep going as long as you can generate distinct ideas — do not
   stop at a fixed count. Move to the research-note phase only when you
   are genuinely out of new angles or the budget is nearly exhausted.
3. **Side products that are always worth doing.** Auxiliary lemmas around
   the definition layer, formalizing known special cases from the
   literature, searching for counterexamples on small instances (kernel
   `decide` where feasible), and barrier analysis (why do known methods
   fail here?).
4. **Research note and artifacts before you finish.** Save your research
   note to `/logs/artifacts/` as a Markdown file: the approaches you
   tried and why each failed, what you verified along the way, and what
   would be needed to go further. Copy all exploration products to
   `/logs/artifacts/` as well, wherever you kept them during the work:
   Lean files with auxiliary lemmas and partial developments (for
   example `/app/scratch/`, an exploration section of `Task/Basic.lean`,
   or standalone files), search and experiment scripts, and computation
   logs. These artifacts are part of the deliverable. An empty
   submission (both slots left as `sorry` and no documented
   exploration) counts as unfinished.

You have **internet access** in this environment: use it. Look up the
current literature frontier on your problem (arXiv, Wikipedia, dblp,
Semantic Scholar), check whether known results or counterexamples exist
that bear on your statement, and cite what you actually consulted in your
research note. Do not trust your training memory for the state of the art —
verify it online.

The floor rules never change: `sorry` scores 0, planted axioms score 0,
ex-falso tricks score 0 and get flagged. Never fabricate a proof.

## Scoring

- Each slot is graded in isolation: the other slot is removed on the
  grader side, never injected as an axiom, so a proof of one slot never
  sees its contradictory twin (and can never exploit it).
- All-or-nothing per slot: the score is **1.0** if the project compiles
  with a slot proved (no `sorry`) using only the standard axioms
  (`propext`, `Classical.choice`, `Quot.sound`), and **0** otherwise.
  There is no partial credit: if neither slot passes, the score is 0.

## Environment

The project builds offline against the mathlib checkout at
`/opt/lean-lib/mathlib4`; use `lake build Task` in `/app` to check.
