# Independent Retranslation Comparison: The GG26 Curve-Decoding Chain

This record compares two independent translations of the curve-decoding chain, covering Lemma 3.2, Theorems 3.3/3.4, Lemma 4.1, and Theorems 4.7/4.8. It documents the basis for adjudication and the outcome.

- Adjudication is based on the original ECCC TR25-166 (Sections 3 and 4 of the component ledger).
- This is the second of three fidelity records (independent retranslation).

## Sources and independence

- **A version (shipped):** It uses the definitions and theorem statements in Sections 2–4 of the paper. It translates them item by item, packages results where the definition layer cannot be made self-contained (`PruningGuarantee` / `ListSizeBound`), and repairs boundary cases one by one.
- **B version (checkpoint sheet):** It uses the same PDF but was completed before A was finalized. Its form is “one plain-language sentence per lemma + dependency graph + errata list,” without knowledge of A's Lean formulation.
- The only shared reference is the paper itself, so the two versions were prepared independently.

## Item-by-item comparison

| Decision | A version (shipped) | B version (checkpoint sheet) | Adjudication |
|---|---|---|---|
| Order of the chain | c1 multi-point proximity propagation → c2 curve list-decodability ⇒ MCA → c3 dimension bound → c4 curve + list decoding ⇒ MCA → c5 subspace design ⇒ curve list-decodability → c6 main theorem | Dependency graph: Lemma 3.2 → Theorems 3.3/3.4, Lemma 4.1 → Theorem 4.7 → Theorem 4.8, plus packaged Theorems 4.5 and 2.23 | ✓ Fully consistent. B's Lemma 2.37 is included inside the proof of c5 in A; B also does not list it as a separate checkpoint. |
| Quantifiers in Lemma 3.2 | `∀ α, ∆(uα, cα) ≤ δ(1+ℓ/(t−ℓ))` and `|T|` is bounded by the same expression times n; premise `ℓ < t` | “At every coordinate, distance ≤ δ(1+ℓ/(t−ℓ)); the union of inconsistent coordinates has the same bound”; errata item 1 already flags that t > ℓ is necessary | ✓ Consistent. Both versions independently found the same boundary issue. |
| Parameters in Theorem 3.3 | err = a/|F|, slack = ℓ/t | “error a/|F| and slack ℓ/t” | ✓ Consistent. |
| Premises of Theorem 3.4 | List-decoding radius δ(1+ℓ/(t₁−ℓ)), list size L; q > (L+1)²ℓ; add `t₂ ≤ 2t₁`, `ℓ < t₁`, `ℓ < t₂` | “Curve list-decodability + list-decodability ⇒ (ℓ, δ, ((t₂−1)L+a)/|F|, ℓ/t₂)”; errata item 3 flags that distinctness is not proved and combining witness sets requires 2t₁ ≥ t₂ | ✓ Consistent. Both versions independently found the same proof gap and repair. |
| Conclusion of Lemma 4.1 | The output lies in `H ≤ C` with finrank < r | “The output lies in a subspace of dimension < r”; does not state H ⊆ C | ✓ Consistent. `H ≤ C` is the minimal strengthening required by the use in Theorem 4.7 (take the span of the output); this is not a disagreement. |
| Output of Theorem 4.7 | b = a·ε/(r+ε) (over ℚ, without rounding) | “(ℓ, 1−τ(r)−ε, a, a·ε/(r+ε))-curve list-decodable”; errata item 6 already flags that ε must be strict | ✓ Consistent. The rational threshold makes the formula hold exactly; for integer cardinalities it is equivalent to a threshold over ℕ (see deviation 1 in the component ledger). |
| Error bound in Theorem 4.8 | t·ℓ·(ℓ+1)·(m(1−τ)+2t²)/|F| (revised form) | Errata item 4: “The paper's err bound does not follow … the Lean main theorem uses a revised form that composes strictly”; it gives the same expression as A | ✓ Consistent. Both versions independently derived the same repair. |
| Range and assumptions in Theorem 4.8 | 2 ≤ m ≤ 4t, field size hq, 0 ≤ τ r ≤ 1, 1 ≤ t, 1 ≤ ℓ | Errata items 4/5/7 give the same set of assumptions | ✓ Consistent. |
| Definition of curve list-decodability | Strengthened-to-subsets form | B's checkpoint sheet does not detail the definition, but errata item 2 flags that Definition 3.1 needs the subset-strengthened form; Theorem 4.7's proof establishes that form | ✓ Consistent. Both versions independently found that Definition 3.1, read literally, does not imply the uses in Theorems 3.3/3.4. |

## Findings from the comparison

1. **No unresolved disagreements.** All six statements align in their mathematical objects, quantifier structure, and threshold formulas. Every difference concerns a paper-side issue (boundary conditions, accounting for err, and the literal strength of the curve list-decodability definition) found by both versions and repaired the same way, rather than a translation disagreement.
2. **The most valuable cross-check is the error term in Theorem 4.8.** Without knowing A's formulation, B independently composed the bounds from 2.23 + 3.4 + 4.7 and obtained the same conclusion: the printed formula cannot be composed, while the repaired version is the first printed term multiplied by (ℓ+1) (derivation in Section 4 of the component ledger). This rules out a casual formula change during translation.
3. **No second full Lean formalization was made.** This independent retranslation checks the shipped Lean against an independent plain-language restatement and errata list. A follow-up like the bciks20 process—an independent agent rewriting the statements from B and the definitions, then checking each one—remains future work and does not affect this conclusion.

## Final statements

`environment/app/Task/Basic.lean` (namespace `ProximityGaps`) contains six checkpoints corresponding one-to-one to Lemma 3.2, Theorems 3.3, Lemma 4.1, Theorem 3.4, Theorem 4.7, and Theorem 4.8 of ECCC TR25-166. Names, quantifier structure, and threshold formulas align item by item; all seven deviations are recorded in Section 3 of `concept-ledger.md`.
