# Independent Retranslation: QMA–QCMA Oracle Checkpoints

This record independently reconstructs the expected statements of eight checkpoints and the core definitions from the paper, without consulting the finalized Lean version, then compares them item by item with the final statements. Disagreements and adjudications are recorded below.

- Compared version: arXiv 2511.09551v2.

## Method

After completing the definition layer, the authoring subagent reread the source sections at a later time: §5.4, §5.5 (Theorem 5.10), §6 (Lemma 6.1 and Theorem 6.2), §7 (Definitions 7.1/7.2, Lemma 7.3, and Claims 7.5–7.8), §9 (Theorem 9.1), and §14 (Theorem 14.1 and Theorem 1.1). It first independently wrote down what each checkpoint should state based only on the source, then compared each item with the finalized statements in `environment/app/Task/Basic.lean`. A single subagent did this work. Two rounds of compilation and page-image checks separated the retranslation from the initial draft; each disagreement is recorded below.

## Checkpoint-by-checkpoint retranslation and comparison

### c1 (Definition 5.7 / Remark 5.9)

- **Retranslation:** The spectral Fourier correlation value α(S,U) = max over unit vectors ψ of ‖Π_U H^{⊗n} Π_S ψ‖²; range [0,1]; it is 0 if S or U is empty. Equivalently, it is the largest Rayleigh quotient of M = Π_S H Π_U H Π_S (for a positive semidefinite matrix, the operator norm equals the largest Rayleigh quotient).
- **Comparison:** The four parts of the finalized statement (upper bound, attainment, ≤ 1, and zero for the empty case) cover this exactly. `sfVal` is defined using `sSup`; the attainment part supplies a maximum rather than only a supremum ✓.
- Disagreement D1: none.

### c2 (Theorem 5.10)

- **Retranslation:** For every α > β, there is a quantum query algorithm (with an n-qubit witness state), using O(1/(α−β)²) queries, such that on yes instances (≥ α) some witness is accepted with probability ≥ 2/3, while on no instances (≤ β) every witness is accepted with probability ≤ 1/3.
- **Comparison:** Same form in the finalized statement; the query bound is C/(α−β)² for some constant C. The witness is an arbitrary unit-vector initial state. The oracle is given in the combined form of equation (11). Premises 1 ≤ n, 0 ≤ β, and α ≤ 1 are added as range constraints (Remark 5.9).
- **Correction:** The modeling in the previous sentence, “the witness is an arbitrary unit-vector initial state,” was incorrect. If the initial state may be any unit vector over the entire register (control bits + address bits + work bits), then for any verifier there is a “witness” with acceptance probability exactly 1, falsifying soundness. It was changed to follow Definition 5.2, with initial state `|ψ⟩ ⊗ |0…0⟩`: the witness occupies only the first `q` work qubits and all other qubits are fixed to `|0⟩` (`qmaAcceptProb`). This is what the retranslation's “n-qubit witness” was intended to mean. See Section 5 of `concept-ledger`.
- Disagreement D2: the source says “an n-qubit witness”; the finalized statement quantifies existentially over the verifier's number w of work qubits and embeds the witness in those work qubits. The semantics agree because the witness register is part of the work register. Recorded.

### c3 (Lemma 6.1)

- **Retranslation:** If (S,U) is yes (≥ 59/100), (Δ,U) is no (≤ 57/100), and w makes A accept on (S,U) with probability ≥ 2/3, then Sampler^U(w,Δ) outputs an element of S∖Δ with probability ≥ 1/(36t²). All t queries made by the sampler are to U.
- **Comparison:** The finalized version states the premises as acceptance-probability conditions (≥ 2/3 on S, ≤ 1/3 on Δ); it does not use the constants 59/100 and 57/100. This expands “the algorithm distinguishes spectral Fourier correlation” into assumptions about its behavior. The success quantity is (1/t)Σ_j P[control bit true ∧ address ∈ S∖Δ | prefix state j], the right side of equation (25).
- **Disagreement D3:** The source's “output sample” includes the step-4 output rule: if x ∈ Δ, output the first non-Δ element in lexicographic order. The finalized success event counts only measured outcomes x ∈ S∖Δ and does not model this replacement rule. Adjudication: replacement can only increase success probability (the replacement may also lie in S∖Δ), so the lower bound direction is preserved. The Lean statement uses the core event that can be defined directly. Recorded.
- **Disagreement D4:** The finalized statement adds 1 ≤ t. The source leaves this implicit: when t = 0, the algorithm cannot distinguish S from Δ, so the premise is impossible. The explicit premise also avoids an undefined 1/(36t²). Recorded.

### c4 (Theorem 6.2)

- **Retranslation:** For a strong yes instance (every (Δ,U) with |Δ| ≤ v is a no instance), there is a query-free sampler for S that produces v distinct samples with success probability ≥ 2^{−q}·(1/(36t²))^v.
- **Comparison:** Same form in the finalized statement. `cumulativeSuccessProb` is the probability of guessing the uniformly chosen witness times the product of conditional probabilities, matching equations (27a)–(27c). Premises: 1 ≤ t and q ≤ w (the witness is embedded).
- **Disagreement D5:** The finalized version states strong yes as an acceptance-probability premise (`hstrong`: ∀ Δ ⊆ S, |Δ| ≤ v, ∀ wit, acceptance ≤ 1/3), using the same parameterization as c3. c7 produces exactly this form after converting the “algorithm is correct” assumption. Recorded.

### c5 (Claim 7.5)

- **Retranslation:** A uniformly random list of ℓ elements is good except with probability at most ℓ⁶/2ⁿ. “Good” means every XOR equation with 2, 4, or 6 terms is trivial (each index occurs an even number of times).
- **Comparison:** Same form in the finalized statement, written as a counting probability. The 2-term case is written as injectivity (`toZ2 (S i) + toZ2 (S j) = 0 → i = j`), equivalent to “each index has even multiplicity” for a pair ✓.
- Disagreement D6: none.

