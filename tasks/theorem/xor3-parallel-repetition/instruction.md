# Task: Parallel repetition of three-player XOR games

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean`
contains a definition layer and exactly one theorem, stated in full and
"proved" by `sorry` inside a marked slot. **Prove that theorem.**

The theorem comes from game theory. A *3-XOR game* `G` is given by a
probability distribution `μ` over question triples `(x, y, z)` and a
target `t(x, y, z)` in a finite abelian group `A`: the verifier samples
`(x, y, z) ~ μ`, collects answers `f(x), g(y), h(z) ∈ A` from the three
players, and accepts iff `f(x) + g(y) + h(z) = t(x, y, z)`. The *value*
`val(G)` is the best acceptance probability over all strategies. In the
*n-fold parallel repetition* the verifier samples `n` independent
challenges and the players must win all of them. An *embedding* of `μ`
into an abelian group is a triple of maps `σ, γ, ϕ` with
`σ(x) + γ(y) + ϕ(z) = 0` on the support of `μ`; `μ` *has no
`ℤ`-embeddings* if every embedding into `(ℤ, +)` is constant in each
coordinate. The theorem is stated conditionally on a packaged
additive-combinatorics input `FreimanAssumption` (part of the
definition layer), and states:

> If `val(G) < 1` and `μ` has no `ℤ`-embeddings, then
> `val(G^⊗n) ≤ 2^{−cn}` for some `c > 0` (depending on the game) and
> all `n ≥ 1`.

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
`xor3_parallel_repetition` stays within the standard axioms
(`propext`, `Classical.choice`, `Quot.sound`); otherwise `0.0`.

## Notes

- Time budget: you have up to **12 hours** of wall-clock time for this task; the run is terminated when it expires.
