# Task: The MDS Main Conjecture over Non-Prime Finite Fields — Prove It or Refute It (Lean 4, machine-verified)

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean` contains
a definition layer and two theorems — the conjecture (`conj`) and its
negation (`refuted`) — each "proved" by `sorry` inside a marked slot.
**Prove either one.**

The conjecture is the **MDS main conjecture over non-prime finite fields**
(Segre's MDS conjecture for linear codes, 1955; the prime-order case was
proved by Simeon Ball, *Journal of the European Mathematical Society*
14(3):733–748, 2012; for orders `q = p^h` with `h ≥ 2` the conjecture is
open).

A *linear code* of length `n` and dimension `k` over the
finite field `F_q` is a `k`-dimensional subspace of the coordinate space
`F_q^n`; its *minimum distance* `d` is the smallest number of nonzero
coordinates of a nonzero codeword. The Singleton bound says `d ≤ n − k +
1`, and a code attaining it is called *MDS* (maximum distance separable).
How long can an MDS code be? The trivial families — repetition-type codes
(`k ≤ 1`, `d = n`) and their duals (`k ≥ n − 1`, `d = 2`) — exist at every
length, so the question is only about *nontrivial* codes (`2 ≤ k ≤ n −
2`). Reed–Solomon codes and their extensions give nontrivial MDS codes of
length up to `q + 1` for every `q`, and when `q` is even, hyperovals of
the projective plane give length `q + 2` at `k = 3` (and dually at
`k = q − 1`). The MDS main conjecture asserts that this is the whole
story:

> Every nontrivial `k`-dimensional linear MDS code of length `n` over
> `F_q` satisfies `n ≤ q + 1`, unless `q` is even and `k = 3` or
> `k = q − 1`, in which case `n ≤ q + 2`.

Ball's 2012 theorem proves this for **prime** `q`. For non-prime orders
`q = p^h` (`h ≥ 2`) the conjecture is **open**: Ball–De Beule (*Designs,
Codes and Cryptography* 65:5–14, 2012) and follow-up work prove it only
for small `k` (roughly `k` up to a constant times `√q`-scale), and the
general case remains unresolved. A proof or a counterexample would both be
landmark results in coding theory and finite geometry. This task is
quantified over non-prime orders only: the statement is required to hold
exactly for fields whose cardinality is not prime, and it says nothing
about the (settled) prime case either way.

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).** The structure `LinearCode F n` (a
  subspace of `Fin n → F`); its dimension `LinearCode.dim`
  (`Module.finrank`); the minimum distance `LinearCode.minDist` (the
  minimum Hamming weight of a nonzero codeword, via mathlib's
  `hammingNorm`; for linear codes this equals the minimum distance between
  distinct codewords, by linearity); the predicate `LinearCode.IsMDS`
  (`d = n − k + 1`, equality in the Singleton bound); and
  `LinearCode.NonTrivial` (`2 ≤ k ≤ n − 2`). As a concrete anchor, the
  zone also defines `repetitionCode F n` (the span of the all-ones
  vector) and proves it is MDS with `d = n` at dimension `1` for every
  length — the trivial family that forces the nontriviality restriction.
- **Slot zone.** Two theorem slots, bodies blank, in this order:

  1. `conj` — the conjecture itself: for every field `F` with
     `¬ Nat.Prime (Fintype.card F)` (finite fields of non-prime order
     `q = p^h`, `h ≥ 2` — cardinality of a finite field is always a prime
     power, and `p^h` is prime iff `h = 1`), every `C : LinearCode F n`
     with `C.NonTrivial` and `C.IsMDS` satisfies `n ≤ Fintype.card F + 1`,
     or else `Even (Fintype.card F)` with `C.dim = 3` or
     `C.dim = Fintype.card F - 1` and `n ≤ Fintype.card F + 2`.
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
