import Mathlib

set_option maxRecDepth 100000
set_option maxHeartbeats 0

-- Instance synthesis for `MonoFree` on a concrete coloring needs more
-- than the default `synthInstance.maxSize` (128): the two color clauses
-- double the instance tree. 512 gives comfortable headroom so that
-- `decide` / `native_decide` work on `MonoFree c` directly.
set_option synthInstance.maxSize 512

/-!
# R(4,6): 2-colorings of K_N with no red K4 and no blue K6

Fixed definition layer for the task `ramsey-r46-lean`. Everything from
the top of this file down to the line `-- END OF FIXED PART` is part of
the problem statement. The judge checks it verbatim; do not edit, move,
or delete it. Your work (auxiliary definitions, lemmas, and the proofs
of the claims) goes below the mark.
-/

namespace R46

/-- A red/blue coloring of the edges of the complete graph `K_N` on the
vertex set `Fin N`: `c.color i j` is the color of the edge `{i, j}`,
where `0 = red` and `1 = blue` (the two elements of `Fin 2`).

The field `symm` forces the coloring to be symmetric: an edge is an
unordered pair, so `color i j` must agree with `color j i`.

The diagonal `color i i` is a don't-care value: `K_N` has no self-loops,
and `MonoFree` below only ever inspects pairs of distinct vertices, so
the diagonal can carry no mathematical content. -/
structure Coloring (N : ℕ) where
  color : Fin N → Fin N → Fin 2
  symm : ∀ i j, color i j = color j i

/-- `MonoFree c` says the coloring `c` has **no red `K4` and no blue
`K6`**: for every set `s` of vertices,

- if `s` has 4 elements, not all six of its internal edges are red
  (color `0`), and
- if `s` has 6 elements, not all fifteen of its internal edges are
  blue (color `1`).

This is the negated Ramsey property for `R(4,6)`. A coloring
`c : Coloring N` with `MonoFree c` certifies `R(4,6) > N`, i.e.
`R(4,6) ≥ N + 1`; a proof that no `c : Coloring N` is `MonoFree`
certifies `R(4,6) ≤ N`.

Reading the red edges as a graph `G` and the blue edges as its
complement, the first clause says that `G` is `K4`-free and the second
that `G` has no independent set of size 6 — the graph formulation used
by the solver sibling task `ramsey-r46`; the two formulations are
equivalent by unfolding the definitions.

Marked `@[reducible]` so that decidable instances for concrete
colorings are found by typeclass resolution (e.g. `by decide` or
`by native_decide` can check small colorings directly). -/
@[reducible]
def MonoFree {N : ℕ} (c : Coloring N) : Prop :=
  ∀ s : Finset (Fin N), (s.card = 4 →
    ¬ ∀ i ∈ s, ∀ j ∈ s, i ≠ j → c.color i j = 0) ∧
  (s.card = 6 →
    ¬ ∀ i ∈ s, ∀ j ∈ s, i ≠ j → c.color i j = 1)

-- END OF FIXED PART

/- Your work goes below. Prove at least one of the two claims.

Rules (machine-checked):
- You may change only the numeral `N` in each claim statement; every
  other token of the claim lines must remain exactly as written, and
  each claim body must stay between its `-- CLAIM ... BEGIN/END` markers.
- No `sorry` / `admit` outside the claim bodies (a claim whose body
  still contains one simply does not score), no `axiom` / `sorryAx`
  anywhere, and the fixed part above must stay verbatim. Both `decide`
  and `native_decide` are allowed.
- Auxiliary definitions and lemmas between the fixed part and the
  claims (or after them) are free. Do not close `namespace R46`. -/

/-- Lower-bound (construction) claim: there exists a red/blue coloring
of `K_N` with no red `K4` and no blue `K6`, certifying `R(4,6) ≥ N + 1`.
`N = 35` ties the published record (Exoo 2012); `N = 36` is a
literature-level new result. Pick your `N`. -/
theorem submission_lower : ∃ c : Coloring 36, MonoFree c :=
-- CLAIM submission_lower BEGIN
by
  sorry
-- CLAIM submission_lower END

/-- Upper-bound (refutation) claim: every red/blue coloring of `K_N`
contains a red `K4` or a blue `K6`, certifying `R(4,6) ≤ N`.
`N = 41` matches the published upper bound (McKay–Radziszowski 1997);
`N = 40` matches the sharpest survey-reported claim
(Angeltveit–McKay 2024, personal communication) and already beats the
published record. Pick your `N`. -/
theorem submission_upper : ∀ c : Coloring 41, ¬ MonoFree c :=
-- CLAIM submission_upper BEGIN
by
  sorry
-- CLAIM submission_upper END
