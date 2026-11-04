set_option maxRecDepth 100000
set_option maxHeartbeats 0

/-!
# Packing 100 equal circles in the unit square: rational-center certificates

Fixed definition layer for the task `circles-in-square-n100-lean-open`.
Everything from the top of this file down to the line `-- END OF FIXED PART`
is part of the problem statement. The judge checks it verbatim; do not edit,
move, or delete it. Your work (auxiliary definitions, the point list, and
the proof of the claim) goes below the mark.

**The problem**: place 100 non-overlapping circles of equal radius `r`
inside the unit square `[0, 1] × [0, 1]`, making `r` as large as possible.
Proven optima exist only for `n ≤ 30` and `n = 36`; for `n = 100` there are
only best-known constructions, no optimality proof. The de-facto record
table is Eckard Specht's Packomania "csq" table
(<https://www.packomania.com/csq/csq.html>, header "Last update:
22-Aug-2022"), whose
`n = 100` row stands at

    r = 0.051401071774      (216 touching pairs; credited to a private
                             communication, reference [20] of the table)

A list of 100 rational centers with pairwise squared distance `≥ 4r²` and
every center in `[r, 1−r]²` is a machine-checkable certificate that the
optimal radius is `≥ r`. The naive 10×10 grid achieves `r = 1/20 = 0.05`
(the naive grid reference point); the printed table value is the published record; any verified `r`
strictly above it is a new world record.
-/

namespace CSQ100

/-- `distSq p q` is the squared Euclidean distance `‖p − q‖²` between two
rational points in the plane, in exact rational arithmetic (no floating
point anywhere). -/
def distSq (p q : Rat × Rat) : Rat :=
  (p.1 - q.1) * (p.1 - q.1) + (p.2 - q.2) * (p.2 - q.2)

/-- `isCircleConfig r S` is the computable predicate "the list `S` of
rational points, used as centers of circles of common radius `r`, forms a
valid packing of equal circles in the unit square":

1. the radius is positive: `0 < r`;
2. every center `p = (x, y)` of `S` sits in `[r, 1−r]²` — the boundary
   condition for a circle of radius `r` around `p` to stay inside
   `[0, 1]²` (together with clause 1 this forces `0 < x, y < 1`,
   subsuming the raw premise `0 ≤ x, y ≤ 1`);
3. for every pair of positions `i ≠ j` in `S`,
   `4r² ≤ ‖p_i − p_j‖²` — the circles do not overlap. The check runs in
   squared space so no square roots appear (squaring `2r ≤ ‖p_i − p_j‖`,
   both sides nonnegative).

This matches the checker of the solver sibling task
`circles-in-square-n100` clause by clause:

- the radius must be a positive decimal, exactly as clause 1;
- the boundary constraints `r ≤ x ≤ 1−r`, `r ≤ y ≤ 1−r` are clause 2,
  verbatim (the checker's separate premise `0 ≤ x, y ≤ 1` is implied by
  clauses 1–2);
- the pairwise constraint `(x_i − x_j)² + (y_i − y_j)² ≥ 4r²` is clause 3,
  verbatim; **duplicate points** need no clause of their own: two
  positions carrying the same point give squared distance `0 < 4r²` (as
  `r > 0`), so clause 3 already rejects every list with duplicates,
  exactly as the checker rejects them;
- clause 3 quantifies over **positions** (via `List.zipIdx`), so the
  diagonal cases `i = j` (where the inequality would read `4r² ≤ 0`) are
  excluded, while every pair of distinct positions is checked — the
  checker's `i < j` loop, read contrapositively;
- exactness: the checker parses decimal strings into exact rationals and
  compares in squared space with no floating-point tolerance; here the
  centers and `r` are `Rat` literals, parsed digit-by-digit by
  `OfScientific` — the same exact decimals (`0.05` *is* `1/20`).

The premise "exactly 100 centers" is pinned in the claim
(`S.length = 100`), exactly as the checker requires exactly 100 pairs.

All clauses live inside a single computable `Bool` function, so `decide` /
`native_decide` check concrete configurations directly and no per-clause
`Decidable` instance synthesis is involved. -/
def isCircleConfig (r : Rat) (S : List (Rat × Rat)) : Bool :=
  decide (0 < r) &&
    S.all (fun p => decide (r ≤ p.1 ∧ p.1 ≤ 1 - r ∧ r ≤ p.2 ∧ p.2 ≤ 1 - r)) &&
    S.zipIdx.all fun (p, i) =>
      S.zipIdx.all fun (q, j) =>
        i == j || decide (4 * r * r ≤ distSq p q)

/-- `CircleConfig r S` packages the computable predicate as the proposition
`isCircleConfig r S = true`.

Marked `@[reducible]` so that decidable instances for concrete point lists
are found by typeclass resolution (e.g. `by native_decide` can check
configurations directly). -/
@[reducible]
def CircleConfig (r : Rat) (S : List (Rat × Rat)) : Prop := isCircleConfig r S = true

-- END OF FIXED PART

/- Your work goes below. Prove the claim.

Rules (machine-checked):
- You may change only the decimal literal `r` in the claim statement
  (write it as a plain decimal: digits with at most one decimal point, no
  exponent notation); every other token of the claim lines must remain
  exactly as written, and the claim body must stay between its
  `-- CLAIM submission_lower BEGIN/END` markers.
- No `sorry` / `admit` outside the claim body (a claim whose body still
  contains one simply does not score), no `axiom` / `sorryAx`, and the
  fixed part above must stay verbatim. `native_decide` is allowed (the
  judge whitelists `Lean.ofReduceBool` and `Lean.trustCompiler`).
- Auxiliary definitions and lemmas between the fixed part and the claim
  (or after it) are free. Do not close `namespace CSQ100`.
- Representation hint: at the record region `r ≈ 0.051401071774` the judge
  scans 10000 ordered position pairs at a handful of rational operations
  each — any `List (Rat × Rat)` works. Bring centers as decimal literals,
  e.g. `(0.05, 0.15)`, or generate the list programmatically. Every
  decimal is an exact rational: `d` digits after the point mean a
  denominator of `10^d`. -/

theorem submission_lower : ∃ S : List (Rat × Rat), S.length = 100 ∧ CircleConfig 0.05 S := by
-- CLAIM submission_lower BEGIN
  sorry
-- CLAIM submission_lower END

end CSQ100
