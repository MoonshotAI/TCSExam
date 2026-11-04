# Executable small-example record — numerical checks of the log-rank-conjecture definitions and special cases

This note presents exact Python calculations (rank via Gaussian elimination over fractions, no third-party dependencies) of three special-case claims and the numerical behavior implied by the statement shapes.
- Script: `tests/reference/small_examples.py` (run locally with python3; output is reproduced below; this independently checks the Lean proofs in `solution-checkpoints.lean`)

## Design notes

- Ranks are computed by exact Gaussian elimination over `Fraction`, avoiding floating-point error; matrices are constructed directly from the 0/1 communication-matrix definitions.
- There is a classical exact result for D on these small examples (both EQ_n and IP_n have value n+1, achieved by bit-by-bit protocols; the rank lower bound `log₂ rank` together with single-point rectangle counting gives the matching lower bound). The script checks only the **upper bounds** asserted by this task's test points (protocol depth), matching the shape of the Lean proofs.
- Two degenerate instances illustrate the statement shape (why `2 ≤ rank` is needed and why the exponent is `1 + log₂ rank`); both are numerical checks only.

## Run output

each row gives a check, its expected value, and the actual output.

| ID | Check | Expected | Actual output |
|---|---|---|---|
| S1 | Rank of EQ_n communication matrix (identity matrix), n = 1..4 | 2^n | 2, 4, 8, 16 ✓ |
| S2 | Rank of IP_n (inner product mod 2) communication matrix, n = 1..3 | 2^n − 1 | 1, 3, 7 ✓ |
| S3 | Test point (a): EQ on Fin 4, rank = 4 and 3 ≤ (log₂ 4)² | rank 4; 3 ≤ 4 | rank = 4, 3 ≤ 4.0000 ✓ |
| S4 | Test point (b): 4×4 matrix for ip2, rank = 3 and 3 ≤ (log₂ 3)³ | rank 3; 3 ≤ 27/8·… | rank = 3, 3 ≤ 3.9816 ✓ |
| S5 | Degenerate case for test point (c): u∧v (both u and v nonconstant), rank = 1, log₂ rank = 0, D = 2 | Pure power `0^c ≥ 2` cannot hold | rank = 1, `2 ≤ 0^c` is always false ✓ (shows why the `2 ≤ rank` assumption is needed) |
| S6 | EQ_1 (equality on one bit): rank = 2, D = 2 | Pure power `(log₂ 2)^c = 1 < 2` always fails; `(1+log₂ 2)^c = 2^c ≥ 2` holds for c ≥ 1 | Both confirmed ✓ (shows why the expression `1 + log₂ rank` is needed) |

## Comparison with Lean

- Lean proofs for S3/S4/S5 are included and compiled (`tests/reference/solution-checkpoints.lean`; all three test points proved; scoring run gave reward = 1.0): S3 uses `Matrix.rank_one` (identity matrix rank = 4) + a 3-bit protocol; S4 uses `Matrix.rank_eq_finrank_span_cols` + linear independence of three columns + a 3-bit protocol; S5 proves existence of a 2-bit protocol (`D ≤ 2`). The rank = 1 side of S5 is confirmed only by this script, not proved in Lean, and is not a test point.
- The general formulas in S1/S2 (rank 2^n for EQ_n and 2^n−1 for IP_n) are standard literature results. This task has a test point only at n = 2 (Fin 4 / two-bit strings); the general formulas are not proved in Lean and are not test points.

## Notes

- The first row of the 0/1 matrix for IP_n (x = all zeros) is all zeros, so the rank is 2^n − 1, **not** 2^n. The ±1 (Hadamard) version is full rank. The task uses the 0/1 version in S2.
- The inequality in the ip2 test point uses c = 3: `(log₂ 3)³ ≈ 3.98 ≥ 3`; for c = 2, `(log₂ 3)² ≈ 2.51 < 3`, which is insufficient. This is why test point (b) uses exponent 3.
