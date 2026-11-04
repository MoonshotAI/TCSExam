# Independent Retranslation: Online Bipartite Matching with Random Arrival Order

This record derives a formalization draft from the literature statement without consulting the shipped Lean file, then compares the two component by component. It is the third fidelity record (independent retranslation).

- Source statement: item 6 in `online-dynamic-streaming.md`. The summary matches standard formulations in the KVV and Mahdian–Yan papers and was cross-checked against primary-source abstracts.
- Method: refine the statement in natural language, draft the types, and compare with the shipped version.

## Step 1: Source statement

In online bipartite matching, one side of the vertices is known in advance, while vertices on the other side arrive one by one and must be matched immediately, with no option to revise earlier decisions. When arrival order is a uniformly random permutation, the best known competitive ratio lies in [0.696, 0.823]. The open problem is to determine its exact value.

## Step 2: Natural-language refinement (resolving ambiguities)

- **Graph:** a bipartite graph G = (U,V,E), with |U| = |V| = n. U is the offline side, known to the algorithm in advance; V is the online side, whose vertices arrive one at a time. The original KVV model has n vertices on each side and does not require a perfect matching to exist.
- **Arrival process:** the n vertices of V arrive in a uniformly random permutation σ, one at a time; the kth vertex to arrive is σ(k). On arrival, the algorithm sees all edges incident to that vertex (its offline neighborhood).
- **Online algorithm:** at each step it must immediately choose either an unused neighbor to match with the current vertex or to leave the vertex unmatched; the choice is irrevocable. The algorithm can see the arrival history so far (which vertices arrived and their neighborhoods) and the matching it has already chosen. Algorithms may be randomized. For a worst-case graph guarantee, randomization cannot beat the best deterministic algorithm: averaging over the algorithm's randomness gives a deterministic algorithm that performs at least as well. Thus it suffices to consider deterministic algorithms.
- **Value and benchmark:** the value of algorithm A on graph G is the expected matching size E_σ[|M|] over σ. The benchmark ν(G) is the maximum matching size of G. If ν(G) = 0, every algorithm also has value 0; by convention the ratio is 1 (both sides of any threshold inequality then hold trivially).
- **Competitive ratio and optimum:** A's guarantee is inf_G E[|M|]/ν(G); the optimal competitive ratio is sup_A of that guarantee (in the literature, asymptotically as n → ∞).
- **Proposition or negation (this task's threshold formulation):** fix t = 3/4, strictly inside the known interval. `conj` says that for every size n there is an algorithm guaranteeing at least 3/4 (a proof would improve the lower bound from 0.696 to 0.75); `refuted` says there is some size n at which no algorithm can guarantee 3/4 (a proof would improve the upper bound from 0.82062 to 0.75).

## Step 3: Independently drafted types

```
BipGraph n        := Finset (Fin n × Fin n)            -- edge (offline u, online v)
nbrs G v          := { u | (u, v) ∈ G }
IsMatching M      := both projections of M are injective
matchingNumber G  := max { #M | IsMatching M ∧ M ⊆ G }
OnlineAlg n       := at step k: (history: arrived vertices + their neighborhoods) × used offline set × current vertex × its neighborhood → Option (Fin n)
exec A G σ        := execute step by step (treat an illegal answer as leaving the vertex unmatched) to produce a matching
execCard          := #(exec A G σ)
expectedCard A G  := (Σ_{σ ∈ S_n} execCard A G σ) / n!      ∈ ℚ
conj              := ∀ n, ∃ A : OnlineAlg n, ∀ G, 3 * ν(G) ≤ 4 * expectedCard A G
refuted           := ¬ conj
```

## Step 4: Component-by-component comparison with the shipped version

| Component | Draft | Shipped version | Finding |
|---|---|---|---|
| Bipartite graph | Edge set `Finset (Fin n × Fin n)` | `BipGraph n`, same | Match |
| Neighborhood | `{ u | (u,v) ∈ G }` | `nbrs G v` (filter + image; `mem_nbrs` proves equivalence) | Match |
| Matching | Both projections injective | `IsMatching` (the image cardinalities equal the matching cardinality, for both sides) | Match (image-card equality is equivalent to `InjOn`) |
| ν(G) | Maximum over matchings | `max'` of the cardinality image of `matchings` (the empty matching is always present, so a maximum exists) | Match |
| Online algorithm | History × used set × current vertex × neighborhood → Option | `OnlineAlg n`, same form; history includes the identity and neighborhood of each arrival | Match |
| Execution | Step by step; treat illegal answers as skipping | `step` / `execUpTo` / `exec`, same; proved that the output is always a matching in G | Match |
| Expectation | Average over all n! permutations | `expectedCard`, summing over the full `Equiv.Perm (Fin n)` and dividing by n!, over ℚ | Match |
| `conj` | ∀ n ∃ A ∀ G, 3ν ≤ 4E | `conj`, same | Match |
| `refuted` | Negation | `refuted`, same | Match |

There are no disagreements. Packaging differences (deterministic algorithms suffice, asymptotic form replaced by a per-size statement, ℚ instead of ℝ, and the convention that ν = 0 is trivial) preserve the intended semantics. See deviations 2/4/5/6 in `concept-ledger.md` for item-by-item justification.

## Notes

- The literature defines the optimal competitive ratio asymptotically (with the supremum as n → ∞). A per-size formalization is standard: the lower-bound direction, “for every n there is an algorithm,” is a stronger form that implies the asymptotic lower bound; the impossibility direction, “there is some n that defeats every algorithm,” is exactly the form used by the literature's upper-bound proof, which exhibits a family of instances. On the threshold 3/4, each direction would imply the corresponding new result in the literature's sense.
- The permutation space for expectation is represented by `Equiv.Perm (Fin n)` (n! elements), rather than probability-language about “uniform random permutations.” Finite averaging suffices, with no measure theory. This is the most direct formalization and translates the survey's “random permutation” semantics directly.
