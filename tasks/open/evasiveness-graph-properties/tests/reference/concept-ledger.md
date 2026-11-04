# Faithfulness Review: The Evasiveness Conjecture (Karp’s Conjecture)

This note explains the task statement for readers comparing the mathematical definitions with the Lean source. The current scoring statements are `conj` and `refuted`; proving either earns full credit.

This document compares the literature statement of the evasiveness conjecture with the Lean statement used by this task, recording its components and every modeling choice.

- Sources: Miller 2011, “Evasiveness of Graph Properties and Topological Fixed-Point Theorems,” Foundations and Trends in Theoretical Computer Science 7(4), pp. 337–415 (arXiv:1306.0110; introduction and background read in full); the Wikipedia entry “Aanderaa–Karp–Rosenberg conjecture” (read 2026-09-06); Kahn–Saks–Sturtevant 1984, Combinatorica 4(4), 297–306; Scheidweiler–Triesch 2013, SIDMA 27(1), 257–265; Rosenberg 1973, SIGACT News 5(4), 15–16.
- Released statement: environment/app/Task/Basic.lean; its fixed region and slot statements match tests/reference/Basic.lean word for word.

## 1. Literature statement and Lean correspondence

Miller 2011 defines a graph property as a function from graphs on a vertex set V to {0,1}, with isomorphic graphs receiving the same value. Query cost counts queried edges; queries may be adaptive, and an algorithm is a binary decision tree. The decision-tree complexity D(P) is the minimum depth of a tree computing P, or the worst-case number of edge queries made by the best algorithm. Karp’s conjecture says **every nontrivial monotone graph property is evasive**, meaning D(P)=C(v,2) and the worst case requires querying every possible edge. Monotone means preserved under adding edges (increasing) or under removing edges (decreasing).

| Concept | Literature | Lean identifier in this task | Notes |
|---|---|---|---|
| Vertex set | A finite set V with |V|=v. | Fin v. | Vertices are labeled; isomorphism invariance removes dependence on labels. |
| Graph | Finite undirected simple graph. | G : SimpleGraph (Fin v). | mathlib SimpleGraph is an undirected simple graph. |
| Graph property | Isomorphism-invariant function from graphs to {0,1}. | GraphProp v (a Bool-valued function) plus IsGraphProperty (separate isomorphism-invariance predicate). | Miller’s definition has these same two parts; see deviation 1. |
| Monotonicity | Preserved by adding edges (increasing; decreasing is equivalent by complement). | IsMonotone P := G ≤ H → P G = true → P H = true. | Uses the increasing direction only; see deviation 2. |
| Nontriviality | Does not map every graph to the same value. | IsNontrivial P := (∃ G, P G = true) ∧ ∃ H, P H = false. | Direct correspondence. |
| Decision tree | Binary tree whose internal nodes query an edge. | DTree v: leaf Bool / query (e : Sym2 (Fin v)) t f. | See deviation 3. |
| Depth | Worst-case number of queries. | DTree.depth (leaf has depth 0; query has max child depth + 1). | |
| Evaluation | Follow the branch dictated by the input graph until a leaf. | DTree.eval G (queries e ∈ G.edgeFinset). | |
| Computes P | Outputs P’s value on every input graph. | DTree.Decides t P := ∀ G, t.eval G = P G. | |
| Complexity D(P) | Minimum depth among trees computing P. | Not defined separately; the conjecture states that every decision tree has depth at least C(v,2). | See deviation 4. |
| Evasive | D(P)=C(v,2). | For every decision tree, v.choose 2 ≤ t.depth. | See deviation 4. |
| Conjecture | Every nontrivial monotone graph property is evasive. | conj: ∀ v P, the three hypotheses imply ∀ decision trees, choose 2 ≤ depth; refuted is its negation. | v is universally quantified. The prime-power case being proved does not settle the universal statement; see §4. |

## 2. Deviations and rationale

1. **Represent a graph property as a Bool-valued function plus a separate isomorphism-invariance predicate.** This follows Miller’s structure exactly: “a graph property is simply a function … to {0,1},” with isomorphism invariance as an additional condition. In Lean, GraphProp v carries a [DecidableRel G.Adj] instance parameter so concrete properties can compute on edge sets. The property’s value does not depend on the choice of instance (proof irrelevance); all three hypotheses and the Decides statement hold for any such instance.

