# Task: Permanent vs. Determinant — Prove It or Refute It (Lean 4, machine-verified)

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean` contains
a definition layer and two theorems — the conjecture (`conj`) and its
negation (`refuted`) — each "proved" by `sorry` inside a marked slot.
**Prove either one.**

The conjecture is the **permanent-vs-determinant problem** (Leslie Valiant,
1979; *The complexity of computing the permanent*, Theoretical Computer
Science 8, 189–201).

The *determinant* of an n×n matrix is the
signed sum over all permutations, and the *permanent* is the same sum with
all signs replaced by +1:

    det(A) = Σ_σ sign(σ) ∏ᵢ Aᵢ,σ₍ᵢ₎,        perm(A) = Σ_σ ∏ᵢ Aᵢ,σ₍ᵢ₎.

Determinants are easy to compute (Gaussian elimination); permanents are
#P-complete. But there is a more basic way determinants could compute
permanents: maybe perm_n is the determinant of some *larger* matrix whose
entries are affine linear forms (a constant plus a linear combination) in
the original variables. The **determinantal complexity** dc(f) of a
polynomial f is the least size m of such a matrix with det = f.

Valiant's conjecture says this cannot be done efficiently:

    dc(perm_n)  is not bounded by any polynomial in n.

In other words, for every exponent c there are arbitrarily large n with
dc(perm_n) > n^c. The problem is **open**: the best lower bound is only
quadratic, dc(perm_n) ≥ n²/2 (Mignon–Ressayre 2004), while the best general
construction is exponential, dc(perm_n) ≤ 2ⁿ − 1 (Grenet 2011). Already the
exact value of dc(perm_4) is unknown (9 ≤ dc(perm_4) ≤ 15; the lower bound is
due to Alper–Bogart–Velasco 2015). A proof would
separate VP from VNP in the strongest known way; a polynomial upper bound
would collapse the classical picture of algebraic complexity.

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).** The generic variable matrix
  (`varMatrix n`: entry (i,j) is the variable `X (i,j)`); the permanent as a
  polynomial (`permPoly n`, mathlib's `Matrix.permanent` of `varMatrix n`;
  the base field is ℝ); determinantal representations (`IsDetRepr f m`: a
  matrix of polynomials of total degree ≤ 1 — affine linear forms — whose
  determinant is `f`); determinantal complexity (`detComp f`: the least such
  `m`, by convention 0 if none exists); the conjecture predicate
  (`SuperpolyDc`: for every exponent c there are arbitrarily large n with
  dc(perm_n) > n^c). API lemmas (fully proved): the permanent's total degree
  is n (`totalDegree_permPoly`), a determinant of affine forms has degree at
  most the matrix size (`totalDegree_det_le`), and the explicit expansions
  `permPoly_two` / `permPoly_three`.
- **Slot zone.** Two theorem slots, bodies blank, in this order:

  1. `conj` — the conjecture itself: `SuperpolyDc`, i.e.
     `∀ c N : ℕ, ∃ n : ℕ, N ≤ n ∧ n ^ c < detComp (permPoly n)` — for every
     exponent `c` and every bound `N` there is an `n ≥ N` with
     dc(perm_n) > n^c.
  2. `refuted` — its negation: `¬SuperpolyDc` (i.e. dc(perm_n) is eventually
     bounded by some monomial n^c).

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
