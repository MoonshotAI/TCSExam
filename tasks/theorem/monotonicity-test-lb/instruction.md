# Task: Query lower bound for monotonicity testing of Boolean functions

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean`
contains a definition layer and exactly one theorem, stated in full and
"proved" by `sorry` inside a marked slot. **Prove that theorem.**

The theorem comes from property testing. A Boolean function
`f : {0,1}ⁿ → {0,1}` is *monotone* if flipping a coordinate of an input
from 0 to 1 can never flip the value from 1 to 0, and it is `ε`-far from
monotone if every monotone function disagrees with it on at least an `ε`
fraction of the cube. A monotonicity tester queries values of an unknown
`f` and must tell the two cases apart; the question is how many queries an
adaptive algorithm needs. The theorem states: for every integer constant
`ℓ ≥ 1` there are a testing distance `ε > 0` and an error `δ > 0` such that
for all sufficiently large `m` (with `n = m²`) no randomized adaptive
algorithm whose deterministic members all have depth at most
`q = n^{1/2−1/(4ℓ+2)}/log₂ n` can both accept the yes distribution `Dyes`
with probability at least `1 − δ` and, jointly under the no distribution
`Dno`, accept an `ε`-far-from-monotone function with probability at most
`δ`. The two distributions and the stronger oracle they are queried through
are defined in the file.

## Rules

- Do not modify the given definitions or the theorem statement — the
  grader extracts the statement textually. If you need auxiliary
  definitions or lemmas, add them as separate declarations below the
  `-- END OF FIXED PART` line in `Task/Basic.lean` itself.
- No new `axiom` declarations and no `native_decide`; the verifier
  rejects these lexically. `sorry`/`admit` left in the theorem slot
  score 0. A `sorry` in your own auxiliary lemmas is not scanned for,
  but if the main theorem's proof depends on it, the `#print axioms`
  check fails (`sorryAx` is never allowed) and the score is 0.
- The project builds offline against the mathlib checkout at
  `/opt/lean-lib/mathlib4`; use `lake build` in `/app` to check.
- No `notation` / `macro` / `syntax` / `elab` / `macro_rules` /
  `initialize` declarations anywhere in your solution — they are
  rejected as semantic-layer rewriting.
- You may create auxiliary/scratch files (e.g. under `/app/Task/` or
  `/tmp`) for exploration, but do not import them from
  `Task/Basic.lean` — an `import` line at the top of `Task/Basic.lean`
  counts as a change to the fixed part and scores 0. Auxiliary content
  used by the main proof must live below the `-- END OF FIXED PART`
  line in `Task/Basic.lean` itself.

## Scoring

All-or-nothing: `1.0` iff the project compiles with the main theorem
proved (its slot free of `sorry`/`admit`) and `#print axioms` of
`monotonicity_testing_lb` stays within the standard axioms (`propext`,
`Classical.choice`, `Quot.sound`); otherwise `0.0`.

## Notes

- Time budget: you have up to **12 hours** of wall-clock time for this task; the run is terminated when it expires.
