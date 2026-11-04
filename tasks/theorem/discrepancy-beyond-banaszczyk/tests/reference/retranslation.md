# Independent Retranslation Cross-Check — Seven Statements in the BJ26 Chain

This note re-translates seven checkpoints from the paper without consulting the shipped Lean statements, then compares each item against the shipped version. Ambiguities and identified differences are recorded below. It is the second of three fidelity records for the L2 tier.

- Source material: full text of arXiv 2508.03961v2 (`bj26.txt`).

## Method

First, the formal content of each result was independently recorded from the paper (quantifiers, premises, conclusions, and constant dependencies); then each item was compared with the shipped Lean statement. Both passes were done by the same subagent at different times: the first-pass notes, prepared while carefully reading the paper and choosing checkpoints, are the initial form of the checkpoints; the second pass (this file) starts again from the source. One genuine error in the first pass—the affine-constraint factor in c1 was missing 1/h—was caught and fixed during the component reconciliation. This second pass checks the corrected statement again.

## Item-by-item retranslation and comparison

### c1 (Theorem 2.2 / Theorem A.4)

Source (restated in Appendix A.2): “Let W ⊂ R^h be a subspace with dimension dim(W) = δh, and E_s ∈ R^{r_s h × h} for all s ∈ [q] be a set of matrices with r_s ≥ 1. Then for any 0 < κ, η, η_s < 1 such that η + κ + Σ η_s ≤ 1 − δ, there is an h × h PSD matrix U satisfying: (i) ⟨wwᵀ, U⟩ = 0 for all w ∈ W, (ii) U_ii ≤ 1 for all i, (iii) Tr(U) ≥ κh, (iv) U ⪯ (1/η)diag(U), and (v) E_s U E_sᵀ ⪯ (r_s/η_s)diag(E_s U E_sᵀ) for all s.”

Retranslation: subspace dimension = δh; each matrix has r_s·h rows (r_s ≥ 1); parameters lie strictly in (0,1); budget is η+κ+Ση_s ≤ 1−δ; conclusion has five parts; in (v), the factor r_s/η_s uses r_s = number of rows/h.

Comparison: shipped version uses R_s := number of rows as a type index and factor R_s/(h·η_s), matching the source (the first pass used R_s/η_s and omitted 1/h; this was corrected and the consistency check rerun). The dimension premise is ≤ in the shipped version (the paper has =), a weaker premise whose direction is needed by c7's application, where only an upper bound on dimension is known. The upper bounds κ,η,η_s < 1 follow from the budget and are not stated separately. The paper has r_s ≥ 1, corresponding to R_s ≥ h, but the proof of A.4 (eigenvalue truncation in Claim A.6) works for arbitrary R_s ≥ 1; the shipped version uses R_s ≥ 1. This is weaker than the printed premise and records that the conclusion holds for more matrix shapes. Part (i) is written as wᵀUw = 0: ⟨wwᵀ, U⟩_F = Σ_ij w_i w_j U_ij = wᵀUw. ✓ The ⪯ conditions in (iv)/(v) are written as quadratic-form inequalities for every test vector, the equivalent definition of the positive-semidefinite order. ✓

### c2 (Fact A.2)

Source: “Let {Z_t : t = 0, 1, ···} be a sequence of random variables with increments ∆Z_t := Z_t − Z_{t−1}, such that Z_0 is deterministic and ∆Z_t ≤ M for all t ≥ 1. If for all t ≥ 1, E_{t−1}[∆Z_t] ≤ −δ E_{t−1}[(∆Z_t)²] holds with 0 < δ < 1/M, where E_{t−1}[·] denotes E[·|Z_1, ···, Z_{t−1}]. Then for all ξ ≥ 0, P[Z_t − Z_0 > ξ] ≤ exp(−δξ).” (Footnote: the original reference has M = 1; this version follows directly by scaling.)

Retranslation: Z_0 is deterministic; increments have only an upper bound M (one-sided); conditional expectation is conditioned on the process's own history; δ < 1/M; conclusion holds for every ξ ≥ 0.

Comparison: shipped version uses the coordinate filtration (the first t layers of Rademacher slices) instead of the process filtration. For all applications in this task they agree, since each Z is a deterministic function of the increments. Direction was checked: the coordinate-filtration condition is stronger (by the tower property), so the shipped premise implies the paper's premise and gives the same conclusion without weakening it. M > 0 is implicit in the paper (δ < 1/M requires M ≠ 0; if M ≤ 0, all increments are ≤ 0 and the conclusion is trivial); shipped version states hM : 0 < M, with no change in content. ✓

