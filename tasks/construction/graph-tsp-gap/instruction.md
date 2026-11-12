# Task: The graph-TSP subtour-LP integrality gap — Open Construction

A Lean 4 project lives in `/app`. `Task/Basic.lean` contains a
definition layer and a claim slot (`main`, together with your own
`certN`, `certAdj`, `certDist` and `claimedAlpha`) — prove the strongest
claim you can. The verifier independently evaluates your best
proven claim against the published literature frontier when the budget
ends; stronger is better, with no upper limit.

In **graph-TSP** you are given a connected, unweighted, undirected graph `G`
on `n` vertices and want the shortest closed walk that visits every vertex
(edges may be reused). Equivalently, it is the TSP on the **shortest-path
metric** of `G`. The **subtour-elimination LP** (a.k.a. Held–Karp relaxation)
on that metric is

```
min  c.x
s.t. x(delta(v)) = 2   for every vertex v
     x(delta(S)) >= 2  for every S, 2 <= |S| <= n-2
     0 <= x_e <= 1
```

and the **integrality gap** is `OPT_tour / OPT_LP`, maximized over all
connected graphs on `n` vertices. The famous **4/3 conjecture** asserts that
this gap is exactly `4/3` — conjectured for metric TSP in general, and open
already for the graph-TSP subclass. On the other side, the gap for graph-TSP
is known to be at most **7/5** (Sebő–Vygen 2014, *Shorter tours by nicer
ears*, Combinatorica 34(5):597–629).

What is known for small `n` (this is why the records start at `n = 11`):

- **Desjardins 2017** (*On Applying Methods for Graph-TSP to Metric TSP*,
  MSc thesis, University of Ottawa, Sylvia Boyd's group), Chapter 5:
  exhaustive computation over **all connected graphs on `6 <= n <= 10`**
  (exact rational LP + Concorde). The exact maxima are `1` (n = 6),
  `16/15` (n = 7), `10/9` (n = 8), `10/9` (n = 9), `8/7` (n = 10), so
  nothing at `n <= 10` is open.
- The same thesis (**Conjecture 5.3.1**) conjectures the exact value for
  every `n` and gives explicit graph families attaining these values
  (**Figure 5.3.1**, Theorem 5.3.2): repeatedly subdivide one edge in each
  of the three "1-paths" of the settled small-n optima. Concretely, at
  `n = 3k - 1` the family member is the **theta graph** `Theta(k,k,k)` —
  two endpoints joined by three paths of length `k`.

These family values are the current best known constructions per `n`:

| `n`  | family value (best known) |
|------|---------------------------|
| 11   | `7/6 ≈ 1.1667`            |
| 12   | `7/6 ≈ 1.1667`            |
| 13   | `32/27 ≈ 1.1852`          |
| 14   | `6/5 = 1.2`               |
| 15   | `6/5 = 1.2`               |
| 16   | `40/33 ≈ 1.2121`          |
| 17   | `11/9 ≈ 1.2222`           |
| 18   | `11/9 ≈ 1.2222`           |
| 19   | `16/13 ≈ 1.2308`          |
| 20   | `26/21 ≈ 1.2381`          |

Beating the family value at some `n` is a genuinely new result (a
counterexample to Conjecture 5.3.1); no published graph beats it at any `n`.
Exceeding `4/3` at any `n` refutes the 4/3 conjecture for graph-TSP (and
hence for metric TSP).

Graph-TSP is the special case of metric TSP where the metric is a graph
metric; the sibling task on general metrics (`tcsexam/tsp-gap-lean-open`)
has *different* records (the Benoit–Boyd family, e.g. `76/61 ≈ 1.2459` at
`n = 20`) behind a different conjecture. Here the conjectured optima are the
sparser, unweighted constructions above.

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).** Everything above
  `-- END OF FIXED PART`:

  - `SimpleAdj adj` — the simple unweighted undirected graph premise
    (symmetric `0/1` matrix, zero diagonal);
  - `EdgeConsistent adj dist`, `adjFOf`, `walkOkF`, `walk_length_ge`,
    `PathsOk` — the shortest-path-closure correctness layer (walk witnesses +
    the proved lower-bound lemma);
  - `MetricCost dist` — the metric premise (symmetry, zero diagonal,
    positivity, triangle inequality);
  - `IsTour`, `tourCost` — tours as lists starting at vertex `0` (with
    symmetric costs the directed and undirected optima coincide);
  - `LPFeasible x`, `LPValue cost x` — the subtour LP, written with symmetric
    variables over ordered pairs (the objective divides the ordered sum by 2);
  - `pot_inv`, `tour_lb_of_potOk` — the potential-table soundness theorems
    (already proved);
  - `GapLB cost α` — the packaged per-instance gap lower bound;
  - `GraphGapBound m adj dist α` — `3 ≤ m ≤ 20` ∧ graph premise ∧ closure
    correctness ∧ `GapLB dist α`;
  - `gapLB_of_cert` — the assembly theorem (already proved).
