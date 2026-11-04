# Executable Small Examples — Checks of the `permanent-vs-determinant` Definition Layer and Witness Matrices

Pure-Python exact-integer polynomial arithmetic independently checks numerical content from three checkpoints: correctness of a small representation, the shape of the Grenet construction, and the degree of the permanent. These examples serve as unit tests for the definition layer.

- Verification script: `tests/reference/verify_small.py` (in this directory, no dependencies; run with `python3 verify_small.py`). Development copy and LU-generation script are in `pvd-open-2026-09-05` (`verify_small.py`, `lu7.py`).

## Design notes

There are only three numerical components in the grading chain: the signed 2×2 representation for checkpoint 1, the Grenet 7×7 matrix for checkpoint 3, and the fact used in the degree argument that total degree of `perm_n` is n. The script represents sparse multivariate polynomials as dictionaries (monomial tuple → integer coefficient), and expands determinants by the Leibniz definition, matching Lean's `Matrix.det`/`Matrix.permanent` definitions exactly. For large matrices (where 15! terms are infeasible), it uses random integer substitutions and fraction-free Bareiss evaluation as a cross-check.

## Small-example table (; all passed)

| ID | Check | Hand-computed / literature expectation | Actual result |
|---|---|---|---|
| V1 | det [[X00, X01], [-X10, X11]] = perm_2 | = X00·X11 + X01·X10 (flipping the sign of one off-diagonal entry suffices) | Pass ✓ |
| V2 | det M = perm_n for Grenet's subset-lattice matrix | n=2 (3×3) and n=3 (7×7): symbolically identical; n=3 and n=4 (15×15): agrees on three random integer substitutions each | Pass ✓ (2 symbolic cases + 6 numeric cases) |
| V3 | Total degree of perm_n is n | For n=2,3,4: sum of exactly n! monomials of degree n, each with coefficient +1 | Pass ✓ |

## Derivation and independent check of the Grenet construction

The task brief gave the shape “Grenet's 2^n − 1 upper-bound construction.” On the authoring side, the subset-lattice matrix was independently derived by counting cycle covers, rather than copied from the literature:

- Row/column indices are nonempty subsets of [n] (there are 2^n − 1).
- For S ≠ [n], put 1 on the diagonal (a self-loop). For a growth edge S → S∪{j} (j ∉ S), put −X(|S|+1, j). For a closing edge [n] → {j}, put +X(1, j).
- Every nonzero permutation term in the determinant corresponds to a principal cycle [n] → {j₁} → {j₁,j₂} → ⋯ → [n], with all remaining vertices on self-loops. The principal cycle has length n and sign (−1)^{n−1}; the product of edge weights is (−1)^{n−1}∏x_{i,jᵢ}. The signs cancel, yielding exactly one term of perm_n.

The script verifies that this construction gives perm_n symbolically for n=2,3 and under random substitutions for n=3,4 (V2). Lean's checkpoint 3 does not repeat this counting argument; instead, it equips the 7×7 matrix with an LU decomposition (M = L·U, L unit lower triangular, U upper triangular, and U's lower-right entry exactly perm_3), then evaluates the determinant using `Matrix.det_mul` and triangular determinant lemmas. The LU witness was generated and checked exactly by `lu7.py` (M = L·U holds exactly; det M = perm_3 was numerically checked).

## Correspondence with Lean

- V1 ↔ representation portion of checkpoint 1: the 2×2 matrix in the proof of `pvd_perm2_exact`, expanded determinant + `ring` (confirmed by a successful Lean run).
- V2 ↔ checkpoint 3: the Grenet 7×7 matrix in `pvd_grenet_perm3`, with its determinant computed from the LU witness (confirmed by a successful Lean run).
- V3 ↔ pinned lemma `totalDegree_permPoly` (total degree of perm_n is n). The Lean proof uses “diagonal monomial coefficient = 1” (the permutation monomials cannot cancel), consistent with the pointwise observations in V3.
