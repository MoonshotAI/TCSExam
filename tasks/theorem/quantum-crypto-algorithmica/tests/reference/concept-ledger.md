# concept-ledger — lean-quantum-crypto-algorithmica (component crosswalk)

This ledger compares eight assessed claims with arXiv 2212.00879v2, Kretschmer–Qian–Sinha–Tal, “Quantum cryptography in Algorithmica,” STOC 2023. It records fidelity deviations and shows how the main theorem is assembled.
For each assessed claim, the ledger gives the source numbering, a plain-language description, the premises and conclusion of the Lean statement, and any differences from the source (numbered in the “deviation list”). The comparison was against the paper's LaTeX source (`main.tex`; the PDF and full text are in the same directory).

## 0. Crosswalk between the definition layer and source objects

| Lean object | Source object | Correspondence |
|---|---|---|
| `Bits n` = Fin n → Bool | {±1}ⁿ (input strings); `N = 2^n` strings | Bool true ↔ −1 (`sgnVal`), encoding the source's `S(x) = {i : x_i = −1}` |
| `sgnVal b` | A value in ±1 | false ↦ 1, true ↦ −1 |
| `chi u y` | Walsh character χ_S(x) = ∏_{i∈S} x_i (§2, Fourier preliminaries) | Product over coordinates |
| `fhat f u` | f̂(x) = 2^{−n}∑_y χ_x(y)f(y) (§2, expectation normalization) | Literal correspondence (the 1/2ⁿ normalization on source line 500) |
| `hadMat n` | Walsh–Hadamard matrix H (§3, walk; H_{x,y} = χ_x(y)/√N) | Symmetric and self-inverse (proved in the fixed layer as `hadMat_mul_self`) |
| `trnc` / `trncHalf` | trnc / trnc_{1/2} (§2 notation: trnc_a clips to [−a,a]; omitted subscript means a=1) | `max (−a) (min a z)`; the fixed layer proves `trncHalf_eq` (`trnc_{1/2}(x) = ½trnc(2x)`, the identity used in source §3.1) |
| `epsF n` | ε = 1/(100n) (end of Definition 8) | Literal correspondence |
| `mWalk n` | m = 200 ln N/ε (step 1 of the proof of Theorem 10) | Rounded up to an integer (deviation 6); ln is the natural logarithm (source convention in §2) |
| `biasF f x` | trnc(√(ε2ⁿ)·f̂(x)) (bias in Definition 8) | Literal correspondence (source lines 614–615) |
| `forrWt f g` | Product probability for g given f: ∏_x (1+g(x)·bias_x)/2 | Weight form of the sampling semantics in Definition 8 (`g(x) = 1` with probability (1+bias)/2) |
| `forrExp C` | E_{(f,g)∼F_n}[C(tt f, tt g)] (left-hand side of Theorem 9/10) | f is uniform over the 2^N functions; g is drawn according to `forrWt` |
| `unifExp C` | E_{z∼{±1}^{2N}}[C(z)] (right-hand side E[C] of Theorem 9/10) | Uniform average over the cube |
| `mlEval c z` | Multilinear function (§2: the unique multilinear expansion, extended from its domain to ℝⁿ) | Expansion with coefficient function c : Finset κ → ℝ; the Forrelation instance uses κ = Bits n ⊕ Bits n |
| `restr ρ z` | Restriction (CHHL19/KQST23: some coordinates fixed to constants in ±1) | ρ : κ → Option Bool; `some` fixes a coordinate and `none` leaves it free |
| `fourierMass2 g` | L_{1,2}(f) = ∑_{|S|=2} |f̂(S)| (§2, line 504) | Evaluation form: f̂(S) = 2^{−|κ|}∑_z χ_S(z)g(z); it agrees with the coefficient form for multilinear g |
| `XStep`/`YStep`/`XLe`/`YLe` | Walk update (proof of Theorem 10: X^{≤i} = X^{≤i−1} + D⊙trnc(X^{(i)}), Y^{≤i} = trnc(Y^{≤i−1} + trnc_{1/2}(√ε H D⊙X^{(i)})), D = 1−|X^{≤i−1}|) | Literal correspondence; driver sequence u : ℕ → Bits n → ℝ, and step i reads u i |
| `stepMeasure`/`drvMeasure` | X^{(i)} ∼ N(0,ε)^N, independently and identically distributed | Finite product measure of coordinate-wise `gaussianReal 0 ε` (drivers indexed by Fin (mWalk n)); `finDrv` views the finite family as a sequence indexed by ℕ |
| `polWalk A` | One-dimensional recurrence in CHHL19 Claim 3.5: B_i = B_{i−1} + (1−|B_{i−1}|)A_i | Literal correspondence |
| `gaussianFoolingProp` | Theorem 15 ([RT19], as restated in [CHLT19, Theorem 9]) | Packaged assumption; see deviation 7 in §2 and the crosswalk below |
| `gaussianTailProp` | Textbook Gaussian tail bounds (used in proofs of Claims 11/12) | Packaged assumption with two bounds: two-sided tail P(|X|≥t) ≤ 2e^{−t²/2v}; and truncated second moment E[X²1_{|X|≥t}] ≤ 2v(t/√v+√v/t)/√(2π)·e^{−t²/2v} (from the Mills ratio) |
| `goodHist K C t x y` | “Good history” predicate in Claim 13 (`y ∈ [−1/2,1/2]^N` and a bound on the expected step size) | See claim c7 |

