# Statement Ledger: The GNRS Conjecture for Planar Graphs

This note explains the task statement for readers comparing the mathematical definitions with the Lean source. The current scoring statements are `conj` and `refuted`; proving either earns full credit.

This ledger compares the published planar version of the GNRS conjecture with the Lean statement in this task, and records the deviations and their rationale. It is intended for task authors and reviewers as one of the three fidelity records (the component-by-component ledger).

Sources: the “GNRS conjecture” Wikipedia entry (); GNRS publication records (FOCS 1999, DOI 10.1109/SFFCS.1999.814611; Combinatorica 24(2):233–269, 2004, DOI 10.1007/s00493-004-0015-x); and consistent later formulations (Filtser, arXiv:1903.02758; Krauthgamer–Lee–Rika, arXiv:1811.02685; Lee–Sidiropoulos, arXiv:0910.1409).

Shipped statement: `environment/app/Task/Basic.lean` (identical, character for character, to the scoring copy in `tests/reference/Basic.lean`).

## 1. Published statement and Lean correspondence

The planar version of the literature statement says there is a constant C < ∞ such that the shortest-path metric (V, d_G) of every finite undirected planar graph G embeds into ℓ₁ with distortion at most C. Distortion means that the distances between image points lie in [c·d, C·d], and the distortion is C/c; an isometric embedding has distortion 1. The stronger background version says every proper minor-closed graph family has an ℓ₁ embedding with bounded distortion; planar graphs are its flagship special case.

| Concept | Literature | Lean identifier in this task | Notes |
|---|---|---|---|
| Graph | Finite undirected graph, possibly with nonnegative edge weights; unweighted graphs are a special case | `G : SimpleGraph V`, with `[Fintype V] [DecidableEq V] [DecidableRel G.Adj]`; unweighted | See deviations 1 (instances) and 2 (unweighted graphs). |
| Planar graph | A graph that can be embedded in the plane | `G.IsPlanar := ¬ G.HasMinor K₅ ∧ ¬ G.HasMinor k33` (Wagner form) | See deviation 3 (definition compromise). |
| Minor | Obtained by vertex deletion, edge deletion, and edge contraction | `G.HasMinor H`, defined using branch sets | See deviation 4. |
| Shortest-path metric | On a connected graph, d_G(u,v) is the minimum number of edges in a path | `G.spDist u v` (computable definition; `spDist_eq_dist` is proved, equating it with `SimpleGraph.dist` on reachable pairs) | See deviation 5; `conj` quantifies only over connected graphs. |
| ℓ₁ space | L¹(μ); for finite metrics, a finite-dimensional space suffices | `Fin k → ℝ` with `l1Dist x y = ∑ i, |x i − y i|` | See deviation 6. |
| Embedding with distortion ≤ C | ∃φ, ∀u v: c·d ≤ ‖φu−φv‖₁ ≤ C·d, with distortion C/c | `G.EmbedsIntoL1 C := ∃ k φ, ∀ u v, d ≤ ‖φu−φv‖₁ ∧ ‖φu−φv‖₁ ≤ C·d` (normalized to be noncontracting) | See deviation 7 (equivalent conventions). |
| Conjecture | ∃C for every planar graph | Main slot `conj`: `∃ C : ℝ, ∀ G, G.Connected → G.IsPlanar → G.EmbedsIntoL1 C`; `refuted` is its negation | See deviation 8 (connectivity). |

## 2. Deviations and rationale

1. **Instance parameters.** The Lean statement quantifies with instances `[Fintype V] [DecidableEq V] [DecidableRel G.Adj]`. Any finite graph has these instances in classical logic, and the instances are proof-irrelevant, so they impose no semantic restriction. They are included to make `spDist` computable (the checkpoint can then be checked by `decide`).

2. **Unweighted graphs.** GNRS state the conjecture for graphs with nonnegative edge weights; unweighted graphs are a special case. The reverse reduction (unweighted ⇒ weighted) is standard: rational weights can be replaced by unweighted edges through subdivision, which preserves planarity; real weights can be handled by rational approximation and a normal-family argument followed by taking a limit. This reduction is well known in the literature but is not proved in Lean, and is recorded here as such. The task uses the unweighted version because mathlib has no weighted `SimpleGraph` and the unweighted version already captures the recognized core difficulty.

3. **Planarity is expressed in Wagner form (excluding K₅ and K₃,₃ minors).** Mathlib has neither a topological definition of planar graphs nor minor theory. This task defines minors using branch sets (deviation 4) and adopts Wagner's theorem (1937: “G is planar iff G has neither a K₅ nor a K₃,₃ minor,” for finite graphs) as a cited definitional compromise; the theorem is not proved in Lean. This is the task's largest compromise in its definitions and follows the task-authoring guidance.

