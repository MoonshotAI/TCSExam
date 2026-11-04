# small-examples — lean-multiflow-gap-planar

This record contains executable small-example checks of the fixed-layer predicates and key paper claims (second track of SOP step 6).

## Run record

All **25/25 checks passed** (`ALL SMALL EXAMPLES PASS`).

## Small-example checklist

- **E1 (literal check against Figure 1)**: 3-edge path, `F_2 = {{e1,e2},{e2},{e2,e3},{e1,e3},E}`—exactly the list in Figure 1 of the paper. The paper's `SDD(G,2,1/2)` (`y_{{e2}} = y_{{e1,e3}} = 1/2`) also satisfies the per-edge probability bound ≤ 1/2.
- **E2 (construction in Theorem 3)**: 6-edge path, w = 3, with the root at an endpoint. Partition F₀/F₁/F₂ by layer modulo w: they partition the edge set, each is a 2w-decomposition, and `rad ≤ i`. Radius-k mass is exactly k/w = 1−(w−k)/w for k = 1,2,3; each edge is cut with probability exactly 1/w.
- **E3 (gadget in Theorem 6)**: w = 4, an 8-cycle plus two attached paths of length 2. The gadget is a cactus; d(r,u) = d(u,r′) = d(r′,v) = d(v,r) = w/2; d(u′,v′) = 2w; and both r–r̃ arcs are shortest paths of length w (the condition needed for Lemma 3).
- **E4 (union-bound arithmetic, exact fractions)**: in Theorem 6, `5 − 9x/2 > 0 ⟺ x < 10/9`; in Theorem 8, `(4−2ε) − 7x/2 > 0 ⟺ x < 8/7 − 4ε/7` (the zero is exactly 8/7 − 4ε/7, including the step R ≤ wp/2). Under the gap convention α = 2wp, 8/7 corresponds to 16/7.
- **E5 (gadget in Theorem 8)**: an 8-cycle with two arbitrary cactus attachments (a triangle plus an attached path) is still a cactus; d(r,u₁) = d(r,u₂) = w/2; each attachment contains a vertex vᵢ with d(uᵢ,vᵢ) ≥ k, and the distance between v₁ and v₂ across the attachments is ≥ 2w (ingredients for the contradiction argument).
- **E6 (upper-bound witness for Definition 6)**: for a path of length k rooted at an endpoint (brute force for k = 1,2,3), every decomposition with `rad < k` is nonempty (it must cut this path). Thus the combinatorial content for the upper bound R ≤ kp holds.
- **E7 (counterexample to the isometry assumption in c2)**: for G = K4, ∅ is a 2-decomposition (diameter 1 < 2). For the generated subgraph H = a 4-cycle, ∅ is not a 2-decomposition (opposite vertices have distance 2, which is not < 2); C4 is not isometric in K4. Without the isometry assumption, Lemma 2 is false when read using each graph's own distance. This is the source of deviation 3 between the fixed layer and the c2 statement.
- **E8 (numerical check of projection)**: on an isometric generated subgraph (a path plus an isolated vertex embedded in the attached graph), the projected distribution has total mass 1, probability on each edge no greater than in the original distribution, and support on decompositions of H. These match the three conclusions of c2 one by one.

## Effects on statement design

- E7 directly determines the `hiso` assumption in c2 (deviation 3 in `concept-ledger.md`).
- E4 checks the constants in the c8 assembly calculation (8/7 and the coefficient 4ε/7).
- The remaining examples are confirmatory and did not lead to further statement changes.
