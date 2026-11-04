# Executable Small Examples: Checking the GNRS Definition Layer

Hand-computable graphs are used to check Lean's definitions of `spDist` values, `WalkSeq` membership, `l1Dist` evaluation, and the bridge `spDist` ↔ mathlib `dist`. Actual output from each run is recorded below.

- Probe file: `Probe2.lean`. In the task app copy, it was checked with `lake build Task`, then compiled using `lake env lean Probe2.lean`. Validation image: a Lean image; Lean 4.33.0 release; mathlib pinned at 5b3f719.

## Design notes

The definitions of `spDist` and `WalkSeq` use only computable operations on `Finset`/`Fin` and decidable graph adjacency, so they are **kernel-computable**: on small graphs, `decide` evaluates them directly (`native_decide` is lexically prohibited by the task, so it is never used; kernel `decide` introduces no extra axioms). The hand-computed expected values come from the definition correspondence in Section 1 of `concept-ledger.md`.

The probe includes `set_option maxRecDepth 32768`, the same setting as the fixed prefix. `set_option` does not propagate across files, so the probe needs its own declaration. The judging variants inherit the fixed prefix and behave the same (empirically, all three positive gates pass).

## Small-example results (; all passed)

| ID | Check | Hand-computed value | Actual output |
|---|---|---|---|
| E1 | cycle4.spDist 0 1 | 1 (adjacent) | `decide` passed ✓ |
| E2 | cycle4.spDist 0 2 | 2 (opposite vertices) | `decide` passed ✓ |
| E3 | cycle4.spDist 0 0 | 0 | `decide` passed ✓ |
| E4 | cycle4.spDist 1 3 | 2 (opposite vertices) | `decide` passed ✓ |
| E5 | k23.spDist 0 1 | 2 (same side, through a leaf) | `decide` passed ✓ |
| E6 | k23.spDist 0 2 | 1 (adjacent across the bipartition) | `decide` passed ✓ |
| E7 | k23.spDist 2 3 | 2 (leaf to leaf, through the center side) | `decide` passed ✓ |
| E8 | k23.spDist 3 4 | 2 | `decide` passed ✓ |
| E9 | starGraph 3:.spDist 0 2 | 1 (center to leaf) | `decide` passed ✓ |
| E10 | starGraph 3:.spDist 1 3 | 2 (leaf to leaf) | `decide` passed ✓ |
| E11 | starGraph 4:.spDist 4 3 | 2 | `decide` passed ✓ |
| E12 | cycle4.WalkSeq 0 2 2 | True (a walk of length 2 exists) | `decide` passed ✓ |
| E13 | ¬ cycle4.WalkSeq 0 2 1 | True (no walk of length 1 exists) | `decide` passed ✓ |
| E14 | ¬ k23.WalkSeq 0 1 1 | True (same-side vertices are not adjacent) | `decide` passed ✓ |
| E15 | k23.WalkSeq 0 1 2 | True (0-2-1) | `decide` passed ✓ |
| E16 | cycle4.dist 0 2 = 2 (via `spDist_eq_dist`; reachability and `spDist` are each decided directly) | 2 | Passed ✓ |
| E17 | k23.dist 2 4 = 2 (same bridge) | 2 | Passed ✓ |
| E18 | l1Dist (0,0) (1,1) = 2 (diagonal in the C₄ embedding) | 2 | `norm_num` passed ✓ |
| E19 | l1Dist (1,1,0,0) (1,0,1,0) = 2 (leaf-to-leaf in the K_{2,3} embedding) | 2 | `norm_num` passed ✓ |
| E20 | Shape of the `IsPlanar` predicate (unfolding gives the Wagner-form conjunction) | `Iff.rfl` | Passed ✓ |

## Run record

- First run: `lake build Task` succeeded (8,691 jobs, exactly the 5 expected `sorry` warnings). E5–E11 in the probe exceeded the recursion-depth limit under the default `maxRecDepth`; `starGraph` was also ambiguous because mathlib now defines `SimpleGraph.starGraph` and both namespaces were open.
- Second run: after setting the recursion limit in the probe and using fully qualified names, E1–E19 passed. Brute-force `spDist` on `starGraph 5` (6 vertices; function-space size on the order of 6⁶) still exceeded depth 32768; replacing it with `starGraph 4` (similar scale to k23) passed.
- Consistency with judging: the c2 `decide` distance table (16 pairs) passed in the judging variant with the positive gate. Brute-force `decide` for c3 exceeded the heartbeat limit; the proof was changed to use API lemmas (`spDist_eq_one_of_walkSeq` / `spDist_eq_two_of_walkSeq`), which passed in the judging variant.md`.

## Issues found

- **`set_option` does not propagate across files:** the fixed prefix's `maxRecDepth` setting applies only in that file, so the probe must set it itself. The judging variant shares the fixed prefix with the shipped task and is unaffected.
- **New mathlib declaration `SimpleGraph.starGraph`:** the pinned mathlib version already has this name, making it ambiguous with the package's `GNRSConjecture.starGraph` when both namespaces are open. There is no conflict inside the package without `open SimpleGraph`; the probe uses the fully qualified name. The definitions are independent and do not refer to each other.
- **Bounded `decide` search on large function spaces:** brute-force `spDist` on a 5-vertex graph works at depth 32768 (as measured on k23); a 6-vertex graph exceeds the limit. Formal proofs therefore use API lemmas for c3 or `decide` on the small table for c2, not large searches.
