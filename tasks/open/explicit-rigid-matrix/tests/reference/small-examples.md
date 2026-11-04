# Executable Small Examples: Numerical Checks for the Definition Layer and Special Cases

Hand-computable or exhaustively enumerable examples check the task's definition layer and the truth of three special-case statements. They serve as unit tests for the definitions.

- Script: `tests/reference/small_examples.py` (pure Python with exact rational arithmetic via `fractions`, no third-party dependencies). The script was; all output below comes from that run.
- Companion: a complete Lean proof probe for special case (b) is at `Probe-b.lean`. It compiled, and `#print axioms` listed only [propext, Classical.choice, Quot.sound]; the log is in the same directory.

## S1: The 3×3 Hilbert matrix (numerical basis for special case (b))

H₃ = [[1, 1/2, 1/3], [1/2, 1/3, 1/4], [1/3, 1/4, 1/5]], with exact arithmetic over ℚ.

- det(H₃) = 1/2160 ≠ 0.
- Its nine 2×2 cofactors are 1/12, 1/12, 1/72, 1/12, 4/45, 1/60, 1/72, 1/60, and 1/240; **all are nonzero**. This is a sufficient condition for special case (b), `IsRigidAt (hilbert 3) 1 2`, to hold: any matrix B differing from H₃ in at most one position retains a full 2×2 cofactor by choosing the pair of rows and columns that avoid the changed position. That cofactor is nonzero, so rank B ≥ 2 > 1.
- **The exact value is R_{H₃}(1) = 3.** The script enumerates supports and solves exactly using the rank-one form B = uvᵀ; it proves that two changed entries do not suffice. A diagonal witness is u = (1, 3/4, 1/2), v = (2/3, 1/2, 1/3), and B = uvᵀ. B differs from H₃ at exactly the three diagonal positions, and all nine of B's 2×2 cofactors are zero, so rank B ≤ 1. The script checks all 46 supports of size at most 2, and none is feasible.
- Conclusion: the Lean statement for special case (b), `IsRigidAt (hilbert 3) 1 2`, is true with slack 1. The exact value 3 is recorded here.

## S2: Rigidity of the identity matrix (construction side of special case (a))

R_{I_n}(r) = n − r. For the upper bound, change n − r diagonal entries to 0, reducing the rank to r. For the lower bound, rank B ≥ rank I − rank(I − B) ≥ n − (number of changed entries). The script illustrates this with (n, ε) = (8, 1/2), changing 4 diagonal entries to reduce the rank to 4, and (16, 1/4), changing 12 entries to reduce it to 4.

Special case (a) asks, for any 0 < ε < 1 and δ > 0, for an n such that `n − ⌊εn⌋ < ⌈n^{1+δ}⌉`. The left side satisfies n − ⌊εn⌋ ≤ (1−ε)n + 1 and grows linearly, while n^{1+δ} grows superlinearly. Thus the inequality holds for sufficiently large n. This is an asymptotic fact; the proof obligation is on the model side.

## S3: Sampling record for special case (c)

- Sampling method: Python `random.Random(20260904)` generates 4×4 matrices with independent uniform entries in {0,1}. The acceptance condition is that all 16 of their 3×3 cofactors (determinants computed exactly over ℚ) are nonzero.
- **The 314th sample met the condition.** The matrix is the shipped `sampleMatrix4`:
  ```
  [1, 1, 1, 0]
  [0, 0, 1, 1]
  [0, 1, 0, 1]
  [1, 0, 0, 1]
  ```
- Frequency: with seed 1, 51 of 10,000 samples had all 3×3 cofactors nonzero (0.51%). The low-frequency event is the sufficient condition that all 3×3 cofactors are nonzero, which is the property needed by this task's proof route for the special case; it is not rigidity itself. S4 illustrates the high-probability rigidity phenomenon.
- This instance satisfies a sufficient condition for special case (c), `IsRigidAt sampleMatrix4 2 2`: any B differing from M in at most one position retains a full 3×3 cofactor, so rank B ≥ 3 > 2.

## S4: Exact sampling of random-matrix rigidity over GF(2)

This illustrates the phenomenon that random matrices are highly rigid. For fixed (n, r), the script enumerates all n×n matrices over GF(2) of rank at most r (using integer bit representations and Gaussian elimination to compute rank), then exactly computes R_M(r) = min_B dist(M, B), the Hamming distance, for uniformly random M. Actual output:

| n | r | Number of matrices of rank ≤ r | Samples | Distribution of R_M(r) {value: count} |
|---|---|---|---|---|
| 4 | 1 | 226 | 300 | {0:2, 1:10, 2:45, 3:97, 4:119, 5:25, 6:2} |
| 4 | 2 | 7576 | 300 | {0:36, 1:131, 2:129, 3:4} |
| 5 | 2 | 145112 | 40 | {1:3, 2:13, 3:16, 4:7, 5:1} |

Read the distributions as moving toward (n−r)² as n grows. For 4×4 matrices of rank 1, the mode is 4, while the upper bound is (n−r)² = 9. The literature shows that for large n, random matrices are highly likely to approach full rigidity (n−r)²; see Section 2 of `concept-ledger`. For small n, the maximum rigidity itself can be below (n−r)² (the largest sampled value for 4×4 matrices with r=2 is only 3). This is a known small-size effect over finite fields. The table illustrates the phenomenon and is not used in any Lean statement.

## Design note: what appears in Lean statements and what remains numerical

- Included in Lean statements: the three special cases. Each needs only a short hand proof that a nonzero small cofactor implies a rank lower bound (or an asymptotic argument plus a construction); none depends on enumeration.
- Numerical results only: the exact value R_{H₃}(1) = 3 (the Lean statement uses only ≥ 2) and the GF(2) distribution in S4 (an illustration of the phenomenon). The model-side proof obligations are mathematical arguments, not recitations of computations.
- `native_decide` is lexically banned in the task, `Matrix.rank` is noncomputable in mathlib, and `decide` cannot handle it. Therefore, all enumeration checks stay in the author-side script and do not enter the judging chain.
