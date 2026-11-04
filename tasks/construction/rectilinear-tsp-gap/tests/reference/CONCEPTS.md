# Concept crosswalk: Lean identifiers in rectilinear-tsp-gap-lean-open ↔ literature definitions ↔ Solver sibling predicate

This document maps from every mathematical concept in the fixed part of this task's definition layer (`environment/app/Task/Basic.lean`) to its source, and an item-by-item alignment with the Solver sibling checker predicate in `construction-conjecture-solver/tasks/rectilinear-tsp-gap`.

## Source anchors

- Per-n record anchors (11: 17/15, 12: 8/7, 13: 23/20, 14: 52/45, 15: 29/25, 16: 64/55; the 1.0 anchor is the maximum in the window, 64/55): Xianghui Zhong, *Lower bounds on the integrality ratio of the subtour LP for the traveling salesman problem*, Discrete Applied Mathematics 365 (2025), 109–129 (open access; arXiv:2102.04765). Transcription and review are recorded in sibling `rectilinear-tsp-gap/PROVENANCE.md`.
- Values closed by exhaustive search for n≤10: Section 4 + Table 1 of the same paper; the ratio is always 1 for n≤5.
- Upper-bound anchor 3/2: Wolsey's classic analysis, as cited in Section 4 of Zhong's paper.
- Certificate structure (LP feasible point + Held–Karp potential table + assembly theorem): copied from the definition layer of the sibling pilot `tsp-gap-lean-open`; its verified proofs (potential lemma, LP/tour/assembly theorems) are preserved byte for byte.

## Predicate alignment table (Lean fixed layer ↔ Solver sibling checker.py)

each row compares one Lean definition with the corresponding literature concept and Solver checker condition.

| Lean identifier | Literature concept | Solver sibling counterpart | Deliberate difference and explanation |
|---|---|---|---|
| `certN` (2≤n≤16; milestones 11≤n≤16) | Number of points n | `MIN_N..MAX_N = 2..16`, scoring window `SCORE_MIN_N..MAX_N = 11..16` | Exact match. |
| `certPX certPY : Fin certN → ℤ` (integer point coordinates) | A set of rational points in the plane | `parse_points`: exact decimal parsing with `Fraction(str(v))` | Multiplying rational point coordinates by a common denominator yields integer points; all distances scale by the same factor, leaving the gap unchanged. Thus the Solver's exact rational parsing corresponds on the Lean side to “integer coordinates are rational coordinates.” The instance classes correspond point by point. |
| `PointsDistinct px py` | Points are pairwise distinct | `points must be distinct` check in `parse_points` | Exact match. |
| (No corresponding assumption) | — | Coordinate bound `\|x\|,\|y\| ≤ 10^6` | The sibling's bound is an input-format safety limit. Scaling does not change the gap, so it does not affect the mathematical claim “there is a rational point set with gap ≥ α.” The Lean version omits it for this reason. |
| `l1Cost px py u v = (px u − px v).natAbs + (py u − py v).natAbs` | L1 (Manhattan) distance | `l1_matrix`: `abs(xa−xb) + abs(ya−yb)` (exact Fraction arithmetic) | Same semantics: on integer points, both sides are the same natural number. Lean uses ℕ, matching the certificate machinery (natural-number costs). |
| `metricCost_l1` (proved in the fixed layer) | The triangle inequality for L1 holds automatically | Checker comment: “triangle inequality comes for free — submit raw points” | Both versions take raw points, not a distance matrix, as the instance. Lean proves this fact as a theorem rather than checking it for each input. |
| `LPFeasible x` | Feasible solution to the subtour-elimination LP: x(δ(v))=2, x(δ(S))≥2, 0≤x≤1 | `tsp_gap.opt_lp`: cutting planes + exact Stoer–Wagner minimum cut, same LP | Undirected edge variables are represented by a symmetric matrix on ordered pairs; the degree constraint is row sum 2. Cut constraints are checked for every nonempty proper subset, including singletons; singleton cuts follow from degree constraints, making this equivalent to the literature's 2≤\|S\|≤n−2 convention. Self-loops are also explicitly excluded. Byte-for-byte the same as the pilot. |
| `LPValue cost x` | LP objective c·x | Return value of `opt_lp` | The ordered-pair sum counts each undirected edge twice, so the definition divides it by 2, matching the literature's objective. Byte-for-byte the same as the pilot. |
| `certW` (potential table) | Dual certificate for Held–Karp DP | `opt_tour`: NumPy implementation of the same recurrence | Any table satisfying `W 1 0 = 0` and `W mask j ≤ W (mask\{j}) i + cost i j` gives a tour lower bound; it need not attain the optimum. States unused by the inequalities receive a large sentinel value. Byte-for-byte the same as the pilot. |
| `pot_inv`, `tour_lb_of_potOk` | Soundness of the potential certificate: a valid potential table implies every tour has cost ≥ T | — (the sibling computes the optimal DP value directly) | Proved in the fixed layer by induction over the visited set. Byte-for-byte the same as the pilot. |
| `GapLB cost α` | Per-instance lower bound on the integrality gap: OPT_tour / OPT_LP ≥ α | `g = tour / lp` (gap) | The LP is a minimization problem, so a feasible point gives OPT_LP ≤ c·x. Thus OPT_tour/OPT_LP ≥ T/(c·x) ≥ α; no LP duality is needed. Byte-for-byte the same as the pilot. |
| `GapBound m px py α` | Packaged statement: 2≤m≤16, point-set assumptions, and gap lower bound α | Valid instance (`premise_ok`) and gap = α | The pilot's `MetricCost cost` conjunct is replaced by `PointsDistinct px py` (equivalent via `metricCost_l1`). |
| `gapLB_of_cert` | Assembly theorem: integer certificate y/D, potential table, and integer inequality p·(c·y) ≤ q·2·T·D imply `GapLB cost (p/q)` | — | The integer inequality is equivalent to (p/q)·(c·y)/(2D) ≤ T. Byte-for-byte the same as the pilot. |
| `claimedAlpha`, `main` | Submission interface | `claimed_gap` (compared with the recomputed value) | The scorer recognizes only the interface names. The type of `main : GapBound certN certPX certPY claimedAlpha` guarantees the instance is valid. The sibling compares `claimed_gap` using tolerance 1e-6; the Lean version proves the full statement in the kernel and has no tolerance. |

