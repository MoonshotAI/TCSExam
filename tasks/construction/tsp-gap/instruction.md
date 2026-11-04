# Task: The metric-TSP subtour-LP integrality gap — Open Construction

The **subtour-elimination LP** (a.k.a. Held–Karp relaxation) for the metric
traveling salesman problem is

```
min  c.x
s.t. x(delta(v)) = 2   for every vertex v
     x(delta(S)) >= 2  for every S, 2 <= |S| <= n-2
     0 <= x_e <= 1
```

Its **integrality gap** is `OPT_tour / OPT_LP`, maximized over all metric
cost functions on `n` vertices. A long-standing conjecture asserts that this
gap is exactly **4/3**.

What is known for small `n`:

- **Benoit–Boyd 2008** (*Finding the exact integrality gap for small
  traveling salesman problems*, Mathematics of Operations Research 33(4)):
  exact computation up to `n = 10`.
- **Cook–Hougardy–Petrich 2026** (*Extending Exact Integrality Gap
  Computations for the Metric TSP*, arXiv:2603.12995): exact gap for all
  `n <= 14` (maximum at `n = 14` is `17/14 ≈ 1.2143`). Version 5 of the
  preprint extends the *general* exact computation to
  `n = 16`: the maximum gap is exactly `11/9` at `n = 15` and exactly
  `27/22` at `n = 16`. Restricted to **half-integral** extreme points of
  the subtour polytope they enumerate everything up to `n = 18`:

  | n    | max gap (half-integral) |
  |------|-------------------------|
  | 15   | `11/9 ≈ 1.2222`         |
  | 16   | `27/22 ≈ 1.2273`        |
  | 17   | enumerated, gap **not computed** |

  For `n >= 17` the maximum over *general* metric instances is **unknown**.
- **Schalekamp–Williamson–van Zuylen** conjectured that the integrality gap
  is always attained at a half-integral point. Their conjecture holds at
  `n = 15` iff no metric instance on 15 vertices beats `11/9`, and at
  `n = 16` iff none beats `27/22` — and version 5 of arXiv:2603.12995
  settles both points affirmatively: the conjecture **holds at `n = 15`
  and at `n = 16`**.

## What's in `/app/Task/Basic.lean`

**Bring your own instance and your own certificate, and prove a gap lower
bound in Lean 4.** Nothing is given: no instance, no LP point, no potential
table, no lemma ladder. In `/app/Task/Basic.lean`, below the line
`-- END OF FIXED PART`, provide (keeping the interface names):

- `certN : ℕ` — your number of vertices. The theorem requires
  `2 ≤ certN ≤ 20`; **only `15 ≤ certN ≤ 20` can set a record**
  (smaller instances serve as sanity checks — see the Petersen anchor
  below). Note that the `n = 15` and `n = 16` cells are closed by
  arXiv:2603.12995 v5: they remain listed as reference
  points only and can no longer be beaten — the meaningful record window
  is `n = 17 .. 20`.
- `certCost : Fin certN → Fin certN → ℕ` — an **integer metric**: symmetric,
  zero diagonal, positive off-diagonal, triangle inequality. This is exactly
  the shortest-path **metric closure** of an integer-weighted support graph
  (rational metrics scale to integer ones without changing the gap).
- `claimedAlpha : ℚ` — the gap lower bound you claim.
- `theorem main : GapBound certN certCost claimedAlpha` — the machine-checked
  certificate, typically assembled via `gapLB_of_cert` from:
  - a **rational LP feasible point** `x = y/D` (integer numerator matrix
    `certY`, denominator `certD`): degree `2` at every vertex, every proper
    nonempty cut carries at least `2`, `0 ≤ x ≤ 1`. Feasibility gives
    `OPT_LP ≤ c·x` — no LP duality needed;
  - a **Held–Karp potential table** `W` (dual of the usual DP): natural
    numbers `W mask j` indexed by visited-set bitmasks (vertex `0` in every
    state) and end vertices `j`, satisfying `W 1 0 = 0`,
    `W mask j ≤ W (mask ∖ {j}) i + cost i j` for every state and predecessor,
    and `T ≤ W (full) j + cost j 0` on the final row. The soundness theorem
    `tour_lb_of_potOk` (proved in the fixed part) turns this into
    `OPT_tour ≥ T`;
  - the integer arithmetic `p * (c·y) ≤ q * (2 * (T * D))` for
    `α = p/q`, i.e. `α · (c·x) ≤ T`.

Entries of `W` at states the inequalities never use may be filled with a
large sentinel (see the placeholder). `W` may be *any* function
`ℕ → Fin certN → ℕ` — a closed form is fine, only the inequalities matter.

