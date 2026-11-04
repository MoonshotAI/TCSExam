# Concept ledger — ramsey-r46-lean

This document provides a crosswalk from each Lean identifier in the definition layer to the literature definition, an item-by-item alignment with the predicate in the Solver sibling task, and a record of formalization choices.

## Literature concepts ↔ Lean identifiers

each row maps a literature definition to its Lean representation and explains any modeling choice.

| Literature definition | Lean identifier (`namespace R46`) | Crosswalk notes |
|---|---|---|
| Vertex set of the complete graph K_N | `Fin N` (parameter of `Coloring`) | N vertices indexed 0..N-1, the standard representation |
| Red/blue 2-coloring of edges (edges are unordered pairs of vertices) | `Coloring N`: `color : Fin N → Fin N → Fin 2` plus field `symm : ∀ i j, color i j = color j i` | 0/1 in `Fin 2` mean red/blue; the `symm` field encodes unordered pairs in the type. **Choice**: no constraint on diagonal `color i i` (K_N has no loops, so the diagonal has no mathematical content; `MonoFree` only considers pairs with `i ≠ j`, so this does not affect truth of any statement). |
| Red K4 (4 vertices, all 6 edges red) | `∀ i ∈ s, ∀ j ∈ s, i ≠ j → c.color i j = 0`, where `s : Finset (Fin N)` and `s.card = 4` | Expressing a “4-tuple” as a 4-element subset (Finset with card = 4) is equivalent to the literature's “any 4 vertices”; `i ≠ j` excludes loops, and the 6 edges are all unordered pairs (symmetry makes the ordered quantification redundant). |
| Blue K6 (6 vertices, all 15 edges blue) | Same form, with `s.card = 6` and `c.color i j = 1` | The 15 edges are all unordered pairs, C(6,2). |
| A coloring with no red K4 and no blue K6 (certificate that R(4,6) > N) | `MonoFree c` := conjunction of the two conditions “for every subset, the corresponding monochromatic clique does not exist” | That is, “every 4-tuple is not all red and every 6-tuple is not all blue.” `@[reducible]` only lets `decide` / `native_decide` synthesize `Decidable` instances directly for small N; it does not change the semantics. |
| Lower-bound claim R(4,6) ≥ N+1 | `submission_lower : ∃ c : Coloring N, MonoFree c` | A valid coloring exists iff R(4,6) > N. |
| Upper-bound claim R(4,6) ≤ N | `submission_upper : ∀ c : Coloring N, ¬ MonoFree c` | Every coloring contains a red K4 or a blue K6 iff R(4,6) ≤ N. When N < R(4,6), this statement is false and cannot be proved validly, so there is no way to gain credit by exploiting that case. |

## Item-by-item alignment with the Solver sibling predicate (ramsey-r46)

The Solver version submits a red-edge list (graph G); the checker's two tests correspond to the two conjuncts of this version's `MonoFree` predicate:

each row pairs a Solver checker condition with the corresponding `MonoFree` conjunct and gives the equivalence.

| Solver checker (`tests/checker.py`) | Corresponding `MonoFree` conjunct | Equivalence |
|---|---|---|
| `find_k(n, red, 4)`: the red graph has no 4-clique (red K4) | First conjunct: for every 4-element subset s, not all pairs inside s are red | Equivalent by definition: the red graph has a 4-clique iff some 4-element subset has all 6 edges red. |
| `find_k(n, blue, 6)`: the complement (blue graph) has no 6-clique = the red graph has no independent set of size 6 | Second conjunct: for every 6-element subset s, not all pairs inside s are blue | Equivalent by definition: blue means absent from the red-edge list (blue is the complement of red); an independent set of 6 vertices iff all 15 edges of the 6-element subset are blue. |
| Format constraints (n ∈ [1,64], valid endpoints, no loops, no duplicate pairs) | Not needed: `Coloring` uses `Fin N` and `symm` to encode validity in the type | Format validity for a graph representation corresponds to type validity for the coloring representation; the unconstrained diagonal does not affect the semantics. |

Converting between the graph and coloring formulations expands the literature statement “R(4,6) > N iff there is an N-vertex graph with no K4 and no independent set of size 6.” Under the correspondence above, the predicates in both versions express the same statement.

