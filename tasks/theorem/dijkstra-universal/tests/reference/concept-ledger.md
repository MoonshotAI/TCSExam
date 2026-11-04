# Component ledger — lean-dijkstra-universal
For task authors checking the mathematical definitions and source correspondence.

- **What this document contains:** A statement-by-statement comparison of the definition layer and tested statements in the three-tier `lean-dijkstra-universal` task with the paper (arXiv 2311.11793v4), including source claims, assumptions, quantifier differences, and modeling choices.
- **Intended readers:** Reviewers. The full text was checked in §§1, 3–7, and 10 (v4 HTML).

## Paper references

Haeupler, Hladík, Rozhoň, Tarjan, Tětek, *Universal Optimality of Dijkstra via Beyond-Worst-Case Heaps*, co-winner of the FOCS 2024 Best Paper Award, arXiv 2311.11793v4 (major revision in May 2025; the heap construction in §10 of v4 is simpler than in the conference version, so v4 is used).

- D = number of distance orders (§3); F = maximum number of forward arcs in a distance order (§3); n > 2 is assumed throughout (§3: “To simplify the statement of certain bounds we assume n > 2”).
- The comparison and time models are defined in §5; the working-set bound is defined in the final paragraph of §4.2.
- Van et al. 2025 = Ivor Van, Eva Rotenberg, Daniel Rutschmann, *Simpler Optimal Sorting from a Directed Acyclic Graph*, SOSA 2025, pp. 350–355 (the bibliography entry was checked item by item).

## c1 `isDistOrder_iff_realized` ↔ Lemma 3.1

- **Paper:** A distance order is **defined** as an order for which there exist nonnegative arc lengths making all true distances pairwise distinct and the order strictly increasing with true distance (§3). Lemma 3.1 proves this is equivalent to the combinatorial characterization that every w ≠ s has an incoming forward arc (v precedes w in the order).
- **Lean:** The definition uses the combinatorial characterization (`IsDistOrder`); the tested statement says this definition is equivalent to the arc-length realization form (`∃ w, w.Nonneg ∧ true distances pairwise distinct ∧ (L u < L v ↔ d*(u) < d*(v))`).
- **Comparison:** Both directions match the paper's proof step by step (⟹ uses the construction with selected arc length j−i and all other arc lengths n; ⟸ uses the final arc of a shortest path, pairwise distinctness, and nonnegativity). Assumptions: the paper's Lemma 3.1 has no n > 2 assumption, and the Lean statement has none either. Quantifiers: pairwise distinct true distances (`d* u = d* v → u = v`) and strict increase correspond word for word to the paper's “all true distances are distinct, and the order is strictly increasing by true distance.”
- **Note:** The paper's definition of a distance order requires “true distances are distinct,” whereas the **true distance order** in the later part of §3 (after Remark 3.3) requires only nondecreasing order plus incoming forward arcs. Lean keeps these as separate predicates (`IsDistOrder` / `IsTrueDistOrder`), as in the paper.

## c2 `relax_count_le` ↔ Lemma 4.2

- **Paper:** At most F − n + 1 comparisons outside heap operations, and at most F − n + 1 heap decrease-key operations.
- **Lean:** `tr.relaxCount ≤ G.maxForwardArcs − G.n + 1` (natural-number subtraction, safe when the actual value F ≥ n−1).
- **Comparison:** A relax event is a comparison made while scanning u to process arc uv when v is labeled and unscanned (the proof of Lemma 4.2 says: “there is one comparison (outside of heap operations) for each arc vw such that w is labeled”). The decrease-key upper bound equals the comparison bound (each decrease-key is triggered by a successful comparison); the paper states both bounds. Lean states only the comparison bound; the c8 proof absorbs decrease-key count into `relaxCount` (`dec ≤ relax`). Nonnegativity of F − n + 1 follows from existence of a distance order (definition-layer `exists_distOrder`) and the fact that every distance order has at least n−1 forward arcs (part of the proof). Assumption n > 2: included in Lean because it is assumed throughout the paper.
- Small example E2: `relax ≤ F − n + 1` holds on 212 random graphs, including equality cases (minimum slack 0).

## c3 `time_lower_bound` ↔ Lemma 6.1