4. **Minors are defined using branch sets.** `G.HasMinor H` means there are nonempty, pairwise disjoint, connected vertex sets in G indexed by the vertices of H, with an edge of G between the branch sets for each adjacent pair in H. This is one of the standard equivalent definitions of a graph minor (Diestel, *Graph Theory*, §1.7; the deletion/contraction operations can be converted to and from the branch-set model). The equivalence is well known but is not proved in Lean. The definition does not claim decidability; it appears only in the statements of `conj`/`refuted` and is not needed by the checkpoints.

5. **Computable distance definition `spDist`.** `spDist u v` is the minimum length of a u-to-v walk of length less than `card V`, and is 0 if there is no such walk, matching the unreachable-pair convention for `SimpleGraph.dist`. A shortest walk can be taken to be a path, and every path has length less than `card V`, so this agrees with the mathematical distance. The definition-layer theorem `spDist_eq_dist` proves equality with `SimpleGraph.dist` for reachable pairs, anchoring the definition to the literature's shortest-path metric. The computable form lets the kernel evaluate the checkpoints' numerical claims with `decide` (`native_decide` is prohibited by the lexical scan).

6. **The ℓ₁ target is finite-dimensional.** For finite metrics, embedding into ℓ₁ is equivalent to embedding into some finite-dimensional space (ℝ^k, ℓ₁): the image is supported in the cone generated by at most n(n−1)/2 cut metrics, a standard fact about the cut cone. `l1Dist` is written directly as the sum of coordinatewise absolute differences, without using `PiLp`, to avoid an extra norm-expansion layer.

7. **Distortion convention.** The literature allows two-sided scaling [c·d, C·d] and defines distortion as C/c. The task uses the noncontracting normalization (c = 1): d ≤ ‖φu−φv‖₁ ≤ C·d. The conventions are equivalent by scaling the embedding by 1/c; this is the standard normalization and agrees with common formulations in GNRS and later work.

8. **Only connected graphs are quantified over.** The literature always works with connected graphs, where the distance is finite. In mathlib, `dist` is 0 on unreachable pairs; if disconnected graphs were allowed, the noncontracting convention would make the statement false solely because of this encoding convention. Two nontrivial components would force the embedding to collapse points from distinct components, contradicting the lower bound for an edge within a component. Adding `G.Connected` restores the intended meaning and matches the literature.

## 3. Distinguishing related problems

- This task concerns ℓ₁ distortion for **unweighted planar graphs**. It is distinct from planar flow-cut problems with terminals cofacial (the Okamura–Seymour family, where the flow-cut gap is exactly 1) and directed planar quasimetric embeddings into directed ℓ₁ (arXiv:2111.07974).
- FC (`google-deepmind/formal-conjectures`) does not contain this task (a repository-tree search was made, at the filename level; a content-level search requiring authentication was not performed, a low-risk limitation).
- The strong GNRS version (all proper minor-closed graph families) is background only and is not part of `conj`, to prevent solvers from treating the stronger statement as the target.

## 4. Current bounds and source checks

Checked for task authoring.

- Best general upper bound for planar graphs: O(√log n) (Rao, SoCG 1999, DOI 10.1145/304893.304983).
- Lower bound 16/7: Kalantarzadeh–Kumar (arXiv:2507.06576, APPROX-RANDOM 2025) show that if a universal constant exists, it cannot be less than 16/7. The previous best lower bound was 2 (Lee–Raghavendra, APPROX 2007; DCG 2010, DOI 10.1007/s00454-009-9172-4).
- Special graph families with proved bounds: trees have distortion 1 (classical); series-parallel graphs and graphs of bounded circuit rank (GNRS 2004); k-outerplanar graphs (CGNRS, SIDMA 2006, DOI 10.1137/S0895480102417379); graphs of bounded pathwidth and graph families that exclude all trees (Lee–Sidiropoulos, Combinatorica 2013, arXiv:0910.1409); 2-clique-sums (Lee–Poore, SoCG 2013); and cofacial terminals embed isometrically (Okamura–Seymour 1981).
- Dual viewpoint: planar flow-cut gaps lie between 2 and O(√log k) (as summarized by Krauthgamer–Lee–Rika, arXiv:1811.02685); the flow-cut gap of K_{2,3} is strictly greater than 1 (as summarized by Chekuri–Shepherd–Weibel, arXiv:1008.2136), locating checkpoint c3 in the literature.
- The conjecture remained open as of 2026-09 (an arXiv search found no work resolving it; papers from 2024–2026 continued to cite it as open).
