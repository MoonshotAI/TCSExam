set_option maxRecDepth 100000
set_option maxHeartbeats 0

-- Instance synthesis on the concrete Rat comparisons inside the predicate
-- below walks a deeper instance tree than the default `synthInstance.maxSize`
-- (128) is sized for; 512 gives comfortable headroom so that `decide` /
-- `native_decide` work on concrete certificates directly.
set_option synthInstance.maxSize 512

/-!
# The Tammes problem at N = 50: rational spherical codes in Q^3

Fixed definition layer for the task `spherical-code-d3-n50-lean-open`.
Everything from the top of this file down to the line `-- END OF FIXED PART`
is part of the problem statement. The judge checks it verbatim; do not edit,
move, or delete it. Your work (auxiliary definitions, lemmas, the point list,
and the proof of the claim) goes below the mark.

The **Tammes problem** asks for the largest possible minimal angle between
`N` points on the unit sphere `S^2`; equivalently, since the cosine
decreases as the angle grows, for the smallest possible maximal pairwise
cosine. For `N = 50` the problem is open: the best known configuration
(E. Szekely, *Sur le probleme de Tammes*, Annales Universitatis
Scientiarum Budapestinensis 17 (1974), 157–175) has maximal pairwise
cosine

    r* = 0.868173209126897451...   (an algebraic number: the relevant root
                                    of 386x^12 + 1679x^11 + 6433x^10 - 743x^9
                                    - 2287x^8 - 19290x^7 + 8490x^6 + 19170x^5
                                    - 5580x^4 - 6885x^3 - 1755x^2 + 2997x - 567)

tracked by Henry Cohn's spherical code table (<https://spherical-codes.org/>)
as the rounded-up value 0.868173209127. A certified 50-point configuration
with maximal normalized pairwise inner product `<= T` proves that the
optimum is `<= T`; any `T < r*` is a literature-level new result.

Rational points cannot lie exactly on the unit sphere, so the certificate
works with **directions**: 50 nonzero rational vectors, compared by the
normalized inner product `<a,b> / (|a| * |b|)` — the cosine of the angle,
which is exactly the quality of the spherical code obtained by projecting
the vectors radially onto `S^2` (the projection is defined because every
vector is nonzero, and projection never changes the normalized inner
products).
-/

namespace SCN50

/-- `normSq x` is the squared Euclidean norm `‖x‖²` of a rational vector in
`Q^3`: the sum of the squares of its three coordinates, in exact rational
arithmetic (no floating point anywhere). -/
def normSq (x : Fin 3 → Rat) : Rat :=
  (List.finRange 3).foldl (fun s i => s + x i * x i) 0

/-- `dot x y` is the inner product `⟨x, y⟩` of two rational vectors in
`Q^3`, in exact rational arithmetic. -/
def dot (x y : Fin 3 → Rat) : Rat :=
  (List.finRange 3).foldl (fun s i => s + x i * y i) 0

/-- `cosLe x y t` is the computable predicate "the normalized inner product
of `x` and `y` is at most `t`":

    ⟨x, y⟩ / (‖x‖ * ‖y‖) ≤ t      (for nonzero `x`, `y`)

decided in exact rational arithmetic — no square roots are ever taken. The
comparison is done on squared quantities, and the sign cases are:

- if `0 ≤ t`: a nonpositive inner product gives cosine `≤ 0 ≤ t`
  immediately (true); a positive inner product is compared by squaring,
  `⟨x,y⟩² ≤ t² · ‖x‖²‖y‖²` — both sides are nonnegative, so squaring
  preserves the order;
- if `t < 0`: the cosine must be negative, so `⟨x,y⟩ < 0` is required, and
  for two negative numbers squaring reverses the order:
  `t² · ‖x‖²‖y‖² ≤ ⟨x,y⟩²`.

This is exactly the comparison the checker of the solver sibling task
`spherical-code-d3-n50` performs against its (positive) thresholds — its
`cmp_cos_vs_rational` returns "below threshold" immediately for a
nonpositive inner product and otherwise compares `num²` against
`t² · den2` with big-integer arithmetic. The negative-`t` branch is
unreachable there because both thresholds are positive; it is
needed here because `t` is a free parameter of the claim. -/
def cosLe (x y : Fin 3 → Rat) (t : Rat) : Bool :=
  let d := dot x y
  let den2 := normSq x * normSq y
  if 0 ≤ t then
    decide (d ≤ 0) || decide (d * d ≤ t * t * den2)
  else
    decide (d < 0) && decide (t * t * den2 ≤ d * d)

