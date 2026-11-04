# Independent Retranslation Comparison: The Monotonicity-Testing Lower-Bound Chain

This record compares two translations of the CCCPS26 monotonicity-testing lower-bound chain, documenting the sources, adjudications, and outcome.

- Adjudication is based on the original arXiv 2511.04558v2.
- This is the second of three fidelity records (independent retranslation).

## Sources and independence

- **B version (retranslation cards):** Its only input was the full paper text. The task required recovering each premise, quantifier, and boundary condition and marking possible OCR issues. A's Lean statements had not been shown when B was written, so the two did not see each other's formulations.
- **A version (shipped):** It used the same paper text and was drafted before B was delivered. Two key judgments were independently made in A: Claim 28's premise should be |R| ≤ √n/2 rather than the printed n/2, and the logarithm in Claim 28 must be base 2. B independently reached both conclusions.
- Thus, the comparison is independent in both directions: neither version knew the other's specific formulation.

## Item-by-item comparison

Read each row as one decision; the adjudication column gives the conclusion and supporting basis.

| Decision | A version (shipped) | B version (retranslation cards) | Adjudication |
|---|---|---|---|
| Convention for √n | Parameterize n = m² (s = m, N = 2^m). | Card 0: §3 begins by assuming √n is an integer (pdftotext displaced the line, making it easy to misread). | ✓ Consistent; A's parameter m faithfully implements the convention. |
| Star rule for ΓM | Even layer: no active edges → 0*, multiple active edges → 1*; odd layer: the reverse. | Same on card 3. | ✓ Identical (verified by small examples E1/E3). |
| Truncation in f_{M,H} | Strictly outside: > n/2+s gives 1; < n/2−s gives 0; the middle layer includes endpoints. | Same on card 4 (“no ambiguity at the threshold” because √n is an integer). | ✓ Consistent. |
| Sampling Dyes/Dno | M has the same distribution on both sides; Hyes uses a constant bit at each leaf; Hno uses a global secret variable plus a sign bit per leaf. | Same on card 5; also confirms both constants are exponentially small in ℓ. | ✓ Consistent (the existential constant forms in c3/c8 cover this). |
| Treatment of Lemma 8 | Folded into c1 rather than stated as its own checkpoint. | Card 2 confirms it consists of two observations used in the proof of c1. | ✓ Consistent; the engine is exhaustively checked by E3. |
| Form of Lemma 5 | Counted separately for each g: |S| ≤ disagreeCount f g. | Card 7: dist ≥ max_S |S|/2ⁿ, with note that this is over logarithmic distance, not point count. | ✓ Consistent; A uses the per-g form, equivalent after minimizing over all monotone g. |
| Form of Lemma 10 | ∃ ε c > 0, ∃ m₀, with explicit constants. | Card 8: two Ω(1) bounds, with constants exponentially small in ℓ. | ✓ Consistent (Ω(1) means a positive constant). B flags a suspicious second factor in the proof: `1−((n−|x*|)/n)^{√n}` versus the standard calculation `1−(|x*|/n)^{√n}`. It does not affect any shipped statement and is recorded in Section 7 of the component ledger. |
| Strong oracle and outcome construction | `oracle`/`Answer`, `memP`/`memR`/`memRho` (case 3 records only a < a₂ and a ≠ a₁). | Same on cards 9/10; confirms that ρ is defined on all of P_u using the two returned bits in the k = 2ℓ−1 case. | ✓ Identical (structural facts checked by E11). |
| Treatment of Fact 11 | Its first two parts go into `Consistent` (c4 premise); the product structure is inline in the c7/c8 proofs. | Same on card 11 (parts 1 and 2, plus part 3's ρ-consistency). | ✓ Consistent. |
| Treatment of Facts 12/16 | Abstract premises for c5 (`hnested` includes a non-root restriction, plus `hchild`, `hroot`, `hmid`). | Same on cards 12/14 (including both the root-level 2|Q| form and the nonempty-P count (2ℓ+1)|Q|). | ✓ Consistent; the nonempty-P count is used in the c7 proof (Fact 12(3)). |
| Dangerous set and B | `Dset` = [n] ∖ (A_{u,0} ∪ A_{u,1}) (empty if P_u is empty); `Broot` = B_ε. | Cards 13/17: the complement bar was lost from `paper.txt`; independent evidence confirms the complement. | ✓ Consistent; both independently read it as a complement. |
| Making Lemma 15 explicit | α_M ≤ (1 + 2|B|/n)·β_M, with premise 2|B| ≤ n. | Card 15: o(1) is exactly |∪D_u|/n; α_M = 2^{−m}, β_M ≥ (1−o(1))·2^{−m}. | ✓ Consistent; 1/(1−t) ≤ 1+2t for t ≤ 1/2 is an explicit upper-bound form of B's conclusion. Both separately checked the m = 0 boundary. |
| Definition 18 | Its three conditions go into `IsGoodOutcome` (constant 100, and even-layer restriction to non-root). | Same on card 16, noting that 100 is the coefficient in Lemma 27's K′ = 100√n log n. | ✓ Consistent; c6's |Δ| ≥ 100·s·t has the same form. |
| Claims 21/22, Corollaries 24/25, and Lemma 26 | Folded into the proof of c5 (expanded in the guided-tier docstring). | Cards 17/18: asymmetric shape min(|P_u|², |P_v|), constants 150/250, and smoothing-lemma exponent 1+α/(1+α). | ✓ Consistent; both identify the asymmetric shape as the source of α = 1. |
| Explicit bound in Lemma 19 | |B| ≤ 4^{2ℓ−1}·(2q)^{1+1/(2ℓ)}·K. | Card 19: the same closed form from the recurrence and combination of roots; o(n) comes from (log n)^{−1/(2ℓ)}. | ✓ Consistent (E8 numerically confirms the closed form and rate). |
| Premise of Claim 28 | Repaired to 2|R| ≤ s (printed n/2 makes binom(√n−|R|, t) meaningless). | Card 20 independently reaches the same conclusion (“the square root was dropped by pdftotext”; in the application, |R_e| ≤ q ≤ √n/2). | ✓ Both independently derive the same repair. |
| Conclusion of Claim 28 | 50^t·|V| ≤ |U|, t = ⌊log₂n⌋. | Card 20 derives 50^t as (√n/2)·(100√n·t)/(t·n) = 50; the logarithm base must be 2. | ✓ Both independently obtain the same explicit form. |
| Form of Lemma 20 | ∀ δ > 0 ∃ m₀, explicit; Lemma 27 folded in. | Card 20: 1 − o(1), one-step o(1/q), and a union bound. | ✓ Consistent; both versions instantiate c6 in its proof with A = A_{u,1}, Δ, and R = R_e. |
| Form of Theorem 17 | Distributional impossibility for testers (∃ ε,δ, over randomized algorithms); equivalence follows from c1 + c3 + averaging. | Card 21: literal statement, derivation from equation (2), and assembly from the three lemmas. | ✓ Consistent; A's δ = c/4 matches the paper's c_ℓ/4 (Section 4 of the component ledger). |
| Relation to Theorem 1 | Theorem 17, made explicit, is the shipped main theorem. | Card 22: choose ℓ large enough that 1/(4ℓ+2) < c, and absorb the logarithmic factor into the exponent margin. | ✓ Consistent (Section 7 of the component ledger notes that Theorems 2/3 are not covered). |

## Findings from this comparison

1. **No unresolved disagreements.** All 22 cards agree with the shipped statements on the objects, quantifier structure, constants, and boundaries.
2. **B independently confirmed two nontrivial judgments:** the repair to |R| in Claim 28 and the logarithm base 2. Either would directly affect c6 if wrong; independent agreement raises confidence.
3. **Six OCR-suspect items flagged by B** (the displaced √n-integer convention, second factor in Lemma 10, complement bar in Fact 23, |R| in Claim 28, three √n coefficient bars, and logarithm base) were all compared with A's treatment. For the first five, A either restored the meaning from context or avoided the issue (c3 uses an existential-constant form that does not depend on the second factor); for the last, A uses base 2 as required by Claim 28.
4. **One finer confirmation by B:** Lemma 15 at m = 0 (all P_u are empty, so α_M = 1 and β_M = 1) agrees with A's counting form. c4 gives 1 ≤ (1+0)·1 in this boundary case.

## Conclusion

The two translations agree on every statement-layer decision, and there are no unresolved disagreements. The shipped Lean statements are a faithful formalization of the Theorem 17 chain.
