# Independent Retranslation Cross-Check: Universal Optimality of Dijkstra's Algorithm
For task authors independently checking the stated theorem against the paper.

This third fidelity pass restates the paper's key claims after a several-hour gap and a compilation cycle from the first pass made while writing the Lean statements, then compares each item with Lean. Ambiguities are recorded below.

- Comparison text: arXiv 2311.11793v4.

## Retranslation record

### Lemma 3.1 (c1)

Second-pass restatement: a total order L of the vertices is a distance order iff every non-source vertex w has an incoming arc vw with v preceding w in L. In §3, “distance order” is defined to mean that some assignment of nonnegative arc lengths gives pairwise distinct true distances from the source, and L lists vertices in increasing order of true distance.

Comparison with Lean: `IsDistOrder L ↔ ∃ w, Nonneg w ∧ (d* pairwise distinct) ∧ (L u < L v ↔ d* u < d* v)`. Match. Ambiguity: “the order is strictly increasing by true distance” means “u comes before v in L iff true distance to u is strictly smaller” (both directions); Lean uses iff ✓. A one-way implication (⟹) would also suffice for the two proof directions but would state less. Here the paper's intent is confirmed as the biconditional: “ordered by increasing true distance,” with distinct distances, gives a strict total-order correspondence.

### Lemma 4.2 (c2)

Second-pass restatement: in one run, there are at most F − n + 1 comparisons outside the heap, and at most F − n + 1 decrease-key operations. When scanning v, every arc vw into an already-labeled w causes one comparison outside the heap; such an arc is forward in the scan order. Exactly n − 1 forward arcs trigger insertions and do not cause an outside-the-heap comparison.

Comparison with Lean: `relaxCount ≤ maxForwardArcs − n + 1`. In the trace model, every outgoing arc is recorded exactly once.
A relax event processes an arc uv when v is labeled and unscanned, including
failed comparisons; an insertion handles an unlabeled target, and a skip
handles an already scanned target. This matches Section 4 and Lemma 4.2.
See the complete-arc-coverage explanation in `concept-ledger.md` and the
positive and negative cases in `TraceSemantics.lean`. The decrease-key bound is not stated separately (it is subsumed by the comparison bound). This is an intentional narrowing of scope: the proof of c8's comparison upper bound needs only the comparison bound.

### Lemma 6.1 (c3)

Second-pass restatement: in the time model, every correct deterministic algorithm needs at least max{n−2, m−2n+2} time in the worst case. For each i < n−1, either the adjacency list of v_i is fully accessed, or an arc v_i v_j with j > i+1 can be hidden to make the output wrong. The total is therefore either at least m − (2n−2) adjacency-list accesses or n−2 fully accessed lists. The whole paper assumes n > 2.

Comparison with Lean: agrees. Ambiguity: the proof of Theorem 6.5 combines the lower bounds as Ω(max{n−2, m−2(n−1), log D}); m−2(n−1) equals m−2n+2 ✓. c3 uses the max form, while c8(iv) combines them into (m + log₂ D)/C.

### Lemma 6.2 (c4)

Second-pass restatement: in the comparison model, every correct deterministic algorithm needs at least ⌈log₂ D⌉ comparisons in the worst case (log base 2; footnote 1). For each of the D distance orders, choose an arc-length assignment with strictly positive lengths and pairwise distinct true distances. Perturb away outcomes equal to 0. The D assignments follow D distinct paths through the decision tree. The relevant subtree is binary, has at least D leaves, and has a leaf at depth ≥ ⌈log₂ D⌉.

Comparison with Lean: `log₂ D ≤ comparisons` over the reals is equivalent to the natural-number comparison count being at least ⌈log₂ D⌉ ✓. No n > 2 assumption is needed ✓.

### Lemma 6.4 (c5)

Second-pass restatement: in the comparison model, every correct deterministic algorithm needs at least F − n + 1 comparisons in the worst case. Choose a distance order L with exactly F forward arcs. Give each forward arc v_i v_j length j−i, and every non-forward arc the same sufficiently large length. If the execution path uses at most F−n comparisons, turn its strict inequalities into equalities and additionally fix the lengths of all v_i v_{i+1} arcs (at most n−1 of them). At most F−1 equations constrain F variables, leaving a solution space that contains a line. Move along the line until a forward-arc length reaches 0, then perturb so exactly one forward arc with j > i+1 has length 0. The algorithm's output is unchanged, but L is no longer an order by true distance.

