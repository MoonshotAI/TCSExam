# Task: The Evasiveness Conjecture — Prove It or Refute It (Lean 4, machine-verified)

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean` contains
a definition layer and two theorems — the conjecture (`conj`) and its
negation (`refuted`) — each "proved" by `sorry` inside a marked slot.
**Prove either one.**

The conjecture is the **evasiveness conjecture** (Karp's conjecture, early
1970s; weaker Ω(v²) form due to Aanderaa–Rosenberg 1973; survey: C. A.
Miller, *Evasiveness of Graph Properties and Topological Fixed-Point
Theorems*, Found. Trends Theor. Comput. Sci. 7(4), 2011; arXiv:1306.0110).

Fix a vertex set of size `v`. A *graph
property* is a boolean function on the simple graphs on these vertices that
does not depend on the labeling: isomorphic graphs get the same value. A
property is *monotone* if adding edges can never destroy it (examples:
connectedness, containing a triangle, non-planarity), and *nontrivial* if some
graph has it and some graph does not. To learn whether an input graph has the
property, an algorithm may ask questions of the form "is there an edge between
these two vertices?", adaptively — such an algorithm is a binary *decision
tree*, and its cost is the number of queries asked on the worst input, i.e.
the tree's depth. There are `C(v,2) = v(v−1)/2` candidate edges, so querying
all of them always suffices. The evasiveness conjecture claims that for every
nontrivial monotone graph property this naive bound is exact:

    every decision tree deciding a nontrivial monotone graph property
    on v vertices has depth at least C(v,2).

The conjecture is **open**: neither a proof nor a counterexample is known. It
is proved when `v` is a prime power (Kahn–Saks–Sturtevant 1984, topological
fixed-point methods); the first non-prime-power case is `v = 6`. The best
general deterministic lower bound is `(1/3 − o(1))·v²`
(Scheidweiler–Triesch 2013). A full proof or a counterexample would both be
major results.

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).** Boolean graph properties
  (`GraphProp v := ∀ G : SimpleGraph (Fin v) [DecidableRel G.Adj], Bool`); the
  three hypotheses of the conjecture as separate predicates
  (`IsGraphProperty`: isomorphism invariance; `IsMonotone`: closure under
  adding edges, i.e. the `G ≤ H` subgraph relation; `IsNontrivial`: some graph
  has the property, some graph does not); deterministic decision trees
  (`DTree v`: `leaf b` outputs a bit, `query e t f` asks whether the unordered
  pair `e : Sym2 (Fin v)` is an edge and continues in `t` on yes, `f` on no),
  their `depth`, evaluation `t.eval G` on a concrete graph, and the
  correctness predicate `t.Decides P`. The running example `hasEdgeProp`
  (having at least one edge) is also defined here.
- **Slot zone.** Two theorem slots, bodies blank, in this order:

  1. `conj` — the conjecture itself: for every vertex number `v`, every
     isomorphism-invariant, monotone, nontrivial `P`, every tree deciding `P`
     has depth at least `v.choose 2`.
  2. `refuted` — its negation.

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
