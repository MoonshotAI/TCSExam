# Executable Examples: Checking the LCCExpLB Definitions

These small, hand-checkable examples exercise the Lean definitions and record their actual outputs, providing unit-test-style checks for the definition layer.

The development-time test file was in the guided tier at `environment/app/Task/Examples.lean`. All checks passed with `lake env lean Task/Examples.lean` using toolchain leanprover/lean4:v4.33.0-rc1. An archived copy is at `LccExamples.lean`.

## What can be evaluated

- `chainSet`/`chainSetHead`/`chainSetContains`/`qsize`/`contiguous`/`chainContains`/`lastPivot`/`kikuchiN`/`kikuchiD` are computable definitions with explicit `Decidable` instances, and can be evaluated directly with `native_decide`/`#eval`.
- `phi`/`psiPiece`/`psiT`/`fM`/`val`/`expectB`/`expectM`/`kikuchiAij*`/`inftyToOne` take real values or use `Classical`/max' constructions, and cannot be executed. Their behavior is supported by proof-based examples (P1–P3), the component ledger, and type-checking of the statement layer.
- Toy code: the repetition code with n = 4, k = 1, d₀ = 1, mapping b ↦ (b,b,b,b). For each coordinate, the matching is the single hyperedge formed by the other three coordinates. This code satisfies every field of `NormalFormCode` (all proofs for the structure instance `toyCode` pass). It is itself an end-to-end small example, with the systematic property, 3-consistency, matching, and correction relation realized field by field.

## Part 1: Executable checks (`#eval` / `native_decide`)

| ID | Check | Expected | Actual output |
|---|---|---:|---|
| E1 | Matching size of the toy code, `(toyCode.H 0).card` | 1 | 1 ✓; reflexive inclusion `⊆` evaluates to true ✓ |
| E2 | Total number of 1-chains = n·(3d₀)¹ = 12 | 12 | 12 ✓ (`native_decide`) |
| E2 | Number of 1-chains with a fixed head = (3d₀)¹ = 3 | 3 | 3 ✓ |
| E2 | Total number of 2-chains = n·(3d₀)² = 36 | 36 | 36 ✓ |
| E2 | Total number of 0-chains = n = 4 | 4 | 4 ✓ |
| E3 | `qsize Q1` (all ★ plus tail) | 1 | 1 ✓ |
| E3 | `qsize Q2` (all non-★) | 4 | 4 ✓ |
| E3 | `contiguous Q1` and `contiguous Q2` | True | Both pass `decide` ✓ |
| E3 | `¬ contiguous Q3` (★, then non-★, then ★ again) | True | Passes `decide` ✓ |
| E4 | `kikuchiN 4 1 0 2` = C(4,2)⁴ | 1296 | 1296 ✓ |
| E4 | `kikuchiD 4 1 0 2` = 2⁴·C(2,1)⁴ | 256 | 256 ✓ |
| E4 | `kikuchiD 4 1 1 2` = 2²·C(2,1)³ | 32 | 32 ✓ |
| E5 | Number of 0-chains with the specified tail coordinate | 1 | 1 ✓ |
| E6 | The concrete 1-chain `c10` satisfies `IsChain` | True | Passes `native_decide` ✓ |
| E6 | `chainContains Qc c10` (tail and all non-★ entries match) | True | Passes ✓ |
| E6 | `¬ chainContains Qc' c10` (a non-★ entry is not in C) | True | Passes ✓ |

The E2 counts agree exactly with the chain-counting formula in Lemma 5.7: each head has (3d₀)^t chains, for a total of n·(3d₀)^t. This directly checks the counting term on the right-hand side of checkpoint c1.

## Part 2: Proof-based examples on the shipped definitions

| ID | Check | Result |
|---|---|---|
| P1 | Expand `phi toyCode 0 b x` into a sum over a single head: `signOf (b 0) * ∑ c ∈ chainSetHead toyCode (0+1) _, signOf (x w₀) * ∏ h, xS x (C_h)` (eliminating the `Fin 1` sum) | `simp only [phi, Fin.sum_univ_one]` passes ✓ |
| P2 | On a concrete sign vector, `xS x {0,1} = -1` when x 0 = 0 and x 1 = 1 | Passes ✓ |
| P3 | The suffix of a 2-chain is a 1-chain (`suffixChain` preserves `IsChain`) | Passes ✓ |

## Issues found and recorded

1. **`decide` does not work over ℝ** (the `Classical` instance gets stuck). Algebraic lemmas about `signOf` were instead proved using pointwise value lemmas (`signOf_zero`/`signOf_one` and `rfl`) plus finite case analysis (`zmod2_eq_zero_or_one`), reducing everything explicitly.
2. **Classical filters blocked evaluation.** Initially, `chainSet` and related definitions were wrapped in `by classical exact`, preventing `native_decide` from unfolding them. Explicit computable `Decidable` instances were added for `IsChain`/`chainContains`/`chainContainsSuffix`/`contiguous`. This gave the definition layer actual computability and made the second part's examples executable.
3. **The `filter_congr_decidable` rewrite approach was unreliable** because instance unification was fragile; it was replaced by the actual-instance approach in item 2.
