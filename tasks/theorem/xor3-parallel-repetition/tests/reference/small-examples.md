# Executable Small Examples — `lean-xor3-parallel-repetition` (BBKLM25)

This record contains executable checks of definition-layer predicates (one of three fidelity checks), along with the script and original results. Because no Lean toolchain is available locally, the examples use a parallel Python implementation rather than `native_decide`.

## Method and artifacts

- Script: `small_examples.py` (pure Python + cmath; distributions, joint distributions, winning probability, value, embeddings, non-binary embeddings, bipartite incidence graph, disk embeddability, characters, sum-zero distributions, Freiman homomorphisms, and lifting equations all mirror the shipped definitions).
- Run command: `python3 small_examples.py`;, all 16 checks passed.

## Checklist

Each row describes the expected behavior of one predicate on a small example and the computed result.

| # | Check | Result |
|---|---|---|
| E1 | `pi3` (joint distribution) for the GHZ problem: all 16 atoms have probability 1/16, summing to 1 | Matches |
| E2 | GHZ game (µ is uniform on the sum-zero elements of Z_2³; t = x∨y∨z mod 2). Exhaustively enumerate all strategies: `val = 3/4`, matching §1.1 of the paper | Matches (0.75) |
| E3 | Integer embeddings of the GHZ-problem distribution (exhaustive over range [−3,3]) are all constant; `NoZEmbedding` holds | Matches |
| E3b | The two-cluster distribution (supp = {(0,0,0),(1,1,0)}) has a nonconstant integer embedding; the predicate distinguishes it | Matches |
| E4 | Under the bipartite-incidence interpretation (`BiAdj`), the GHZ distribution is pairwise connected | Matches |
| E4b | The two-cluster distribution is not pairwise connected | Matches |
| E5 | GHZ tensor T = (−1)^{x∨y∨z} is decomposable on the closed disk (A(x)=iˣ in §2.1.2 of the paper); solvability confirmed by a rational-phase linear-system criterion | Matches |
| E5b | A single-point tensor with phase 1/3 is decomposable (sanity check: a single point is always decomposable) | Matches |
| E6 | A constant map is a 2-fold Freiman homomorphism on Z_2 | Matches |
| E6b | On Z_4, f = {0↦0,1↦1,2↦2,3↦0} is refuted by the relation 1+1 = 0+2 | Matches |
| E7 | GHZ lifting equation: x+y+z = 2·(x∨y∨z) (mod 4) holds pointwise on all four support points (key observation from §2.1.2 of the paper) | Matches |
| E7b | No lift exists for N=1 (`val = 3/4 < 1`, so there is no perfect strategy) | Matches |
| E8 | `sumZeroDist`: over Z_2 and Z_3 the probabilities sum to 1 and support size is exactly |A|² | Matches |
| E9 | **Numerical check of c1's arithmetic identity:** For the GHZ game and specific strategies (f = identity, g = h = 0), compute both sides pointwise for n = 1 and n = 2. Winning probability as a real equals the character average as a complex value (error < 1e-9), checking c1's sign convention (positive F/G/H, negative T_S) and normalization factor m^{−n}. | Matches (n=1: 0.75; n=2: 0.5625; both sides agree) |

## Notes

- Exhaustive search for integer embeddings in E3 is bounded to [−3,3]. The absence of a Z-embedding for GHZ also has a pointwise linear-equation proof: subtracting pairs among the four equations forces each of the three maps to be constant; see §5 of concept-ledger.
- The E5 criterion reduces “disk-valued” to phase (the modulus must be 1 for the product to equal 1), then solves modulo 1 as a rational-phase linear system. This matches `NonembeddableD` item by item (A/B/C have modulus ≤ 1 and product identically 1, so their modulus is constantly 1).
