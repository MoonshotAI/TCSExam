# Independent Retranslation: The Evasiveness Conjecture

This record derives a formalization draft from the literature without consulting the shipped Lean file, then compares the two component by component. It is the third fidelity record (independent retranslation).

- Source statements: the introduction to Miller's 2011 survey (arXiv:1306.0110, read from the original) and the Wikipedia entry “Aanderaa–Karp–Rosenberg conjecture.”
- Method: refine the source in natural language, draft the types, then compare with the shipped version.

## Step 1: Source statement

Miller 2011, Chapter 0 (introduction, restated point by point):

- Let V be a finite set of size v, and let G_V be the set of undirected graphs on V. A graph property is a function P : G_V → {0,1} that assigns the same value to isomorphic graphs.
- Algorithmic cost is the number of edge queries; queries may be adaptive, so an algorithm is a binary decision tree. The decision-tree complexity D(P) of P is the minimum depth of a decision tree computing P, i.e. the worst-case number of edge queries used by the best algorithm.
- If D(P) = C(v,2), the largest possible value, P is called evasive.
- A graph property is monotone if it is preserved when edges are added (monotone increasing) or when edges are removed (monotone decreasing).
- **Karp's conjecture: every nontrivial monotone graph property is evasive.** The source says, “All nontrivial monotone graph properties are evasive,” and “To date, this conjecture is unproven and no counterexamples are known.”

The Wikipedia entry adds that nontrivial means the property does not assign the same value to every graph; an evasive decision algorithm must query all n(n−1)/2 candidate edges in the worst case; and Rosenberg's 1973 motivating example, the nonempty-property test, is evasive.

## Step 2: Natural-language refinement (resolving ambiguities)

- **Vertex set:** a labeled set of v vertices; invariance under graph isomorphism expresses that the property does not depend on labels.
- **Graph:** finite, undirected, and simple. Candidate edges are unordered pairs of distinct vertices, for a total of C(v,2).
- **Decision tree:** internal nodes query a candidate edge, with two branches for “present” and “absent”; leaves return 0 or 1. Depth is the maximum number of queries on a root-to-leaf path.
- **Tree computes P:** for every input graph, the leaf reached by following its answers has value P.
- **D(P):** the minimum depth among trees that compute P. Every property has D(P) ≤ C(v,2), via the naive tree that queries all edges in order. Thus P is evasive iff every decision tree computing P has depth ≥ C(v,2).
- **Monotone:** use the increasing (preserved by adding edges) convention; the decreasing case reduces by complementing P (flip all leaves of the same tree, preserving depth).
- **Nontrivial:** there is a graph with P = 1 and a graph with P = 0. For v ≤ 1 there is no nontrivial property, so the conjecture is vacuous for those values.
- **Conjecture:** for every vertex count v and every isomorphism-invariant, monotone, nontrivial P, every decision tree computing P has depth ≥ C(v,2).

## Step 3: Independently drafted types

```
Prop_v := SimpleGraph (Fin v) → Bool
isoInv P  := ∀ G H, G ≃g H → P G = P H
mono P    := ∀ G H, G ≤ H → P G = true → P H = true
nontriv P := (∃ G, P G = true) ∧ (∃ G, P G = false)
Tree_v    := leaf Bool | query (e : Sym2 (Fin v)) Tree_v Tree_v
depth     := leaf → 0; query → 1 + max
run G t   := follow the branch determined by whether e ∈ G.edgeFinset
computes t P := ∀ G, run G t = P G
Conjecture := ∀ v P, isoInv P → mono P → nontriv P → ∀ t, computes t P → v.choose 2 ≤ t.depth
```

## Step 4: Component-by-component comparison with the shipped version

| Component | Draft | Shipped version | Finding |
|---|---|---|---|
| Property type | `SimpleGraph (Fin v) → Bool` | `GraphProp v` (with an additional `[DecidableRel G.Adj]` instance parameter) | Match (the instance supports computation of specific properties but does not affect the value; deviation 1 in `concept-ledger`) |
| Isomorphism invariance | ∀ G H, G ≃g H → P G = P H | `IsGraphProperty`, same form | Match |
| Monotonicity | G ≤ H → P G = true → P H = true | `IsMonotone`, same form | Match |
| Nontriviality | There is a positive example and a counterexample | `IsNontrivial`, same form, positive example first | Match |
| Decision tree | Inductive leaf/query type | `DTree`, same form | Match |
| Depth | Leaf depth 0; query depth 1 + max | `DTree.depth`, same form | Match |
| Evaluation | Follow whether the edge belongs to `edgeFinset` | `DTree.eval`, same form | Match |
| Computes/decides | ∀ G, run = P | `DTree.Decides`, same form | Match |
| Conjecture | ∀ v P, three premises imply depth ≥ choose 2 | `conj`, same form (`refuted` is its negation) | Match |
| C(v,2) | Binomial coefficient | `v.choose 2` (matches mathlib's `card_edgeFinset_top_eq_card_choose_two`) | Match |

There are no disagreements. The only packaging difference is that the draft omits a decidability instance (treating a “query response” as a mathematical function), while the shipped form includes the instance for computation. The propositions are the same; see deviation 1 in `concept-ledger.md`.

## Notes

- The source defines D(P) as a “minimum depth”; both the draft and shipped version rephrase it as “every decision tree has depth ≥ C(v,2).” This uses the fact that the naive all-edges tree gives the upper bound C(v,2), which the literature (the Wikipedia entry's “Query complexity” section) states explicitly. The rephrasing is equivalent.
- Quantifier order: ∀ v (all vertex counts) is outermost. The cases v ≤ 1 are vacuous by the nontriviality premise, matching the source, which does not separately exclude small v.
- There is no quantifier-order trap: the three premises follow P, and tree t is innermost. “Every tree deciding P” corresponds to the source's “every algorithm.”
