# Executable Small Examples — Exact Numerical Checks for Special Cases of `bin-packing-mirup`

Pure-Python checks (standard library, exact rational arithmetic) verify numerical facts behind the task's three special-case checkpoints and record the original output.

- Script: `tests/reference/verify_mirup.py` (standard library only, about 25 seconds); original output saved at `verify_mirup.out` ().

## Method

Each instance has item sizes l_1..l_n and capacity L, all positive integers; equivalently, normalize item sizes to (0,1] and capacity to 1. Volumes in the tables below use normalized sizes.

- A pattern is a subset of items whose total size is ≤ L. The pattern LP assigns a nonnegative weight to each pattern so that every item is covered at least once, minimizing the total weight. The script solves the dual LP on **maximal patterns** (maximize Σw_i subject to Σ_{i∈p} w_i ≤ 1 for every pattern) by exact rational simplex (Bland's rule). It reads a primal solution from shadow prices of the optimal dual tableau, then substitutes it back to verify dual feasibility, primal feasibility, and equality in strong duality; the script asserts all three checks.
- OPT is computed by exact depth-first search (items sorted in descending size; branches with equal loads are pruned as symmetric).
- Lean correspondence: patterns ↔ `patterns l L`; pattern-LP value ↔ `lpVal l L`; OPT ↔ `optNumber l L hle`; natural-number dual/primal certificates (X, W and common denominator D) ↔ applications of pinned-zone lemmas `lpVal_le_of_natCover` / `le_lpVal_of_natDual` (the Lean certificates are the certificates below multiplied by their common denominator).

## Numerical results

Each row is one instance; vol is normalized total volume; LP is the exact pattern-LP value; OPT is the integer optimum. IRUP means OPT = ⌈LP⌉ (the integer-round-up property); MIRUP means OPT ≤ ⌈LP⌉+1.

### Special case (a): equal-size items (checkpoint `mirup_uniform`)

| c/L (normalized size) | n | m = ⌊L/c⌋ | LP = n/m | OPT = ⌈n/m⌉ | Conclusion |
|---|---|---|---|---|---|
| 1/3 | 7 | 3 | 7/3 | 3 | Holds |
| 2/5 | 9 | 2 | 9/2 | 5 | Holds |
| 17/50 | 5 | 2 | 5/2 | 3 | Holds |
| 1/2 | 6 | 2 | 3 | 3 | Holds |
| 3/4 | 5 | 1 | 5 | 5 | Holds |

For equal-size instances, LP = n/m and OPT = ⌈n/m⌉, so IRUP (and hence MIRUP) holds. Note that OPT ≠ ⌈total volume⌉ (e.g. c = 17/50, n = 5: volume 17/10, ⌈volume⌉ = 2 < 3 = OPT), so the checkpoint does not use a volume-based formulation.

### Special case (b): exact values for small instances (checkpoint `mirup_small`)

| Instance (integer form) | Normalized | vol | LP | OPT | Notes |
|---|---|---|---|---|---|
| instB1: sizes (6,4,4,3,3), capacity 12 | (1/2, 1/3, 1/3, 1/4, 1/4) | 5/3 | 9/5 | 2 | LP is strictly between the volume and OPT (witness of a nonintegral LP) |
| instB2: sizes (7,7,7,7), capacity 12 | (7/12 ×4) | 7/3 | 4 | 4 | No two items fit together; all patterns are singletons, so LP = OPT = n, much larger than volume |
| instB3: sizes (3,3,2,2,2), capacity 6 | (1/2, 1/2, 1/3, 1/3, 1/3) | 2 | 2 | 2 | Both bins are exactly full, so LP = OPT = volume |

Lean proofs use certificates of the same kind as the script (values below are normalized; Lean takes a common denominator D to obtain natural-number certificates):

- instB1: primal weights {0,1}:1/5, {0,2}:1/5, {1,2,3}:2/5, {1,2,4}:2/5, {0,3,4}:3/5 (total 9/5, every item covered exactly once; Lean D = 5 and X stores the numerators); dual w = (3/5, 2/5, 2/5, 1/5, 1/5) (total 9/5; Lean D = 5 and W = (3,2,2,1,1)).
- instB2: primal assigns weight 1 to each of the four singleton patterns (D = 1); dual w = (1,1,1,1) (D = 1).
- instB3: primal {0,1}:1, {2,3,4}:1 (D = 1); dual w = (1/2, 1/2, 1/3, 1/3, 1/3) (total 2; Lean D = 6 and W = (3,3,2,2,2)).
- OPT lower bounds for all three: instB1/instB3 cannot fit in one bin (volume > capacity, and `¬ PacksIn _ _ 1` can be decided by kernel enumeration); instB2 has four pairwise-incompatible items (pinned lemma `le_optNumber_of_pairwise_incompatible`).

### Random checks (locating these results relative to “small-instance exhaustive verification”)

- 3,000 random instances with n ≤ 6 and sizes k/12: 0 MIRUP violations and 0 IRUP failures.
- 2,000 random instances with n ∈ 7..9 and sizes k/18: 0 IRUP failures, consistent with the complete classification of Kartak et al. 2015 that every instance with ≤ 9 items satisfies IRUP.

### Special case (c): an instance tight at +1 (checkpoint `mirup_tight`)

instC: sizes (4,6,6,9,16,29,32,37,40,62), capacity 81 (one of the non-integral instances appearing at n = 10 in Table 1 of Kartak–Kurz–Ripatti–Scheithauer 2015; all instances with ≤ 9 items are integral, so this follows the smallest-scale counterexample convention):

- **LP = 3 (exactly):** primal certificate has seven patterns with weight 1/3 and one with weight 2/3 ({0,4,5,6}, {1,3,5,7}, {1,2,6,7}, {1,2,5,8}, {3,6,8}, {0,7,8}, {0,2,3,9} each have weight 1/3; {4,9} has weight 2/3). Every item is covered exactly once, total weight 3 (Lean D = 3 and X numerators 1/1/1/1/1/1/1/2). Dual certificate w = (0,0,0,0,0,1/2,1/2,1/2,1/2,1), total 3 (Lean D = 2 and W = (0,0,0,0,0,1,1,1,1,2); the five larger items carry all dual weight, with pairwise sums ≤ 1).
- **OPT = 4:** packing {16,62}, {4,37,40}, {6,9,29,32}, {6} (loads 78, 81, 76, 6). To prove three bins are impossible, count unused capacity: total size is 241 = 3·81 − 2, so three bins have at most 2 units of total slack. If the bin containing 62 has load ≤ 78, total load is at most 78+81+81 = 240, a contradiction. If its load is ≥ 79, its companion items (drawn only from sizes ≤ 19, namely {4,6,6,9,16}) have total size in [17,19]. No subset of {4,6,6,9,16} sums to 17 or 18; if the sum is 19, it must contain both 4 and 9 (three small `decide` checks). Thus the companion items in the other bin containing 40 can only come from {6,6,16,29,32,37}; every subset of this set summing to ≤ 41 has size ≤ 38, so that bin's load is ≤ 78. Total load is then at most 81+78+81 = 240, again a contradiction.
- Therefore OPT = 4 = ⌈LP⌉ + 1: IRUP fails, while MIRUP is tight on this instance (MIRUP itself holds, so this does not conflict with the main conjecture).

## Cross-checks

- LP ≥ volume holds for all instances (asserted by the script); likewise LP ≤ OPT (the dual certificate also lower-bounds OPT).
- For (a), LP = n/m agrees with the theoretical dual solution w ≡ 1/m. For instB1, the LP = 9/5 was recomputed by hand from the dual LP: three tight constraints—{1/2,1/4,1/4}, {1/2,1/3}, {1/3,1/3,1/4}—give w = (3/5, 2/5, 2/5, 1/5, 1/5).
- For instC, LP = 3 agrees with Δ_p = 1 in Table 1 of the paper (OPT − LP = 1). The two n = 9 instances with L = 104 in the same table were rechecked by this script as IRUP (LP = volume = 209/104, OPT = 3); see `mirup_numerics.out`.
