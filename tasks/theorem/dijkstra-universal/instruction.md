# Task: Universal optimality of Dijkstra's algorithm
For participants proving the stated theorem in Lean.

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean`
contains a definition layer and exactly one theorem, stated in full and
"proved" by `sorry` inside a marked slot. **Prove that theorem.**

The theorem comes from algorithm analysis. A *distance order* of a
directed graph with a source `s` is a total order of the vertices in
which every vertex other than `s` has an incoming *forward arc* (an arc
from an earlier vertex); write `D` for the number of distance orders and
`F` for the maximum number of forward arcs of any distance order. The
theorem states: there is a constant `C > 0` such that on every directed
graph with `n > 2` vertices (all reachable from the source), Dijkstra
traces exist on every non-negative arc-length assignment; every Dijkstra
trace has time at most `C·(m + log₂ D)` and at most `C·(F + log₂ D)`
comparisons, where the costs are those of a heap with the working-set
bound; every correct time-model algorithm (decision trees with
incidence-list access) spends at least `(m + log₂ D)/C` time on some arc
lengths and representation; and every correct comparison-model algorithm
(linear-function decision trees) makes at least
`(F − n + 1 + log₂ D)/C` comparisons on some arc lengths. In other
words, Dijkstra's algorithm with a working-set-bound heap is universally
optimal in time, and universally optimal in comparisons up to an
additive term in `n`. An interval-DAG bound is given as the hypothesis
`hidag`.

The fixed trace definition records exactly one event for every outgoing arc
processed during a scan. An arc to an unlabeled vertex inserts it (`ins`);
an arc to a labeled, unscanned vertex performs a distance comparison
(`relax`), including when that comparison fails; an arc to an already
scanned vertex is skipped (`skip`) without a distance comparison. These
conditions ensure that `compCost` counts all comparisons outside the heap.

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
