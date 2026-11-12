# Task: Log-squared randomized lower bound for small-set chasing

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean`
contains a definition layer and exactly one theorem, stated in full and
"proved" by `sorry` inside a marked slot. **Prove that theorem.**

The theorem comes from the theory of online algorithms. In *small-set
chasing* on a finite metric space, an online algorithm controls one
server; each request is a finite subset `S` of points, and serving it
means moving into `S`, paying the distance travelled. The theorem
states:

> There are a universal constant `c > 0` and a threshold `n₀` such that
> for every `n ≥ n₀` there is an `n`-point metric space `M` and a start
> point for which small-set chasing admits a distributional lower bound
> of `c·(log₂ n / log₂ log₂ n)²`: a finite sample space carrying a
> distribution of request sequences with positive expected optimal cost
> such that every deterministic online algorithm pays, in expectation,
> at least `c·(log₂ n / log₂ log₂ n)²` times the expected optimal cost.

## Rules

- For verifier safety, executable commands `#eval`, `#exec`, `#exit`, and
  `#compile` are not allowed in submitted Lean files, including harmless
  diagnostics. Remove these commands before submission; the verifier rejects
  them before compiling the proof.
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
`mss_loglog_lower` stays within the standard axioms (`propext`,
`Classical.choice`, `Quot.sound`); otherwise `0.0`.

## Notes

- Time budget: you have up to **12 hours** of wall-clock time for this task; the run is terminated when it expires.
