# Independent Retranslation Cross-Check: Planar Multiflows and the Cactus Gap

This record independently re-translates eight checkpoints and the core definitions from arXiv 2507.06576v3, then checks them against the finalized Lean statements. The authoring subagent did both passes at different times: it first finalized Lean, then retranscribed the statements from the PDF text and arXiv HTML and compared them. This is a limitation; the two passes were not done by separate agents.

## Mathematical restatement from the second pass

Conventions: G = (V,E) is a finite undirected simple graph; d = d_G; F_t(G) = {F ⊆ E : every component C of G∖F satisfies ∀u,v ∈ C, d_G(u,v) < t}; rad_F(r) = max{d_G(r,v) : v is in the component of r in G∖F}; F^k_{2w}(G,r) = {F ∈ F_{2w}(G) : rad_F(r) < k}; SDD(G,2w,p) is a distribution y on F_{2w}(G) with ∀e: Σ_{F∋e} y_F ≤ p; SDD(G,2w,p,r) is an SDD(G,2w,p) supported on F^w_{2w}(G,r).

- **T3 + Observation 1 (Corollary 1):** For a tree T, any root r, and w ≥ 1, there is an SDD(T,2w,1/w) distribution y such that Σ_{rad<w} y = 1 and, for every k ∈ [1,w], Σ_{rad<k} y ≥ 1 − (w−k)/w.
- **Lemma 2 (Definition 5):** If H ≤ G is a subgraph and x is an SDD(G,2w,p), then y_F := Σ_{F′: F′∩E(H)=F} x_{F′} is an SDD(H,2w,p). Second-pass note: if component diameter is measured using distances in each graph itself, this requires F′∩E(H) ∈ F_{2w}(H), i.e. d_H < 2w inside components of H. From G one only obtains d_G < 2w, while d_H ≥ d_G, so this does not hold without an extra condition. See adjudication D1.
- **T4:** If a graph family is closed under 1-sums and acceptable, then for every (G,r) there is an SDD(G,2w,p) distribution y with Σ_{F^w_{2w}(G,r)} y = 1.
- **T5:** If a graph family is closed under 1-sums, contains K2, and is strongly acceptable, then for every (G,r) and k ∈ {1,…,w}, there is an SDD(G,2w,p,r) distribution y with Σ_{F^k} y ≥ 1 − p(w−k).
- **Lemma 3:** Let P be a shortest path of length w from r to r′, and let y be an SDD(G,2w,p,r). Then (i) for every F ∈ F^w_{2w}(G,r), F∩E(P) ≠ ∅; and (ii) Σ_{F∈F^w, |F∩E(P)|≥2} y_F ≤ wp − 1.
- **Definition 6 + equations (8) and (15):** R^k = inf_{(G,r): G∈𝒢} max_{y: SDD(G,2w,p,r)} Σ_{F^k} y_F; (8) gives 1−(w−k)p ≤ R ≤ kp; (15) says there is an (H′,r′) with max < R + ε.
- **T7 (specialized to l=2):** If a graph family is closed under 1-sums, contains K2, and is strongly acceptable, then for a base graph (G,r), attachment vertices u₁,u₂, and attached graphs (G₁,r₁),(G₂,r₂), there is an SDD(GS,2w,p,r) distribution y with Σ_{F^k(GS,r)} y ≥ R and each projection y(Gᵢ) is an SDD(Gᵢ,2w,p,rᵢ).
- **T8 + Corollary 2:** If the cactus family is strongly acceptable, then (∀ε>0: wp ≥ 8/7 − 4ε/7) ⟹ wp ≥ 8/7. Here w is even.

## Cross-check against the finalized Lean statements

