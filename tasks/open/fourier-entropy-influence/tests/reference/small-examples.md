# Executable Small Examples: Numerical Checks for the FEI Definition Layer

Hand-computed Boolean functions are used to exercise the entropy and influence definitions. A standalone Python implementation recomputes the values, while positive Lean proofs check the three checkpoint slots. Actual run outputs are recorded below.

- Python material: `tests/reference/verify_small.py` (standard library only; about 2 seconds per run).
- Lean material: positive proofs of the three checkpoints, verified in the judging chain.

## Design notes

The FEI definitions are real-valued (natural logarithms and division), so they are not suitable for numerical checks via kernel `decide`. A Python script performs the numerical comparison by independently recomputing the cube points, characters, Fourier coefficients, entropy, and influence from first principles. These correspond one-to-one to the Lean definitions (the mapping is in the script's docstring). A line-by-line check of `verify_small.py` confirms that it does not reuse any Lean-side result. Hand-computed expectations come from Section 1 of `concept-ledger.md`. The Lean-side definitions are checked by proving the three checkpoint examples in the judging chain; logs are in `PROVENANCE.md`.

## Python run record

| ID | Check | Hand-computed expectation | Actual output |
|---|---|---|---|
| E1 | Dictator (n = 1..4, each coordinate) | H = 0, I = 1 (spectrum concentrated at {i}) | All [ok], 10/10 |
| E2 | Parity (n = 1..4) | H = 0, I = n (spectrum concentrated at [n]) | All [ok], 4/4 |
| E3 | `andTwo` (n = 2, checkpoint c3) | H = 2·ln 2 ≈ 1.3862943611, I = 1 (spectrum is uniform over four coefficients ±1/2) | [ok] |
| E4 | `maj3` (majority, n = 3; symmetric-function comparison) | H = 2·ln 2, I = 3/2 (spectrum: three 1/2 coefficients and one −1/2) | [ok] |
| E5 | Parseval check (each function in E1–E4) | Σ_S f̂(S)² = 1 | All = 1.000000000000 |
| E6 | Minterm family (f = 1 only at one point) | H/I approaches 4·ln 2 ≈ 2.77258872 as n grows | n=2: 1.3863; n=3: 2.0489; n=4: 2.3584; n=6: 2.5922; n=8: 2.6636; n=10: 2.6923 |
| E7 | Exhaustive enumeration at n = 3 (256 functions) | max H/I = 2.0488665300 (attained by minterm); H ≤ 3·I for every nonconstant f | [ok] |
| E8 | Exhaustive enumeration at n = 4 (65,536 functions) | max H/I = 2.3584163352 (attained by minterm); H ≤ 3·I for every nonconstant f | [ok] |

Full stdout is archived at `verify-small.log`.

## Issues found

- **The intuition that AND₂ is the worst case for H/I is wrong.** The initial script assumed AND₂ (2·ln 2) attains the worst ratio for n ≤ 4. Exhaustive enumeration showed that the minterm family is worse (2.0489 at n=3 and 2.3584 at n=4), with the ratio tending toward 4·ln 2 as n grows. The c3 wording was changed to claim only that any FEI constant must satisfy C ≥ 2·log 2 (which follows from AND₂ alone), not that this is optimal. The minterm trend is included for comparison in Section 5 of `concept-ledger.md`. This is an example where numerical verification directly corrected the task wording.
- **Constant-function boundary:** for a constant function H = I = 0, so there is no constraint on C. The exhaustive script skips ratio calculation when I = 0 (noted in the script). On the Lean side, the conjecture at I(f) = 0 reduces to H ≤ 0; Parseval plus nonnegative entropy gives H = 0 for a constant function, so this does not affect equivalence of the statement.

## Lean-side examples (positive proofs in the judging chain; see `PROVENANCE.md`)

- Checkpoints c1 (`fei_dictator`), c2 (`fei_parity`), and c3 (`fei_andTwo`) each passed isolated judging through the actual `tests/score.py` (logs `partial-*.log`), confirming that each special case is provable from the Lean definitions.
- A combined submission for all three (partial-all) scored 1.0 through the judging chain (log `partial-all.log`).
