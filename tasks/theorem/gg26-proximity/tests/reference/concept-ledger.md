# Component Crosswalk — Lean Statements for the GG26 Curve-Decodability Chain (Lemma 3.2, Theorems 3.3/3.4, Lemma 4.1, Theorems 4.7/4.8)

- What this document contains: A line-by-line crosswalk between the paper and the Lean identifiers in this task, including every deviation and its rationale.
- Intended readers: Task authors and reviewers; one of the three L2 fidelity records (component crosswalk).
- Source: Full PDF of ECCC TR25-166. IACR ePrint 2025/2054 was blocked by Cloudflare and could not be obtained. The ECCC page says “Revisions: 1”; ECCC TR25-166 is the paper’s public full-text version. Page numbers, numbering, and formulas below refer to the ECCC version.
- Packaged statements: `environment/app/Task/Basic.lean` (namespace `ProximityGaps`).

## 1. Checkpoint numbering crosswalk

Each row documents one checkpoint. “Dependencies” lists other checkpoints expected to be used in its Lean proof; the grader injects them as axioms in isolation.

| Checkpoint | Lean name | Paper reference | Informal content | Dependencies |
|---|---|---|---|---|
| c1 | `closeness_propagates_from_many_points` | Lemma 3.2 | If two word-valued curves of degree ≤ ℓ are within distance δ at at least t parameter points (t > ℓ), then they are within distance δ(1+ℓ/(t−ℓ)) everywhere; the union of coordinates where their coefficient words differ has size at most δn(1+ℓ/(t−ℓ)). | None |
| c2 | `mca_of_curve_decodable` | Theorem 3.3 | (ℓ,δ,a,t) curve decodability implies (ℓ, δ, a/|F|, ℓ/t) mutual correlated agreement. | c1 |
| c3 | `list_recovery_output_low_dimensional` | Lemma 4.1 | List recovery for a subspace-design code against coordinatewise low-dimensional subspace inputs; the output is contained in a subspace of the code of dimension < r. | None |
| c4 | `mca_of_curve_decodable_and_list_decodable` | Theorem 3.4 | Curve decodability + (δ(1+ℓ/(t₁−ℓ)), L) list decodability implies (ℓ, δ, ((t₂−1)L+a)/|F|, ℓ/t₂) mutual correlated agreement (q > (L+1)²ℓ). | c1 |
| c5 | `curve_decodable_of_subspace_design` | Theorem 4.7 | A τ-subspace-design code is (ℓ, 1−τ(r)−ε, a, a·ε/(r+ε)) curve-decodable. | c3 + packaged Theorem 4.5 |
| c6 | `mca_of_subspace_design` (main theorem) | Theorem 4.8 | Mutual correlated agreement for a τ-subspace-design code (proximity 1−τ((ℓ+1)t)−3/(2t), slack 1/m). | c4 + c5 + packaged Theorem 2.23 |

Auxiliary (not checkpoints): `mca_mono` proves monotonicity of the three MCA parameters; the main theorem uses it to absorb rounding of the list size. Lemma 2.37 of the paper (Vandermonde-vector interpolation) is not a separate checkpoint; it is an internal step in the proof of c5, with `Matrix.det_vandermonde` in mathlib as the main ingredient.

## 2. Definition-layer crosswalk (paper ↔ this task)

| Concept | Paper | Identifier in this task | Notes |
|---|---|---|---|
| Relative Hamming distance | Def. 2.1: ∆(x,y) = |{i : xᵢ≠yᵢ}|/n | `relDist` (ℚ-valued) | Direct match. |
| Curve evaluation uα | Starting in §2.1: uα = ∑ⱼ uⱼ·αʲ | `curveEval u α` (coefficient words indexed by `Fin (ℓ+1)`) | The paper uses u₀..uℓ, ℓ+1 words; Lean uses `Fin (ℓ+1) → (Fin n → V)`. |
| Code | F-additive code C ⊆ Σⁿ (Σ = F_q^s) | `C : Submodule F (Fin n → V)` | Σ is generalized to any finite-dimensional F-vector space V (the paper uses only its linear structure; `Fintype V` is needed to count lists). |
| Curve decodability | Def. 3.1 | `CurveDecodable` | **Strengthened to subsets**, see Deviation 1; thresholds a,b are in ℚ (equivalent to ℕ thresholds when cardinalities are integral). |
| Mutual correlated agreement | Def. 2.7 | `MCA` | Direct match, including the quantifier δ' ≤ δ and the ∃β condition. |
| List decoding | Condition 1 of Thm. 3.4: “(δ(1+ℓ/(t₁−ℓ)), L) list-decodable” | `ListDecodable` (at most L codewords in the δ-ball around each point, with L : ℚ) | The paper gives no explicit definition; this is fixed from its use (“more than L codewords in the ball” gives a contradiction). |
| Coordinate annihilator Cᵢ | §1.2 / Def. 4.4 | `coordKer i` (kernel of the projection map) | |
| Subspace-design property | Def. 2.17 | `IsSubspaceDesign` | Direct match: (∑ᵢ dim Aᵢ)/n ≤ (dim A)·τ(r), τ : ℕ → ℚ. |
| Distance to a product of subspaces | ∆(c, L₁×⋯×Lₙ) in Lemma 4.1 | `relDistProd` | Fraction of coordinates whose symbols do not lie in Lᵢ. |
| Pruning guarantee | Theorem 4.5 ([AHS25] randomized pruning algorithm) | `PruningGuarantee` (packaged as an assumption) | See Deviation 6 and the derivation in Section 4. |
| CZ25 list-size bound | Theorem 2.23 ([CZ25]) | `ListSizeBound` (packaged as an assumption) | External theorem, packaged directly: open ball of radius 1−τ(k)−1/k has at most (1−τ(k))·k codewords. The paper writes τ(1/ε); here k = 1/ε is a positive integer. |