Comparison with Lean: `((F:ℝ) − n + 1) ≤ comparisons` ✓. The paper uses “L is the unique distance order” and distinct true distances here (the assignment of forward-arc length j−i gives d*(v_i) = i−1) ✓, from the same construction as c1.

### Lemma 7.3 (c6)

Second-pass restatement: in a run, ∑_v log W(v) = O(log D), where W(v) is the number of vertices inserted between inserting and removing v, including v. Let the insertion order be v_1..v_n and the intervals be [a_i = i, b_i], where b_i is the total number of insertions by the time v_i is removed. Every topological order of the interval DAG I gives a topological order of the search tree T (each arc uv of T satisfies b_u < a_v because v is inserted only after u is removed); every topological order of T is a distance order. Then apply the interval-counting lemma of Van et al.

Comparison with Lean: ∃ C>0, ∀ G w tr, ∑ log₂ W v ≤ C(1 + log₂ D), with a single C for all graphs. This is the form after the quantifier position was repaired. Difference: +1 is explicit (the literal O(log D) claim is false at D=1; see the counterexample for c6 in `concept-ledger`). The Van et al. result is packaged as the `hidag` premise. Match.

### §10.2 (c7)

Second-pass restatement: Lemma 10.2 says |H_i| ≤ 2^{2^i} at all times. Lemma 10.4 says that if i > 0 and H_i changes during an insertion, then at the start of that insertion (after creating the new H_0), |H_{i−1}| > 2^{2^{i−1}} − 2^{2^{i−2}}. Corollary 10.5 says that when i > 1, the working set of an item in H_i has size > 2^{2^{i−2}} − 2^{2^{i−3}}. Lemma 10.3 says there are at most 1 + log log n inner heaps, where n is the total number of insertions.

Comparison with Lean (0-based `heaps[i]` corresponds to the paper's H_{i+1}): (a) |heaps[i]| ≤ 2^{2^{i+1}} ✓ (reindexing Lemma 10.2); (b) if i ≥ 1 and x ∈ heaps[i], then 2^{2^{i−1}} − 2^{2^{i−2}} < t − x ✓ (reindexing Corollary 10.5; “working set size” is replaced by the current partial count, which the proof supports at every time; see `concept-ledger`); (c) heaps.length ≤ 1 + ⌊log₂⌊log₂(t−1)⌋⌋ ✓ (integer form of Lemma 10.3; equivalence derivation in `concept-ledger`).

### Theorem 7.4 and Theorems 6.5/6.6 (c8)

Second-pass restatement: the main theorem combines three results. Theorem 6.5: every correct deterministic algorithm in the time model needs Ω(m + log D). Theorem 6.6: in the comparison model, every correct deterministic algorithm needs Ω(F − n + 1 + log D). Theorem 7.4: Dijkstra's algorithm with a working-set-bound heap takes O(m + log D) time and O(F + log D) comparisons. Hence it is universally optimal in time, and universally optimal in comparisons up to an additive n term.

Comparison with the five-way Lean conjunction: (i) it runs, (ii) time upper bound, (iii) comparison upper bound, (iv) time lower bound, (v) comparison lower bound. Ambiguities: (1) the paper's definition of universal optimality (§5) is that on every graph, cost is within a constant factor of the cost required by any correct algorithm under the worst edge-weight assignment. The ratio form of (ii)+(iv) implies this predicate (with constant C²); the direction is recorded here. The result was split into upper and lower bounds so each part is directly provable and comparable. (2) The comparison gap F − (F−n+1) = n−1 is exactly the paper's “additive term in n” ✓. (3) The `hidag` premise follows the packaging policy and does not change the theorem; Van et al. is a published, proved lemma.

## Conclusion

The second-pass restatement agrees item by item with the Lean statements. All intentional scope restrictions, explicit conditions, and reindexings are documented in `concept-ledger` and this file. The trace abstraction requires complete arc coverage and accounts for the
comparisons specified in Section 4 of the paper.
