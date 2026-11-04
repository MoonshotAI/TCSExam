# Statement Ledger: The Fourier Entropy–Influence Conjecture

This note explains the task statement for readers comparing the mathematical definitions with the Lean source. The current scoring statements are `conj` and `refuted`; proving either earns full credit.

This ledger compares the literature statement of the Fourier Entropy–Influence (FEI) conjecture with the Lean statement in this task, and records every deviation and its rationale. It is intended for task authors and reviewers as one of the three fidelity records (the component-by-component ledger).

Sources: background survey `learning-theory-boolean-testing.md`, item 4 (short name `fourier-entropy-influence`, recommended as the top choice); Friedgut–Kalai 1996, “Every monotone graph property has a sharp threshold,” Proc. Amer. Math. Soc. 124(10):2993–3002; O'Donnell–Wright–Zhou, ICALP 2011, “The Fourier Entropy–Influence Conjecture for certain classes of Boolean functions”; and recent frontier work by Xiao Han 2024 (Combinatorica 45(1), arXiv:2312.08271).

Shipped statement: `environment/app/Task/Basic.lean` (identical, character for character, to the scoring copy in `tests/reference/Basic.lean`).

## 1. Published statement and Lean correspondence

The survey gives the standard literature statement: there is a universal constant C > 0 such that, for every Boolean function f: {±1}ⁿ → {±1}, the Shannon entropy H(f̂²) of the probability distribution formed by the squared Fourier coefficients is at most C · I(f). Here I(f) = Σᵢ Infᵢ[f] is the total influence, the sum over coordinates of the probability that flipping coordinate i changes the function value.

| Concept | Literature | Lean identifier in this task | Notes |
|---|---|---|---|
| Boolean cube | {±1}ⁿ | `Cube n := Fin n → Bool` (abbrev) | Uses sign vectors; ±1 values are supplied by `pmOne` (see deviation 1). |
| Embedding into ±1 | xᵢ ∈ {−1,+1} | `pmOne : Bool → ℝ` (`true ↦ 1`, `false ↦ −1`) | Same convention as the `aaronson-ambainis` task in the open-problem line. |
| Character | χ_S(x) = ∏_{i∈S} xᵢ | `charFn S x := ∏ i ∈ S, pmOne (x i)` | S is `Finset (Fin n)`. |
| Fourier coefficient | f̂(S) = 2⁻ⁿ Σₓ f(x)χ_S(x) | `fourierCoeff f S` | Standard normalization, written as an expectation. |
| Boolean function | f: {±1}ⁿ → {±1} | `f : Cube n → ℝ` plus predicate `IsBoolean f := ∀ x, f x = 1 ∨ f x = -1` | See deviation 2. |
| Fourier entropy | H(f̂²) = Σ_S f̂(S)²·log(1/f̂(S)²) | `fourierEntropy f := ∑ S, entropyTerm ((fourierCoeff f S)^2)` | Uses natural logarithms (deviation 3); zero terms are handled as in deviation 4. |
| f̂² is a probability distribution | Parseval: Σ f̂² = 1 | `sum_sq_fourierCoeff_isBoolean` (proved) | The general form `sum_sq_fourierCoeff` is also proved. |
| Coordinate influence | Infᵢ[f] = Prₓ[f(x) ≠ f(x^⊕i)] | `influence f i := 2⁻ⁿΣₓ (f x − f (flipAt x i))² / 4` | L² form; equivalence to the probability form is proved in `influence_eq_card` (deviation 5). |
| Total influence | I(f) = Σᵢ Infᵢ[f] | `totalInfluence f := ∑ i, influence f i` | |
| Conjecture | ∃C, ∀n ∀f, H ≤ C·I | `FeiConjecture := ∃ C : ℝ, 0 < C ∧ ∀ {n} (f : Cube n → ℝ), IsBoolean f → fourierEntropy f ≤ C * totalInfluence f` | Main slot `conj`; `refuted` is its exact negation (deviation 6). |

## 2. Deviations and rationale

1. **The cube is represented as `Fin n → Bool` with a `pmOne` embedding rather than directly as `Fin n → ℝ`.** The Boolean structure (flipping and enumerating coordinates) is native to Bool (`!b` and the `Fin.cons` enumeration), while all ±1 arithmetic is concentrated in the single function `pmOne`. Four lemmas (`pmOne_mul_self`/`pmOne_not`/`pmOne_mul_pmOne`/`pmOne_ne_zero`) cover all sign operations. The convention `true ↦ 1` matches the `aaronson-ambainis` task. Which value is interpreted as “true” does not affect the conjecture: globally negating a ±1-valued function leaves its entropy and influence unchanged.