Both directions of the underlying conjectures count, and both live in the
same certificate: a construction with `gap > 11/9` at `n = 15` (resp.
`> 27/22` at `n = 16`) would be a counterexample to the
Schalekamp–Williamson–van Zuylen conjecture at that `n` — except that
arXiv:2603.12995 v5 rules this out, having proved the conjecture at both
points. The live counterexample window is `n = 17 .. 20`. (This
certificate format proves lower bounds for an explicit instance; proving
a universal *upper* bound on the gap of all `n`-vertex instances is out
of its scope.)

The frontier (what would actually be new):

The strongest known explicit lower bounds are the Benoit–Boyd 2008 family
values, one per `n` (the family is conjectured pointwise optimal):

| `n`  | 15     | 16      | 17      | 18      | 19      | 20      |
|------|--------|---------|---------|---------|---------|---------|
| gap  | `11/9` | `27/22` | `53/43` | `26/21` | `77/62` | `76/61` |

A certified gap strictly above the family value at your `n` is a
genuinely new result. The meaningful record window is
`n = 17 .. 20`: at `n = 15` and `n = 16` the family value coincides with
the *proved* general maximum (arXiv:2603.12995 v5), so those two cells
can no longer be beaten. Textbook constructions (a "theta" graph of
three equal paths) already reach `26/21 ≈ 1.238` at `n = 20` — below the
family value there, so they are strong but not records. The open problem
is to push the best explicit lower bound toward `4/3`.

**The definition layer (fixed; do not modify).** Everything above
`-- END OF FIXED PART` in `Task/Basic.lean`:

- `MetricCost cost` — the metric-closure premise (symmetry, zero diagonal,
  positivity, triangle inequality);
- `IsTour`, `tourCost` — tours as lists starting at vertex `0` (with
  symmetric costs the directed and undirected optima coincide);
- `LPFeasible x`, `LPValue cost x` — the subtour LP, written with symmetric
  variables over ordered pairs (the objective divides the ordered sum by 2);
- `pot_inv`, `tour_lb_of_potOk` — the potential-table soundness theorems
  (already proved);
- `GapLB cost α` — the packaged per-instance gap lower bound;
- `GapBound n cost α` — `2 ≤ n ≤ 20 ∧ MetricCost cost ∧ GapLB cost α`;
- `gapLB_of_cert` — the assembly theorem (already proved).

**Sanity anchors.** The Petersen graph (10 vertices, unit edges, metric
closure: non-edges have distance 2) has `OPT_LP = 10` (take `x = 2/3` on
every graph edge: the Petersen graph is 3-edge-connected), `OPT_tour = 11`
(it is non-Hamiltonian), gap exactly `11/10`. Certifying it inside the layer
exercises every piece of the pipeline. A theta graph (two endpoints joined
by three paths of length `k`) has `n = 3k - 1` and gap `1.2` at `k = 5`
(`n = 14`), `26/21 ≈ 1.238` at `k = 7` (`n = 20`).

## Rules

- Do not change any **code** above the line `-- END OF FIXED PART`; the
  verifier compares it (comments stripped, whitespace-normalized) against
  its reference. Comments and docstrings up there are free to edit — they
  do not affect judging.
- Keep the interface names `certN`, `certCost`, `claimedAlpha`, `main`; the
  verifier type-checks `main` against `GapBound certN certCost claimedAlpha`
  and evaluates `certN` and `claimedAlpha` to evaluate your proof.
- No `sorry`, `admit`, `axiom`, `sorryAx`, `native_decide`, `implemented_by`,
  `extern`, `unsafe`, or `opaque` anywhere in the file (checked lexically on
  the comment-stripped source). `#print axioms main` must stay within the
  standard axioms (`propext`, `Classical.choice`, `Quot.sound`).
- The file sets `maxRecDepth`, `maxHeartbeats 0` and
  `synthInstance.maxSize` at the top — leave those lines alone.
- The verifier recompiles your submission from scratch with a ~28-minute
  probe budget; your certificate checks (typically large `decide`
  computations) must fit inside it. Note that `matGet` on `List (List ℕ)`
  costs one list traversal per lookup — the frontier lives at
  `n = 15 .. 20`, where a full potential table has `n·2^(n-2)` live
  entries, so representation choices matter.

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
against the published literature frontier (the Benoit–Boyd family value
at your `n` — `11/9` at `n = 15` up to `76/61` at `n = 20`, per the
Background table). **A strictly stronger certified bound is always
better, and there is no upper limit** — the family value at your `n` is
the bar to beat, beating it is a literature-level new result, and pushing
the best explicit lower bound toward `4/3` is the open problem.

## Environment

The project builds offline against the mathlib checkout at
`/opt/lean-lib/mathlib4`; use `lake build Task` in `/app` to check.
Agent budget: 12 hours. A helper `/app/snapshot.sh` mirrors your `/app/Task` workspace into `/logs/artifacts/` every 5 minutes once started — launch it early with `nohup /app/snapshot.sh >/dev/null 2>&1 &` so your work is preserved whatever happens later.