## 3. Statement-level deviations (itemized, with reasons)

Deviation 1 gives the definition in the form established and used by the proof. Deviations 2–5 repair boundary conditions and typographical issues; without these repairs, the statements are false or the proofs fail. Deviation 6 packages external or randomized material. Each item was checked against the source.

1. **`CurveDecodable` is strengthened to arbitrary subsets (the largest deviation).** Definition 3.1 of the paper quantifies only over the full close set A = {α : ∆(uα, f(α)) ≤ δ}. But the proof of Theorem 3.3 applies the property to a δ'-close set (δ' ≤ δ), and the iteration in Theorem 3.4 applies it to a set after peeling, Aⱼ = A₀ ∖ (B₀∪⋯∪B_{j−1}). Neither use follows literally from the original definition, which quantifies only over “exactly the full close set”; changing f outside the set to make it far away requires a far codeword, which is not guaranteed. The proof of Theorem 4.7 actually establishes the strengthened form (its argument works step by step for any subset A satisfying the closeness premise). Packaged definition: `∀ u f A, (∀ α ∈ A, ∆(uα, f α) ≤ δ) → a ≤ |A| → ∃ c, b ≤ |{α ∈ A | f α = curve c at α}|`. Also a,b are rational thresholds: the paper uses naturals (“at least a elements”), and for integer cardinality (m : ℚ) ≥ a is equivalent to m ≥ ⌈a⌉. ℚ is used so c5’s output b = a·ε/(r+ε) matches the paper’s formula without rounding.
2. **c1 (Lemma 3.2) adds `ℓ < t`.** The paper says “for all t ∈ ℕ, … ⟹ ∆(…) ≤ δ(1 + ℓ/(t−ℓ))”. Its proof’s key step, |T|(1 − ℓ/t) ≤ δn, gives an upper bound only when 1 − ℓ/t > 0 (that is, t > ℓ). If t ≤ ℓ, the right side 1+ℓ/(t−ℓ) is negative or undefined, making the claim false (example: ℓ = t = 1, u₀=0, u₁=0, c₀=0, c₁=v≠0 on a single coordinate, T that coordinate; |T| = 1 > δ·(1+1/0)·n is undefined). The package adds `ht : ℓ < t`.
3. **c4 (Theorem 3.4) adds `t₂ ≤ 2 * t₁`.** The last paragraph of the paper’s proof says “We have (L+1) distinct degree-ℓ curves” but does not prove pairwise distinctness: curves produced in rounds i and j may have identical coefficient vectors (then both pass through f₀ on Bᵢ∪Bⱼ, and there is no contradiction). Repair: if two round curves coincide, merge their witness sets Sᵢ ⊇ Bᵢ∪Bⱼ. Since the B sets are disjoint, |Sᵢ| ≥ 2t₁; apply Lemma 3.2 at t := 2t₁ to get slack ℓ/(2t₁). To retain the paper’s target slack ℓ/t₂ requires 2t₁ ≥ t₂. The package adds `ht : t₂ ≤ 2 * t₁`. The paper’s own substitution in Theorem 4.8 (t₁ = 2ℓt, t₂ = mℓ) satisfies this when m ≤ 4t. For m > 4t, monotonicity from m = 4t does not apply (slack 1/m becomes stronger and err grows; neither direction is monotone enough to cover it), see Deviation 5. Also added `ℓ < t₁` and `ℓ < t₂` (needed at both uses of Lemma 3.2 and for the domains of the slack expressions).
4. **The lower bound on ε in c5 (Theorem 4.7) is strict: `(ℓ+1)/r < ε`.** The paper writes ε ≥ (ℓ+1)/r. At equality, the strict containment in Lemma 4.1, ∆(c, product) < 1−τ(r)−(∑ℓᵢ)/(nr), can fail: ∑ℓᵢ can reach n(ℓ+1), making the bound exactly 1−τ(r)−ε, and the candidate codeword may be only ≤ that distance. The package uses strict inequality. The substitution in Theorem 4.8, ε = 3/(2t) > 1/t = (ℓ+1)/r, has slack, so is unaffected. Also added `0 < r` (domain of ε/(r+ε)).
5. **Three repairs in c6 (Theorem 4.8, the main theorem):**
   - **Correct the err expression.** The paper prints (ℓ, 1−τ(tℓ+t)−3/(2t), t·ℓ·(m(1−τ(tℓ+t))+2t²(ℓ+1))/|F|, 1/m). Its proof combines Theorem 3.4, where err should be ((t₂−1)·L+a₀)/q. L comes from Theorem 2.23: taking k = r gives L = r(1−τ(r)); taking k = t gives L = t(1−τ(t)). Neither gives the proof’s L = t(1−τ(r)) (the first differs by a factor ℓ+1; in the second τ has a different argument, and there is no monotonicity premise on τ). Therefore, the printed err cannot be derived from 2.23+3.4+4.7. The package uses a version that composes strictly: err = t·ℓ·(ℓ+1)·(m(1−τ((ℓ+1)t))+2t²)/|F|. Use the k := r route. The first term, (mℓ−1)(ℓ+1)t(1−τ), is at most mℓ(ℓ+1)t(1−τ), using τ ≤ 1. The second term is a₀ = 2ℓt(2tr/3+1) = (4/3)ℓ(ℓ+1)t³+2ℓt, at most 2ℓ(ℓ+1)t³ when 3 ≤ (ℓ+1)t². This version is **slightly weaker** than the printed theorem (first term is ℓ+1 times larger), with the same asymptotic form; proximity and slack match the paper exactly.
   - **Range for m: 2 ≤ m ≤ 4t.** The paper says “any integers t, m, ℓ ∈ ℕ.” After the repair in Deviation 3, the composition works only when t₂ = mℓ ≤ 4ℓt = 2t₁, i.e. m ≤ 4t; m > 4t does not follow monotonically from m = 4t (Deviation 3). Also, the domain of slack 1/m and the requirement t₂ > ℓ need m ≥ 2; t₁ = 2ℓt > ℓ needs t ≥ 1; and the list-radius inequality needs ℓ ≥ 1. The package adds `ht : 1 ≤ t`, `hm : 2 ≤ m`, `hmt : m ≤ 4 * t`, `hℓ : 1 ≤ ℓ`.
   - **Field-size premise and signs of τ.** Theorem 3.4 requires q > (L+1)²ℓ, omitted from Theorem 4.8. The package adds `hq : ((r(1−τ r)+1)²·ℓ : ℚ) < |F|` (L = r(1−τ(r)), r = (ℓ+1)t). It also adds `hτr : 0 ≤ τ r` (needed for the list-radius inequality 1−τ(r)−1/r ≥ (1−τ(r)−3/(2t))·2t/(2t−1)) and `hτ1 : τ r ≤ 1` (needed to bound the first err term). The paper’s τ : N → ℝ≤1 (Def. 2.17) and the fact that for an actual code τ(r) ≥ R − 1/n > 0 (Lemma 2.18) support these premises.
