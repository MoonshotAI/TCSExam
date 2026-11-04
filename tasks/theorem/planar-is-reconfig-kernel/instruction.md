# Task: Linear kernel for independent-set reconfiguration in planar graphs

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean`
contains a definition layer and exactly one theorem, stated in full and
"proved" by `sorry` inside a marked slot. **Prove that theorem.**

The theorem comes from graph reconfiguration. An independent set in a
graph is a set of vertices no two of which are adjacent; picture a token
on each of its vertices. In the *token jumping* (TJ) model, one step
removes a single token from its vertex and places it on any other
vertex, provided the result is again an independent set. The ISR-TJ
problem asks, given a graph `G` and two size-`k` independent sets `Is`,
`It`, whether a sequence of such jumps transforms `Is` into `It`. A
*kernel* is a compression of the instance to an equivalent one whose
size is bounded by a function of `k` alone. Write `X := Is ∪ It` for the
*key vertices*; the vertices outside `X` are grouped into *projection
classes* by their neighborhood inside `X`, and `N2`/`N3` count the
nonempty classes on exactly 2, respectively at least 3, key vertices.
The theorem states:

> Fix `1 ≤ r` and `1 ≤ k`. Let `G` be a finite simple graph with no
> `K_{3,r}` minor, given together with a proper coloring with
> `max{r,6300} + 3` colors and with the bound
> `N2(G) + N3(G) ≤ 2^{5r+13}·(r+3)^{2r+5}·k`. Let `Is`, `It` be
> independent sets of size `k`. Then there is a vertex set `W ⊇ X` with
> `|W| ≤ K(r)·k`, where
> `K(r) = 2 + q + (r−1)·B + q·(B·(4r−1)+1)` for `q = max{r,6300}+3` and
> `B = 2^{5r+13}·(r+3)^{2r+5}`, such that `Is` reconfigures into `It`
> under token jumping if and only if it does so using only vertices of
> `W`.

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
`isr_tj_linear_kernel` stays within the standard axioms
(`propext`, `Classical.choice`, `Quot.sound`); otherwise `0.0`.

## Notes

- Time budget: you have up to **12 hours** of wall-clock time for this task; the run is terminated when it expires.
