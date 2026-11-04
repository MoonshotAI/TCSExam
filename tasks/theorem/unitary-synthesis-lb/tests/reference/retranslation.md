# Independent Retranslation Cross-Check: Eight Statements in the LMW24 Chain

This record compares a second translation of eight checkpoints, derived from the paper without consulting the shipped Lean statements, against the shipped version. Ambiguities and disagreements are documented below.

- Source: full text of arXiv 2310.08870v1 at `lmw.txt`.
- The retranslation is the second of three fidelity records (independent retranslation).

## Method


## Checkpoint-by-checkpoint findings against the shipped statements

The second pass concluded (as quoted from `retranslation-independent.md`): c1 matches the paper; c2/c3 have a literal “real ≤ complex” type issue, and the proof establishes a modulus version; c3/c5/c7 have a possible division-by-zero issue when wt = 0; c4 matches the paper (the tail bound at v = 0 is read by a limit); c6's statement matches, but the paper's proof has a genuine flaw; c7 matches; c8 matches (M = 1 needs separate treatment).

**All eight shipped statements match the second retranslation line by line and need no changes.** The second pass suggested two treatments different from those actually used in the shipped version; these were adjudicated below. Three additional paper-side flaws do not affect the statements and are recorded here.

## Disagreements and adjudication

1. **Taking the modulus of decAdv (c2/c3):** Both passes independently reached the same conclusion: Definition 4.2 defines a complex-valued quantity, while the inequalities in Lemmas 4.3/4.9 compare real numbers; the proof takes Re and then the modulus. What is proved is the modulus version. The shipped statement uses `‖decAdv ...‖` (complex norm; see deviation 1 in `concept-ledger`). The versions agree. ✔
2. **Division by zero when wt = 0 (c3):** The second pass suggested adding a nonzero-row premise or truncating the index set. The shipped version takes a third route: Lean's totalized 1/0 = 0 gives the scaled matrix a placeholder value 0 on a zero row, which is exactly the correct value because the amplitude of a zero row is always 0. Thus V·ψ_h = D·wtVec and the c3 inequality still hold on zero rows. Small-example E2 exhaustively checks a zero row, and E5 exhaustively checks domination. Therefore c3 needs no extra premise; it is stronger than the version with an added premise and remains true. For c5/c7/c8, the proof still needs E[D†D] = Id and the weights to sum to 1, so it adds the explicit premise `∀ i, 0 < wt V i` (packaged as an assumption; see deviation 2 in `concept-ledger`). Adjudication: keep the shipped treatment. ✔
3. **Isometry premise in c1/c2:** The second pass included “V is an isometry” in the quantifiers, following the paper's context. Shipped c1 (typical amplitude) and c2 (decoupling) omit that premise: their proofs use only E[h(x)h(y)] = δ and Hermiticity of Pj, respectively, and do not depend on isometry. The statements without this premise are stronger and true (small-example E1 numerically checks the same identity for general random isometries, and the computation itself does not invoke isometry). Adjudication: keep the stronger shipped form. ✔
4. **Boundary v = 0 in c4:** The second pass noted that the paper's tail bound at v(Z) = 0 must be read as a +∞ limit. In the shipped Lean statement, the placeholder from x/0 = 0 gives exp(0) = 1; the right side is d1+d2 ≥ 1 ≥ probability. This is true but looser than the limit interpretation. The degenerate case v = 0 is equivalent to every C_k = 0 and has no practical effect. Adjudication: record that the shipped statement holds. ✔
5. **Dimension premise in c4:** The second pass read Tropp's original theorem as requiring d1, d2 ≥ 1. The shipped version requires only 1 ≤ d1+d2, covering a one-sided zero-dimensional case where the proposition still holds (see deviation 3 in `concept-ledger`). Adjudication: keep the broader true statement. ✔
6. **The case M = 1:** The second pass wrote “M = 1 implies ∆A ≡ 0” (isometry forces N = 1, so pA does not depend on h or f). The shipped version records E[adv] = 0, which holds for any V when M = 1 and does not require isometry. These agree within c8's scope, which includes the isometry premise; the main-theorem proof only needs E[adv] = 0. Adjudication: no conflict; small-example E9b verifies it numerically. ✔

## Paper-side flaws (statements are sound and do not include these claims)

- **Nonconstancy claim in the proof of Lemma 4.19:** The paper asserts that “|S|²−1 is nonconstant, so the infimum in ψ₁ is attained at some κ₂ > 0.” But degenerate cases such as |S|² ≡ 1 (m = 1 and |a₁| = 1, or m = 2 and a = (1/√2, i/√2)) make |S|²−1 ≡ 0, so the assertion fails. The result still holds (0 is subexponential for any parameter), but the proof needs another route. This burden belongs to the proof of c6 and does not affect its statement. The second pass found this independently; the first authoring pass missed it, so this is an additional contribution from the second pass.
- **Definition 4.23 (ψ₁ norm) mixes up κ and t; Lemma 4.15 omits “family” from its statement.** Both are typographical issues. This task's statement layer contains no ψ₁ norm, and the function family's domain is unambiguous, so neither matters.
- **Equation (24) has no absolute value around adv:** This agrees with the shipped version (“adv ≤ 1” holds without absolute values, and the M > e^K branch is unaffected).

## Open issues

No unresolved disagreements.
