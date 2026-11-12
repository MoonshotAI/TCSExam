# Task: PRGs for Constant-Width ROBPs (Width 4) — Prove It or Refute It (Lean 4, machine-verified)

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean` contains
a definition layer and two theorems — the conjecture (`conj`) and its
negation (`refuted`) — each "proved" by `sorry` inside a marked slot.
**Prove either one.**

The conjecture is the **constant-width PRG problem at width 4** (Nisan,
*Combinatorica* 12(4):449–461, 1992, for the `O(log² n)`-seed generator for
all widths; the constant-width question is posed explicitly by
Braverman–Rao–Raz–Yehudayoff, FOCS 2010, and Forbes–Kelley, FOCS 2018).

A *read-once branching program* (ROBP) of
length `n` and width `w` in standard order is a layered directed graph with
layers `0, …, n`, exactly `w` states per layer, one designated start state
in layer 0, and a set of accepting states in the last layer. Every state of
layer `i` has one outgoing edge labelled 0 and one labelled 1, both going
to layer `i + 1`, and layer `i` reads the input bit `x i`. On input
`x ∈ {0,1}ⁿ` the program walks from the start state following the edge
labelled `x i` at layer `i`, and accepts iff it ends in an accepting
state. Width-`w` length-`n` ROBPs are the standard nonuniform model of
randomized logspace computations.

A *pseudorandom generator* (PRG) with seed length `s` is a function
`G : {0,1}ˢ → {0,1}ⁿ`. It **ε-fools** a program `B` if the acceptance
probability of `B` on `G(y)` for a uniform random seed `y` differs from
its acceptance probability on a uniform random `n`-bit input by at most
`ε`. Nisan (1992) constructed explicit PRGs with seed `O(log² n)` fooling
all polynomial-width ROBPs with error `1/n`. Whether the seed can be
`o(log² n)` for **constant** width is open: for width 2 the problem is
solved with optimal seed `O(log(n/ε))` (small-bias spaces, via
Bogdanov–Dvir–Verbin–Yehudayoff, *Theory Comput.* 9:283–293, 2013); for
width 3, Meka–Reingold–Tal (STOC 2019) give seed `Õ(log n · log(1/ε))`,
which at error `ε = 1/n` is still `Õ(log² n)` — no asymptotic improvement
over Nisan at that error. For width 4 no explicit generator with seed
`o(log² n)` at error `1/n` is known (Doron–Hoza, APPROX/RANDOM 2025), and
none is known even for the weaker hitting-set notion. **Width 4 is the
first width at which the problem is completely open.** The conjecture
asserts that such a generator exists:

    ∃ explicit family G n : {0,1}^(s n) → {0,1}^n,
      (∀ n ≥ 1, G n (1/n)-fools every width-4 length-n ROBP) ∧
      s n / (log n)² → 0.

"Explicit" means computable in time polynomial in `n`, pinned down as two
clauses: the seed-length schedule `s` is uniformly polynomial-time
computable (a fixed machine outputs `s n` from the unary `n` within a
polynomial step bound), and every output bit `G n y i` is computable by a
single-tape Turing machine within `k·n^c` steps on the unary encoding of
`(n, y, i)` (see below). Without an explicitness clause the statement would
not express the open problem — nonconstructively, counting arguments give
short seeds for any class.

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).** The ROBP structure (`step`, `start`,
  `accept`) with the path walk `B.run x`; the acceptance count/probability
  `B.acceptCount`, `B.acceptProb : ℚ` over uniform inputs; the fooled
  count/probability `B.fooledCount G`, `B.fooledProb G : ℚ` on generator
  outputs; the fooling relation `B.Fools ε G`; the fixed-zone lemma
  `B.fooledProb_id : B.fooledProb id = B.acceptProb`. The input space is
  enumerated by bit encodings (`inputOf`, `allInputs`), and a proved
  cross-multiplication bridge (`fools_iff`, with the
  `Decidable (B.Fools ε G)` instance) turns the rational fooling
  inequality into a single integer inequality, so `Fools` is decidable by
  kernel computation. The explicitness
  layer: single-tape Turing machines (`TM`, alphabet `Option Bool` with
  `none` as blank, transitions `TM.next`, bounded runs `TM.run`,
  `TM.ComputesBit`), the tape encoding `encodeInput n m y i` (`n` in unary,
  a blank, the seed bits, a blank, `i` in unary), and the predicate
  `Explicit s G` (the seed-length schedule `s` is uniformly
  polynomial-time computable, and some machine computes every output bit
  `G n y i` within `k·n^c` steps). Two concrete instances:
  `parityROBP : ROBP 4 2` (the parity program) and
  `andGen : {0,1}² → {0,1}³`, `(a, b) ↦ (a, a ∧ b, b)`; also
  `tableOfPerm` (a bit-encoding of the width-2 length-3 permutation
  transition tables) and `quarter` (the rational `1/4` as a structure
  literal). All definitions
  are computable, so claims about small concrete programs and small machine
  runs are provable by `decide` (kernel computation only).
- **Slot zone.** Two theorem slots, bodies blank, in this order:

  1. `conj` — the conjecture: `∃ s : ℕ → ℕ, ∃ G : ∀ n, (Fin (s n) → Bool) →
     (Fin n → Bool)`, with `Explicit s G`,
     `∀ n ≥ 1, ∀ B : ROBP n 4, B.Fools (1 / (n : ℚ)) (G n)`, and
     `Filter.Tendsto (fun n => (s n : ℝ) / (Real.log n) ^ 2) atTop (nhds 0)`
     — an explicit generator family with seed `o(log² n)` fooling all
     width-4 length-`n` ROBPs with error `1/n`.
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
