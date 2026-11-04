# Executable small examples: lean-negations-small-depth (second track of SOP step 6)

This record checks the behavior of the test-point statements on small examples; output from `small_examples.py`.

Script: `small_examples.py` (pure Python; run directly with `python3`). Illustrative output:

```
1. coeff formula on K2: P_G = x_{1,0}x_{2,0} + x_{1,0}x_{2,1} + x_{1,1}x_{2,0}; OK
2. supp(P_G) == fG^{-1}(1) on K2: OK
3. P_G == Q2 - 2*Q1 + Q0 on K2: OK
4. l=1 corruption: max legal rectangle mass = 2/3 < 2^-1/2 = 0.7071: OK
5. balanced partition of [n] exists for n in {2} and all n >= 4, fails for n in {0,1,3}: OK
6. edgeless graph: P_G = sum_a m_a = prod_i (x_{i,0}+x_{i,1}), all coeffs 1: OK
ALL SMALL EXAMPLES: ok
```

Item-by-item mapping:

1. **First part of c1 (coefficient formula)**: for n=2 on the single-edge graph K₂, enumerate all 4 assignments and check `(graphPoly G).coeff (expVec a) = (e(G[supp a]) − 1)²`: the coefficient is 1 for supp = ∅, {0}, or {1}, and 0 for supp = {0,1} (whose induced edge count is exactly 1).
2. **Second part of c1 (support characterization)**: on the same graph, check pointwise in both directions that `expVec a ∈ supp(P_G) ⟺ fG a = true`.
3. **Algebraic core of c2**: check pointwise on K₂ that `P_G = Q₂ − 2Q₁ + Q₀`, where `Qₚ = Σ_a (Σ_{uv} a_u a_v)^p · m_a`.
4. **Bound in c5**: for ℓ=1, enumerate all legal 1-rectangles (`|L ∩ R| ≠ 1`); the maximum mass is exactly 2/3, below `2^{−1/2} ≈ 0.707`. Also verify that for ℓ=0 the mass is 1, so c5 must require `1 ≤ ℓ`.
5. **Origin of the c3/c4 assumptions**: enumerate whether a balanced partition (both sides satisfy `n ≤ 3|·|` and `3|·| < 2n`) exists for n = 0..8. None exists for n ∈ {0, 1, 3}; one exists for n = 2 and for all n ≥ 4. The `4 ≤ n` assumption in c3/c4 conservatively covers all degenerate cases (when n=1 or 3 there is no balanced partition, so the literal claim that “a balanced pair decomposition exists” is false—see item 2 of the step 6.5 self-check).
6. **The `(e+1)²` form in c2**: on an edgeless graph, `P_G = Σ_a m_a = ∏ᵢ (x_{i,0}+x_{i,1})` (all coefficients are 1). In this case `35·(e+1)²·n = 35n` still bounds the formula size `4n+1`, confirming that the `(e(G)+1)²` form covers the `e = 0` case.
