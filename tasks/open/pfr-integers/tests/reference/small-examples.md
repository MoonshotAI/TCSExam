# Executable small-example record — behavior checks for the pfr-integers definition layer

This record captures actual outputs from applying the Lean definitions to small integer sets that can be checked by hand (pointwise and set addition, doubling, and the point set and covering for a convex body inside a progression).
- Test file: `Probe.lean` (inside a copy of the reference app, run `lake build Task` followed by `lake env lean Probe.lean`; an independent CPU validation environment; toolchain leanprover/lean4:v4.33.0-rc1, mathlib pinned at 5b3f719)

## Design notes

Pointwise set addition `A + A` (mathlib's pointwise addition on `Finset`) and membership in the concrete set `prog024` use only computable operations on `Finset ℤ` / `Set ℤ` and already-proved definition-layer lemmas (`prog024_toSet` / `prog024_toFinset_eq`, which are themselves part of test point c3). Every small example is closed by kernel `decide` or a short combinatorial proof (`native_decide` is banned by the task's lexical scan and is not used). Hand-computed expected values come from the concept ledger (sections 1 and 4). E9 is a sanity check of mathlib's Freiman-homomorphism API (the four-element characterization for order 2); it is independent of the statement layer and only confirms that the API behaves as expected.

## Small-example table (measured in the sandbox)

each row gives a check, the hand-computed expected value, and the actual result.

| ID | Check | Expected by hand | Actual output |
|---|---|---|---|
| E1 | Sumset of {0,2,4} | Exactly {0,2,4,6,8} | `decide` passed ✓ |
| E2 | `\|{0,2,4}+{0,2,4}\|` | 5 = 2·3−1 (statement of c1) | `decide` passed ✓ |
| E3 | Size of sumset for singleton {7} | 1 = 2·1−1 | `decide` passed ✓ |
| E4 | Sumset size for {0,1,3} (not an arithmetic progression) | 6 > 5 = 2·3−1 | `decide` passed ✓ (both checks) |
| E5 | Sumset size for interval {0,…,9} | 19 = 2·10−1 | `decide` passed ✓ |
| E6 | `0, 2, 4 ∈ prog024.toSet` | All three are members (rewrite using `prog024_toSet`, then `decide`) | Passed ✓ |
| E7 | `1, 3, 5 ∉ prog024.toSet` | None of the three are members | Passed ✓ |
| E8 | `{0,2,4} ⊆ {0} + prog024.toFinset` | One translate covers the set (rewrite using `prog024_toFinset_eq`, then `decide`) | Passed ✓ |
| E9 | Doubling map is an order-2 Freiman homomorphism from [-2,2] to [-4,4] | Four-element characterization `isAddFreimanHom_two` + omega | Passed ✓ |
| E10 | The 2n−1 bound is attained on {0,1} | 3 = 3 | `decide` passed ✓ |
| E11 | Exactly one translate is needed for the covering | `\|{0}\| = 1` and `{0}+P = {0,2,4}` | Passed ✓ |

## Run record


## Issues found

- **Pointwise addition requires `open scoped Pointwise`**: mathlib's `Finset` pointwise-addition instance is in the Pointwise scope, so the first compilation could not resolve `HAdd (Finset ℤ) (Finset ℤ)`. The scope was opened in the fixed layer after imports; the task statement and scoring variants share that fixed layer.
- **Kernel `decide` works for `Finset` operations over ℤ**. The task-writing warning about “ℚ does not reduce” does not apply here; all numerical assertions use `Finset` over ℕ/ℤ.
- **`prog024.dim` is not used for instance resolution**: `OfNat` and rewriting on `Fin prog024.dim` get stuck because the definition does not delta-reduce. The definition layer uses `prog024_toSet_fin1` (`rfl`) to bridge the semantics to `Fin 1`; all concrete proofs are carried out over `Fin 1`.
