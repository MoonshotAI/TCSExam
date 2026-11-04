# Component Crosswalk — Lean Statements for the LMW24 Single-Query Lower-Bound Core Chain (Proposition 4.4, Lemmas 4.3/4.9, Theorems 4.10/4.17, Lemma 4.11, Lemmas 4.13/4.19, and Lemmas 4.15/4.16)

- What this document contains: A line-by-line crosswalk between the paper and the Lean identifiers in this task, including every deviation and its rationale.
- Intended readers: Task authors and reviewers; one of the three L2 fidelity records (component crosswalk).
- Source: arXiv 2310.08870v1 (2023-10-13; downloaded and; the PDF and full text are stored at `lmw.pdf` / `lmw.txt`). Paper numbering and formulas refer to arXiv v1. The conference version appeared at STOC (ACM Symposium on Theory of Computing) 2024 (pp. 979–990).
- Packaged statements: `environment/app/Task/Basic.lean` (namespace `UnitarySynthesisLB`).

Plain-language terminology (at first use): A **binary phase state** is a complex vector whose amplitudes are all ±1/√N; an **isometry** is a matrix V satisfying V†V = I; an **oracle** is an external function an algorithm can query as a black box, here acting once as a diagonal ±1 matrix O_f; **distinguishing advantage** is the maximum difference in probability between two families of random phase states; **spectral relaxation** replaces “maximize over oracle f” with “maximize over unit vectors,” giving an operator norm of a matrix; **width** is the maximum factor by which a row’s mean-square amplitude exceeds its weight, as defined in Lemma 4.11 of the paper.

## 1. Checkpoint numbering crosswalk

Each row documents one checkpoint. “Dependencies” lists other checkpoints expected to be used in its Lean proof; the grader injects them as axioms in isolation.

| Checkpoint | Lean name | Paper reference | Informal content | Dependencies |
|---|---|---|---|---|
| c1 | `typical_amplitudes` | Proposition 4.4 | After applying V to a random phase state, the mean squared amplitude at coordinate i equals wt_i. | None |
| c2 | `decoupling_advantage` | Lemma 4.3 | E_R[adv] ≤ 4·E_{R,R′} max_f ‖decAdv‖. | None |
| c3 | `spectral_relaxation_dominates` | Lemma 4.9 | max_f ‖decAdv‖ ≤ specRelax. | None |
| c4 | `matrix_rademacher` | Theorem 4.10 (= Theorem 4.1.1 of [Tropp 2015]) | Expectation and tail bounds for a matrix Rademacher series. | None |
| c5 | `spectral_expectation_fixed` | Lemma 4.11 | For fixed R: E_{R′}[specRelax] ≤ √(2 ln(2M)·width(R)/K). | c4 (expectation half) |
| c6 | `sq_rademacher_subexp` | Lemma 4.13 = Lemma 4.19 (proof in §4.6) | ‖S‖²−1 has mean zero and is sub-exponential (γ an absolute constant). | c4 (1×1 tail half) |
| c7 | `width_bound` | Lemmas 4.15 + 4.16 | Width tail bound and expectation bound (when M ≤ e^K, E[width] ≤ C). | c6 |
| c8 | `advantage_expectation_bound` (main theorem) | Theorem 4.17 | ∃ absolute C: E_R[adv] ≤ C·√(ln M/K). | c2, c3, c5, c7 |

