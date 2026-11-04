# Task: NEXP versus TC⁰ — Prove It or Refute It (Lean 4, machine-verified)

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean` contains
a definition layer and two theorems — the conjecture (`conj`) and its
negation (`refuted`) — each "proved" by `sorry` inside a marked slot.
**Prove either one.**

The conjecture is **NEXP ⊄ TC⁰**: some language in nondeterministic
exponential time cannot be computed by any family of constant-depth,
polynomial-size circuits over unbounded fan-in threshold (majority) gates
(Williams 2011 proved `NEXP ⊄ ACC`; Chen–Tell, STOC 2019, *Bootstrapping
Results for Threshold Circuits "Just Beyond" Known Lower Bounds*, made the
TC⁰ statement the explicit next goal).

A Boolean circuit is a DAG of gates feeding
input bits to output bits. **TC⁰** is the class of languages computed by
circuit families of *constant depth* and *polynomial size* over unbounded
fan-in threshold gates, where a threshold gate `thr k` outputs 1 iff the
number of 1s among its inputs is at least `k` (majority on `n` inputs is
`thr ⌈n/2⌉`; AND is `thr n`; OR is `thr 1`; negations are free, on the
inputs of each gate). TC⁰ is the weakest circuit class with direct
arithmetic power: integer multiplication, integer division and sorting all
have TC⁰ circuit families. Whether **NEXP ⊄ TC⁰** is a front line of
circuit lower bounds: Williams' "algorithmic method" (better algorithms
imply circuit lower bounds) proved `NEXP ⊄ ACC` (Williams 2011), but ACC ⊆
TC⁰ (a `MOD_m` gate is a constant-depth polynomial-size threshold
construction), so the TC⁰ statement is the stronger one and remains
**open** — Chen–Tell (STOC 2019, *Bootstrapping Results for Threshold
Circuits "Just Beyond" Known Lower Bounds*) showed that even mild
improvements of the best-known TC⁰ lower bounds, or of the best
quantified-derandomization algorithms for TC⁰ circuits, would already imply
`NEXP ⊄ TC⁰`. The statement is open in the uniform and the nonuniform
reading alike; this task takes the customary nonuniform reading. A proof or
a disproof would both be landmark results.

mathlib has no time-bounded machine model, so "some language in NEXP"
cannot be quantified directly. The development pins the statement to the
standard NEXP-complete language **SUCCINCT-SAT**: an instance is a circuit
`C` describing an exponentially large CNF formula (clause `c` contains
literal `(v, s)` iff `C` accepts the packed input `(c, v, s)`), asking
whether the described formula is satisfiable. SUCCINCT-SAT is NEXP-complete
(Papadimitriou–Yannakakis 1986, polynomial-time reductions; the strengthening
to AC⁰ reductions is standard folklore) and TC⁰ is closed under AC⁰
reductions, so `SUCCINCT-SAT ∉ TC⁰ ⟺ NEXP ⊄ TC⁰`. The conjecture
slot `conj` says `succinctSatFamily ∉ TC⁰`; the `refuted` slot is its
literal negation (`SUCCINCT-SAT ∈ TC⁰`, which would collapse NEXP into
TC⁰).

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
  TC⁰ basis (`tc0Basis`: threshold gates `thr k`, unbounded fan-in). The
  dense description-circuit encoding of SUCCINCT-SAT: at input length `N`,
  with `n = succSatVars N`, the first `succLen n` bits of the input encode
  a level-`n` *description circuit* over the AND/OR basis — `2n+1` primary
  inputs (`n` clause-index bits, `n` variable bits, 1 sign bit), `n`
  internal gates, one output gate, each gate described by one op bit
  (0 = AND, 1 = OR), `3n+1` wiring bits and `3n+1` negation bits; reads
  beyond `N` are `false` (padding). `descCircuit` decodes the description,
  and `succinctSatFamily N x` decides whether the CNF it describes — `2^n`
  clauses over `2^n` variables, clause `c` containing literal `(v, s)` iff
  the description circuit accepts the packed input `(c, v, s)` — is
  satisfiable. TC⁰ membership (`InTC0`): there exist a depth bound `d` and
  a size exponent `c` such that for every `N ≥ 1` some circuit over
  `tc0Basis` of depth ≤ d and size ≤ N^c computes the family. Also the AND
  and OR characteristic families (`andFamily`, `orFamily`) and a concrete
  two-input XOR circuit `sampleXorCircuit` over the threshold basis.
- **Slot zone.** Two theorem slots, bodies blank, in this order:

  1. `conj` — the conjecture itself: `¬ InTC0 succinctSatFamily`
     (SUCCINCT-SAT has no TC⁰ circuits).
  2. `refuted` — its negation: `InTC0 succinctSatFamily` (SUCCINCT-SAT has
     TC⁰ circuits, which would collapse NEXP into TC⁰).

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
