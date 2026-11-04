# Executable Small Examples — Behavioral Checks for the Caccetta–Häggkvist Definition Layer and Special Cases

Small hand-computable or exhaustively enumerable examples check task statements and definitions and record the actual output; they serve as unit tests for the definition layer.

- Script: `tests/reference/verify_small_examples.py` (pure Python, no dependencies; all checks passed in 2.9 seconds). Lean-side validation was run inside the pinned `tcs-lean-base:5b3f719` container (toolchain leanprover/lean4:v4.33.0-rc1).

## Part 1: Python exhaustive checks (numerical anchors for the statements)

The script `verify_small_examples.py` exhaustively checks the mathematical content of the statements directly, without going through Lean.

| ID | Check | Expected | Actual result |
|---|---|---|---|
| A | Five (n,k) pairs listed by `sc_circulant`: in the directed circulant graph (steps 1..k), every vertex has out-degree exactly k and girth exactly ⌈n/k⌉ (a cycle of that length exists, and no shorter cycle exists) | All true | (4,1)→⌈4/1⌉=4, (5,2)→3, (7,2)→4, (7,3)→3, (10,3)→4; all True ✓ |
| B | k=1: every acyclic directed graph with n ≤ 4 and minimum out-degree ≥ 1 (2,429 graphs) contains a directed cycle of length ≤ n | No counterexample | All 2,429 have a cycle ✓ |
| C | k=2: every acyclic directed graph with n ≤ 5 and minimum out-degree ≥ 2 (161,308 graphs) contains a directed cycle of length ≤ ⌈n/2⌉ | No counterexample | All 161,308 satisfy the claim ✓ |

Group A shows that the `sc_circulant` statement is true and its bound cannot be improved (it witnesses tightness of the conjecture). Groups B/C show that special cases `sc_k1`/`sc_k2` agree with the paper's claims on small graphs; k=1 and k=2 are already proved cases, so these are numerical restatements, not proofs.

## Part 2: Lean runs (behavioral anchors for the definition layer)

The shipped `Task/Basic.lean` was run inside the pinned image with proofs inserted into the theorem slots; this was for validation only and is not published with the task.

| ID | Check | Expected | Actual result |
|---|---|---|---|
| L1 | Fill the `sc_k1` slot with a complete proof (following outgoing edges for n+1 steps forces a repetition; take the shortest repeated-index segment to extract a simple cycle) | Compiles, axioms within whitelist | 0 compile errors; `#print axioms` = [propext, Classical.choice, Quot.sound] ✓ |
| L2 | Fill the `sc_circulant` slot with `decide` | Compiles, axioms within whitelist | About 36 seconds, 0 errors; same axioms ✓ (requires `set_option maxRecDepth 1000000` from the fixed zone; default depth is insufficient) |
| L3 | Original shipped file (five `sorry` slots), `lake build Task` | Exactly 5 `sorry` warnings, no errors | Exactly 5 ✓ |

## Issues found

- **Silent `sorry` recovery for `D.cycSucc`**: The verification draft's arc condition was once written as `show D.adj ... (D.cycSucc t) ...`. When name resolution failed, Lean 4.33-rc1 recovered with `sorry`, exited with code 0, and printed no error. Only `#print axioms` exposed `sorryAx`. This illustrates why the grading chain does not trust exit codes and checks the axiom whitelist. The draft was fixed to use the explicit `Digraph.cycSucc` name, after which the axiom check was clean.
- **Kernel recursion depth:** `decide` on `sc_circulant` exceeded the default `maxRecDepth`, so the fixed zone sets `set_option maxRecDepth 1000000` (affects elaboration resources only; the kernel still checks the full proof). With this option it passed in 36 seconds.
- **`omit ... in` syntax:** This toolchain's mathlib version does not support `omit [Fintype V] in theorem` after a docstring. The definition layer was changed to use explicit binders (`outDegree` and the Decidable instances each carry `[Fintype V]`).
