# Statement Ledger: The Alon–Jaeger–Tarsi Conjecture over Prime Fields

This note explains the task statement for readers comparing the mathematical definitions with the Lean source. The current scoring statements are `conj` and `refuted`; proving either earns full credit.

This ledger compares the plain-language conjecture, its sources, and the Lean identifiers in this task, and records the design choices and their rationale. It is intended for task authors and reviewers as one of the three fidelity records (the component-by-component ledger).

Sources: survey `dig2-additive-polynomial.md` §8 (short name `alon-jaeger-tarsi-conjecture`, including source and frontier checks); arXiv:math/0510025 (the standard conjecture for all finite fields of size at least 4); Nagy–Pach, arXiv:2107.03956 (2021, resolving prime fields for p > 61 and p ≠ 79); arXiv:2604.26320 (April 2026, still aiming to settle the prime-field case and thus recent evidence that the problem remains open); Alon–Tarsi 1989 (a polynomial-method solution for all finite fields of nonprime order).

Shipped statement: `environment/app/Task/Basic.lean` (namespace `AlonJaegerTarsi`).

## 1. Plain-language statement and Lean correspondence

The remaining statement in the survey is: for every prime p ≥ 5, every positive integer n, and every nonsingular n×n matrix A over F_p, there is a vector x ∈ F_pⁿ such that all coordinates of x and A·x are nonzero.

| Component | Literature statement | Shipped Lean statement | Notes |
|---|---|---|---|
| Field quantifier | Every prime p ≥ 5 | `∀ (p : ℕ) [Fact p.Prime], 5 ≤ p →` | The threshold choice is explained in decision 1. |
| Dimension quantifier | Every positive integer n | `∀ (n : ℕ)` | At n = 0 the proposition is vacuously true (the empty matrix has determinant 1, and “every coordinate is nonzero” for the empty vector holds vacuously); including it is harmless. |
| Matrix quantifier | Every n×n matrix over F_p | `∀ (A : Matrix (Fin n) (Fin n) (ZMod p))` | `ZMod p` represents F_p. |
| Nonsingularity | Nonsingular | `A.det ≠ 0` | Over a field, nonzero determinant is equivalent to nonsingularity; see decision 4. |
| Conclusion | There is an x such that every coordinate of x and A·x is nonzero | `HasAJTVector A`, meaning `∃ x, NowhereZero x ∧ NowhereZero (A *ᵥ x)`; `NowhereZero x := ∀ i, x i ≠ 0` | `A *ᵥ x` is mathlib's existing `Matrix.mulVec`. |

## 2. Design decisions and rationale

1. **Use p ≥ 5, not “odd prime.”** The task brief informally said “for every odd prime p,” but that wording cannot be formalized literally: at p = 3 the statement is false (there is already a counterexample at n = 2; see the enumeration and hand calculation in small-examples.md). If the statement said “odd prime,” the `refuted` slot could be discharged instantly by `decide` over 81 matrices, defeating the purpose of an open proof-conjecture task. The literature threshold is field size q ≥ 4 (counterexamples are known for p = 2 and 3); over prime fields this becomes p ≥ 5. The shipped `AJTConjecture` matches the remaining statement in the survey exactly.

2. **Restrict to prime fields.** The original conjecture is stated for all finite fields with |F| ≥ 4. Alon–Tarsi (1989) resolved all fields of nonprime order, so the open part is precisely the prime-field case. A version over every finite field could also be written in Lean (`∀ (F : Type) [Field F] [Fintype F], 4 ≤ Fintype.card F → …`), but it would fold an already solved case back into the statement and would not match the focus on the remaining open problem. The two versions are equivalent in the sense that the overall conjecture remains unresolved, since the nonprime-field case has a published proof. The task follows the prime-field version in the survey.

3. **Keep solved prime cases inside the conjecture.** Nagy–Pach (2021) settled p > 61 with p ≠ 79, so the unresolved cases are p ∈ {5, 7, …, 61} ∪ {79}. The shipped statement still quantifies over every p ≥ 5: this is the standard remaining form of the conjecture and matches the survey. The conjecture as a whole remains open; removing each already proved prime individually would depart from the literature statement.

4. **Represent nonsingularity as `A.det ≠ 0`.** Mathlib has no `Matrix.Nonsingular` predicate (a full search of the pinned mathlib revision 5b3f719 confirmed this; `nonsing_inv` is a construction, not a predicate). Over a field, `IsUnit A ↔ IsUnit A.det ↔ A.det ≠ 0` (`Matrix.isUnit_iff_isUnit_det`), so the three forms are equivalent. We use `A.det ≠ 0` because it is the most elementary and can be decided directly for literal finite fields without extra instances.

