# Task: The Log-Rank Conjecture — Prove It or Refute It (Lean 4, machine-verified)

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean` contains
a definition layer and two theorems — the conjecture (`conj`) and its
negation (`refuted`) — each "proved" by `sorry` inside a marked slot.
**Prove either one.**

The conjecture is the **log-rank conjecture** of communication complexity
(Lovász and Saks, *Lattices, Möbius functions and communication
complexity*, FOCS 1988; journal version J. Comput. System Sci. 1993).

For a two-party Boolean function
`f : X × Y → {0,1}`, let `D(f)` be its deterministic communication
complexity — the depth of the shallowest two-party protocol tree computing
`f` — and let `rank(M_f)` be the rank over the reals of its communication
matrix `M_f[x, y] = f(x, y)`. Since a depth-`d` protocol partitions the
matrix into at most `2^d` monochromatic rectangles, `log₂ rank(M_f) ≤ D(f)`
always holds; the rank of the matrix is one of the strongest known
lower-bound methods for `D(f)`. The conjecture of Lovász and Saks
says this lower bound is tight
up to a polynomial: for some constant `c`, every `f` satisfies
`D(f) ≤ (log₂ rank(M_f))^c`. The best known upper bound is `D(f) = O(√rank)`
(Sudakov–Tomon 2024); the largest known separation is
`D(f) = Ω((log₂ rank)²)` (Pabbaraju 2026). Settling it in either direction
would be a major result.

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).** `commMatrix f` (the 0/1
  communication matrix over `ℝ`), `Protocol X Y` (two-party protocol trees:
  `alice g l r` branches on a bit `g x` of Alice's input, `bob g l r` on a
  bit of Bob's, `leaf b` outputs `b`) with `depth` / `run` / `Computes`,
  the deterministic communication complexity `D f` (the least achievable
  protocol depth — the fixed zone proves the trivial pinpoint protocol, so
  the minimum is attained), the conjecture `LogRankConjecture`, and the
  two-bit inner product `ip2`. The conjecture is stated as

  ```lean
  def LogRankConjecture : Prop :=
    ∃ c : ℝ, 0 < c ∧ ∀ {X Y : Type} [Fintype X] [Fintype Y] (f : X → Y → Bool),
      2 ≤ (commMatrix f).rank →
        (D f : ℝ) ≤ (1 + Real.logb 2 ((commMatrix f).rank : ℝ)) ^ c
  ```

  Two degeneracies force this exact shape. The hypothesis `2 ≤ rank`
  excludes the trivial cases: a rank-1 matrix `u ∧ v` with both `u, v`
  nonconstant has `log₂ rank = 0` but `D = 2`. And the `1 + log₂ rank`
  form is the big-O content of the textbook statement: the pure power is
  already impossible at rank `2` (equality on one bit has `D = 2` but
  `(log₂ 2)^c = 1` for every `c`); the two forms are asymptotically
  equivalent, the exponents differing by an arbitrarily small amount.
- **Slot zone.** Two theorem slots, bodies blank, in this order:

  1. `conj : LogRankConjecture` — the conjecture itself.
  2. `refuted : ¬ LogRankConjecture` — its negation.

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
