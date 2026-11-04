# Independent Retranslation Cross-Check — The Inner PCP Composition Core of MZ24

This note records the third of three fidelity checks: an independent subagent, without access to this task's Lean statements or checkpoint cards, formally retranslated 11 definitions, lemmas, and theorems from the paper and compared each statement against the shipped version. Disagreements and their adjudication are recorded below.

- Materials: The retranslator received the full paper text (from `pdftotext`, with OCR distortion warnings) and images of 12 key pages (pages 6, 7, 8, 34, 35, 38, 40, 41, 42, 43, 91, and 92). For each of §1.2.1's tests and obstacle 1, Definition 5.11, Lemma 5.12, Lemmas 5.13 and 5.14, Definition 5.22, Lemmas 5.23–5.25, Theorem 5.26, Lemma 5.18, and Theorem D.1, the retranslator drafted a strict statement, checked degenerate cases, and recorded internal contradictions in the text.

## 1. Cross-check results, item by item

Each row gives one item; the “Conclusion” column records agreement between the two versions. The statement structure agrees completely across all 11 items: quantifier structure, list of assumptions, constants, and exponents.

| Item | Retranslator's key point | Relation to shipped version | Conclusion |
|---|---|---|---|
| §1.2.1 tests and completeness | Sequential sampling; completeness is exactly 1; requires 0 ≤ ℓ₂ ≤ ℓ₁ ≤ n | Shipped version uses equivalent uniform sampling of pairs (bias 8); side conditions agree | Agree |
| §1.2.1 obstacle 1 | Exact equality q^{−ℓ₂} (not merely Θ), with uniform fibers under the restriction map | Shipped c2 agrees (existence follows by averaging over the full table) | Agree |
| Definition 5.11 | The codimension of the intersection of t distinct members is t·r; N < t is vacuously true | Shipped version agrees (`T.inf id` is a finite intersection plus the member premise) | Agree |
| Lemma 5.13 | The printed bound N^{1/j}/q^r is consistent with the last line of the proof; at most q^{jr} bad members per j-subset | Shipped c4 agrees (the early draft's concern about a factor of 2 was resolved on recheck: j! ≥ 2 absorbs the +s term; see §4 of concept-ledger) | Agree (shipped version follows the printed bound) |
| Lemma 5.14 | Smallest counterexample at r = 0, N = 1, m = 2; requires r ≥ 1 | Shipped c5 agrees (adds 1 ≤ r, bias 2) | Agree |
| Definition 5.22 | Three-conjunct structure; well-definedness requires dim Q ≤ 2ℓ ≤ dim W (not printed) | Shipped version agrees; well-definedness is handled by the 0/0 = 0 convention for `zoomProb` (degenerate-case analysis for each checkpoint is in §4 of the reconciliation table) | Agree |
| Lemma 5.23 | The printed Cζ^{−r} is the clearest printing error among all 11 items; the proof gives a (Cζ^k, ζ)-maximal object for some k ≤ r | Shipped c3: a (C′, ζ)-maximal object for some C′ ≥ Cζ^r, a closed statement of the iterative conclusion | Agree (see residual issue and adjudication 1) |
| Lemma 5.24 | For r ∈ {0,1}, printed conclusion 1 is unsatisfiable; the application restates it as 1 ≤ r′ ≤ r₂; standing assumptions are inherited from the prose | Shipped package adds 1 ≤ r, gives conclusion 1 in a uniform s form (bias 3), and states n ≥ 2^{100}q^ℓ explicitly | Agree |
| Lemma 5.25 | The β condition has additive c: (2q^{−2ℓ+r₁} + c); page image and proof are consistent in both directions. The tuple-sum bound is loose by a factor q/(q−1), which is absorbed | Shipped c6 uses the clean form 16/β² (bias 4); making 1 ≤ ℓ explicit absorbs the slack in the sum bound | Agree |
| Theorem 5.26 | Constants match term by term (160/δ, C^{−2}, exponent 100(t−1)!(10/δ)²ℓξ^{−1}); δ³ vs. δ⁵ is inconsistent, but safe in direction | Shipped main theorem agrees; environmental assumption strengthened to 2^{100}q^ℓ (bias 5) | Agree (see adjudication 2) |
| Lemma 5.18 | Use page image for j ≥ 2^{100r²a²}, dim ≥ 2^{100}j; conclusion 3q^{(r/2)(j−a)}/√m | Shipped package `GenericZoomSampling` agrees | Agree (page-image check; see adjudication 2) |
| Theorem D.1 | Matches page image item by item; defined only for γ ≥ 1/M | Shipped package `GenericListDecodingBound` adds 1/M ≤ γ (bias 7) | Agree |

## 2. Disagreements and adjudications

Three cases involved a substantive disagreement or an initial error by one side that was later corrected. Evidence and decisions are recorded here.

1. **Realization of Lemma 5.23.** The retranslator gave two candidates: the “exact form” (∃ k ≤ r, a (Cζ^k, ζ)-maximal object) and the “uniform weakest closed form” (a (Cζ^r, ζ)-maximal object), the latter relying on its §5.2 monotonicity claim that (X,ζ)-maximality passes to a smaller threshold. The primary translation rechecked this claim: the direction of the second conjunct is wrong (“no extension reaches ζX” does not imply “no extension reaches ζY”; the latter must rule out larger sets), so the (Cζ^r, ζ)-maximal closed form cannot be read directly from the proof. **Adjudication: the shipped version states that there exists C′ ≥ C·ζ^{ambCodim W} such that the object is (C′, ζ)-maximal.** This is equivalent to the retranslator's “exact form” (take C′ = Cζ^k) and does not rely on that monotonicity claim. Both sides agree that printed Cζ^{−r} is a typo.
2. **Whether the dimension premise in Lemma 5.18 is 2^{100}·j or 2^{100j}.** In its chain check of Theorem 5.26, the retranslator read 2^{100j} and reported a “three-level inconsistency in the environmental assumptions” (q^ℓ < 2^{100}q^ℓ < 2^{200ℓ}). The primary translation rechecked the page 38 image with a local enlargement (`pg-038.png`, region (500,230,600,70)): the print says 2^{100}j (100 is a superscript and j is on the baseline), so the dependence on j is linear. **Adjudication: 2^{100}·j.** This resolves the three-level inconsistency: for large ℓ, n ≥ 2^{100}q^ℓ gives dim(V⋆) ≥ 2^{100}·2ℓ (the exponential dominates the linear term). The retranslator's §10.1 expression, dim(W_amb) ≥ 2^{100}j, agrees.
3. **Constant factor in Lemma 5.13.** An early draft by the primary translator weakened the conclusion to N^{1/j}/(2q^r), citing a “+s term in the greedy deletion count and a printed bound off by a factor of 2^{1/j}.” The retranslator restated the printed bound N^{1/j}/q^r and checked it against the last line of the proof. On recheck, the primary translator verified that N ≤ s + C(s,j)·q^{jr}, for s ≥ j+1, closes as N ≤ s^j·q^{jr} using C(s,j) ≥ s and 2·C(s,j) ≤ s^j (j! ≥ 2); the cases s = j and s < j are covered separately by j^j ≥ j+1 and S′ = S. **Adjudication: ship the printed bound N^{1/j}/q^r; no deviation is recorded** (the reconciliation table's §4 retains the step-by-step calculation).

The retranslator also noted that the intermediate “C²M/4” in the proof of Theorem 5.26 should read C²M/16 (the final constant is unchanged), and that the prose describing the subfamily size is stronger than the lemma's output (with slack absorbed). These are proof-side typos; they do not change the statements, so the shipped main-theorem statement is unaffected. They are recorded for reference on the proof side (for model responses).

## 3. Remaining items

- Neither side opened the original [GRS00] source to check the original statement of Theorem 15. The fidelity of `GenericListDecodingBound` is therefore based on the paper's restatement in the page image; it is a packaging assumption and does not affect the proof of grading correctness. Verification status: Theorem D.1 is locator-only (checked against MZ24's restatement); all other items are content-reviewed.
- The retranslator's degenerate-case checks and the primary translator's SOP 6.5 self-check independently reach the same conclusions for r = 0 / ℓ₂ = 0 / N < j / m = 1 / the empty family (see §4 of the reconciliation table).
