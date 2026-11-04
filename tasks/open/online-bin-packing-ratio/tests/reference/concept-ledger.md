# Faithfulness Review: The Optimal Competitive Ratio for Online Bin Packing

This note explains the task statement for readers comparing the mathematical definitions with the Lean source. The current scoring statements are `conj` and `refuted`; proving either earns full credit.

This review compares the literature statement about the optimal asymptotic competitive ratio for online bin packing with the Lean statement used by this task, and records every modeling choice and its rationale.

- **Sources:** Balogh–Békési–Dósa–Epstein–Levin, “A New and Improved Algorithm for Online Bin Packing,” ESA 2018 (LIPIcs.ESA.2018.5), for the upper bound; the same authors, “A New Lower Bound for Classic Online Bin Packing,” *Algorithmica* 83(7):2047–2062 (2021, arXiv:1807.05554), for the lower bound; item 5 of `online-dynamic-streaming.md`.
- **Released statement:** `environment/app/Task/Basic.lean`; it matches `tests/reference/Basic.lean` word for word.

## 1. Literature statement and Lean correspondence

The two papers use the standard one-dimensional online bin-packing model. Items of positive size at most 1 arrive one at a time. Each item must be placed, before the next arrives, into a bin whose total item size is at most 1; assignments cannot be changed. The goal is to minimize the number of bins. The asymptotic competitive ratio of an online algorithm A is the infimum of r such that there is a constant C with A(I) ≤ r·OPT(I)+C for every instance I, where OPT is the offline optimum. R* is the infimum of these ratios over all online algorithms. The known interval is 1.54278 ≤ R* ≤ 1.57829, and improving either endpoint would be a new result.

| Concept | Literature | Lean identifier in this task | Notes |
|---|---|---|---|
| Item / instance | A sequence of item sizes in (0,1]. | `l : List ℝ`; `ValidInstance l := ∀ x ∈ l, 0 < x ∧ x ≤ 1` | Capacity is normalized to 1, as in the ESA 2018 abstract: “items of positive sizes no larger than 1 ... bins of total sizes no larger than 1.” |
| Packing | Assign items to bins of capacity 1. | `PacksIn l k := ∃ f : Fin l.length → Fin k, ∀ b, ∑_{i: f i = b} l.get i ≤ 1` | Each bin’s total size is at most 1, pointwise. |
| Offline optimum OPT | Minimum number of bins. | `optNumber l := sInf {k : ℕ | PacksIn l k}` | For a valid instance the set is nonempty (`packsIn_self`) and the infimum is attained (`optNumber_spec`). |
| Online algorithm | An algorithm that assigns each arriving item immediately and irrevocably. | `OnlineAlg` structure: `assign : List ℝ → List ℕ` plus `length_eq`, `prefix_consistent`, and `feasible`. | See deviations 1–3. |
| Algorithm cost A(I) | Number of bins used by A on I. | `algCost A l := costOf (A.assign l)`; `costOf asg := asg.toFinset.sup (· + 1)`. | See deviation 4. |
| Asymptotic competitive ratio | The infimum of r for which there is C with A(I) ≤ r·OPT(I)+C for every I. | `AsympBound A r := ∃ C : ℝ, ∀ l, ValidInstance l → (algCost A l : ℝ) ≤ r * optNumber l + C` | Exactly the additive-constant definition of “asymptotic competitive ratio” in both papers. |
| R* | Infimum of the asymptotic ratios over all online algorithms. | `RStar := sInf ratioSet`; `ratioSet := {r | ∃ A, AsympBound A r}`. | `inf_A inf{r : A has the bound} = inf{r : some A has the bound}`; both take the infimum of the same set. |
| Main `conj` statement | Improved upper-bound direction: R* ≤ 1.56. | `conj : RStar ≤ 1.56`. | 1.56 lies strictly inside (1.54278,1.57829); proving it improves the 1.57829 upper bound. |
| Main `refuted` statement | Improved lower-bound direction: R* > 1.56. | `refuted : ¬ RStar ≤ 1.56`. | Over the reals, ¬(a≤b) iff b<a; proving this improves the 1.54278 lower bound. |

## 2. Deviations and rationale

