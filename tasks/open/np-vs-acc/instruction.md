# Task: NP versus ACC — Prove It or Refute It (Lean 4, machine-verified)

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean` contains
a definition layer and two theorems — the conjecture (`conj`) and its
negation (`refuted`) — each "proved" by `sorry` inside a marked slot.
**Prove either one.**

The conjecture is **NP ⊄ ACC**: some language in NP cannot be computed by
any family of constant-depth, polynomial-size circuits over unbounded
fan-in AND/OR/MOD_m gates (Williams 2011 proved `NEXP ⊄ ACC`, improved to
`NQP ⊄ ACC` by Murray–Williams 2018; textbook statement: Arora–Barak,
*Computational Complexity: A Modern Approach*, Chapter 14).

A Boolean circuit is a DAG of gates feeding
input bits to output bits. **ACC** is the class of languages computed by
circuit families of *constant depth* and *polynomial size* over unbounded
fan-in AND, OR and MOD_m gates, where a MOD_m gate outputs 1 iff the number
of 1s among its inputs is a multiple of the fixed modulus `m` (negations are
free, on the inputs of each gate). Whether **NP ⊄ ACC** is one of the front
lines of circuit lower bounds: it became an explicit target with Williams'
"algorithmic method" (better algorithms imply circuit lower bounds), which
proved `NEXP ⊄ ACC` (Williams 2011), later improved to `NQP ⊄ ACC`
(Murray–Williams 2018); pressing the statement down to NP is the recognized
next step and is **open**. The textbook statement is in Arora–Barak,
*Computational Complexity: A Modern Approach*, Chapter 14. A proof or a
disproof would both be landmark results.

mathlib has no polynomial-time predicate, so "some language in NP" cannot be
quantified directly. The development pins the statement to the standard
NP-complete language **SAT**: SAT is NP-complete under AC⁰ reductions and
ACC is closed under AC⁰ reductions, so `SAT ∉ ACC ⟺ NP ⊄ ACC`. The
conjecture slot `conj` says `satFamily ∉ ACC`; the `refuted` slot is its
literal negation (`SAT ∈ ACC`, which would collapse NP into ACC).

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).** Bit strings and Boolean function
  families; gate bases (`CircuitBasis`: operation type + arity constraint +
  evaluation), gates with per-input free negation flags, and circuits
  (`Circuit B N M G`: `N` input wires, `M` output gates, `G` internal
  gates; gate `i` may only read wires `< N + i`, so the DAG is acyclic by
  construction). Evaluation (`Circuit.wireValue`, `Circuit.eval`), depth
  (`Circuit.wireDepth`, `Circuit.depth`) and size (`Circuit.size = G + M`)
  are defined by structural recursion, so concrete circuits compute by
  kernel reduction; one-step API lemmas (`wireValue_lt`, `wireValue_gate`,
  `wireDepth_lt`) are fully proved. The AND/OR basis (`aonBasis`) and the
  ACC basis (`accBasis m`: AND, OR and MOD_m, unbounded fan-in). The dense
  CNF-matrix encoding of SAT: at input length `N`, the first `n·2n` bits
  (with `n = satVars N = ⌊√(N/2)⌋`) encode an `n`-variable, `n`-clause CNF
  formula — bit `(i, 2j)` / `(i, 2j+1)` of the matrix records whether clause
  `i` contains the positive / negative literal of variable `j`; remaining
  bits are padding. `satFamily N x` decides whether the encoded formula is
  satisfiable. ACC membership (`InACC`): there exist a depth bound `d`, a
  size exponent `c` and a modulus `m` such that for every `N ≥ 1` some
  circuit over `accBasis m` of depth ≤ d and size ≤ N^c computes the family.
  Also the MOD₂ characteristic family `mod2Family` and a concrete two-input
  circuit `sampleModCircuit` over the MOD₃ basis.
- **Slot zone.** Two theorem slots, bodies blank, in this order:

  1. `conj` — the conjecture itself: `¬ InACC satFamily` (SAT has no ACC
     circuits).
  2. `refuted` — its negation: `InACC satFamily` (SAT has ACC circuits,
     which would collapse NP into ACC).

## Rules

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
