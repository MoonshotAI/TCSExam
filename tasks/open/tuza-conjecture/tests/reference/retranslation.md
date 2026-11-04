# Independent Retranslation: Tuza's Conjecture

This record derives a formalization draft from the literature statement without consulting the shipped Lean file, then compares the two component by component. It is the third fidelity record (independent retranslation).

- Source statement: the conjecture as summarized in `dig2-extremal-set-design.md`; the summary matches standard formulations of Tuza's conjecture.
- Method: refine the statement in natural language, draft the types, then compare with the shipped version.

## Step 1: Source statement

For any finite graph G, let ν_t(G) be the maximum number of pairwise edge-disjoint triangles (the triangle edge-packing number), and τ_t(G) the minimum size of an edge set meeting every triangle (the triangle edge-cover number; deleting that set leaves a triangle-free graph). Tuza's conjecture says that τ_t(G) ≤ 2·ν_t(G) always holds. If valid, the constant 2 is tight: equality holds for graphs whose every block is K₄.

## Step 2: Natural-language refinement (resolving ambiguities)

- **Graph:** finite, undirected, and simple (no loops or multiple edges), as in the literature.
- **Triangle:** three pairwise adjacent vertices of G, together with the three edges between them.
- **Edge-disjoint:** two triangles share no edge; they may share a vertex.
- **Packing:** a family of pairwise edge-disjoint triangles; ν is the largest possible size of such a family.
- **Cover:** an edge set F meeting every triangle in at least one edge (equivalently, G − F is triangle-free); τ is the minimum size of such an edge set. The cover consists of edges of G.
- **Conjecture:** for every finite graph G, τ(G) ≤ 2·ν(G).
- **Tightness:** on K₄ (and more generally, a graph all of whose blocks are K₄), τ = 2ν.

## Step 3: Independently drafted types

```
G : SimpleGraph V, with V finite
triangles(G) := {s : Finset V | #s = 3 ∧ every two vertices in s are adjacent}
cover(F) := F ⊆ edges(G) ∧ ∀ s ∈ triangles(G), triangleEdges(s) ∩ F ≠ ∅
τ(G) := min { #F | cover(F) }
packing(T) := T ⊆ triangles(G) ∧ ∀ s ≠ t ∈ T, triangleEdges(s) ∩ triangleEdges(t) = ∅
ν(G) := max { #T | packing(T) }
Conjecture := ∀ G, τ(G) ≤ 2 * ν(G)
```

## Step 4: Component-by-component comparison with the shipped version

| Component | Draft | Shipped version | Finding |
|---|---|---|---|
| Triangle | {#s = 3 and every pair is adjacent} | `G.cliqueFinset 3` (`IsNClique 3` = `IsClique ∧ #s = 3`) | Match (`IsClique` means pairwise adjacent). |
| Edges of a triangle | `triangleEdges(s)` | Same concept: `s.sym2` filtered to remove diagonal pairs | Match |
| Cover | F ⊆ edges(G), intersecting every triangle's edge set | `IsTriangleCover`, same form (intersection written as `¬Disjoint`) | Match |
| τ | Minimum over covers | `min'` of the cardinality image of `coverCandidates` | Match (same candidate set; existence of the minimum is proved). |
| Packing | T ⊆ triangles, pairwise edge-disjoint | `IsTrianglePacking`, same form | Match |
| ν | Maximum over packings | `max'` of the cardinality image of `packingCandidates` | Match |
| Conjecture | ∀ G, τ ≤ 2ν | `conj` (`refuted` is its negation) | Match |
| Tightness | τ = 2ν on K₄ | c1: τ(K₄) = 2 ∧ ν(K₄) = 1 | Match |

There are no disagreements. Two packaging differences—representing a triangle by a triple of vertices rather than a subgraph, and explicitly restricting covers to edges of G—preserve semantics. See deviations 1/2 in `concept-ledger.md`.

## Notes

- The equivalent wording “G − F has no triangle” is not used directly (mathlib requires a `DeleteEdges` wrapper), but the two forms are equivalent for finite graphs: F meets every triangle iff deleting F leaves no triangle. The shipped definition uses “intersects,” keeping the definition layer smaller.
- The conjecture has one universal quantifier, ∀ G, with no hidden existential constant; the constant 2 is fixed in `TuzaBound`.
