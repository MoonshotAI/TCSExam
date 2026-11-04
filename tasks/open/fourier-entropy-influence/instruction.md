# Task: The Fourier Entropy–Influence Conjecture — Prove It or Refute It (Lean 4, machine-verified)

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean` contains
a definition layer and two theorems — the conjecture (`conj`) and its
negation (`refuted`) — each "proved" by `sorry` inside a marked slot.
**Prove either one.**

The conjecture is the **Fourier Entropy–Influence conjecture** (FEI), first
raised by Ehud Friedgut and Gil Kalai in 1996 (*Every monotone graph
property has a sharp threshold*, Proc. Amer. Math. Soc. 124(10):2993–3002)
and standardized under its present name by Ryan O'Donnell, John Wright and
Yuan Zhou (ICALP 2011, *The Fourier Entropy–Influence Conjecture for
certain classes of Boolean functions*). It is **open**: the best general
bound to date is Xiao Han 2024's
`H(f̂²) ≤ O(I(f) + Σₖ Iₖ(f)·log(1/Iₖ(f)))` (Combinatorica 45(1)), and work
in 2024–2025 still treats the conjecture itself as unresolved.

Every Boolean function `f : {±1}ⁿ → {±1}`
has a Fourier expansion `f(x) = ∑_{S ⊆ [n]} f̂(S)·χ_S(x)`, where
`χ_S(x) = ∏_{i ∈ S} xᵢ` and `f̂(S) = 2⁻ⁿ∑ₓ f(x)χ_S(x)`. By Parseval the
squared coefficients `f̂(S)²` form a probability distribution on the subsets
of `[n]`; its **Shannon entropy** is

    H(f̂²) = ∑_S f̂(S)² · log(1 / f̂(S)²).

The **total influence** is `I(f) = ∑ᵢ Infᵢ[f]`, where `Infᵢ[f]` is the
probability that flipping a uniformly random input's `i`-th bit changes the
value of `f`. The conjecture:

    there is a universal constant C such that  H(f̂²) ≤ C · I(f)  for every
    Boolean function f on every cube {±1}ⁿ.

Dictators (`H = 0, I = 1`) and parities (`H = 0, I = n`) make the two ends
trivial; already `AND₂` shows `C ≥ 2·ln 2`, and the minterm/`AND` family
forces `C ≥ 4·ln 2`. A proof or a counterexample would both be publishable
results (FEI implies a weak form of Mansour's conjecture on DNF spectra).

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).** The cube `Cube n := Fin n → Bool`;
  the ±1 embedding `pmOne` (`true ↦ 1`, `false ↦ −1`); bit flip `flipAt`;
  characters `charFn S x = ∏_{i ∈ S} pmOne (x i)`; Fourier coefficients
  `fourierCoeff f S`; the entropy `fourierEntropy f` (natural log; the
  constant `C` absorbs base changes); influences `influence f i` (the L²
  form, equal to the flip probability for ±1-valued `f` by
  `influence_eq_card`) and `totalInfluence f`; the predicate `IsBoolean f`;
  and the conjecture `FeiConjecture`. A full API is proved: character
  orthogonality (`sum_charFn`, `sum_charFn_pointwise`), coefficient
  extraction (`fourierCoeff_charFn`), linearity (`fourierCoeff_add/smul/neg`),
  the Fourier expansion (`fourier_expansion`), Parseval
  (`sum_sq_fourierCoeff`, and `sum_sq_fourierCoeff_isBoolean` — the spectrum
  really is a probability distribution), and cube enumeration for concrete
  computations (`sum_cube_succ`, `sum_cube_zero`). Three concrete example
  functions are fixed here too: `dictator i`, `parityFun n`, `andTwo`, with
  their `IsBoolean` lemmas.
- **Slot zone.** Two theorem slots, bodies blank, in this order:

  1. `conj` — the conjecture itself: `FeiConjecture`, i.e. `∃ C > 0, ∀`
       Boolean `f`, `fourierEntropy f ≤ C * totalInfluence f`.
  2. `refuted` — its negation: `¬ FeiConjecture`.

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
