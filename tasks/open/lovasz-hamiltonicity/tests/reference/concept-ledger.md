# Faithfulness Review: Lovász’s Hamilton-Path Conjecture for Vertex-Transitive Graphs

This note explains the task statement for readers comparing the mathematical definitions with the Lean source. The current scoring statements are `conj` and `refuted`; proving either earns full credit.


This document compares Lovász’s 1969 question with the Lean statement used by this task and records the modeling choices.

- **Released statement:** environment/app/Task/Basic.lean; it matches tests/reference/Basic.lean word for word.
- **Standard formulations:** for example, the introductions of Groenland–Johnston–Scott–Tan 2025 and Alspach’s survey.

## 1. Literature statement and Lean correspondence

Lovász asked in 1969 whether every finite connected vertex-transitive graph has a Hamilton path. The conjecture concerns a **path**: the Petersen graph is vertex-transitive but has no Hamilton cycle, so the cycle version is false. Exactly five connected vertex-transitive graphs without a Hamilton cycle are currently known: K₂, the Petersen graph, the Coxeter graph, and the two graphs obtained by replacing every vertex of the Petersen and Coxeter graphs with a triangle. All five have Hamilton paths.

| Concept | Literature | Lean identifier in this task | Notes |
|---|---|---|---|
| Graph | Finite undirected simple graph. | G : SimpleGraph V with [Fintype V] [DecidableEq V]. | SimpleGraph is undirected/simple; Fintype gives finiteness. |
| Connected | There is a path between every pair of vertices. | G.Connected (mathlib: Preconnected ∧ Nonempty V). | mathlib treats the empty graph as disconnected, consistent with the literature; it is not a counterexample. |
| Vertex-transitive | Automorphism group acts transitively on vertices. | G.IsVertexTransitive := ∀u v:V, ∃e:G≃gG, e u=v. | Defined here because mathlib has no existing definition (repository search for vertex-transitive found no relevant API); ≃g is RelIso G.Adj G.Adj. |
| Hamilton path | A path passing through every vertex exactly once. | G.HasHamiltonianPath := ∃u v:V, ∃p:G.Walk u v, p.IsHamiltonian. | mathlib Walk.IsHamiltonian requires each vertex to occur exactly once in the support. |
| Conjecture | Every connected vertex-transitive graph has a Hamilton path. | Main slot conj universally quantifies over all finite graphs; refuted is its literal negation. | |
| Standard counterexample to the cycle version | Petersen graph: vertex-transitive, has a Hamilton path, and has no Hamilton cycle. | Definition-layer petersenGraph (15-edge list on Fin 10) plus explicit witness petersenHamPath; checkpoint c1. | mathlib has no Petersen-graph constructor, so it is defined here. |

## 2. Deviations and rationale

1. **Represent Hamilton paths using mathlib’s Walk.IsHamiltonian** (∀v, p.support.count v=1). This agrees pointwise with “a path visiting every vertex exactly once”: mathlib has proved the connection lemmas IsHamiltonian→IsPath (no repeated vertex implies a path) and IsPath plus full coverage→IsHamiltonian. mathlib uses SimpleGraph.IsHamiltonian for the cycle property, so the path version is a four-line wrapper named HasHamiltonianPath.

2. **Express vertex-transitivity using graph isomorphisms ≃g (RelIso).** For every u,v there is a bijection preserving adjacency that sends u to v. This is the pointwise form of transitivity of the automorphism group and is equivalent to the group-action formulation in the literature. mathlib has no existing definition (a repository search for “ransitive” found only unrelated Turán/complete-multipartite entries), so a two-line definition was added.

3. **Do not require a decidable adjacency instance in the conjecture.** conj requires only [Fintype V] and [DecidableEq V]; the latter is needed only for List.count in Walk.IsHamiltonian. Unlike the Tuza package, this definition layer has no computability requirement. Adjacency of a finite graph is decidable in classical logic, so omitting DecidableRel G.Adj does not change the mathematical scope.

4. **Define refuted as the literal negation of the literature statement.** Negating “for every finite graph, connected and vertex-transitive implies it has a Hamilton path” is classically equivalent to “there is a finite connected vertex-transitive graph with no Hamilton path.” The model supplies the counterexample.

5. **Define the Petersen graph by an explicit 15-edge list on Fin 10**: outer 5-cycle on vertices 0–4, inner 5-point star on 5–9, and spokes i~i+5. This avoids a Kneser-graph constructor and keeps the definition layer small. A Python check provides an independent verification (petersen_check.py): 3-regularity, girth 5, automorphism group of order 120 (the full S₅), transitive action, and no Hamilton cycle—all standard signatures of K(5,2).

6. **Handle mathlib’s convention for Hamilton cycles on a one-vertex graph.** SimpleGraph.IsHamiltonian uses Fintype.card≠1→∃… and treats the singleton graph as Hamiltonian. For checkpoint c2, the card=1 case uses the definition-layer lemma hasHamiltonianPath_of_subsingleton (the trivial walk is a Hamilton path), consistent with this convention. The literature also counts the degenerate one-vertex path as a Hamilton path, so there is no discrepancy.

## 3. Distinction from nearby problems

- The log-rank conjecture (Lovász–Saks 1988, represented by this repository’s log-rank-conjecture package) shares an author but is unrelated.
- Lovász’s Local Lemma is unrelated.
- Lower bounds on the circumference of connected vertex-transitive graphs are quantitative weakenings in the same direction (n^(13/21) is partial progress on longest-cycle length), not a solution of this conjecture. This task is the full structural existence question about a Hamilton path and has no numerical parameter in its statement.

## 4. Known frontier

- For the longest cycle in a connected vertex-transitive graph of order n: Babai 1979 proved Ω(√n); DeVos improved it in 2023; Groenland–Johnston–Scott–Tan 2025 obtained n^(13/21). This is the background supplied by the parent agent and agrees with the 2025 arXiv paper; it was not independently verified online in this review.
- Exactly five connected vertex-transitive graphs without Hamilton cycles are known: K₂, Petersen, Coxeter, and the two truncations; all have Hamilton paths.
- Some restricted cases are settled: connected Cayley graphs of abelian groups have Hamilton cycles, and results are known for several special orders (p, 2p, pq, etc.).
- Work in 2025 still treats the conjecture as open (Groenland–Johnston–Scott–Tan).

## 5. Review level

**Locator-only, recorded as such.** The original 1969/1970 proceedings page was not checked. During authoring, web-search quota was exhausted and direct arXiv access failed; the statement is anchored to standard survey formulations and background supplied by the parent agent. The key Petersen properties (vertex-transitivity, a Hamilton path, and no Hamilton cycle) were independently checked both by Python and by Lean kernel decide; see small-examples.md. These checks do not depend on the literature summary.
