# Faithfulness Review: The Bin-Packing MIRUP Conjecture

This note explains the task statement for readers comparing the mathematical definitions with the Lean source. The current scoring statements are `conj` and `refuted`; proving either earns full credit.

This document compares the conjecture’s plain-language statement and sources with the Lean identifiers used by this task, and records the design choices and their rationale.

- **Survey:** approximation-inapproximability-pcp.md §5 (bin-packing-mirup).
- **Sources:** Kartak–Kurz–Ripatti–Scheithauer, Discrete Applied Mathematics 2015 (arXiv:1405.5988; abstract and Table 1 checked); Borges et al., arXiv:2305.15291 (2023, evidence that the conjecture remains open, via the survey).
- **Released statement:** environment/app/Task/Basic.lean (namespace BinPackingMIRUP).

## 1. Plain-language statement and correspondence

The MIRUP conjecture (Scheithauer–Terno 1995) says that for every one-dimensional bin-packing instance I, with positive integer item sizes and bin capacity and each item no larger than the capacity, the integer optimum OPT(I) and the Gilmore–Gomory configuration-LP optimum LP(I) satisfy OPT(I)≤⌈LP(I)⌉+1.

| Component | Literature | Released Lean statement | Notes |
|---|---|---|---|
| Instance | Positive integers: item sizes l₁,...,lₙ and capacity L, with lᵢ≤L (Kartak et al. write (n,L,l)). | l : Fin n→ℕ, L : ℕ, hpos : ∀i, 0<l i, hle : ∀i, l i≤L. | Another common convention uses rational sizes in (0,1] and capacity 1. Scaling all sizes by 1/L makes the forms equivalent (decisions 1 and 2). |
| Pattern | A combination of items that fits in one bin. | IsPattern l L p := ∑ i∈p, l i≤L, with p : Finset (Fin n). | For BPP each item has demand 1, so a pattern is a subset; agrees with Kartak et al.’s proper pattern (aᵢ≤bᵢ) when b≡1. |
| Configuration LP | Minimize Σxₚ subject to xₚ≥0 and each item covered at least once. | lpVal l L : ℝ is the infimum of total rational fractional-cover weight (IsFracCover plus sInf). | Finite LP with rational data; the infimum is attained, so this is the usual LP optimum (decision 3). The LP value is invariant under scaling; the integer and (0,1] formulations have the same LP value. |
| Integer optimum OPT | Minimum number of bins. | optNumber l L hle : ℕ is the least k for which PacksIn l L k. | PacksIn means an assignment to k bins with load at most L in each. n bins always suffice (packsIn_self), so the minimum is well-defined. |
| Conjectured inequality | OPT(I)≤⌈LP(I)⌉+1. | optNumber l L hle ≤ Nat.ceil (lpVal l L)+1. | LP≥0, and Nat.ceil matches the integer ceiling in the literature. |
| Quantifiers | Every instance. | ∀ {n} (l : Fin n→ℕ) (L : ℕ) (hpos) (hle), …. | At n=0 the empty instance has OPT=0 and satisfies the inequality trivially; including it is harmless. |

## 2. Design decisions

1. **Use BPP (an item list with unit demand), not general CSP (a demand vector).** The literature conjectures MIRUP for both CSP and BPP; Borges et al. 2023 write, “It is conjectured that MIRUP holds for all instances of the CSP and BPP.” BPP is the standard special case and remains open itself. Kartak et al.’s full classification is by number of items: all instances with at most 9 items are IRUP, and nonintegral cases start at 10 items. The BPP form also gives the cleanest formalization, since a pattern is a subset; the task follows this scope from the survey.

