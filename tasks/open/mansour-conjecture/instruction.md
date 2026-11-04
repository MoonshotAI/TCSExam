# Task: Mansour's Conjecture — Prove It or Refute It (Lean 4, machine-verified)

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean` contains
a definition layer and two theorems — the conjecture (`conj`) and its
negation (`refuted`) — each "proved" by `sorry` inside a marked slot.
**Prove either one.**

The conjecture is **Mansour's conjecture** (Yishay Mansour, COLT 1992; *An
O(n^{log log n}) learning algorithm for DNF under the uniform distribution*,
J. Comput. System Sci. 50(3):543–550, 1995; statement as in the Simons
Institute open-problem collection *Real Analysis in Computer Science* and
O'Donnell, *Analysis of Boolean Functions*, §4.4).

A *DNF* (disjunctive normal form) is an OR
of terms, each term an AND of literals (a variable `x i` or its negation).
Its *size* is the number of terms. Every Boolean function `f : {±1}ⁿ → {±1}`
has a Fourier expansion: for each set `S` of coordinates, the coefficient
`f̂(S) = E[f(X)·χ_S(X)]`, where `χ_S(X) = ∏_{i ∈ S} X_i` and the expectation
is over the uniform distribution on the cube. The *spectral mass* of `f` is
`Σ_S f̂(S)² = 1` (Parseval). The spectrum of `f` is **ε-concentrated** on a
collection `ℱ` of coefficient sets if the mass outside `ℱ` is at most `ε`:

    Σ_{S ∉ ℱ} f̂(S)² ≤ ε.

Mansour's conjecture claims that DNFs have tightly concentrated spectra:
there is a universal constant `C` such that for every DNF with `s > 1` terms
and every `ε ∈ (0, 1/2]`, the spectrum of the computed function is
`ε`-concentrated on some collection `ℱ` with `|ℱ| ≤ s^{C·log(1/ε)}`. (For
constant `ε` this is `poly(s)` coefficients.) The conjecture is **open** —
the best known bound for general DNFs is concentration on
`(s/ε)^{O(log log(s/ε) · log(1/ε))}` coefficients (Mansour 1995; Lecomte–Tan
2021 sharpens the dependence on the read number and still lists proving the
conjecture as "the obvious open problem"). It is proved for random DNFs
and constant-read DNFs (Klivans–Lee–Wan 2010), and for read up to
Θ̃(log log s) (Lecomte–Tan 2021); the
weak form `s^{O(1/ε)}` follows from the Fourier Entropy–Influence
conjecture. A proof or a counterexample would both be publishable results.

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).** Two layers, in the
  `MansourConjecture` namespace:
  - *Theory layer (over ℚ, for proofs).* The cube `Fin n → Bool`; the
    embedding `pmOne : Bool → ℚ` (`true ↦ 1`, `false ↦ −1`); characters
    `chi S x`; uniform expectation `cubeAvg`; Fourier coefficients
    `fourierCoeff f S = E[f·χ_S]`; terms `Term n` (positive/negative literal
    sets) with satisfaction `T.Sat x`, variable set `T.vars`, consistency
    `T.Consistent`; DNF satisfaction `DNFSat D x` and the computed ±1-valued
    function `dnfFun D`; concentration `SpectralConcQ` (over ℚ) and
    `SpectralConc` (over ℝ, the conjecture's form); decision trees `DTree`
    (`eval`, `depth`, `evalFun`) and low-degree collections `lowDegree d`;
    the running example `selectorDnf`/`selectorSupport`/`selectorNum`.
    API lemmas are fully proved: character orthonormality
    (`cubeAvg_chi`, `cubeAvg_chi_mul`), Fourier inversion
    (`fourier_inversion`), Parseval (`parseval`), linearity and the shift
    rule (`fourierCoeff_add/sub/smul`, `fourierCoeff_chi_singleton_mul`),
    the single-term expansion (`Term.ind_eq_sum`, `Term.ind_coeff`,
    `dnfFun_single`, `dnfFun_single_expansion`), and
    `card_symmDiff_singleton`.
  - *Compute layer (over ℤ, for kernel computation).* `pmOneZ`, `chiZ`,
    `dnfFunZ`, and `fourierNum f S = Σ_x f(x)·χ_S(x) ∈ ℤ` — for a ±1-valued
    `f`, the integer **numerator** `2^n · f̂(S)`. The kernel does not
    evaluate rational arithmetic, so decidable claims about concrete
    instances are stated over ℤ; cast lemmas bridge the layers
    (`fourierCoeff_dnfFun_eq_num : f̂ of a DNF = numerator / 2^n`).
- **Slot zone.** Two theorem slots, bodies blank, in this order:

  1. `conj` — the conjecture itself (`Conjecture`): `∃ C : ℕ`, for every
     DNF `D` (a `List (Term n)`) with `1 < D.length` terms and every real
     `ε` with `0 < ε ≤ 1/2`, some collection `ℱ` satisfies
     `SpectralConc (dnfFun D) ε ℱ` and
     `(ℱ.card : ℝ) ≤ (D.length : ℝ) ^ ((C : ℝ) * Real.log (1 / ε))`.
  2. `refuted` — its negation (`¬Conjecture`).

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
