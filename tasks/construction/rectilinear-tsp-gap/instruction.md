# Task: The rectilinear-TSP subtour-LP integrality gap — Open Construction

In **rectilinear TSP** you are given `n` points in the plane and want the
shortest tour visiting all of them under the **L1 (Manhattan) distance**
`|dx| + |dy|`. The **subtour-elimination LP** (a.k.a. Held–Karp relaxation)
on that metric is

```
min  c.x
s.t. x(delta(v)) = 2   for every vertex v
     x(delta(S)) >= 2  for every S, 2 <= |S| <= n-2
     0 <= x_e <= 1
```

and the **integrality gap** is `OPT_tour / OPT_LP`, maximized over all point
sets on `n` points. The **4/3 conjecture** — gap exactly `4/3` — is
conjectured for metric TSP in general and is **open already for the
rectilinear case**; the gap is at most `3/2` by Wolsey's classic analysis.

What is known for small `n` (this is why the task window starts at `n = 11`) —
all from **X. Zhong**, *Lower bounds on the integrality ratio of the subtour
LP for the traveling salesman problem*, **Discrete Applied Mathematics 365
(2025) 109–129** (open access; arXiv:2102.04765):

- **Section 4**: exact computation of the maximum ratio over all rectilinear
  instances for `6 <= n <= 10`. The exact maxima are

  | n    | max gap (settled)  |
  |------|--------------------|
  | 6    | `18/17 ≈ 1.0588`   |
  | 7    | `13/12 ≈ 1.0833`   |
  | 8    | `34/31 ≈ 1.0968`   |
  | 9    | `31/28 ≈ 1.1071`   |
  | 10   | `28/25 = 1.1200`   |

  so nothing at `n <= 10` is open. (For `n <= 5` the ratio is always 1.)
- **Section 5.3**: an explicit family `I^2_{i,j,k}` for every
  `n = i + j + k + 6`, generalizing the settled optima. The points lie on
  three horizontal lines: `X_0..X_{i+1}` on `y = 0` with `X_0 = (0,0)`,
  `X_{i+1} = (1,0)`; `Z_0..Z_{k+1}` on `y = h`; `Y_0..Y_{j+1}` (the *inner*
  points) on the middle line `y = h_Y`, where

  ```
  h   = 1 + (j+1)/(j+3) * (1/(i+1) + 1/(k+1) - 1)
  h_Y = 1/2 + (j+1)/(j+3) * (1/(i+1) - 1/2)
  X_s = (s*(j+1)/((j+3)(i+1)) + 1/(j+3), 0)        1 <= s <= i
  Y_s = ((s+1)/(j+3), h_Y)                         0 <= s <= j+1
  Z_s = (s*(j+1)/((j+3)(k+1)) + 1/(j+3), h)        1 <= s <= k
  ```

  (Coordinates as printed in the paper, with one correction: the arXiv text
  prints `h_Y` with `1/(k+1)` instead of `1/(i+1)`; the printed version is
  contradicted by the paper's own Figure 3 and collapses the `n = 8, 9`
  optima to ratio 1. The reading above reproduces all five settled maxima
  exactly. Every record holder below has `i = k`, where the two readings
  coincide.)
- The family ratios converge to **4/3** as `n -> infinity` (Theorem 5.2).
  The best family member per `n` — the current best known construction —
  in the task window (re-verified 2026-09-17, compositions in brackets):

  | n    | family value (best known) |
  |------|---------------------------|
  | 11   | `17/15 ≈ 1.1333` (I²_{1,3,1}) |
  | 12   | `8/7 ≈ 1.1429`   (I²_{1,4,1}) |
  | 13   | `23/20 = 1.1500` (I²_{1,5,1}) |
  | 14   | `22/19 ≈ 1.1579` (I²_{2,4,2}) |
  | 15   | `7/6 ≈ 1.1667`   (I²_{2,5,2}) |
  | 16   | `142/121 ≈ 1.1736` (I²_{2,6,2}) |

  Beating the family value at some `n` is a genuinely new result; no
  published point set beats it at any `n`.

## What's in `/app/Task/Basic.lean`

**Bring your own point set and your own certificate, and prove a gap lower
bound in Lean 4.** Nothing is given: no instance, no LP point, no potential
table, no lemma ladder. In `/app/Task/Basic.lean`, below the line
`-- END OF FIXED PART`, provide (keeping the interface names):

- `certN : ℕ` — your number of points. The theorem requires
  `2 ≤ certN ≤ 16`; **only `11 ≤ certN ≤ 16` can set a record**
  (smaller instances serve as sanity checks — see the collinear anchor
  below; `n ≤ 10` is settled).
