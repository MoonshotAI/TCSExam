# Task: The Polar-Code Scaling Exponent — Prove It or Refute It (Lean 4, machine-verified)

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean` contains
a definition layer and two theorems — the conjecture (`conj`) and its
negation (`refuted`) — each "proved" by `sorry` inside a marked slot.
**Prove either one.**

The conjecture concerns the **scaling exponent of polar codes** (Arikan
2009, *Channel polarization: a method for constructing capacity-achieving
codes for symmetric binary-input memoryless channels*, IEEE Trans. Inf.
Theory 55(7)), in the form used by the finite-length-scaling literature
(Hassani–Alishahi–Urbanke, IEEE Trans. Inf. Theory 2014;
Mondelli–Hassani–Urbanke, IEEE Trans. Inf. Theory 2016).

Polar codes are the first explicit,
low-complexity codes proved to achieve channel capacity, and they are in the
5G control-channel standard. Send data at rate `R` over a binary memoryless
symmetric (BMS) channel `W` of (symmetric) capacity `I(W)`, with a polar code
of block length `N`, and keep the block error probability below a fixed
target. As `R` approaches `I(W)`, the required block length grows
polynomially in the reciprocal of the gap: `N = Θ((I(W) − R)^(−μ))`. The
number `μ` is the **scaling exponent** of the channel; it measures how fast
the `2^n` synthetic channels produced by the polar recursion polarize to
perfect or useless extremes.

The value of `μ` for the binary erasure channel (BEC) is `3.627`, computed by
Korada–Montanari–Telatar–Urbanke (ISIT 2010). It is conjectured that the same
exponent is **universal**: every BMS channel has scaling exponent `3.627`
(Mondelli–Hassani–Urbanke 2016). What is proved today for general BMS
channels is only `3.579 ≤ μ ≤ 4.63` (Hassani–Alishahi–Urbanke 2014;
Wang–Lin–Vardy–Gabrys 2022, improving `μ ≤ 4.714` of Mondelli–Hassani–Urbanke
2016). Closing this interval is the central open quantitative question of
polar-code theory.

This task uses the **threshold form** of the conjecture at the value 4.0,
which lies strictly inside the proved interval `(3.579, 4.63)`:

- `conj`: every BMS channel has scaling exponent **at most 4**. Proving it
  improves the best proved universal upper bound from 4.63 to 4.0.
- `refuted`: its negation — some BMS channel fails the rate-`2^(−n/4)`
  bound (scaling exponent at least 4). Proving it improves the best proved
  universal lower bound from 3.579 to 4.0.

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).** Binary-input channels with finite
  output alphabets as explicit transition laws (`Channel`: a function
  `Fin 2 → Y → ℝ` with nonnegativity and unit-sum proofs); output symmetry
  (`IsBMS`: an involution of the output alphabet exchanging the two input
  distributions); the Bhattacharyya parameter `Z(W) = ∑ y √(W(0,y)·W(1,y))`
  and the symmetric mutual information `I(W)` (uniform input); Arikan's
  channel transforms `polarMinus` (`W⁻`) and `polarPlus` (`W⁺`) and the
  depth-`n` synthetic channels `polarChannel W s` over transform sequences
  `s : List Bool`; the finite Bhattacharyya process `fracGood W n t`, the
  fraction of the `2^n` depth-`n` synthetic channels with `Z ≤ t` — this is
  `P(Z_n ≤ t)` with no measure theory involved; the scaling predicate
  `ScalingExponentLe W ν` ("`W` has scaling exponent at most `ν`"): for
  every `0 < pe < 1` there is a constant `c` such that for all `n ≥ 1`,
  `fracGood W n (pe·2^(−n)) ≥ I(W) − c·2^(−n/ν)` — the good-channel mass
  approaches `I(W)` at rate at least `2^(−n/ν)`;
  the binary erasure channel `BEC ε` on the output alphabet `Option (Fin 2)`
  (`none` is the erasure symbol); the Arikan kernel `polarKernel` and the
  polar generator matrices `polarGen n` (bit-reversed Kronecker powers,
  `G_{2n} = B_{2n}·(G₂ ⊗ G_n)`). Well-formedness of the transforms and basic
  sanity lemmas (`Z_nonneg`, `Z_le_one`, `isBMS_BEC`) are fully proved.
- **Slot zone.** Two theorem slots, bodies blank, in this order:

  1. `conj` — the threshold conjecture:
     `∀ (W : Channel Y), IsBMS W → ScalingExponentLe W 4` — every BMS
     channel `W` satisfies `ScalingExponentLe W 4`.
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