Scope crosswalk (items not included): The oracle construction and distinguishing-game layer in Section 3 (Definitions 3.2–3.16, the Talagrand upper tail in Lemma 3.18, the Lipschitz chain in Lemmas 3.23–3.26, and the space compression in §§3.5, 3.29–3.33); Theorem 4.18 (the tail-bound upgrade of the main theorem, = Theorem 4.17 + Lemma 3.18); and the cryptographic consequence in Section 5 (Theorem 5.2) are not formalized. As requested, the task takes only the mathematical core, which contains almost no quantum definitions. The challenger–adversary reduction (Claim 3.17) and the consequence “single-query lower bound ⟹ unitary synthesis is impossible” (Theorems 1.1/1.4) appear only as background in the problem statement. The two halves of Theorem 4.10 form one checkpoint; Lemmas 4.15 and 4.16 form one checkpoint; Proposition 4.20 (E‖S‖² = Σ‖a_i‖²) is not separate and supplies the mean-one part of c6; Bernstein’s inequality (Theorem 4.14, cited from Corollary 2.8.3 of [Vershynin 2018]) is not separate and is an internal ingredient of c7.

## 2. Definitions crosswalk (paper ↔ this task)

| Concept | Paper | Identifier in this task | Notes |
|---|---|---|---|
| Boolean value as ±1 | h : [N] → {±1} | `phase : Bool → ℂ` (true ↦ 1, false ↦ −1) | Bool makes finite enumeration convenient. |
| Function family | R : [K] × [N] → {±1} | `Fam K N := Fin K → Fin N → Bool` | R_k is written `R k`. |
| Phase state | |ψ_h⟩ = (1/√N)Σ_x h(x)|x⟩ (Def. 3.2) | `psi h : Fin N → ℂ` | Equivalent statement. |
| Inner product | ⟨u|v⟩ (conjugate-linear in the left argument) | `cinner u v = Σ i, star (u i) * v i` | Equivalent statement. |
| Isometry weight | wt_{V,i} := (1/N)·⟨v_i|v_i⟩ (Def. 4.1) | `wt V i = (1/N)·Σ_x ‖V i x‖²` | The paper’s |v_i⟩ is the conjugate of row i of V, so ⟨v_i|ψ_h⟩ = (V·ψ_h)_i. |
| Oracle action | O_f (diagonal ±1 unitary) | `oracleMat f = Matrix.diagonal (phase ∘ f)` | Equivalent statement. |
| Projection | Π ∈ ℂ^{M×M} projection | `IsProj Pj := Pj.IsHermitian ∧ Pj * Pj = Pj` | Equivalent statement (`Π` is a reserved Lean token; code uses `Pj`). |
| Acceptance probability | p_A(h|f) = ⟨ψ_h|V†O_fΠO_fV|ψ_h⟩ (§3) | `pA V Pj f h := Re(cinner (V*ᵥψ_h) (O_f*ᵥ(Pj*ᵥ(O_f*ᵥ(V*ᵥψ_h)))))` | The quadratic form is real because it is Hermitian; taking Re is only for type convenience. |
| Distinguishing advantage | Δ_A(R) = max_f [E_k p_A(R_k|f) − E_h p_A(h|f)] (single-query form of Def. 3.13) | `adv V Pj R` (maximum via `Finset.sup'`) | Equivalent statement. |
| Decoupled advantage | ΔDecup(R,R′|f) := E_k ⟨ψ_{R_k}|V†O_fΠO_fV|ψ_{R′_k}⟩ (Def. 4.2) | `decAdv V Pj R R' f : ℂ` | Complex-valued; the lemmas use its complex norm `‖·‖`, see Deviation 1. |
| Weight vector | |wt_V⟩ = Σ_i √wt_i |i⟩ (Def. 4.5) | `wtVec V` | Equivalent statement. |
| Rescaling matrix | D_{V,h} = Σ_i (⟨v_i|ψ_h⟩/√wt_i)|i⟩⟨i| (Def. 4.6) | `rescale V h` | At wt_i = 0 the junk value 0 for 0/0 agrees with the true value 0; see Deviation 2. |
| Spectral relaxation | ΔSpectral = ‖E_k[D†_{V,R_k}ΠD_{V,R′_k}]‖_op (Def. 4.8) | `specRelax V Pj R R'` | Operator norm is defined as a variational supremum. |
| Operator norm | ‖A‖_op | `opNorm A := sSup {‖A·u‖ : ‖u‖ = 1}` | Equals 0 if there are no unit vectors (`sSup ∅ = 0`). |
| Width | width(R) := max_i (1/K)Σ_k |⟨v_i|ψ_{R_k}⟩|²/wt_i (included in Lemma 4.11) | `width V R := ⨆ i, ...` | Maximum is replaced by a supremum; 0 when M = 0. |
| Variance statistic | v(Z) = max{‖E[ZZ†]‖op, ‖E[Z†Z]‖op} (Theorem 4.10) | `vStat C = max (opNorm (Σ C C†)) (opNorm (Σ C†C))` | Expectation is precomputed using independence; see Deviation 4. |
| Sub-exponential | Pr[|X|>t] ≤ 2·exp(−t/γ) (Def. 4.12) | `SubExp X γ` | Finite uniform sample-space version. |

