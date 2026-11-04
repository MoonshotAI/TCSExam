# Independent Retranslation: The GNRS Conjecture

This record derives a formalization draft from the literature without consulting the shipped Lean file, then compares the two component by component. It is the third fidelity record (independent retranslation).

- Source: the Wikipedia “GNRS conjecture” entry and consistent restatements in later literature, including Filtser 2019 and Krauthgamer–Lee–Rika 2018.

## Step 1: Source statement

The GNRS conjecture says that there is a constant C < ∞ such that the shortest-path metric of every planar graph G embeds into ℓ₁ with distortion at most C. Distortion means there is a map φ and c > 0 such that all pairs u,v satisfy c·d(u,v) ≤ ‖φ(u)−φ(v)‖₁ ≤ C·d(u,v); the distortion is C/c (equivalently, use the noncontracting normalization c = 1). A stronger version says that every proper minor-closed graph family (closed under deleting edges/vertices and contracting edges, and not equal to all graphs) has an ℓ₁ embedding with distortion bounded by a constant depending only on the family. Planar graphs are a flagship special case of a minor-closed family.

## Step 2: Natural-language refinement (resolving ambiguities)

- **Graph:** finite, undirected, simple, and connected (finite distances require connectedness, which is standard in the literature's setting).
- **Planar graph:** embeddable in the sphere/plane. For finite graphs, Wagner's theorem gives the equivalent combinatorial form: no K₅ minor and no K₃,₃ minor.
- **Minor:** obtainable by deleting vertices or edges and contracting edges; equivalently, use the branch-set model (each vertex of H corresponds to a nonempty connected branch set in G, the branch sets are pairwise disjoint, and every edge of H corresponds to an edge of G between the corresponding branch sets).
- **Shortest-path metric:** d(u,v) is the minimum number of edges in a u-to-v walk; a shortest walk is a path and has length at most |V|−1.
- **ℓ₁:** for a finite metric space, embedding into ℓ₁ is equivalent to embedding into some finite-dimensional (ℝ^k, ‖·‖₁), with ‖x‖₁ = Σᵢ |xᵢ|.
- **Distortion convention:** use the noncontracting normalization d(u,v) ≤ ‖φ(u)−φ(v)‖₁ ≤ C·d(u,v).
- **Conjecture:** there is C such that every connected planar graph G admits such a φ.

## Step 3: Independently drafted types

```
G : SimpleGraph V, V finite, G connected
IsPlanar G := ¬ HasMinor G K₅ ∧ ¬ HasMinor G K₃,₃
HasMinor G H := ∃ branch sets B : V(H) → Set V, nonempty ∧ connected ∧ pairwise disjoint ∧ adjacent according to H's edges
dist := shortest-path length (minimum over paths of length < card V; unreachable = 0)
embeds(G, C) := ∃ k : ℕ, ∃ φ : V → (Fin k → ℝ),
  ∀ u v, dist u v ≤ Σ i |φ u i − φ v i| ∧ Σ i |φ u i − φ v i| ≤ C · dist u v
Conjecture := ∃ C : ℝ, ∀ G, G connected → IsPlanar G → embeds(G, C)
```

## Step 4: Component-by-component comparison with the shipped version

| Component | Draft | Shipped version | Finding |
|---|---|---|---|
| Graph | Finite simple graph + connectedness premise | Same (`SimpleGraph V` plus `Fintype` and other instances, and `G.Connected`) | Match |
| Planarity | No K₅ or K₃,₃ minor (Wagner) | `IsPlanar := ¬ HasMinor K₅ ∧ ¬ HasMinor k33` | Match |
| Minor | Branch-set model | `HasMinor`, with four branch-set conditions | Match |
| Distance | Shortest-path length, unreachable = 0 | `spDist`, same form; `spDist_eq_dist` anchors it to mathlib's `dist` | Match |
| ℓ₁ | Finite-dimensional real vector and sum of coordinate absolute differences | `l1Dist` on `Fin k → ℝ` | Match |
| Embedding | Noncontracting and expansion at most C | `EmbedsIntoL1 C`, same form | Match |
| Conjecture | ∃ C ∀ connected planar graphs | `conj` (`refuted` is its negation) | Match |

There are no disagreements. Reasons and equivalence arguments for the connectedness premise, Wagner's form of planarity, and the noncontracting normalization are in deviations 3/7/8 of `concept-ledger.md`.

## Notes

- The source statement specifies only the distortion ratio C/c. The choice of noncontracting normalization follows common practice in the GNRS and later literature (deviation 7 in `concept-ledger`).
- Weighted graphs are not included in the draft: the unweighted case is already the core difficulty, and the reduction between weighted and unweighted versions is a standard literature result (deviation 2 in `concept-ledger`).
- The stronger statement for arbitrary minor-closed graph families is not included in `conj`; this task formalizes the planar case. The stronger form is included as background in `instruction`, and the two formulations coincide on planar graphs.
