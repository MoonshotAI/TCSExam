# Task: Log-competitive memoryless algorithm for chasing positive bodies

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean`
contains a definition layer and exactly one theorem, stated in full and
"proved" by `sorry` inside a marked slot. **Prove that theorem.**

The theorem comes from online algorithms. In *positive body chasing*, an
online algorithm sees a sequence of constraints in the nonnegative
orthant and must maintain a feasible point while paying the weighted ℓ1
distance it moves. Each constraint is a single halfspace — a covering
constraint `⟨c^t, x⟩ ≥ 1` or a packing constraint `⟨p^t, x⟩ ≤ 1 + ε` —
and cost is measured by the *upward recourse*
`∑_t ∑_i w_i·(x^t_i − x^{t-1}_i)⁺`. The algorithm answers each violated
constraint with a single KL-divergence projection (a covering update
with an additive offset `ε/(4·d^t·c^t_i)`, where `d^t` is the row
sparsity); it is presented here only through a response bundle
`ChaseRun` of the properties the analysis uses (the trajectory and the
KKT multipliers, with tightness and multiplier conditions, monotonicity,
and frozenness outside the support). The theorem states: the algorithm's
upward recourse is at most `K = (2 + ε)(1 + ε)·log(1 + 40d²/ε²)/ε`
times the upward recourse of every exactly-feasible benchmark
trajectory.

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

All-or-nothing: the score is 1 if the project compiles with the theorem
proved (no `sorry`) using only the standard axioms, and 0 otherwise.

## Notes

- Time budget: you have up to **12 hours** of wall-clock time for this task; the run is terminated when it expires.
