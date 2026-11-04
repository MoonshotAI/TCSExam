# Executable small examples — lean-qma-qcma-oracle

This document records Executable checks of the statement predicates on small examples (the second of three fidelity checks); `small_examples.py` in the same directory reimplements the definition-layer objects with NumPy.

## Small-example checklist

each row gives a check and the part of the statement it validates.

| ID | Check | Statement component |
|---|---|---|
| E1 | Three hand-computed values of γ_y(S) (n=2, S=[00,01]: γ=2, 0, ℓ) | `gamma` (eq. 28) |
| E2 | `sfVal` (n=1, S=U={0}) = 1/2 | `sfVal`/`forrelMat` |
| E3 | `sfVal` for an empty oracle = 0 | Fourth part of c1 |
| E4 | `sfVal` ∈ [0,1] on 200 random pairs (f,g) | Third part of c1 |
| E5 | Rayleigh identity ‖Π_U H Π_S ψ‖² = ⟨ψ, M ψ⟩ agrees with the maximum eigenvalue | First and second parts of c1 |
| E6 | Sum of `uWeight` over all U = 1 (including the exclusion rule for y=0) | Packaged Definition 7.2 |
| E7 | Good-list predicate: positive example passes, duplicate point fails | Two clauses of `IsGoodList` |
| E8 | A 4-equation nontrivial instance is rejected | `EvenMultiplicity` |
| E9 | Minimum eigenvalues of PSD bounds M−A and B−M are ≥ 0 (small good-list example) | First and second parts of c6 |
| E10 | Rayleigh quotient of B ≤ (1+κ)/2 + κ‖Δ‖/ℓ (300 random vectors × two choices of Δ) | Third part of c6 |
| E11 | The `|S⟩` Rayleigh quotient of A equals the explicit value in eq. (43) and is ≥ (44c) | Fourth part of c6 |
| E12 | Scan the Taylor inequality `1/2+κx/2−κ²x²/4 ≤ 1−e^{−κx}/2 ≤ 1/2+κx/2` | Core inequality in the c6 proof |
| E13 | Asymptotic comparison for c8 (base-2 logarithm): first crossing at n=59280 for a=1 and n=113200 for a=2 | Final numerical step of the c8 proof |
| E14 | Window `t1 ≤ 0.57`, `t2 ≥ 0.59` (`κ=1/10`, `ρ ≤ 0.005`, `ℓ ≥ 500`) | c7 instantiated window |
| E15 | Mixed-argument constant: `(1/3)/2` gives `1/(36t²)` by Cauchy–Schwarz | Constant in c3 |

## Actual errors found by the small examples during development

1. **Incorrect transcription of `inclProb` (serious)**: the draft used `(1−e^{−κγ})/2`; the correct form is `1−e^{−κγ}/2` (eq. (36) and §1.4). At γ=0, E9 exposed the error because the minimum eigenvalue of M−A was −1/2; this error also made the Taylor lower bound miss by 1/2 at γ=0. E9 passed after the correction, which was incorporated into the final version and regression-checked.
2. **Exponent placement in Theorem 9.1**: `pdftotext` did not reveal which terms in eq. (54) were squared. Inspection of the page image confirmed that the second and third terms are squared as a whole, consistent with the restatement in eq. (227). E13 checks the asymptotic comparison using the corrected form.
3. **Misreading `(vt)` in E13**: the initial small example read `(vt)` as v·T (where T = vt is the total number of queries), but it denotes T itself. Also, the initial scan stopped at 3·10⁴ even though the crossing for a=1 is at 5.9·10⁴. The check passed after both corrections.

## Run record

- 2026-08-15, `venv` created with uv, NumPy 2.5.2: `EXAMPLES ALL: ok` (15/15).