- **Claim slot.** **Bring your own graph and your own certificate, and
  prove a gap lower bound in Lean 4.** Nothing is given: no instance, no LP
  point, no potential table, no lemma ladder. Below the line
  `-- END OF FIXED PART`, provide (keeping the interface names):

  - `certN : ℕ` — your number of vertices. The theorem requires
    `3 ≤ certN ≤ 20`; **only `11 ≤ certN ≤ 20` can set a record**
    (smaller instances serve as sanity checks — see the cycle anchor below).
  - `certAdj : Fin certN → Fin certN → ℕ` — the **adjacency matrix** of a
    connected simple unweighted undirected graph (the *graph* is submitted,
    not its closure — you must also certify the closure, below).
  - `certDist : Fin certN → Fin certN → ℕ` — its **shortest-path metric
    closure**. Exactness is machine-checked, not trusted: you prove
    `MetricCost certDist` (triangle inequality), `EdgeConsistent`
    (graph edges have distance `1`), and exhibit, for every ordered pair
    `u v`, an explicit graph walk of length exactly `certDist u v`
    (`PathsOk`); the proved lemma `walk_length_ge` in the fixed part shows
    every graph walk is at least that long, so `certDist` is forced to be the
    true shortest-path metric.
  - `claimedAlpha : ℚ` — the gap lower bound you claim.
  - `theorem main : GraphGapBound certN certAdj certDist claimedAlpha` — the
    machine-checked certificate, typically assembled via `gapLB_of_cert` from:
    - a **rational LP feasible point** `x = y/D` (integer numerator matrix
      `certY`, denominator `certD`): degree `2` at every vertex, every proper
      nonempty cut carries at least `2`, `0 ≤ x ≤ 1`. Feasibility gives
      `OPT_LP ≤ c·x` — no LP duality needed;
    - a **Held–Karp potential table** `W` (dual of the usual DP): natural
      numbers `W mask j` indexed by visited-set bitmasks (vertex `0` in every
      state) and end vertices `j`, satisfying `W 1 0 = 0`,
      `W mask j ≤ W (mask ∖ {j}) i + dist i j` for every state and
      predecessor, and `T ≤ W (full) j + dist j 0` on the final row. The
      soundness theorem `tour_lb_of_potOk` (proved in the fixed part) turns
      this into `OPT_tour ≥ T`;
    - the integer arithmetic `p * (c·y) ≤ q * (2 * (T * D))` for
      `α = p/q`, i.e. `α · (c·x) ≤ T`.

  `W` may be *any* function `ℕ → Fin certN → ℕ` — a closed form or a table
  computed by an in-Lean loop is fine, only the inequalities matter. The
  conjectured optimal LP points of the record families are **half-integral**
  (`x = 1/2` on the end-gadget edges, `x = 1` on the path edges, plus short
  cross-path closure edges), so denominators stay small.

