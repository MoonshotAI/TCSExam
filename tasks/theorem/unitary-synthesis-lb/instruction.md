# Task: One classical query cannot synthesize every unitary

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean`
contains a definition layer and exactly one theorem, stated in full and
"proved" by `sorry` inside a marked slot. **Prove that theorem.**

The theorem comes from quantum query complexity. A one-query adversary
is a triple `(M, V, Pj)`: an isometry `V : ℂ^N → ℂ^M` and a projection
`Pj` on `ℂ^M`. It prepares a *binary phase state*
`|ψ_h⟩ = (1/√N) Σ_x h(x)|x⟩` for a Boolean function `h : [N] → {±1}`,
applies `V`, makes a single oracle query (the oracle `f : [M] → {±1}`
acts as the diagonal sign matrix `O_f`), and measures with `Pj`; its
acceptance probability is `p_A(h|f) = Re ⟨Vψ_h, O_f Pj O_f Vψ_h⟩`. For a
function family `R : [K] × [N] → {±1}`, the distinguishing advantage is
`Δ_A(R) = max_f [ E_k p_A(R_k|f) − E_h p_A(h|f) ]`. The theorem states:

> There is an absolute constant `C > 0` such that for every one-query
> adversary `(M, V, Pj)` with `1 ≤ M`, `1 ≤ K`, and all isometry
> weights positive, the expected distinguishing advantage over a
> uniformly random function family is at most `C·√(ln M / K)`.

## Rules

- For verifier safety, executable commands `#eval`, `#exec`, `#exit`, and
  `#compile` are not allowed in submitted Lean files, including harmless
  diagnostics. Remove these commands before submission; the verifier rejects
  them before compiling the proof.
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
`advantage_expectation_bound` stays within the standard axioms
(`propext`, `Classical.choice`, `Quot.sound`); otherwise `0.0`.

## Notes

- Time budget: you have up to **12 hours** of wall-clock time for this task; the run is terminated when it expires.
