# Task: The Paley-Graph Ramsey Conjecture — Prove It or Refute It (Lean 4, machine-verified)

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean` contains
a definition layer and two theorems — the conjecture (`conj`) and its
negation (`refuted`) — each "proved" by `sorry` inside a marked slot.
**Prove either one.**

The conjecture is the **Paley-graph Ramsey conjecture in its
polylogarithmic form**: clique number and independence number of the Paley
graph on `q` vertices are both `(log q)^{O(1)}`.

Erdős (1947) proved by the probabilistic method that graphs
with clique number and independence number at most `2·log₂ N` exist; the
open problem is an *explicit* (polynomial-time constructible) family, with
the current frontier `K = (log N)^{O(1)}` (Xin Li, FOCS 2023). The Paley
graph family is the canonical candidate: for a prime `q ≡ 1 (mod 4)` the
vertices are the elements of the field `ZMod q`, and two distinct vertices
are adjacent iff their difference is a quadratic residue. Adjacency is a
residue test, so the graphs are trivially explicit; the conjecture is
exactly the statement that this family achieves a polylogarithmic Ramsey
bound:

> There is a universal exponent `k` such that for every prime
> `q ≡ 1 (mod 4)`, the Paley graph on `q` vertices has neither a clique nor
> an independent set of size `(⌊log₂ q⌋ + 1)^k + 1`.

The stronger `O(log q)` bound is known to be **false** for the Paley
family: Graham & Ringrose (1990) proved that for infinitely many primes
`p ≡ 1 (mod 4)` the least quadratic non-residue `n(p)` satisfies
`n(p) ≥ c·log p·log log log p`, and the set `{0, …, n(p)−1}` is then a
clique in the Paley graph `P_p`. The genuinely open question is the
polylogarithmic upper bound: the best known unconditional upper bound is
`~√q` (Hanson–Petridis 2021; Yip 2020, arXiv:2004.01175), while the best
known lower bounds (Graham–Ringrose 1990, `log p·log log log p`; Montgomery
1971 under GRH, `log p·log log p`) fall short of any `(log p)^{1+ε}` — so
both proving and refuting the conjecture would be new.

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).** The Paley graph
  `paleyGraph q hqp hq4 : SimpleGraph (ZMod q)` (for `q` prime with
  `q % 4 = 1`: two distinct vertices are adjacent iff their difference is a
  square; the `q ≡ 1 (mod 4)` condition makes `-1` a square, so adjacency
  is symmetric); a Boolean quadratic-residue test `qrBool` with the bridge
  theorem `isSquare_iff_qrBool`, which makes Paley adjacency cheap to
  decide (the instance `paleyAdjDecidable` decides through `qrBool`, not
  through the `IsSquare` existential); the unfolding lemma
  `cliqueFree_def` (`G.CliqueFree n ↔ ∀ t : Finset V, ¬ G.IsNClique n t` —
  `decide` cannot see through `CliqueFree` on its own, so rewrite with this
  or `show` the `∀`-form first); and the conjecture predicate
  `PaleyPolylogRamsey`. The file sets `maxRecDepth 8192` so kernel `decide`
  recurses deep enough for the larger finite checks; for the larger graphs,
  exploiting the graph's symmetry (a clique can be translated so that one
  vertex is 0, and only the neighbors of 0 remain to be checked) keeps the
  finite checks small.
- **Slot zone.** Two theorem slots, bodies blank, in this order:

  1. `conj` — the conjecture itself: `PaleyPolylogRamsey`, i.e. `∃ k : ℕ`
     such that for every prime `q ≡ 1 (mod 4)`, both the Paley graph on `q`
     vertices and its complement are `CliqueFree ((Nat.log 2 q + 1)^k + 1)`
     — no clique and no independent set of that size.
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