**Sanity anchors.** Any **cycle** `C_n` has gap exactly `1` (the cycle
itself is a tour of cost `n`, and `x = 1` on the cycle edges is LP-feasible
with value `n`): certifying `α = 1` at, say, `n = 11` exercises every piece
of the pipeline. The `n = 10` settled optimum (a `P3` and a triangle
joined by paths of lengths `2, 3, 2`, gap exactly `8/7 ≈ 1.1429`) is a
good small rehearsal. The theta graph `Theta(7,7,7)` at `n = 20` has
`OPT_LP = 21`, `OPT_tour = 26`, gap exactly `26/21 ≈ 1.2381` — the
family value there.

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
- Keep the interface names `certN`, `certAdj`, `certDist`, `claimedAlpha`,
  `main`; the verifier type-checks `main` against
  `GraphGapBound certN certAdj certDist claimedAlpha` and evaluates `certN`
  and `claimedAlpha` to evaluate your proof.
- No `sorry`, `admit`, `axiom`, `sorryAx`, `implemented_by`, `extern`,
  `unsafe`, or `opaque` anywhere in the file (checked lexically on the
  comment-stripped source). `native_decide` **is allowed**: at `n = 20` the
  certificate checks are far too large for kernel `decide`. `#print axioms
  main` must stay within the whitelisted axioms (`propext`,
  `Classical.choice`, `Quot.sound`, `Lean.ofReduceBool`,
  `Lean.trustCompiler`).
- The file sets `maxRecDepth`, `maxHeartbeats 0` and
  `synthInstance.maxSize` at the top — leave those lines alone.
- The verifier recompiles your submission from scratch with a ~28-minute
  probe budget; your certificate checks (typically large `native_decide`
  computations) must fit inside it. Representation choices matter: a
  `List (List ℕ)` lookup costs one list traversal per access — at
  `n = 15 .. 20` a full potential table has `n·2^(n-2)` live entries, so
  keep big tables in `Array`s (or generate them with a deterministic loop),
  never in list-of-lists form.

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
per the Background table — `7/6` at `n = 11` up to `26/21` at `n = 20`;
only `n = 11 .. 20` is open, `n ≤ 10` is settled by exhaustive
enumeration). **A strictly stronger certified bound is always
better, and there is no upper limit** — the family value at your `n` is
the bar to beat, beating it is a literature-level new result (a
counterexample to Conjecture 5.3.1), and a certified `α > 4/3` refutes
the 4/3 conjecture.

## Environment

The project builds offline against the mathlib checkout at
`/opt/lean-lib/mathlib4`; use `lake build Task` in `/app` to check.
Agent budget: 12 hours. The container has internet access. A helper `/app/snapshot.sh` mirrors your `/app/Task` workspace into `/logs/artifacts/` every 5 minutes once started — launch it early with `nohup /app/snapshot.sh >/dev/null 2>&1 &` so your work is preserved whatever happens later.

## Notes

- The family LP points are half-integral, and the record families are built
  from two small end-gadgets joined by long "1-paths" whose internal
  vertices must all be visited. Beating them likely needs a qualitatively
  different shape: cubic 3-edge-connected non-Hamiltonian graphs (snarks;
  `x = 2/3` on every edge is LP-feasible with cost `n`), theta variants,
  chains of short cycles, and asymmetric subdivisions are all fair game.
  The thesis exhaustively checked only `n ≤ 10` (all graphs) and `n ≤ 16`
  (cubic/subcubic only), so denser or non-half-integral witnesses may well
  exist at `n ≥ 11`.
- The closure layer is part of the certificate, not of the trusted
  verifier: any error in your `certDist` (a distance too small to realize,
  or too large to be shortest) makes some premise unprovable, and the whole
  submission fails. Compute the closure exactly before you start proving.
- A workable certificate architecture at `n = 20`: array-backed matrices
  (`Array ℕ` with flat row-major indexing), a potential table built once by
  a deterministic in-Lean loop into an array (the exact Held–Karp DP), and
  every finite check discharged by `native_decide`.
