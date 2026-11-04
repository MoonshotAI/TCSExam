# Component crosswalk — Lean statements for the CZ25 folded RS-code list-decoding chain (Lemma 2.8, 2.10, Theorem 2.11, Lemma 2.18, Theorem 2.15, Lemma 2.19, Theorem 2.20, Corollary 2.21)

This ledger compares each paper claim with its Lean identifier and records every deviation and its reason.

The source is the full HTML of arXiv 2408.15925v3, accepted at STOC 2025. Paper numbering follows v3, the latest revision.
- Shipped statement: `environment/app/Task/Basic.lean` (namespace `FoldedRSGSB`).

## 1. Crosswalk of assessed-claim identifiers

Each row covers one assessed claim. “Dependencies” are other claims expected to be used in the Lean proof; during judging, they are isolated and injected as axioms.

| Claim | Lean name | Paper reference | Content (plain language) | Dependencies |
|---|---|---|---|---|
| c1 | `wronskian_det_ne_zero_iff_independent` | Lemma 2.8 | t polynomials of degree < k (k < q) are linearly independent iff the folded Wronskian determinant is a nonzero polynomial | None |
| c2 | `wronskian_det_basis_smul` | Lemma 2.10 | Folded Wronskian determinants for two bases of the same subspace differ by a nonzero scalar in F (well-definedness of the geometric polynomial) | None |
| c3 | `agreement_edges_supply_roots` | Theorem 2.11 | A hypergraph edge family whose members agree on their block evaluations supplies roots, with multiplicity, for the basis Wronskian determinant (divisibility form); the determinant is nonzero | c1 + c2 |
| c4 | `flat_partition_exists` | Lemma 2.18 | A vertex set containing 0 and spanning dimension ℓ ≥ 1 can be partitioned into ℓ+1 nonempty blocks so that every transversal is affinely independent | None |
| c5 | `loss_sum_le` | Theorem 2.15 | A weight condition on every proper subset implies total loss ≤ (L−ℓ)k/(s−L+1) (the premise L ≤ s was added as a repair) | c4 |
| c6 | `weight_forces_collision` | Lemma 2.19 | Total weight ≥ (m−1)k/(s−m+2) implies that two of the m message polynomials are equal (the premise m−1 ≤ s was added as a repair) | c3 + c5 |
| c7 | `frs_list_decodable_relaxed_gsb` | Theorem 2.20 (= Theorem 1.3) | Folded RS code is (L/(L+1)(1−sR/(s−L+1)), L) list-decodable (k ≤ s·n) | c6 |
| c8 | `frs_list_decodable_capacity` (main theorem) | Corollary 2.21 (= Corollary 1.4) | Folded RS code achieves list-decoding capacity with optimal list size: (1−R−ε, L) list-decodable (added premise n < q) | c7 |

Auxiliary results (not assessed claims): no separately proven helper lemmas. `mca_mono` from gg26 has no counterpart here; “shrinking the radius preserves list-decodability” and “checking c7's premises” are derived directly inside the c8 proof. Fact 2.5 of the paper (equivalence of two definitions of affine dimension) is not a separate assessed claim: this task uses the form of Fact 2.5 directly as the definition (see deviation 7).

## 2. Definition-layer crosswalk (paper ↔ task)

