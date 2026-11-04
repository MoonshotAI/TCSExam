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
unreachable there because both scoring thresholds are positive; it is
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
  rejects as duplicates (claims with `t ≥ 1` are vacuous and score 0
  anyway, since the scoring baseline is below `1`);
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

/- Oracle proof (judge-side; not part of the agent-facing stub): the
deterministic Coulomb-relaxation configuration of the solver sibling task
`spherical-code-d3-n50` (12000 fixed-schedule steps of pairwise
inverse-square repulsion from the Fibonacci-spiral seed, coordinates
truncated toward zero to 12 decimals — the same point set as
`/app/examples/example_relaxed50.json`). The same construction is the
oracle of the solver sibling, so the two editions score the same run at
the same value.

The coordinates below are the published decimal coordinates scaled by
10^12; the normalized inner product is invariant under positive rescaling
of each point, so this is the same spherical-code certificate. Its exact
maximal normalized inner product is `p* = 0.87705060493286680...`
(witness pair (31, 47)), and the claimed threshold is the exact rational
ceiling of `p*` at 15 decimals, `T = 877050604932867/10^15` — the ceiling
was verified by exact integer arithmetic (`num^2 <= T^2 * den2` for every
pair, computed with big-integer fractions). Expected score:
((0.9045852811944625 - T) / (0.9045852811944625 - 0.868173209126))^3
≈ 0.432418, printed floored to 0.432417 (milestone "progress") —
identical construction and printed score to the solver edition's oracle,
cross-validating predicate alignment between editions. -/

/-- One coordinate: an exact 12-decimal rational given by its scaled
integer numerator, `sc x = x / 10^12`. -/
def sc (x : Int) : Rat := (x : Rat) / 1000000000000

/-- A point of `Q^3` from three scaled-integer coordinates. -/
def pt (x y z : Int) : Fin 3 → Rat := fun k => ([sc x, sc y, sc z].getD k.val 0)

/-- The 50-point relaxed configuration (see the comment above). -/
def relaxed50 : List (Fin 3 → Rat) :=
  [
    pt (-653753062838) (-380868828483) (653869916969),
    pt (314978553369) (-942644658718) (110496870125),
    pt (985490942422) (106757932097) (131948271442),
    pt (372116334321) (574060955184) (729371958237),
    pt (675330756264) (501637763) (-737514825615),
    pt (-187977088472) (276457803290) (-942462570720),
    pt (677592463414) (-713988407107) (-176320753285),
    pt (-879709043584) (-428964840312) (205185682764),
    pt (898189057814) (-269781109552) (-347094467472),
    pt (472995437203) (101570554725) (875190687106),
    pt (-671433330473) (49166983914) (-739432140511),
    pt (-576477649810) (-505851574233) (-641706867747),
    pt (364706755591) (-455987611354) (811827740790),
    pt (-453428364652) (31194640043) (890746660145),
    pt (-839430265796) (499338090832) (214518763535),
    pt (31324545412) (-112179011391) (993194161409),
    pt (234137567464) (-887912957346) (-395967397241),
    pt (-71343855144) (800584248497) (594957910604),
    pt (-882008729815) (297523087410) (-365432090801),
    pt (-657247093272) (722921287577) (-213098733813),
    pt (-70038057932) (388073228750) (918963459321),
    pt (-202206960075) (-526941106654) (825497071717),
    pt (-898137659221) (-273362666378) (-344414862801),
    pt (534112207534) (-521158578618) (-665671004096),
    pt (-183993915031) (-981856198591) (45876404820),
    pt (-279324698660) (-856700105768) (-433638837622),
    pt (360420206524) (898165009388) (-251787391739),
    pt (-281341978099) (-219426585142) (-934183421545),
    pt (-456039959076) (856216679539) (242735562710),
    pt (905247246519) (245957829582) (-346456589972),
    pt (231875860314) (-173422912475) (-957161469571),
    pt (470695750972) (828058482447) (304572913540),
    pt (55195392100) (725548802887) (-685953645168),
    pt (786773795210) (-161710138351) (595681816345),
    pt (907264525959) (-391315691042) (154087993950),
    pt (60145072635) (-838091957324) (542203321002),
    pt (27830514979) (991611104669) (126225510625),
    pt (-998038882181) (36681321000) (50723469358),
    pt (593007207643) (582762556455) (-555635001125),
    pt (-534112207534) (521158578618) (665671004096),
    pt (-668958490206) (-732653396191) (-125353657426),
    pt (11279265913) (-617630210030) (-786387755384),
    pt (596990381084) (-675551445425) (432703974415),
    pt (-480047220328) (568530765791) (-668077416624),
    pt (782797194485) (385905820815) (488165186967),
    pt (-475760671261) (-785621854950) (395537715906),
    pt (-838124468584) (86827071085) (538524312252),
    pt (784298954942) (620110241754) (-18396666740),
    pt (-206806332536) (926034748790) (-315738475412),
    pt (310943994490) (331902382532) (-890592297720)
  ]

theorem submission_upper : ∃ S : List (Fin 3 → Rat), S.length = 50 ∧ SphericalCodeUpper S 877050604932867 1000000000000000 := by
-- CLAIM submission_upper BEGIN
  exact ⟨relaxed50, by native_decide, by native_decide⟩
-- CLAIM submission_upper END

end SCN50