2. **Boolean functions are represented as real-valued functions plus an `IsBoolean` predicate.** Fourier coefficients are naturally real-valued, so the definition layer uses the function space `Cube n → ℝ` (influence and entropy are defined for arbitrary real-valued functions) and passes Booleanity as a hypothesis. This matches the literature's practice of defining quantities for real-valued functions first and then stating the conjecture for Boolean functions.

3. **Entropy uses the natural logarithm (`Real.log`), while the literature often uses log₂.** Changing the base introduces only a constant factor, which is absorbed into the universal constant C; the conjectures with either base are equivalent. Checkpoint c3's numerical value (2·log 2) is given using the natural logarithm.

4. **The zero-entropy term uses mathlib's conventions.** `entropyTerm p := p * Real.log p⁻¹`. At p = 0, `0⁻¹ = 0` and `Real.log 0 = 0`, so the term is 0. This is the standard Shannon-entropy convention 0·log(1/0) = 0 and requires no special case.

5. **Influence is defined in L² form:** `2⁻ⁿΣₓ(f(x) − f(x^⊕i))²/4`. For a ±1-valued function, the squared difference is 4 when flipping changes the value and 0 otherwise, so this agrees pointwise with the probability definition in the literature (`influence_eq_card` is proved, including its cardinality form). The L² form is defined for every real-valued function and lets checkpoint proofs use algebra without going through filtered counting.

6. **`refuted` is exactly the negation of the literature statement, `¬FeiConjecture`.** In classical logic this is equivalent to saying that for every C > 0 there is some n and Boolean f with H > C·I. The model can choose which equivalent form to use for a refutation.

7. **The dimension n = 0 is included.** There is one function on the empty cube, and it is constant; its entropy and influence are both 0, so 0 ≤ C·0 holds trivially. Including n = 0 is equivalent to the literature statement (where n ≥ 1 is only implicit background). At n = 0, checkpoint c2 (parity) is the constant χ_∅ = 1, with H = 0 and I = 0 = n, so it still holds.

## 3. Distinguishing related problems

- **Fourier Min-Entropy–Influence (FMEI) conjecture:** the min-entropy version, min_S log(1/f̂(S)²) ≤ C·I(f), is weaker than FEI and is not the subject of this task.
- **Mansour's conjecture:** Fourier concentration for DNF formulas (item 6 in the survey). FEI implies its weak form, but it is a different conjecture; the survey describes the relationship.
- **`aaronson-ambainis`:** a task in the same line uses the same Boolean-cube infrastructure (the conventions for `pmOne`/`flipAt`/`cubeAvg` agree), but its conjecture is different: low-degree polynomials must have a high-influence coordinate. The statements do not overlap.
- **O'Donnell's textbook, *Analysis of Boolean Functions* (2014), does not contain this conjecture.** Do not cite that book as its source. The task and instruction text specifically cite Friedgut–Kalai 1996 and O'Donnell–Wright–Zhou 2011.

## 4. Source attribution check ()

- Xiao Han 2024 (the arXiv:2312.08271 text, also appearing in Combinatorica 45(1)) writes: “This conjecture was first proposed by Friedgut and Kalai in the study of monotone graph properties in the 1990s [10],” where [10] is Friedgut–Kalai, Proc. AMS 124(10):2993–3002, 1996. **The conjecture was first proposed by Friedgut–Kalai in 1996.**
- O'Donnell–Wright–Zhou's ICALP 2011 paper established the current name (“The Fourier Entropy–Influence Conjecture”) and proved it for several function classes, including DNF and read-once formulas. It is the standard source most often cited in the literature.
- Both works are cited in this task: the prompt and document state that Friedgut–Kalai 1996 first proposed the conjecture and O'Donnell–Wright–Zhou, ICALP 2011, standardized it. This matches the survey's item 4 source field, which names Friedgut–Kalai 1996. The dispatch wording “OWZ 2011 proposed it” is interpreted as “gave the standard formulation”; this distinction is recorded here.

## 5. Current bounds and source checks

Checked against the survey and source material.

- Best general upper bound: H ≤ O(I(f) + Σₖ Iₖ(f)·log(1/Iₖ(f))) (Xiao Han 2024, Combinatorica 45(1); the constant was improved later, as noted in arXiv search results); the earlier bound was O(I·log n).
- Function classes for which the conjecture is proved include read-once formulas, random DNF, and symmetric functions (OWZ 2011 and later work).
- The conjecture remains open: Han 2024 still treats it as open when giving the new upper bound; the introduction of arXiv:2511.07739 (2025, a lower bound on Fourier entropy for the p-biased cube) still frames its result as progress toward FEI.
- Lower bound on the constant: AND₂ forces C ≥ 2·log 2 (checkpoint c3); the minterm/AND_n family gives sup H/I ≥ 4·log 2, with `verify_small.py` showing the numerical trend as n → ∞ toward 4·log 2 ≈ 2.7726.
