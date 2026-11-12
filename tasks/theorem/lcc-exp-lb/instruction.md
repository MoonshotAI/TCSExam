# Task: Exponential lower bound for linear 3-query locally correctable codes

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean`
contains a definition layer and exactly one theorem, stated in full and
"proved" by `sorry` inside a marked slot. **Prove that theorem.**

The theorem comes from coding theory. A *linear 3-query locally
correctable code* in *normal form* is a systematic linear code
`ℒ : F₂ᵏ → F₂ⁿ` together with, for every coordinate `u`, a 3-uniform
hypergraph matching `H u` of `d0` edges such that `x_u = Σ_{v ∈ C} x_v`
(over F₂) for every edge `C ∈ H u` and every codeword `x`. The theorem
states: there is an absolute constant `C > 0` such that every such code
with `d0 ≥ δn` satisfies `k ≤ C·(log₂ n)⁸/δ²`, i.e.
`n ≥ 2^{(δ²k/C)^{1/8}}`. A linear 2-LDC lower bound is given as a
hypothesis.

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
