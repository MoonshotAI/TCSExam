# Faithfulness Review: Tuza’s Conjecture

This note explains the task statement for readers comparing the mathematical definitions with the Lean source. The current scoring statements are `conj` and `refuted`; proving either earns full credit.

This document compares the literature statement of Tuza’s conjecture with the Lean statement used by this proof-oriented open-problem task.

- **Original source:** Tuza 1981, in Finite and Infinite Sets, Proceedings of the Colloquium on Mathematical Society János Bolyai 37, North-Holland 1984, p. 888.
- **Released statement:** environment/app/Task/Basic.lean; it matches tests/reference/Basic.lean word for word.

## 1. Literature statement and Lean correspondence

For any finite graph G, let ν(G) be the largest number of pairwise edge-disjoint triangles (triangle edge-packing number), and let τ(G) be the minimum size of an edge set meeting every triangle (triangle edge-cover number). Tuza’s conjecture is τ(G)≤2·ν(G). If true, the constant 2 is tight: graphs whose blocks are all K₄ attain equality.

| Concept | Literature | Lean identifier in this task | Notes |
|---|---|---|---|
| Graph | Finite undirected simple graph. | G : SimpleGraph V with [Fintype V] [DecidableEq V] [DecidableRel G.Adj]. | SimpleGraph already means simple undirected; Fintype gives finiteness. |
| Triangle | A triangle (K₃ subgraph) of G. | G.triangleFinset := G.cliqueFinset 3 (vertex triples). | See deviation 1. |
| Triangle edges | The three edges of a triangle. | triangleEdges s := s.sym2.filter (¬ ·.IsDiag). | For a 3-clique this is exactly its three edges; checked in small example E5. |
| Cover | An edge set intersecting every triangle. | G.IsTriangleCover F := F⊆G.edgeFinset ∧ ∀s∈G.triangleFinset, ¬Disjoint (triangleEdges s) F. | See deviation 2. |
| τ(G) | Minimum cover size. | G.triangleCoverNumber, the Finset.min′ of cover cardinalities. | Candidates are subsets of the edge set; the full edge set is a cover (proved), so the minimum exists. |
| Packing | A family of pairwise edge-disjoint triangles. | G.IsTrianglePacking T := T⊆G.triangleFinset ∧ ∀s≠t∈T, Disjoint (triangleEdges s) (triangleEdges t). | Shared vertices are allowed, as required by “edge-disjoint.” |
| ν(G) | Maximum packing size. | G.trianglePackingNumber, the Finset.max′ of packing cardinalities. | The empty family is always a candidate (proved), so a maximum exists. |
| Conjecture | τ(G)≤2·ν(G) for every finite graph. | G.TuzaBound := G.triangleCoverNumber≤2*G.trianglePackingNumber; conj universally quantifies over finite graphs, refuted is its negation. | |
| Tightness | Equality for a block chain of K₄s. | Finite example: τ=2 and ν=1 for K₄. | Smallest tight example. |

## 2. Deviations and rationale

1. **Represent a triangle by its vertex triple (a 3-clique), not as a subgraph.** In the literature a triangle is a K₃ subgraph; in a simple graph it is uniquely determined by its three vertices, and the cover and packing definitions use only its three edges. triangleEdges maps the triple back to those edges, so both numbers agree pointwise with the literature. mathlib’s cliqueFinset is directly available and decidable, avoiding wrappers for subgraph existence.

2. **Restrict cover candidates to edges of G.** The literature defines a cover as a subset of G’s edges whose removal leaves no triangle, and this task makes F⊆G.edgeFinset explicit. Every edge of each triangle is an edge of G (proved by triangleEdges_subset_edgeFinset); allowing nonedges as candidate “edges” would not produce a smaller cover, so τ is unchanged.

3. **Define τ and ν by filtering power sets and taking Finset.min′/max′, making them computable.** This lets the kernel check numerical claims for small graphs (c1 and c3) directly with decide; native_decide is forbidden by the lexical scan, but kernel decide is permitted. The finite definitions are exponential and intended only for small instances. General proofs use the proved API lemmas triangleCoverNumber_le, le_triangleCoverNumber, le_trianglePackingNumber, trianglePackingNumber_le, and the two attainment lemmas.

4. **The refuted slot is the literal negation of the literature statement.** ¬∀G, TuzaBound G is classically equivalent to the existence of a finite graph G with τ(G)>2·ν(G). The model chooses the counterexample.

5. **Construct twoTriangles using explicit adjacency on Fin 6.** Vertices within each block are adjacent, giving the disjoint union of two vertex-disjoint K₃s. No mathlib graph constructor is introduced, keeping the definition layer small.

## 3. Distinction from nearby problems

- FC (google-deepmind/formal-conjectures) includes ErdosProblems/621, a different inequality about triangle cover and packing (4(a+t)≤n²). It is related but not this conjecture, as checked in the survey.
- This is an open structural decision statement: either a proof for every graph or a machine-checkable counterexample would resolve it. It differs from parameter-search tasks in the conjecture dataset.

## 4. Known frontier

- Best general-graph constant: 66/23≈2.87 (Haxell 1999); the trivial upper bound is 3·ν.
- The conjecture holds asymptotically for dense graphs (Baron–Kahn 2016), and for restricted classes including planar graphs and graphs with maximum degree at most 6 (degree at most 7 is under review).
- Work from 2024–2026 still treats the original conjecture as open: new bounds for generalized Tuza (arXiv:2406.06501), a binary-matroid extension, a maximum-degree-7 special case (arXiv:2608.06538), and a random-geometric-graph version (arXiv:2606.09736).
