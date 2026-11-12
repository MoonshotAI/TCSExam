# Task: Polynomial Freiman–Ruzsa over the Integers — Prove It or Refute It (Lean 4, machine-verified)

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean` contains
a definition layer and two theorems — the conjecture (`conj`) and its
negation (`refuted`) — each "proved" by `sorry` inside a marked slot.
**Prove either one.**

The conjecture is the **polynomial Freiman–Ruzsa conjecture over the
integers** (Marton's conjecture in ℤ; the strengthening of Freiman's
theorem proposed by Ruzsa in the 1990s; the convex-progression formulation
of Lovett–Regev, *Discrete Analysis* 2017:8, Conjecture 1.2; see also
Manners, arXiv:1709.09738).

For a finite set `A` of integers, the *sumset*
`A + A = {a + b : a, b ∈ A}` measures how much additive structure `A` has:
`|A+A|` is small exactly when `A` is highly structured. Freiman's theorem
says that if `|A+A| ≤ K·|A|`, then `A` is contained in a (low-dimensional)
progression-like object whose size is comparable to `|A|`; the polynomial
Freiman–Ruzsa conjecture asks for the tight, polynomial dependence of every
parameter on the doubling constant `K`:

> There are constants `C₁ C₂` such that every finite nonempty `A ⊆ ℤ` with
> `|A+A| ≤ K·|A|` is covered by at most `K^{O(1)} = (K+1)^{C₂}` translates
> of a **convex body progression** `P` of dimension at most `C₁·log₂(K+1)`
> and size at most `(K+1)^{C₂}·|A|`.

A *convex body progression* is the set of lattice points of a symmetric
convex bounded body in `ℝ^d`, mapped into `ℤ` by a homomorphism `ℤ^d → ℤ`
and then translated — ordinary arithmetic progressions (`d = 1`, the body
an interval) are the simplest examples. The conjecture is **open**. (The
stronger formulation with *generalized arithmetic progressions* in place of
convex body progressions is known to be false — Lovett–Regev 2017 — which
is why the statement uses convex bodies.) A proof or a counterexample would
both be landmark results in additive combinatorics.

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).** The structure `ConvexProgression G`
  (dimension `dim`, a symmetric convex bounded `body : Set (Fin dim → ℝ)`, a
  `base` point, and a `map : (Fin dim → ℤ) →+ G`); its point set
  `ConvexProgression.toSet`; the finiteness theorem `finite_toSet` over `ℤ`
  and the resulting `ConvexProgression.toFinset` (with `coe_toFinset` /
  `mem_toFinset` API); the preimage-side lattice point set
  `ConvexProgression.latticeFinset` (the technical notion of size in the
  conjecture, with `finite_latticeSet` / `coe_latticeFinset` API and the
  comparison lemma `toFinset_card_le_latticeFinset_card`); and a concrete
  instance `prog024` (the integer points of `[-1, 1]`, scaled by `2`,
  shifted by `2`). The pointwise sum `A + A` of finsets is mathlib's
  (`open scoped Pointwise` is already in effect), so `(A + A).card` is
  computable and claims about small concrete sets are provable by `decide`.
- **Slot zone.** Two theorem slots, bodies blank, in this order:

  1. `conj` — the conjecture itself: `∃ C₁ C₂ : ℕ, ∀ A : Finset ℤ,
     A.Nonempty → ∀ K : ℕ, (A + A).card ≤ K * A.card → ∃ P`, with `P.dim ≤
     C₁ * Nat.log 2 (K + 1)`, `P.latticeFinset.card ≤ (K + 1) ^ C₂ * A.card`
     (size = lattice points of the body on the preimage side, as in Manners's
     footnote 1 — not the image-set cardinality), and
     `A ⊆ X + P.toFinset` for some `X` of at most `(K + 1) ^ C₂` shifts.
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
