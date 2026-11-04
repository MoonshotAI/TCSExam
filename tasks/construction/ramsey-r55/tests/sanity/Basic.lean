import Mathlib

set_option maxRecDepth 100000
set_option maxHeartbeats 0

/-!
# R(5,5): 2-colorings of K_N with no monochromatic K5

Fixed definition layer for the task `ramsey-r55-lean`. Everything from the
top of this file down to the line `-- END OF FIXED PART` is part of the
problem statement. The judge checks it verbatim; do not edit, move, or
delete it. Your work (auxiliary definitions, lemmas, and the proofs of the
claims) goes below the mark.
-/

namespace R55

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

/-- `MonoFree c` says the coloring `c` has **no monochromatic `K5`**: for
every 5-element set `s` of vertices, there is no color `col` such that all
ten edges inside `s` have color `col`.

This is the negated Ramsey property. A coloring `c : Coloring N` with
`MonoFree c` certifies `R(5,5) > N`, i.e. `R(5,5) ≥ N + 1`; a proof that
no `c : Coloring N` is `MonoFree` certifies `R(5,5) ≤ N`.

Marked `@[reducible]` so that decidable instances for concrete colorings
are found by typeclass resolution (e.g. `by decide` can check small
colorings directly). -/
@[reducible]
def MonoFree {N : ℕ} (c : Coloring N) : Prop :=
  ∀ s : Finset (Fin N), s.card = 5 →
    ¬ ∃ col : Fin 2, ∀ i ∈ s, ∀ j ∈ s, i ≠ j → c.color i j = col

-- END OF FIXED PART

/- Sanity fixture (tests/sanity): a verified legal coloring at N = 13.
The Paley coloring: edge {i,j} is red iff (j - i) mod 13 is a nonzero
quadratic residue mod 13. The Paley graph on 13 vertices is
self-complementary with clique number 3, so neither color contains a K5. -/

/-- The nonzero quadratic residues mod 13, closed under negation. -/
def qr13 : List ℕ := [1, 3, 4, 9, 10, 12]

/-- The Paley 2-coloring of K_13. -/
def paley13 : Coloring 13 where
  color := fun i j => if ((j.val + 13 - i.val) % 13) ∈ qr13 then 0 else 1
  symm := by decide

theorem submission_lower : ∃ c : Coloring 13, MonoFree c :=
-- CLAIM submission_lower BEGIN
by
  exact ⟨paley13, by decide⟩
-- CLAIM submission_lower END

theorem submission_upper : ∀ c : Coloring 46, ¬ MonoFree c :=
-- CLAIM submission_upper BEGIN
by
  sorry
-- CLAIM submission_upper END
