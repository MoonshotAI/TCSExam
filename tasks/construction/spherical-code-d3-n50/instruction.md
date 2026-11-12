# Task: The Tammes problem for 50 points — Open Construction

How do you place 50 points on the unit sphere so that the closest pair is
as far apart as possible? This is the **Tammes problem** for `N = 50`:
originally asked by the botanist P. M. L. Tammes in 1930 (the points model
pollen-grain pores), it is the classical problem of *spherical codes* —
configurations on the sphere maximizing the minimal angle between any two
points. Equivalently, since the cosine decreases as the angle grows:

    maximize  theta_min  =  min over pairs of the angular distance
<=>
    minimize  p  =  max over pairs  <a, b> / (||a|| * ||b||)   (the maximal
                   cosine, a.k.a. max inner product; smaller is better)

Despite its simple statement, exact optima are rare. In 3 dimensions the
proven cases are only `N <= 14` and `N = 24` (Fejes Toth). From `N = 15`
on — including `N = 50` — every case is open: we only have a best-known
construction, not a proof.

The best-known values are tracked by **Henry Cohn's spherical code
table**, <https://spherical-codes.org/>. For `N = 50` the table lists

    max inner product = 0.868173209127

from E. Szekely, *Sur le probleme de Tammes*, Annales Universitatis
Scientiarum Budapestinensis 17 (1974), 157–175 — a construction that has
stood for over 50 years. The table also publishes the minimal polynomial
of its cosine,

    386x^12 + 1679x^11 + 6433x^10 - 743x^9 - 2287x^8 - 19290x^7 + 8490x^6
    + 19170x^5 - 5580x^4 - 6885x^3 - 1755x^2 + 2997x - 567 = 0,

whose relevant root is the true record value
`r* = 0.8681732091268974516747...`. Note that the printed table value is
`r*` rounded **up** to 12 decimals — this matters for the precision rules
below.

Only the construction direction is certifiable: every valid configuration
is an explicit certificate of `optimum <= T`. A certified configuration
whose maximal normalized pairwise inner product is below the record line
is a literature-level new result, beating a record that has stood since
1974.

## What's in `/app/Task/Basic.lean`

In `/app/Task/Basic.lean`, below the line `-- END OF FIXED PART`, prove
the claim `submission_upper`:

```lean
theorem submission_upper : ∃ S : List (Fin 3 → Rat), S.length = 50 ∧ SphericalCodeUpper S num den := by
```

where **you choose the two numerals `num` and `den`** — the threshold is
the rational `T = num/den`, and **the smaller the better**. You may change
**only** the two numerals in the claim statement; the claim body must stay
between its `-- CLAIM submission_upper BEGIN/END` markers. The judge
accepts the claim only for `0 < T <= 1`.

The fixed definition layer (do not modify the code) gives you:

- `normSq x : Rat` — the squared norm `‖x‖²` of a rational vector in `Q^3`
  (sum of the three squared coordinates, exact rational arithmetic);
- `dot x y : Rat` — the inner product `⟨x, y⟩`;
- `cosLe x y t : Bool` — the computable predicate "the normalized inner
  product `⟨x,y⟩ / (‖x‖·‖y‖)` is at most `t`", decided in exact rational
  arithmetic with **no square roots**: for `t ≥ 0` a nonpositive inner
  product passes immediately and a positive one is compared by squaring
  (`⟨x,y⟩² ≤ t²·‖x‖²‖y‖²`); for `t < 0` the inner product must be
  negative and squaring reverses the comparison
  (`t²·‖x‖²‖y‖² ≤ ⟨x,y⟩²`);
- `isSphericalCode S t : Bool` — every point of `S` is nonzero, and every
  pair of distinct positions satisfies `cosLe` (computable, scans all
  position pairs);
- `SphericalCodeUpper S num den : Prop` —
  `isSphericalCode S (num/den) = true`, the packaged certificate.

**Why the condition certifies a spherical-code bound.** Rational points
cannot lie exactly on the unit sphere, so the certificate works with
*directions*. Given 50 nonzero rational vectors with every normalized
pairwise inner product `≤ T`, project each vector radially onto `S^2`
(defined, since they are nonzero). For `T < 1` the projections are 50
distinct points — two positions carrying the same direction would have
normalized inner product `1 > T`. The projected 50-point spherical code
has maximal pairwise cosine `≤ T`, i.e. minimal angle `≥ arccos T`, so
the optimal value for `N = 50` is at most `T`.

Boundary behavior, aligned with the solver sibling task
`spherical-code-d3-n50`: the zero vector is rejected (its direction is
undefined), and duplicate points are rejected automatically for `T < 1` —
two copies of the same nonzero point sit at normalized inner product `1`.
Unlike the sibling checker, no unit-ball constraint `‖v‖² ≤ 1` is imposed:
the normalized inner product is invariant under positive rescaling of each
point, so a configuration in the ball and its radial projection are the
same certificate.

Bring your own point set as data — typically a `List (Fin 3 → Rat)` built
by a small helper, e.g.

```lean
def pt (x y z : Int) : Fin 3 → Rat := fun k => ([x, y, z].getD k.val 0 : Rat)
```

with coordinates scaled to integers (the normalized inner product is
invariant under positive rescaling of each point, so integer-scaled
coordinates lose nothing), or a programmatic generator — and prove the
claim, e.g. `exact ⟨myPoints, by native_decide, by native_decide⟩`.
**`native_decide` is allowed and is the intended certificate path**: the
judge whitelists `Lean.ofReduceBool` and `Lean.trustCompiler`, alongside
the three standard axioms. The judge automatically lets `native_decide`'s
generated internal axioms (`._native.native_decide.ax_*`) through;
`native_decide` can be used directly.

