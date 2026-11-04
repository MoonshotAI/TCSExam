# Small examples — lean-dijkstra-universal (executable small examples)
For task authors checking small instances and event-accounting regressions.

This is the second fidelity check: reimplement the Lean definition-layer predicates and cost semantics in pure Python, then run them on small graphs; script at `small_examples.py`.

Run details: with local Python 3; runtime was about 20 seconds.

## Results summary (all PASS)

each row gives one small example, the checked claim, and its result.

| Example | Check | Result |
|---|---|---|
| E1 | Both directions of Lemma 3.1: over 2642 (graph, vertex-order) pairs, when the combinatorial characterization holds, the constructed arc lengths are realized (true distance = rank); when it does not hold, none of the random arc-length samples realizes it | PASS (`tested=2642`) |
| E2 | Lemma 4.2: simulate Dijkstra traces on 212 random graphs; number of relaxations ≤ F − n + 1; slack (F−n+1−relax) has minimum 0 and maximum 4, including equality cases | PASS |
| E3 | Semantics of Lemma 7.3: maximum of `∑ log₂ W(v) / (1 + log₂ D)` is 0.931 (constant C ≥ 1 suffices, leaving slack in the packaged ∃C form) | PASS |
| E4 | Interval-DAG bound of Van et al.: over 300 random interval families, maximum of `∑ log₂(length) / (1 + log₂ D(I))` is 1.268 | PASS |
| E5 | c7(a)(b): simulate 200 runs of random heaps with deletions; `|Hᵢ| ≤ 2^(2^(i+1))` and the partial-work-set lower bound `2^(2^(i−1)) − 2^(2^(i−2))` hold throughout | PASS |
| E5c | c7(c): with exact Lean semantics (empty heaps remain in the list), heap count is always ≤ `1 + ⌊log₂⌊log₂(t−1)⌋⌋` | PASS |
| E6 | Trace-validity checker: 212 simulated runs satisfy every `DijkstraTrace` field constraint (scan permutation, source scanned first, valid arcs, no duplicates within a block, insertion count, insertion before scan, constraints on both ends of relaxations, and scan order matching true distances). This shows the trace constraints are satisfiable and directly guards against vacuous truth. | PASS |
| E7 | Degenerate shapes: path graph D=1, F=n−1, W all 1, relax=0; star graph D=(n−1)!, F=n−1; 3-vertex complete graph D=2, F=3 | PASS |

## Issues found and fixed by the small examples (recorded for reviewers)

1. The first E5 simulation removed an empty heap from the list on deletion (unlike Lean's `heaps.set` semantics), causing many false failures in E5a. Keeping the empty heap in the list fixed the check. This also confirms that the Lean model (`List.set`, which does not remove empty heaps) is consistent with the paper's invariant argument.
2. The first Python copy of `trace_W` in E7 added 1 too many (`cumIns` already includes the implicit source insertion), so W was all 2 on a path graph instead of 1. The corrected formula `W = cumIns(scanIdx) − insRank` matches the Lean definition exactly and passed. This bug was only in the Python copy and did not affect the Lean definition; it prompted a second check of the Lean definition's 0/1-based indexing.

## Boundary checks (against the step 6.5 self-check)

- The +1 term in c6 is needed when D = 1 (counterexample in c6 of `concept-ledger.md`: D=1 while `∑ log₂ W ≥ 1`). This coexists with the E3 random-sample ratio bound of 0.931: the counterexample has D=1 and ratio 1/1 = 1, and a hand-built check confirms that random sampling in E3 does not cover it.
- For t = 1 (zero insertions), c7(c) gives `Nat.log 2 (Nat.log 2 0) = 0`, so the bound is 1 while the heap count is 0 ✓.
- For c7(b) at i = 1, the lower bound is `2 − √2 ≈ 0.586 < 1 ≤ t − x` ✓ (`t − x ≥ 1` because x ≤ t−1).


## Arc-event regression checks

`TraceSemantics.lean` checks arc coverage and comparison accounting directly
against the Lean type. On a complete three-vertex graph with zero arc lengths, the source inserts both
other vertices, arc 1→2 records one unsuccessful comparison, and the three
backward arcs record skips. The checks establish `relaxCount = 1`, insertion
list `[1, 2]`, and working-set sizes `[1, 2, 1]`.

The same module proves that omitting the comparison, omitting backward
arcs, and classifying the forward comparison as a skip cannot produce a
legal trace. It also constructs the complete legal trace, so the coverage
requirements are checked for satisfiability in this example.

Run from the task project with
`lake env lean /path/to/tests/reference/TraceSemantics.lean` after building
`Task`. Compilation must run in an isolated CPU environment; the module uses
kernel-checked `decide` and no `native_decide`.
