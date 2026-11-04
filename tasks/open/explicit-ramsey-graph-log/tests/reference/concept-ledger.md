# Statement and sources: The Paley-Graph Ramsey Conjecture

This note describes the current mathematical statement and its literature sources. It is for readers comparing the task with the Lean formalization.

The conjecture is the **Paley-graph Ramsey conjecture in its
polylogarithmic form**: clique number and independence number of the Paley
graph on `q` vertices are both `(log q)^{O(1)}`.

Erdős (1947) proved by the probabilistic method that graphs
with clique number and independence number at most `2·log₂ N` exist; the
open problem is an *explicit* (polynomial-time constructible) family, with
the current frontier `K = (log N)^{O(1)}` (Xin Li, FOCS 2023). The Paley
graph family is the canonical candidate: for a prime `q ≡ 1 (mod 4)` the
vertices are the elements of the field `ZMod q`, and two distinct vertices
are adjacent iff their difference is a quadratic residue. Adjacency is a
residue test, so the graphs are trivially explicit; the conjecture is
exactly the statement that this family achieves a polylogarithmic Ramsey
bound:

> There is a universal exponent `k` such that for every prime
> `q ≡ 1 (mod 4)`, the Paley graph on `q` vertices has neither a clique nor
> an independent set of size `(⌊log₂ q⌋ + 1)^k + 1`.

The stronger `O(log q)` bound is known to be **false** for the Paley
family: Graham & Ringrose (1990) proved that for infinitely many primes
`p ≡ 1 (mod 4)` the least quadratic non-residue `n(p)` satisfies
`n(p) ≥ c·log p·log log log p`, and the set `{0, …, n(p)−1}` is then a
clique in the Paley graph `P_p`. The genuinely open question is the
polylogarithmic upper bound: the best known unconditional upper bound is
`~√q` (Hanson–Petridis 2021; Yip 2020, arXiv:2004.01175), while the best
known lower bounds (Graham–Ringrose 1990, `log p·log log log p`; Montgomery
1971 under GRH, `log p·log log p`) fall short of any `(log p)^{1+ε}` — so
both proving and refuting the conjecture would be new.

The exact definition layer and quantified statements are in `environment/app/Task/Basic.lean`, with the scoring copy in `tests/reference/Basic.lean`. The `conj` and `refuted` statements are exact negations; proving either earns full credit. Finite illustrative checks are documented in `small-examples.md`.