- `certPX certPY : Fin certN → ℤ` — the coordinates of your point set as
  **integers**. Rational point sets scale to integer ones (multiply all
  coordinates by a common denominator) without changing any distance ratio,
  hence without changing the gap — submit the scaled integer form. The
  points must be **pairwise distinct** (`PointsDistinct`), and the cost
  matrix is the exact L1 distance `l1Cost` — the triangle inequality is
  proved once and for all in the fixed layer (`metricCost_l1`), so raw
  points are all you submit, never a distance matrix.
- `claimedAlpha : ℚ` — the gap lower bound you claim.
- `theorem main : GapBound certN certPX certPY claimedAlpha` — the
  machine-checked certificate, typically assembled via `gapLB_of_cert` from:
  - a **rational LP feasible point** `x = y/D` (integer numerator matrix
    `certY`, denominator `certD`): degree `2` at every vertex, every proper
    nonempty cut carries at least `2`, `0 ≤ x ≤ 1`. Feasibility gives
    `OPT_LP ≤ c·x` — no LP duality needed;
  - a **Held–Karp potential table** `W` (dual of the usual DP): natural
    numbers `W mask j` indexed by visited-set bitmasks (point `0` in every
    state) and end points `j`, satisfying `W 1 0 = 0`,
    `W mask j ≤ W (mask ∖ {j}) i + cost i j` for every state and predecessor,
    and `T ≤ W (full) j + cost j 0` on the final row. The soundness theorem
    `tour_lb_of_potOk` (proved in the fixed part) turns this into
    `OPT_tour ≥ T`;
  - the integer arithmetic `p * (c·y) ≤ q * (2 * (T * D))` for
    `α = p/q`, i.e. `α · (c·x) ≤ T`.

Entries of `W` at states the inequalities never use may be filled with a
large sentinel (see the placeholder). `W` may be *any* function
`ℕ → Fin certN → ℕ` — a closed form, or a table computed inside Lean by
your own code, is fine; only the inequalities matter.

The frontier (what would actually be new): a certified gap strictly above
the family value at your `n` (table above) is a genuinely new result —
the family has stood since 2021 (arXiv) / 2025 (journal).
A certified gap above **4/3** refutes the 4/3 conjecture for rectilinear
TSP (and hence for metric TSP); the family's asymptote is exactly `4/3`,
so you would need something qualitatively different. (This certificate
format proves lower bounds for an explicit instance; proving a universal
*upper* bound on the gap of all `n`-point instances is out of its scope.)

**The definition layer (fixed; do not modify).** Everything above
`-- END OF FIXED PART` in `Task/Basic.lean`:

- `PointsDistinct px py` — the point-set premise (all points distinct);
- `l1Cost px py` — the exact L1 distance `|x_u − x_v| + |y_u − y_v|` on
  integer points, as a natural number;
- `metricCost_l1` — the proof that this cost is a finite metric whenever the
  points are distinct (the metric premise of the gap literature comes for
  free);
- `IsTour`, `tourCost` — tours as lists starting at point `0` (with
  symmetric costs the directed and undirected optima coincide);
- `LPFeasible x`, `LPValue cost x` — the subtour LP, written with symmetric
  variables over ordered pairs (the objective divides the ordered sum by 2);
- `pot_inv`, `tour_lb_of_potOk` — the potential-table soundness theorems
  (already proved);
- `GapLB cost α` — the packaged per-instance gap lower bound;
- `GapBound n px py α` —
  `2 ≤ n ≤ 16 ∧ PointsDistinct px py ∧ GapLB (l1Cost px py) α`;
- `gapLB_of_cert` — the assembly theorem (already proved).

**Sanity anchors.** Collinear equispaced points — e.g. the placeholder
instance in the template, `(0,0), (1,0), (2,0), (3,0)` — have gap exactly
`1` at every `n` (tour and LP both equal `2(n−1)`); certifying one inside
the layer exercises every piece of the pipeline. The settled `n = 10`
maximizer `I^2_{1,2,1}` (gap exactly `28/25 = 1.12`, Zhong 2025 Table 1)
is a good mid-size certificate rehearsal; scaled by `10` it has integer
coordinates. The family members in the task window have `h = 1` and
`h_Y = 1/2`, so `I^2_{1,n-8,1}` scaled
by `2(n−5)` is integral; at `n = 16` that is `22 ×`, giving `OPT_LP = 110`,
`OPT_tour = 128`.

## Rules

- Do not change any **code** above the line `-- END OF FIXED PART`; the
  verifier compares it (comments stripped, whitespace-normalized) against
  its reference. Comments and docstrings up there are free to edit — they
  do not affect judging.
- Keep the interface names `certN`, `certPX`, `certPY`, `claimedAlpha`,
  `main`; the verifier type-checks `main` against
  `GapBound certN certPX certPY claimedAlpha` and evaluates `certN` and
  `claimedAlpha` to evaluate your proof.
