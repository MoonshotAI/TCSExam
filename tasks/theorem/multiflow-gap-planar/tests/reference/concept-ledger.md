# concept-ledger — lean-multiflow-gap-planar

- **What this document contains:** A component-by-component comparison of eight tested statements and the fixed layer with the source (arXiv 2507.06576v3), recording all discrepancies and checking the main-theorem assembly.
- **Intended readers:** Task authors and reviewers; use with `small-examples.md` (executable small examples) and `retranslation.md` (independent retranslation).

## 0. Fixed-layer comparison

| Fixed-layer definition | Source object | Comparison |
|---|---|---|
| `IsDiamDecomp G F t` | §2: `F` is a t-diameter decomposition iff `diam(F) < t` (every pair of vertices in each connected component of `G∖F` has G-distance < t) | Consistent. Distance uses `G.dist` (shortest path; junk value 0 if unreachable, but two points within a component are reachable, so junk does not enter the semantics). The source's final note says “measure distance within the large graph”; read it as distance in the graph at hand; see discrepancy 3. |
| `decomps G t` | §2: `F_t(G)` | Consistent (`G.edgeFinset.powerset` filtered; `F ⊆ E(G)` is guaranteed by construction). |
| `RootedRadLt G F r k` | §§2/5: `rad_F(r) < k` (each point in r's component is at G-distance < k from r) | Consistent. |
| `rootedDecomps G w r k` | §5: `F^k_{2w}(G, r) = {F ∈ F_{2w}(G) : rad_F(r) < k}` | Consistent. |
| `IsSDD G w p y` | Definition 2: `SDD(G, 2w, p)` is a probability distribution on `F_{2w}(G)`, with each edge cut with probability ≤ p | Consistent. y is a total function with a support constraint, matching the source's “distribution defined only on `F_{2w}(G)`”; total mass 1 is summed over `decomps`; `edge_le` is the per-edge ≤ p condition. |
| `IsRootedSDD G w p r y` | §5: `SDD(G, 2w, p, r)` (supported on `F^w_{2w}(G, r)`) | Consistent (the support and rooted conditions together are equivalent to support on `F^w_{2w}(G,r)`; the source has the equivalent form `Σ_{F^w} y_F = 1`). |
| `IsCactus G` | §2: every edge belongs to at most one cycle | Consistent (written as: two cycles sharing an edge have the same edge set). |
| `CactusAcceptable / CactusStronglyAcceptable` | §5: G is SDD(2w,p)-acceptable / strongly acceptable | Consistent, with the graph family specialized to cacti (discrepancy 2); arbitrary finite vertex types are allowed (equivalent to Fin n, not listed as a separate discrepancy). |
| `radMass / radGuarantee / critR` | Definition 6: `R^k = inf_{G,r} max_{y} Σ_{F^k} y_F` | Consistent: sInf (over rooted finite cacti) ∘ sSup (radius-k mass of rooted SDDs). Difference between max and sSup: see discrepancy 4. |
| `projDist H G w y` | Definition 5: projected distribution | Consistent (generated subgraph H, with the same vertex type). |
| `Sum2V / Sum2Adj / sum2Graph` | Definitions 4/7: 1-sum / generalized 1-sum (two attachments) | Consistent: vertex set = base-graph vertices ⊕ nonroot vertices of attachment 1 ⊕ nonroot vertices of attachment 2; seven adjacency cases (base graph, two root attachments × two directions, and interiors of the two attachments). |
| `sum2Emb / sum2EdgeEmb / sum2Proj` | Embedding in Definition 7 and projection in Definition 5 | Consistent (roots map to attachment vertices; edge embedding via `Sym2.map`; injectivity proved). |

## 1. Discrepancy register (also listed at the top of the task statements)

1. **The LP side is excluded:** Theorem 1 (Carr–Vempala), the multicut LP, and Theorem 2 (gap ⇔ existence of SDD) are not formalized; the main theorem is a pure SDD statement. The “16/7 gap lower bound” is included only as an interpretation via Theorem 2: if the gap is ≤ α, then `SDD(2w, α/2w)` is acceptable; the main theorem gives `8/7 ≤ w·(α/2w) = α/2`, hence α ≥ 16/7.
2. **Specialize the graph family to cacti:** The source's Theorems 4/5/7/8 are stated for arbitrary graph families closed under minors, decompositions, and 1-sums and containing K2. The paper actually uses only the cactus family. Closure of cacti under 1-sums and membership of K2 are proof content for each tested statement (proof: every cycle in a 1-sum lies in one summand—crossing summands would require passing through the cut vertex twice; hence a 1-sum of cacti is still a cactus).
3. **Distance convention and c2's isometry assumption:** Decompositions/radii use each graph's own `dist`. With this reading, Lemma 2 fails for general subgraphs—counterexample (confirmed in small example E7): G = K4 (diameter 1, ∅ is a 2-decomposition), H = a 4-cycle spanning subgraph of G. Projection maps all mass on ∅ to the non-decomposition ∅ in H (opposite vertices have distance 2, not < 2). All uses in the source (1-sum projections in Theorems 4/5/7) are isometric subgraphs (by the cut-vertex argument), so c2 adds assumption `hiso`, exactly matching the source's use.
4. **Use sInf/sSup for R:** Definition 6 writes inf/max in the source. Attainment of the maximum (compactness) is not asserted and belongs to proof content; the empty-set sSup = 0 convention does not apply under the strong-acceptability assumption. Both inequalities in equation (8) and the approximate extremal witness in (15) are packaged in c6.
5. **Specialize Theorem 7 to two attachments:** The source handles l attachments; the only use in the paper is Theorem 8 with l = 2. The general-l proof is the same argument (pigeonhole choice of ⌈m/l⌉).
6. **Do not make Theorem 6 (20/9) a separate tested statement:** Its cycle + pair-of-paths construction is a warm-up for Theorem 8, and its conclusion is strictly subsumed by c8. The explicit construction in §8 (including multicut cost) is excluded as outside the pure-SDD line.
7. **Make parameter ranges explicit:** `1 ≤ w`, `0 < p < 1`, `1 ≤ k ≤ w` (the source fixes w,p at the start of §5 and takes k ∈ {1,…,w}; when w=0, `F_0` is always empty and no SDD exists, so every claim is vacuously true but has no content); c8 adds `Even w` and `2 ≤ w` (the source fixes an even w at the start of §6, with k = w/2).
8. **The distribution in Theorem 5's conclusion is a rooted SDD:** The source concludes “there exists an SDD(G,2w,p,r) y with `Σ_{F^k} y_F ≥ 1−p(w−k)`”—both rooted strength (support on `F^w`) and the radius-k mass lower bound hold. c4 follows this (`IsRootedSDD ∧ 1−(w−k)p ≤ radMass`).

## 2. Statement-by-statement comparison

### c1 `tree_sdd_rooted` ⟷ Theorem 3 + Observation 1 (Corollary 1)

- **Source Theorem 3:** For a tree T and any w ∈ ℕ, there is an `SDD(T, 2w, 1/w)`. Observation 1 adds two properties of the constructed decomposition: (1) `rad_{F_i}(r) ≤ w−1` almost surely for any root r chosen in advance; (2) the probability of `rad ≤ k−1` is k/w ≥ `1 − (w−k)/w`, for k = 1..w. Corollary 1 packages both.
- **Task:** `G.IsTree` (mathlib: connected and acyclic) + `1 ≤ w` + arbitrary root r; conclusion: `IsRootedSDD G w (1/w) r y` (including support on rad < w) ∧ for every k ∈ [1,w], `1 − (w−k)·(1/w) ≤ radMass k`.
- **Item-by-item:** Range of w (source says ℕ, w=0 is meaningless, so use 1 ≤ w ✓); root arbitrary ✓ (source Corollary 1: “Let r be an arbitrary root”); radius-k mass bound ✓ (k/w = 1−(w−k)/w exactly, while the source states ≥); p = 1/w ✓. Empty graph / singleton: `IsTree` includes connectedness; singleton tree with ∅ decomposition and radius 0 ✓, so it holds.

### c2 `sdd_projection` ⟷ Lemma 2 + Definition 5

- **Source:** If x is an SDD(G,2w,p) and H is a subgraph, then the projection y is an SDD(H,2w,p).
- **Task:** H and G have the same vertex type (spanning subgraph), `H ≤ G` + isometry assumption `hiso`. Projection follows Definition 5 (for `F ∈ F_{2w}(H)`, `y_F = Σ_{F'∩E(H)=F} x_{F'}`).
- **Item-by-item:** Support (F'∩E(H) is a decomposition of H) follows by `hiso` ✓; the source uses ambient-graph distances directly, so this holds as written there. Total mass and edge_le agree by expanding definitions. Added isometry assumption is recorded in discrepancy 3. The source has no range assumptions on w/p, and neither does this task.

### c3 `acceptable_imp_strongly` ⟷ Theorem 4

- **Source:** If G is closed under 1-sums and is SDD(2w,p)-acceptable, then for every G ∈ G and every root r there is an `SDD(G,2w,p,r)` (supported on `F^w_{2w}(G,r)`).
- **Task:** If the cactus family is acceptable, it is strongly acceptable (`CactusStronglyAcceptable` means every rooted graph has a rooted SDD).
- **Item-by-item:** Conclusion form ✓ (`IsRootedSDD` is equivalent to support on `F^w`); closure under 1-sums is proof content (discrepancy 2); 0<p<1 and 1≤w are parameter restrictions (discrepancy 7). The source proof (LP (6), optimal value 0 + averaging with m > 1/z) was checked: attainment of the LP optimum = attainability of the infimum of bad mass is a compactness argument in the proof.

### c4 `rooted_sdd_radius_mass` ⟷ Theorem 5

- **Source:** If G is 1-sum-closed, contains K2, and is strongly acceptable; for G ∈ G, root r, and k ∈ {1,…,w}, there is an `SDD(G,2w,p,r)` y such that `Σ_{F^k} y_F ≥ 1 − p(w−k)`.
- **Task:** Strongly acceptable cactus family + cactus `(G,r)` + `1≤k≤w` implies existence of a rooted SDD and `1−(w−k)·p ≤ radMass k`.
- **Item-by-item:** Both parts of the conclusion (rooted strength + mass bound) ✓ (discrepancy 8); containing K2 and closure are proof content; the form `1−p(w−k)` matches (real subtraction `(w:ℝ)−k` is nonnegative under k≤w ✓).
- **Record of a typo in the source (does not affect the statement):** In the proof of Theorem 5, “there exists an SDD(H, 2w, p, r)” should use v instead of r (the later partition of A and B uses `F^w_{2w}(H, v)` and their masses sum to 1). The guided-tier proof sketch roots the graph at v.

### c5 `shortest_path_double_cut` ⟷ Lemma 3

- **Source:** P is a shortest path of length w from r (other endpoint r′), and y is an `SDD(G,2w,p,r)`. Then (i) every F ∈ `F^w_{2w}(G,r)` intersects E(P); (ii) `Σ_{|F∩E(P)|≥2} y_F ≤ w·p − 1`.
- **Task:** `P : G.Walk r u`, `P.length = w`, `∀ Q, w ≤ Q.length` (shortest); y is a rooted SDD. Conclusion is a conjunction: (i) `∀ F ∈ rootedDecomps w r w, F ∩ P.edges.toFinset ≠ ∅`; (ii) the mass of the filter with `2 ≤ card` is ≤ `w·p − 1`.
- **Item-by-item:** (i) every source F ∈ F^w intersects P ✓ (use shortestness: d(r,u)=w; if they did not intersect, rad ≥ w); (ii) summation over `F^w_{2w}(G,r)` ✓, threshold ≥2 ✓, right side w·p−1 ✓. P need not be assumed to be a path (a shortest walk is automatically a path) ✓. For w=0, no SDD exists, so the premise is unsatisfiable and the statement is vacuously true (recorded in E checks).

### c6 `critR_properties` ⟷ Definition 6 + equation (8) + equation (15)

- **Source:** Fix k∈{1,…,w}; `R = inf_{G,r} max_y Σ_{F^k} y_F`. Equation (8): `1−(w−k)p ≤ R ≤ k·p` (left side from Theorem 5; right side from the argument that a length-k shortest path must be cut). Equation (15): choose `(H′,r′)` such that `max < R + ε`.
- **Task:** Three conjuncts: lower bound, upper bound, and for every ε>0 there is a finite rooted cactus with `radGuarantee < critR + ε`.
- **Item-by-item:** Lower bound (c4 + sInf properties) ✓; upper bound (a length-k path graph rooted at an endpoint; a tree is a cactus; any rooted SDD gives k-mass ≤ kp, because any decomposition with rad<k must cut that path—confirmed by small example E6) ✓; approximate witness is the approximation property of sInf ✓. Assumptions: strongly acceptable, 0<p<1, 1≤w, 1≤k≤w ✓.

### c7 `onesum2_rooted_sdd` ⟷ Theorem 7 (l=2)

- **Source:** If G is closed under 1-sums, contains K2, and is strongly acceptable; given a base graph G, root r, attachment vertices u₁..u_l, and attachments `(G_i, r_i)`, there is an SDD(·,2w,p,r) y on `GS(L)` with `Σ_{F^k} y_F ≥ R` (≥ `1−(w−k)p`) and each projection `y(G_i)` is an `SDD(G_i,2w,p,r_i)`.
- **Task:** l=2; base graph and both attachments are cacti. Conclusion has four conjuncts: rooted SDD at `Sum.inl r` ∧ `critR ≤ radMass` ∧ both projections are rooted SDDs.
- **Item-by-item:** `Σ ≥ R` ✓ (“≥ `1−(w−k)p`” restates the left side of equation (8), already covered by c6, so is not repeated in the conclusion); rooted strength of projections ✓ (the use in Claim 5 of Theorem 8 requires a projection that is `SDD(H′_i,2w,p,r′_i)`); l=2 specialization is discrepancy 5. The 1-sum construction is in the fixed layer (`Sum2V`/`sum2Graph`), and attachment roots map to attachment vertices ✓.

### c8 `cactus_sdd_gap_lower_bound` ⟷ Theorem 8 + Corollary 2 (main theorem)

- **Source Theorem 8:** If the cactus family is strongly SDD(2w,p)-acceptable, then `w·p ≥ 8/7 − 4ε/7` for every ε>0. Corollary 2 takes ε→0⁺ to obtain `w·p ≥ 8/7`. Starting in §6, w is a fixed even number.
- **Task:** Acceptable (plain) + even w ≥ 2 + 0<p<1 implies `8/7 ≤ w·p`. The proof derives plain→strong via c3.
- **Item-by-item:** Constant 8/7 ✓ (uses the limit version, with no ε weakening); w even ✓; w≥2 (so k=w/2≥1) ✓; direction of conclusion ✓ (acceptability implies the lower bound; nonvacuous—Theorem 2 in the reverse direction and the known upper bound show acceptability holds for sufficiently large p).

## 3. Check of main-theorem assembly (derive c8 from c3/c5/c6/c7, step by step)

1. c3: `hacc` ⟹ strongly acceptable (requires 0<p<1 and 1≤w, supplied by c8).
2. Set k := w/2 (because w is even, k is a natural number; w≥2 implies 1≤k≤w ✓, satisfying the assumptions of c4/c6/c7).
3. Assume for contradiction `w·p < 8/7`. Choose `ε := (8/7 − w·p)·7/8 > 0`, so that `w·p < 8/7 − 4ε′/7` for ε′ ≤ ε (take ε′ = ε).
4. Use the third conjunct of c6 to choose `(H′, r′)` with `radGuarantee(H′,r′) < R + ε`.
5. Build `X = C_{2w} ⊕_{u₁} H′₁ ⊕_{u₂} H′₂` (on the cycle, the distances between r,u₁,r̃,u₂ are w/2; use two copies of H′). X is a cactus (proof content: each cycle lies in one summand).
6. Apply c7 to X: obtain a rooted SDD y with `radMass_X(k) ≥ R`, and both projections are rooted SDDs on `(H′₁,r′₁)` and `(H′₂,r′₂)`.
7. Inside `A := F^k_{2w}(X,r)`, `d(r,u₁)=d(r,u₂)=k`, so every F must cut both r–uᵢ arcs (by the radius condition).
8. Apply c5 to the two r–r̃ geodesics Pa′, Pb′ (each has length w): the mass of Aa, Ab (cuts of Pa, Pb with `|F∩|≥2`) is each ≤ wp−1.
9. Claim 5 calculation: the projection to H′₁ is a rooted SDD, so its k-mass is at most `radGuarantee < R+ε`. The mass of Ac (traces in `F₁^k`) is less than `(R+ε) − (1 − wp/2)`: the part A′_a that does not cut Pu₁ (all F in that class) has mass ≥ `1 − kp = 1 − wp/2` (sum the constraints over the k edges of Pu₁). The same holds for Ad.
10. Union bound: `A* = A ∖ (Aa∪Ab∪Ac∪Ad)` has mass at least `R − [2(wp−1) + 2(R+ε−(1−wp/2))] = 4 − 2ε − 3wp − R ≥ 4 − 2ε − (7/2)wp` (using c6's `R ≤ kp = wp/2`) `> 0 ⟺ wp < 8/7 − 4ε/7` ✓ (arithmetic checked in small example E4).
11. Choose F ∈ A* with `y_F > 0`: it does not cut Pa or Pb, and radius-k fails inside both attachments, so there are vᵢ ∈ H′ᵢ in the same component as uᵢ with `d(uᵢ,vᵢ) ≥ k = w/2`. Then `d(v₁,v₂) = d(v₁,u₁)+d(u₁,u₂)+d(u₂,v₂) ≥ w/2 + w + w/2 = 2w` (the u₁–u₂ route on the r side has not been cut … more precisely, v₁, v₂, u₁, u₂ lie in the same component, and the u₁u₂ distance via the uncut r-side is w/2+w/2 = w) ⟹ contradiction, since F is a 2w-decomposition.
12. Therefore `8/7 − 4ε/7 ≤ wp` for every ε>0; taking the limit gives `8/7 ≤ wp`.

At each use site, the assumptions match those of c3/c5/c6/c7: c3's 1≤w follows from 2≤w; c5's rooted SDD comes from c7 and its shortest paths are cycle arcs; c7's k range follows from k=w/2.

## 4. Content not included

- Theorem 1, Theorem 2 (both sides of the LP), §2.1 (LP relaxation), Theorem 6 in §6 (20/9, subsumed by c8), §8 (explicit construction, including multicut cost), and §1.1 (background on demand-flow variants).
