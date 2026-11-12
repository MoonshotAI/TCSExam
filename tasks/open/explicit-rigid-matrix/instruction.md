# Task: Valiant Rigidity of the Hilbert Matrices — Prove It or Refute It (Lean 4, machine-verified)

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean` contains
a definition layer and two theorems — the conjecture (`conj`) and its
negation (`refuted`) — each "proved" by `sorry` inside a marked slot.
**Prove either one.**

The conjecture is **Valiant's matrix-rigidity problem** (Valiant 1977,
*Graph-theoretic arguments in low-level complexity*, MFCS), instantiated to
one concrete candidate family: the Hilbert matrices over `ℚ`.

The rigidity `R_A(r)` of an `n × n` matrix `A` is the
minimum number of entries one must modify to bring its rank down to at most
`r`. Valiant (1977) asked for an *explicit* matrix family `{A_n}` with
fixed constants `ε, δ > 0` such that `R_{A_n}(ε·n) ≥ n^{1+δ}` for all `n`;
such a family would give the first super-linear explicit lower bound for
linear circuits. Random matrices are rigid, but no explicit family is
known; the Walsh–Hadamard, Fourier and circulant candidates were proved
*not* rigid in the required regime (Alman–Williams 2017; Dvir–Liu 2020).

In this task the conjecture is instantiated to one concrete candidate
family: the **Hilbert matrices over `ℚ`** (`H_n(i,j) = 1/(i+j+1)`). The
statement is:

> there exist rational `ε, δ > 0` such that for every `n`, bringing the
> rank of the `n × n` Hilbert matrix down to at most `⌊ε·n⌋` requires
> modifying at least `⌈n^{1+δ}⌉` entries.

The Hilbert family is explicit (closed-form entries), so proving `conj`
resolves Valiant's problem in the affirmative; proving `refuted` rules out
the Hilbert/Cauchy candidate, in the spirit of the published non-rigidity
theorems for Hadamard and Fourier matrices.

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).** The difference count
  `diffCount A B` (the number of positions where two `n × n` matrices
  differ — the "number of entries to modify" in the definition of
  rigidity); the rigidity predicate `IsRigidAt A r s` (every matrix of rank
  at most `r` differs from `A` in at least `s` entries — equivalently,
  Valiant's rigidity value satisfies `R_A(r) ≥ s`); the candidate family
  `hilbert n : Matrix (Fin n) (Fin n) ℚ` (entry `(i, j)` is
  `1 / (i + j + 1)`, a closed formula, so the family is explicit in
  Valiant's sense); the conjecture predicate `HilbertRigid`; and a sampled
  explicit `{0,1}`-valued `4 × 4` matrix `sampleMatrix4` over `ℚ` (all
  sixteen of its `3 × 3` minors are nonzero).
- **Slot zone.** Two theorem slots, bodies blank, in this order:

  1. `conj` — the conjecture itself: `HilbertRigid`, i.e.
     `∃ ε δ : ℚ, 0 < ε ∧ 0 < δ ∧ ∀ n : ℕ, IsRigidAt (hilbert n)
     ⌊ε * (n : ℚ)⌋₊ ⌈(n : ℝ) ^ (1 + (δ : ℝ))⌉₊` — for every `n`, reducing
     the rank of the `n × n` Hilbert matrix to at most `⌊ε·n⌋` requires
     modifying at least `⌈n^{1+δ}⌉` entries.
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