- No `sorry`, `admit`, `axiom`, `sorryAx`, `implemented_by`, `extern`,
  `unsafe`, or `opaque` anywhere in the file (checked lexically on the
  comment-stripped source). `native_decide` **is allowed**: `#print axioms
  main` must stay within the whitelisted axioms `propext`,
  `Classical.choice`, `Quot.sound`, `Lean.ofReduceBool`, `Lean.trustCompiler`
  (the last two are what `native_decide` introduces). The judge
  automatically lets `native_decide`'s generated internal axioms
  (`._native.native_decide.ax_*`) through; `native_decide` can be used
  directly.
- The file sets `maxRecDepth`, `maxHeartbeats 0` and
  `synthInstance.maxSize` at the top — leave those lines alone.
- The verifier recompiles your submission from scratch with a ~28-minute
  probe budget; your certificate checks must fit inside it. Representation
  matters: at `n = 16` a full Held–Karp table has `2^16 × 16 ≈ 10^6`
  entries, so a table shipped as a `List (List ℕ)` literal is too large to
  elaborate, and `matGet` on lists costs one traversal per lookup. The
  oracle solution instead *computes* the table inside Lean from the cost
  matrix (an `Id.run` dynamic program over `Array (Array ℕ)`) and lets
  `native_decide` run both the build and the `2^16`-mask cut/potential
  enumerations in native code; that whole pipeline checks in minutes.
  Submissions at smaller `n` can afford simpler representations.

## How to work

You have a 12-hour budget and are expected to use it. Matching the
published record (the family value at your `n`) is the beginning of the work, not the end
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

The verifier re-checks your Lean proof, reads `α := claimedAlpha` and
`n := certN` from the compiled probe, and independently evaluates `α`
against the published literature frontier (the family value at your `n`,
per the Background table — `17/15` at `n = 11` up to `142/121` at
`n = 16`; only `n = 11 .. 16` is open, `n ≤ 10` is settled). **A strictly stronger certified bound is always better, and there is no
upper limit** — the family value at your `n` is the bar to beat, beating
it is a literature-level new result, and a certified `α > 4/3` refutes
the 4/3 conjecture for rectilinear TSP (and hence for metric TSP).

## Environment

The project builds offline against the mathlib checkout at
`/opt/lean-lib/mathlib4`; use `lake build Task` in `/app` to check.
Agent budget: 12 hours. The container has internet access. A helper `/app/snapshot.sh` mirrors your `/app/Task` workspace into `/logs/artifacts/` every 5 minutes once started — launch it early with `nohup /app/snapshot.sh >/dev/null 2>&1 &` so your work is preserved whatever happens later.

## Notes

- The optimal fractional tours of the family members are **half-integral**:
  `x = 1` on the three line paths and `x = 1/2` on the six edges joining the
  three lines at their ends (the paper's `x_{i,j,k}`, Section 5.1). For the
  record member at `n = 16` (`I^2_{2,6,2}`) the exact values are
  `OPT_LP = 121` and `OPT_tour = 142`, independently recomputed on the
  solver sibling's stack (per-n family table in PROVENANCE.md). Half-integral
  extreme points are the conjectured worst case in general, but the paper's
  exhaustive computation stops at `n = 10` — at `n ≥ 11` better
  non-half-integral or differently-shaped witnesses may well exist.
- What makes the ratio large here: the LP spreads fractional mass over the
  short edges along the three lines, while every tour must pay vertical
  detours to collect the inner points. The paper's analysis suggests the
  extremal shape keeps more points on the middle line (roughly
  `j+1 : i+1 : k+1 = sqrt(5) : 1 : 1` asymptotically) — but that asymptotic
  is not the per-`n` truth: in the window the discrete optimum is the
  `(1, n−8, 1)` member. Perturbing the three-line layout, unbalancing the
  line heights, or leaving the three-line shape entirely are all fair game.
- A certificate for a *new* instance needs three inventions, all explicit:
  the point set itself, a subtour-LP feasible point of small value on it
  (half-integral guesses are a good starting point), and a Held–Karp
  potential table — for the last one, computing the exact DP inside Lean
  (as the oracle does) turns an `O(n² 2ⁿ)` search you would otherwise have
  to do offline into a kernel-checked artifact.
- Rectilinear TSP sits between the two sibling tasks in this collection:
  general metric TSP (`tcsexam/tsp-gap-lean-open`, arbitrary metric cost
  matrices, records e.g. `27/22 ≈ 1.2273` at `n = 16`) and graph-TSP
  (`tcsexam/graph-tsp-gap-lean-open`, shortest-path metrics of unweighted
  graphs). L1-embeddable metrics are a different subclass with its own
  record lines, and the three-line extremal structure is specific to the
  geometric cases.
