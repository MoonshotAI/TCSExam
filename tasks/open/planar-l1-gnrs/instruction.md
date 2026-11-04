# Task: The GNRS Conjecture — Prove It or Refute It (Lean 4, machine-verified)

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean` contains
a definition layer and two theorems — the conjecture (`conj`) and its
negation (`refuted`) — each "proved" by `sorry` inside a marked slot.
**Prove either one.**

The conjecture is the **GNRS conjecture** (Anupam Gupta, Ilan Newman, Yuri
Rabinovich, Alistair Sinclair; FOCS 1999, journal version *Cuts, trees and
ℓ₁-embeddings of graphs*, Combinatorica 24(2): 233–269, 2004).

Every connected graph `G` carries a
metric: the shortest-path distance `d(u,v)`, the number of edges on a
shortest `u`–`v` path. A map `φ` from the vertices of `G` into an `ℓ₁`
space (real vectors, with the distance `‖x − y‖₁ = Σᵢ |xᵢ − yᵢ|`) has
**distortion** at most `C` if no pair of vertices is contracted and no
pair is expanded by a factor more than `C`:

    d(u,v) ≤ ‖φ(u) − φ(v)‖₁ ≤ C · d(u,v)   for all vertices u, v.

Every finite metric space embeds into `ℓ₁` with *some* finite distortion,
and arbitrary `n`-vertex graphs can force distortion `Ω(log n)`
(bounded-degree expanders). The GNRS conjecture claims that **planar
graphs are dramatically better**: there is a universal constant `C` such
that the shortest-path metric of *every* planar graph embeds into `ℓ₁`
with distortion at most `C`. By the duality between `ℓ₁` embeddings and
multi-commodity flows (Linial–London–Rabinovich 1995), this is
equivalent to a constant flow/cut gap on planar networks. The authors
stated the conjecture more generally for every proper minor-closed
family of graphs (a family closed under deleting and contracting edges,
other than the family of all graphs); planar graphs are the flagship
case.

The conjecture is **open**. The best known upper bound for `n`-vertex
planar graphs is `O(√log n)` (Rao 1999), and the universal constant, if
it exists, cannot be smaller than 16/7 (Kalantarzadeh–Kumar 2025, improving
the earlier bound of 2 by Lee–Raghavendra 2007/2010). It has
been proved for several restricted families: trees embed isometrically,
series–parallel graphs and graphs of bounded circuit rank (GNRS 2004),
`k`-outerplanar graphs (Chekuri–Gupta–Newman–Rabinovich–Sinclair 2006),
graphs of bounded pathwidth (Lee–Sidiropoulos 2013), and 2-clique-sums
of bounded graphs (Lee–Poore 2013). A proof or a counterexample would
both be landmark results.

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).**
  - `G.WalkSeq u v n` — "there is a walk of length `n` from `u` to `v` in
    `G`", given by a vertex sequence; a decidable predicate on finite
    graphs.
  - `G.spDist u v` — the shortest-path distance as a *computable*
    natural number (the minimum walk length below `card V`, and `0` when
    no walk exists). The fully proved theorem `spDist_eq_dist` shows it
    coincides with mathlib's `SimpleGraph.dist` on reachable pairs, so
    on connected graphs it is exactly the literature's shortest-path
    metric. API lemmas (`spDist_le_of_walkSeq`, `walkSeq_of_spDist`,
    `spDist_self`, `spDist_symm`) are fully proved.
  - `l1Dist x y = ∑ i, |x i − y i|` — the `ℓ₁` distance on `Fin k → ℝ`.
  - `G.EmbedsIntoL1 C` — "the shortest-path metric of `G` embeds into
    `ℓ₁` with distortion at most `C`": there exist a dimension `k` and a
    map `φ : V → Fin k → ℝ` with `(G.spDist u v : ℝ) ≤ l1Dist (φ u) (φ v)`
    and `l1Dist (φ u) (φ v) ≤ C * G.spDist u v` for all `u v`.
  - `G.HasMinor H` — graph minors via branch sets (disjoint nonempty
    connected sets, one per vertex of `H`, linked by edges following
    `H`); `G.IsPlanar` — no `K₅` minor and no `K₃,₃` minor. By Wagner's
    theorem (1937) this is equivalent to the topological definition of
    planarity; the equivalence is a cited definitional choice (see
    `tests/reference/concept-ledger.md` of the packaged task) and you do
    not need it for any proof.
  - Concrete graphs: `starGraph n` (the star with
    `n` leaves), `cycle4` (the 4-cycle), `k23` (`K_{2,3}`).
- **Slot zone.** Two theorem slots, bodies blank, in this order:

  1. `conj` — the conjecture itself: `∃ C : ℝ, ∀ (G : SimpleGraph V)`,
     with `V` a fintype, `G.Connected → G.IsPlanar → G.EmbedsIntoL1 C` —
     every finite connected planar graph satisfies `G.EmbedsIntoL1 C`.
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
