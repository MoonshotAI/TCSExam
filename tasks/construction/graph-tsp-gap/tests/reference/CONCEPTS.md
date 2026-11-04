# Concept crosswalk: Lean identifiers in graph-tsp-gap-lean ↔ literature definitions and sibling checker

This document maps from every mathematical concept in the fixed part of this task's definition layer (`environment/app/Task/Basic.lean`) to its source, an item-by-item alignment with the Solver sibling `graph-tsp-gap` scoring semantics, and a record of deliberate differences from the literature's formulation.

## Source anchors

- Scoring anchors (Desjardins family, values for each n: 11: 7/6, 12: 7/6, 13: 32/27, 14: 6/5, 15: 6/5, 16: 40/33, 17: 11/9, 18: 11/9, 19: 16/13, 20: 26/21; the 1.0 anchor uses the maximum, 26/21): Nicholas Desjardins, *On Applying Methods for Graph-TSP to Metric TSP*, University of Ottawa master's thesis, 2017 (advisor Sylvia Boyd), Conjecture 5.3.1 + Figure 5.3.1 + Theorem 5.3.2.

- Values closed by exhaustive search for n≤10: the same thesis, Tables 5.2.1/5.2.2 (exact maxima: 1 at n=6, 16/15 at n=7, 10/9 at n=8, 10/9 at n=9, 8/7 at n=10).
- Upper-bound anchor 7/5: Sebő, Vygen, *Shorter Tours by Nicer Ears*, Combinatorica 34(5):597–629, 2014.
- Attribution of the 4/3 conjecture for graph-TSP: end of §2.4 in Desjardins's thesis.
- Scoring curve and record line for each n: exactly match sibling `tests/checker.py` (BASELINE=1, STANDING=26/21, per-n RECORDS table, no cap).

## Predicate alignment with the Solver sibling checker (item by item)

each row pairs a condition in the Solver checker (`tests/checker.py` + `tests/tsp_gap.py`) with its counterpart in this task's Lean definition layer.

| Solver sibling (`tests/checker.py` + `tests/tsp_gap.py`) | Lean definition layer in this task | Notes |
|---|---|---|
| Integer constraint `3 <= n <= 20` (`MIN_N, MAX_N`) | `GraphGapBound`: `3 ≤ m ∧ m ≤ 20` | Exact match. |
| Simple graph: no self-loops (`u == v` rejected), no parallel edges (deduplicate unordered pairs) | `SimpleAdj`: `adj u u = 0` and `adj u v ≤ 1` | A 0/1 adjacency matrix has no duplicate edges by construction; semantics agree. |
| Undirected (register an edge in both directions) | `SimpleAdj`: `adj u v = adj v u` | Same condition. |
| Connected (BFS from 0 reaches all vertices) | `PathsOk` (an explicit path is supplied for every pair of vertices) | `PathsOk` gives paths for every pair, stronger than the BFS input; in an undirected graph, “0 reaches all vertices” is equivalent to “every pair is connected.” |
| Floyd–Warshall shortest-path closure (`metric_closure`) | `certDist` is pinned down by four conditions: `MetricCost` (triangle inequality) + `EdgeConsistent` (graph edges have length exactly 1) + `PathsOk` (for each pair, a graph path has length exactly `dist u v`) + the fixed-layer lemma `walk_length_ge` (every graph path has length ≥ `dist u v`, by induction along the path using the triangle inequality) | An exhibited path gives “shortest path ≤ dist”; the lemma gives “shortest path ≥ dist.” Together they show that `dist` is exactly the matrix computed by Floyd–Warshall, without trusting any computation process. |
| Subtour LP (`opt_lp`: minimize c·x; degree constraints x(δ(v))=2; cut constraints x(δ(S))≥2 for every nonempty proper subset, including singletons, using global minimum-cut separation; and 0≤x≤1) | `LPFeasible` + `LPValue` (same as the original tsp-gap pilot) | Undirected edge variables are represented by a symmetric matrix on ordered pairs; the objective divides the ordered sum by 2. Cut constraints are checked for every nonempty proper bitmask, including singletons. These are the same LP. |
| `OPT_tour`: Held–Karp DP (`opt_tour`, starting from 0) | `IsTour` / `tourCost` (a list starting from 0) | With a symmetric metric, each undirected tour corresponds to two reversed lists of equal cost. A closed walk can be shortened to a tour using the triangle inequality, so both formulations have the same optimum (same argument as in the pilot `CONCEPTS.md`). |
| `gap = OPT_tour / OPT_LP` | `GapLB dist α` implies the ratio is ≥ α | For the minimization LP, a feasible point gives `OPT_LP ≤ c·x`; the potential table gives `OPT_tour ≥ T`; hence the ratio is ≥ T/(c·x) ≥ α. Only a lower bound is proved, consistent with scoring that rewards a larger ratio. |
| No hidden input outside the stated assumptions | Same: the instance, closure, path witnesses, LP point, and potential table are all included and checked by the machine | Same setup. |

