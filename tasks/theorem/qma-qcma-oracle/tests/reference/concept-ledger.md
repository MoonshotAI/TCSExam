# Component ledger — lean-qma-qcma-oracle

- **What this document contains:** A comparison of all eight tested statements with the source text, including assumptions, quantifiers, boundary conditions, and constants, plus a record of every fidelity-related difference.
- **Intended readers:** Task authors and reviewers. Reference version: arXiv 2511.09551v2.

## 0. Overview: paper structure and task decomposition

The paper's main chain is: spectral forrelation definition (§5.4) → QMA inclusion (Theorem 5.10) → resampling reduction (§6: Lemma 6.1, Theorem 6.2) → strong yes-instance distribution (§7: Definitions 7.1/7.2, Lemma 7.3, including Claims 7.5–7.8) → bosonic-compression-oracle sampling upper bound (§§8–13: Theorem 9.1) → property-testing lower-bound form (Theorem 14.1) → diagonalization to the main theorem (Theorem 1.1).

The main theorem uses the property-testing form of Theorem 14.1 plus QMA inclusion, with three explicit assumptions: `hMW : mwAmplificationProp`, `hConc : matrixConcentrationProp`, and `hUB : samplerUpperBoundProp`. The bosonic-compression-oracle component (§§8–13) is supplied through `hUB`; diagonalization (the proof of Theorem 1.1 in §14) remains outside this statement. The table lists the three assumed facts and the separately defined `traceDistanceProp`. This last proposition is not an assumption of the main theorem and must be proved if used.

| Proposition | Content | Source |
|---|---|---|
| `mwAmplificationProp` | Amplifies the gap of a quantum-evidence verifier to 2/3 versus 1/3, using O(t/(c−s)²) queries (evidence is on the first q work qubits, with the remaining qubits fixed to \|0⟩; corrected in the 2026-08-17 rework, see Section 5) | Marriott–Watrous (Annual IEEE Symposium on Foundations of Computer Science 2004 / Theory of Computing 2005), cited in the paper as [MW05] |
| `traceDistanceProp` (defined only) | Difference in pure-state projective measurement probabilities is at most the state distance (eq. (21)); no proof is supplied to the main theorem | Wilde, *Quantum Information Theory*, cited in the paper as [Wil17] |
| `matrixConcentrationProp` | Entrywise concentration of the kernel matrix (Hoeffding) + norm transfer (Gershgorin), Claims 7.6–7.7 (with positivity assumptions 0 ≤ κ and 0 ≤ ρ, added in the 2026-08-17 rework; see Section 5) | Hoeffding 1963; Gershgorin circle theorem (textbook) |
| `samplerUpperBoundProp` | Upper bound on sampling success probability, Theorem 9.1 (eq. (54), checked against the page image) | Results proved in §§8–13 of the paper (bosonic compression oracle) |

## 1. Statement-by-statement comparison

### c1 `spectral_forrelation_rayleigh` ↔ Definition 5.7 + Remark 5.9