6. **Two assumptions are packaged** (same treatment as HenselLift/MatchingSet in bciks20):
   - `PruningGuarantee C τ r ε`: Theorem 4.5 describes the probability of the randomized algorithm PRUNED. The package assumes its expected-average consequence: for H ≤ C (finrank ≤ r) and any finite family of point pairs (y α, c α), where c α ∈ H and ∆(y α,c α) ≤ 1−τ(r)−ε, there is a coordinate set S with H_S = {0} such that at least an ε/(r+ε) fraction of the pairs agree coordinatewise on all of S. Derivation: the algorithm in Theorem 4.5 depends only on H (the paper emphasizes “oblivious to the codeword” in §§1.2 and 4.2), so the same random S works for every pair in the family with probability Pr[cᵢ=yᵢ for all i∈S and dim H_S=0] ≥ ε/(r+ε). For indicator X(S) = 1[dim H_S=0]·(number of pairs agreeing on S), taking expectation gives E[X] ≥ |A|·ε/(r+ε); therefore some S attains this value. If a > 0, X(S)>0 implies dim H_S=0; if a = 0, take S=[n], which zeroes any H. This is exactly the form consumed in the proof of Theorem 4.7.
   - `ListSizeBound C τ`: Theorem 2.23 ([CZ25], external literature) is packaged directly.