## Crosswalk (Lean identifiers ↔ literature concepts)

each row describes one Lean definition, the corresponding graph-TSP concept, and the intentional modeling choice.

| Lean identifier | Literature concept | Deliberate difference and explanation |
|---|---|---|
| `SimpleAdj adj` | Simple undirected unweighted graph | Adjacency matrix values are naturals, restricted by the assumptions to 0/1; this makes direct `decide` checks convenient. |
| `EdgeConsistent` / `PathsOk` / `walk_length_ge` | Shortest-path metric closure | The scorer does not compute the closure. It is fixed by the conjunction of the metric condition, edge-length consistency, path witnesses, and the path lower-bound lemma. The per-pair paths are certificate data. |
| `MetricCost dist` | Finite integer metric: symmetric, zero on the diagonal, positive off the diagonal, and satisfying the triangle inequality | Exactly matches the tsp-gap pilot. |
| `IsTour l`, `tourCost` | TSP tour and its cost | A directed list starting from vertex 0; with symmetric costs it has the same optimum as the undirected formulation. |
| `LPFeasible x`, `LPValue` | Feasible solution and objective of the subtour-elimination LP (Held–Karp relaxation) | Exactly matches the tsp-gap pilot (ordered-pair representation, objective divided by 2). |
| `certW` (potential table) | Dual certificate for Held–Karp DP | Any table satisfying the inequalities gives a tour lower bound; it need not attain the optimum. The oracle computes the exact DP table during Lean evaluation with a deterministic loop (2^20×20 entries; too large to write as a literal). |
| `GapLB dist α` | Per-instance lower bound on the integrality gap | Same as the pilot. |
| `GraphGapBound m adj dist α` | Packaged statement for this task: 3≤m≤20, graph assumptions, correct metric closure, and gap lower bound α | Milestones count only 11≤m≤20. The literature has closed n≤10 (the largest maximum in this range is ≤8/7, below the target Desjardins-family values), so α alone cannot award a false milestone. |
| `gapLB_of_cert` | Assembly theorem: integer certificate y/D, potential table, and integer inequality p·(c·y) ≤ q·2·T·D imply `GapLB dist (p/q)` | Exactly matches the tsp-gap pilot. |
| `certN / certAdj / certDist / claimedAlpha / main` | Submission interface (the model supplies the graph and all witnesses) | The scorer recognizes only the interface names; the type of `main : GraphGapBound certN certAdj certDist claimedAlpha` guarantees the instance is valid. |

## Formalization choices