## 3. Deviation record (all six items)

1. **Complex norm for decAdv:** ΔDecup in Definition 4.2 is complex-valued (a cross quadratic form between two different phase states, not necessarily real), while Lemmas 4.3 and 4.9 compare real numbers. The next-to-last line of the proof of Lemma 4.3 explicitly includes absolute values (“≤ 4·E E max |E_k[⟨ψ_{S+}|W|ψ_{S−}⟩]|”), but the final line drops them. The package follows the proof: c2 and c3 use `‖decAdv ...‖` in their statements (the complex norm). This is a minor imprecision in the paper’s statement layer, corrected according to its proof and recorded here.
2. **Positive-weight premise:** wt_i = 0 iff row i of V is all zero; then ⟨v_i|ψ_h⟩ ≡ 0, so assigning 0/0 the junk value 0 in the rescaling matrix agrees with its true value (c3 needs no extra premise, and V·ψ_h = D·wtVec holds for every row). However, E[D†D] = Id (Equation (30) in the c5 proof) needs wt_i > 0, and c6 as used in c7 needs a_x = v_{i,x}/√⟨v_i|v_i⟩ to be defined. The paper implicitly excludes zero rows (they can be removed from V without changing anything). The package explicitly adds `∀ i, 0 < wt V i` to c5, c7, and c8 as a “necessary premise packaged as an assumption.” Satisfiability: with M = N and V = I, all premises hold.
3. **Dimension premise `1 ≤ d1 + d2` in c4:** when d1 = d2 = 0, the tail bound is false as written (at t = 0, the event on the left has probability 1, while the coefficient d1+d2 on the right is 0). The paper implicitly assumes positive matrix dimension (consistent with the definition of v(Z) and Tropp’s original theorem requiring d1+d2 ≥ 2). The weaker `1 ≤ d1+d2` suffices: when one side has dimension zero, opNorm is 0 and vStat is 0, so both halves hold (at t = 0 the right side is d1+d2 ≥ 1).
4. **Precomputing vStat:** the paper defines v(Z) = max{‖E[ZZ†]‖op, ‖E[Z†Z]‖op}. Independent mean-zero Rademacher variables give E[ZZ†] = Σ_k C_kC_k† and E[Z†Z] = Σ_k C_k†C_k (cross terms vanish); the package defines it directly using the latter sums. This is equality, not a weakening. When vStat = 0, Lean’s x/0 = 0 junk value makes the tail bound’s −t²/0 equal 0, so exp(0) = 1 and the right side d1+d2 bounds the probability. This holds but is looser than the paper’s limiting interpretation (that case is equivalent to all C_k = 0 and is degenerate); see retranslation adjudication 4.
5. **`1 ≤ M` in the main theorem:** the paper’s proof says “because M ≥ 2.” When M = 1, ln M = 0 and E[adv] = 0 exactly (the isometry forces N = 1, so pA is independent of h and f and adv ≡ 0; for any V with M = 1, E[adv] = 0 as well). Thus the package uses 1 ≤ M, covering M = 1 beyond the paper’s stated range, where the result still holds. When N = 0, the premise `∀ i, 0 < wt V i` is unsatisfiable (wt ≡ 0), so the statement is vacuously true; this is a known degenerate case, not a weakening.
6. **Scope selection:** the main theorem is Theorem 4.17 (expectation bound), not Theorem 4.18 (tail-bound upgrade); the latter requires the Lipschitz/Talagrand chain in Section 3 (Lemmas 3.18–3.26), the game layer excluded from scope. Theorem 4.17 is a separately numbered endpoint theorem in Section 4 and is the main theorem for this mathematical core.

