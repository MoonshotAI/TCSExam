# Executable small examples — kernel checks of the XOR log-rank conjecture definitions

This note records kernel-decidable numerical values for the definition layer on minimal instances, all closed by `decide` (kernel computation, without `native_decide`); one of the three fidelity checks (executable small examples).
- Probe: `tests/reference/SmallExamples.lean` (run `lake env lean` in the app environment after compiling `Task`; exit code 0 and no output; log at `logs/probe.log`)

## E1. Spectrum of `fpar2` (integer numerator layer)

`fpar2 = fun x => x 0 ^^ x 1` (XOR of two bits on `Fin 2`) has ±1 form `-χ_{0,1}`. The integer numerator of its Fourier coefficient, `fourierNum (boolSignZ fpar2) S = 2²·f̂(S)`, is:

| S | Numerator (measured by `decide`) | Coefficient (= numerator/4) |
|---|---|---|
| ∅ | 0 | 0 |
| {0} | 0 | 0 |
| {1} | 0 | 0 |
| {0,1} | −4 | −1 |

Kernel check: the cardinality of `univ.filter (fourierNum (boolSignZ fpar2) · ≠ 0)` is 1. By the bridge lemma `sparsity_eq_filter_num`, this gives `sparsity fpar2 = 1`; it has the same value as the sign proof for test point c3.

## E2. Spectrum of a constant function

For `fun (_ : Fin 2 → Bool) => true`, `fourierNum · ∅ = 4` (coefficient 1), and the number of nonzero coefficients is 1. This matches the sign proof for c1 at arbitrary n.

## E3. Parity-query truth table (`Fin 2`, S = {0,1})

Query semantics: `parityQuery S x = true` exactly when `χ_S(x) = +1` (the number of −1 coordinates is even).

| x | `parityQuery {0,1} x` (measured) | `fpar2 x` |
|---|---|---|
| ![true, true] | true | false |
| ![true, false] | false | true |
| ![false, true] | false | true |
| ![false, false] | true | false |

Thus `fpar2 x = !parityQuery {0,1} x` (the sign convention in `pmOne_xor`), and the tree for c3 is built from this relation.

## E4. Computing small trees and their depth (measured)

- `node {0,1} (leaf true) (leaf false)` computes `fpar2` (`Computes` unfolds and is closed by `decide`); depth = 1.
- `leaf true` computes the constant function (depth = 0).

## E5. Degenerate-case check (statement safety)

When `sp = 1`, `(1 + Real.logb 2 1)^c = 1`: both the constant function (depth 0) and ±χ_S (depth 1, c2) satisfy the main-slot upper-bound form. `sp = 0` is impossible (`sparsity_pos` is already proved). In mathlib, `Real.logb 2 0 = 0` (a junk value), so even if `sp = 0`, the right-hand side is 1 and the statement does not fail during evaluation.