## Scoring curve and anchors (shared with the sibling version)

- `reward = max(0, (α − 1) / (142/121 − 1))`, uncapped: baseline 1 = gap for collinear equally spaced points (exactly 1, score 0); 1.0 anchor = maximum family value in the window, 142/121 (n=16, I²_{2,6,2}; anchor corrected); at α = 4/3 the score is exactly 55/27 ≈ 2.037.
- Reference values: 17/15 → 242/315 ≈ 0.768; 8/7 → 121/147 ≈ 0.823; 23/20 → 121/140 ≈ 0.864; 22/19 → 121/133 ≈ 0.910; 7/6 → 121/126 ≈ 0.960; 142/121 → 1.0.
- Flags: `record_broken` (α strictly exceeds the family value for that n; record lines exist only for 11..16, since n≤10 is closed); `beyond_4_3` (α > 4/3, which disproves the rectilinear case and therefore the 4/3 conjecture for metric TSP).
- Difference from the pilot curve: the pilot baseline is 11/10 (Petersen value) and standing value 76/61; this task uses baseline 1 (collinear floor) and standing value 142/121. These match the sibling checker.py constants BASELINE/STANDING ().

## Three structural differences from the pilot (all recorded)

1. **Instance form**: metric-cost matrix (`certCost`) → integer point set (`certPX`/`certPY`) plus L1 cost derived in the fixed layer. The `GapBound` signature changes accordingly; `metricCost_l1` supplies the metric assumption once as a theorem instead of requiring it for each instance.
2. **Allow `native_decide`**: the pilot bans `native_decide` lexically; this task removes it from the banned-token list (the five-axiom allowlist propext / Classical.choice / Quot.sound / Lean.ofReduceBool / Lean.trustCompiler is unchanged). Reason: at the top of the n=16 scoring window, cut and potential checks enumerate 2^16 masks (about 10^7 checks), which kernel `decide` cannot handle. The oracle uses Arrays, builds the DP table inside Lean, and runs it through `native_decide`.
3. **n window**: [2,20] (milestones 15..20) → [2,16] (milestones 11..16), matching the sibling scoring window.

## Checks completed

- Sibling known-bound check: per-n family values, correction of the coordinate formula typo (height of Y-line i/k), correction of the n=8 label in Table 1, and all five closed values were reproduced exactly. This task uses those results in its statement.
- Oracle instance (`I²_{1,8,1}` scaled to integer coordinates by ×22): all certificate conditions were checked in Python first (including y symmetry/diagonal/upper bound/degree/65,534 cuts, potential inequalities, hT, and gap arithmetic `64·440 = 55·2·128·2 = 28160`). The sibling scoring stack `tsp_gap.py` recomputed the same scaled instance: OPT_LP=110, OPT_tour=128, gap=64/55.
- Open sandbox checks: compile the fixed layer, confirm the stub scores 0, score the complete oracle and measure `native_decide` runtime, and confirm mutation/replacing proof with `sorry` scores 0.
