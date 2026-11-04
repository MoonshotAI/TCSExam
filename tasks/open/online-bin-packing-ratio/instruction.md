# Task: The Optimal Competitive Ratio of Online Bin Packing — Prove It or Refute It (Lean 4, machine-verified)

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean` contains
a definition layer and two theorems — the conjecture (`conj`) and its
negation (`refuted`) — each "proved" by `sorry` inside a marked slot.
**Prove either one.**

The conjecture concerns the **optimal asymptotic competitive ratio `R*`**
of one-dimensional online bin packing — a value that has been bracketed but
never determined (upper bound: Balogh–Békési–Dósa–Epstein–Levin, ESA 2018;
lower bound: the same authors, *Algorithmica* 83(7), 2021).

In one-dimensional bin packing, items of
sizes in `(0, 1]` must be packed into bins of capacity 1, using as few bins
as possible. In the **online** problem the items arrive one by one and each
item must be assigned to a bin immediately, without knowing the future and
without ever moving an already-placed item. An online algorithm `A` has
**asymptotic competitive ratio** at most `r` if there is a constant `C`
such that for every instance `I`,

    A(I) ≤ r · OPT(I) + C,

where `OPT(I)` is the minimum number of bins the items fit into. The
optimal ratio `R*` is the infimum of `r` over all online algorithms. Its
true value is **unknown**: since 2018 the bracket has been

    1.54278 ≤ R* ≤ 1.57829

(lower bound: Balogh–Békési–Dósa–Epstein–Levin, *Algorithmica* 83(7),
2021; upper bound: same authors, ESA 2018). Closing this gap from either
side would be a publishable result.

## What's in `/app/Task/Basic.lean`

The file has two zones (namespace `OnlineBinPacking`):

- **Definition zone (do not modify).** An instance is a `List ℝ`; it is
  valid (`ValidInstance`) when every item size lies in `(0, 1]`.
  - `PacksIn l k` — the items of `l` can be assigned to `k` bins, every
    bin's total at most 1;
  - `optNumber l : ℕ` — the offline optimum `OPT(l)` (the least such `k`;
    attained for valid instances, `optNumber_spec`);
  - `OnlineAlg` — an online algorithm: a function assigning every input
    sequence to bin indices (`assign : List ℝ → List ℕ`), with fields
    forcing **prefix consistency** (decisions are irrevocable) and
    **feasibility** (bin capacity respected on every valid instance);
  - `algCost A l` — the number of bins `A` opens on `l`;
  - `AsympBound A r` — `∃ C, ∀` valid `l`, `algCost A l ≤ r · optNumber l + C`;
  - `RStar : ℝ` — the infimum of the achievable ratios (`sInf ratioSet`);
  - concrete online algorithms `nextFit` and `firstFit` (with their
    invariants proved: Next Fit's consecutive bins always sum to more
    than 1; both algorithms' runs are feasible packings);
  - the concrete instances `ones k` (`k` items of size 1, optimum `k`,
    proved: `optNumber_ones`) and `instFFR` (six items of each size
    6/41, 14/41, 21/41 — on this instance First Fit opens 10 bins
    against an optimum of 6).
  - Proved API: `optNumber_le_of_packsIn`, `list_sum_le_optNumber`
    (volume bound), `le_optNumber_of_pairwise_incompatible`,
    `optNumber_le_algCost`, `packsIn_of_feasible`, cost-of-assignment
    lemmas (`add_one_le_costOf`, `costOf_le`, `card_le_costOf`,
    `binOf_lt_costOf`, `fiber_sum_univ_eq_range`).
- **Slot zone.** Two theorem slots, bodies blank, in this order:

  1. `conj` — the conjecture itself: `RStar ≤ 1.56`. Proving it improves
     the best known upper bound 1.57829.
  2. `refuted` — its negation: `¬ RStar ≤ 1.56` (i.e. `RStar > 1.56`).
     Proving it improves the best known lower bound 1.54278.

**Important.** Real and rational arithmetic does not reduce in the Lean
kernel (`Rat.normalize` goes through `Nat.gcd`, which is well-founded),
so `decide` cannot check `ℝ` or `ℚ` computations. For concrete numeric
work, route computations through scaled natural-number shadows (like the
capacity-41 scaling of `instFFR`: a function on `List ℕ` with
`ℕ`-arithmetic comparisons *is* kernel-computable) and lift the results
through casts; use the volume bound `list_sum_le_optNumber` and explicit
packings (`optNumber_le_of_packsIn`) for optimum computations.

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