**Representation is not the bottleneck here.** At the record region
`T ≈ 0.8681732091268975` the check scans 2500 ordered position pairs in exact
rational arithmetic — any `List` representation evaluates quickly under
`native_decide`. (Only avoid exotic non-computable encodings: everything
must reduce by compilation.)

**Precision rules for chasing the record.** All validation is exact
rational arithmetic: pairwise comparisons use squared quantities with
big-integer arithmetic, and the comparison with the record is exact. The
record value to work against is `0.8681732091268975` — the true record
`r*` (the algebraic number above) rounded **up** at the 16th decimal
digit; Szekely's construction itself, whose exact max inner product is
`r*`, sits at this value. Strictly beating it (`T < 0.8681732091268975`)
means strictly beating the 1974 record — a genuine new result. Because
your claim is a rational `T = num/den` and every check is exact, leave a
small exact-arithmetic margin between your configuration's true maximal
inner product and the `T` you claim (any genuine improvement comfortably
clears a 1e-12 margin).

**Sanity anchors.** Two worked examples ship in the container as JSON
decimal point lists (the same files as in the solver sibling task
`spherical-code-d3-n50`), together with their deterministic generator:

- `/app/examples/example_fib50.json` — the 50-point Fibonacci
  spiral: exact maximal normalized inner product
  `0.90458528119446257...`. Embedding it (coordinates are exact
  12-decimal rationals) and proving `SphericalCodeUpper` at some `T`
  exercises the whole pipeline — fixed layer, point representation,
  `native_decide`, and the claim interface.
- `/app/examples/example_relaxed50.json` — a deterministic Coulomb
  relaxation of the spiral seed: exact maximal normalized inner product
  `0.87705060493286680...` (witness pair (31, 47)).
- `/app/examples/gen_examples.py` — regenerates both.

## Rules

- For verifier safety, executable commands `#eval`, `#exec`, `#exit`, and
  `#compile` are not allowed in submitted Lean files, including harmless
  diagnostics. Remove these commands before submission; the verifier rejects
  them before compiling the proof.
  `native_decide` remains allowed as described in this task.
- Do not change any **code** above the line `-- END OF FIXED PART`; the
  verifier compares it (comments stripped, whitespace-normalized) against
  its reference. Comments and docstrings up there are free to edit — they
  do not affect judging.
- Keep the interface name `submission_upper` and the pinned claim shape;
  the verifier parses the two numerals `num` and `den` from the claim
  header.
- No `axiom` / `sorryAx` anywhere; `sorry` / `admit` only inside the
  claim body, and a body that still contains one is simply not scored.
  Every scored claim must depend only on the whitelisted axioms
  (`propext`, `Classical.choice`, `Quot.sound`, `Lean.ofReduceBool`,
  `Lean.trustCompiler`) — `#print axioms` is checked.

## How to work

You have a 12-hour budget and are expected to use it. Matching the
published record (`T = 0.8681732091268975`) is the beginning of the work, not the end
of it — do not submit early with only a tied record. Stronger is
better, with no upper limit.

Work in this order:
1. **Anchor check.** Verify the frontier values in the Background
   against the linked sources — if an anchor looks stale or wrong, say
   so in your final summary rather than trusting it blindly.
2. **Bank a claim early, then keep improving.** Get one certified
   claim on the board (a sanity cell exercises the pipeline; a fetched
   published construction ties the record), then keep pushing:
   improve your construction, try a different method, or attack a
   harder cell. Every strictly stronger certified bound counts for
   more. Keep going as long as you can generate distinct ideas —
   do not stop at a fixed count.
3. **Use the internet.** Look up the literature (constructions,
   records, techniques) rather than trusting training memory. Certifying
   a published record ties it; going beyond it takes a strictly
   stronger object the literature does not have.

The floor rules never change: a scored claim must not contain `sorry`,
planted axioms or redefinition tricks are rejected. Never fabricate a
proof.

## Scoring

The verifier re-checks your Lean proof, parses `T` from the proven claim,
and independently evaluates it against the published literature frontier
(`0.8681732091268975`, Szekely 1974 — see Background). **A strictly
stronger certified bound is always better, and there is no upper limit**
— the published record is the bar to beat, and beating it (any certified
`T` strictly below) is a literature-level new result.

## Environment

The project builds offline with `lake build Task` in `/app`.
Agent budget: 12 hours. The container has internet access. A helper `/app/snapshot.sh` mirrors your `/app/Task` workspace into `/logs/artifacts/` every 5 minutes once started — launch it early with `nohup /app/snapshot.sh >/dev/null 2>&1 &` so your work is preserved whatever happens later.

## Notes

- The published record configuration is highly symmetric (Szekely's
  construction is a deltahedral arrangement); the published coordinate
  file gives 16-decimal coordinates whose exact evaluation is
  `0.8681732091268975...`. Certifying that point set (suitably rescaled
  to rationals) ties the record; beating it takes a strictly smaller
  maximal inner product.
- Known heuristics that reach the frontier region quickly: Coulomb /
  logarithmic repulsion relaxation from a good seed, simulated annealing
  on the worst pair, convexification swaps. Reaching the record itself is
  the hard part — it has resisted 50 years of numerical optimization.
- A mild subtlety when rounding coordinates: the exact rational
  evaluation of a rounded configuration can drift across your intended
  threshold in either direction. Leave a small exact-arithmetic margin
  between your configuration's true maximal inner product and the `T` you
  claim (any genuine improvement comfortably clears a 1e-12 margin).
- The final check itself is seconds at these sizes.
