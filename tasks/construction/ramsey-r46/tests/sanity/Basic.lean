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

/- Sanity fixture (tests/sanity): a verified legal coloring at N = 14.
The construction is a 14-vertex induced subgraph of the solver
sibling ramsey-r46's shipped N = 24 baseline graph
(`environment/examples/example_n24.json`, deterministic starter
`local_search.py 24 1`); any induced subgraph of a `(4,6)-free` graph
is again `(4,6)-free`. Both the symmetry field and `MonoFree` are
discharged by `native_decide` (allowed in this task; the axiom
whitelist includes Lean.ofReduceBool and Lean.trustCompiler). The
MonoFree check is bridged to two `∀ s ∈ Finset.powersetCard k, ...`
clauses, each checked by its own `native_decide` call. -/

/-- The red edges of the sibling's baseline graph induced on vertices
`0 .. 13`, each pair listed once as `(min, max)`. 37 edges. -/
def redEdges14 : List (ℕ × ℕ) :=
  [
    (0, 1), (0, 5), (0, 6), (0, 9), (0, 10), (1, 2),
    (1, 4), (1, 5), (1, 7), (1, 9), (1, 10), (1, 12),
    (1, 13), (2, 5), (3, 4), (3, 8), (3, 9), (4, 10),
    (5, 8), (5, 12), (5, 13), (6, 8), (6, 9), (6, 10),
    (6, 11), (6, 12), (7, 8), (7, 9), (7, 10), (7, 11),
    (7, 12), (8, 11), (8, 13), (9, 11), (9, 13), (11, 12),
    (11, 13)  ]

/-- The induced subgraph as a coloring: edge `{i, j}` is red (`0`) iff
the normalized pair `(min, max)` appears in `redEdges14`, blue (`1`)
otherwise. Symmetry holds because the pair is normalized before
lookup. -/
def ex14 : Coloring 14 where
  color i j :=
    if redEdges14.contains (min i.val j.val, max i.val j.val) then 0
    else 1
  symm := by native_decide

/-- Bridge: `MonoFree` (fixed definition, quantified over all subsets
with cardinality guards) is equivalent to the same two clauses
quantified over `Finset.powersetCard` only. The right-hand side is kept
as two inline `∀ s ∈ ...` clauses (no auxiliary definition) so that
typeclass resolution synthesizes their `Decidable` instances. -/
theorem monoFree_iff (c : Coloring 14) :
    MonoFree c ↔
      (∀ s ∈ (Finset.univ : Finset (Fin 14)).powersetCard 4,
        ¬ ∀ i ∈ s, ∀ j ∈ s, i ≠ j → c.color i j = 0) ∧
      (∀ s ∈ (Finset.univ : Finset (Fin 14)).powersetCard 6,
        ¬ ∀ i ∈ s, ∀ j ∈ s, i ≠ j → c.color i j = 1) := by
  unfold MonoFree
  constructor
  · intro h
    constructor
    · intro s hs
      exact (h s).1 (Finset.mem_powersetCard.mp hs).2
    · intro s hs
      exact (h s).2 (Finset.mem_powersetCard.mp hs).2
  · rintro ⟨h4, h6⟩ s
    exact ⟨fun hs => h4 s (Finset.mem_powersetCard.mpr
             ⟨Finset.subset_univ s, hs⟩),
           fun hs => h6 s (Finset.mem_powersetCard.mpr
             ⟨Finset.subset_univ s, hs⟩)⟩

/-- The red side of the check, by exhaustive native computation over
the `C(14,4) = 1,001` four-subsets. -/
theorem ex14_noRedK4 :
    (∀ s ∈ (Finset.univ : Finset (Fin 14)).powersetCard 4,
      ¬ ∀ i ∈ s, ∀ j ∈ s, i ≠ j → ex14.color i j = 0) := by
  native_decide

/-- The blue side, over the `C(14,6) = 3,003` six-subsets. -/
theorem ex14_noBlueK6 :
    (∀ s ∈ (Finset.univ : Finset (Fin 14)).powersetCard 6,
      ¬ ∀ i ∈ s, ∀ j ∈ s, i ≠ j → ex14.color i j = 1) := by
  native_decide

/-- The induced subgraph is `(4,6)-free`. -/
theorem ex14_free : MonoFree ex14 :=
  (monoFree_iff ex14).mpr ⟨ex14_noRedK4, ex14_noBlueK6⟩

/-- Lower-bound (construction) claim: there exists a red/blue coloring
of `K_N` with no red `K4` and no blue `K6`, certifying `R(4,6) ≥ N + 1`.
`N = 35` ties the published record (Exoo 2012); `N = 36` is a
literature-level new result. Pick your `N`. -/
theorem submission_lower : ∃ c : Coloring 14, MonoFree c :=
-- CLAIM submission_lower BEGIN
⟨ex14, ex14_free⟩
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
