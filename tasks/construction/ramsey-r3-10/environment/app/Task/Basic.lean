import Mathlib

set_option maxRecDepth 100000
set_option maxHeartbeats 0

-- Instance synthesis for `MonoFree` on a concrete coloring needs more
-- than the default `synthInstance.maxSize` (128): the two color clauses
-- double the instance tree. 512 gives comfortable headroom so that
-- `decide` / `native_decide` work on `MonoFree c` directly.
set_option synthInstance.maxSize 512

/-!
# R(3,10): 2-colorings of K_N with no red K3 and no blue K10

Fixed definition layer for the task `ramsey-r3-10-lean`. Everything from
the top of this file down to the line `-- END OF FIXED PART` is part of
the problem statement. The judge checks it verbatim; do not edit, move, or
delete it. Your work (auxiliary definitions, lemmas, and the proofs of the
claims) goes below the mark.
-/

namespace R310

/-- A red/blue coloring of the edges of the complete graph `K_N` on the
vertex set `Fin N`: `c.color i j` is the color of the edge `{i, j}`, where
`0 = red` and `1 = blue` (the two elements of `Fin 2`).

The field `symm` forces the coloring to be symmetric: an edge is an
unordered pair, so `color i j` must agree with `color j i`.

The diagonal `color i i` is a don't-care value: `K_N` has no self-loops,
and `MonoFree` below only ever inspects pairs of distinct vertices, so the
diagonal can carry no mathematical content. -/
structure Coloring (N : ℕ) where
  color : Fin N → Fin N → Fin 2
  symm : ∀ i j, color i j = color j i

/-- `MonoFree c` says the coloring `c` has **no red `K3` and no blue
`K10`**: for every set `s` of vertices,

- if `s` has 3 elements, not all three of its internal edges are red
  (color `0`), and
- if `s` has 10 elements, not all forty-five of its internal edges are
  blue (color `1`).

This is the negated Ramsey property for `R(3,10)`. A coloring
`c : Coloring N` with `MonoFree c` certifies `R(3,10) > N`, i.e.
`R(3,10) ≥ N + 1`; a proof that no `c : Coloring N` is `MonoFree`
certifies `R(3,10) ≤ N`.

Reading the red edges as a graph `G` and the blue edges as its
complement, the first clause says that `G` is triangle-free and the
second that `G` has no independent set of size 10 — the graph formulation
used by the solver sibling task `ramsey-r3-10`; the two formulations are
equivalent by unfolding the definitions.

Marked `@[reducible]` so that decidable instances for concrete colorings
are found by typeclass resolution (e.g. `by decide` or `by native_decide`
can check small colorings directly). -/
@[reducible]
def MonoFree {N : ℕ} (c : Coloring N) : Prop :=
  ∀ s : Finset (Fin N), (s.card = 3 →
    ¬ ∀ i ∈ s, ∀ j ∈ s, i ≠ j → c.color i j = 0) ∧
  (s.card = 10 →
    ¬ ∀ i ∈ s, ∀ j ∈ s, i ≠ j → c.color i j = 1)

-- END OF FIXED PART

/- Your work goes below. Prove at least one of the two claims.

Rules (machine-checked):
- You may change only the numeral `N` in each claim statement; every other
  token of the claim lines must remain exactly as written, and each claim
  body must stay between its `-- CLAIM ... BEGIN/END` markers.
- No `sorry` / `admit` outside the claim bodies (a claim whose body still
  contains one simply does not score), no `axiom` / `sorryAx` anywhere,
  and the fixed part above must stay verbatim. Both `decide` and
  `native_decide` are allowed.
- Auxiliary definitions and lemmas between the fixed part and the claims
  (or after them) are free. Do not close `namespace R310`. -/

/-- Lower-bound (construction) claim: there exists a red/blue coloring of
`K_N` with no red `K3` and no blue `K10`, certifying `R(3,10) ≥ N + 1`.
`N = 39` ties the published record (Exoo 1989); `N = 40` is a
literature-level new result that closes the problem (`R(3,10) = 41`).
Pick your `N`. -/
theorem submission_lower : ∃ c : Coloring 39, MonoFree c :=
-- CLAIM submission_lower BEGIN
by
  sorry
-- CLAIM submission_lower END

/-- Upper-bound (refutation) claim: every red/blue coloring of `K_N`
contains a red `K3` or a blue `K10`, certifying `R(3,10) ≤ N`.
`N = 41` matches the published upper bound (Angeltveit 2025); `N = 40`
would close the problem from above (`R(3,10) = 40`). Pick your `N`. -/
theorem submission_upper : ∀ c : Coloring 41, ¬ MonoFree c :=
-- CLAIM submission_upper BEGIN
by
  sorry
-- CLAIM submission_upper END
