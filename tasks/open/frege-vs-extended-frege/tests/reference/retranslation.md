# Independent Retranslation: Separating Frege from Extended Frege

This record independently derives a formalization draft from the literature without consulting the shipped Lean file, then compares the two component by component. It is the third fidelity record (independent retranslation).

- Source statements: the “Extended Frege” section of the Wikipedia “Frege system” page and the p-simulation section of “Propositional proof system,” captured via proxy.

## Step 1: Source statements

- “Cook and Reckhow also defined an extension of a Frege system, called extended Frege, which takes a Frege system F and adds an extra derivation rule which allows one to derive a formula p ↔ D, where ↔ abbreviates its definition in the language of the particular F and the atom p does not occur in previously derived formulas including axioms and in the formula D. The purpose of the new derivation rule is to introduce 'names' or shortcuts for arbitrary formulas. It allows one to interpret proofs in Extended Frege as Frege proofs operating with circuits instead of formulas.” (Wikipedia, “Frege system,” Extended Frege section)
- “A propositional proof system P p-simulates Q (written as P ≤p Q) when there is a polynomial-time function F such that P(F(x)) = Q(x) for every x. That is, given a Q-proof x, we can find in polynomial time a P-proof of the same tautology.” The weaker version says: “a pps P simulates or weakly p-simulates a pps Q if there is a polynomial p such that for every Q-proof x of a tautology A, there is a P-proof of A of size at most p(|x|).” (Wikipedia, “Propositional proof system”)
- “Reckhow's 1979 theorem states that all Frege systems are p-equivalent.” (Wikipedia, “Frege system”)
- The conclusion condition that extension variable p does not occur in the formula being proved A is not stated in Wikipedia's Extended Frege section. It comes from Cook–Reckhow 1979 and the standard textbook formulation. Without it, the system could “prove” a bare atom p: introduce p ↔ D with D provable, derive D → p, then use modus ponens to derive p, violating soundness. See deviation 3 in `concept-ledger.md`.

## Step 2: Natural-language refinement (resolving ambiguities)

- **System:** fix any Frege system (by Reckhow's theorem, the separation problem does not depend on the choice of system); use the Hilbert presentation with ten axiom schemata and modus ponens, the same system as fnpb.
- **Extension step:** a line has form (p → D) ∧ (D → p), with ↔ expanded into the chosen connectives. p is a fresh atom: it does not occur in D or in any previous line. A sequence whose lines are justified by an axiom, modus ponens, or an extension step is an EF sequence.
- **EF proof of A:** an EF sequence ending in A, with the conclusion condition that none of the p variables introduced by extension steps occurs in A.
- **Proof length:** the sum of the symbol counts on all lines, with the symbol count fixed explicitly.
- **Simulation (length formulation):** there is a degree d such that every EF proof π of conclusion A has a Frege proof π′ of the same conclusion with |π′| ≤ (|π|+1)^d (a monomial represents an arbitrary polynomial).
- **Conjecture:** simulation is impossible: for every degree d, there is an EF proof π of conclusion A satisfying the conclusion condition such that every Frege proof π′ of A has |π′| > (|π|+1)^d. “The shortest Frege proof exceeds the bound” and “every Frege proof exceeds the bound” are equivalent; use the latter.
- **Negation:** literally negate the simulability statement (there is a degree d that covers every EF proof).

## Step 3: Independently drafted types

```
Formula α := atom α | falsum | and | or | imp        (¬φ = φ → ⊥)
size / subst / eval / Tautology                       (as in fnpb)
vars : Formula α → List α                             (occurring atoms, including repetitions)
IsAxiom / IsProof / Provable / proofSize              (as in fnpb)
IsEFProof π := ∀ k, IsAxiom π[k] ∨ (∃ i j < k, MP) ∨
  (∃ p D, π[k] = (p → D) ∧ (D → p) ∧ p ∉ vars D ∧ ∀ l < k, p ∉ vars π[l])
ExtStep π k p := ∃ D, π[k] = (p → D) ∧ (D → p) ∧ p ∉ vars D ∧ ∀ l < k, p ∉ vars π[l]
EFProves π φ := IsEFProof π ∧ getLast? π = some φ ∧ ∀ k p, ExtStep π k p → p ∉ vars φ
Conjecture := ∀ d : ℕ, ∃ φ, ∃ π, EFProves π φ ∧
  ∀ π', IsProof π' → π'.getLast? = some φ → (proofSize π + 1)^d < proofSize π'
Negation := ¬ Conjecture
```

## Step 4: Component-by-component comparison with the shipped version

| Component | Draft | Shipped version | Finding |
|---|---|---|---|
| Formula / length / semantics / system / proof | Same as fnpb | Same names under `Frege.*` | Match |
| Variables | `vars`, a `List` that includes repetitions | `Formula.vars`, same form | Match |
| Shape of extension step | (p→D)∧(D→p) | Same shape in the third branch of `IsEFProof` | Match |
| Freshness condition | p∉vars D ∧ ∀ l < k, p∉vars π[l] | Same two conditions | Match |
| EF proof | Final line + conclusion condition | Three conjuncts in `EFProves` | Match |
| Conjecture quantifiers | ∀ d ∃ φ ∃ π (EF proof ∧ lower bound) | `conj`, same order | Match |
| Simulation bound | (proofSize π + 1)^d | Same | Match |
| Negation | ¬Conjecture | `refuted`, literal negation | Match |

There are no disagreements. Packaging choices (fixing one system, expanding ↔, using a monomial, the length convention, and defining `ExtStep` syntactically) preserve semantics. See deviations 1/2/3/5/7 in `concept-ledger.md`.

## Notes

- The core quantifier order is: ∀ d (outermost, one degree at a time), then ∃ φ ∃ π (an EF-proof witness), then ∀ π′ (every Frege proof of the same conclusion exceeds the bound). `refuted` is its literal negation. In classical logic it is equivalent to “there is a degree d such that every EF proof has a Frege translation within the monomial bound”; the model can unfold this equivalent form itself.
- Direction check: Frege is the simulating system; EF is the system being simulated. `conj` says “no simulation” (separation, the standard conjecture), while `refuted` says “a simulation exists.” The direction is not reversed (see Section 3 of `concept-ledger.md`).
- An alternative not used: encode EF proofs as an inductive type with a justification tag on each line, precisely distinguishing modus-ponens lines from extension lines. This departs from fnpb's style of putting validity in a predicate and loses structural symmetry with `IsProof`; the syntactic criterion `ExtStep` is recorded in deviation 3 of `concept-ledger.md`.