| Concept | Paper | Task identifier | Notes |
|---|---|---|---|
| Relative Hamming distance | Convention before §2: ∆(x,y) = |{i : xᵢ≠yᵢ}|/n | `relDist` (ℚ-valued) | Literal correspondence; word type is `Fin n → Fin s → F` (block alphabet F_q^s represented as an F-vector space) |
| List-decodability | “(ρ, L) list-decodable” in Theorem 1.3 etc. (not defined separately in the paper) | `ListDecodable C ρ L` (at most L codewords in the closed radius-ρ ball around each point, L : ℚ) | Fixed according to the paper's usage (proof of Theorem 2.20 argues by contradiction from L+1 codewords at distance ≤ ρ); using ℚ for L matches the gg26 family |
| Generator of F^× | Definition 1.2: “generator γ of F_q^×” | `IsGenerator γ`: ∀ x ≠ 0, ∃ i, γ^i = x | Literal correspondence |
| Appropriate evaluation points | Definition 1.2: the sn elements γ^i·α_j are pairwise distinct | `Appropriate γ s α`: `(ij : Fin s × Fin n) ↦ γ^i·α_j` is injective | Literal correspondence (i starts at 0) |
| Folded evaluation block | §1: block i of codeword (f(αᵢ), f(γαᵢ), …, f(γ^{s−1}αᵢ)) | `foldEval γ s f a := fun j => f.eval (γ^j * a)` | Literal correspondence |
| Folded RS code | FRS^{(s,γ)}_{n,k}(α₁..αₙ) ⊆ (F_q^s)ⁿ | `frsCode γ s α k`: image of degree-<k polynomials under the encoding linear map (Submodule) | Encoding map `frsEncodeLM` is F-linear (paper §1 convention “f ↦ C(f)”); degree < k uses mathlib's `Polynomial.degreeLT` |
| Rate | R = k/(sn) (§1 and Theorem 2.20) | Inline `(k : ℚ)/((s : ℚ)*(n : ℚ))` (c7) and `(k : ℚ)/(N : ℚ)` (c8, N = sn) | Literal correspondence |
| Affine dimension | Definition 2.2 (dimension of smallest affine hull) = Fact 2.5 (dimension of the span of differences) | `affDim S`: F-dimension of the polynomial span of all pairwise differences | Uses the form of Fact 2.5 (deviation 7); no base point needs to be chosen, and the empty set/singleton automatically has dimension 0 |
| Folded Wronskian | Definition 2.7: entry (u,v) is f_v(γ^{u−1}X) (1-indexed) | `foldedWronskian γ f`: entry (u,v) is `(f v).comp (C (γ^u) * X)` (0-indexed) | Literal correspondence (row u corresponds to source row u+1) |
| Geometric-consistency hypergraph | Definition 2.1: vertex set plus edge eᵢ = {f ∈ V : C(f)[i] = y[i]} | Not represented as a type: stated directly with `V : Finset (Polynomial F)` and `e : Fin n → Finset (Polynomial F)`. The c3 premises `he` + `hy` say “eᵢ ⊆ V and evaluations agree within a block”; c6 uses the original complete induced edge | See deviation 6 |
| Weight | Definition 2.6: wt(e) = max(|e|−1, 0), with weights summed | `wt e := ∑ i, ((e i).card − 1)` (truncated natural-number subtraction implements max) | Literal correspondence; restricted subhypergraph E\|_H is written `fun i => e i ∩ H` |
| Loss function | Definition 2.13: Loss(e) = max(0, |e|−1−dim̃(e)) | `loss e := (e.card − 1) − affDim e` (truncated natural-number subtraction implements max) | Literal correspondence |
| Geometric polynomial | Definition 2.9: monic normalization λ·det W_γ(basis) | No separate object: c3 states “determinant of any basis is nonzero ∧ divisible by ∏” | See deviation 6 (monic normalization is not used by the chain) |
| Flat | Definition 2.17 (matroid flat) | No separate definition; used internally in the c4 proof idea | A proof tool for paper Lemma 2.18, not part of the statement layer |

## 3. Statement-layer deviations (itemized, with reasons)

Reading the list: deviations 1–4 repair missing boundary conditions (without them, a proposition is false or vacuous under an empty premise; each includes a counterexample or derivation). Deviations 5–7 are choices of formulation. Each was checked against the source. All deviations are also listed, with matching numbers, in the header block comment of the guided-tier `Basic.lean`.

