# Task: Online Bipartite Matching under Random Arrival Order — Prove It or Refute It (Lean 4, machine-verified)

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean` contains
a definition layer and two theorems — the conjecture (`conj`) and its
negation (`refuted`) — each "proved" by `sorry` inside a marked slot.
**Prove either one.**

The conjecture concerns the **competitive ratio of online bipartite
matching under random arrival order** (online bipartite matching:
Karp–Vazirani–Vazirani, STOC 1990; the random arrival order model:
Goel–Mehta, SODA 2008).

A bipartite graph has `n` *offline* vertices
(known in advance) and `n` *online* vertices. The online vertices arrive one
at a time; when a vertex arrives, its incident edges are revealed, and an
online algorithm must immediately decide either to match it to one of its
still-unmatched offline neighbors or to leave it unmatched forever. Decisions
cannot be revoked. In the **random order model** the arrival sequence is a
uniformly random permutation of the `n` online vertices. An algorithm may
also use its own randomness: it is modeled as a deterministic decision rule
fed by a *random tape* of `t` uniformly random bits. The value of an
algorithm on a graph `G` is the expected size `E[|M|]` of the matching it
produces (the expectation averages over both the arrival permutation and the
tape), and its performance guarantee is this expectation compared against
`ν(G)`, the size of a maximum matching.

The **optimal competitive ratio** of this model — the best worst-case ratio
`E[|M|] / ν(G)` any online algorithm can guarantee, asymptotically as
`n → ∞` — is **open**. It is known to be at least `0.696` (Mahdian–Yan, STOC
2011, via the Ranking algorithm) and at most `0.823` (Manshadi–Oveis
Gharan–Saberi, Math. Oper. Res. 2012), recently improved to
`1 − e/e^e ≈ 0.82062` (Chierichetti–Giacchini–Panconesi–Vattani, ICALP
2025). Even the exact competitive ratio of the Ranking algorithm in this
model is unknown.

This task fixes the threshold `3/4`, which lies strictly inside the known
interval, and asks for either direction in asymptotic form:

- `conj` — from some size threshold `N` on, at **every** size `n ≥ N` some
  randomized online algorithm guarantees `E[|M|] ≥ (3/4)·ν(G)` on every
  graph `G`. Proving it improves the best known lower bound from `0.696` to
  `0.75`.
- `refuted` — for **every** size threshold `N`, at **some** size `n ≥ N` no
  randomized online algorithm guarantees that. This is the literature's
  upper-bound shape: every algorithm, randomized ones included, is beaten at
  infinitely many sizes. Proving it improves the best known upper bound to
  `0.75`.

Either proof would be a publishable result.

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).** Bipartite graphs on `n + n` vertices
  as edge finsets (`BipGraph n := Finset (Fin n × Fin n)`, edge `(u, v)` =
  offline `u` joined to online `v`); offline neighborhoods (`nbrs G v`);
  matchings (`IsMatching`) and the maximum matching number
  (`matchingNumber G`, the `Finset.max'` over all matchings); randomized
  online algorithms (`OnlineAlg n t`: a deterministic decision rule fed by a
  random tape of `t` uniform bits — at step `k` the algorithm sees its tape,
  the history of arrivals and their neighborhoods, the set of
  already-matched offline vertices, the arriving vertex and its
  neighborhood, and answers `some u` or `none`; deterministic algorithms
  are the case `t = 0`); one execution step (`step`), the state after `k`
  arrivals (`execUpTo`), the final matching (`exec`), its size (`execCard`),
  and the expected size over all `n!` arrival permutations and all `2^t`
  tapes (`expectedCard`, a rational number with denominator `n! * 2^t`); the
  greedy algorithm (`greedyAlg`, which ignores its tape).
  API lemmas (the execution always produces a matching of the graph, its
  size is at most `matchingNumber G`, the expectation is too, a zero-length
  tape collapses the double average to the single permutation average,
  states grow monotonically) are fully proved. All notions are computable,
  so claims about small concrete instances are provable by `decide`.
- **Slot zone.** Two theorem slots, bodies blank, in this order:

  1. `conj` — the conjecture itself, the lower-bound direction at
     threshold `3/4`: `∃ N : ℕ, ∀ n ≥ N, ∃ t : ℕ, ∃ A : OnlineAlg n t,
     ∀ G : BipGraph n, 3 * (matchingNumber G : ℚ) ≤ 4 * expectedCard A G`.
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
