# Independent Retranslation: Frege Is Not Polynomially Bounded

This record derives a formalization draft from the literature without consulting the shipped Lean file, then compares the two component by component. It is the third fidelity record (independent retranslation).

- Source statements: the Wikipedia entries “Frege system,” “Propositional proof system,” and “Proof complexity,”.

## Step 1: Source statements

- “Among the major challenges of proof complexity is showing that the Frege system, the usual propositional calculus, does not admit polynomial-size proofs of all tautologies. Here the size of the proof is simply the number of symbols in it, and a proof is said to be of polynomial size if it is polynomial in the size of the tautology it proves.” (“Proof complexity”)
- “A Frege system is a propositional proof system whose proofs are sequences of formulas derived using a finite set of sound and implicationally complete inference rules.” Formalized as: a finite functionally complete connective set K and a finite Frege rule set R; an F-proof of A is a sequence A₁…A_m with A_m = A, where each A_k is an axiom (an instance of X) or follows from earlier formulas by a substitution instance of a rule in R. (“Frege system”)
- “Reckhow's 1979 theorem states that all Frege systems are p-equivalent.” (“Frege system”)
- “There is a polynomially bounded propositional proof system if and only if NP = coNP.” (“Propositional proof system”)

## Step 2: Natural-language refinement (resolving ambiguities)

- **Formula:** infinitely many propositional variables (p₀, p₁, …), combined with arbitrary nesting from a functionally complete set of connectives. Formula length is the number of symbols.
- **System:** fix any Frege system (by Reckhow's theorem, the conjecture does not depend on which system is chosen); use a Hilbert presentation with axiom schemata and modus ponens.
- **Proof:** a finite sequence of formulas. Each line is an axiom-schema instance or follows by modus ponens from earlier lines A_i and A_j = A_i → A_k (i,j < k). The proved formula is the last line.
- **Proof length:** the sum of the symbol counts of all lines, explicitly measured in symbols rather than number of lines.
- **Conjecture:** there is a family of tautologies {τₙ} and a constant c such that |τₙ| ≤ n^{O(1)} (represented by (n+1)^c), but for every degree d, from some N onward every Frege proof of τₙ has more than (n+1)^d symbols.
- “The shortest proof has length > q(n)” is equivalent to “every proof has length > q(n)”; use the latter and avoid defining shortest length.
- Represent “polynomial” by the explicit monomial family (n+1)^d (every polynomial is bounded uniformly for n ≥ 1 by some (n+1)^d).

## Step 3: Independently drafted types

```
Formula α := atom α | falsum | and | or | imp        (¬φ = φ → ⊥)
size : Formula α → ℕ                                  (symbol count)
subst : (α → Formula β) → Formula α → Formula β
eval : (α → Bool) → Formula α → Bool
Tautology φ := ∀ v, eval v φ = true
IsAxiom : Formula α → Prop                            (all instances of the ten schemata)
IsProof π := ∀ k : Fin π.length, IsAxiom π[k] ∨ ∃ i j < k, π[j] = π[i] ⇒ π[k]
Provable φ := ∃ π, IsProof π ∧ π.getLast? = some φ
proofSize π := (π.map size).sum
Conjecture := ∃ τ : ℕ → Formula ℕ, ∃ c : ℕ,
  (∀ n, Tautology (τ n)) ∧ (∀ n, size (τ n) ≤ (n+1)^c) ∧
  (∀ d, ∃ N, ∀ n ≥ N, ∀ π, IsProof π → π.getLast? = some (τ n) → (n+1)^d < proofSize π)
Negation := ¬ Conjecture
```

## Step 4: Component-by-component comparison with the shipped version

| Component | Draft | Shipped version | Finding |
|---|---|---|---|
| Formula | atom/falsum/and/or/imp | `Frege.Formula`, same five constructors | Match |
| Negation | Abbreviation for φ → ⊥ | Same (noted in the file header and docstring) | Match |
| Formula size | Symbol count | `Formula.size` (atom/⊥ count as 1; a connective counts 1 + left + right) | Match (unit-size convention; checked by small example E4). |
| Axiom schemata | Ten: k/s/exFalso/peirce/three ∧ rules/three ∨ rules | `IsAxiom`, same ten, with matching constructors | Match |
| Proof | Sequence; each line axiom or MP with valid indices | `IsProof`, same form; MP requires π[j] = π[i] ⇒ π[k] with i,j < k | Match |
| Provability | Last line is φ | `Provable` (`getLast? = some φ`, which implies nonempty) | Match |
| Proof length | Sum of symbol counts across lines | `proofSize` | Match |
| Tautology | True under all assignments | `Tautology` (implication evaluation unfolds to ¬φ∨ψ) | Match |
| Conjecture | ∃ family ∃ c, tautology ∧ size bound ∧ ∀ d eventually every proof > (n+1)^d | `conj`, same quantifier order and content | Match |
| Negation | ¬Conjecture | `refuted`, literal negation | Match |
| Variable supply | Infinite (ℕ) | Main slot uses α = ℕ | Match |

There are no disagreements. Packaging differences (fixing one system, using a monomial representative, and universalizing instead of taking shortest length) preserve semantics; see deviations 2/5/6 in `concept-ledger.md`.

## Notes

- Quantifier core: ∃ τ ∃ c (family and size bound outside), then ∀ d ∃ N ∀ n ≥ N (superpolynomial proof growth inside). `refuted` is its literal negation; classically this is equivalent to “for every family and c there is a d such that for infinitely many n there is a short proof.” The model can expand this equivalent form itself.
- The implication from the family version to the textbook version of “not polynomially bounded” is in deviation 5 of `concept-ledger`; the literature uses both formulations interchangeably.
- The relation to complexity classes (NP ≠ coNP implies the conjecture; the conjecture does not imply NP ≠ coNP) is not in the Lean statement, since that is a complexity-class claim outside the definition layer. It is included in `instruction` and the file-header note for context.
