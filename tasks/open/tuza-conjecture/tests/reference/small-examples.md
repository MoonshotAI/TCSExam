# Executable Small Examples — Behavioral Checks for the Tuza-Conjecture Definition Layer

Small hand-computable graphs exercise Lean definitions (values of τ/ν, triangle sets, and triangle edge sets) and record the actual output; they serve as unit tests for the definition layer.

- Test file: `Probe.lean`, compiled with `lake env lean Probe.lean` inside a copy of the task app, using image `tcs-lean-base:5b3f719` and toolchain leanprover/lean4:v4.33.0-rc1.

## Design notes

Definitions of τ/ν (powerset filters plus `Finset.min'`/`max'`) use only computable operations on `Finset`/`Quot` and decidable instances for `SimpleGraph`, so they are **computable**: kernel `decide` evaluates small graphs directly (`native_decide` is prohibited by lexical scanning of task statements and is never used; proof terms from kernel `decide` introduce no extra axioms, as confirmed by the `#print axioms` whitelist). Hand-computed expectations come from §1 of concept-ledger.

Recursion depth: powerset search over cover/packing candidates exceeds the default `maxRecDepth` (512); on the first probe, `decide` reported `maximum recursion depth has been reached`. The definition layer sets `set_option maxRecDepth 8192` in the fixed zone before END OF FIXED PART; this is shipped unchanged to the grading variant, after which all small examples pass.

## Small-example table (; all passed)

| ID | Check | Hand-computed expectation | Actual result |
|---|---|---|---|
| E1 | Cover number τ of K₄ | 2 (two disjoint edges cover all four triangles; a single edge cannot) | `decide` passes ✓ |
| E2 | Packing number ν of K₄ | 1 (the four triangles pairwise share an edge) | `decide` passes ✓ |
| E3 | Two vertex-disjoint triangles (`twoTriangles`, Fin 6) | τ = 2, ν = 2 (τ = ν, strictly less than 2ν) | `decide` passes ✓ (two checks) |
| E4 | Empty graph on 5 vertices (no triangles) | τ = 0, ν = 0 (empty cover, empty packing) | `decide` passes ✓ (two checks) |
| E5 | Triangle membership and edge set in K₄ | `{0,1,2}` is a triangle; its edge set is exactly `{01,02,12}` | `decide` passes ✓ (two checks; default depth suffices) |
| E6 | K₄ with one edge removed | Two remaining triangles share the opposite edge: τ = 1, ν = 1 | `decide` passes ✓ (two checks) |
| E7 | Number of triangles in K₄ | 4 | `decide` passes ✓ (default depth suffices) |

## Issues found

- **Default recursion depth is insufficient:** nested evaluation over candidate subsets (64 edge subsets for K₄), triangle filtering, and disjointness checks exceeds 512. Resolution: pin `maxRecDepth 8192` in the fixed zone. The model does not need to know about it; grading variants inherit the same fixed zone and behave consistently (partial-c1/c3 passed).
- **Axiom cleanliness of kernel `decide`:** E1–E7 are proved with `by decide`; the grading chain's `#print axioms` whitelist was checked in practice (all three checkpoints PASS in partial-all), confirming kernel evaluation adds no extra axioms such as `Lean.ofReduceBool`.
