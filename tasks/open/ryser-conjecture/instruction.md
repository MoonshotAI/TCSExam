# Task: Ryser's Conjecture — Prove It or Refute It (Lean 4, machine-verified)

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean` contains
a definition layer and two theorems — the conjecture (`conj`) and its
negation (`refuted`) — each "proved" by `sorry` inside a marked slot.
**Prove either one.**

The conjecture is **Ryser's conjecture** (attributed to Herbert Ryser,
c. 1970; standard reference: DeBiasio–Kamel–McCourt–Sheats,
*Generalizations and strengthenings of Ryser's conjecture*, Electronic
Journal of Combinatorics 2021).

A hypergraph `H` is *`r`-partite
`r`-uniform* if its vertex set is split into `r` parts and every edge
contains exactly one vertex from each part (for `r = 2` these are exactly the
bipartite graphs). Two numbers measure how the edges of `H` can be packed and
covered:

- `ν(H)`, the **matching number**: the maximum number of pairwise *disjoint*
  edges of `H` (no two share a vertex);
- `τ(H)`, the **vertex cover number**: the minimum size of a set of vertices
  that meets every edge of `H`.

Always `ν(H) ≤ τ(H) ≤ r·ν(H)`: one vertex can cover several packed edges, and
the `r·ν` vertices of a maximum matching meet every edge. Ryser's conjecture
claims the tight linear bound with constant `r−1`:

    τ(H) ≤ (r−1)·ν(H)   for every r-partite r-uniform hypergraph H with r ≥ 2.

For `r = 2` this is **Kőnig's theorem** (`τ = ν` on bipartite graphs). The
`r = 3` case was proved by Aharoni (2001, by topological methods); the
conjecture is **open for all r ≥ 4** (DeBiasio–Girão–Haxell–Stein 2024,
arXiv:2409.18250). The constant `r−1` cannot be lowered: the *truncated
projective plane* of order `r−1` (when `r−1` is a prime power) is
intersecting (`ν = 1`) with `τ = r−1`. A proof or a counterexample would both
be publishable results.

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).** `r`-partite `r`-uniform hypergraphs as
  finsets of transversals (`RPartiteHypergraph r V`, the parts being `r`
  disjoint copies of one type `V`; an edge is a function `e : Fin r → V`
  picking its vertex `e i` in part `i`); vertex covers (`H.IsCover`) and the
  cover number `H.coverNumber` (τ, the `Finset.min'` over all covers);
  matchings (`H.IsMatching`, pairwise disjointness = differing in every part)
  and the matching number `H.matchingNumber` (ν, the `Finset.max'` over all
  matchings); the bound `H.RyserBound : Prop := τ(H) ≤ (r−1)·ν(H)`. The
  definitions live in the `RPartiteHypergraph` namespace, so write
  `H.coverNumber` etc. as dot notation. API lemmas (cover/matching bounds,
  attainment of both extrema) are fully proved. Concrete instances:
  `konigWitness` (a 2-partite witness of Kőnig's theorem), `paschConfig`
  (the Pasch configuration, the truncated Fano plane), and `truncatedPG3`
  (the truncated projective plane of order 3). Both numbers are computable,
  so claims about the small concrete instances are provable by `decide`.
- **Slot zone.** Two theorem slots, bodies blank, in this order:

  1. `conj` — the conjecture itself:
     `∀ (r : ℕ) [NeZero r] (_ : 2 ≤ r) (V : Type*) [Fintype V]
     [DecidableEq V] (H : RPartiteHypergraph r V), H.RyserBound` — for all
     `r ≥ 2`, all `V`, all `H : RPartiteHypergraph r V`, `H.RyserBound`.
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
