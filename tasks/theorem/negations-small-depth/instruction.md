# Task: The power of subtraction in arithmetic formulas

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean`
contains a definition layer and exactly one theorem, stated in full and
"proved" by `sorry` inside a marked slot. **Prove that theorem.**

The theorem comes from arithmetic complexity. An arithmetic formula
computes a multivariate polynomial using `+`, `−`, `×` gates; it is
*monotone* if it has no subtraction gate and all its constants are
non-negative. From any `n`-vertex graph `G` one builds the *graph
polynomial* `P_G = Σ_{a ∈ {0,1}ⁿ} (e(G[supp a]) − 1)² · ∏ᵢ x_{i,aᵢ}`
on the variable set `{x_{i,0}, x_{i,1}}` (all coefficients
non-negative). The theorem states: for every degree `d ≥ 2` there are
a constant `c > 0` and a threshold `N₀` such that for all `n ≥ N₀` and
every `n`-vertex `d`-regular spectral expander `G` (second largest
eigenvalue in absolute value of the adjacency matrix at most `d^{3/4}`),
the graph polynomial `P_G` is computed by an explicit arithmetic
formula of size at most `35·(e(G)+1)²·n`, but every monotone arithmetic
formula computing `P_G` has size at least `2^{c·n}`. A random-matching
existence lemma is given as the hypothesis `expanderMatchingProp`
(with per-degree constants).

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

All-or-nothing: the score is 1 if the project compiles with the theorem
proved (no `sorry`) using only the standard axioms (`propext`,
`Classical.choice`, `Quot.sound`), and 0 otherwise.

## Notes

- Time budget: you have up to **12 hours** of wall-clock time for this task; the run is terminated when it expires.
