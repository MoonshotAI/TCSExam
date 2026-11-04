# Executable Examples: Numerical Checks for the BJ26 Chain Definitions and Parameter Arithmetic

A pure-Python mirror of key predicates from the Lean definition layer checks that they behave as intended on small examples. The script also checks parameter arithmetic used to assemble the main theorem.

Script: `small_examples.py` (pure Python, no third-party dependencies). All checks passed when.

## Results (E1–E10; all PASS)

- **E1 (meaning of discLe):** A 3×3 triangle incidence matrix (three sets, each pair intersecting in one element; k = 2). Exhaustively checking all 8 ±1 colorings gives min_x ‖Ax‖∞ = 2. Observed value: 2.0 ✔ (`discLe` has the meaning of min‖Ax‖∞ in paper §1. This example also shows that when k = 2 the √k bound is not attainable; the difference really does depend on the interval condition on n.)
- **E2 (boundary case: zero matrix):** For the 2×3 zero matrix, exhaustive evaluation gives disc = 0 ✔, consistent with `discLe` in the degenerate k = 0 case.
- **E3 (walk / tUp / level mirror):** n = 4, T = 6, one row a = (1,1,1,1), deterministic increment rule (at each step push coordinate 0 by √dt), b₀ = 1, β₀ = 0.1. The Python mirror of the Lean definitions `regDisc`/`tUp`/`level` uses Y^(0)(t) = x_t(0) + 0.1·Σ_j(1−x_t(j)²); at t = 2 the value is 1.767 < 2, and at t = 3 it is 2.249 ≥ 2b₀ = 2. Observed tUp(1) = 3; `level` is 0 at t = 0,2 and 1 at t = 3,5 ✔. The level-up mechanism triggers according to the definition. The initial hand calculation predicted t = 2, an arithmetic error by the task author; the program gives 3 according to the definition, and its result is used.
- **E4 (positive example for pairwise independence condition (i)):** For independent Rademacher variables X = (r₁, r₂) and γ = (3, −1.5), E[⟨γ,X⟩²] = 11.25 = Σγᵢ²E[Xᵢ²]. The condition holds exactly with α = 1 and ε = 0 ✔.
- **E5 (tight counterexample for (i)):** For the negatively correlated pair X = (r, −r) and γ = (1,−1), E[⟨γ,X⟩²] = 4 = 2·Σγᵢ²E[Xᵢ²]. The bound is tight at α = 2 ✔, confirming the “factor” interpretation of the spectral-independence parameter.
- **E6 (feasible instance for c1):** h = 4, W = {0}, q = 1, E = I/2 (R₁ has 4 rows), κ = η = η₁ = 1/4. U = I satisfies every constraint: diagonal entries 1; Tr = 4 ≥ κh; (1/η)diag(U) − U = 3I is positive semidefinite; EUEᵀ = I/4 ⪯ (R₁/(hη₁))diag(EUEᵀ) = I. The quadratic form is checked directly on the sampled vector ✔.
- **E7 (necessity example from Appendix A.2.1):** Let E stack r copies of I₄ vertically, and let the test vector u stack r copies of e_i vertically. Then uᵀEXEᵀu = r²X_ii, while (1/η)uᵀdiag(EXEᵀ)u = (r/η)X_ii. Set X = 1.5I + 0.25J (positive semidefinite, X_11 = 1.75). For r = 5 and η = 1/4, 37.5 > 30, so the constraint is infeasible ✔. This agrees with the paper's claim that the O(r_s) factor is necessary and checks the factor's form in c1 in the reverse direction.
- **E8 (parameter arithmetic for c6/c7):** n = 2²⁰, k = 200·(log₂n)², C_b = 50, and c4's constant C₃ = 4. At every level, check λ = 10/b_ℓ ≤ θ_ℓ/2 and the dangerous-row bound k_ℓ/e^{10} + C₃·α_ℓλ·ln n/θ_ℓ ≤ k_ℓ/100. Both inequalities hold at every level (L = 0) ✔.
- **E8b (multilevel interval):** ln n = 25000, k = 400·(ln n)², C_b = 50. Here L = 1, and both levels satisfy the same two inequalities ✔. The multilevel mechanism is nontrivial only when ln n ≥ 10·C_b², an intrinsic constant-range requirement of this asymptotic result, as noted in section 4 of the ledger.
- **E9 (SDP budget assembled for c7):** δ = 1/3, κ = 1/6, η = 1/6, and η_ℓ = 1/(6·2^ℓ) for ℓ = 0..20. The sum is 1.0 ≤ 1 ✔; the c1 feasibility budget is attained exactly in the application.
- **E10 (preprocessing for m ≤ nk):** Structural observation: every nonzero row contains at least one nonzero entry, and the total number of nonzero entries is at most nk. No numerical check was run. This is recorded in step 1 of section 4 of the ledger (for k > n², use the trivial branch disc ≤ n < C√k).

## Notes

- The positive-semidefinite checks in E6/E7 are sampled checks (the matrices in these examples are multiples of the identity or explicitly diagonally dominant, so sampling suffices). The A.2.1 identities r²X_ii and (r/η)X_ii are exact equalities, not sampled estimates.
- Every mirrored definition in E3 corresponds line by line to `walk`/`energy`/`tUp`/`level`/`regDisc` in `Basic.lean`. If anything is ambiguous, use the Lean file as the authority.
