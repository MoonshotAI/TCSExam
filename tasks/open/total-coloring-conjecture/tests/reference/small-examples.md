# Executable Small Examples — Behavioral Checks for the Total-Coloring-Conjecture Definition Layer

Small hand-computable graphs exercise Lean definitions (`TotalColorable` upper/lower chromatic-number tests and numerical `maxDegree`), with an independent Python exhaustive search to cross-check the total chromatic number. Actual outputs are recorded here.

- Test files: `Probe2.lean`, `Probe3.lean`, `Probe4.lean` (compiled inside a task-app copy with `lake env lean`, image `tcs-lean-base:5b3f719`, toolchain leanprover/lean4:v4.33.0-rc1); independent check: `tests/reference/verify_small.py` (pure Python exhaustive enumeration, no code shared with the Lean definitions).

## Design notes

`TotalColorable k` (there exist vertex and edge colorings satisfying three compatibility conditions) depends only on decidable existential quantification over finite types, so it **is decidable**: for small graphs, kernel `decide` evaluates it directly (`native_decide` is prohibited by lexical scanning of the task statements and is never used; proof terms from kernel `decide` introduce no extra axioms, as confirmed by the `#print axioms` whitelist and E9–E12). The total chromatic number χ'' itself is defined using `Nat.find` and cannot be evaluated by the kernel. A numerical claim χ'' = m is assembled from two `decide` checks—upper bound `TotalColorable m` and lower bound `¬ TotalColorable (m−1)`—using API lemmas (`totalChromaticNumber_le` / `le_totalChromaticNumber` / `TotalColorable.mono`). Hand-computed expectations come from concept-ledger §1 and known literature values (χ''(K_n), χ''(K_{n,n}); Behzad–Chartrand–Cooper 1967).

Recursion depth: enumerating coloring functions exceeds the default `maxRecDepth` (512), so the definition layer pins `set_option maxRecDepth 8192` (inside the fixed zone, before END OF FIXED PART, and shipped unchanged into the grading variant); all small examples pass with this setting.

Heartbeat budget: each `by decide` must be its own theorem, since each declaration gets an independent 200,000-heartbeat budget. In the initial probe, two `decide`s and their combined proof were put in one `example`, exceeding the budget (observed `(deterministic) timeout ... maximum number of heartbeats (200000)`). Splitting them into independent helper theorems made all checks pass.

## Small-example table (; all passed)

| ID | Check | Hand-computed expectation | Actual result |
|---|---|---|---|
| E1 | K₃ has a total 3-coloring (upper bound) | Yes (color edge {i,j} with the third color) | `decide` passes ✓ |
| E2 | K₃ has no total 2-coloring (lower bound) | No (three pairwise adjacent vertices need 3 colors) | `decide` passes ✓ |
| E3 | Star K_{1,3} has a total 4-coloring | Yes (one center color + three distinct edge colors; assign remaining colors to leaves) | `decide` passes ✓ |
| E4 | Star K_{1,3} has no total 3-coloring | No (center color + three pairwise adjacent edge colors require 4 distinct values) | `decide` passes ✓ |
| E5 | K_{2,2} has a total 4-coloring | Yes | `decide` passes ✓ (enumerates 4⁴ vertex colorings × 4⁴ edge colorings) |
| E6 | K_{2,2} has no total 3-coloring | No (C₄ has no total 3-coloring with periodic colors) | `decide` passes ✓ |
| E7 | `maxDegree` values | K₃=2, K_{1,3}=3, K_{2,2}=2 | `decide` passes ✓ (all three) |
| E8 | χ''(K₂) = 3 (verbatim example in `instruction.md`) | 3 = Δ+2 (Δ=1) | Compiles ✓ |
| E9–E12 | `#print axioms` on four helper theorems proved with `decide` | Only propext / Classical.choice / Quot.sound | Measured exactly these three ✓ |
| E13–E15 | Full proof forms of the three checkpoints (χ'' = 3/4/4, composed via API) | Match the literature values | Compile ✓ (12 seconds) |

## Independent Python cross-check ()

`verify_small.py` exhaustively enumerates every vertex-coloring × edge-coloring combination for the same graphs to compute χ''; it shares no code with the Lean definitions.

| Graph | Python χ'' | Lean result | Δ (computed) | χ'' ≤ Δ+2 |
|---|---|---|---|---|
| K₃ | 3 | 3 (E1+E2) | 2 | Holds |
| Star K_{1,3} | 4 | 4 (E3+E4) | 3 | Holds |
| K_{2,2} | 4 | 4 (E5+E6) | 2 | Holds (equality) |

Log: `verify-small.log` (“all passed,” exit code 0, runtime 0.02 seconds).

## Issues found

- **Heartbeat is budgeted per declaration:** combining two or more `decide`s in one proof command exceeds 200,000 heartbeats (the single upper-bound check for K_{2,2} already uses about 65,000 combinations). Resolution: the task statement and `instruction.md` explicitly say to put each `by decide` in a separate theorem. The three-checkpoint proof forms follow this rule and passed in the grading chain.
- **Misaligned parameters in dot notation:** `hk.mono X` expands with `G`, the graph parameter of `TotalColorable.mono`, explicit before the proof arguments, causing an application-type mismatch. Resolution: call it with named arguments `(h := hk) (hkl := ...)`, and show this in the `instruction.md` example.
- **`Nat.find` cannot be evaluated by the kernel:** χ'' cannot be proved by applying `decide` directly to a checkpoint statement. This is an intentional definition-layer choice (deviation 4; see concept-ledger); proofs use only `TotalColorable` decisions plus API lemmas.
- **Axiom cleanliness of kernel `decide`:** measured E9–E12; the four helper theorems have only propext / Classical.choice / Quot.sound in `#print axioms`, confirming kernel evaluation does not introduce axioms such as `Lean.ofReduceBool`. The partial-all grading-chain whitelist check also passed all three checkpoints.