- **Paper:** In the time model, any correct deterministic algorithm requires Ω(m) time. The proof gives `max{n−2, m−2n+2}` (the proof of Theorem 6.5 combines this as `Ω(max{n−2, m−2(n−1), log D})`; `m−2(n−1) = m−2n+2`).
- **Lean:** `max ((n:ℝ) − 2) ((m:ℝ) − 2·n + 2) ≤ time`, for some nonnegative arc lengths and a legal representation.
- **Model comparison:** The time model is a decision tree with `access v` nodes (return the next arc in v's adjacency list or null, one item per unit of time). Comparison nodes may use only pairs of already accessed vertices (`WF` predicate, with support ⊆ the visited set). This corresponds to §5 of the paper: “the only operations allowed on arc lengths are comparisons of linear functions of arc lengths, but all arc lengths in such a function must be of previously accessed arcs.” Output is a true distance order (`IsTrueDistOrder`), matching the problem definition in §5. A representation `Rep` is a permutation of each vertex's outgoing arcs (`Rep.Legal`: no duplicates and exactly the set of outgoing arcs), matching the paper's “every representation of the graph (every permutation of the incidence lists).” Correctness is quantified over every graph with the same vertex set and source (the algorithm receives only the vertex set and source; arcs are discovered by accessing adjacency lists). This is the form after the 2026-08-20 repair; see the repair record at the end.
- **Difference:** The Ω(m) notation in Lemma 6.1 is made explicit as a max form (same proof content); the undirected variant m−n+1 in the paper's remark is not packaged.

## c4 `comparison_lower_bound_log` ↔ Lemma 6.2

- **Paper:** At least ⌈log₂ D⌉ comparisons in the worst case (a footnote specifies that log is base 2).
- **Lean:** `Real.logb 2 D ≤ comparisons` (real inequality; for a natural-number comparison count, ≥ log₂ D is equivalent to ≥ ⌈log₂ D⌉).
- **Comparison:** A decision-tree comparison is a three-way comparison of a linear function of arc lengths with 0 (the proof of Lemma 6.2 begins by allowing this form). No n > 2 assumption (none in the paper's lemma). The average-case and randomized remarks (⌊log₃ D⌋, Yao's principle) are not packaged.

## c5 `comparison_lower_bound_forward` ↔ Lemma 6.4

- **Paper:** At least F − n + 1 comparisons.
- **Lean:** `((F:ℝ) − n + 1) ≤ comparisons`, for some nonnegative arc lengths. If F < n−1, the right-hand side is negative and the statement holds trivially (in fact, `exists_distOrder` guarantees F ≥ n−1; this is part of the proof).
- **Comparison:** The statement matches the proof's linear-equation dimension argument: at most F−n comparison equations plus at most n−1 pinning equations is fewer than F variables, so the solution space contains a line; move along it until a forward-arc length becomes 0. Assumption n > 2 is included (assumed throughout the paper). The undirected case (the simplified version F = m) is not packaged.

## c6 `working_set_log_sum` ↔ Lemma 7.3

- **Paper:** `∑_{v∈V} log W(v) = O(log D)`.
- **Lean:** `∃ C > 0, ∀ G (2 < n) w tr, ∑_v log₂ (W v) ≤ C·(1 + log₂ D)`; C is uniform over all graphs.
- **Quantifier comparison:** The big-O constant is absolute and does not depend on the graph. The paper's proof chain has this same form: the constant comes from Lemma 7.1 (a uniform ∃C for all interval families, packaged as `IntervalDAGBound`); the only graph-dependent step is the instance-wise inequality D(I) ≤ D(T) ≤ D.
- **Key comparison — why +1 is needed:** The paper's O(log D) has a right-hand side of 0 when D = 1, but there are graphs with D = 1 and `∑ log₂ W > 0` (for example, vertices s,a,b with arcs s→a, s→b, a→b and an additional b→a, or similar arcs making the distance order unique; after scanning s, both a and b are in the heap, W(a) = 2, and the sum is at least 1). The intended meaning of the asymptotic notation is `≤ C·(1 + log D)` (or equivalently `log(2D)`), made explicit in Lean. Small example E3 (212 random graphs; maximum ratio `∑/(1+log₂ D)` was 0.931) supports using a small constant.
- Van et al. Lemma 2.3 is packaged as `IntervalDAGBound`: there is C > 0 such that for any k integer intervals contained in [1,k], `∑ log₂(bᵢ−aᵢ+1) ≤ C·(1 + log₂ D(I))`. The O(log D(I)) in the paper's Lemma 7.1 is likewise made explicit with +1 (when D(I) = 1 the intervals are pairwise separated, all lengths are 1, and the left-hand side is 0, so the source form already holds; +1 is only a safeguard). Small example E4 (300 random interval families; maximum ratio 1.268) supports it.
- **Interval construction comparison:** The paper uses insertion-rank intervals `[aᵢ = i, bᵢ]` (i is the insertion rank of the vertex; bᵢ is the total number of insertions at its deletion). Lean's `insRank` (0-based, src = 0) and `cumIns` (implicit initial insertion including src) implement the same meaning: `W v = cumIns (scanIdx v) − insRank v`. Small example E7 (W is all 1 on path graphs) and E3 check the semantics.

## c7 `outer_heap_invariants` ↔ §10.2 (Lemma 10.2 + Corollary 10.5 + Lemma 10.3)

- **Index conversion:** Lean's `heaps[i]` (0-based) = the paper's H_{i+1} (1-based).
- **(a) ↔ Lemma 10.2:** `|heaps[i]| ≤ 2^(2^(i+1))` is equivalent to the paper's `|H_{i+1}| ≤ 2^(2^(i+1))` ✓.
- **(b) ↔ Corollary 10.5:** The paper states “i > 1 ⟹ the working-set size of an item in Hᵢ is > 2^(2^(i−2)) − 2^(2^(i−3))”. With 0-based i ≥ 1, substitute paper index i+1 to get `2^(2^(i−1)) − 2^(2^(i−2))` ✓. The paper's “working-set size” is the full count at deletion; Lean uses the current partial count `t − x` (t is the next timestamp; inserted items are 1..t−1; the partial working set including x itself is `t−1−x+1 = t−x`). A partial count is at most the full count, so the direction is consistent. The proof of Corollary 10.5 (Lemma 10.4 + insertion-order invariant) gives this lower bound at any time, so the stronger form holds; checked by small example E5 (random runs including deletions).
- **(c) ↔ Lemma 10.3:** The paper says “at most 1 + log log n inner heaps” (n is the total number of insertions). Lean: `heaps.length ≤ 1 + ⌊log₂⌊log₂(t−1)⌋⌋`. Equivalence: the paper gives real-valued `len ≤ 1 + log₂log₂ n`; since len is an integer, `len−1 ≤ ⌊log₂ log₂ n⌋`; `2^(len−1) ≤ log₂ n`, whose left side is an integer, so `≤ ⌊log₂ n⌋`; hence `len−1 ≤ log₂⌊log₂ n⌋`, and `len−1 ≤ ⌊log₂⌊log₂ n⌋⌋` ✓. Checked by small example E5c.
- **Not packaged:** Lemma 10.1 (insertion-order invariant) and Lemma 10.4 (lower bound when the structure changes) are proof content for (b). The amortized charging finish of Theorem 10.6 (the convergence argument for `insert`'s `∑ 1/2^(2^(i−2))`) and the lookup structures of §§10.3/10.4 (compressed-tree union-find with exponential links and bit-vector suffix-min) are not formalized. c7 covers the combinatorial core of §10; the complete data-structure theorem is beyond the size of an L2 task (precedent: NP/coNP membership was not formalized in bidding-games).
- Lean's deletion model (any item in any heap can be deleted, and empty heaps remain in the list) is broader than the paper's. The paper's invariant proofs (Lemmas 10.1/10.2/10.4) hold for arbitrary deletions, so the statement is true and more general.

## c8 `dijkstra_universally_optimal` ↔ Theorem 7.4 + Theorem 6.5 + Theorem 6.6

- **Paper Theorem 7.4:** Dijkstra with a working-set-bound heap runs in O(m + log D) time and performs O(F + log D) comparisons. Hence it is universally optimal in time and universally optimal in comparisons up to an additive term in n.
- **Comparison of Lean's five conjuncts:**
  - (i) **Executability** (`∀` nonnegative w, `Nonempty trace`): implicit in the paper (algorithm correctness cites Tarjan 1983); made explicit as a conjunct to prevent vacuity (Section 6.5, check 7).
  - (ii) **Time upper bound** `C·(m + log₂ D)` follows from c6 + cost definition (processing m arcs + n insert/decrease-key operations at O(1) + delete-min at O(log W)).
  - (iii) **Comparison upper bound** `C·(F + log₂ D)` follows from c2 + c6.
  - (iv) **Time lower bound** `(m + log₂ D)/C` follows from c3 (`max{n−2, m−2n+2} ≥ (m+1)/6`, since `2(n−2)+(m−2n+2) = m−2` and n−2 ≥ 1) + c4 transferred to the time model via `TimeTree.project` (comparison count ≤ time; combined constant 12).
  - (v) **Comparison lower bound** `(F − n + 1 + log₂ D)/C` follows from c4 + c5 (combined constant 2).
  - “Universally optimal in time” means the conjunction of (ii)+(iv) (Dijkstra's worst-case cost divided by any algorithm's worst-case cost is at most C²) ✓; “up to an additive term in n” means (iii)+(v) (the upper bound uses F while the lower uses F−n+1, a gap of exactly n−1 as an additive term) ✓.
- The `hidag` assumption is a proved theorem of Van et al., Lemma 2.3 (peer-reviewed SOSA 2025); it is used as an external fact under the packaging policy (precedents: reachability determinism in bidding-games and four external facts in lossless-expander).
- n > 2 ✓ (assumed throughout the paper).

## Definition-layer choices (fidelity-difference ledger)

1. The distance-order definition uses the combinatorial characterization (c1 states the equivalence).
2. Lemma 4.1 (the scan order is a true distance order) is a trace constraint, `scan_dist_order`; executability is conjunct (i) of c8. Dijkstra correctness is a textbook result (Tarjan 1983), with existing verification in multiple proof systems, and is treated as background.
3. Heap cost is encoded directly into `timeCost`/`compCost` using the working-set bound (matching the conditional analysis in §7); c7 formalizes part of the §10 existence result.
4. Asymptotic notation is made explicit (∃C form with the necessary +1); the n > 2 assumption is applied statement by statement; `⌈log₂ D⌉` is written as a real inequality.
5. See c7 for the 0-based/1-based index conversion.
6. `W` is defined using natural-number subtraction; on a legal trace its value is ≥ 1 (part of the proof), while the definition is bounded for arbitrary input (truncated subtraction).

## Repair record: c3 time-model correctness now quantifies across graphs; silent sorry in definition-layer `pathLen_append`

### Defect and counterexample

During the fifth pre-check, the model proved that c3 `time_lower_bound` was false under the original formalization. `TimeTree G` was indexed by a fixed graph, and `Correct` only required outputting a true distance order for that graph. On a path graph the distance order is unique, so a decision tree consisting of a constant-output leaf can be “correct” without accessing any input, and its runtime is 0 by definition, while the statement requires some input with time ≥ `max{n−2, m−2n+2} > 0`. The model constructed this counterexample explicitly in Lean (three-vertex path graph + constant leaf tree).

### Support in the paper

The time-model definition in §5 says: “The algorithm must discover the arcs and their costs by traversing the incidence lists” — the algorithm is given only the vertex set, source, and adjacency lists, and must discover arcs by accessing them. The key step in the adversary argument for Lemma 6.1 (§6.1) is to “add an arc vᵢvⱼ (j > i+1) on the same vertex set” to form another graph: if the algorithm has not accessed that adjacency-list position, its behavior and output are unchanged, but the output is incorrect on the new graph. This requires correctness to quantify over every graph with the same vertex set and source. The graph-indexed formalization omitted this requirement, allowing a degenerate decision tree that reads no input to count as a “correct algorithm.”

### Repair (synchronized across all three tiers)

- `TimeTree` is now indexed by the vertex set (`TimeTree n`): leaves output `Equiv.Perm (Fin n)`; the linear functions at comparison nodes are defined over ordered vertex pairs (`Fin n × Fin n → ℝ`; arc-length assignments are already defined on all ordered pairs, see `ArcLen`); `access` nodes are unchanged.
- `TimeTree.Correct s A` now requires `WF ∅` and, for **every** graph with the same vertex set and source (choose any arc set with no self-loops and a reachable source, repackage it as `Digraph`, then apply `IsTrueDistOrder`), every nonnegative arc-length assignment, and every legal representation, the output is a true distance order. This matches §5 of the paper.
- The visited set in `WF` is now a finset of ordered pairs (it no longer requires them to be actual arcs, which the algorithm does not know in advance).
- `project`/`project_eval_fst_le`/`project_correct` were updated together: `project` restricts comparisons on pairs to the graph's arcs along a representation; `project_eval_fst_le` adds the invariant that visited pairs are arcs of the current graph (maintained during execution by WF and legal representations), proving comparison results agree under the two indexings. The comparison model (`CompTree`, used by c4/c5) continues to know the graph's arcs, as in the paper, and is unchanged.
- The c3 statement now uses `A : TimeTree G.n`, `hA : A.Correct G.src`; conjunct (iv) of c8 was updated accordingly. Other tested statements are unchanged.
- The definition-layer instance `Fintype G.Arc` changed from `Subtype.fintype _` to `Finset.Subtype.fintype G.arcs` (the corresponding existing mathlib instance for ↥s, so `Finset.sum_coe_sort` matches directly; instance semantics are unchanged).
- Fixed a **pre-existing silent sorry** in definition-layer `pathLen_append`: `subst hz` eliminates `y`, but the following `show … y …` refers to the now-unavailable identifier. This toolchain emits only a warning (“declaration uses sorry”), not an error, leaving a `sorryAx` in the proof. The warning in line 308 of the old verification log `full3-final-bytes.log` was this issue; the task pipeline counted only slot sorries and did not run `#print axioms` on the definition layer. The repair changes `y` to `z` in the `show` statement (matching the repair made by the model in its trajectory).

### Review of the definition-layer tampering alert (guided tier 7046831 scored 0)

The alert was valid, and the grader comparison was correct. The model changed a definition-layer proof body to fix the silent `pathLen_append` sorry (the tested statement was unchanged), triggering a definition-layer comparison failure. Its final report of “7/8 genuine proofs” was not verified by the grader (grading stopped at the definition-layer comparison step). The repair direction was correct, but under the rules any definition-layer change scores 0. The root cause was on the task-authoring side: the pre-existing silent sorry in the definition layer was a defect in this task family, and it was fixed in the same repair. The bare tier 7046833 scored 0 because its main-theorem slot still contained `sorry` (the model did not prove the main theorem in the bare tier), which is a normal difficulty signal.

## Repair record: move c6's existential quantifier before the universal quantifiers (one constant for all graphs)

### Defect and counterexample

A repository-wide adversarial falsification scan (group-3, Section 6) confirmed that the original c6 placed `∃ C` after `∀ G w tr`, so the constant could be chosen separately for each instance. The right-hand factor `1 + log₂ D ≥ 1` is always positive (definition-layer `numDistOrders_pos`). For any fixed left-side value S, choose `C := (|S| + 1)/(1 + log₂ D)`, which is strictly positive and satisfies the inequality. A few lines of tactic can prove the statement without using `hidag` (the interval-DAG bound of Van et al.). The statement was true but trivial: c6 came for free, and quantifier placement removed the content of Lemma 7.3 (whose constant is uniformly determined by the Van et al. bound). The quantifier order in c8 (`∃ C, 0 < C ∧ ∀ G …`) was already correct; c6 was an oversight, not intentional.

### Support in the paper

Lemma 7.3 is an asymptotic statement `∑_{v∈V} log W(v) = O(log D)`: the big-O constant is absolute and independent of the graph. The proof chain has this same form: the constant comes from Lemma 7.1 (Van et al. Lemma 2.3, a uniform ∃C over all interval families, packaged in the task as `IntervalDAGBound`); the only graph-dependent step is the instance-wise inequality D(I) ≤ D(T) ≤ D. Moving ∃C before ∀G is exactly the form delivered by the proof.

### Repair (synchronized across all three tiers)

- The c6 statement is now `∃ C > 0 ∧ ∀ (G : Digraph) (2 < G.n) (w) (hw) (tr), ∑ v, log₂ (tr.W v) ≤ C·(1 + log₂ G.numDistOrders)`: ∃C is moved to the front, matching c8 and the quantifier structure of `IntervalDAGBound`. The guided/ladder tested statements match token for token; the bare tier has no c6, and the main theorem is unchanged.
- The docstring, `instruction.md`, and `checkpoints.json` now specify that the constant is uniform over all graphs.
- The explicit +1 and interval-construction comparison are unchanged (see c6 above).


## Complete arc coverage and event classification

`DijkstraTrace` records exactly one event per outgoing arc. This requirement
is essential for comparison accounting: on a complete three-vertex graph,
a log that only inserts the two other vertices from the source would omit
the comparison on arc 1→2, even though its insertion order and scan order
are otherwise consistent.

The three event classes follow [the source paper, Section 4 and Lemma 4.2](https://arxiv.org/html/2311.11793v4#S4).
The algorithm processes every outgoing arc. An `ins` event handles an
unlabeled target, a `relax` event handles a labeled, unscanned target, and
a `skip` event handles an already scanned target. Every `relax` records the
distance comparison, even if no decrease-key follows. Checking whether a
target is scanned does not compare arc-length expressions and therefore
contributes no comparison-model cost.

`arc_covered`, together with `arc_ok` and `block_nodup`, requires exactly one
event for every outgoing arc. `skip_valid` requires the target of each skip
to have an earlier scan index. The insertion-count, insertion-before-scan
and relaxation-validity fields force the remaining events into their
appropriate classes. In particular, a previously labeled forward target
cannot be reinserted or skipped to avoid its comparison. The `insCount`,
`insEvents`, and `relaxCount` filters assign zero to skips.

`TraceSemantics.lean` supplies kernel-checked examples on a complete
zero-weight graph, including a failed comparison and all backward skips.
Its negative cases show that omitting a comparison, omitting backward
arcs, and relabeling a forward comparison as a skip cannot produce a legal
trace. The regression module imports the provided theorem statement but
does not use its unfinished proof.
