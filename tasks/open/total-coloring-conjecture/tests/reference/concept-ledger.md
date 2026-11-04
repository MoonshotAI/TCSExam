# Faithfulness Review: The Total Coloring Conjecture

This note explains the task statement for readers comparing the mathematical definitions with the Lean source. The current scoring statements are `conj` and `refuted`; proving either earns full credit.

This document compares the literature statement of the Total Coloring Conjecture with the Lean statement used by this task, recording every modeling choice and its rationale.

- Sources: Behzad’s 1965 PhD dissertation (Michigan State University); independently proposed by Vizing in 1968. Open Problem Garden also lists it.
- Released statement: environment/app/Task/Basic.lean; it matches tests/reference/Basic.lean word for word.

## 1. Literature statement and Lean correspondence

The standard statement is that every finite simple graph G satisfies χ″(G)≤Δ(G)+2. The total chromatic number χ″(G) is the minimum number of colors needed to color both vertices and edges so that adjacent vertices, adjacent edges, and each vertex and its incident edges all receive distinct colors. Δ(G) is the maximum degree. The complete-graph and complete-bipartite cases are known: χ″(Kₙ)=n for odd n and n+1 for even n; χ″(Kₙ,ₙ)=n+2 (Behzad–Chartrand–Cooper 1967).

| Concept | Literature | Lean identifier in this task | Notes |
|---|---|---|---|
| Graph | Finite undirected simple graph. | G : SimpleGraph V, with [Fintype V] [DecidableEq V] [DecidableRel G.Adj]. | SimpleGraph already means a simple undirected graph; Fintype gives finiteness. |
| Adjacent vertices | Joined by an edge. | G.Adj (existing mathlib definition). | |
| Edge | Unordered pair of vertices. | e : Sym2 V; graph edges are G.edgeFinset : Finset (Sym2 V) (existing mathlib API). | |
| Adjacent edges | Distinct edges sharing an endpoint. | EdgesAdj e₁ e₂ := e₁ ≠ e₂ ∧ ∃ v, v ∈ e₁ ∧ v ∈ e₂. | Endpoint relation uses Sym2 membership; see deviation 1. |
| Incident edge and vertex | Vertex v is an endpoint of edge e. | v ∈ e (decidable Sym2 membership in mathlib). | |
| Total coloring | Color vertices and edges simultaneously under the three compatibility rules. | G.IsTotalColoring c f: vertex colors c : V → Fin k; edge colors f : G.edgeFinset → Fin k; adjacent vertices, adjacent edges, and incident vertex-edge pairs must differ in color. | See deviations 2 and 3. |
| k-total-colorable | There is a total coloring using at most k colors. | G.TotalColorable k := ∃ c f, G.IsTotalColoring c f. | Color names do not matter; Fin k is standard. See deviation 3. |
| χ″(G) | Minimum number of colors. | G.totalChromaticNumber: Nat.find of the least k admitting a coloring. | Existence follows from totalColorable_add_card; not directly kernel-computable. See deviation 4. |
| Δ(G) | Maximum degree. | G.maxDegree (mathlib): maximum vertex degree, with 0 for the empty graph. | No deviation. |
| Conjecture | χ″(G)≤Δ(G)+2 for every finite graph. | G.TotalColorBound := G.totalChromaticNumber ≤ G.maxDegree+2; main slot conj quantifies over all finite graphs and refuted is its negation. | |

## 2. Deviations and rationale

1. **Represent edges as Sym2 V, unordered pairs, and use Sym2 membership for endpoints.** In a simple graph, edges correspond one-to-one with unordered vertex pairs. mathlib already provides edgeFinset/Sym2.Mem and decidable membership. “Adjacent edges” as distinct edges sharing an endpoint is the standard definition, translated directly by EdgesAdj.

2. **Assign edge colors only to actual edges of G (functions on the subtype ↥G.edgeFinset); nonedges have no color.** Only edges of G participate in the literature definition. This reduces the finite enumeration from k^|Sym2 V| to k^(|V|+|E|), making kernel decide feasible for small-graph checkpoints. On K_{2,2}, the search has about 4^4 × 4^4 ≈ 65,000 assignments and took 17 seconds; see small-examples.md.

3. **Use Fin k for the color set.** “At most k colors” is equivalent to coloring with Fin k, since color names can be relabeled. k-colorability is monotone in k (TotalColorable.mono, proved).

4. **Define χ″ using Nat.find, so it is noncomputable for direct kernel evaluation.** Numeric checkpoint claims χ″=m are proved through two definition-layer facts: TotalColorable m and ¬TotalColorable (m−1), each checked by an independent kernel decide theorem with its own heartbeat budget. They are combined using totalChromaticNumber_le (upper bound), le_totalChromaticNumber (lower bound), and TotalColorable.mono (monotonicity). This matches χ″=min{k | k-total-colorable}, and the minimum is attained (totalColorable_totalChromaticNumber).

5. **Use |E|+|V| colors as an existence bound.** Give every vertex and every edge a distinct color, using disjoint color ranges; totalColorable_add_card proves this. The literature’s observation that every finite graph has a total coloring is the same argument. It only ensures the minimum exists and does not occur in any slot statement.

6. **The refuted slot is the literal negation of the literature statement.** ¬∀G, TotalColorBound G is classically equivalent to the existence of a finite graph G with χ″(G)>Δ(G)+2. The counterexample graph is unconstrained and chosen by the model.

7. **Construct the starK13 and k22 example graphs using explicit adjacency on Fin 4.** This avoids extra graph constructors in mathlib and keeps the definition layer small. K₂,₂ is the 4-cycle C₄; the statement uses the complete-bipartite notation, consistent with the family χ″(Kₙ,ₙ)=n+2.

## 3. Distinction from nearby problems

- FC (google-deepmind/formal-conjectures) does not include this conjecture; the survey searched the full repository for “total coloring” and found no match.
- Vizing’s theorem concerns edge chromatic number χ′∈{Δ,Δ+1}; this problem colors vertices and edges together and is a natural next question.
- Behzad’s conjecture, the total coloring conjecture, and the Total Coloring Conjecture (TCC) are names for the same conjecture.
- This is an open structural decision statement: either a proof for every graph or a machine-checkable counterexample would resolve it. Its form differs from parameter-search tasks in the conjecture dataset.

## 4. Known frontier

- General bound χ″(G)≤Δ(G) + 10^26 (Molloy–Reed 1998); asymptotic bound Δ+poly(log Δ) (Hind–Molloy–Reed 1998).
- Proved special cases: complete graphs, complete multipartite graphs, graphs with Δ≤3, and planar graphs with Δ≥7 (Sanders–Zhao 1999; the Δ=6 case remains open).
- Papers in Journal of Combinatorial Theory B (2023) and EJC (2024) still treat the conjecture as open, in work relating the weak total-coloring conjecture to Hadwiger’s conjecture. The general case remains unresolved.
