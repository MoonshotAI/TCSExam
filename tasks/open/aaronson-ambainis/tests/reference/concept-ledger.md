# Faithfulness Review: The Aaronson–Ambainis Conjecture

This note explains the task statement for readers comparing the mathematical definitions with the Lean source. The current scoring statements are `conj` and `refuted`; proving either earns full credit.

This document compares the task’s Lean statement with the original conjecture in the Theory of Computing journal paper and records all differences.

- **Primary source:** Aaronson and Ambainis, “The Need for Structure in Quantum Speedups,” Theory of Computing 10(6):133–166, 2014., the journal version was checked against Conjecture 1.7 and §§1.2–1.3 (influence definition and the L1/L2 discussion).
- **Status evidence:** Bhattacharya, ITCS 2025, arXiv:2402.13952 (the random-restriction version is proved; the general case remains open); Dinur, Friedgut, Kindler, O’Donnell 2006 (an influence lower bound decaying exponentially with degree, the current known frontier).
- **Released statement:** environment/app/Task/Basic.lean (namespace AaronsonAmbainis).

## 1. Review level

**Content reviewed.** The conjecture statement and influence definition were checked sentence by sentence against the Theory of Computing journal page. The arXiv link in item 3 of quantum-interactive-nonlocal.md incorrectly points to a different physics paper. The correct source is the 2014 ToC journal paper; arXiv:0911.0996 is its matching preprint. This document follows the journal version.

## 2. Component-by-component correspondence

| Original component | Literature form | Lean identifier | Relation |
|---|---|---|---|
| Polynomial p : ℝᴺ→ℝ of degree ≤ d | Any real polynomial; not required to be multilinear. | MvPolynomial (Fin n) ℝ; p.totalDegree≤d. | Matches. |
| Boolean cube | Uniform X∈{0,1}ᴺ. | Fin n→Bool, embedded into {±1}ⁿ by pmOne. | Deviation 1. |
| Boundedness 0≤p(X)≤1 on the cube | Two pointwise inequalities. | BoundedOnCube p. | Matches after using the {±1} cube; see deviation 1. |
| Variance E[(p(X)−E[p])²]≥ε | Uniform expectation. | ε≤cubeVariance p (cubeAvg sums over 2ⁿ points then divides by 2ⁿ). | Matches. |
| Influence Inf_i[p] | E[(p(X)−p(Xᶦ))²], the **squared difference**; Xᶦ flips coordinate i. | cubeInfluence p i (flipAt x i flips coordinate i). | Matches. |
| Conclusion: some i has Inf_i[p]≥(ε/d)^O(1) | There are constants c,k with Inf_i≥c·(ε/d)^k. | ∃ C : ℕ, (ε/(d:ℝ))^C≤cubeInfluence p i. | Deviation 2. |

The original paper’s §1.3 notes that early versions used L1 influence (expected absolute difference), but the proof required L2 influence (expected squared difference). Appendix 6 proves the two versions of the conjecture equivalent. The journal statement fixes the L2 version, which this task follows.

## 3. Deviations and rationale

1. **Use the {±1} cube instead of {0,1}.** The paper states formulas on {0,1}ᴺ; this task uses {±1}ⁿ. The affine map x↦2x−1 is a bijection between the cubes and preserves, pointwise, polynomial degree (affine substitution does not increase degree, and the inverse has the same property), uniform expectation (by reindexing under a bijection), and expected squared differences (under the same substitution). The conjectures on the two cubes are therefore equivalent. The {±1} cube is standard in Boolean Fourier analysis and gives clean values for small examples such as the dictator.

2. **Absorb the constant in (ε/d)^O(1).** The paper’s conclusion says that there are constants c,k with Inf_i≥c·(ε/d)^k; Lean states ∃ C:ℕ with Inf_i≥(ε/d)^C. These are equivalent here. Since p is bounded between 0 and 1, its variance is at most 1/4: E[p²]≤E[p], so Var(p)≤E[p]−E[p]²≤1/4. Hence ε/d≤1/4<1. Given c,k, take C=k+⌈log₄(1/c)⌉; then (ε/d)^C≤(1/4)^(C−k)(ε/d)^k≤c·(ε/d)^k. The converse is immediate with c=1.

## 4. Important correction to the task brief

The authoring brief stated a scaled version with Var(p)≥1 and no boundedness requirement: for a universal constant C, every degree-≤d polynomial with variance at least 1 would have some coordinate influence at least d^(−C). **That scaled claim is false.** Let p(X)=(X₁+…+Xₙ)/√n. It has variance 1 and degree 1, but each influence is 4/n and tends to zero as n increases. The brief also required consistency with the ToC statement; where these conflict, the original paper takes precedence. This task uses the paper’s bounded version (0≤p≤1 and Var(p)≥ε imply some influence at least (ε/d)^C). Boundedness is essential: the scaled sum above is not bounded between 0 and 1 and so is not a counterexample to the original conjecture.