## 4. Main-theorem assembly check (c8 follows from c2+c3+c5+c7, checked step by step against the proof of Theorem 4.17)

The paper’s proof has two branches. For M ≤ e^K:

1. E_R[adv] ≤ 4·E_{R,R′} max_f ‖decAdv(R,R′,f)‖ — apply c2 (premise hPj follows from IsProj in c8).
2. max_f ‖decAdv‖ ≤ specRelax — apply c3 pointwise for each R,R′ (premise hV follows from c8), then take expectations.
3. E_{R′}[specRelax(R,R′)] ≤ √(2 ln(2M)·width(R)/K) — apply c5 for each R (premises hK, hPj, hw follow from c8).
4. E_R √(2 ln(2M)·width(R)/K) ≤ √(2 ln(2M)·E_R[width(R)]/K) — Jensen’s inequality (√ is concave).
5. E_R[width(R)] ≤ C_w — expectation branch of c7 (branch condition M ≤ e^K; hK and hw follow from c8).
6. ln(2M) ≤ 2 ln M (M ≥ 2); handle M = 1 separately (adv ≡ 0, see Deviation 5). Combined constant: 4·√(2·2·C_w).

For M > e^K: adv ≤ 1 (since pA ∈ [0,1]: O_f·Pj·O_f is a subprojection acting on the unit vector Vψ_h; ‖Vψ_h‖ = ‖ψ_h‖ = 1 follows from hV and N ≥ 1, with N = 0 already excluded by hw), and 1 ≤ √(ln M/K) (M > e^K implies ln M > K). Combine constants: C := max{4·√(4·C_w), 1}. The quantifier shape agrees with the paper (∃ absolute C, ∀ parameters). Premise check: c8’s premises (1 ≤ M, 1 ≤ K, isometry, projection, positive weights) cover every premise needed at each point where a checkpoint is applied (c2 uses hPj; c3 uses hV; c5 uses hK, hPj, hw; c7 uses hK, hw)—passes item 3 of self-check 6.5.

## 5. Premise-by-premise check for each checkpoint (including degenerate parameters)

