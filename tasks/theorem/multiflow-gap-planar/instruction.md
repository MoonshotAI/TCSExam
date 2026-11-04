# Task: Multiflow-multicut gap lower bound on planar graphs

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean`
contains a definition layer and exactly one theorem, stated in full and
"proved" by `sorry` inside a marked slot. **Prove that theorem.**

The theorem is a pure-graph statement behind a multiflow–multicut gap
lower bound. A *small-diameter decomposition distribution*
`SDD(G, 2w, p)` of a graph is a probability distribution on edge sets
whose removal leaves components of diameter `< 2w`, under which every
edge is cut with probability at most `p`. A *cactus* is a graph in which
every edge lies on at most one cycle. The theorem states: if the cactus
family is `SDD(2w, p)`-acceptable for an even `w ≥ 2` and `0 < p < 1` —
every finite cactus graph admits such a distribution — then
`8/7 ≤ w·p`. Via the gap–SDD equivalence (not formalized here), this
says the multiflow–multicut gap of cactus, and hence planar, graphs is
at least `16/7`.

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
proved (no `sorry`) using only the standard axioms, and 0 otherwise.

## Notes

- Time budget: you have up to **12 hours** of wall-clock time for this task; the run is terminated when it expires.
