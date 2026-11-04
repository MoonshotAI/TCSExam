# Task: The KRW Composition Conjecture — Prove It or Refute It (Lean 4, machine-verified)

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean` contains
a definition layer and two theorems — the conjecture (`conj`) and its
negation (`refuted`) — each "proved" by `sorry` inside a marked slot.
**Prove either one.**

The conjecture is the **KRW composition conjecture**
(Karchmer–Raz–Wigderson, "Super-logarithmic depth lower bounds via the direct
sum in communication complexity", *computational complexity* 5:191–204, 1995).

A *Boolean formula* is a tree of binary AND
and OR gates whose leaves are signed literals (a variable `xᵢ` or its
negation `¬xᵢ`) or Boolean constants. The *depth* of a formula is the length
of the longest root-to-leaf path; leaves have depth 0 and negations are free
(they live at the leaves). The **formula depth** `D(f)` of a Boolean function
`f` is the minimum depth over all formulas computing it. Formula depth is the
complexity measure of the class NC¹: separating NC¹ from P amounts to
exhibiting an explicit function family of super-logarithmic formula depth,
and the best lower bound known today is still Håstad 1998's `(3 − o(1))·log n`.

The *block composition* of `f` on `m` variables and `g` on `n` variables is
the function on `m × n` variables that feeds each block of `n` inputs into a
copy of `g` and applies `f` to the `m` results:

    (f ⋄ g)(x₁, …, xₘ) = f(g(x₁), …, g(xₘ)).

Always `D(f ⋄ g) ≤ D(f) + D(g)` (compose two optimal formulas). The KRW
conjecture claims a matching lower bound — in the **reciprocal-share form**
used by the current literature (Gavinsky–Meir–Weinstein–Wigderson, ECCC
TR13-190 rev. 11 (2017), Conjecture 1.3 and footnote 3(ii)): there is a
universal `k ≥ 2` such that for all **non-constant** `f` (outer) and `g`
(inner),

    D(f ⋄ g) ≥ D(f) + D(g)/k.

(A related-formulation warning: the stronger form `D(f ⋄ g) ≥ D(f) + D(g) − c` with
a universal additive constant is NOT the open conjecture — Pudlák's example,
already recorded in KRW 1995 (p. 196), makes the additive gap grow like
`log log n`, so that form was known false from the start.) Iterated on a
growing function family, the share form would yield super-logarithmic
depth lower bounds and separate NC¹ from P (KRW 1995, Thm 5.2). It is a
proposed route towards NC¹ ≠ P that appears to require only combinatorial
techniques. The
conjecture is **open**: recent progress covers restricted cases only — a
strong-composition variant with outer function XOR and a random inner
function (Chukhin–Kulikov–Mihajlin, STACS 2025), and compositions with the
universal relation in place of one factor (Gavinsky–Meir–Weinstein–Wigderson
2017). The non-constancy hypothesis is essential: with `g` constant, `f ⋄ g`
is constant while `D(f)` is arbitrary.

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).** De Morgan formulas over a finite
  variable index set (`KRW.BFormula`: `const` / `lit i b` / `and` / `or`);
  their `depth` and `eval`; `BFormula.Computes φ f` (φ agrees with f on every
  assignment); the formula-depth complexity `KRW.depthOf f` (the minimum
  depth over all formulas computing f, defined as an `sInf` over ℕ and proved
  attained); the block composition `KRW.blockComp f g`; non-constancy
  `KRW.NonConst f` (f takes both values); variable renaming
  (`BFormula.rename`), negation by duality (`BFormula.dual`), substitution
  (`BFormula.subst`), and the composed formula `BFormula.compFormula` with
  its computation and depth lemmas; a DNF construction (`BFormula.dnfOf`)
  witnessing that every Boolean function is computed by some formula; the
  finite enumeration `BFormula.upTo d` of all formulas of depth at most `d`
  with `BFormula.mem_upTo` as its membership lemma; and an exhaustion
  principle (`KRW.not_computes_of_exhaust`, over `KRW.assignments4`, the
  explicit list of all 16 assignments on the 2×2 block variables) for
  kernel-checkable lower bounds on four variables. All API lemmas
  (`depthOf_le`, `le_depthOf`, `exists_computes_depth_eq`,
  `compFormula_computes`, `depth_compFormula_le`, …) are fully proved. Small
  instances are kernel-checkable: `Computes` on concrete functions is
  decidable, so exhaustive claims over `upTo d` are provable by `decide`.
- **Slot zone.** Two theorem slots, bodies blank, in this order:

  1. `conj` — the conjecture itself: `∃ k : ℕ, 2 ≤ k`, for all arities
     `m`, `n` and all non-constant `f` on `m` variables and `g` on `n`
     variables, `k·D(f) + D(g) ≤ k·D(f ⋄ g)` (natural multiplication; this
     is `D(f ⋄ g) ≥ D(f) + ⌈D(g)/k⌉` — no division or truncated
     subtraction).
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