2. **Use integer item sizes and integer capacity, not rational sizes in (0,1].** There are two reasons. (i) This is the literature’s native representation (Kartak et al. write (n,L,l)). (ii) It matters computationally: kernel decide cannot compute rational arithmetic. Rat.normalize calls Nat.gcd, which is well-founded recursion and does not reduce in the kernel; probes confirmed that decide fails on Nat.gcd 7 12=1 and (7/12:ℚ)≤1. In the integer form, pattern checks (Σl i≤L) and packing feasibility are natural-number arithmetic and can use decide. The forms are equivalent by dividing by L; patterns, LP value, and OPT are unchanged by scaling.

3. **Define lpVal by an infimum, not a chosen minimum, and use ℝ.** Real infima have a direct definition and avoid proving attainability first; attainability for finite LPs is noted. lpVal is consequently noncomputable, so exact LP values in the checkpoints are established by sandwiching with a primal upper certificate and a dual lower certificate (the bridge lemma in decision 4). This is the central mechanism in the special-case proofs.

4. **Put the certificate bridge lemmas in the fixed region, with natural-number versions.** Since rational arithmetic cannot be checked by decide (decision 2), the fixed region adds natural-number lemmas on top of the general rational certificate results lpVal_le_of_feasible and le_lpVal_of_dual (weak duality): lpVal_le_of_natCover (natural item weights X, each item covered at least D times, imply LP≤(ΣX)/D) and le_lpVal_of_natDual (natural item weights W, with each pattern’s weight sum at most D, imply LP≥(ΣW)/D). Their side conditions are natural-number inequalities and can be checked by decide. The lemmas themselves are proved once in the fixed region using rational identities and weak duality; an agent supplies only the certificates. This follows the “definition layer includes base APIs” pattern from tuza-conjecture. The fixed region also includes lpVal_le_optNumber (LP≤OPT because a packing is a fractional cover of total weight k), optNumber_le_of_packsIn, le_optNumber_of_not_packsIn, and le_optNumber_of_pairwise_incompatible (pairwise incompatible items each require their own bin).

5. **Put the concrete checkpoint instances in the fixed region** (instB1..3, instC, and validity proofs), following tuza’s twoTriangles precedent. This keeps slot statements clean; for example, mirup_tight states optNumber instC 81 instC_le=4 ∧ Nat.ceil(lpVal instC 81)=3, and injected axioms in scoring variants do not mention temporary constructions. Item-size functions use List.getD, which the kernel can reduce. Vector notation ![...] and match on Fin could not be reduced by decide in the probes.

6. **Include maxRecDepth 1000000 and maxHeartbeats 8000000 in the fixed region.** The tuza precedent sets maxRecDepth 8192 in its fixed region. Checkpoint decide needs to enumerate subsets among 2¹⁰ patterns and check coverage sums; default resources are insufficient. These options only affect proof-search resources, not the statement.

7. **Do not use LP duality for the OPT lower bound.** LP≤OPT, so a dual certificate can at best show OPT≥⌈LP⌉. In (c), OPT=4>⌈LP⌉=3, exactly the nonintegrality gap, so a combinatorial proof is needed. The first design used decide to enumerate 3¹⁰ assignments for ¬PacksIn instC 81 3; probes took over 600 seconds, unreliable under the scorer’s 900-second per-variant limit. It was replaced by a hand proof accounting for slack: total size 241=3·81−2, while the bins containing items 62 and 40 force total slack at least 3, a contradiction. The needed subset-sum facts ({0,...,4} and {1,2,4,5,6,7}) are small and decide checks them in seconds. The same hand proof is in small-examples.md.

8. **Do not state checkpoint (a) as “OPT=⌈total volume⌉.”** For identical item sizes, OPT=⌈n/m⌉ where m=L/c is items per bin; this need not equal the ceiling of total volume. For example, L=100,c=34,n=5 gives OPT=3>⌈1.7⌉=2. Small-example checks confirm LP=n/m and OPT=⌈n/m⌉, so (a) states the MIRUP inequality itself. IRUP holds for equal-sized items, and implies MIRUP.

## 3. Checkpoints and literature status

