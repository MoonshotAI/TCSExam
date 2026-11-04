# Task: Caccetta–Häggkvist Conjecture — Prove It or Refute It (Lean 4, machine-verified)

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean` contains
a definition layer and two theorems — the conjecture (`conj`) and its
negation (`refuted`) — each "proved" by `sorry` inside a marked slot.
**Prove either one.**

The conjecture is the **Caccetta–Häggkvist conjecture** (1978; full
citation in the Reference section): every loopless digraph on `n` vertices
with minimum out-degree at least `k` contains a directed cycle of length at
most `⌈n / k⌉`.

In a digraph, an arc `v → w` goes one way. The out-degree
of `v` counts its out-arcs. A directed cycle is a closed directed walk with
distinct vertices, and its length is the number of vertices (equivalently
arcs). Undirected intuition says large minimum degree forces short cycles;
the conjecture predicts the exact directed analogue, and it is tight: the
circulant digraph on `n` vertices with arcs `i → i+1, …, i+k` (indices mod
`n`) has minimum out-degree `k` and directed girth exactly `⌈n / k⌉`.

This is an **open problem**. The constant cases `k = 1, …, 5` are theorems
(`k = 1` trivial; `k = 2` by Caccetta–Häggkvist; `k = 3` by Hamidoune;
`k = 4` and `5` by Hoáng–Reed — see B. D. Sullivan's 2006 survey,
arXiv:math/0605646), and already `k = ⌈n/3⌉` (out-degree `n/3` forces a
directed triangle) has been open for nearly fifty years: the best known
constant is `0.3465` (Hladký–Král'–Norin) against the conjectured `1/3`.

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).** A `Digraph` structure (boolean
  adjacency, loopless; 2-cycles allowed), `outDegree`, directed cycles as
  injective sequences `Fin ℓ → V` with consecutive arcs (indices read
  modulo `ℓ`, via `cycSucc`), the predicate `D.HasCycleOfLengthLe m` with a
  `Decidable` instance, and the circulant family `Digraph.circulant n k`.
  A `set_option maxRecDepth` line (kernel enumeration over small vertex
  sets needs it) is part of the fixed zone.
- **Slot zone.** Two theorem slots, bodies blank, in this order:

  1. `conj` — the conjecture itself: `∀ (V : Type) [Fintype V] [Nonempty V]
     (D : Digraph V) (k : ℕ), 1 ≤ k → (∀ v, k ≤ D.outDegree v) →
     D.HasCycleOfLengthLe ((Fintype.card V + k - 1) / k)` (the ceiling
     `⌈n / k⌉` written as natural division, valid for `k ≥ 1`).
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

## Reference

Caccetta, Häggkvist, *On minimal digraphs with given girth*, Proceedings
of the 9th Southeastern Conference on Combinatorics, Graph Theory and
Computing (Congressus Numerantium 21), 1978, pp. 181–187.
