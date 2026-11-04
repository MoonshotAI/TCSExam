# Executable Small Examples — Numerical Checks of the `explicit-ramsey-graph-log` Definition Layer and Special Cases

Small hand-checkable or enumerable cases exercise the Paley-graph and clique-number definitions and record the actual output; they serve as unit tests for the definition layer.

- Script: `tests/reference/small_examples.py` (pure Python standard library; exact algorithms: branch-and-bound maximum clique plus exhaustive search).
- Algorithm regression tests: `src/tcsexam/tests/test_paley_small_examples.py` compares all simple graphs with at most five vertices against independent subset enumeration, checks all 720 relabelings of a six-vertex example, and exhaustively checks the small Paley graphs and their complements.

## Design notes

- Clique number / independence number is expressed in Lean using `CliqueFree` (“contains no k-clique”); an exact clique number is pinned down by `CliqueFree (k+1)` together with `¬ CliqueFree k`. Python computes the maximum clique size directly.
- Paley graphs are self-complementary (multiplication by a nonsquare gives an isomorphism P_q ≅ P_qᶜ), so ω = α. The Python script computes each independently rather than assuming this; the row-by-row equality gives independent confirmation of self-complementarity on these examples.

## Part 1: Paley graphs for small primes (numerical basis for special case a)

Actual output of `small_examples.py` (exact maximum clique by branch-and-bound):

| q | ω(P_q) | α(P_q) | ⌊log₂ q⌋ | ω / ⌊log₂ q⌋ |
|---|---|---|---|---|
| 5 | 2 | 2 | 2 | 1.000 |
| 13 | 3 | 3 | 3 | 1.000 |
| 17 | 3 | 3 | 4 | 0.750 |
| 29 | 4 | 4 | 4 | 1.000 |
| 37 | 4 | 4 | 5 | 0.800 |
| 41 | 5 | 5 | 5 | 1.000 |
| 53 | 5 | 5 | 5 | 1.000 |

Each row is a prime q ≡ 1 (mod 4). The last column gives the finite ratio ω/⌊log₂ q⌋. For the current polylogarithmic bound, these finite cases already satisfy ω = α ≤ ⌊log₂ q⌋+1, corresponding to exponent k = 1. These computations illustrate the definitions and do not prove the quantified conjecture.

## Part 2: Witness for R(4,4) > 17 and the scale of G(N,1/2) (numerical basis for special case b)

- Paley(17): ω = 3, α = 3. Exhaustively checking all C(17,4) = 2380 four-element subsets finds no 4-clique and no 4-independent set (script output `4-clique: False, 4-independent-set: False`). This is the existence witness for slot b; the Lean-level check uses the reference proof for slot b (the `powersetCard`-based `decide` route).
- Samples from G(N,1/2) (seed 20260904, three samples per size):

| N | Sample | ω | α | 2·log₂ N |
|---|---|---|---|---|
| 8 | 0 | 3 | 3 | 6.00 |
| 8 | 1 | 4 | 3 | 6.00 |
| 8 | 2 | 4 | 4 | 6.00 |
| 16 | 0 | 5 | 6 | 8.00 |
| 16 | 1 | 4 | 5 | 8.00 |
| 16 | 2 | 4 | 5 | 8.00 |
| 32 | 0 | 6 | 6 | 10.00 |
| 32 | 1 | 7 | 7 | 10.00 |
| 32 | 2 | 6 | 6 | 10.00 |
| 64 | 0 | 8 | 8 | 12.00 |
| 64 | 1 | 8 | 8 | 12.00 |
| 64 | 2 | 8 | 7 | 12.00 |

The scale in Erdős 1947 is ~2·log₂ N; for these small N, sampled ω and α stay below that scale (factor about 0.5–0.7), consistent with the existence of logarithmic-size cliques. This part is sampling only and is not formalized in Lean.

## Part 3: Boundary cases (numerical basis for special case c)

- K₅: ω = 5, α = 1 (script output agrees with the expected values).
- Empty graph on 5 vertices: ω = 1, α = 5 (script output agrees with the expected values).
- 0-clique: the empty set is a 0-clique in every graph, so no graph satisfies `CliqueFree 0`. This follows directly from the Lean definition (`IsNClique 0 ∅` holds); Python does not check it. The reference proof for slot c checks it at Lean level.

## Search regression case

On vertices 0 through 4, the edges `{0,3}`, `{0,4}`, `{1,2}`, `{2,3}`,
and `{3,4}` contain the triangle `{0,3,4}`, so the clique number is 3.
This example exercises the distinction between greedy-color order and
vertex-number order. The search recurses on the remaining candidates
adjacent to the chosen vertex; candidates are removed in greedy-color
order as each branch finishes. An additional vertex-number cutoff can
discard members of that triangle.

## Relation to the Lean definitions

`CliqueFree` expresses the absence of a clique of a specified size.
For finite examples, unfold it with `cliqueFree_def` before using `decide`.
The task's `qrBool` computes quadratic residues, and
`isSquare_iff_qrBool` connects that computation to Paley adjacency.
Translation symmetry lets a clique be translated so that it contains 0;
the remaining vertices then lie in the neighborhood of 0. This reduces
the finite checks needed for the q = 13 and q = 17 examples.