### c6 (Claim 7.8 and equations (39), (41)–(44))

- **Retranslation:** A^S ⪯ M^S ⪯ B^S (Taylor's entrywise diagonal inequalities plus conjugation); ‖B^S[Δ]‖ ≤ (1+κ)/2 + κ|Δ|/ℓ; ‖A^S‖ ≥ 1/2 + 3κ/2 − 15κ²/4 − 5κ/ℓ.
- **Comparison:** The four parts of the finalized statement have the same form. The PSD sandwich uses the difference of the full matrices; this is equivalent to the source's principal-submatrix form A^S[Δ] ⪯ …, since restricting a positive semidefinite matrix difference to any Δ gives the principal-submatrix order.
- **Disagreement D7 (important):** The diagonal entry at y = 0: because U excludes 0, the 0-entry of M^S is 0. The Taylor lower bound on the A side is 1/2+κℓ/2−κ²ℓ²/4, which is ≤ 0 only when κℓ ≥ 1+√3. The finalized statement makes the premise 3 ≤ κℓ explicit. Claim 7.8 in the source does not discuss this case: the diagonal of A^S includes the y=0 term 1/2+κγ_0/2−κ²γ_0²/4, while 𝔼[Π_U] is 0 at y=0, so the sandwich there requires the lower bound to be ≤ 0. Adjudication: the source lemma holds in its application range (κ=1/10, ℓ ≥ 500 ⟹ κℓ ≥ 50); the task makes this premise explicit. Recorded.
- **Disagreement D8:** Translation of `inclProb`: the finalized form is 1−e^{−κγ}/2, matching equation (36) and §1.4 (“1 − ½e^{−κγ}”). The initial draft incorrectly wrote (1−e^{−κγ})/2; small example E9 caught the error, which was corrected. Recorded.

### c7 (Lemma 7.3)

- **Retranslation:** κ ∈ [0,1], ρ ≥ 0, t1 = (1+κ)/2+v/ℓ+ρ, t2 = (1+3κ)/2−15κ²/4−5κ/ℓ−ρ, and t1 < t2 imply that Strong_κ sampling is (t1,t2,v)-strong yes, except with probability ℓ⁶2^{−n} + 2ℓ²e^{−ρ²2ⁿ/(2ℓ²)}.
- **Comparison:** Same form; the finalized statement adds 1 ≤ ℓ, v ≤ ℓ, and 3 ≤ κℓ.
- **Disagreement D9:** The source omits v ≤ ℓ. If v > ℓ, strong yes is impossible because Δ = S is constrained by both branches, so the statement is vacuously true there. The finalized statement adds v ≤ ℓ to keep the nonvacuous range explicit (the paper uses v = ℓ/100). Recorded.

### c8 (Theorem 14.1 and QMA containment)

- **Retranslation:** For every constant a > 0 and every t,q ≤ a·n^a, there is n₀ such that for all n ≥ n₀ there is a pair (S*,U*) of size n on which every q-witness, t-query classical-witness algorithm errs (on the yes side, ∀w < 2/3; on the no side, ∃w > 1/3).
- **Comparison:** Same form plus the QMA side (instantiate c2 with a constant number of queries). The QMA side corresponds to the opening of the proof of Theorem 1.1: “containment follows from Theorem 5.10.”
- **Disagreement D10:** In the source theorem, ∃ n₀ follows ∀ a in the quantifier order (a threshold for each a). The finalized order is ∀ a → ∃ n₀ → ∀ n ✓, as required.
- **Disagreement D11:** The main theorem does not include the diagonalization in the final paragraph of §14 used for Theorem 1.1. Adjudication: the property-testing formulation is the technical core of the paper; the complexity-class formulation requires the definition layer for enumerating P-uniform Turing machines, which is outside this task's scope. The treatment follows the sibling task's “normal-form version.” Recorded.
- **Disagreement D12:** Exponent scope in Theorem 9.1. Page-image checks of equations (54)/(227) confirm that the second and third terms are squared together: `((vt)⁴/ℓ^{1/32})^v + e^{−5vt})²`. The initial draft followed the pdftotext output and read them as unsquared; this has been corrected. Recorded.

## Cross-check of core definitions

- `sfVal` ↔ equation (16) (squared operator-norm form) ✓; entries of `hadMat` are 2^{−n/2}(−1)^{x·y} ✓; `gamma` ↔ equation (28), (1/ℓ)(Σ(−1)^{y·s_i})² ✓; `uWeight`/`strongWeight` ↔ Definition 7.2 (exclude y=0; independent bit) ✓; `IsGoodList` ↔ “good” in the proof of Lemma 7.3 (trivial equations for k=1,2,3) ✓; `unifState` = |S⟩ (uniform superposition with coefficient 1/√ℓ) ✓; `QueryAlgorithm`/`runState` ↔ Definitions 5.1/5.2 and the alternating sequence in §6.1 (equation (18)) ✓; `acceptProb` ↔ “measure the first qubit” (control/output bit is true) ✓; `mergeOracle` ↔ equation (11) (b=0 → S, b=1 → U) ✓; `concGood` ↔ the two Rayleigh-form branches of Claim 7.7 ✓; `samplerUpperBoundProp` ↔ strong version of equation (54) (query T first, then output v guesses; end of §9.1) ✓.

## Open issues

- A single subagent performed the retranslation (there was no second independent agent); the cross-check is supported by page-image checks and executable small examples. A reviewer rereading the source should prioritize D7 (the κℓ premise) and D12 (the squared exponent).
