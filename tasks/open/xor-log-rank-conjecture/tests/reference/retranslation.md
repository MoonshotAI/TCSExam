# Independent Retranslation: Formalizing the XOR Log-Rank Conjecture

This record compares a formalization draft independently derived from the literature, without consulting the shipped definition layer, against `Task/Basic.lean` component by component. It is the third fidelity record (independent retranslation).

- The same person wrote this file and the shipped file. “Independent” here means deriving the draft from the survey and literature abstracts first and only then comparing it with the shipped version. This is stronger than direct copying but weaker than a two-person independent check, and is recorded as such.

## From the literature statement to a formalization draft

Literature statement (survey and TWXZ 2013 abstract): there is a constant c such that for every f : 𝔽₂ⁿ → {−1,1}, PDT(f) ≤ (log sp(f))^c; sp(f) is the number of nonzero Fourier coefficients; and a parity decision tree may query the parity of any subset of coordinates at each step.

Derivation:

1. **Representation of f:** use a cube type and a ±1-valued range. Choose `Fin n → Bool` for the cube (with `Fintype` and decidable equality built in); let f be Boolean-valued and obtain its ±1 values by embedding. The sibling task `mansour-conjecture` already uses the same encoding (`pmOne`), so reuse it to reduce risk. → Shipped as `boolSign f = pmOne ∘ f`.
2. **Fourier coefficient:** the Fourier expansion on 𝔽₂ⁿ is the parity-basis expansion, f̂(S) = E_x[f(x)·χ_S(x)], where χ_S(x) = (−1)^{⊕_{i∈S} x_i}. Use rational values (the coefficients are rational, with denominator 2ⁿ) and uniform expectation. No general Fourier theory from mathlib is needed. → Shipped as `chi` / `cubeAvg` / `fourierCoeff`.
3. **Sparsity:** count nonzero coefficients by filtering a finite set and taking cardinality. → `sparsity`.
4. **Parity decision tree:** an inductive type with two constructors: a leaf carrying the answer, or an internal node carrying query set S and two subtrees. `eval` branches according to the query answer; depth is max+1. → `ParityTree`.
5. **PDT ≤ B:** the literature defines it as minimum depth. Use the equivalent existential form “there is a tree of depth ≤ B computing f,” avoiding a minimum over an infinite type. → `ComputesInDepth`.
6. **Quantifiers and constant:** ∃ c is outermost (one global constant, independent of n and f), then ∀ n ∀ f; upper bound log^c sp. Degenerate case: when sp = 1 (±χ_S), log sp = 0, so the literal statement fails on a constant or single character (depth 0/1 versus 0^c or a placeholder value). The literature's O(log^c sp) absorbs constants into the Big-O notation. The formal statement makes this explicit by adding 1: (1+log₂ sp)^c, whose right side is 1 when sp=1, enough for depth 1 of ±χ_S. → Shipped conjecture uses `(1 + Real.logb 2 (sparsity f))^c`.

## Component-by-component comparison with the shipped version

| Component | Retranslation draft | Shipped version | Finding |
|---|---|---|---|
| f / cube | `Fin n → Bool` + `pmOne` | Same | Match |
| χ_S / f̂ | ℚ-valued, uniform expectation | Same | Match |
| sp(f) | Filter nonzero coefficients and take cardinality | Same (plus an engineering bridge at the ℤ layer) | Match |
| Query | Parity of a coordinate subset, Boolean answer | Same (Boolean convention: χ_S = +1 means true; a bridge lemma removes the sign) | Semantically equivalent (complementing the answer only swaps subtrees). |
| Tree / depth / computation | Inductive type, max+1, agreement for every x | Same | Match |
| PDT ≤ B | Existential form | Same | Match |
| Quantifiers | Outer ∃ c, then ∀ n ∀ f | Same | Match |
| Degenerate case | Add 1 | Same (`(1+log₂·)^c`, with c : ℕ) | Match; a natural-number c is equivalent to a real exponent after rounding up (recorded as deviation 2 in `concept-ledger`). |
| Refutation slot | ¬P | Same | Match |

Finding: no substantive disagreement. Engineering additions (integer-valued computation layer, positivity lemma, monotonicity lemma) do not change the statement.

## Remaining source-check risks

- The exact conjecture numbering in the body of the TWXZ paper was not checked line by line; the anchor was its abstract and the survey's paraphrase. The abstract says, “we ... actually conjecture that its communication cost is already log^{O(1)} rank(M_f),” which is equivalent in form to this statement (∃ c, log^c).
- Montanaro–Osborne's original statement is in communication-complexity form (D^CC ≤ polylog(sp)); the PDT form follows TWXZ (PDT ≥ CC/2, with both bounds still open). Both the task instructions and survey use the PDT formulation.