- **Source:** `α = ‖Π_U H^{⊗n} Π_S‖²_op = max_{‖ψ⟩‖=1} ‖Π_U H^{⊗n} Π_S |ψ⟩‖²`; range [0,1]; value is 0 if either oracle set is empty (Remark 5.9).
- **Task:** `sfVal f g = opNormSq (projOracle g * hadMat n * projOracle f)`, where `opNormSq A = sSup {normSq (A *ᵥ ψ) | IsUnitVec ψ}`. The distinction between sSup and max is resolved by branch 2 (the maximum is attained).
- **Four tested branches:** (1) Rayleigh quotient for every unit vector is ≤ sfVal; (2) a unit vector attaining equality exists; (3) sfVal ≤ 1; (4) an empty oracle set gives 0 (functional form `∀ x, f x = false`).
- **Quantifiers:** ψ ranges over all unit vectors (as in the paper's maximum); branch 2 provides the existence required by “max.” The form used in §7 is the Rayleigh quotient of M^{S,U}: the pointwise identities between `inner ψ (sfMat f g *ᵥ ψ)` and `normSq (forrelMat f g *ᵥ ψ)` are proved at the definition layer (`normSq_forrelMat_eq_inner`).
- **Assumptions:** None (holds for all f and g). Degenerate case: at n = 0, `Bits 0` is a singleton and the statement remains true (not vacuously true).

### c2 `qma_verifier_exists` ↔ Theorem 5.10

- **Source:** For any α > β, there is an algorithm using O(1/(α−β)²) queries and an n-qubit quantum witness, accepting yes instances (≥ α) with probability ≥ 2/3 and accepting any witness on no instances (≤ β) with probability ≤ 1/3. Proof: the two-projective-measurement circuit accepts with probability exactly ‖Π_U H Π_S ψ‖², followed by Marriott–Watrous amplification.
- **Task:** The verifier uses the combined oracle (eq. (11)); `∃ C > 0, t ≤ C/(α−β)²`. The quantum witness is an arbitrary unit state on the first `q` work qubits, with the control qubit, address qubits, and remaining work qubits fixed to `|0⟩` (`qmaAcceptProb`, i.e. `|ψ⟩ ⊗ |0…0⟩` in Definition 5.2; corrected in the 2026-08-17 rework. The old model, which allowed any unit initial state, made the soundness branch false; see Section 5).
- **Assumptions:** `1 ≤ n` (the source explicitly has an n-qubit witness; n=0 is degenerate), `0 ≤ β`, `β < α`, `α ≤ 1` (within the spectral-forrelation value range, Remark 5.9).
- **Packaging difference:** MW amplification is a black box (`mwAmplificationProp`); the query bound is written as C·(t+1)/(c−s)² (t is the base verifier's query count). Constants 2/3 and 1/3 match the source.
- **Constant check:** Theorem 5.10 states “O(1/(α−β)²)”; the task's `C/(α−β)²` has the same form.

### c3 `hybrid_sampler_success` ↔ Lemma 6.1

- **Source:** If (S,U) is yes (≥ 59/100), (Δ,U) is no (≤ 57/100), and w accepts with probability ≥ 2/3, then `Sampler^U(w,Δ)` outputs a point in S∖Δ with probability ≥ 1/(36t²). Proof (21)–(25): the acceptance gap 1/3 is at most the trace distance, which is at most the state distance, which is at most Σ 2‖Γψ_j‖; conclude by Cauchy–Schwarz.
- **Task:** The yes/no conditions are written directly as acceptance-probability assumptions (`hyes: ≥ 2/3 on S`; `hno: ≤ 1/3 on Δ`). The spectral-forrelation constants appear only in c7/c8; this packages the same content differently, since the algorithm's completeness and soundness behavior is exactly what the 59/100 and 57/100 thresholds imply.
- **Conclusion quantity:** `(1/t)Σ_j measProb` (prefix state j, control bit true ∧ address ∈ S∖Δ) corresponds to the right side of source (25), the average query weight for a uniformly random j. The Γ projection includes control bit = true (source Γ = Σ_{x∈S∖Δ} |1,x⟩⟨1,x| ⊗ id ✓).
- The sampler's output rule (“if x ∈ Δ, output the first symbol in lexicographic order not in Δ”) is not part of the statement: it only makes the success event larger, so it does not affect the lower-bound direction (recorded in the component ledger).
- **Assumption `1 ≤ t`:** At t = 0, `1/(36t²)` is undefined; the source algorithm makes at least one query (distinguishing two oracles requires a query). This is made explicit.
- **Constant check:** (22a) gives 1/3 ≤ …; (24) and Cauchy–Schwarz give `(1/6)² ≤ t·Σ ⟹ (1/t)Σ ≥ 1/(36t²)` ✓ (numerically rechecked in small example E15).

### c4 `cumulative_sampler_success` ↔ Theorem 6.2

- **Source:** For a yes instance (S,U) such that (Δ,U) is no for every Δ with |Δ| ≤ v, `CumulativeSampler` outputs v distinct points with probability ≥ `2^{−q}·(1/(36t²))^v`; proof is guess the witness (2^{−q}) times the conditional chain (27a)–(27c).
- **Task:** `cumulativeSuccessProb = (1/2^q)·Σ_{wit} chainProb wit ∅ v`; the recursive `chainProb` matches the paper's iteration. Distinctness of the samples follows from the construction (each round draws from S∖Δ) ✓.
- **Assumptions:** `1 ≤ t` (as in c3), `q ≤ w` (the witness is embedded in the work qubits). The Δ bound in hstrong is ≤ v, as in the source; before round k, `|Δ| = k ≤ v−1`, used in the induction ✓.
- **Quantifiers:** hstrong ranges over every wit (soundness direction) ✓, matching the source definition of a no instance; hyes asserts an existing wit (completeness direction) ✓.

### c5 `random_multiset_good` ↔ Claim 7.5

- **Source:** Except with probability ℓ⁶/2ⁿ, a random list of ℓ elements is good (for k=1,2,3, the only solutions to the 2k-term XOR equations are trivial). Proof: there are at most `C(ℓ,2)+C(ℓ,4)+C(ℓ,6) ≤ ℓ⁶` nontrivial equations, each holds with probability exactly 2^{−n}, and apply the union bound.
- **Task:** “Good” is expressed by `IsGoodList` (for 2 terms: the injective condition `i≠j ⟹ S_i≠S_j`; for 4/6 terms: if the sum is zero, every index has even multiplicity), matching the source's “trivial = every index occurs an even number of times” word for word (checked against the page image).
- **Statement form:** Number of bad lists / 2^{nℓ} ≤ ℓ⁶/2ⁿ (explicit probability for a uniformly random list).
- **Degenerate cases:** For ℓ = 0, the left side is 0 ≤ 0 ✓; for ℓ = 1 there are no nontrivial equations ✓.

### c6 `expected_matrix_bounds` ↔ Claim 7.8 + eqs. (39), (41)–(44)

- **Source:** A^S[Δ] ⪯ M^S[Δ] ⪯ B^S[Δ] (for arbitrary Δ, including the full space); `‖B^S[Δ]‖ ≤ (1+κ)/2 + κ|Δ|/ℓ`; `‖A^S‖ ≥ 1/2 + 3κ/2 − 15κ²/4 − 5κ/ℓ`.
- **Task: four branches:** two PSD-difference statements (full-matrix form, stronger than the principal-submatrix form, obtained by conjugating with the diagonal-entry inequality and consistent with the source derivation); Rayleigh upper bound for B (unit vectors supported on Δ); and |S⟩-Rayleigh lower bound for A.
- **Key discrepancy:** the y = 0 term. U excludes 0 (Definition 7.2), so the 0 diagonal entry of M^S is 0. At this point, the value of A is `1/2+κℓ/2−κ²ℓ²/4`, which is ≤ 0 when κℓ ≥ 1+√3. The task explicitly assumes `3 ≤ κℓ` (the paper's “in particular” regime κ=1/10, ℓ ≥ 500 gives κℓ ≥ 50). Claim 7.8 in the source does not explicitly discuss this point (the definition of A^S includes the Taylor value at y=0); the note “trivially holds” in Lemma 7.3 covers the small-parameter regime. This explicit condition is recorded here.
- eq. (41): diagonal entry of A is `1/2+κ/2−3κ²/4+κ²/(2ℓ)` (checked against the page image: count 3ℓ²−2ℓ); eq. (42): off-diagonal entry `κ/ℓ−3κ²/ℓ+4κ²/ℓ²` (count 12ℓ−16); eq. (43): `A^S = [1/2+κ(1/2−1/ℓ)+κ²(−3/4+7/(2ℓ)−4/ℓ²)]id_S + [κ−3κ²+4κ²/ℓ]|S⟩⟨S|`; the weakening from (44b) to (44c) requires κ ≤ 1 and 1 ≤ ℓ (difference `(κ/ℓ)(4+15κ/2−4κ/ℓ) ≥ 0`); both are assumptions.
- Taylor inequality (eq. (35)): `1/2+κx/2−κ²x²/4 ≤ 1−e^{−κx}/2 ≤ 1/2+κx/2` (x ≥ 0) — checked by numerical scan in small example E12 ✓.
- **Error caught by the small example (fixed):** the initial version of `inclProb` incorrectly used `(1−e^{−κγ})/2`; the correct expression is `1−e^{−κγ}/2` (consistent with eq. (36) and §1.4). The PSD sandwich in E9 failed at γ=0 under the incorrect expression (difference −1/2) and passes after correction.

### c7 `strong_yes_whp` ↔ Lemma 7.3

- **Source:** For κ ∈ [0,1], ρ ≥ 0, and t1 < t2 (eq. (30)), Strong_κ sampling is a (t1,t2,v)-strong yes instance except with probability `ℓ⁶2^{−n} + 2ℓ²e^{−ρ²2ⁿ/(2ℓ²)}`. Since 2026-08-17, the packaged `matrixConcentrationProp` includes assumptions `0 ≤ κ`, `0 ≤ ρ` (these were missing before the rework; see Section 5).
- **Task:** Same form; adds `1 ≤ ℓ`, `v ≤ ℓ`, and `3 ≤ κℓ` (see c6). In the source, v ≤ ℓ is implicit: for v > ℓ, no strong yes instance can exist (`Δ = S` would have to satisfy both ≥ t2 and ≤ t1 < t2), making the statement vacuously true in this region. Adding v ≤ ℓ keeps the statement non-vacuous; the paper uses v = ℓ/100.
- `t1 = (1+κ)/2 + v/ℓ + ρ`, `t2 = (1+3κ)/2 − 15κ²/4 − 5κ/ℓ − ρ` (checked against page image eq. (30a)/(30b) ✓).
- The strong-yes definition has two branches: completeness `t2 ≤ sfVal` (on the support), and soundness `∀ Δ ⊆ support, |Δ| ≤ v ⟹ sfVal ≤ t1` ✓, matching Definition 7.1.
- Proof assembly: c5 (good list) + packaged concentration (Claims 7.6–7.7) + c6 (sandwich) + c1 (Rayleigh-form conversion). For Δ = ∅, c1's fourth branch directly gives 0 ≤ t1.

### c8 `qma_qcma_oracle_separation` ↔ Theorem 14.1 + QMA inclusion

- **Source Theorem 14.1:** For t(n), q(n) ≤ a·n^a, there is n₀ such that for n ≥ n₀ every classical-witness algorithm with witnesses of length q and t queries has an instance it misclassifies (two branches: (S*,U*) ≥ 59/100 but every w is accepted with probability < 2/3, or (S*,U*) ≤ 57/100 but some w is accepted with probability > 1/3). Proof: ℓ = 2^{n/10}, v = 1000q; Theorem 6.2 + Lemma 7.3 + Theorem 9.1 yield a contradiction.
- **Task:** Same two branches plus the QMA side (there exists a constant-query verifier, by specializing c2 to α=59/100, β=57/100). Resource bounds `t ≤ a·n^a`, `q ≤ a·n^a` (inequalities over ℕ) match the source.
- **Discrepancy 1 (diagonalization):** The enumeration of Turing machines and length-gap construction in Theorem 1.1 are not packaged. The main theorem uses the property-testing form; the paper says in §14, “This is technically not yet an oracle separation between QCMA and QMA,” i.e. Theorem 14.1 is the technical core, and diagonalization is the standard final step.
- **Discrepancy 2 (choice of ρ):** The printed formula in the source “in particular” paragraph is `ρ = (2ℓ²/2ⁿ)·ln(2ⁿ/(2ℓ⁴))` (checked against the page image, with no square root), which is incompatible with its constraint equation `2ℓ²exp(−ρ²2ⁿ/(2ℓ²)) = ℓ⁶2^{−n}`. The task follows the equation and uses `ρ = √(2ℓ²·2^{−n}·ln(2^{n+1}/ℓ⁴))`.
- **Discrepancy 3 (rounding):** `ℓ = 2^{n/10}` is implemented as `2^{⌊n/10⌋}`.
- **Explicit packaged assumptions:** `samplerUpperBoundProp` assumes `4 ∣ v` (v in Theorem 13.12 is divisible by 4), `n ≤ T` (a WLOG assumption in the proof), `2cT^13 ≤ ℓ^{1/10}` (Corollary 13.11 has R ≤ ℓ^{1/10}/2 and R = cT^13), and `n₀ ≤ n` (“suitably large n”). In the c8 proof, v = 1000q is divisible by 4 ✓, and T = max(vt, n) ensures T ≥ n (the added phase gate changes only phase, not measurement statistics; this follows from the definition-layer property that `measProb` is invariant under phase gates).
- **Asymptotic calculation** (part of the c8 proof): Lower bound `(1−2ℓ⁶2^{−n})·2^{−q}(36t²)^{−1000q} ≈ 2^{−O(q log n)}`; upper-bound terms are approximately `2^{1000q(O(log n)−n/5)} + 2^{2000q(O(log n)−n/320)} + e^{−10T}`. For v = 1000q and sufficiently large n, the lower bound exceeds the upper bound. Small example E13 confirms a crossing point for a ∈ {1,2} (first n = 59280 for a=1; first n = 113200 for a=2).

## 2. Check of main-theorem assembly (the 11 steps in the c8 proof)

1. **QMA side:** Apply c2 with α = 59/100 and β = 57/100 (α−β = 1/50, `(α−β)² = 1/2500`) to obtain a constant-query verifier; assumptions `0 ≤ 57/100 < 59/100 ≤ 1` ✓.
2. **Contradiction on the QCMA side:** Assume the algorithm is correct on every instance (yes completeness + no soundness).
3. Instantiate c7 with κ = 1/10, v = ℓ/100 (= `2^{⌊n/10⌋}/100`, at least 1000q for sufficiently large n), and ρ from discrepancy 2: with probability at least `1 − 2ℓ⁶2^{−n} > 0` the instance is strong yes (57/100, 59/100, ℓ/100). Check the thresholds: `t1 = 0.55 + 0.01 + ρ ≤ 0.57 ⟺ ρ ≤ 0.01`; `t2 = 0.6125 − 0.5/ℓ − ρ ≥ 0.59 ⟺ ρ + 0.5/ℓ ≤ 0.0225`; ℓ ≥ 500 and ρ ≤ 0.01 for sufficiently large n (ρ → 0) ✓ (small example E14).
4. The algorithm is correct on every strong yes instance, so c4 applies (hstrong uses v = 1000q ≤ ℓ/100 ✓) and gives the sampling lower bound.
5. Strong average success is at least `(1−2ℓ⁶2^{−n})·2^{−q}(36t²)^{−1000q}`.
6. Convert the combined-oracle algorithm to a single-oracle algorithm (absorb U into the unitary; handled in §6.1; decompose the combined gate into a fixed diagonal gate × an S phase gate).
7. Check assumptions for the packaged result: `4 ∣ 1000q` ✓; T = max(1000qt, n) ≥ n ✓; `2cT^13 ≤ ℓ^{1/10} = 2^{⌊n/10⌋/10}`. Since `T ≤ 1000a²n^{2a}+n`, the left side is approximately `2c(1000a²)^13 n^{26a}`, while the right side is exponential, so the condition holds for sufficiently large n ✓.
8. Substitute ℓ, v, and T into the three upper-bound terms.
9. Asymptotic comparison (upper bound < average lower bound) ⟹ contradiction.
10. Therefore some instance is misclassified: either yes completeness fails (first branch) or no soundness fails (second branch).
11. Choose n₀ as the maximum of the thresholds for all assumptions (a function of c and a); the QMA side has no threshold requirement.

## 3. Record of the systematic error checks in Section 6.5

1. **Constraints on existential witnesses:** The c8 existential instance has a misclassification condition (two branches); the c2 existential verifier has acceptance-probability conditions; the c1 existential ψ has an equality condition. Degenerate case: for c8 with an empty pair (S,U), both branches are false (sfVal = 0 does not satisfy ≥ 59/100; the ≤ 57/100 branch still requires some wit accepted with probability > 1/3 and does not hold automatically) ✓.
2. **Degenerate parameters:** n=0 (singleton space, statement holds); ℓ=0 (c5 holds; c6/c7 require 1 ≤ ℓ); t=0 (c3/c4 require 1 ≤ t); v=0 (c4: the right side `2^{−q} ≤ cumulativeSuccessProb = 2^{−q}·Σ_wit 1·…… = 1 ≥ 2^{−q}` ✓; c7 includes v ≤ ℓ ✓); q=0 (`2^0 = 1`, unique witness) ✓.
3. **Synchronized assumptions:** The hstrong bound in c8's use of c4, v = 1000q ≤ ℓ/100, matches c7's v ✓. The c6 premises used by c7 (1 ≤ ℓ, 0 ≤ κ ≤ 1, 3 ≤ κℓ) hold for κ=1/10 and ℓ ≥ 500 ✓. The c3 hyes/hno conditions follow inside c8 from the assumption that the algorithm is correct ✓.
4. **Evaluation points:** The `1/ℓ` factor in γ_y (eq. (28) ✓, checked against page image); U excludes y=0 (Definition 7.2 ✓); `inclProb = 1−e^{−κγ}/2` (transcription error caught by the small example and fixed); κ = 1/10; 59/100 and 57/100 (Remark 5.9 and start of §6 ✓).
5. **Base conditions:** `1 ≤ t`, `1 ≤ ℓ`, `3 ≤ κℓ`, `4 ∣ v`, `n ≤ T`, `2cT^13 ≤ ℓ^{1/10}` are all explicit.
6. **Two-sided conditions and boundaries:** c6 sandwich is two-sided ✓; c7 strong yes has both branches ✓; c8 misclassification has both branches ✓; the strong-yes condition `|Δ| ≤ v` includes equality, as in the source.
7. **Weakening and vacuity:** c3 is more general than Lemma 6.1 (it does not fix the constants 59/100), which is parameterization rather than weakening. The QMA side of c8 has constant query bound `tQ ≤ C` (O(1/(α−β)²) is a constant when α−β=1/50) ✓. c7 adds v ≤ ℓ to avoid vacuity ✓.
8. **Notation/macro ban in the writable region:** As in the rest of the repository, this has not been implemented (the sibling-task convention is retained).
9. **Consistency between task statement and grader:** The grading description in `instruction` was checked sentence by sentence against `score.py` (lexical scanning first strips comments ✓; the task currently says “rejected by a lexical scan” without mentioning comment stripping, as in sibling tasks. The grader behavior matches the sibling tasks and the same wording is retained).
## 5. Rework record

**Trigger:** A 5163 pre-check showed an inverted result: full score on the bare tier, 1/8 on the guided tier, and 0 on the ladder tier. Review (`review-qma-qcma-inversion-2026-08-17.md`) confirmed that the bare-tier full score was a vacuity exploit and that the task had two defects. This section records the corrections.

**Defect A (packaged assumption was false):** The old `matrixConcentrationProp` quantified κ and ρ over all real numbers without positivity assumptions. Counterexample (machine-verified under the formulation without this condition): n = 0, ℓ = 1, S ≡ 0, ρ = −2. The first branch of `concGood` fails; the bad-event weight on the left is at least 1 while the right side is `2e^{−2} < 1`, so the assumption is false. The main theorem and c7 could therefore be proved by ex falso, causing the vacuity exploit. **Correction:** Add `0 ≤ κ → 0 ≤ ρ →` after the proposition's quantifiers, matching the source of Lemma 7.3 (“κ ∈ [0,1] and ρ ≥ 0”) and the nonnegative-deviation setting of Hoeffding in Claims 7.6–7.7. The c6/c7 use sites already had assumptions `0 ≤ κ`, `0 ≤ ρ`, so their invocation forms are unchanged. Also, when κ < 0, `inclProb` falls outside [0,1] and `uWeight` is no longer a probability weight, so positivity of κ is required as well.

**Defect B (quantum-witness model made soundness always false):** The old QMA-side witness was any unit initial state on the entire `QReg n w` (control qubit + address qubits + work qubits). For any verifier, choosing an initial state equal to the inverse of the total unitary applied to an accepting basis state makes the acceptance probability exactly 1 (agents on the two tiers machine-verified `exists_acceptProb_one` / `qma_part_false`). Thus soundness did not hold for every verifier; the soundness branch of c2 and the QMA branch of the main theorem were false, while `mwAmplificationProp` was provable under the same degenerate quantification (there was no vacuity exploit channel; this was a genuinely false statement). **Correction:** Tighten the model in the standard way following Definition 5.2: the witness occupies only the first `q` work qubits, with the control qubit, address qubits, and remaining work qubits fixed to `|0⟩`. Add the definition-layer objects `qmaInit` (initial state with qubits fixed to zero), `isUnitVec_qmaInit` (unit norm), `qmaAcceptProb` (acceptance probability wrapper), and embedding helpers `embedWit_injective`, `restr_embedWit`. Replace the “arbitrary unit initial state” quantification in `mwAmplificationProp`, c2, and the QMA branch of the main theorem with this wrapper. The QCMA side (c3, c4, the QCMA branch of the main theorem, and all sampling probabilities) already used a `classicInit` basis-state embedding and is unaffected. The arbitrary-initial-state quantification in `samplerUpperBoundProp` is a sampling upper bound (averaged over all (S,g)); the vacuity construction does not apply to it, so it was left unchanged.

**Choice of packaging shape:** The review report sketched a wrapper where the entire work register is the witness (`ψ : Bits w → ℂ`). The final version instead uses “witness on the first q qubits + zero on the rest” (explicit `q ≤ w`). Reason: the output verifier after standard Marriott–Watrous amplification has zero-initialized auxiliary qubits while preserving the witness size. If the entire work register is quantified as the witness, the adversary controls the verifier's auxiliary qubits after amplification, and the soundness branch is no longer a standard MW guarantee. With the prefix form, the amplification statement matches the literature: q witness qubits are arbitrary, and the verifier fixes its auxiliary qubits to zero.

**Semantic check after the fix:** Defect A's counterexample no longer contradicts the new statement because ρ = −2 does not satisfy the assumption. After fixing defect B, the soundness branch of c2 is no longer always false: for the base verifier (the two-projective-measurement circuit of Theorem 5.10, w = q = n), any witness ψ is accepted with probability exactly `‖Π_g H^{⊗n} Π_f ψ‖² ≤ sfVal f g ≤ β` on a no instance, for all ψ. The genuine proof route from the paper is restored.

## 4. Follow-up items

- The diagonalization in Theorem 1.1 is not packaged (the main theorem uses the property-testing form); a complexity-class version would require a definition layer for P-uniform circuit families.
- The paper is version 2 from 2026-01-17; check again if a later version appears.

## Statement requirements

- **What this records:** Repairs for two source-reference leaks found during final verification (`qma-bare-cert-260916`).
- **Finding:** Two source section numbers remained in model-visible headings: `## Quantum query algorithms (Definitions 5.1-5.2)` and `## The Strong distribution (Definitions 7.1-7.2)` (leaked in all three tiers). The 2026-09-07 neutralization rework (854d96c) said all source numbers had been replaced with neutral references, but these two headings were missed; the source-reference gate in `check.py` caught them.
- **Fix:** Removed the number parentheticals from both headings (`## Quantum query algorithms`, `## The Strong distribution`) and synchronized all three tiers' environment/app and tests/reference copies. This was a comment-only change; the statement and code regions were untouched, and app==ref remains byte-for-byte identical.
- **Verification:** The source-reference gate passed after the repair (the other two gates also passed: app==ref and code-region difference from old HEAD equals the repaired comment lines; all three gates passed against the new HEAD after commit). C/D/G sandbox items were rerun during final verification; see `qma-bare-cert-260916.md` for the record.