1. **c5 (Theorem 2.15) adds premise `L ≤ s`.** The paper does not state it. Counterexample (numerically checked in small example E7): s = 1, L = 2, ℓ = 1, k = 5, n = 1, V = {0, 1, 2} (three constant polynomials, affine dimension 1), e₁ = V. For every proper subset H with |H| ≥ 2, the restricted weight is 1 < (|H|−1)·5/(1−|H|+2) = 5, so the premise holds. But the right side of the conclusion is (L−ℓ)k/(s−L+1) = 5/0, which is 0 under Lean's division-by-zero convention; total loss = 1 ≤ 0 is false. The paper's own use (proof of Lemma 2.19) always invokes this at L = m′−1 ≤ s−1, so the repair does not affect the chain. Shipped statement adds `hLs : L ≤ s`.
2. **c6 (Lemma 2.19) adds premise `m − 1 ≤ s`.** The paper does not state it. When s < m−1, the denominator s−m+2 ≤ 0 over ℚ, so the right side is ≤ 0 and the weight premise holds for any hypergraph, while the conclusion “not pairwise distinct” is false (m = 3, s = 1; take f = 0, 1, X; small example E8). The proof needs h(t) = (t−1)k/(s−t+2) to be strictly increasing for t ≤ m (minimal-subset argument) and needs c5's call condition L′ = m′−1 ≤ s; both follow from m−1 ≤ s. The paper's application (Theorem 2.20, m = L+1, s ≥ L) has s−m+2 ≥ 1 exactly.
3. **c7 (Theorem 2.20) uses degree bound `k ≤ s * n`.** Theorem 1.3 states k ∈ [n], while Theorem 2.20 (the restatement in §2) gives no upper bound on k. The proof needs the encoding map to be injective on degree-<k polynomials: two message polynomials are equal iff their difference vanishes at the sn pairwise distinct points γ^j·αᵢ; a nonzero polynomial of degree < k has at most k−1 roots. The exact bound is k ≤ sn. The condition k ∈ [n] implies k ≤ sn when s ≥ 1, so it covers the paper's statement. Whether the claim holds for k > sn was not checked (the encoding is no longer injective and the conclusion changes meaning); this task does not cover that range.
4. **c8 (Corollary 2.21) adds premise `n < q`.** The paper omits it from Corollary 2.21; its proof invokes Theorem 2.20, which needs q > n. `Appropriate` implies n ≤ q (when s ≥ 2, sn ≤ q−1; when s = 1, distinct α give n ≤ q). The paper's proof does not cover the boundary n = q (possible only for s = 1). Shipped statement adds `hqn : n < Fintype.card F`.
5. **c1 (Lemma 2.8) is stated for any number t of polynomials.** In Definition 2.7, the paper uses the same letter s for both the folding parameter and the number of polynomials (an s×s matrix). The chain's actual use (Theorem 2.11 and its proof) forms a Wronskian from ℓ basis vectors, where ℓ ≠ s. The original GK16/GW13 lemma holds for any number of polynomials (the proof follows that number), so the shipped statement is for arbitrary t. The degenerate case k = 0 was tested: degree < 0 gives only the zero polynomial; for t ≥ 1 both sides of the iff are false, and for t = 0 both are true. Thus the proposition holds without adding k ≥ 1 (c3/c6/c7 add 1 ≤ k separately).
6. **Two formulation choices in c3 (Theorem 2.11):**
   - The edge family is stated as “eᵢ ⊆ V and polynomials in eᵢ all have the same folded evaluation on block i” (premises `he`, `hy`), weaker than the paper's complete induced edge (eᵢ = {f ∈ V : C(f)[i] = y[i]}). The paper's proof uses only within-block evaluation agreement (h_v(γ^jαᵢ) = g_v(γ^jαᵢ) − g₀(γ^jαᵢ) = 0), so it works step by step under the weaker premise. When c6 calls it, it uses the complete induced edge, which satisfies the weaker form.
   - Monic normalization of the geometric polynomial (λ ∈ F_q^× in Definition 2.9) is omitted from the statement. The conclusion requires only that the determinant be nonzero and divisible by a product of linear factors; both are invariant under multiplication by an element of F^×. c6 consumes it in the same way (more roots than the degree implies a contradiction).
7. **Affine dimension uses the form of Fact 2.5 as its definition.** Paper Definition 2.2 is “the dimension of the smallest affine hull” (with a min and an existential quantifier); Fact 2.5 proves it equals the linear dimension of the span of differences. The latter requires no choice, automatically gives dimension 0 for the empty set and a singleton, and is directly computable, so the shipped code uses it as the definition (`affDim`). Equivalence is supported by paper Fact 2.5.

Two other routine judging-side notes (same convention as gg26): `ListDecodable` takes list size in ℚ (equivalent to a natural-number threshold for integer cardinalities); `wt` and `loss` use truncated subtraction on ℕ to implement max(·, 0), literally matching the paper's max form.

## 4. Parameter check for assembling the main theorem (arithmetic from c7 to c8, checked item by item)

Reading the section: this checks step by step that the shipped main theorem follows from c7; it also contains the weight calculation inside c7. Small examples E5/E6 were checked numerically.

