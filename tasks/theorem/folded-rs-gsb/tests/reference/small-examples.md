# Executable small-example record — behavior checks for the FoldedRSGSB definition layer

This record captures actual outputs from running the definition layer on examples small enough to calculate by hand; a record of each run, serving as unit tests for the definitions.
- Test file: `small_examples.py` (E1–E9 all passed with Python 3.10; run with `python3 small_examples.py`, which prints `ALL PASS`)

## Why use a parallel Python implementation

- There is no Lean toolchain on the local machine (the task-authoring rules reserve compilation for the platform), so no Lean-side small examples were written or run. Every row below uses a Python implementation parallel to the shipped definitions: polynomials over ZMod 5 are represented by coefficient tuples; `affDim` is implemented by Gaussian elimination on the span of all pairwise differences; `foldedWronskian` composes `f_v(γ^u·X)`. Each construction corresponds directly to the Lean definition.
- Coverage includes numerical behavior of definition-layer predicates (E1–E4), parameter calculations for the main theorem assembly (E5–E6), counterexamples/vacuous-truth checks for two repaired assumptions (E7–E8), and a small example of a flat partition (E9).

## Results

each row gives the check, the value expected by hand from the definition, and the program's output. The generator of ZMod 5 is γ = 2 (2¹=2, 2²=4, 2³=3, 2⁴=1).

| ID | Check | Expected | Actual output |
|---|---|---|---|
| E1 | `foldEval`: f = 1+2X, a = 1, s = 3, block = (f(1), f(2), f(4)) | (3, 0, 4) | (3, 0, 4) ✓ |
| E2a | Positive `foldedWronskian` case: det W(1, X) = 1·2X − X·1 = X | Nonzero polynomial X | X ✓ |
| E2b | Negative case: det W(X, 2X) = 4X² − 4X² | Zero polynomial | 0 ✓ |
| E3a | `affDim`: {0, 1, X} is affinely independent, dimension = 3−1 | 2 | 2 ✓ |
| E3b | `affDim`: {0, 1, 2} (three constants), degenerate case, dimension = 1 | 1 | 1 ✓ |
| E4a | `loss`: {0,1,X} has no loss | 0 | 0 ✓ |
| E4b | `loss`: for {0,1,2}, loss = 3−1−1 | 1 | 1 ✓ |
| E4c | `wt`: total weight of [{0,1,X}, {0,1,2}] = 2+2 | 4 | 4 ✓ |
| E5 | c8 parameter check: R = 1/4, ε = 1/8, L = 6 > (1−R−ε)/ε = 5, threshold for s is 65; take s = 66 | ρ = 267/427 > 5/8 = 1−R−ε | 267/427 > 5/8 ✓ (strict); the intermediate closed form `L/(L+1)(1−R−(εL−(1−R−ε))/L)` is exactly 5/8 ✓ |
| E6 | c7 weight check: for n=12, k=6, s=3, L=2, `n(1−ρ) = n/(L+1) + Lk/((L+1)(s−L+1))` | Both sides equal | 6 = 6 ✓ |
| E7 | Counterexample check for the repaired c5 assumption (s=1, L=2, k=5, V={0,1,2}, e₁=V): weight condition holds for every proper subset (1 < 5), total loss is 1, right side `(L−ℓ)k/(s−L+1) = 5/0` (Lean's division-by-zero convention gives 0) | Assumptions true ∧ conclusion false (without the assumption, the claim is false) | Assumptions true; loss 1 > 0 ✓ |
| E8 | Vacuous-case check for the repaired c6 assumption (m=3, s=1): denominator s−m+2 = 0, so the weight assumptions are automatically satisfiable, while f = (0,1,X) has pairwise distinct entries | Denominator is 0 (assumptions vacuous, conclusion may fail) | Denominator = 0 ✓ |
| E9 | c4 small example: for V = {0,1,X} (ℓ=2), the one-block partition `{{0},{1},{X}}` has transversal (= V itself) with affine dimension 2 = ℓ | 2 | 2 ✓ |

## Issues found

- **Bug in the Python parallel implementation itself**: the first version of `rank` used `zip` on coefficient vectors of different lengths and truncated them positionwise, incorrectly computing the rank of the difference set for {0,1,X} as 1 (E3a failed). Padding vectors to equal length fixed the issue. The bug was in the parallel implementation; the shipped Lean definition was unaffected. This is recorded to help reviewers check that the small-example code matches the definitions.
- **Numerical intuition for E5**: the difference between ρ and 1−R−ε (`267/427 − 5/8 = 1/3416`) is small. The strict inequality in c8 relies on the strictness of the lower bound on s; the Lean proof must preserve strictness through the `lt_of_...` chain. This is recorded for the platform verification run.
- **Not covered**: the linearity-field proofs (`map_add'` / `map_smul'`) for `frsEncodeLM` are checked at compile time and cannot be verified locally; they remain in `PROVENANCE.md`. `ListDecodable`, `Appropriate`, and `IsGenerator` are direct quantified statements with no numerical content, so no small examples were defined for them.