5. **Give `HasAJTVector` the weaker assumption `[CommRing F]`, not `[Field F]`.** “There exists an everywhere-nonzero x such that A·x is everywhere nonzero” can be stated over any commutative ring. Requiring a field would make literal `ZMod 3`/`ZMod 5` cases require instances such as `Fact (Nat.Prime 3)`; mathlib does not register those instances for small primes (the search found only `Fact (Prime 2/3)`, using the general `Prime` predicate rather than `Nat.Prime`). The field semantics are supplied by `[Fact p.Prime]` in `AJTConjecture`, so the definition remains lightweight.

6. **Decidability support on the fixed finite domains.** The instances `decNowhereZero` and `decHasAJTVector` connect the two definitions to mathlib's `Fintype.decidableForallFintype` and `Fintype.decidableExistsFintype`, so enumeration checkpoints (a) and (b) can be verified with `decide`. `native_decide` is prohibited by the lexical blacklist; all enumeration uses kernel `decide`. Checkpoint (b), which enumerates 625 matrices, exceeds the default recursion depth and needs `set_option maxRecDepth 16384` (stated in the task; the probe took about 18 seconds).

7. **Constraint on helper lemmas in the `refuted` slot.** The scoring system's proof-hole detector assigns 0 and marks SUSPECT if the slot calls a helper stated as `theorem X : False` or `theorem X : ¬ …` (following the bciks20 template). An honest refutation naturally has a positive form (`∃ p ≥ 5, ∃ A, A.det ≠ 0 ∧ ¬ HasAJTVector A`); the task specifies that helper lemmas must be stated positively.

## 3. Checkpoints and their connection to the literature

| Checkpoint | Content | Status in the literature |
|---|---|---|
| `conj` | The conjecture itself, over prime fields | Open (a 2026-04 preprint still targets it, arXiv:2604.26320). |
| `refuted` | Negation of the conjecture | Likewise open; counterexamples at p = 2 and 3 are known but outside the statement's range. |
| `ajt_p3_small` | At p = 3: the statement holds for n = 1, and there is a counterexample for n = 2 | Boundary fact for the q ≥ 4 threshold; decidable by enumeration (8/48 counterexamples; see small-examples.md). |
| `ajt_p5_n2` | At p = 5, the statement holds for n = 2 | Smallest prime on the open side and smallest nontrivial dimension; decidable by enumeration (480/480); see small-examples.md for the counting argument. |
| `ajt_n1` | The statement holds for n = 1 over every prime field | Trivial dimension of the conjecture; proved generally. |

## 4. Statement-layer deviations

None. This is the first release of the task, and the statement matches the remaining statement in survey §8 component by component (see the table in section 1).

## 5. Systematic error checks

1. **Constraints on existential witnesses:** The required relation between x and A is exactly `NowhereZero x ∧ NowhereZero (A *ᵥ x)`; x cannot be degenerate because being everywhere nonzero excludes the zero vector.
2. **Degenerate parameters:** At n = 0 the statement holds vacuously (see the note in section 1); n = 1 is separately covered by checkpoint `ajt_n1` and is true.
3. **Main-statement assumptions versus checkpoint assumptions:** The checkpoint instances derive from the quantifier structure of `AJTConjecture` without losing assumptions. The direction matters: `ajt_p3_small`/`ajt_p5_n2`/`ajt_n1` are instances or boundary cases, while `ajt_p3_small` includes a counterexample at p = 3 and therefore does not conflict with the main conjecture, which assumes p ≥ 5.
4. **Substitution/evaluation points:** There is no structure here with expansion points; not applicable.
5. **Base cases:** `ajt_n1` has no induction; enumeration checkpoints have no base case.
6. **Two-sided conditions and off-by-one boundaries:** The p ≥ 5 threshold was checked numerically (false at p = 3; true for p = 5, n = 2). Both parts of `NowhereZero`, for x and for A·x, are present.
7. **Weakening and vacuity:** `conj` is not weakened and matches the remaining literature statement. Its assumptions are satisfiable (for any p ≥ 5 and n, nonsingular matrices exist). Under the p ≥ 5 condition, `refuted` cannot exploit counterexamples at p = 2 or 3 because those primes are outside its quantifier range.

## 6. Open checks and remaining notes

- The original source (the 1980s Alon–Jaeger–Tarsi papers and their connection to matroid-group connectivity) has not been traced beyond the survey's citations. The statement itself is simple (two quantifier blocks, ∀∃), so the risk is low. The verification level is **content-reviewed** for the statement (checked against the survey and arXiv abstracts) and **locator-only** for the frontier fact that p > 61, p ≠ 79 has been resolved.
- The enumeration proof for `ajt_p5_n2` depends on kernel `decide` performance; recheck the recursion-depth setting when changing toolchains.
