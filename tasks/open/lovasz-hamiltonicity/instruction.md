# Task: Lovász's Hamiltonicity Conjecture — Prove It or Refute It (Lean 4, machine-verified)

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean` contains
a definition layer and two theorems — the conjecture (`conj`) and its
negation (`refuted`) — each "proved" by `sorry` inside a marked slot.
**Prove either one.**

The conjecture is **Lovász's Hamiltonicity conjecture** (László Lovász,
research problem posed in 1969; published in *Combinatorial Structures and
Their Applications*, Proc. Calgary Internat. Conf. 1969, Gordon and Breach
1970).

A graph is **vertex-transitive** when every
vertex looks the same: for any two vertices `u`, `v` some automorphism of the
graph maps `u` to `v`. A **Hamiltonian path** is a walk that visits every
vertex exactly once. The conjecture states:

    Every finite connected vertex-transitive graph has a Hamiltonian path.

The conjecture asks for a *path*, not a cycle: the Petersen graph (10
vertices) is vertex-transitive and has no Hamiltonian cycle — only five
connected vertex-transitive graphs without a Hamiltonian cycle are known
(K₂, the Petersen graph, the Coxeter graph, and the truncations of the
latter two) — but it does have a Hamiltonian path, and so do the other four.
The conjecture is **open**: no counterexample is known, and even the
quantitative weakening is far from settled — the best lower bound on the
length of a longest *cycle* in a connected vertex-transitive graph on `n`
vertices was Θ(√n) (Babai 1979) for over forty years, improved by DeVos
(2023) and then by Groenland–Longbrake–Steiner–Turcotte–Yepremyan (2025) to
`n^(13/21)`. A proof or a counterexample would both be publishable results.

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).** Vertex-transitivity
  `G.IsVertexTransitive` (via mathlib's graph isomorphisms `G ≃g G`); the
  existence of a Hamiltonian path `G.HasHamiltonianPath` (via mathlib's
  `Walk.IsHamiltonian`: a walk whose support contains every vertex exactly
  once); a helper for one-vertex graphs
  `G.hasHamiltonianPath_of_subsingleton`; and the **Petersen graph**
  `petersenGraph` on `Fin 10` (explicit 15-edge list: outer pentagon, inner
  pentagram, spokes) together with an explicit Hamiltonian path
  `petersenHamPath` through it (the walk `0-1-2-3-4-9-6-8-5-7`). The
  definitions live in the `SimpleGraph` namespace, so write
  `G.IsVertexTransitive` etc. as dot notation.
- **Slot zone.** Two theorem slots, bodies blank, in this order:

  1. `conj` — the conjecture itself: every finite connected vertex-transitive
     graph has a Hamiltonian path.
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
