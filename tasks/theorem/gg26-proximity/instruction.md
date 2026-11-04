# Task: Optimal proximity gaps for algebraic codes

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean`
contains a definition layer and exactly one theorem, stated in full and
"proved" by `sorry` inside a marked slot. **Prove that theorem.**

The theorem comes from coding theory. A code has a *proximity gap* if,
along a low-degree parametric curve of words, either almost no curve
points are close to the code or all of them are; the formal statement is
about *mutual correlated agreement* (MCA) for *subspace-design* codes
(codes whose low-dimensional subspaces lose dimension quickly when
pinned at coordinates). The theorem states:

> Every `τ`-subspace-design code has mutual correlated agreement with
> proximity `1 − τ((ℓ+1)t) − 3/(2t)`, error
> `t·ℓ·(ℓ+1)·(m(1−τ((ℓ+1)t)) + 2t²)/|F|`, and slack `1/m`
> (for `2 ≤ m ≤ 4t`, under the stated field-size and boundary
> hypotheses).

Two ingredients are given as hypotheses: a pruning guarantee
(`PruningGuarantee`) and a list-size bound (`ListSizeBound`), both
packaged as hypothesis-level definitions in the file.

## Rules

- Do not modify anything above the line `-- END OF FIXED PART`, the
  theorem statement, or the `-- CHECKPOINT ...` marker lines.
- You may add your own auxiliary definitions and lemmas below the
  `-- END OF FIXED PART` line, outside the checkpoint slot.
- No new `axiom` declarations and no `native_decide`; the verifier
  rejects these lexically. `sorry`/`admit` left in the theorem slot
  score 0. A `sorry` in your own auxiliary lemmas is not scanned for,
  but if the main theorem's proof depends on it, the `#print axioms`
  check fails (`sorryAx` is never allowed) and the score is 0.
- The project builds offline against the mathlib checkout at
  `/opt/lean-lib/mathlib4`; use `lake build Task` in `/app` to check.
- No `notation` / `macro` / `syntax` / `elab` / `macro_rules` /
  `initialize` declarations anywhere in your solution — they are
  rejected as semantic-layer rewriting.
- You may create auxiliary/scratch files (e.g. under `/app/Task/` or
  `/tmp`) for exploration, but do not import them from
  `Task/Basic.lean` — an `import` line at the top of
  `Task/Basic.lean` counts as a change to the fixed part and scores
  0. Auxiliary content used by the main proof must live below the
  `-- END OF FIXED PART` line in `Task/Basic.lean` itself.

## Scoring

All-or-nothing: `1.0` iff the project compiles with the main theorem
proved (its slot free of `sorry`/`admit`) and `#print axioms` of
`mca_of_subspace_design` stays within the standard axioms
(`propext`, `Classical.choice`, `Quot.sound`); otherwise `0.0`.

## Notes

- Time budget: you have up to **12 hours** of wall-clock time for this task; the run is terminated when it expires.
