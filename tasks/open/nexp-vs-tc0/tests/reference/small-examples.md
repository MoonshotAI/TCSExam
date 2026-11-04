# Executable Small Examples — Behavioral Checks for the NEXP vs. TC⁰ Definition Layer

Small hand-computable inputs exercise Lean definitions (circuit evaluation/depth/size, threshold gates, description-circuit decoding, the SUCCINCT-SAT family) and record the actual output; they serve as unit tests for the definition layer.

- Test method: Probe files (about 80 lines of `example ... := by decide` assertions) run inside a sandbox copy of the task app using `lake env lean Probe.lean` (a Lean validation image, toolchain v4.33.0-rc1 from the pinned toolchain family, mathlib pinned at 5b3f719). Probes are not shipped in the task package to prevent leakage; all assertion contents are recorded here.

## Design notes

Evaluation and depth are structurally recursive on the number of gates processed (`wireValuesUpTo`/`wireDepthsUpTo`); the level function uses counting (`succSatVarsGo`) rather than `Nat.sqrt`; description-circuit decoding (`markedWires`/`descGate`/`descCircuit`) is also structurally recursive. **All are kernel-computable**, so `decide` directly evaluates small instances (`native_decide` is prohibited by lexical scanning of the task statement and is never used; kernel `decide` introduces no extra axioms). Hand-computed expected values are from concept-ledger, §§1–2.

Encoding length at level n: `succLen n = (n+1)·(1+2·(3n+1)) = (n+1)(6n+3)`, giving 3, 18, 45, 84, … . A description circuit at level n has 2n+1 primary inputs (n clause-index bits + n variable-index bits + 1 sign bit), n internal gates, and 1 output gate. Each gate has a block (1 type bit + (3n+1) connection bits + (3n+1) negation bits); gate g scans only connection bits with indices < 2n+1+g.

## Small-example table (run in a sandbox; all passed, probe output only `PROBE_DONE`, no errors)

| ID | Check | Hand-computed expectation | Actual result |
|---|---|---|---|
| E0a | `succLen 0 / 1 / 2 / 3` | 3 / 18 / 45 / 84 | `decide` passes ✓ |
| E0b | `succSatVars 0 / 2 / 3 / 17` | 0 / 0 / 0 / 0 | `decide` passes ✓ |
| E0c | `succSatVars 18 / 44 / 45 / 84` | 1 / 1 / 2 / 3 | `decide` passes ✓ |
| E1a | `sampleXorCircuit.depth` | 2 (two internal-gate layers + output-gate layer) | `decide` passes ✓ |
| E1b | `sampleXorCircuit.size` | 3 (G + M = 2 + 1) | `decide` passes ✓ |
| E1c | `sampleXorCircuit` truth table = XOR of all 4 inputs | thr1=OR, thr2=AND, output=thr2(OR,¬AND) | `decide` passes ✓ |
| E2a | `andFamily 3` on (1,1,1) / (1,0,1) | true / false | `decide` passes ✓ |
| E2b | `orFamily 3` on (0,0,1) / (0,0,0) | true / false | `decide` passes ✓ |
| E3a | `tc0Basis` thr 2 on (1,1,0) / (1,0,0) | true / false | `decide` passes ✓ |
| E3b | `tc0Basis` thr 0 on (0,0,0) (empty sum ≥ 0) | true | `decide` passes ✓ |
| E3c | `tc0Basis` thr 3 on (1,1,1) (AND = thr n) | true | `decide` passes ✓ |
| E4a | `markedWires x 0 3`, with connection bits 1 and 3 set in x | [0, 2] (collect set bits in range, in order) | `decide` passes ✓ |
| E4b | `markedWires x 0 1` (same x, range narrowed to 1) | [0] (out-of-range set bit is ignored) | `decide` passes ✓ |
| E4c | `markedWires x 0 3`, with one additional set bit at out-of-range position 4 | [0, 2] (out-of-range connection bit is dead) | `decide` passes ✓ |
| E5a | `(descCircuit xSat1).size` (level 1) | 2 (1 internal gate + 1 output gate) | `decide` passes ✓ |
| E5b | `succinctSatFamily 18 xSat1`: g0 = in0∨in1, output = OR(g0); clause c contains literal (v,s) iff c∨v | true (every clause is satisfiable) | `decide` passes ✓ |
| E5c | `succinctSatFamily 18 xUnsat1`: output = AND(¬g0), g0 = AND(∅) = true ⟹ description circuit is identically false | false (every clause is empty) | `decide` passes ✓ |
| E6a | `succinctSatFamily 45 (bit 33)`: output = in2 (variable-index bit 0) | true (σ all 1s satisfies it) | `decide` passes ✓ |
| E6b | `succinctSatFamily 45 (bit 31)`: output = in0 (clause-index bit 0); clause-index bit 0 = 0 gives an empty clause | false | `decide` passes ✓ |
| E6c | `succinctSatFamily 45` (all-zero instance): output gate AND(∅) = true ⟹ description circuit is identically true | true (every clause contains all literals) | `decide` passes ✓ |
| E7a | `clauseInput 1 (c=1) (v=1) true` | (1,1,1) (clause bit / variable bit / sign bit) | `decide` passes ✓ |
| E7b | `clauseInput 1 (c=1) (v=0) false` | (1,0,0) | `decide` passes ✓ |

Instance bit layout: the two 18-bit instances in E5 use block 0 for the internal gate and bits 9–17 for the output gate; every bit is listed in the probe. The 45-bit instances in E6 set a single bit with `fun w => w.val == k`.

## Issues found

- **The probe must build Task olean first:** see the first round in the run log. This is not a definition-layer defect and does not affect the grading chain (each grading variant is complete and does not import Task).
- **Signature of `List.getElem_mem`:** in this pinned toolchain it takes an explicit bound proof (`(h : n < l.length) : l[n]'h ∈ l`). The first iteration used it implicitly and failed to typecheck; fixed by passing `i.isLt` explicitly. This was a development issue; definition-layer semantics are unchanged.
- **Axiom cleanliness of kernel `decide`:** E1c is the same computation as c3. The grading chain's `#print axioms` whitelist was checked in practice (positive gate c3 PASS), confirming kernel evaluation does not introduce extra axioms such as `Lean.ofReduceBool`.