Cross-checks: ① Recompute the sibling version's bundled construction `example_n24.json` (N=24, 107 red edges) using a literal Python transcription of this version's predicate. Every 4-element subset is not all red (brute force over C(24,4)), and every 6-element subset is not all blue (brute force over C(24,6)); both formulations agree. ② Parse the Lean-side oracle edge list `redEdges14` (the induced subgraph on vertices 0..13 of the sibling's N=24 graph, 37 red edges) back into the sibling JSON certificate and run the original sibling checker (`tests/checker.py`): valid=1, reward=0 (milestone baseline). The same cross-run with the complete N=24 edge list also passed; both versions give the same score for the same construction. ③ Negative controls (the all-red graph on 4 vertices and all-blue graph on 6 vertices) are both rejected by both formulations. The record construction at N=35 (Exoo 2012) has not been checked end-to-end in Lean: checking the blue condition on 35 vertices requires scanning C(35,6) ≈ 1.6×10⁶ six-element subsets. `native_decide` may be able to handle it in principle (the sibling Python checker takes seconds), but this requires the record graph data and corresponding proof work; see “Open checks” in `PROVENANCE.md`.

## Record anchors (same sources as the Solver sibling version; see `../../../construction-conjecture-solver/tasks/ramsey-r46/PROVENANCE.md`)

- Lower-bound record: a valid coloring on 35 vertices (Exoo 2012, *On the Ramsey Number R(4,6)*, EJC 19(1) #P66) → lower-bound record N=35.
- Upper-bound record (two source conventions): the formally published value R(4,6) ≤ 41 (McKay–Radziszowski 1997, *Subgraph Counting Identities and Ramsey Numbers*, JCT B 69:193–209) → upper-bound record N=41. A survey reports R(4,6) ≤ 40 in DS1 rev #18, Table Ib (Angeltveit–McKay 2024, personal communication, not formally published). The task statement and scoring use the formally published value as the record and mention the survey value in the statement.
- Trivial anchors: construction direction N=24 (R(4,5) = 25 implies a coloring on 24 vertices with no red K4 and no blue K5, and hence no blue K6; same baseline as the Solver version); upper-bound direction N=56 = C(8,3), the Erdős–Szekeres recursion bound (`R(s,t) ≤ C(s+t−2, s−1)`, a textbook result requiring no computation).
- Dynamic survey: Radziszowski, *Small Ramsey Numbers*, EJC DS1 rev #18; accepted interval 36–40, width 4, with the true value possibly any integer from 36 to 40.

## Scoring conventions (two modes; default is `solver_cubic`)

- `solver_cubic` (default in `judge.json`): the lower-bound curve is identical to the Solver version (N≤24 → 0; `((N−24)/11)³`, 35 → 1.0, ≥36 marked `record_broken` with no cap); the upper-bound mirror is `((56−N)/15)³`, 41 → 1.0, and ≤40 marked `record_broken` with no cap. In this mode, the N=14 sanity/oracle receives 0 (milestone baseline, valid=1), matching the sibling oracle's full N=24 graph (also baseline score 0).
- `alpha_milestone`: any non-vacuous proof passing all gates receives the α-milestone score 1.0; `record_matched` (35 / 41) = 1.0; `record_broken` (lower bound ≥36 / upper bound ≤40) continues above 1 using the same cubic curve, without a cap.
- One difference from pilot r55: because that pilot request specified “sanity should receive full credit,” it once defaulted to `alpha_milestone`. This task follows the instruction “share scoring anchors with the Solver sibling version,” so its default is `solver_cubic`; `alpha_milestone` remains available as a one-switch option (`judge.json` `score_mode`).
- **`native_decide` is allowed** (a key difference from the pilot; the axiom allowlist is propext / Classical.choice / Quot.sound / Lean.ofReduceBool / Lean.trustCompiler; the lexical gate bans only `axiom` / `sorryAx`, while the pilot also banned `native_decide`). Reason: kernel `decide` is already slow at small N when the two colors are asymmetric, so the only plausible path for checking candidates at record scale is `native_decide`. The authors explicitly accept its reliability cost (`trustCompiler`).
