# Task: Frege versus Extended Frege — Prove It or Refute It (Lean 4, machine-verified)

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean` contains
a definition layer and two theorems — the conjecture (`conj`) and its
negation (`refuted`) — each "proved" by `sorry` inside a marked slot.
**Prove either one.**

The conjecture is the **Frege versus Extended Frege separation conjecture**
— that Frege cannot polynomially simulate Extended Frege (the framework and
the question originate with Cook–Reckhow, *The relative efficiency of
propositional proof systems*, J. Symbolic Logic 44(1):36–50, 1979; as the
prevailing conjecture see Krajíček, *Proof Complexity*, Cambridge University
Press, 2019).

A *Frege system* is the usual
axiom-and-rule calculus of propositional logic: finitely many axiom schemes
and modus ponens, where a proof is a finite sequence of formulas, each line
an axiom instance or obtained from two earlier lines by modus ponens. An
*Extended Frege* (EF) system adds the **extension rule**: at any point one
may introduce a fresh atom `p` as an abbreviation for an already-built
formula `D`, by deriving the biconditional `p ↔ D` (with `p` new: it occurs
neither in `D` nor in any earlier line, and — the *conclusion condition* —
not in the formula being proved). Extension variables let EF proofs operate
on circuits rather than formulas, so EF proofs can be much shorter. The
question is whether **Frege can p-simulate Extended Frege**: whether every
EF proof can be converted into a Frege proof of the same tautology with at
most polynomial blow-up in symbol size. The prevailing conjecture is that
it **cannot**. A separation would be
the first among proof systems at the level of Frege and above — separations
between weaker systems are known, e.g. resolution versus cutting planes and
bounded-depth Frege versus Frege — and would almost certainly require new
proof-length lower-bound techniques. After nearly fifty years the question
is open in both directions.

By Reckhow's 1979 theorem all Frege systems are p-equivalent (and their EF
extensions are p-equivalent as well), so the question does not depend on
which concrete Frege system is used. The development fixes one standard
system: ten axiom schemes over the connectives `{⊥, ∧, ∨, →}` with modus
ponens as the only rule.

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).** In namespace `Frege`: propositional
  formulas `Formula α` over an atom type (constructors `atom`, `falsum`,
  `and`, `or`, `imp`; negation `¬φ` is read as `φ → ⊥`); formula size in
  symbols (`Formula.size`); the atoms of a formula (`Formula.vars`);
  substitution (`Formula.subst`); Boolean evaluation (`Formula.eval`) and
  tautologies (`Tautology`); the ten axiom schemes (`IsAxiom`); Frege
  proofs as sequences of formulas (`IsProof`), provability (`Provable`),
  and proof size in symbols (`proofSize`). The Extended Frege layer:
  `IsEFProof` (Frege steps plus extension steps, with the freshness side
  conditions on `Formula.vars`), `ExtStep` (line `k` of `π` is an extension
  step introducing `p`), `EFProves π φ` (an EF proof of `φ`, with the
  conclusion condition), and `EFProvable φ`. The proved API: every axiom
  is a tautology (`IsAxiom.tautology`), modus ponens preserves tautologies
  (`Tautology.mp`), and evaluation only depends on the atoms occurring in
  the formula (`Formula.eval_agree`).
- **Slot zone.** Two theorem slots, bodies blank, in this order, in
  namespace `FregeVsExtendedFrege` (with `open Frege`):

  1. `conj` — the separation conjecture: for every degree `d` there is an
     Extended Frege proof `π` of some formula `φ` (over the atom type `ℕ`)
     such that every Frege proof of `φ` has `proofSize` greater than
     `(proofSize π + 1) ^ d`.
  2. `refuted` — its negation.

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