| Retranslated item | Lean statement | Finding |
|---|---|---|
| Notation | `IsDiamDecomp` / `rootedDecomps` / `IsSDD` / `IsRootedSDD` | Match (arbitrary “junk” distances do not affect semantics: vertices within a component are necessarily reachable). |
| T3 + Observation 1 | `tree_sdd_rooted` | Match. rad<k is equivalent to rad≤k−1; k/w = 1−(w−k)/w is attained, while the source states ≥; w≥1 is made explicit. |
| Lemma 2 | `sdd_projection` (adds `hiso` to preserve distances) | **Disagreement D1**, below. |
| T4 | `acceptable_imp_strongly` (specialized to the cactus family) | Match (specialization recorded). |
| T5 | `rooted_sdd_radius_mass` | Match. The source explicitly requires an SDD(G,2w,p,r) distribution (rooted); Lean's `IsRootedSDD ∧ mass bound` follows that. |
| Lemma 3 | `shortest_path_double_cut` | Match. P is represented as a shortest walk (automatically a path); the summation domain in (ii), F^w_{2w}(G,r), is identical. |
| Definition 6 | `critR` (`sInf`∘`sSup`) + `critR_properties` | Match. The HTML version confirms the quantifier order: the infimum includes G and r; max is replaced with `sSup` (attainment is left to the proof). |
| T7 | `onesum2_rooted_sdd` (l=2) | Match (specialization recorded; the conclusion “≥ 1−(w−k)p” is covered by c6 and not repeated). |
| T8 + Corollary 2 | `cactus_sdd_gap_lower_bound` (plain acceptability + even w ≥ 2 ⟹ 8/7 ≤ wp) | Match. The source states strong acceptability for T8; the proof derives it from plain acceptability via T4 (c3). Corollary 2's ε→0 step also matches. |

## Disagreements and adjudications

- **D1 (distance convention in Lemma 2):** A note at the end of §2 says that distances between vertices in a component are measured in the larger graph. If read strictly as distances in each graph itself, Lemma 2 fails for a general subgraph: take G = K4 and H = a 4-cycle (a spanning subgraph). The empty set is a 2-decomposition of G, but its projected mass is entirely on the empty set, which is not a decomposition of H (confirmed by small example E7). However, in all uses in the paper (1-sum projections for T4/T5/T7), the subgraphs preserve distances in the larger graph through cut vertices. Adjudication: c2 adds the distance-preservation premise `hiso` (∀u v t, d_G < t → d_H < t), which exactly matches the source's use. Recorded as deviation 3 in `concept-ledger`.
- **D2 (the maximum in Definition 6):** The source writes max; the set of rooted SDDs is a compact polytope, so the maximum is attained. Lean uses `sSup` without asserting attainment; proofs of c6/c7/c8 must handle this themselves (by compactness or another argument). This does not change the truth of the statement.
- **D3 (rootedness of the distribution in T5's conclusion):** T5 says “an SDD(G,2w,p,r) distribution y = {y_F | F ∈ F_{2w}(G)}”; the notation indexes all F ∈ F_{2w}, but the qualifier makes it an SDD(G,2w,p,r) supported on F^w. Lean's `IsRootedSDD` (support plus rootedness) is equivalent; c4 follows the rooted form.
- **D4 (range of w):** §5 fixes “w ∈ ℕ,” and §6 fixes “w is an even integer.” At w=0, F_0 is always empty and no SDD exists (also for an empty graph: d(v,v)=0 is not < 0), so propositions become vacuous. The Lean layer consistently requires 1 ≤ w (c8 also adds even and ≥2), avoiding a misleading vacuous reading.
- **D5 (root-radius count in Theorem 8):** The sum in equation (16) is over F^k_{2w}(G,r), with k = w/2; A := F^k_{2w}(G,r). Lean's `radMass X w (inl r) k` matches. The correction term in A′_a, 1 − wp/2, comes from summing edge constraints over |E(Pu₁)| = k edges; small example E4 checks the arithmetic.

## Conclusion

The eight Lean checkpoints agree item by item with the second retranslation. D1–D5 have all been adjudicated and recorded; no ambiguity remains unresolved.
