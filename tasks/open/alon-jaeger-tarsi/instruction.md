# Task: Alon–Jaeger–Tarsi Conjecture — Prove It or Refute It (Lean 4, machine-verified)

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean` contains
a definition layer and two theorems — the conjecture (`conj`) and its
negation (`refuted`) — each "proved" by `sorry` inside a marked slot.
**Prove either one.**

The conjecture is the **Alon–Jaeger–Tarsi conjecture** in its remaining,
prime-field form (first proposed by Jaeger in 1981; the non-prime finite
fields settled by Alon–Tarsi, 1989; the prime fields `p > 61`, `p ≠ 79` by
Nagy–Pach, arXiv:2107.03956, 2021).

Fix a finite field `F` and a nonsingular square matrix `A`
over `F`. The conjecture says there is always a vector `x` such that
**every component of `x` and every component of `A·x` is nonzero**. It was
proposed for all finite fields of order at least 4 (the statement is false
over the fields of order 2 and 3 — counterexamples are known). Alon and
Tarsi (1989) proved it for every *non-prime* finite field by the polynomial
method, and Nagy–Pach (arXiv:2107.03956, 2021) proved it for every prime
field `ZMod p` with `p > 61`, `p ≠ 79`. What remains open is exactly the
statement packaged here as `AJTConjecture`: the prime fields `p ≥ 5`, with
the small primes `p ∈ {5, 7, …, 61}` and `p = 79` still unresolved.

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).** `NowhereZero x` (every component of
  `x` is nonzero), `HasAJTVector A` (some nowhere-zero `x` has a
  nowhere-zero image `A *ᵥ x`), `AJTConjecture` (the conjecture statement),
  and two decidability instances (for `NowhereZero` and `HasAJTVector`)
  backing `decide` proofs over small concrete instances.
- **Slot zone.** Two theorem slots, bodies blank, in this order:

  1. `conj` — the conjecture itself: `∀ (p : ℕ) [Fact p.Prime], 5 ≤ p → ∀
     (n : ℕ) (A : Matrix (Fin n) (Fin n) (ZMod p)), A.det ≠ 0 →
     HasAJTVector A` (over a field, `A.det ≠ 0` is exactly nonsingularity).
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
