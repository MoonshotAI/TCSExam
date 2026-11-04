# Statement and sources: Online Bipartite Matching under Random Arrival Order

This note describes the current mathematical statement and its literature sources. It is for readers comparing the task with the Lean formalization.

The conjecture concerns the **competitive ratio of online bipartite
matching under random arrival order** (online bipartite matching:
Karp–Vazirani–Vazirani, STOC 1990; the random arrival order model:
Goel–Mehta, SODA 2008).

A bipartite graph has `n` *offline* vertices
(known in advance) and `n` *online* vertices. The online vertices arrive one
at a time; when a vertex arrives, its incident edges are revealed, and an
online algorithm must immediately decide either to match it to one of its
still-unmatched offline neighbors or to leave it unmatched forever. Decisions
cannot be revoked. In the **random order model** the arrival sequence is a
uniformly random permutation of the `n` online vertices. An algorithm may
also use its own randomness: it is modeled as a deterministic decision rule
fed by a *random tape* of `t` uniformly random bits. The value of an
algorithm on a graph `G` is the expected size `E[|M|]` of the matching it
produces (the expectation averages over both the arrival permutation and the
tape), and its performance guarantee is this expectation compared against
`ν(G)`, the size of a maximum matching.

The **optimal competitive ratio** of this model — the best worst-case ratio
`E[|M|] / ν(G)` any online algorithm can guarantee, asymptotically as
`n → ∞` — is **open**. It is known to be at least `0.696` (Mahdian–Yan, STOC
2011, via the Ranking algorithm) and at most `0.823` (Manshadi–Oveis
Gharan–Saberi, Math. Oper. Res. 2012), recently improved to
`1 − e/e^e ≈ 0.82062` (Chierichetti–Giacchini–Panconesi–Vattani, ICALP
2025). Even the exact competitive ratio of the Ranking algorithm in this
model is unknown.

This task fixes the threshold `3/4`, which lies strictly inside the known
interval, and asks for either direction in asymptotic form:

- `conj` — from some size threshold `N` on, at **every** size `n ≥ N` some
  randomized online algorithm guarantees `E[|M|] ≥ (3/4)·ν(G)` on every
  graph `G`. Proving it improves the best known lower bound from `0.696` to
  `0.75`.
- `refuted` — for **every** size threshold `N`, at **some** size `n ≥ N` no
  randomized online algorithm guarantees that. This is the literature's
  upper-bound shape: every algorithm, randomized ones included, is beaten at
  infinitely many sizes. Proving it improves the best known upper bound to
  `0.75`.

Either proof would be a publishable result.

The exact definition layer and quantified statements are in `environment/app/Task/Basic.lean`, with the scoring copy in `tests/reference/Basic.lean`. The `conj` and `refuted` statements are exact negations; proving either earns full credit. Finite illustrative checks are documented in `small-examples.md`.
