# Executable small-example record — behavior checks for the Aaronson–Ambainis definition layer

This note gives concrete values of Lean definitions on examples small enough to calculate by hand (degree / variance / influence), serving as unit tests for the definition layer.
- Test file: `tests/reference/SmallExamples.lean` (compiled with `lake env lean` inside the open-aa-v1 image; zero errors and zero warnings; log at `tests/reference/logs/small-examples.log`)

## Why all examples are proofs

`cubeAvg` / `cubeVariance` / `cubeInfluence` depend on `MvPolynomial.eval`, which mathlib marks noncomputable, so the `#eval` route is unavailable. As in the small-example record for lean-bciks20-agreement, every example is therefore a proof: the expected value is calculated by hand and Lean checks the equality. The helper lemmas (the cube-character sum is zero, expectation is linear, the dictator evaluation formula, etc.) are shared with the positive controls and included in the file.

## Examples and results

each row gives a function, its hand-computed value, and the value proved in Lean; all agree.

| ID | Function (n) | Hand calculation | Lean proof |
|---|---|---|---|
| E1 | Constant 1 (n = 2) | Var = 0 | `ex1_variance_const`: `cubeVariance` = 0 ✓ |
| E2 | X₀ (±1 dictator, n = 2) | Var = 1 | `ex2_variance_xdict` = 1 ✓ |
| E3 | X₀ (n = 2) | Inf₀ = 4 (difference is always ±2X₀ = ±2, so its square is 4), Inf₁ = 0 | `ex3_influence_xdict_self` = 4, `ex3_influence_xdict_other` = 0 ✓ |
| E4 | (1+X₀)/2 (0/1 dictator, n = 2) | Var = 1/4, Inf₀ = 1, Inf₁ = 0 | All three results in `ex4` (instances of the general dictator lemma at n = 2) ✓ |
| E5 | (1+X₀X₁)/2 (n = 2, degree 2) | Var = 1/4, Inf₀ = Inf₁ = 1 | All three results in `ex5` ✓ |
| E6 | (1+maj₃)/2, where `maj₃ = (X₀+X₁+X₂−X₀X₁X₂)/2` (n = 3, degree 3, symmetric) | Var = 1/4, Inf₀ = 1/2 | `ex6_variance_maj3`, `ex6_influence_maj3_zero` ✓ |

Hand calculations (all coordinates are ±1; `uᵢ = pmOne(x i)`):

- E2: E[X₀] = 0, Var = E[X₀²] = 1.
- E3: `p(X) − p(X⁰) = 2X₀`, whose square is always 4; the difference in coordinate 1 is always 0.
- E4: the difference is X₀, whose square is always 1; Var = E[(X₀/2)²] = 1/4.
- E5: the difference in coordinate 0 (or 1) is X₀X₁, whose square is always 1; E[X₀X₁] = 0, so Var = E[(X₀X₁/2)²] = 1/4.
- E6: the squared difference in coordinate 0 equals `(1 − X₁X₂)/2` pointwise, with expectation `(1 − E[X₁X₂])/2 = 1/2`. Also E[maj₃] = 0 and `maj₃²` is pointwise 1, so Var = 1/4. E6 also shows that the influence (1/2) of a balanced symmetric function is lower than the dictator's influence (1), consistent with the qualitative discussion of the symmetric case in test point (b).

## Issues found

- The small examples found no defect in the definition layer. Three rounds of compile errors were all in proof drafts (mathlib lemma-name differences across versions, a timeout while elaborating the implicit argument in `⟨0, by norm_num⟩` inside a `have`, and `rw` rewriting only the first matching occurrence); none required changing the shipped definitions.
- Two deliberate choices in the definition layer (the cube uses {±1} rather than {0,1}, and a conclusion constant is absorbed) are not defects; see deviations 1 and 2 in `concept-ledger.md`.
