# Task: Optimal list size of explicit folded Reed-Solomon codes

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean`
contains a definition layer and exactly one theorem, stated in full and
"proved" by `sorry` inside a marked slot. **Prove that theorem.**

The theorem comes from coding theory. A folded Reed–Solomon code packs
the evaluations of a low-degree polynomial `f` at consecutive powers of
a multiplicative generator `γ` into blocks: the `i`-th symbol of the
encoding is the block `f(αᵢ), f(γαᵢ), …, f(γ^{s−1}αᵢ)`. A code is
*list-decodable* with radius `ρ` and list size `L` if no Hamming ball
of radius `ρ` contains more than `L` codewords. The theorem states:

> For `ε > 0`, `1 ≤ k < N`, `s ∣ N`, `n = N / s`, `q > n`, rate
> `R = k/N`, and any `L > (1−R−ε)/ε` and
> `s > L·(L−1)·R/(εL−(1−R−ε)) + L − 1`, the folded Reed–Solomon code
> `FRS^{(s,γ)}_{n,k}(α)` at appropriate evaluation points is
> `(1 − R − ε, L)` list-decodable.

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
`frs_list_decodable_capacity` stays within the standard axioms
(`propext`, `Classical.choice`, `Quot.sound`); otherwise `0.0`.

## Notes

- Time budget: you have up to **12 hours** of wall-clock time for this task; the run is terminated when it expires.