- **c1** (no premises): the proof uses only E[h(x)h(y)] = δ_xy and does not need isometry, so the package omits an isometry premise (a strengthening). At N = 0 both sides are 0 (empty sum and the junk value for 1/0 are consistent), so the proposition still holds. Compared with the original: E_h‖⟨v_i|ψ_h⟩‖² = wt_{V,i}, quantified over all V and i. ✔
- **c2** (premises 1 ≤ K and Pj Hermitian): Lemma 4.3 has no explicit premise (the game setup assumes K ≥ 1, Π is a projection, and V is an isometry). The proof uses only that Pj is Hermitian (so W is Hermitian); neither projection idempotence nor isometry of V is needed, so omitting isometry is a strengthening. K = 0 is excluded (the paper assumes K nonempty). For M = 0, adv = 0 and decAdv = 0, so 0 ≤ 0. ✔
- **c3** (premise V†V = I): Lemma 4.9 has no explicit premise (the game setup assumes V is an isometry). The proof needs Σ_i wt_i = 1 (from isometry and a trace argument), making O_f·wtVec a unit vector. At N = 0, the isometry premise can hold while Σ wt = 0, but then u = 0 and both sides are 0, so the statement still holds. At K = 0, both sides are 0. ✔
- **c4** (premises 1 ≤ d1+d2 and finite, decidably-equal ι): see Deviation 3; decidable equality for ι is needed by the `Pi.fintype` instance and has no paper counterpart (finite sets are implicit in the paper), so this is recorded as an implementation-level premise. If ι is empty, Z ≡ 0 and the expectation bound 0 ≤ 0 holds; for the tail bound at t = 0, 1 ≤ d1+d2. ✔
- **c5** (premises 1 ≤ K, IsProj Pj, and ∀ i, 0 < wt_i): these are implicit in the paper’s Lemma 4.11. When M = 0, specRelax = 0 (no unit vectors), width = 0 (empty supremum), ln 0 = 0, so 0 ≤ 0. ✔
- **c6** (premises Σ‖a_i‖² = 1 and ∃ absolute γ ≥ 1): when m = 0, the premise is unsatisfiable (the empty sum is 0 ≠ 1), so the statement holds vacuously. Lemmas 4.13/4.19 in the paper are represented verbatim. ✔
- **c7** (premises 1 ≤ K, ∀ i, 0 < wt_i, ∃ absolute c > 0, and ∃ absolute C ≥ 1): the constant c/γ² in the paper’s Lemma 4.15 is absorbed into the existential c, as stated; the M ≤ e^K condition in Lemma 4.16 is the same branch condition. For M = 0, width ≡ 0, the tail-bound left side is 0, and the expectation branch is 0 ≤ C. ✔
- **c8:** see the assembly check in Section 4 and Deviation 5. ✔

## 6. Self-check for common errors under rule 6.5

1. **Are existential outputs constrained?** The main theorem and c6/c7 existentially quantify only scalar constants (C, γ, c); there is no constructed object or degenerate-value loophole. ✔
2. **Degenerate parameters:** N = 0 (c1 remains consistent; c5/c7/c8 are vacuous through hw; c2/c3 hold trivially); M = 0 (c2/c3/c5/c7 hold; c8 excludes M = 0 but M = 1 was checked exactly, adv ≡ 0); K = 0 (excluded by hK in c2/c5/c7/c8; c3 holds); d1+d2 = 0 (excluded by hd in c4, shown necessary); m = 0 (c6 vacuous); t = 0 (tail-bound right side in c4 is at least 1; the c7 tail event is width ≥ 1 and is nondegenerate). Individual calculations are in small-examples.md E9. ✔
3. **Are the main-theorem premises at least as strong as the premises required where each checkpoint is applied?** See the final paragraph of Section 4; each use was checked individually. ✔
4. **Are substitution and evaluation points consistent?** The 1/√wt_i diagonal factor in the rescaling matrix, the (1/K)Σ_k average in spectral relaxation, and the (1/K)Σ_k average in width were checked against Defs. 4.6/4.8 and Lemma 4.11. The c6 substitution in c7, a_x = v_{i,x}/√⟨v_i|v_i⟩, matches the opening paragraph of §4.4, which gives Σ_x ‖a_x‖² = 1. This task has no upstream unproved draft source. ✔
5. **Base cases:** no induction or recursive statement. ✔
6. **Two-sided bounds and boundary cases:** the c6 sub-exponential predicate includes absolute value (|X| > t), matching Def. 4.12; c7’s tail event is one-sided (width ≥ 1+t), matching Lemma 4.15 (whose proof uses two-sided Bernstein and then takes one side). The terms min{t², t}, coefficient 2M, and threshold e^K are unchanged. ✔
7. **Weakening and vacuity:** c4 adds 1 ≤ d1+d2, and c5/c7/c8 add positive weights; these are all satisfiable explicit forms of assumptions implicit in the paper. Each conclusion has the same form as the paper (no relaxed constants, removed quantifiers, or missing conclusion branch; scope selection is a separate main theorem, not a weakening; see Deviation 6). The premises are jointly satisfiable (for example, M = N, V = I, Pj = I). ✔
