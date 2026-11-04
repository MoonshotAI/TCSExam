set_option maxRecDepth 100000
set_option maxHeartbeats 0

/-!
# Kissing number in dimension 9: integer kissing configurations in Z^9

Fixed definition layer for the task `kissing-d9-lean-open`. Everything from
the top of this file down to the line `-- END OF FIXED PART` is part of the
problem statement. The judge checks it verbatim; do not edit, move, or
delete it. Your work (auxiliary definitions, lemmas, the point list, and
the proof of the claim) goes below the mark.

The **kissing number** in dimension 9 is the largest number of unit spheres
that can simultaneously touch a central unit sphere in `R^9` without
overlapping one another; equivalently, the largest number of points that
can be placed on the unit sphere `S^8` with every pair separated by an
angle of at least 60°. The published interval is

    306 <= kissing number <= 363

(lower bound: J. Leech & N. J. A. Sloane, *Sphere packings and
error-correcting codes*, Canadian Journal of Mathematics 23 (1971),
718–745; upper bound: F. C. Machado & F. M. de Oliveira Filho,
*Improving the semidefinite programming bound for the kissing number by
exploiting polynomial symmetry*, Experimental Mathematics 27 (2018),
362–369). A valid configuration of `n` points certifies
`kissing number >= n`; `n = 306` ties the standing record, and
`n >= 307` is a literature-level new result.
-/

namespace KD9

/-- `normSq x` is the squared Euclidean norm `‖x‖²` of an integer vector in
`Z^9`: the sum of the squares of its nine coordinates, in exact integer
arithmetic (no floating point anywhere). -/
def normSq (x : Fin 9 → Int) : Int :=
  (List.finRange 9).foldl (fun s i => s + x i * x i) 0

/-- `distSq x y` is the squared Euclidean distance `‖x − y‖²` between two
integer vectors in `Z^9`, in exact integer arithmetic. -/
def distSq (x y : Fin 9 → Int) : Int :=
  (List.finRange 9).foldl (fun s i => s + (x i - y i) * (x i - y i)) 0

/-- `isKissingConfig S` is the computable predicate "the list `S` of integer
vectors in `Z^9` forms a valid kissing configuration":

1. `S` is nonempty;
2. every point of `S` is nonzero;
3. for every pair of positions `i ≠ j` in `S`,
   `M ≤ ‖x_i − x_j‖²`, where `M = max_z ‖z‖²` is the largest squared norm
   in `S` — i.e. `max ‖x‖² ≤ min ‖x − y‖²` over distinct points.

This matches the checker of the solver sibling task `kissing-d9` clause by
clause:

- the **zero vector** is rejected by clause 2 (the radial-projection
  argument needs nonzero vectors), exactly as the checker rejects it;
- **duplicate points** need no clause of their own: two positions carrying
  the same (nonzero) point give `‖x_i − x_j‖² = 0 < M`, so clause 3
  already rejects every list with duplicates, exactly as the checker
  rejects them;
- clause 3 quantifies over **positions** (via `List.zipIdx`), so the
  diagonal cases `i = j` (where the inequality would read `M ≤ 0`) are
  excluded, while every pair of distinct positions is checked — the
  checker's `‖x − y‖² < max_z ‖z‖²` rejection, read contrapositively.

All clauses live inside a single computable `Bool` function, so `decide` /
`native_decide` check concrete configurations directly and no per-clause
`Decidable` instance synthesis is involved.

A computable `isKissingConfig S = true` (packaged as `KissingConfig S`)
together with `n ≤ S.length` is a machine-checkable certificate that the
9-dimensional kissing number is at least `S.length`, hence at least `n`.
Write `M = max ‖x‖²` and `m = min ‖x − y‖²`, so `M ≤ m`, and rescale all
points by `1/sqrt(m)`: then every pairwise distance is `≥ 1` and every
norm is `≤ 1`. For two points with `a = ‖x‖ ≤ b = ‖y‖ ≤ 1`,

    cos(angle(x,y)) = (a² + b² − ‖x−y‖²) / (2ab)
                    ≤ (a² + b² − 1) / (2ab) ≤ 1/2,

where the last step uses `a² − ab + b² = b² − a(b − a) ≤ b² ≤ 1`. So every
pairwise angle is at least 60°, and projecting the `S.length` nonzero
points radially onto the unit sphere (they are nonzero, so the projection
is defined) places `S.length` non-overlapping unit spheres around a
central one. -/
def isKissingConfig (S : List (Fin 9 → Int)) : Bool :=
  let M := S.foldl (fun m x => if m < normSq x then normSq x else m) 0
  decide (0 < S.length) &&
    S.all (fun x => normSq x != 0) &&
    S.zipIdx.all fun (x, i) =>
      S.zipIdx.all fun (y, j) =>
        i == j || decide (M ≤ distSq x y)

/-- `KissingConfig S` packages the computable predicate as the proposition
`isKissingConfig S = true`.

Marked `@[reducible]` so that decidable instances for concrete point lists
are found by typeclass resolution (e.g. `by native_decide` can check
configurations directly). -/
@[reducible]
def KissingConfig (S : List (Fin 9 → Int)) : Prop := isKissingConfig S = true

-- END OF FIXED PART

/- Your work goes below. Prove the claim.

Rules (machine-checked):
- You may change only the numeral `n` in the claim statement; every other
  token of the claim lines must remain exactly as written, and the claim
  body must stay between its `-- CLAIM submission_lower BEGIN/END` markers.
- No `sorry` / `admit` outside the claim body (a claim whose body still
  contains one simply does not score), no `axiom` / `sorryAx`, and the
  fixed part above must stay verbatim. `native_decide` is allowed (the
  judge whitelists `Lean.ofReduceBool` and `Lean.trustCompiler`).
- Auxiliary definitions and lemmas between the fixed part and the claim
  (or after it) are free. Do not close `namespace KD9`.
- Representation hint: the record region is `n ≈ 306`, where the judge
  scans ~94k ordered point pairs at nine integer operations each — any
  `List` of points works. Write points through a small helper, e.g.
  `def pt (v : List Int) : Fin 9 → Int := fun k => v.getD k.val 0`, or
  generate the list programmatically. -/

theorem submission_lower : ∃ S : List (Fin 9 → Int), S.length ≥ 18 ∧ KissingConfig S := by
-- CLAIM submission_lower BEGIN
  sorry
-- CLAIM submission_lower END

end KD9
