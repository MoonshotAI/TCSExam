# Faithfulness Review: Ryser’s Conjecture

This note explains the task statement for readers comparing the mathematical definitions with the Lean source. The current scoring statements are `conj` and `refuted`; proving either earns full credit.

This document compares the literature statement of Ryser’s conjecture with the Lean statement used by this task and records all modeling choices.

- **Standard reference:** DeBiasio–Kamel–McCourt–Sheats, “Generalizations and strengthenings of Ryser’s conjecture,” Electronic Journal of Combinatorics, 2021.
- **Released statement:** environment/app/Task/Basic.lean; it matches tests/reference/Basic.lean word for word.

## 1. Literature statement and Lean correspondence

For every integer r≥2 and every r-partite r-uniform hypergraph H (the vertex set is partitioned into r parts, and every edge contains exactly one vertex from each part), the cover number τ(H), the minimum size of a vertex set meeting every edge, and the matching number ν(H), the maximum number of pairwise disjoint edges, satisfy τ(H)≤(r−1)·ν(H). For r=2 this is Kőnig’s theorem; r=3 was proved by Aharoni in 2001; the conjecture remains open for r≥4 (explicitly stated by DeBiasio–Girão–Haxell–Stein 2024). The constant r−1 is tight when a truncated projective plane exists (for order r−1 a prime power): it is an intersecting hypergraph with τ=r−1.

| Concept | Literature | Lean identifier in this task | Notes |
|---|---|---|---|
| r-partite r-uniform hypergraph | Finite hypergraph with r vertex parts, each edge containing one vertex from each part. | RPartiteHypergraph r V, with edges : Finset (Fin r→V). | See deviations 1 and 2. |
| Vertex | A vertex in one part. | (i,v) : Fin r×V, vertex v in part i. | Different parts are disjoint by construction. |
| Edge | One vertex from every part. | e : Fin r→V, where e i is the vertex in part i. | See deviation 2. |
| Cover | Vertex set meeting every edge. | H.IsCover C := ∀e∈H.edges, ∃i:Fin r, (i,e i)∈C. | |
| τ(H) | Minimum cover size. | H.coverNumber, the Finset.min′ of the cardinalities of all covers. | Candidates are subsets of the vertex set; the full vertex set is always a cover when r≥1, so a minimum exists. |
| Matching | Pairwise disjoint family of edges. | H.IsMatching M := M⊆H.edges ∧ ∀e≠e′∈M, ∀i, e i≠e′ i. | “Disjoint” means different in every part; vertices have part labels, so two edges share a vertex exactly when they agree in some part. |
| ν(H) | Maximum matching size. | H.matchingNumber, the Finset.max′ of the cardinalities of all matchings. | The empty family is always a matching, so a maximum exists. |
| Conjecture | τ(H)≤(r−1)·ν(H) for every r≥2 and every r-partite r-uniform H. | H.RyserBound := H.coverNumber≤(r−1)*H.matchingNumber; conj universally quantifies r≥2, V, and H, and refuted is its negation. | |
| Tightness | Equality for truncated projective planes. | Checkpoints c2 (truncated Fano plane, r=3) and c3 (truncated PG(2,3), r=4). | The first two smallest members of the truncated-projective-plane family. |

## 2. Deviations and rationale

1. **Represent the r parts by r disjoint copies of one type V.** The literature allows parts of different sizes. Take V to be the disjoint union of the parts; every literature instance is isomorphic to an RPartiteHypergraph r V, with edges corresponding pointwise, and conversely each such structure is literally an r-partite r-uniform hypergraph (part i is {(i,v):v∈V}). τ and ν are invariant under isomorphism, so the universal conjectures have the same truth value. This encoding is chosen because vertices are Fin r×V and edges are functions Fin r→V, avoiding Sigma types and per-part instances and supporting kernel decidability.

2. **Represent an edge by a transversal function Fin r→V, not a vertex set.** In an r-partite r-uniform hypergraph, an edge is uniquely determined by its vertex in each part; the function is the same object in another form. Two edges share a vertex iff some coordinate i has e i=e′ i (the part label prevents vertices in different parts from being equal). This makes edge equality, cover membership, and disjointness decidable coordinate by coordinate.

3. **Define τ and ν by filtering power sets and using Finset.min′/max′, so they are computable.** This lets the kernel decide the numeric claims on the three small checkpoints (native_decide is forbidden by lexical scanning, but kernel decide is allowed). These finite definitions are exponential and intended only for small-instance computation; general reasoning uses the proved API lemmas coverNumber_le, le_coverNumber, le_matchingNumber, matchingNumber_le, and the two extremum-attainment lemmas.

4. **Require [NeZero r] (r≥1) for coverNumber.** At r=0, the empty edge (the unique function Fin 0→V) cannot be covered by any vertex set, so the cover number is not well-defined for arbitrary hypergraphs. The conjecture only uses r≥2; this parameter requirement changes no instance in its scope. matchingNumber needs no such assumption because the empty family is always a matching.

5. **Define refuted as the literal negation of the literature statement.** ¬∀r≥2,∀V,∀H,RyserBound is classically equivalent to the existence of r≥2 and an r-partite r-uniform hypergraph with τ>(r−1)ν. The model chooses the counterexample structure.

6. **Attribute the conjecture to Ryser in the conventional way (around 1970), although no formal publication record was found.** The statement is anchored to the 2021 survey by DeBiasio–Kamel–McCourt–Sheats; the original source was not opened and checked directly. The survey documents the source and the evidence of open status (a 2024 paper explicitly says r≥4 remains open). This source check is weaker than the LEAN task family’s content-reviewed standard and is recorded as such.

## 3. Distinction from nearby problems

- FC (google-deepmind/formal-conjectures) does not contain this conjecture. A full repository-tree check found ErdosProblems/723 named Ryser, but it is the Bruck–Ryser theorem, unrelated here.
- **Relation to tuza-conjecture in this line:** Both concern packing/covering duality, but Tuza concerns edge covers/packings of graph triangles, while this task concerns vertex covers/matchings in r-partite hypergraphs. Their definition layers, tight families, and known results differ.
- Lovász’s strengthening, requiring a cover to split into ν classes, was disproved in 2025. This task states Ryser’s original conjecture without that strengthening and is unaffected; the survey records the distinction.
- This is an open structural decision statement: a proof for every r-partite hypergraph or a machine-checkable counterexample would resolve it.

## 4. Known frontier

- r=2: Kőnig’s theorem (τ=ν); r=3: Aharoni 2001 (topological methods); r≥4: open. DeBiasio–Girão–Haxell–Stein 2024 explicitly say it “is still open for all r≥4.”
- The intersecting case (ν=1) holds for r≤5 (Tuza); the fractional-cover version holds (Lovász, Füredi); there are partial results for restricted classes such as linear hypergraphs.
- The trivial bound τ≤r·ν follows by taking all vertices of a maximum matching to cover every edge; it differs from the conjectured bound only by one in the coefficient.
