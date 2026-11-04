# Independent Retranslation: The Optimal Competitive Ratio for Online Bin Packing

This record derives a formalization draft from the literature without consulting the shipped Lean file, then compares the two component by component. It is the third fidelity record (independent retranslation).

- Source: abstract-level statements from the two papers establishing the bounds (). The ESA 2018 upper-bound paper and the Algorithmica 2021 lower-bound paper use consistent formulations of the problem and of “asymptotic competitive ratio.”

## Step 1: Source statements (the two abstracts)

ESA 2018 (upper-bound paper): “items of positive sizes no larger than 1 are presented one by one to be packed into subsets called bins of total sizes no larger than 1, such that every item is assigned to a bin before the next item is presented”; its result is an algorithm AH with asymptotic competitive ratio at most 1.57829.

Algorithmica 2021 (lower-bound paper): “We improve the lower bound on the asymptotic competitive ratio of any online algorithm for bin packing to above 1.54278.”

## Step 2: Natural-language refinement (resolving ambiguities)

- **Instance:** a finite sequence of items, each with size in (0,1]; bin capacity is normalized to 1.
- **Packing:** assign each item to a bin so the sum of item sizes in every bin is ≤ 1. Feasibility is part of the definition.
- **Offline optimum OPT(I):** the minimum number of bins needed for a feasible packing of instance I.
- **Online algorithm:** items arrive in order; the bin assignment of item i is fixed when it arrives and cannot later be changed. The algorithm cannot see future items. Its output must be a feasible packing.
- **Cost A(I):** the number of bins opened (used) by algorithm A on instance I.
- **Asymptotic competitive ratio:** the asymptotic ratio of A is the infimum of all r for which there is a constant C such that, for every instance I, A(I) ≤ r·OPT(I) + C. The additive constant is precisely what makes the ratio “asymptotic.”
- **R*:** the infimum of the asymptotic ratios of all deterministic online algorithms. The known bounds are 1.54278 ≤ R* ≤ 1.57829; the open problem is to improve either side.

## Step 3: Independently drafted types

```
instance  := l : List ℝ, valid := ∀ x ∈ l, 0 < x ∧ x ≤ 1
packs(l, k) := ∃ f : Fin l.length → Fin k, ∀ b, ∑_{i : f i = b} l_i ≤ 1
OPT(l)    := min { k | packs(l, k) }              -- nonempty (put each item in its own bin)
OnlineAlg := structure { assign : List ℝ → List ℕ; |assign l| = |l|;
              prefix : l₁ is a prefix of l₂ ⇒ first |l₁| assignments of assign l₂ = assign l₁;
              feasible : ∀ valid l, ∀ b, ∑_{i : assign(l)_i = b} l_i ≤ 1 }
cost(A,l) := (maximum bin index in assign l + 1) (0 for the empty list)
Bound(A,r) := ∃ C : ℝ, ∀ valid l, cost(A,l) ≤ r·OPT(l) + C
R*        := inf { r : ℝ | ∃ A, Bound(A,r) }
conj      := R* ≤ 1.56
refuted   := ¬ (R* ≤ 1.56)
```

## Step 4: Component-by-component comparison with the shipped version

| Component | Draft | Shipped version | Finding |
|---|---|---|---|
| Instance | `List ℝ`, with sizes in (0,1] | `ValidInstance` | Match |
| Packing | Assignment function + each bin's total size ≤ 1 | `PacksIn` | Match |
| OPT | Minimum feasible number of bins | `optNumber` (`sInf` of a set of naturals, with attainment proved) | Match (`sInf` equals the least natural when the set is nonempty; see deviation 4 in `concept-ledger`) |
| Online algorithm | Prefix-consistent, always-feasible assignment | `OnlineAlg`, with fields of the same names | Match |
| Cost | Maximum bin index + 1 | `costOf` / `algCost` | Match (accounting difference explained in deviation 3 of `concept-ledger`) |
| Asymptotic bound | ∃ C, ∀ l, cost ≤ r·OPT + C | `AsympBound` | Identical |
| R* | Infimum of achievable ratios | `RStar := sInf ratioSet` | Match (inf_A inf{r} = inf{∃A}; see the R* row in `concept-ledger`) |
| `conj` / `refuted` | R* ≤ 1.56 / negation | Same names | Match |

There are no disagreements. The two packaging choices—prefix-consistent assignments versus decision functions, and maximum bin index + 1 versus number of nonempty bins—preserve semantics. See deviations 1/3 in `concept-ledger` for the arguments.

## Notes

- The draft and shipped version independently chose the same online-algorithm formalization (prefix-consistent assignments). This is not coordination: it directly expresses “irrevocable decisions made without knowing the future.” A decision-function form would need extra state to encode past decisions, making the definition layer heavier while preserving the same semantics.
- The papers do not discuss the empty instance. Here OPT = 0 and cost = 0, so every bound holds trivially and R* is unaffected.
- Quantifier order: the true form of `conj` is “∃ algorithm A, ∃ C, ∀ instances, cost ≤ 1.56·OPT + C,” which follows directly from an upper-bound proof. `R* ≤ t` via `csInf_le` requires an achievable ratio ≤ t, matching that form. The true form of `refuted` is “∀ algorithms A, ∀ r ≤ 1.56, ∀ C, ∃ instance with cost > r·OPT + C,” the standard lower-bound form. `t < sInf ratioSet` via `lt_csInf` requires every achievable ratio to be > t, matching that form.
