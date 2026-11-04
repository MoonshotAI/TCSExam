# Concept crosswalk: Lean identifiers in tsp-gap-lean ↔ literature definitions

This document maps from each mathematical concept in the fixed part of this task's definition layer (`environment/app/Task/Basic.lean`) to its source, including deliberate differences from the literature's formulation.

## Source anchors

- Record values (n=15 → 11/9, n=16 → 27/22, n≤14 closed, maximum 17/14 at n=14): Cook, Hougardy, Petrich, *Extending Exact Integrality Gap Computations for the Metric TSP*, arXiv:2603.12995, Table 4.

- Values closed for n≤10: Benoit, Boyd, *Finding the exact integrality gap for small traveling salesman problems*, Math. Oper. Res. 33(4):921–931, 2008.
- Half-integral optimal-point conjecture (the gap is always attained at a half-integral point): Schalekamp, Williamson, van Zuylen (locator-only).
- Petersen graph sanity check: LP value 10, tour value 11, and integrality gap exactly 11/10, consistent with the literature and the Solver version's scoring library.

## Crosswalk

each row maps a Lean identifier to the corresponding TSP concept and records deliberate modeling choices.

| Lean identifier | Literature concept | Deliberate difference and explanation |
|---|---|---|
| `MetricCost cost` | Metric closure: a finite metric on a complete graph | Costs are natural numbers: symmetric, zero on the diagonal, positive off the diagonal, and satisfying the triangle inequality. Any rational metric can be scaled to an integer metric without changing the integrality gap, so this restriction is without loss of generality. |
| `IsTour l`, `tourCost cost l` | TSP tour (Hamiltonian cycle) and its cost | A tour is represented as a directed list starting at vertex 0. With symmetric costs, each undirected tour corresponds to two lists in opposite directions with equal cost, so “every list has cost ≥ T” is equivalent to saying the minimum undirected tour cost is ≥ T. |
| `LPFeasible x` | Feasible solution of the subtour-elimination LP (Held–Karp relaxation): degree constraints x(δ(v))=2, cut constraints x(δ(S))≥2, and 0≤x≤1 | The undirected edge variables are represented by a symmetric matrix on ordered pairs (`x u v = x v u`); the degree constraint is “each row sums to 2.” Cut constraints are checked for every nonempty proper subset, including singletons. The literature often writes 2≤\|S\|≤n−2; singleton cuts follow from the degree constraint, so the formulations are equivalent. Self-loops are also explicitly excluded. |
| `LPValue cost x` | LP objective value c·x | Summing over ordered pairs counts each undirected edge twice, so the definition divides the ordered sum by 2, matching the literature's objective value. |
| `certW` (potential table) | Dual certificate for Held–Karp dynamic programming (DP) | DP state f(S,j) is the minimum path cost from 0 that visits exactly S and ends at j. Any table satisfying `W 1 0 = 0` and `W mask j ≤ W (mask\{j}) i + cost i j` provides a lower bound; it need not be optimal. States not used by these inequalities (sets not containing 0, j∉S, or j=0 when S≠{0}) may be assigned a large sentinel value. |
| `pot_inv`, `tour_lb_of_potOk` | Soundness of the dual certificate: a valid potential table implies every tour has cost ≥ T | Proved in the fixed layer by induction over the visited set. |
| `GapLB cost α` | Per-instance lower bound on the integrality gap: OPT_tour / OPT_LP ≥ α | The LP is a minimization problem, and a feasible point gives OPT_LP ≤ c·x. Hence OPT_tour/OPT_LP ≥ T/(c·x) ≥ α. No LP duality is needed. |
| `GapBound n cost α` | Packaged statement for this task: 2≤n≤20, metric assumptions, and gap lower bound α | Milestones count only 15≤n≤20; small instances (such as Petersen at n=10) are sanity checks. For n≤14, the literature has closed the maximum at ≤17/14<11/9, below the milestone, so scoring α alone cannot award a false milestone. |
| `gapLB_of_cert` | Assembly theorem: integer certificate y/D, a potential table, and integer inequality p·(c·y) ≤ q·2·T·D imply `GapLB cost (p/q)` | The integer inequality is equivalent to (p/q)·(c·y)/(2D) ≤ T, that is, α·(c·x) ≤ T. |
| `certN / certCost / certY / certD / certW / certT / claimedAlpha / main` | Submission interface (the model supplies the instance and all witnesses) | The scorer recognizes only the interface names; the type of `main : GapBound certN certCost claimedAlpha` guarantees the instance is valid. |

## Checks completed

- The fixed layer compiled with leanprover/lean4:v4.33.0-rc1 + mathlib4 (style warnings only).
- The complete Petersen sanity proof in `solution/Basic.lean` compiled in about 85 seconds; `#print axioms main` listed only standard axioms. The scorer accepted it and assigned 0.45.
- Scorer self-checks: blank submission scores 0 (lexical `sorry` rejection), inserted `axiom` is caught, and milestone mappings pass unit checks at each tier (11/9→1.0, 27/22→1.1, above-record result marked `record_broken`, n=20 theta marked `beyond_table4` without a record label).
- Open check: kernel-checking time for full certificates at n=15/16 has not been measured. This cost is left to the model; the statement gives a verification budget and representation suggestions.