### c3 (Lemma A.3)

Source: “Let y_t ∈ [−1,1]^n be a random process for t ∈ [0,T] with increment dy_t = v_t √dt, where v_t ∈ R^n is an arbitrary mean-zero random vector such that E[v_t v_tᵀ] ⪯ O(1)·diag(E[v_t v_tᵀ]). Then for any vector a ∈ R^n, with probability at least 1 − 1/poly(n), ⟨a, y_T − y_0⟩ ≤ O(‖a‖_2 log^{1/2} n).” (Footnote: the distribution of v_t may depend on all earlier v_{t'}.)

Retranslation: cube constraint; zero mean plus second-moment diagonal dominance (matrix order); arbitrary a; failure probability 1/poly(n).

Comparison: shipped version writes the matrix-order condition as a conditional-expectation quadratic-form condition (equivalent); specializes O(1) to a σ parameter (σ ≥ 1); and instantiates 1/poly(n) as failure probability n^{-(c+1)}, with a factor (c+1) in the threshold. The proof takes a union bound over T steps, and when T ≤ n^c the exponent difference is absorbed by that threshold factor, so the forms agree. The small-increment premise ∃M₀ corresponds to the natural smallness of dy = v√dt. y_0 is arbitrary, as in the paper's conclusion. ✓

### c4 (Theorem 3.7)

Source: “Suppose that (1) α ≥ 1, θ > 0, B ≥ 1, and m are all polynomially upper bounded in n, (2) dt = 1/n^c where the constant c can be chosen arbitrarily large, and (3) ‖dZ_t‖_∞ = O(√dt) for all time steps t. Then for any parameter λ > 0 satisfying λ ≤ θ/2 and λB ≤ log n, with probability at least 1 − 1/poly(n), the number of coordinates that ever become bad throughout the process is at most m/e^{λB} + O(λα log n/θ).” (Setup: Z_0(i) ≤ 0, increments satisfy the pairwise-independence condition (α,θ), and “bad” means Z_t(i) ≥ B.)

Retranslation: Z_0 ≤ 0; conditional pairwise independence (the version in Definition 3.5); polynomially bounded parameters; arbitrarily small step size; two constraints on λ; conclusion counts coordinates that ever cross the threshold.

Comparison: shipped `everBad` (∃ t ≤ T, B ≤ Z t ω i) matches “ever become bad.” ✓ λ ≤ θ/2 and λB ≤ log N match verbatim. ✓ “Polynomially bounded + arbitrarily small dt + O(·) constant” are packaged as ∃ C M₀ ε₀ (ledger deviation 3); failure probability is 1/N. ✓ Definition 3.5 in the paper says: “E[⟨γ,X⟩²] ≤ α·E[⟨γ²,X²⟩] and E[X(i)] ≤ −θ·E[X(i)²]”; `CondPWSlackU` at S = all and ε = 0 matches it verbatim. ✓

### c5 (multilayer version of Lemma 3.6, §5.2)

Source (§5.2): “the increment of this vector is (α_ℓ, θ_ℓ)-pairwise independent with α_ℓ := k_ℓ/(µη_ℓ) = 6k_ℓ2^ℓ/µ and θ_ℓ := β_ℓ/10 = b_ℓ/(2^ℓ·100k_ℓ)”; increment identity (multilayer form of equation (19), §3.2.1): dY^(ℓ)(i) = ⟨E^(ℓ)_{t,i}, v_t⟩√dt − β_ℓ⟨a_i², v_t²⟩dt.

Retranslation: the paper's α_ℓ expression uses the upper bound k_ℓ/µ (after |M^(ℓ)|/n_t ≤ k_ℓ/µ); θ_ℓ = β_ℓ/10; based on η = 1/6, η_ℓ = η/2^ℓ, |E^(ℓ)(j)| ≤ 1.2|a_i(j)|, and β_ℓ ≤ 0.1.

Comparison: shipped α uses the exact history-dependent value (2^ℓ/η)(|M^(ℓ)|/n_t), while the paper's 6k_ℓ2^ℓ/µ is its upper bound on the invariant event. The exact form is stronger and c6's inductive structure needs it (on histories where the invariant fails, the paper's upper bound does not hold); recorded in §4 of the ledger. (i) The support restriction (only medium rows) matches the paper's application: the affine spectral-independence constraint covers only rows of E^(ℓ) (the medium rows). (ii) Shipped version applies to all rows, whereas the paper states it only for medium rows. The same calculation for large rows was checked in the ledger (β_ℓ² ≤ 2.5η follows from β_ℓ ≤ 0.1); this is a natural extension of the paper's method and needs no new premise.

### c6 (Lemma 5.2)

Source: “Assume k = Ω(log² n). Then, with high probability, for all columns j ∈ [n] and all levels ℓ ∈ {0, ···, L}, at most k_ℓ rows in column j ever reach level ℓ. Moreover, at most k_L/100 rows in column j ever become dangerous at level L.”

Retranslation: k = Ω(log² n); with high probability, two count bounds (at most k_ℓ rows ever reach level ℓ; at most k_L/100 rows become dangerous at level L).

Comparison: shipped version states all parameters from the §5.1 table as premises (k_ℓ = k/100^ℓ, b_ℓ = C2^ℓ√k_ℓ, β_ℓ = b_ℓ/(2^ℓ·10k_ℓ), µ = b₀²/log n, the bounds on L, η = 1/6); these are defined in §5.1 and directly used in the proof of Lemma 5.2. ✓ “Ω(log² n) and C sufficiently large” are made explicit as ∃C_th, where C_th depends only on m,n,A,η and the internal constant in c4. ✓ “With high probability” becomes ≥ 1 − 1/√n (the paper's proof gives 1 − 1/poly(n), and 1/√n suffices for a fixed polynomial). ✓

### c7 (Theorem 1.3)

Source: “Let A ∈ {0,1}^{m×n} be a set system where each element lies in at most k sets. If k = Ω(log² n), then disc(A) = O(k^{1/2}).” (Theorem 5.1 is its exact form, stated for {0,±1} matrices, with no hidden factor in the k ≥ log² n branch.)

Retranslation: {0,1} set system; column degree ≤ k; k = Ω(log² n); disc = O(√k).

Comparison: shipped version uses {0,±1}, the stronger form of Theorem 5.1; §5 of the paper proves this form. Ω/O are made explicit as ∃c C. The premise n ≥ 2 is the standard explicit threshold for Theorem 3.7's asymptotic phrase “n sufficiently large.” Together, k ≥ c(log n)² and k ≤ n imply that for small n the interval is either empty (so the implication is vacuously true) or covered by the constant. The existence form of disc agrees verbatim with the definition in §1 of the paper. ✓

## Ambiguities and differences on record

1. **Factor r_s (corrected):** the first pass wrote the c1 affine-constraint factor as R_s/η_s (where R_s is the number of rows), but the paper uses r_s/η_s with r_s = R_s/h. This would introduce a factor of h when consumed by c7. It was corrected to R_s/(h·η_s), and all consistency checks were rerun.
2. **Premise r_s ≥ 1:** Appendix A.4 has r_s ≥ 1 (that is, R_s ≥ h), but the main text of Theorem 2.2 does not. Its proof (Claim A.6) works for arbitrary R_s ≥ 1, and in applications in §§3 and 5, r_1 = |M_t|/n_t may be less than 1. The shipped premise is R_s ≥ 1, matching actual use in the paper.
3. **“<” vs. “≤” for small rows:** §3.1 says “less than µ,” §4 says “≤ µ_p,” and §5.1 says “at most µ.” Shipped version uses ≤, matching the selected formulation in §5.
4. **Summation range for energy G:** equation (18) sums over all coordinates; §5.1 uses only live elements. The difference is at most the dead-element contribution, #dead/n ≤ 1, which is absorbed in the check β_ℓG ≤ b_ℓ. Shipped version uses the all-coordinate form.
5. **Logarithm base:** not specified in the paper. The difference between the natural-log and base-2 conventions used in the literature is absorbed into constants in k = Ω(log² n). Shipped version uses `Real.log` (natural logarithm).
6. **Choice of polynomial for “with high probability”:** c3 uses n^{-(c+1)} and c6 uses 1 − 1/√n; both are valid instantiations of the paper's “1/poly(n),” and constant absorption was checked in §4 of the ledger.

## Conclusion

The seven shipped statements agree item by item with the paper under the recorded choices of formulation. The second pass found no additional statement errors.
