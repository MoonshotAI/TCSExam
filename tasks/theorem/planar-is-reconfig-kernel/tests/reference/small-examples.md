# Executable Small Examples — Behavioral Checks for the `PlanarISReconfigKernel` Definition Layer

Hand-checkable examples run a Python mirror of the definition layer and record the actual output; they serve as unit tests for these definitions.

- Test file: `small_examples.py` (E1–E7 all passed; run with `python3 small_examples.py`; final line: `ALL SMALL-EXAMPLE CHECKS PASSED`).

## Design: what can and cannot be run

- All definition-layer concepts (`TJStep`/`Reconf`/`ReconfIn`, `projClass`/`C1`/`C2`/`C3`/`N2`/`N3`, the branch-set definition of `HasK3rMinor`, the `bigClass` threshold, the per-class rules for `TrimCon`, and three constant functions) are computable on finite graphs. They are mirrored directly in Python using a 0/1 adjacency matrix.
- The Lean statements themselves (the theorem forms of the checkpoints) are not compiled locally (Lean/lake are unavailable; compilation is left to the platform). These examples check that the semantics of the definition-layer predicates agree with the paper's concepts on small cases, especially open/closed boundary choices and degenerate cases.
- Two expected values were initially wrong during development and were corrected by the examples; both are recorded here. For E5d, the first attempt at the case-2 threshold had |C2| = 33, which did not exceed 40 (the arithmetic check of q(N2(3r−2)+k) is the point of the example). For E6c, it was initially thought that a path on 3 vertices had no K_{3,0} minor; under the branch-set definition, its three singleton sets form a valid K_{3,0} model, consistent with c2/c3's degenerate analysis at r = 0.

## Small-example catalog

Each item gives the check, the hand-computed expected value, and the observed result. All truth values are found by exhaustive enumeration in the script (reachability uses BFS on independent sets; minors use branch-set enumeration).

| ID | Check | Expected | Result |
|---|---|---|---|
| E1a | Path P3, k=1: {0} → {2} reachable (one token-jump move) | Reachable | Pass ✓ |
| E1b | K2, k=1: {0} → {1} reachable (TJ permits jumping to any vertex, including one adjacent to the source) | Reachable | Pass ✓ |
| E1c | Triangle, k=1: every singleton can reach every other singleton | All reachable | Pass ✓ |
| E1d | Path P4, k=2: {0,2} → {1,3} (via {0,3}; direct jump to {1,2} is not independent) | Reachable | Pass ✓ |
| E1e | Star K1,4, k=2: {1,2} → {3,4} is reachable in G but not after removing vertex 4 from W (`ReconfIn` restriction semantics) | Reachable in one case, not in the other | Pass ✓ |
| E2a | Six-vertex case (X = {0,1}; one vertex of class 1, one of class 0, two of class 2): C1 = {2,4}, C2 = {3,5}, C3 = ∅, N2 = 1, N3 = 0 | Exact agreement field by field | Pass ✓ |
| E2b | Same case: V = X ∪ C1 ∪ C2 ∪ C3 (a complete partition) | Equal | Pass ✓ |
| E2c | Same case: `projClass {0,1}` is exactly {3,5} (class-membership semantics) | Equal | Pass ✓ |
| E3a | Boundary case of Lemma 7: X = {0,1,2}, two vertices in class C3 (r = 3): |C3| = 2 = (r−1)·N3, attaining equality | Equality holds | Pass ✓ |
| E3b | Same case: no K_{3,3} minor (5 vertices) | None | Pass ✓ |
| E3c | Add a third vertex to the same class: a K_{3,3} minor appears (the class itself is a K_{3,3} subgraph) | Present | Pass ✓ |
| E4a | Lemma 6 scenario: X = {0,1} with one edge, C1 = {2,3} isolated vertices, q = 2, k = 1: premise qk ≤ |C1| holds | Holds | Pass ✓ |
| E4b | Same case: {0} → {1} is reachable (via C1) | Reachable | Pass ✓ |
| E4c | Same case: sequence lies in X ∪ Im (the whole graph in this example) | Holds | Pass ✓ |
| E5a | Construction 13 threshold: q = 4, r = 2, k = 2, one 25-vertex class 2 (large-class threshold q(2r−1)+1 = 13); case-2 condition is |C2| = 25 > q(N2(3r−2)+k) = 24 | Triggered | Pass ✓ |
| E5b | Same case: take I of size 6 = N2(3r−2)+k vertices (the class itself is independent) | Correct size | Pass ✓ |
| E5c | Same case: rich rule (6 ≥ 3r−1 = 5) retains all 6 points of C_Y ∩ I; |W ∩ C2| = 6 ≤ q(N2(4r−1)+k) = 36 and |I ∩ W| = 6 ≥ k | Holds | Pass ✓ |
| E5d | Two-class case (28-vertex and 13-vertex large classes, N2 = 2): case-2 condition 41 > 40 | Triggered | Pass ✓ |
| E5e | Same case: class A is rich (7 ≥ 5) and retains 7; class B is poor (3 ≤ 4) and retains an independent set of 2r = 4 vertices disjoint from I | Correct count | Pass ✓ |
| E5f | Same case: |W ∩ C2| = 11 ≤ q(N2(4r−1)+k) = 72 | Holds | Pass ✓ |
| E5g | Same case: |I ∩ W| = 7 ≥ k = 2 (exactly the 3 I-vertices from the poor class are lost; upper bound N2(3r−2) = 8) | Holds | Pass ✓ |
| E6a | K_{3,3}: has a K_{3,3} minor and no K_{3,4} minor (6 vertices cannot support 7 disjoint nonempty branch sets) | Has one, not the other | Pass ✓ |
| E6b | Triangle has a K_{3,0} minor (three singleton branch sets, with no cross-edge condition) | Present | Pass ✓ |
| E6c | Path P3 has a K_{3,0} minor (singleton sets are connected; confirms the degenerate analysis “K_{3,0}-minor-free iff at most 2 vertices”) | Present | Pass ✓ |
| E7a | For r = 1, 2, 3: K(r) ≥ 2 + q + q(B(3r−2)+1) + (r−1)B (assembly bound covering the untrimmed branch) | Holds | Pass ✓ |
| E7b | For r = 1, 2, 3: K(r) ≥ 3 (covers the trivial yes-branch where |W| ≤ 3k) | Holds | Pass ✓ |