| Slot | Content | Literature status |
|---|---|---|
| conj | The conjecture for integer-form BPP. | Open; Borges et al. 2023 still cites it as a conjecture, as does the exact-algorithm paper arXiv:2308.03595. |
| refuted | Negation of the conjecture. | Open. The largest known OPT/LP ratio is 17/16 (Kartak et al. 2015, a 14-item instance); there is no known counterexample to OPT≤⌈LP⌉+1. |
| mirup_uniform | MIRUP for equal-size items. | Elementary solved case: IRUP holds and OPT=⌈n/m⌉=⌈LP⌉. |
| mirup_small | Exact LP and OPT values on three small instances. | A small version of Kartak-style computational verification (exact LP, exact OPT, and certificates). |
| mirup_tight | instC has LP=3 but OPT=4=⌈LP⌉+1. | The 10-item L=81 instance family from Kartak–Kurz–Ripatti–Scheithauer 2015, Table 1; all instances with at most 9 items are IRUP, so this is the traditionally smallest nonintegral instance. |

## 4. Statement-layer deviations

There is no substantive deviation. The scope is BPP only (decision 1), and instances use integer sizes (decision 2), equivalent to the (0,1] rational convention. The main conjecture agrees component by component with §5 of the survey and the table above.

## 5. Checks against systematic formulation errors

1. **Existential witnesses satisfy the required constraints.** PacksIn produces an assignment f with capacity checked for every bin; IsFracCover produces pattern weights x with every item covered at least once. Neither witness can use a degenerate value to evade the condition: for n≥1 an empty assignment does not cover the items, and an empty cover fails every item constraint.
2. **Degenerate parameters:** At n=0, OPT=0≤⌈LP⌉+1 trivially; PacksIn holds for zero bins on the empty instance and optNumber=0. For L=0, hpos and hle cannot both hold when n≥1, so the premise is empty. For n=1, OPT=LP=1.
3. **The main statement’s domain contains the checkpoints.** All checkpoint instances, including instC, are instances in the main conjecture’s quantifier range. mirup_tight states OPT=⌈LP⌉+1, consistent with the main upper bound. mirup_uniform is a direct consequence of the main conjecture on a subclass; its proof could instantiate conj, but the scorer removes the main slot to invalidate that route, as stated in the task instructions.
4. **Substitution or evaluation structure:** Not applicable; the task has no such structures.
5. **Base cases:** The proof of (a) handles n=0 separately (k=0 branch); the enumerated checkpoints have no induction structure.
6. **Both sides and off-by-one boundaries:** The right side is exactly ⌈LP⌉+1, not LP+1 and not ⌈LP+1⌉. Nat.ceil is used; LP≥0, so it agrees with integer ceiling. Checkpoint (c) witnesses that +1 is tight. The size conditions 0<l i≤L include both endpoints of the literature convention; an item of size L is legal and occupies one bin by itself.
7. **Weakening or vacuity:** conj is not weakened and matches the literature. Its premise is satisfiable (for example, any instance with all item sizes 1). A known instance with OPT=⌈LP⌉+1 is not a counterexample to MIRUP; checkpoint (c) is deliberately such an instance and the task says it satisfies the conjectured bound.

## 6. Open checks and remaining items

- The original Scheithauer–Terno 1995 EJOR paper was not checked in full; this table relies on the survey’s retelling. The conjecture is a simple inequality, so the risk is low. Review level is **content reviewed at the statement level against the survey and the abstract/table of arXiv:1405.5988**.
- The claim that OPT−LP’s additive integrality gap is currently known to be at most logarithmic (Hoberg–Rothvoß 2017 and others) is locator-only, based on the survey; the task statement does not depend on it.
- The cost of checkpoint decide (2¹⁰ pattern enumeration and coverage checks) depends on toolchain performance; probe results are in PROVENANCE.md. Recheck maxRecDepth, maxHeartbeats, and scoring timeouts if the toolchain changes.
