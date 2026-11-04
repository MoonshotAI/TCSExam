# Faithfulness Review: The Permanent-versus-Determinant Conjecture

This note explains the task statement for readers comparing the mathematical definitions with the Lean source. The current scoring statements are `conj` and `refuted`; proving either earns full credit.

This document compares Valiant’s 1979 conjecture with the Lean statement used by the task, explaining all modeling choices.

- **Primary source:** Valiant, “The complexity of computing the permanent,” Theoretical Computer Science 8 (1979), 189–201.
- **Released statement:** environment/app/Task/Basic.lean; it matches tests/reference/Basic.lean word for word.

## 1. Literature statement and Lean correspondence

The survey’s formulation asks whether there is a polynomial q(n) such that the n×n permanent (the determinant formula with every permutation sign replaced by +1) can be represented as the determinant of a q(n)×q(n) matrix whose entries are variables or field constants. Equivalently, is the determinantal complexity dc(perₙ) polynomially bounded? Valiant’s conjecture says no.

The usual meaning of “matrix entries” in Valiant 1979 and later work such as Mignon–Ressayre 2004 is affine linear forms in the original variables (a constant plus a linear combination). “Variables or field constants” is the degree-at-most-one special case and describes the same model.

| Concept | Literature | Lean identifier in this task | Notes |
|---|---|---|---|
| Permanent | Σ_σ ∏ᵢ xᵢ,σ(i), with all signs positive. | permPoly n := (varMatrix n).permanent; mathlib Matrix.permanent is Σσ:Perm n, ∏i M(σ i)i, applied to the generic variable matrix. | See deviation 1. |
| Variables | n² formal variables. | X(i,j) : MvPolynomial (Fin n×Fin n) ℝ. | |
| Base field | Characteristic-zero field (Mignon–Ressayre setting). | ℝ. | See deviation 2. |
| Matrix entries are affine linear forms | Constant plus a linear combination of variables. | Each matrix entry p satisfies p.totalDegree≤1. | See deviation 3. |
| Representation | det(A)=f for an m×m matrix A. | IsDetRepr f m (there exists such A with A.det=f). | For m=0, det=1 (empty product); for m=1 determinant is the entry itself, matching the literature. |
| dc(f) | Minimum representation size. | detComp f := sInf {m | IsDetRepr f m}. | See deviation 4. |
| Conjecture | dc(perₙ) is not polynomially bounded. | SuperpolyDc := ∀c N, ∃n≥N, n^c<detComp(permPoly n); this is the main conj slot and refuted is its negation. | See deviation 5. |

## 2. Deviations and rationale

1. **Use mathlib’s Matrix.permanent directly.** Its product is ∏i M(σ i)i, whereas the literature often writes ∏i M(i,σ(i)). Replacing σ by its inverse reindexes the same permutation sum, so the two expressions agree pointwise.

2. **Fix the base field to ℝ.** The literature usually states the problem over a characteristic-zero field (Valiant’s original problem is meaningful over arbitrary fields; Mignon–Ressayre’s lower bound uses characteristic 0, and Cai–Chen–Li extend it to characteristic not 2). ℝ is a representative characteristic-zero field and is convenient for scoring-side computation (ring and degree arguments). All witness matrices in the three checkpoints use integer coefficients and need no extra properties of ℝ.

3. **Formalize “affine linear form” as totalDegree≤1.** Over ℝ, polynomials of total degree at most 1 are exactly constants plus linear combinations of variables, including the constant and zero degenerate cases. This matches the literature pointwise.

4. **Define detComp with Nat.sInf, whose empty-set convention is 0.** For a polynomial with no determinant representation, dc is therefore set to 0. The conjecture is a lower-bound statement n^c<dc; 0 can never satisfy it, so the empty-set convention cannot make the conjecture vacuously true. Grenet’s construction shows the representation set for permₙ is nonempty, so this convention does not affect the truth value.

5. **Express “not polynomially bounded” as ∀c ∀N ∃n≥N, n^c<dc(permₙ).** This is the classical expansion of “there is no c for which dc(permₙ)≤n^c for all sufficiently large n.” Constant factors are absorbed by increasing the exponent by 1, matching the standard n^O(1) meaning. refuted is its literal negation, classically equivalent to the existence of c,N such that for all n≥N, dc(permₙ)≤n^c, i.e. dc(permₙ)=n^O(1).

6. **Use natural-number exponentiation for n^c.** The comparison n^c≤dc is over ℕ. At c=0, n^0=1 and the statement asks dc(permₙ)>1, which follows for n≥2 from the degree lower bound; there is no vacuous edge case.

## 3. Distinction from nearby problems

- This is the **projection version of VP≠VNP**: it asks whether the permanent has a polynomial-size determinant representation, not about general algebraic circuits. Superpolynomial dc(permₙ) implies VP≠VNP (determinants have polynomial-size weakly skew circuits); the converse does not follow. The survey lists this separately as det-perm-projection, distinct from vp-vs-vnp.
- Searching FC (google-deepmind/formal-conjectures) for “permanent” and “Valiant” found only Wikipedia/DeterminantalConjecture.lean, about determinants of sums of normal matrices, unrelated to this conjecture (checked in the survey).
- This is a structural decision statement: either proving superpolynomial dc or disproving it with a polynomial bound resolves the conjecture.

## 4. Known frontier

- Lower bound: dc(permₙ)≥n²/2 (Mignon–Ressayre 2004; Cai–Chen–Li extend it to every field of characteristic not 2). This is the best general lower bound in more than forty years.
- Upper bound: dc(permₙ)≤2ⁿ−1 (explicit construction by Grenet 2011; the survey also mentions the n·2^(n−1) scale).
- Small values: dc(perm₂)=2; dc(perm₃) is known to lie in the range {5,6,7} (checkpoint 3 proves only ≤7 and does not claim the exact value); dc(perm₄)∈[8,15], exact value unknown (task brief).
- Evidence the problem remains open: ECCC TR24-015 (2024) says in its abstract that the best known lower bound for permanent determinantal complexity is quadratic, while the conjecture asks for a bound exceeding every polynomial.
