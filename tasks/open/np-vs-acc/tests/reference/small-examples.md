# Executable Small Examples: Checking the NP-vs-ACC Definition Layer

Small, hand-checkable inputs exercise the Lean definitions for circuit evaluation, depth and size, MOD₂ families, SAT families, and gate semantics. Actual output from each run is recorded below.

- Probe: about 60 lines of `example ... := by decide` assertions, run in a sandbox copy of the task app using `lake env lean Probe.lean` (a Lean validation image, pinned toolchain family v4.33.0-rc1, mathlib pinned at 5b3f719). The probe is not included in the task package, to prevent leakage; all assertions are recorded here.

## Design notes

Evaluation and depth recurse structurally over the number of gates processed (`wireValuesUpTo` / `wireDepthsUpTo`). The number of SAT variables is computed by counting (`satVarsGo`) rather than `Nat.sqrt`. **All definitions are kernel-computable**, so `decide` evaluates small instances directly (`native_decide` is lexically banned by the task and is never used; kernel `decide` introduces no extra axioms). Hand-computed values come from Section 1 of `concept-ledger.md`.

Two empirical issues were fixed and retested:

- **`Nat.sqrt` does not reduce in the kernel** (`Nat.sqrt 2 = 1` fails even under `rfl`), so the initial `satVars := Nat.sqrt (N/2)` stalled for all N ≥ 4 (for N = 2, sqrt 1 happens to evaluate). Replacing it with the counting function `satVarsGo` made all cases N = 0…18 evaluate immediately.
- Semantics of the MOD gate in `accBasis 6`: it outputs 1 iff the number of 1s is divisible by 6. The initial probe incorrectly expected three 1s to be true; the hand calculation was wrong, the definition was correct.

## Small-example results (sandbox; all passed; probe exited without errors)

| ID | Check | Hand-computed result | Actual output |
|---|---|---|---|
| E0a | `satVars 0 / 2 / 7` | 0 / 1 / 1 (largest n with 2n² ≤ N) | `decide` passed ✓ |
| E0b | `satVars 8 / 17 / 18` | 2 / 2 / 3 | `decide` passed ✓ |
| E1a | `sampleModCircuit.depth` | 2 (one internal-gate layer + output-gate layer) | `decide` passed ✓ |
| E1b | `sampleModCircuit.size` | 2 (G + M = 1 + 1) | `decide` passed ✓ |
| E1c | Truth table of `sampleModCircuit` = OR of all 4 inputs | MOD₃ is NOR, so its negation is OR | `decide` passed ✓ |
| E2a | `mod2Family 3` on (1,1,0) | True (two 1s, even) | `decide` passed ✓ |
| E2b | `mod2Family 3` on (1,0,0) | False (one 1, odd) | `decide` passed ✓ |
| E3a | `satFamily 2` on (1,0) (n=1: clause = {x₀}) | True (σ = 1 satisfies it) | `decide` passed ✓ |
| E3b | `satFamily 2` on (0,0) (empty clause) | False (empty clause is unsatisfiable) | `decide` passed ✓ |
| E3c | `satFamily 2` on (1,1) (clause = x₀ ∨ ¬x₀) | True | `decide` passed ✓ |
| E4a | `satFamily 4` on (1,0,1,1) (n=1; last 2 bits are padding) | True (padding bits are ignored) | `decide` passed ✓ |
| E4b | `satFamily 4` on (0,0,1,1) | False | `decide` passed ✓ |
| E5a | `satFamily 8` with bit 0 = 1, bit 5 = 1 and all others 0 (n=2: clause 0 = {x₀}, clause 1 = {¬x₀}) | False (contradictory clauses) | `decide` passed ✓ |
| E5b | `satFamily 8` with bit 0 = 1, bit 6 = 1 and all others 0 (clause 0 = {x₀}, clause 1 = {x₁}) | True (σ = (1,1)) | `decide` passed ✓ |
| E6a | `aonBasis` AND on (1,0) | False | `decide` passed ✓ |
| E6b | `aonBasis` OR on (1,0) | True | `decide` passed ✓ |
| E6c | `accBasis 6` MOD on six 1s | True (6 ≡ 0 mod 6) | `decide` passed ✓ |
| E6d | `accBasis 6` MOD on five 1s | False | `decide` passed ✓ |
| E7 | `finProdFinEquiv ((1,2) : Fin 2 × Fin 4)` | ⟨6⟩ (row-major: 2 + 4·1) | `decide` passed ✓ (encoding agrees with the documented bit layout). |

## Run record

- First round: E3 (N=2) passed; E4/E5 (N=4/8) reported `did not reduce to isTrue or isFalse`. The cause was non-reduction of `Nat.sqrt`. The initial expected value for E5 was also wrong (three 1s in MOD₆ output 0; the definition was correct).
- Second round: after replacing it with `satVarsGo`, all 19 assertions in E0–E7 passed (probe output contained only PROBE_DONE and no errors); `lake build Task` for the shipped version also passed.

## Issues found

- **`Nat.sqrt` does not reduce in the kernel:** see above. Resolution: define `satVarsGo` in the definition layer with explicit fuel (structural recursion, kernel-computable) and prove `satVarsGo_le` (every reachable value still satisfies 2n² ≤ N). The asymptotic maximality claim (fuel = N reaches ⌊√(N/2)⌋) is a metatheoretic argument recorded in `concept-ledger.md`.
- **Axiom cleanliness of kernel `decide`:** E1c, the same computation as c3, was checked against the judging-chain `#print axioms` whitelist (positive gate c3 passed), confirming that kernel evaluation introduces no extra axioms such as `Lean.ofReduceBool`.