/-- `isSphericalCode S t` is the computable predicate "the list `S` of
rational vectors in `Q^3` forms a valid spherical-code certificate at
threshold `t`":

1. every point of `S` is nonzero;
2. for every pair of positions `i ≠ j` in `S`, the normalized inner product
   of `x_i` and `x_j` is at most `t` (`cosLe`).

This matches the checker of the solver sibling task
`spherical-code-d3-n50` clause by clause:

- the **zero vector** is rejected by clause 1 (its direction, hence its
  angle to anything, is undefined), exactly as the checker rejects it;
- **duplicate points** need no clause of their own: two positions carrying
  the same nonzero point have normalized inner product `1`, which clause 2
  rejects whenever `t < 1` — exactly the configurations the checker
  rejects as duplicates (claims with `t ≥ 1` are vacuous anyway);
- clause 2 quantifies over **positions** (via `List.zipIdx`), so the
  diagonal cases `i = j` (where the cosine is `1`) are excluded, while
  every pair of distinct positions is checked — the checker's all-pairs
  loop over 1225 unordered pairs, read contrapositively;
- the premise "exactly 50 points" is pinned in the claim
  (`S.length = 50`), exactly as the checker requires exactly 50 points;
- the checker's unit-ball constraint `‖v‖² ≤ 1` has no counterpart here by
  design: the normalized inner product is invariant under positive
  rescaling of each point, so a configuration in the ball and its radial
  projection are the same certificate — dropping the ball constraint
  changes neither the certified bound nor the accepted configurations.

All clauses live inside a single computable `Bool` function, so `decide` /
`native_decide` check concrete configurations directly and no per-clause
`Decidable` instance synthesis is involved.

A computable `isSphericalCode S t = true` (packaged as
`SphericalCodeUpper S num den`, where `t = num/den`) together with
`S.length = 50` is a machine-checkable certificate that the optimal
maximal cosine for `N = 50` is at most `t`: project the 50 nonzero vectors
radially onto `S^2` (defined, since they are nonzero) — for `t < 1` the
projections are 50 distinct points (equal projections would have cosine
`1 > t`), and every pairwise cosine is at most `t`, so the minimal angle
is at least `arccos t`. -/
def isSphericalCode (S : List (Fin 3 → Rat)) (t : Rat) : Bool :=
  S.all (fun x => normSq x != 0) &&
    S.zipIdx.all fun (x, i) =>
      S.zipIdx.all fun (y, j) =>
        i == j || cosLe x y t

/-- `SphericalCodeUpper S num den` packages the computable predicate as the
proposition `isSphericalCode S (num/den) = true`.

Marked `@[reducible]` so that decidable instances for concrete point lists
are found by typeclass resolution (e.g. `by native_decide` can check
configurations directly). -/
@[reducible]
def SphericalCodeUpper (S : List (Fin 3 → Rat)) (num den : Nat) : Prop :=
  isSphericalCode S ((num : Rat) / (den : Rat)) = true

-- END OF FIXED PART

/- Your work goes below. Prove the claim.

Rules (machine-checked):
- You may change only the two numerals `num` and `den` in the claim
  statement — the threshold is the rational `t = num/den`, smaller is
  better; every other token of the claim lines must remain exactly as
  written, and the claim body must stay between its
  `-- CLAIM submission_upper BEGIN/END` markers.
- No `sorry` / `admit` outside the claim body (a claim whose body still
  contains one simply does not score), no `axiom` / `sorryAx`, and the
  fixed part above must stay verbatim. `native_decide` is allowed (the
  judge whitelists `Lean.ofReduceBool` and `Lean.trustCompiler`).
- Auxiliary definitions and lemmas between the fixed part and the claim
  (or after it) are free. Do not close `namespace SCN50`.
- Claims are evaluated only for `0 < num/den ≤ 1`. Representation
  hint: at the record region `t ≈ 0.868173209126` the check scans 2500
  ordered position pairs in exact rational arithmetic — any `List` of
  points works. Write points through a small helper, e.g.
  `def pt (x y z : Int) : Fin 3 → Rat := fun k => ([x, y, z].getD k.val 0 : Rat)`,
  with coordinates scaled to integers (the normalized inner product is
  invariant under positive rescaling of each point), or generate the list
  programmatically. -/

theorem submission_upper : ∃ S : List (Fin 3 → Rat), S.length = 50 ∧ SphericalCodeUpper S 9045852811944625 10000000000000000 := by
-- CLAIM submission_upper BEGIN
  sorry
-- CLAIM submission_upper END

end SCN50
