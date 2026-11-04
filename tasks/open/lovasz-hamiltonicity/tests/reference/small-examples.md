# Executable Small Examples — Behavioral Checks for the Lovász-Conjecture Definition Layer

Small hand-computable graphs exercise definition-layer properties (edge count, degree sequence, Hamiltonian path, triangle-free status of the Petersen graph, and three predicates for complete graphs) and record the actual output; they serve as unit tests for the definition layer.

- Two independent routes: Python computation (`tests/reference/petersen_check.py`, standard library only) and Lean-kernel `decide` (probe `Probe.lean`, image `tcs-lean-base:5b3f719`, toolchain leanprover/lean4:v4.33.0-rc1).

## Design notes

All key Petersen-graph properties (vertex-transitivity, Hamiltonian path, no Hamiltonian cycle) are directly computable and do not rely on secondary descriptions in the literature. Decidability of `Walk.IsHamiltonian` is provided by the definition-layer instance `SimpleGraph.decWalkIsHamiltonian` (universal quantification + `List.count`, directly evaluated by kernel `decide`; `native_decide` is prohibited by lexical scanning of the task statement and is never used). Hand-computed expectations come from §1 of concept-ledger and standard graph facts: Petersen graph has 10 vertices, 15 edges, is 3-regular, has girth 5, has automorphism group of order 120, and is hypohamiltonian.

Recursion depth: the `decide` used by the c1 grading case (count on a support of 10 elements) works at the default `maxRecDepth` (512), confirmed by probe L3, so the definition layer does not need a pinned depth. Deeper filtering by `cliqueFinset 3` (120 triples) occurs only in the probe; the probe file locally sets `maxRecDepth 8192` (L5), outside the definition layer and grading variant.

## Python small-example table (; 11/11 passed)

| ID | Check | Expected | Actual result |
|---|---|---|---|
| A1–A3 | Basic parameters of the Petersen graph | 10 vertices, 15 edges, 3-regular | PASS (all degrees are 3) |
| A4 | Girth | 5 (no triangles or 4-cycles) | PASS (girth=5) |
| B1 | Connectivity | 0 reaches all 10 vertices | PASS |
| C1 | Order of the automorphism group | 120 (full order of S₅, characteristic value for the Kneser graph K(5,2)) | PASS (DFS enumerates exactly 120) |
| C2 | Vertex-transitivity | Orbit of vertex 0 covers all vertices | PASS |
| D1–D2 | Lean-side witness `0-1-2-3-4-9-6-8-5-7` | Consecutive vertices adjacent; each vertex appears exactly once | PASS |
| E1 | No Hamiltonian cycle | Backtracking finds no 10-cycle (hypohamiltonian) | PASS |
| F1 | Complete graphs K_n (n=1..8) | Connected, vertex-transitive, and has a Hamiltonian path | PASS |

Run command: `python3 tests/reference/petersen_check.py`; output is 11 lines of PASS with exit code 0 (the log is the actual output from this command; see `PROVENANCE.md`).

## Lean small-example table (; 9/9 passed, PROBE_EXIT=0)

| ID | Check | Expected | Actual result |
|---|---|---|---|
| L1 | `petersenEdges.card` | 15 | `decide` passes ✓ |
| L2 | 3-regularity (`neighborFinset` at every vertex) | Degree 3 at each vertex | `decide` passes ✓ |
| L3 | `petersenHamPath.IsHamiltonian` | True (same `decide` as the c1 grading variant; **default recursion depth**) | `decide` passes ✓ |
| L4 | Length of the witness path | 9 (9 edges on 10 vertices) | `decide` passes ✓ |
| L5 | Triangle-free | `cliqueFinset 3 = ∅` (locally increase recursion depth) | `decide` passes ✓ |
| L6 | Complete positive proof of c1 | `⟨0, 7, petersenHamPath, by decide⟩` | Pass ✓ |
| L7 | Positive proof of c2 (cycle truncation + singleton case) | Compiles | Pass ✓ |
| L8 | Positive proof of c3 (`connected_top` + `Equiv.swap`) | Compiles | Pass ✓ |
| L9 | Pointwise support of witness path | `[0,1,2,3,4,9,6,8,5,7]` (compare Python D2) | `decide` passes ✓ |


## Issues found during task authoring

- **Namespace for `Walk.cons`:** first compile reported `Unknown identifier Walk.cons`. The Petersen witness is defined inside namespace `LovaszHamiltonicity`; `Walk` requires `open SimpleGraph (Walk)` (now in the fixed zone).
- **No decidable instance for `IsHamiltonian`:** mathlib's `Walk.IsHamiltonian` is a `def`, and typeclass search does not unfold it, so c1's `decide` could not synthesize `Decidable`. Resolution: add the definition-layer instance `SimpleGraph.decWalkIsHamiltonian` (universal quantification + count, with `[Fintype V]`); probe L3 and grading-chain partial-c1 both pass.
- **Default depth is insufficient for `cliqueFinset`:** filtering over the powerset of 120 triples exceeds 512, similar to the powerset search in Tuza. Since this occurs only in the extra probe example L5, no depth pin is added to the definition layer; the grading variant is unaffected (the c1 `decide` passes at default depth).
- **Incorrect declaration order in the sorry-depend case:** inserting a helper theorem after `conj` caused `Unknown identifier`, making the test depend on the wrong failure mechanism. After moving it before `conj` and rerunning, compilation passed but `#print axioms` included `sorryAx`, which the whitelist correctly rejected (`logs/sorry-depend.log`).
