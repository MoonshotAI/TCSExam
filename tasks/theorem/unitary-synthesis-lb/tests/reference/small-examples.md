# Executable Small Examples — Numerical Checks for the LMW24 Chain's Definition Layer and Predicates

Pure-Python mirrors of key predicates in Lean's definition layer were tested on small examples to check that their behavior matches the paper's intent, including the semantics of degenerate parameters.

- Script: `small_examples.py` (pure Python, no third-party dependencies); all checks E1–E10 passed when, including the nondegenerate versions after fixes to E5/E6/E8.

## Results (all PASS)

Each item states what was checked, the small-example input, the expected result, and the observed result.

- **E1 (semantics of the c1 identity):** N = 3, M = 5 random isometry; enumerate all 2³ = 8 phase functions and compute E_h‖(Vψ_h)_i‖² = wt_i row by row. All 5 rows agree exactly (error < 1e-9). ✔ (`psi`/`wt`/`unifExp` have the meanings of the two sides of Proposition 4.4 in the paper.)
- **E2 (scaling identity):** M = 3, N = 2 isometry with one zero row added (a degenerate row with wt = 0); enumerate all phase functions and check V·ψ_h = D_{V,h}·wtVec. Holds componentwise, including at the zero row. ✔ Both sides are 0 at the zero row—garbage value 0/0 = 0 is consistent with the true value, so c3 needs no extra premise.
- **E3 (weight sum):** M = 6, N = 4 random isometry; Σ_i wt_i = 1 holds exactly. ✔ After setting one row to zero, the sum drops below 1. ✔ This confirms that the c3 proof's “weight sum is 1” premise really requires an isometry.
- **E4 (opNorm mirror):** Random 2×2 complex matrix. Closed-form maximum eigenvalue of A†A vs. dense sampling of the unit sphere: 2.119617 vs. 2.119570 (sampling approaches the supremum from below, relative difference < 3e-5). ✔ Semantics of the variational-form supremum are correct.
- **E5 (c3 domination, exhaustive):** M = N = K = 2; choose each Pj as a non-diagonal rank-1 projection uu† (u = (1, i)/√2; a diagonal projection would make pA independent of f and degenerate the example). Enumerate all 16×16 pairs (R, R′) and 4 choices of f: max_f ‖decAdv‖ ≤ specRelax holds in every case; worst lhs − rhs = 0 (some cases attain equality). ✔
- **E6 (c2 decoupling, exhaustive):** Same setup; enumerate all R and (R, R′) pairs: E[adv] = 0.021534 ≤ 4·E max_f‖decAdv‖ = 1.523387. ✔ The direction and scale of the constant-4 inequality are correct; slack comes from spectral relaxation and taking absolute values.
- **E7 (c6 mean and width concentration):** m = 5 uniform complex weights (|a_i| = 1/√5); enumerate all 2⁵ sign vectors and compute E‖S‖² = 1 exactly (special case of Proposition 4.20). ✔ Sample 200 families with M = 16, N = 8, K = 40: maximum width 1.553, max |width − 1| = 0.553, close to 1. ✔ Qualitative check of the concentration semantics in c7; c is existential, so no numerical comparison is made.
- **E8 (main-theorem scale sanity check):** M = N = 2, non-diagonal rank-1 projection: exhaustive check at K = 2 gives E[adv] = 0.1721; sampling 400 families at K = 4 gives 0.1433. Ratio 1.20, consistent with the direction of decay by √2 ≈ 1.41. ✔ Structural check of the existential constant C; no constant comparison.
- **E9 (degenerate parameters):** At N = 1 and K = 1, adv is finite and ≤ 1. ✔ At M = 1, E[adv] = 0 exactly (pA is independent of f; calculation for the M = 1 branch of deviation 5). ✔ At M = 1 with Pj = 0, adv ≡ 0. ✔
- **E10 (1×1 case of c4 and zero-dimensional counterexample):** For 1×1 matrix a = (3+4i), vStat = 25 = |a|². ✔ Anchor for the derivation of Theorem 4.21. When d1 = d2 = 0, the tail bound is false literally (at t = 0, the left-side probability is 1 and the right-side coefficient is 0), confirming the necessity of c4's premise 1 ≤ d1+d2. ✔

## Notes

- The first versions of E5/E6/E8 used diagonal projections Pj (diag(1,0) or I); then O_f·Pj·O_f was independent of f and E[adv] ≡ 0, degenerating the example (first run of E8: FAIL). Replacing these with non-diagonal rank-1 projections made the examples nondegenerate. This itself supports the definition's semantics: with diagonal projections, the indicated sign is indeed cancelled.
- The opNorm mirror uses the closed form (largest eigenvalue of A†A) in dimensions ≤ 2; larger dimensions are used only for qualitative sampling (E7b).
- Each mirrored definition corresponds line by line to `Basic.lean`: `phase/psi/wt/oracleMat/pA/adv/decAdv/wtVec/rescale/opNorm/specRelax/width/vStat`. In case of ambiguity, follow the Lean file.
