# Executable small examples — lean-posbody-chasing

This record presents executable small-example checks for the lean-posbody-chasing definition layer and test-point statements (actual script output).
- Script: `small_examples.py` (pure Python, no third-party dependencies).; output `ALL SMALL EXAMPLES PASS` (60 random instances, 222 failed assertions before fixing two bisection-direction bugs in the script; both bugs concerned its root-finding direction and were unrelated to the statement layer)

## Small-example checklist

E1–E3 check basic inequalities and the chain of constants; E4 checks closed-form values on a hand-computed instance; E5 numerically simulates the actual KL projection algorithm (a nonempty witness for the instantiated response bundle + Lemma 3.3/3.4 inequalities); E6 simulates Algorithm 1 (both conclusions of Lemma 3.7, dual feasibility in Lemma 3.8, and the main inequality).

- **E1 (poor man's Pinsker)**: check `a−b ≤ a·log(a/b)` on 5 pairs (a,b), including b close to 0 and the boundary a = b. Passed.
- **E2 (ratio lemma)**: check `(u+B)/(v+B) ≤ (u+A)/(v+A)` for v ≤ u, 0 < A ≤ B, and `u/v ≤ (u+A)/(v+A)` for u ≤ v, A > 0; 3 cases each, including v = 0, u = 0, and u = v boundaries. Passed.
- **E3 (constant chain in c4)**: for ε ∈ {0.01, 0.1, 0.5, 1}, check all three: `1/(1−ε/10) ≤ 1+ε/5`; `(1+ε/4)(1+ε/5) ≤ 1+ε/2`; and `(1+ε/2)(1+(2+ε)/ε) = (2+ε)(1+ε)/ε`. Passed.
- **E4 (hand-computed instance)**: n = 2, w = (1,1), ε = 1/4. For t = 1, cover c = (1,1) (`x¹ = (1/2, 1/2)`, closed form `y¹ = log 17`); for t = 2, package p = (4,0) (`x² = (5/16, 1/2)`, `z² = −log(5/8)/4`). Check bundle tightness (3.1)/(3.3), Lemma 3.3 bound, Lemma 3.4 inequality, and the S = ∅ degenerate case of Lemma 3.9 (left side = −4z² ≤ 0 = log 1). Passed.
- **E5 (algorithm simulation, 60 instances)**: n ∈ [2,4], T ∈ [2,6], ε ∈ {0.1, 0.3, 0.5, 1}, with random weights and sparse sequences of constraints (add only violated constraints). Numerically solve the two KL projections by bisection over the multipliers (the covering projection includes the offset ε/(4d^t c^t_i)). Check that the cover increases and the package decreases monotonically, coordinates outside the support remain fixed, tightness (3.1)/(3.3) within error < 10⁻⁶, the Lemma 3.3 bound at every covering step, and the full Lemma 3.4 inequality. **The response bundle is instantiated by the actual algorithm and is nonempty and true**. Degenerate coordinates (`x^{t−1}_i = 0`) remain 0 under the package projection, consistent with deviation 3. Passed.
- **E6 (Algorithm 1 simulation, same 60 instances)**: follow Algorithm 1 from the paper, constructing ỹ inductively at each time (decrease each coordinate's remaining budget independently, then take the maximum coordinate decrease at that time). Check (3.12) (`Σ_C ỹ ≥ (1−ε/10)Σ_C y`, error 10⁻⁶); (3.11) for all prefixes (i,s,t), with segment sum ≤ `w_i·log(1+40d²/ε²)`; the scaled dual solution in Lemma 3.8 (box bounds `0 ≤ r̄ ≤ w`, both dual constraints, with r̄ computed directly from the max-prefix definition); and the main inequality (algorithm's regret ≤ K times the baseline regret, where the baseline is a one-step jump to an all-time feasible point found by random search). Passed.

## Feedback on statement design

- The two first-round failures in the script (E5-tight = 0) came from incorrect root-finding directions in the script itself (the binary-search endpoints for the cover update were reversed, and the package inequality direction was reversed); they were not statement-layer issues. All checks passed after correction.
- No statement changes were needed. The constants 40d²/ε², ε/10, 1+ε/4, 1+ε, and (2+ε)(1+ε)/ε hold on all random instances with margin ≥ 10⁻⁶.
