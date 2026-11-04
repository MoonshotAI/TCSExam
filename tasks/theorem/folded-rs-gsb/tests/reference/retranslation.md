# Independent Retranslation Comparison — The CZ25 Folded RS-Code List-Decoding Chain

Cross-check of Lemmas 2.8, 2.10, 2.18, and 2.19; Theorems 2.11, 2.15, and 2.20; and Corollary 2.21.

This note compares two independently prepared “translations,” records how differences were adjudicated, and gives the resulting conclusions. It is one of three fidelity records for the L2 tier.

- Materials: Version A (shipped, `environment/app/Task/Basic.lean`, namespace `FoldedRSGSB`) contains Lean statements written after checking each item against the full text of arXiv 2408.15925v3. Version B is the checkpoint card at `checkpoint-card.md`, prepared directly from the paper's HTML **before** the Lean statements were written. It first drew a dependency graph, restated each lemma's premises and conclusion in plain language, and separately listed eight boundary conditions and paper errata. Adjudication uses the original arXiv 2408.15925v3 (sections 3 and 4 of the component reconciliation table).

## Sources and independence of the two versions

- **Version A (shipped):** Based on the structural content of §1.1, all of §2, and Appendices A and B. Each item was translated and checked against the paper, with boundary conditions repaired individually and supported by a counterexample or derivation.
- **Version B (checkpoint card):** Based on the same full text, but completed before Version A was finalized. It gives “one plain-language sentence per lemma + premise/conclusion elements + dependencies + errata,” without knowledge of Version A's Lean formulation.
- The paper itself is the only shared reference, so the two versions were prepared independently.

## Item-by-item comparison

| Decision point | Version A (shipped) | Version B (checkpoint card) | Adjudication |
|---|---|---|---|
| Chain order | c1 Wronskian criterion → c2 change of basis → c3 root supply; c4 flat partition → c5 loss bound; c3+c5 → c6 forced collision → c7 relaxed generalized Singleton bound → c8 capacity (main theorem) | Dependency graph: Lemmas 2.8/2.10 → Theorem 2.11, Lemma 2.18 → Theorem 2.15, 2.11+2.15 → Lemma 2.19 → Theorem 2.20 → Corollary 2.21 | ✓ Fully agree |
| Which result is the main theorem | Corollary 2.21 (= Corollary 1.4) | Same (“take Corollary 2.21 as the main theorem … Theorem 2.20 is its direct predecessor”) | ✓ Agree |
| Number of elements in Lemma 2.8 | Arbitrary t (repairs overlapping paper notation) | Errata item 5 says the same | ✓ Agree (both versions independently identified the same notation overlap) |
| k ≥ 1 in Lemma 2.8 | Not added (when k = 0, both sides of the iff are simultaneously true or false) | “Degenerate test: k = 0 … hence do not add a k ≥ 1 premise” | ✓ Agree |
| Edges in Theorem 2.11 | `e i ⊆ V` plus consistent evaluation within each block (weak form) | “Ship the weak premise ‘subset + consistent evaluation’ … proof unchanged” (errata item 6) | ✓ Agree |
| Making the geometric polynomial monic | Not included in the statement | Same in errata item 7 | ✓ Agree |
| Statement form of Lemma 2.18 | A block function p → Fin (ℓ+1), each block nonempty, and affDim of every transversal = ℓ | “∃ block function p … each block nonempty … ∀ reps …” | ✓ Agree; ℓ = 0 holds trivially, and premise 1 ≤ ℓ agrees with the paper's ℓ ∈ [L]; both versions match |
| Repair to Theorem 2.15 | Add `L ≤ s`, with counterexamples for s=1/L=2 | Errata item 1: “missing premise; proposition can be false (counterexample)” | ✓ Agree (both independently found the same missing premise and same counterexample construction) |
| Repair to Lemma 2.19 | Add `m − 1 ≤ s` | Same in errata item 2 (“when s < m−1, the premise is vacuously true while the conclusion can be false”) | ✓ Agree |
| Conclusion of Lemma 2.19 | `¬ Function.Injective f` | “∃ i ≠ j, fᵢ = fⱼ” | ✓ Agree (equivalent statements; negating Injective is idiomatic in Lean) |
| k bound in Theorem 2.20 | `k ≤ s * n` (exact injectivity budget) | Errata item 3 says the same (“k ≤ sn is exact and covers the paper's k ∈ [n]”) | ✓ Agree |
| Domain condition in Corollary 2.21 | Add `n < q` | Same in errata item 4 | ✓ Agree |
| Trivial branch in Corollary 2.21 | If 1−R−ε ≤ 0, the ball contains at most one point (the ball is empty when L=0) | Same in errata item 8 (“not mentioned in the paper's proof; Lean proof must handle separately”) | ✓ Agree |
| Definition of affine dimension | Difference-set span form from Fact 2.5 | “Fact 2.5 and Definition 2.2 are equivalent” (conventions section) | ✓ Agree |

## Analysis of disagreements (results of this check)

1. **No unresolved disagreements.** All eight statements agree item by item at the levels of objects, quantifier structure, and threshold formulas. Every difference is a paper-side issue independently identified and repaired in both versions (four omitted boundary conditions, a notation overlap, and a statement-level choice), rather than a translation disagreement.
2. **The two versions' most valuable cross-check is the pair of counterexamples for repaired premises.** Without knowing Version A's Lean formulation, Version B independently constructed the c5 counterexample at s=1/L=2 and the c6 vacuity argument at m=3/s=1. These match deviations 1/2 in Version A's concept-ledger and rule out the possibility that the premises were added casually during translation. Python small examples E7/E8 separately verify the numerical behavior of the counterexamples.
3. **A second full Lean formalization was not produced.** This independent retranslation provides cross-checking at the level of “independent plain-language restatement + independent errata list ↔ shipped Lean.” A follow-up modeled on bciks20—another agent rewriting the statements from Version B and the definition layer alone, then checking each item—is listed as future work and does not affect the current conclusion.

## Final version

`environment/app/Task/Basic.lean` (namespace `FoldedRSGSB`) contains eight checkpoint statements corresponding one-to-one to Lemmas 2.8, 2.10, and 2.18–2.19; Theorems 2.11, 2.15, and 2.20; and Corollary 2.21 of arXiv 2408.15925v3. Names, quantifier structure, and threshold formulas match item by item; all seven deviations are recorded in §3 of `concept-ledger.md`.
