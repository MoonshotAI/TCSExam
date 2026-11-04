# Executable Small Examples — Behavioral Checks for the `ProximityGaps` Definition Layer

Hand-checkable examples exercise Lean definitions and record the output of each run; they serve as unit tests for the definition layer.

- Test file: development version `Task/Examples.lean` (E1–E8 all passed with toolchain leanprover/lean4:v4.33.0-rc1 and mathlib pinned at 5b3f719). Run command: `lake env lean Task/Examples.lean`; no output means all checks passed.

## Design: what can and cannot be executed

- `relDist` and `curveEval` are **computable** definitions (they use only `Finset.univ/filter/card` and finite sums over `Fin`), so `native_decide` runs them directly over ZMod 5 (E1–E4).
- `relDistProd` / `CurveDecodable` / `MCA` / `IsSubspaceDesign` use submodule membership decisions or classical constructions and are not executable by definition; proof-based small examples check their predicate behavior (E5–E8).
- `PruningGuarantee` and `ListSizeBound` are packaged assumptions (forms of assumptions in external theorems); their validity is supported by the component reconciliation table (deviation 6 in concept-ledger), so no small examples are provided.

## Part 1: Executable checks (`native_decide`, over ZMod 5)

Each row states what was checked, its hand-computed expected value, and the `native_decide` result.

| ID | Check | Expected | Result |
|---|---|---|---|
| E1 | Relative Hamming distance between two words over `Fin 4` that differ in 2 positions | `2/4` | Pass ✓ |
| E2 | Distance between identical words | `0` | Pass ✓ |
| E3 | A degree-1 curve at `α = 0` returns the constant-term word (`curveEval ![u₀,u₁] 0 = u₀`) | `![1,2]` | Pass ✓ |
| E4 | A line at `α = 2` has coordinate values `u₀ + 2·u₁` (`(1,0) + 2·(1,1) = (3,2)` over ZMod 5) | `![3,2]` | Pass ✓ |

## Part 2: Proof-based examples (using shipped definitions)

| ID | Check | Expected | Proof |
|---|---|---|---|
| E5 | `relDistProd` is 0 when `L ≡ ⊤` (every coordinate belongs) | `0` | `simp [relDistProd]` ✓ (ZMod 5, n = 3) |
| E6 | `CurveDecodable` holds trivially at `b = −1` (for any code, use the zero curve) | Holds | `le_trans (by norm_num) (Nat.cast_nonneg _)` ✓ |
| E7 | `MCA` holds vacuously at `err = 1` (the premise probability is at most 1) | Holds | cardinality ≤ domain size + `div_le_one` + `linarith` ✓ |
| E8 | `IsSubspaceDesign` holds when `τ ≡ 1` (fix subspace dimension ≤ original dimension, average ≤ dim A) | Holds | `Submodule.finrank_mono` + monotonicity of sums + `div_le_div_of_nonneg_right` ✓ (n > 0) |

## Issues found

- **An untyped lambda made typeclass search stall:** In the initial statement, a predicate such as `Finset.univ.filter fun α => relDist (curveEval u α) ...` left the type of `α` ambiguous, and synthesis for `curveEval`'s `[Module F V]` instance stalled (`Module ?m V`). All such lambdas now specify `fun α : F =>` explicitly (synchronized across all three shipped tiers). This first surfaced while writing E1–E4, after which the statement layer was fixed consistently.
- **The `Field` instance for `ZMod 5` is not automatic:** `Fact (Nat.Prime 5)` is needed. After the test file registered the `⟨by decide⟩` instance at the top, E1–E5 passed (same trap as in the bciks20 small examples).
- **Names of division-order lemmas changed:** `div_le_div_iff` / `div_le_div_right` / `div_lt_div_right` no longer exist in current mathlib. The small examples and `mca_mono` use `div_le_div_of_nonneg_left` / `div_le_div_of_nonneg_right` / `div_lt_div_iff_of_pos_right` instead; all signatures were checked.
- **The submodule finrank of ⊓ must be written under ↥:** `Module.finrank F (A ⊓ coordKer i)` elaborates ⊓ at the `Type` level and fails to find `Min (Type _)`; shipped statements consistently use `Module.finrank F ↥(A ⊓ coordKer i)`, synchronized with E8.
- **`open ... in` must precede the docstring:** If the docstring comes first, this toolchain's parser rejects the file (`unexpected token 'open'; expected 'lemma'`). All shipped files now place `open Classical in` before the docstring; only `ListDecodable`, `ListSizeBound`, and `relDistProd` need Classical.