2. **Use only the increasing monotonicity direction.** The literature also calls decreasing properties monotone. The two directions are exchanged by Boolean complementation, and complementation does not change decision-tree depth (flip every leaf of the same tree). Thus the increasing-only conjecture is equivalent to the version allowing both directions. This convention also matches the Wikipedia wording, “remains true when edges are added.”

3. **Allow queries over all Sym2 (Fin v), including diagonal pairs, and allow repeated queries and trees deeper than C(v,2).** A diagonal query always answers “no,” and a repeated query adds no information, so no optimal tree needs either and D(P) is unchanged. The main statement is a lower bound, so it only becomes stronger for deeper trees. This avoids encoding “off-diagonal pairs and no repeated query” in the type.

4. **Write D(P)=C(v,2) as “every decision tree has depth at least C(v,2).”** Every graph property can be decided by the naive tree that queries all C(v,2) candidate edges in a fixed order, so D(P)≤C(v,2) always. Therefore equality is equivalent to the lower bound. The lower-bound form avoids adding a minimum-depth operator to the definition layer.

5. **Give v no extra lower bound, including when v≤1.** There is no nontrivial property when v≤1 because there is only one graph. The hypotheses are then empty and both main slots are vacuously true. The literature’s “nontrivial” hypothesis already excludes those values, so no explicit 2≤v is needed.

6. **Define refuted as the literal negation of conj.** This is ¬∀v P, … → choose 2 ≤ depth. Classical logic makes it equivalent to the existence of v, a nontrivial monotone property P, and a decision tree of depth < C(v,2), i.e. D(P)<C(v,2), exactly the failure of the conjecture.

## 3. Distinction from nearby problems

- **The original Aanderaa–Rosenberg conjecture (weak Ω(v²) form):** Rivest–Vuillemin proved it in 1975 with a v²/16 bound. This task concerns Karp’s stronger, exact C(v,2) claim. The weak form being proved does not settle the strong form: the best general deterministic lower bound is (1/3−o(1))·v² (Scheidweiler–Triesch 2013), still a constant factor below C(v,2)≈v²/2.
- **Prime-power vertex counts:** Kahn–Saks–Sturtevant 1984 proved those cases using topological fixed-point methods. conj quantifies over every v, so the prime-power theorem does not settle it; the conjecture remains open from the first non-prime-power value v=6 onward. Miller 2011 says, “To date, this conjecture is unproven and no counterexamples are known.” Both conj and refuted are therefore genuinely open.
- **Properties that are not monotone:** Some nonmonotone graph properties can be decided with O(v) queries (the scorpion graph, Best–van Emde Boas–Lenstra 1974, Report ZW 30/74; also listed in the Wikipedia entry), showing that monotonicity is necessary asymptotically. Checkpoint c2 instead tests the more elementary necessity of nontriviality: for small vertex counts, no nontrivial non-evasive property appears—exhaustive search for v≤4 and all ten natural candidates at v=5 were evasive.
- **Rivest–Vuillemin parity-balance condition** (non-evasiveness implies equal numbers of satisfying and falsifying graphs of even/odd edge count) and the KSS evasiveness criterion are proof-technique background and are not in the statement layer.

## 4. Known frontier

- Deterministic bounds: Rivest–Vuillemin proved v²/16 in 1975; Kleitman–Kwiatkowski improved it in 1980; Kahn–Saks–Sturtevant (1984) proved prime-power cases and improved the general lower bound; Korneffel–Triesch 2010 (Combinatorica 30(6):735–743); Scheidweiler–Triesch 2013 (SIDMA 27(1):257–265) reached (1/3−ε)·v², the current best.
- Every nontrivial monotone property on bipartite graphs is evasive (Yao 1988, SIAM J. Comput. 17(3):517–520); minor-closed properties are evasive for sufficiently large v (Chakrabarti–Khot–Shi 2001).
- Randomized query complexity: Karp’s conjecture predicts Ω(n²); the best known lower bound is Ω(n^(4/3)(log n)^(1/3)) (Chakrabarti–Khot 2007). Quantum query complexity has lower bound Ω(n^(2/3)(log n)^(1/6)).
- Evidence of open status: Miller 2011 explicitly calls the conjecture “unproven and no counterexamples are known”; the Wikipedia entry (2026-05 version) still lists it as open.