- **Use one ∀ with multiple clauses in predicates**: `SimpleAdj` is one `∀ u v` carrying three clauses (`adj u v = adj v u ∧ adj u v ≤ 1 ∧ adj u u = 0`); `PathsOk` is one `∀ u v` carrying two clauses (the walk check is true ∧ its length is exactly dist+1). Prior lesson from ramsey-r3-10: splitting the same quantifier into several independent ∀ conjuncts can make the `Decidable` instance tree exceed the default `synthInstance.maxSize`, causing `native_decide` to fail directly. Keeping multiple clauses under one ∀ halved the instance tree and passed. The fixed layer also uses the pilot's `synthInstance.maxSize 2048` as a safeguard.
- **Use `Array`, not `List`, for large tables**: the pilot warns in the task statement that each `matGet` lookup traverses a linked list. The n=20 potential check performs around 10⁸ lookups, which is too slow for `native_decide` with lists. The oracle stores adjacency, distance, and LP numerator matrices as flat `Array ℕ` values (400 literal entries); the potential table is computed inside Lean as an `Array ℕ` (2^20×20 entries).
- **Compute the potential DP table instead of writing it as a literal**: a source literal for 2^20×20 entries would be around hundreds of megabytes and too large for the parser. Instead, construct it once in an `Id.run do` loop. During `native_decide` compilation, it is evaluated and cached as a top-level constant, and all checks share the same table.
- **Allow `native_decide`**: this is the largest scoring difference from the tsp-gap pilot. The pilot bans `native_decide` lexically (its n=10 Petersen certificate can be checked with kernel `decide`). For this task, the cut checks on the n=20 certificate (2^20 cuts × 400 entries) and the potential check (about 10⁸ combinations) are only practical during compilation. The axiom allowlist therefore includes `Lean.ofReduceBool` and `Lean.trustCompiler` (the pilot's `judge.json` already lists these five axioms).
- **Match the fixed-layer end marker at line start**: the pilot's `score.py` uses `text.find("-- END OF FIXED PART")`, but the pilot's own header comment contains that string on line 33. The first match is in the comment, so fixed-layer protection covers only the first 33 lines. This task's `score.py` instead uses the line-start regex `^-- END OF FIXED PART`; the marker occurs only at the start of its line in the reference file (). The pilot was not changed; this difference was noted in the delegation report.

## Checks completed

- The fixed layer compiled with leanprover/lean4:v4.33.0-rc1 + mathlib4 (pinned revision 5b3f719), with only style warnings and the stub's `sorry` warning. The `walkGo_ge` / `walk_length_ge` proofs also compiled on this pinned version.
- The stub (placeholder C₃ certificate + `sorry` main) scored 0; the lexical `sorry` gate rejected it before compilation.
- The complete C₃ certificate assembly smoke probe (`gapLB_of_cert` + a tiny equivalent using `unfold`/`native_decide`) compiled. `#print axioms` listed only allowlisted axioms and `._native.native_decide.ax_*` entries (filtered by the scorer); `#eval` output matched the scorer's parser format.
- The oracle `theta(7,7,7), n=20` received a full score: reward exactly 1.0, `record_broken = false`, `beyond_4_3 = false`, n = 20 parsed correctly, and α = 26/21 parsed correctly. **Total scoring wall time was 476 seconds**, including mathlib loading, probe compilation, and all `native_decide` runs; the 1700-second probe budget had about 3.5× headroom.
- Axiom check passed (the successful scoring path implies `#print axioms main` was within the allowlist: propext / Classical.choice / Quot.sound / Lean.ofReduceBool / Lean.trustCompiler, plus filtered `._native` entries).
- Negative controls: changing one byte in the fixed layer scored 0 (fixed-layer comparison blocked it); replacing oracle `pot_step` with `sorry` scored 0 (lexical gate blocked it).
- Local scorer logic self-checks in Python (no Lean involved): four fixed-layer normalization cases (blank, mutation, deletion of marker, line-start anchoring); positive and negative lexical cases; interface-name presence; pointwise scoring curve (1 → 0, 7/6 → 0.7, 6/5 → 0.84, 26/21 → 1.0, 4/3 → 1.4, out-of-range clamped to 0); `record_broken` by n (record line only for 11..20, not n=10); `beyond_4_3` boundary (not marked at exactly 4/3); probe-output parsing and axiom allowlist (including filtering `._native.native_decide.ax_*`).
- All anchors in `judge.json` were compared character-for-character with sibling `tests/checker.py` and match (BASELINE=1, STANDING=26/21, per-n RECORDS, and 4/3 boundary).