- Weight calculation inside c7 (Theorem 2.20): R = k/(sn) ⟹ sR = k/n; ρ = L/(L+1)·(1 − sR/(s−L+1)) ⟹ 1−ρ = 1/(L+1) + Lk/(n(L+1)(s−L+1)), hence n(1−ρ) = n/(L+1) + Lk/((L+1)(s−L+1)) ✓ (matches the lower bound on |I_i| at paper line 710). L+1 codewords give Σᵢ|Iᵢ| ≥ (L+1)·n(1−ρ) = n + Lk/(s−L+1). Double-counting gives Σⱼ|e_j| = Σᵢ|Iᵢ|, so wt ≥ Σⱼ(|e_j|−1) = Σᵢ|Iᵢ| − n ≥ Lk/(s−L+1) = (m−1)k/(s−m+2) (m = L+1) ✓.
- Premises for c7's call to c6: m = L+1 ≥ 2 ✓ (`hL`); m−1 = L ≤ s ✓ (`hLs`); 1 ≤ k ✓; k < q: k ≤ sn (`hkn`), while `Appropriate` + q > n give sn ≤ q−1 (if s ≥ 2, all γ^jαᵢ ∈ F^×; if s = 1, n ≤ q−1 follows from `hqn`) ⟹ k ≤ q−1 < q ✓.
- Two cases for c8 (the paper proof does not mention the trivial branch, but the shipped proof must handle it):
  - 1−R−ε ≤ 0: the closed ball of radius ≤ 0 contains at most y itself (relDist = 0 iff codeword = y), so the number of codewords is ≤ 1 ≤ L when L ≥ 1. If L = 0, `L > (1−R−ε)/ε` and ε > 0 imply 1−R−ε < 0; the ball is empty and 0 ≤ 0 ✓.
  - 1−R−ε > 0: L > (1−R−ε)/ε > 0 ⟹ L ≥ 1; denominator εL−(1−R−ε) > 0 ✓; s > L(L−1)R/(εL−(1−R−ε)) + L−1 ≥ L−1 ⟹ s ≥ L (strictly greater than L−1 in ℕ) ✓; k ≤ sn: k < N = sn ⟹ k ≤ sn−1 ✓; 1 ≤ n: s ∣ N and N ≥ 1 ⟹ s ≤ N ⟹ n = N/s ≥ 1 ✓; 1 ≤ s ✓ (s ∣ N, N ≥ 1).
- Check ρ > 1−R−ε in the branch 1−R−ε > 0: sR/(s−L+1) = R + R(L−1)/(s−L+1). From s−L+1 > L(L−1)R/(εL−(1−R−ε)) (strict, with positive denominator), we get R(L−1)/(s−L+1) < (εL−(1−R−ε))/L. Thus sR/(s−L+1) < R + (εL−(1−R−ε))/L, and hence ρ = L/(L+1)(1 − sR/(s−L+1)) > L/(L+1)·(1 − R − (εL−(1−R−ε))/L) = L/(L+1)·(L+1)(1−R−ε)/L = 1−R−ε ✓ (matches paper line 744). Shrinking the radius preserves list-decodability (closed-ball containment) ✓.
- Rate in the c8 conclusion: R = k/N = k/(sn) (N = sn from s ∣ N and n = N/s), matching the rate in c7 ✓.

## 5. Outstanding items

- Paper §3 (upper bound on list-recovery radius, Theorems 3.1/3.7), Appendix A (univariate multiplicity-code transfer), and Appendix B (generalization to strong-subspace design codes) are outside this task. The classical Wronskian chain in Appendix A is isomorphic to this task's definition layer and could support a later companion task.
- A footnote to Theorem 1.3 says that the average-radius version also holds; this task includes only ordinary list-decoding form.
- Truth of the claims in the boundary cases k > sn (encoding not injective) and n = q (only when s = 1) was not checked; the shipped statement excludes them by premises (deviations 3/4).
- No Lean toolchain is available locally: compilation verification using `lake build` for the three tiers was not run on this machine and remains for platform verification (evaluation runner oracle/nop round). Lean-side small examples (native_decide version) were not written; definition-layer behavior was cross-checked with a parallel Python implementation (`small-examples.md`).
