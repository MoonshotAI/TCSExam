# Faithfulness Review: Caccetta–Häggkvist Conjecture

This note explains the task statement for readers comparing the mathematical definitions with the Lean source. The current scoring statements are `conj` and `refuted`; proving either earns full credit.


This document checks each component of the shipped Lean statement against the paper’s statement and records its source and any deviations.

Caccetta and Häggkvist, “On minimal digraphs with given girth,” *Proceedings of the 9th Southeastern Conference on Combinatorics* (*Congressus Numerantium* 21), 1978, pp. 181–187. The standard formulation follows Hladký–Král'–Norin and recent surveys (revised arXiv:2102.12830).

## Standard literature statement

For every integer k≥1 and every n-vertex digraph D with minimum out-degree at least k, D contains a directed cycle of length at most ⌈n/k⌉. The cases k=1,...,5 are theorems: k=1 is trivial; k=2 was proved by Caccetta–Häggkvist; k=3 by Hamidoune; and k=4,5 by Hoáng–Reed (see Sullivan’s 2006 survey, arXiv:math/0605646). The case k=⌈n/3⌉—out-degree n/3 forcing a directed triangle—is the best-known open case, with best constant 0.3465 (Hladký–Král'–Norin).

## Component-by-component comparison

| Component | Paper | Shipped Lean statement | Assessment |
|---|---|---|---|
| Graph | Loopless digraph (no self-loops; 2-cycles are allowed). | `structure Digraph`: Bool adjacency plus `loopless : ∀ v, adj v v = false`; 2-cycles are not excluded. | Matches. |
| Vertex set | n vertices (implicitly finite and nonempty). | `(V : Type) [Fintype V] [Nonempty V]`, with n=`Fintype.card V`. | Matches; see deviation 1 for why Nonempty is needed. |
| Minimum out-degree ≥ k | Minimum, over v, of out-degree. | `∀ v, k ≤ D.outDegree v`; out-degree counts outgoing neighbors (`Finset.filter.card`). | Matches. |
| Directed cycle | A closed directed walk with no repeated vertices; length is the number of arcs, equal to the number of vertices. | An injective sequence `f : Fin ℓ → V` with arcs between consecutive terms, including the last-to-first edge using indices modulo ℓ; length ℓ. | Matches: injectivity is equivalent to no repeated vertices. |
| Length bound ⌈n/k⌉ | Ceiling function. | Natural-number division `(n + k - 1) / k`, equal to ⌈n/k⌉ for k≥1. | Matches; deviation 2 concerns the notation. |
| Hypothesis k≥1 | The conjecture is stated for every integer k≥1. | Explicit hypothesis `1 ≤ k`. | Matches. |

## Deviations

1. **Explicit `[Nonempty V]` hypothesis.** The paper implicitly assumes n≥1. If Lean allowed the empty type, the out-degree premise for k≥1 would hold vacuously while the conclusion (there is a cycle) would be false. Adding `Nonempty` is therefore a necessary formal completion and does not change the mathematical content.

2. **Write the ceiling as `(n + k - 1) / k`.** Natural-number division gives ⌈n/k⌉ when k≥1. This avoids reals and a separate ceiling function, and makes computation and arithmetic reasoning simpler. The special cases sc_k1/sc_k2 write ⌈n/1⌉ and ⌈n/2⌉ directly as `n` and `(n + 1) / 2`, the same formula with k=1 and k=2 substituted.

3. **Represent a directed cycle by an injective sequence `Fin ℓ → V`, not by a List.** This supports decidability (`Decidable (HasCycleOfLengthLe m)`), so sc_circulant can check small instances with `decide`. It is mathematically equivalent to a closed walk with no repeated vertices: the sequence gives the walk, injectivity prevents repeats, and indices modulo ℓ close the cycle.

4. **Choice of (n,k) for sc_circulant.** Each of [(4,1),(5,2),(7,2),(7,3),(10,3)] satisfies 2k<n, so every vertex has exactly k outgoing neighbors and no step wraps into the opposite direction. The five cases cover ⌈n/k⌉=4,3,4,3,4, including two small instances of the best-known k=3 case. They witness that the bound cannot be lowered and support no other claim; see the numerical checks in group A of small-examples.md.

5. **Form of `refuted`.** Negation `¬` applies to the entire `conj` statement, including all instance parameters and hypotheses. It therefore says that some k≥1 and some digraph satisfying the out-degree condition has no cycle of length at most ⌈n/k⌉, exactly the negation of the conjecture.

## Checks against systematic formulation errors

- **Could “contains a cycle” have weakened to “contains a closed walk”?** The existential cycle is required to be injective. Without injectivity, a closed walk is weaker (every digraph with positive out-degree has a closed walk). Injectivity is present, and exhaustive groups B/C use the same no-repeated-vertices semantics.
- **Could the length convention be off by one?** Length equals vertex count equals arc count: f lists ℓ vertices and there are ℓ arcs, including the last-to-first edge. Group A verifies tightness of ⌈n/k⌉ on small cyclic examples; an off-by-one convention would fail this check.
- **Could in-degree have been counted instead of out-degree?** `outDegree` counts exactly the w with `adj v w = true`, in the outgoing direction. Group A’s script counts outgoing neighbors, matching the Lean definition term by term.
- **Could k=0 or a vacuous premise make the statement trivial?** The explicit condition `1 ≤ k` excludes k=0, for which ⌈n/0⌉ is undefined and which is outside the conjecture.
- **Could the two proposition slots both score as true and receive full credit?** `conj` and `refuted` are negations; scoring checks them independently against an axiom whitelist, and the kernel ensures that at most one can be proved without `sorry`.