## 1. Claim-by-claim comparison

### c1 `multilinear_lipschitz` = Fact 14 (the source describes it as an expert-known but unpublished result and cites [CHLT19, Lemma 2.7])

- Source: Let C : [−1,1]^{2N} → [−1,1] be a multi-linear function. Then for every z, z′ ∈ [−1,1]^{2N} we have |C(z) − C(z′)| ≤ 2N·‖z−z′‖_∞.
- Lean: For `mlEval c`, if it is bounded on the box (premise `hbox`), then `|mlEval c z − mlEval c z'| ≤ (Fintype.card κ) * sup'_i |z i − z' i|`; the premises `hz` and `hz′` put both points in the box; κ is nonempty.
- Comparison: |κ| is 2N ✓; `sup'` is ‖·‖_∞ ✓; boundedness on the box matches the source's range [−1,1] (values ±1 at cube vertices imply boundedness on the box; the fixed layer proves this bridge as `abs_mlEval_le_one`). The `Nonempty` premise is clean: the source has 2N ≥ 2, while `sup'` is undefined for an empty type. The empty-type case is excluded (κ = Bits n ⊕ Bits n is nonempty at c8 ✓).

### c2 `forrelation_expectation` = expansion of Definition 8 + the identification at the end of the proof of Theorem 10

- Source (final paragraph): “we observe that X′ is the uniform distribution over {−1,1}^N and the expectation of any multilinear polynomial under (X′, trnc(√ε H X′)) is the same as that under the Forrelation distribution F_n.”
- Lean: Two parts: `forrExp (mlEval c) = 2^{−N}·∑_f mlEval c (Sum.elim (sgnVal∘f) (biasF∘(sgnVal∘f)))` and `unifExp (mlEval c) = mlEval c 0`.
- Comparison: ① First part: under Definition 8, the coordinates of g are independent and have mean `bias`; taking expectation of a multilinear C over g equals evaluating it at the bias vector (finite expansion, no probability theory) ✓. ② Second part: the expectation of a multilinear polynomial under the uniform distribution is its constant term, C(0⃗) ✓ (the source's use of E[C] = C(0⃗) runs throughout the assembly). ③ Link between the walk's `trnc(√ε H X′)` and Definition 8's `trnc(√(ε2ⁿ)f̂)`: √ε·(Hf)(x) = √(ε2ⁿ)·f̂(x) because f̂ = Hf/√N; numerical check in small example E14 ✓. This identity gives “X′ uniform ⟹ walk-output expectation = F_n expectation.”

### c3 `restriction_identity` = Claim 16 (restated in KQST23 from [CHHL19, Claim 3.3])

- Source: Let f be a multilinear function on ℝⁿ and v ∈ (−1,1)ⁿ. Let δ ∈ [0,1]ⁿ with δ_i ≤ 1−|v_i|. Then, there exists a distribution over random restrictions ρ such that for any z ∈ ℝⁿ, f(v + δ⊙z) − f(v) = E_ρ[f_ρ(z) − f_ρ(0⃗)].
- Lean: There is a finite set W of functions with values in {−1,0,1} and nonnegative weights p summing to 1 such that the identity holds for every z. Here w i = ±1 freezes the coordinate and w i = 0 leaves it free (`f_ρ(z) := f(w + (1−|w|)⊙z)`).
- Comparison: ① Range of v: the source uses the open cube (−1,1)ⁿ; Lean uses the closed cube [−1,1]ⁿ (deviation 4). At the boundary, |v_i| = 1 forces δ_i = 0, and the identity still holds (the explicit distribution degenerates to freezing that coordinate); the walk history can contain ±1 (clipping atoms), and the closed cube is needed to apply Claim 13. ② Class of “random restrictions”: KQST23 does not expand this definition (a note says this form is implicit in the CHHL19 proof). The task authors prove an explicit product distribution (coordinates independent: freeze +1 with probability (1−δ_i+v_i)/2, freeze −1 with probability (1−δ_i−v_i)/2, keep free with probability δ_i; nonnegativity follows exactly from δ_i ≤ 1−|v_i|). They cross-check it against the original proof of CHHL19 Claim 3.3 (special case δ = 1−|v|: freeze sign(v_i) with probability |v_i|, otherwise choose ±1 according to (x_i+1)/2). Both have the same coordinate-wise moments E[w_i] = v_i and E[w_i+(1−|w_i|)z_i] = v_i + δ_i z_i. Small example E6 checks the full identity numerically, including boundary points and z outside the cube ✓. ③ The source allows z ∈ ℝⁿ (a polynomial identity, not restricted to the cube) ✓; Lean does too.

### c4 `polarize_1d` = Claim 17 ([CHHL19, Claim 3.5])

- Source: Let A_1,…,A_m ∈ [−1,1] be independent symmetric random variables with E[A_i²] ≥ p. For i = 1,…,m define B_i = B_{i−1} + (1−|B_{i−1}|)A_i, where B_0 = 0. Then E[B_m²] ≥ 1−q for q = 3exp(−mp/16).
- Lean: On a probability space, `iIndepFun A μ`; for each i, `IdentDistrib (A i) (−A i)` (symmetry); pointwise |A i ω| ≤ 1; and `p ≤ ∫ (A i)²` when i < m. Conclusion: `1 − 3*exp(−(m*p)/16) ≤ ∫ (polWalk A m)²`.
- Comparison: The four premises—independence, symmetry, boundedness, and second moment—match item by item; the recurrence is literal; the constant 3 and exponent −mp/16 in the conclusion are literal. Boundary case m = 0: B_0 = 0, so the conclusion 0 ≥ 1−3 ✓ holds. Measure-theoretic formalization: independence and symmetry are stated using mathlib's `iIndepFun` and `IdentDistrib` (standard formal forms of the source's probabilistic statements). The CHHL19 proof was checked (recurrence for C_i = 1−|B_i|, square-root moment, then Markov plus a trivial bound). Its statement that “|B| and sign(B) are independent” is loose at B=0 but does not affect the result: for either convention for sign(0) in ±1, the pointwise recurrence and conditional-factor bound hold. The guided-tier proof idea follows this argument.

### c5 `walk_untruncated` = Claim 11

- Source: With probability at least 1−m/N^{10}, for all i ∈ [m]: Y^{≤i} = √ε H X^{≤i} and Y^{≤i} ∈ [−1/2,1/2]^N.
- Lean: `(drvMeasure n).real {ω | ∀ i ≤ mWalk n, (∀ j, YLe i (finDrv ω) j = √ε·(hadMat n *ᵥ XLe i (finDrv ω)) j) ∧ (∀ j, |YLe i (finDrv ω) j| ≤ 1/2)} ≥ 1 − m/N^{10}`, with premise n ≥ 1.
- Comparison: ① Range of i: the source uses [m]; Lean extends this to i = 0 (YLe 0 = 0 = √ε·H·0 and 0 ∈ [−1/2,1/2], so this case is true) ✓. ② Probability bound m/N^{10} is literal; m = ⌈200 ln N/ε⌉ (deviation 6) does not change the form of the bound: the source induction gives Pr ≥ 1 − i/N^{10}, then sets i = m. ③ Premise n ≥ 1: not explicit in the source, but its proof's bad-event sum 2N e^{−1/(2ε)} + 2N e^{−1/(8ε²)} + 2N e^{−1/(8ε)} ≤ 1/N^{10} holds throughout n ≥ 1 (checked in small example E8; starting at n=1, each term is at most 2^{−10n}/3). When m/N^{10} > 1 the statement is vacuously true, so n ≥ 1 covers the entire non-vacuous range ✓. ④ The two truncations in Y^{≤i} disappear on the good event (`trnc_of_abs_le`), and the linearized identity follows from linearity of H ✓. The guided-tier proof follows the source's details: induction on E_i with three bad events at each step.

### c6 `walk_polarized` = Claim 12

- Source: With probability at least 1−1/N², we have |X^{≤m}| ∈ [1−1/N³, 1]^N.
- Lean: Has premises `7 ≤ n` and `hGT`; conclusion has the same form (1−1/N³ ≤ |X^{≤m}_j| ≤ 1 for every j).
- Comparison: ① Probability 1−1/N² and interval [1−1/N³, 1]^N are literal (the upper bound follows from the fixed-layer lemma `abs_XLe_le`; including it in the statement matches the source interval) ✓. ② **Premise n ≥ 7 (deviation 5):** the source's proof step q = 3e^{−mε/32} ≤ 1/N⁶ requires 3 ≤ N^{1/4}, or N ≥ 81 (n ≥ 7). Small example E9 verifies pointwise that this step fails for n ≤ 6 (at n=6, q/N⁻⁶ ≈ 1.09 > 1). The source omits the premise, leaving “for sufficiently large N” implicit in the print; it is made explicit here for the range where the proof is valid. ③ Chain E[A_i²] ≥ ε − 1/N⁵⁰ ≥ ε/2: the second truncated moment is bounded by the second part of `gaussianTailProp`, giving at most 1/N⁵⁰ (checked in E9: 2ε(1/√ε+√ε)/√(2π)·e^{−1/(2ε)} ≤ 2^{−50n}, valid for all n ≥ 1); and 1/N⁵⁰ ≤ ε/2 for n ≥ 1 ✓. ④ Markov plus a union bound over coordinates: Pr[1−|B_m| ≥ 1/N³] ≤ N³·E[1−|B_m|] ≤ N³·N⁻⁶ = N⁻³; union over N coordinates gives N⁻² ✓.

### c7 `step_small` = Claim 13

- Source: For any i ∈ [m], with probability at least 1−2/N² over (X^{≤i−1}, Y^{≤i−1}) (the history before step i), the i-th step size satisfies E_{X^{(i)}}[C(X^{≤i},Y^{≤i}) − C(X^{≤i−1},Y^{≤i−1})] ≤ O(tε/√N).
- Lean: `∃ K > 0, ∀ i ∈ Finset.Icc 1 (mWalk n), (drvMeasure n).real {ω | goodHist K (mlEval c) t (XLe (i−1) (finDrv ω)) (YLe (i−1) (finDrv ω))} ≥ 1 − 2/N²`; premises n ≥ 2, hGF, hGT, C Boolean-valued (hBool), t ≥ 0, and L_{1,2} ≤ t for all restrictions (hL12).
- Comparison: ① **Two-sided form (deviation 3):** the source prints a one-sided statement (without absolute value), but its proof gives a two-sided bound via Theorem 15, and the assembly uses the two-sided form (absolute value of the conditional expected difference). Lean uses |·| (second part of `goodHist`). The one-sided statement follows by symmetry (assuming closure under negation) and is equivalent. ② Good-history predicate: the source proof assumes y^{≤i−1} ∈ [−1/2,1/2]^N (this occurs with probability at least 1−1/N²); Lean includes that condition in the definition of good history (first part of `goodHist`). Thus c7's probability bound 1−2/N² matches the union of the source's two bad events (y is not small; Hoeffding event fails) ✓. ③ Premise n ≥ 2: by c5, the probability that y is small is at least 1−m/N^{10}, and m ≤ N^8 exactly when n ≥ 2 (checked in small example E10, including the ceiling margin) ✓. ④ Constant in O(tε/√N): expressed as ∃K, matching the source's O(·); since `gaussianFoolingProp` requires t ≥ 1, the right side is written with max(t,1) (deviation 2, also affecting the main theorem). ⑤ Covariance check for δ := ε/√N: Var(X_j) = ε; Var(2√ε H(d⊙X))_j = 4ε²∑H²d² ≤ 4ε² ≤ ε; cross-covariance ≤ 2ε^{3/2}/√N ≤ δ; H-covariance ≤ 4ε²/√(εN) = 4ε^{3/2}/√N ≤ δ (since 4√ε ≤ 1). The variance condition ε ≤ 1/(8 ln(2N/δ)) holds for every n ≥ 1 (checked in E10) ✓. ⑥ Hoeffding event: rows of H are orthogonal and entries are ±1/√N, so for j≠k there are exactly N/2 terms +1/N and N/2 terms −1/N. Paired differences (D²_l − D²_l')/N are independent, symmetric, and bounded by 1/N; 2e^{−1/ε} = 2/N^{100}, and a union bound over pairs gives 2N²/N^100 ≤ 1/N² (E10) ✓. ⑦ Applying Claim 16 at v = (x,y) ∈ [−1,1]^{2N}, δ = (d, 1/2): d_j = 1−|x_j|, and 1/2 ≤ 1−|y_j| when y is small ✓. The closed cube in c3 is necessary here because x may contain ±1; see c3.

#### Statement requirements

- The original statement placed `∃ K` after `{n} c t`, allowing K to depend on n, c, and t. Taking `K := 200·n·√N/max(t,1)` makes the right side `K·max(t,1)·ε/√N = 2`. Since C is bounded on the cube (hBool + `abs_mlEval_le_one`), the integrand is pointwise at most 2; the second part of `goodHist` then holds for every ω, so the event reduces to the small-y event alone (a consequence of c5). The entire `gaussianFoolingProp` result (the mathematical content of this claim) was bypassed; the grader confirmed that this inflated proof passed.
- Repair: move `∃ K` before `{n} c t` (aligning with the ∃K ∀n form of the c8 main theorem). K can no longer refer to n, c, or t at the type level, so the inflated witness above is rejected mechanically at compile time. The source meaning of O(·) (a constant independent of n; the proof takes K := K_GF) is unaffected, and the guided-tier wording “gives the claim with K := K_GF” remains literal.
- Additional check (same report): the first part of `goodHist`, `∀ j, |YLe j| ≤ 1/2`, is not constructionally true. The outer truncation in YStep is trnc (clipping to [−1,1]); two saturated increments of the same sign can add up to 1 (machine counterexample: n = 10, drive first constantly 1/2 and then constantly 1; YLe 2 = 1). This part retains actual probabilistic content, so the claim definition was not changed.

### c8 `forrelation_pseudorandom` = Theorem 10 (main theorem)

- Source: Let N = 2^n. Let 𝒞 be a family of 2N-variate Boolean functions, which is closed under restrictions. Assume that for any C ∈ 𝒞 it holds that L_{1,2}(C) ≤ t. Then, for any C ∈ 𝒞 it holds that |E_{f,g∼F_n}[C(tt f,tt g)] − E[C]| ≤ O(t·log N/√N).
- Lean: `∃ K > 0, ∀ n ≥ 1, ∀ c, (hBool : ±1-valued on the cube), ∀ t ≥ 0, (hL12 : fourierMass2 ≤ t for all ±1 restrictions) → |forrExp (mlEval c) − unifExp (mlEval c)| ≤ K * max t 1 * (Real.log (2^n) / Real.sqrt (2^n))`.
- Comparison: ① **∃K ∀n≥1 form (deviation 2):** standard explicit form of O(·). Small n are absorbed using the trivial bound ≤ 2 for both `forrExp` and `unifExp` (averages of ±1-valued functions; `forrWt` sums to 1, checked in E12), max(t,1) ≥ 1, and min_{1≤n≤n₀} ln(2ⁿ)/√(2ⁿ) > 0 over finitely many n. K can cover these cases. For large n, use the walk assembly (threshold n₀ = 24 for δ ≤ 1/N; checked in E10, Pr[¬ℰ] ≤ 1/N for n ≥ 24), with the constants absorbed likewise. ② **max(t,1) (source of deviations 2/7):** the packaged Raz–Tal theorem (`gaussianFoolingProp`) requires t ≥ 1, as stated in CHLT19 Theorem 9; hence the proof route yields a right side with max(t,1)·…. For t ≥ 1 this matches the source. For t < 1, the source's printed O(t·log N/√N) is not covered by its own proof (because CHLT19 Theorem 9 quantifies t ≥ 1); record this. ③ **Family reduced to one function + all-restrictions premise (deviation 7):** the source uses only closure of the family under restrictions; a single function with “L_{1,2} ≤ t for all restrictions” is equivalent (a restriction of a restriction is still a restriction). ④ log is natural logarithm (source uses ln; m = 200 ln N/ε uses the natural logarithm, and a base change is absorbed into the constant) ✓. ⑤ Premises: n ≥ 1 (at n = 0, N = 1 and the ε definition degenerates; the source assumes positive n), C Boolean-valued, t ≥ 0, and the restriction bound ✓.

## 2. Deviation list (same numbering as the task header comments)

1. **Scope restriction:** only Theorem 10 is packaged. Theorem 9 (the AC⁰ special case, using the polynomial(n) bound on L_{1,2} from [Tal17]), the oracle construction (§4), applications to t-Forrelation states and pseudorandom states (§§5–7), and the multi-copy conjecture (§8) are not included. No quantum objects are formalized; this matches the candidate record's scope: the assessed core is pure Boolean-function analysis, with quantum objects only as context.
2. **Explicit form of big O:** the main theorem uses ∃K>0, ∀n≥1, an existence-of-constant form. Small n are absorbed using the trivial bound ≤ 2 and max(t,1) ≥ 1; large n follow from the walk assembly (the δ ≤ 1/N threshold is also absorbed into the choice of K).
3. **Right side max(t,1):** the packaged Raz–Tal theorem (`gaussianFoolingProp`) requires t ≥ 1 in its CHLT19 Theorem 9 restatement; therefore c7/c8 use max(t,1)·…. For t ≥ 1 this agrees with the source.
4. **Closed interval in Claim 16:** v ∈ [−1,1]^κ (the source prints an open interval); at the boundary, |v_i| = 1 forces δ_i = 0, so the identity still holds. The walk history can include ±1 (clipping atoms), and the closed interval is needed to apply Claim 13.
5. **Added premise n ≥ 7 to Claim 12:** omitted in the source; its proof step q = 3e^{−mε/32} ≤ 1/N⁶ requires 3 ≤ N^{1/4}. Added n ≥ 2 to Claim 13, needed for m ≤ N^8. Both are made explicit for the range in which the proof is valid.
6. **m rounded up to ⌈200 ln N/ε⌉:** the source writes 200 ln N/ε as a number of steps (a real value); rounding does not change the form of any bound. The margin is checked in small examples E9/E10.
7. **Two packaged external facts:** `gaussianFoolingProp` (RT19 restated through CHLT19; single-function plus all-restrictions form) and `gaussianTailProp` (tail bound plus truncated second moment; Mills-ratio constant checked and numerically rechecked in small example E13). Not packaged: Hoeffding (mathlib already has the sub-Gaussian API), Fact 14 / Claim 16 / Claim 17 (the substance of c1/c3/c4, respectively), and Tal17 (outside the scope with Theorem 9).

## 3. Main-theorem assembly check (c1–c7 ⟹ c8)

Proof obligations for c8 (to be completed by the model) = the assembly portion of the proof of Theorem 10 + three claims. Checked step by step:

1. **Good event ℰ:** c5 event (failure ≤ m/N^{10}) ∩ c6 event (failure ≤ 1/N²) ∩ good history in c7 at every step (failure ≤ 2/N² per step, union over m steps ≤ 2m/N²). Pr[¬ℰ] ≤ m/N^{10} + 1/N² + 2m/N² ≤ 1/N (n ≥ 24, E10) ✓.
2. **Step-by-step progress:** on ℰ, the history at step i satisfies `goodHist`, and E_{X^{(i)}}[C(new)−C(old)] ≤ K₇·max(t,1)·ε/√N. Conditioning changes the distribution of X^{(i)} by total variation at most δ; the integrand is bounded by 2 (C is bounded on the box via `abs_mlEval_le_one`). Thus |E[·|ℰ] step difference| ≤ K₇·max(t,1)·ε/√N + O(δ). Telescoping over m steps gives ≤ O(m·max(t,1)·ε/√N) = O(max(t,1)·ln N/√N) (m·ε = 200 ln N + O(ε), E15) ✓. Start point (X⁰, Y⁰) = (0,0): C(0⃗) = `unifExp` (second part of c2) ✓.
3. **Rounding:** on ℰ, |X^{≤m}| ∈ [1−1/N³,1]^N, so X′ := sgn(X^{≤m}) is within sup distance 1/N³ of X^{≤m}. Let Y′ := √ε H X′; by c5, Y^{≤m} = √ε H X^{≤m}, and their difference is `err`, with each coordinate at most √ε·√N/N³ ≤ 1/N² (√(εN) ≤ N always holds) ✓. Also Y′ ∈ [−1,1]^N (|Y′| ≤ |Y^{≤m}| + |err| ≤ 1/2 + 1/N² ≤ 1; N ≥ 2, i.e. n ≥ 1) ✓. c1 (Fact 14) gives |E[C(X′,Y′)|ℰ] − E[C(X^{≤m},Y^{≤m})|ℰ]| ≤ 2N·(1/N²) = 2/N ✓ (premise: bounded on the box, from `abs_mlEval_le_one` + hBool).
4. **X′ is uniform:** coordinates are independent (the walk updates coordinates independently and drivers are coordinate-wise independent) and symmetric (negating all drivers negates the walk; the Gaussian symmetric measure is invariant). Coordinates have no atom at 0 (clipping creates atoms only at ±1; before a coordinate reaches ±1 it has a density component); hence `sgn(X^{≤m})` is uniform on the cube ✓.
5. **Identification:** since X′ is uniform, E[C(X′, trnc(√ε H X′))] = 2^{−N}∑_f C(f, trnc(√ε H f)) = 2^{−N}∑_f C(f, bias_f) (√ε(Hf) = √(ε2ⁿ)f̂, E14) = `forrExp C` (first part of c2) ✓. Remove conditioning with a δ correction (≤ 2δ·1) ✓.
6. **Combine:** |forrExp − unifExp| ≤ O(m·max(t,1)ε/√N) + 2/N + O(δ) ≤ K·max(t,1)·ln N/√N, choosing K to cover the constants and the finite range n < 24 ✓.
7. **Premise transfer:** for n ≥ 24, c8's branch uses c5 (n ≥ 1 ✓), c6 (n ≥ 7 ✓ since 24 ≥ 7), and c7 (n ≥ 2 ✓). c7's hBool/ht/hL12 come directly from the c8 premises of the same names ✓; `gaussianFoolingProp`/`gaussianTailProp` are supplied by c8's hGF/hGT ✓ (under the axiom-injection mechanism, c8's proof references the claims and their premises).

## 4. Degenerate cases and vacuity check (summary of the 6.5 self-check)

- c1: `sup'` is undefined when κ is empty; the `Nonempty` premise excludes this, and κ is nonempty at c8 ✓.
- c2: when n = 0, N = 1; in F_0, f is uniform over ±1 and g has zero bias and is uniform, so the identity `forrExp = unifExp` still holds by algebra ✓.
- c3: κ empty, δ = 0, and boundary v (±1) all hold pointwise (E6 includes a boundary case) ✓.
- c4: m = 0 (B_0 = 0, 0 ≥ 1−3 ✓); p ≤ 0 (right side of the conclusion is > 1, hence trivially true) ✓.
- c5: for n ≥ 1, when m/N^{10} > 1 the statement is vacuously true; the non-vacuous range holds by E8 ✓.
- c6/c7 premises (n ≥ 7 / n ≥ 2) are the proof's valid ranges; small examples confirm the thresholds are tight (at n=6, c6's q ≤ N⁻⁶ step fails, so the premise cannot be removed) ✓.
- c8 vacuity: assumptions are satisfiable (`gaussianFoolingProp` and `gaussianTailProp` are proven theorems; C = constant 1 with any t ≥ 0 satisfies hL12; C = product of two coordinates with t = 1 also satisfies it) ✓ non-vacuous.
- Premise synchronization: c8's large-n branch supplies each premise required when calling c5/c6/c7 (see step 7 in §3) ✓.