7. **The output subspace in c3 (Lemma 4.1) is required to satisfy `H ≤ C`.** The paper says the output is “contained within a linear space of dimension less than r”; taking the span of the output list gives a subspace of C (C itself is a subspace). The proof of Theorem 4.7 needs H ≤ C (pruning requires H to be a subspace of the code). Also added `0 < r` (domain of (∑ℓᵢ)/(nr); the paper’s bound is undefined at r = 0).

## 4. Main-theorem assembly check (arithmetic for c6, checked item by item)

The packaged main theorem follows from c4, c5, and the packaged assumptions; this derivation also explains Deviation 5.

- Substitutions: r = (ℓ+1)t, t₁ = 2ℓt, t₂ = mℓ, ε = 3/(2t), δ₀ = 1−τ(r)−3/(2t), a₀ = t₁(2tr/3+1) (over ℚ).
- c5 gives (ℓ, δ₀, a₀, a₀·ε/(r+ε)) curve decodability. For hε, (ℓ+1)/r = 1/t < 3/(2t). Its output b₀ = a₀·ε/(r+ε) = t₁·(2tr/3+1)·(3/(2t))/((ℓ+1)t+3/(2t)) = t₁·(2tr+3)/(2tr+3) = t₁ (a rational identity).
- The packaged list-size bound with k := r gives list decoding at radius 1−τ(r)−1/r and list size L = r(1−τ(r)). c4 needs radius δ₀·(1+ℓ/(t₁−ℓ)) = δ₀·2t/(2t−1). The inequality 1−τ(r)−1/r ≥ (1−τ(r)−3/(2t))·2t/(2t−1) is equivalent to 3−(2t−1)/r ≥ 1−τ(r), which follows from r > 2t−1 (ℓ ≥ 1) and 1−τ(r) ≤ 1 (hτr). ✓
- Conditions for c4: t₂ ≤ 2t₁ iff m ≤ 4t (hmt); ℓ < t₁ iff 1 ≤ 2t; ℓ < t₂ iff 2 ≤ m; q > (L+1)²ℓ (hq). ✓
- c4 outputs MCA with parameters (ℓ, δ₀, ((mℓ−1)L + a₀)/q, ℓ/(mℓ)); slack ℓ/(mℓ) = 1/m, as required. ✓
- Err domination:
  [((mℓ−1)(ℓ+1)t(1−τ) + (4/3)ℓ(ℓ+1)t³ + 2ℓt)/q]
  [le (tℓ(ℓ+1)m(1−τ) + 2t³ℓ(ℓ+1))/q.]
  For the first term use (mℓ−1) ≤ mℓ and 1−τ ≥ 0 (hτ1). For the second, 2ℓt ≤ (2/3)ℓ(ℓ+1)t³ iff 3 ≤ (ℓ+1)t² (since ℓ,t ≥ 1). Then use `mca_mono` in the err direction to reach the target err. ✓
- The δ := (1−τ(r)−1/t)(1−ℓ/t₁) in the paper is not needed in the package composition: curve decodability can use δ₀ directly (its monotonicity in δ is “larger δ implies smaller δ,” and δ₀ is exactly Theorem 4.7’s output bound). In the paper’s proof the direction of “δ ≤ 1−τ(r)−3/(2t)” is reversed (in fact δ ≥ 1−τ(r)−3/(2t)); this does not affect the final statement.

## 5. Follow-up items

- The paper’s Theorem 4.8 claim for m > 4t and Corollary 4.9 (perfect MCA at m = n) are outside the packaged main theorem. Under the strict proof audit in Deviations 3/5, this is not merely a weaker choice in the packaged statement: the paper’s proof, once made rigorous, covers only m ≤ 4t. If a rigorous proof covering m > 4t is found (for example, by improving collision handling in Theorem 3.4), the main theorem can be broadened.
- The IACR ePrint 2025/2054 version was not checked (Cloudflare blocked access). It is the same paper as ECCC TR25-166 (same title, authors, and date; ECCC is the authors’ public full-text archive).
- Section 5 (random RS/random linear codes) and the folded-RS corollary (Corollary 4.10, Theorem 1.2) are out of scope. The former uses the LMS25/BCDZ25b local-property threshold theorem; the latter uses the GK16 subspace-design theorem for FRS. Both exceed the self-contained definition layer.