1. **Represent an online algorithm as a prefix-consistent packing function rather than a decision function.** In the literature, when item i arrives, the algorithm chooses a bin based on the items seen so far and earlier decisions; those earlier decisions are determined by the history. This task defines the algorithm directly as a packing assignment on the whole input, `assign : List ℝ → List ℕ`, and uses `prefix_consistent` to express that extending the input does not change assignments on its prefix—capturing irrevocability and lack of future knowledge. The forms simulate one another: folding a decision function over the input yields a prefix-consistent assignment, and each value of a prefix-consistent assignment depends only on the prefix, defining the corresponding decision function. This is the standard formalization of online algorithms and preserves the semantics pointwise.

2. **Make feasibility a field of the structure rather than a separate quantified condition.** In the literature, a packing algorithm is understood to output a valid packing. Here `feasible` (for every valid instance and bin, the total size assigned to it is at most 1) is a proof field of the structure. Thus quantifying over `A : OnlineAlg` automatically ranges only over feasible algorithms, matching the literature.

3. **Allow the empty sequence and define cost as “largest bin index + 1.”** The empty instance has OPT=0 and algorithm cost 0, a trivial case that does not affect R*. The cost counts every bin index opened, including skipped empty indices; the literature counts nonempty bins. Thus the task’s measure can be larger for an algorithm that skips indices. However, every natural algorithm family such as Next Fit, First Fit, and Harmonic uses consecutive indices 0,...,k−1, so both measures agree for the algorithms establishing the known bounds and R* is unchanged. Since nonempty-bin count is at most opened-bin count, this convention only strengthens an adversarial lower-bound construction that applies to every algorithm, so the direction is safe.

4. **Define OPT as `sInf` of a set of natural numbers without assuming computability.** For a valid instance the set is nonempty, since assigning each item to its own bin is feasible (`packsIn_self`); hence the infimum is attained (`optNumber_spec`, the minimum). For an invalid instance containing an item larger than 1, the set can be empty, in which case mathlib sets `sInf ∅ = 0`. The `ValidInstance` hypothesis excludes that degenerate case from all theorems.

5. **Quantify only over deterministic online algorithms.** `OnlineAlg.assign` is a function and has no randomness. The two bound papers use the deterministic-algorithm convention (“any online algorithm” in the abstract of the lower-bound paper by Balogh et al.). Lower bounds for randomized online algorithms are a separate question with separate literature and are outside this statement.

## 3. Distinction from nearby problems

- **bin-packing-mirup** (in the same proof-conjecture-lean repository) is the Scheithauer–Terno MIRUP conjecture: the integer optimum for offline bin packing differs from the rounded configuration-LP optimum by at most 1. It is an offline decision statement; this task concerns an online problem and a numerical value R* in the reals. They share only the basic definitions of an instance, `PacksIn`, and the optimum number of bins; their proof targets are entirely different.
- **Bounded-space online bin packing** is a variant with a known optimal Harmonic algorithm family. It appears only as background in the survey and is not part of this task.
- **Absolute competitive ratio** omits the additive constant (the same authors have a separate optimal absolute-ratio result, SODA 2015). This task uses the asymptotic convention from the two cited papers, so `conj`/`refuted` and the known bounds use the same notion.

## 4. Known frontier

- Upper bound 1.57829 (Balogh–Békési–Dósa–Epstein–Levin, ESA 2018, LIPIcs.ESA.2018.5, AH algorithm); the previous best was 1.58889 (Harmonic++, Seiden 2002).
- Lower bound 1.54278 (same authors, *Algorithmica* 83(7):2047–2062, 2021; arXiv:1807.05554); earlier bounds were 1.54037 (Balogh et al. 2012) and 1.54015 (van Vliet 1992).
- Evidence that the bounds have not moved: the 2025 arXiv:2505.09321 paper says “This is the currently best lower bound” (referring to 1.54278) and “The currently best-known strategy ... yields a ratio of approximately 1.57829.” Yao’s 1980 result, 1.5, is the starting lower bound in this line.
- against the LIPIcs paper page, arXiv abstract, Crossref bibliography, and the relevant passages of arXiv:2505.09321; all agree.
