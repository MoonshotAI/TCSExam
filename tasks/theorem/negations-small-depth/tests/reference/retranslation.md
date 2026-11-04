# Independent Retranslation — `lean-negations-small-depth`

This is the third independent-retranslation check under step 6 of the SOP. It compares a fresh rendering of the source with the finalized statements and records any ambiguities.

## Method and independence

The same subagent repeated the retranslation **at a different time and from a different text source**: the first pass used the full `pdftotext` output (`cbfmsy25.txt`); the second independently rewrote the checkpoint statements from the arXiv HTML version (`2512.19515v1`, extracted text retained in `/tmp/negations-html.txt`) and then diffed them item by item. Between the passes, the translator worked only on the grader and `task.toml` and did not revisit the first-pass wording. This record is not fully independent under the SOP's ideal standard of using different people/subagents, since the same agent did both passes; that limitation is recorded explicitly. The key ambiguity below has been cross-checked against the HTML source.

## Ambiguities and rulings

1. **Is the expression inside the square in (1) a sum or a product?** `pdftotext` rendered the inner Σ as Π in `P_G = Σ_a (Σ_{uv∈E} a_u a_v − 1)² · ∏ᵢ x_{i,aᵢ}` (in two places: equation (1) after Theorem 1.1 and the definition in §2.1). Evidence for the ruling: (a) expanding the proof of Lemma 2.1 as `Q = Q₂ − 2Q₁ + Q₀` (lines 585–613) works only with a sum, by `(X−1)² = X²−2X+1`; (b) the support characterization in Corollary 2.8, `{a : Σ_{uv} a_u a_v ≠ 1}` (lines 1050–1052; the Σ is not corrupted here in `pdftotext`), agrees with the sum; and (c) equation (1) in the HTML version is exactly `\left(\sum_{\{u,v\}\in E(G)}a_{u}a_{v}-1\right)^{2}`. **The product form is false** (its support would be the independent sets, inconsistent with fG). The finalized statement uses the sum form.
2. **“n variables” in Theorem 1.1 versus “n vertices” in §2:** Theorem 1.1's polynomial has n variables and is constructed from a graph with n/2 vertices (lines 122–124); all lemmas in §2 are stated for n-vertex graphs and 2n variables. The finalized statement follows §2's notation (n-vertex graph, variable set `Fin n × Bool`); the main theorem quantifies per graph. This is only a change of letter and does not affect the content.
3. **Endpoints of the balance interval:** The source has `[1/3, 2/3)·|X|` (line 791; same in HTML): closed on the left, open on the right. The finalized condition `n ≤ 3·Y.card ∧ 3·Y.card < 2·n` is the pointwise equivalent integer form (`|Y| ≥ n/3 ⟺ 3|Y| ≥ n`; `|Y| < 2n/3 ⟺ 3|Y| < 2n`). At n=3, the interval cannot be satisfied on both sides (small example 5), so c3/c4 require 4 ≤ n.
4. **“only contains monomials from P” in Lemma 2.3:** This means the support of each product gᵢhᵢ is contained in the support of P (lines 821–822), not equal to it. Finalized statement: `(p.g * p.h).support ⊆ P.support`. ✓
5. **Strict inequality in Lemma 2.6:** The source has `Pr[b ∈ R] < 2^{−ℓ/2}` (line 915), strictly. The finalized statement preserves `<`.
6. **Tail bound in Lemma 2.7:** `Pr[|M ∩ E_G(A,B)| ≤ γm] ≤ exp(−γm)` (lines 955–957). The event uses **≤ γm** and `exp` is the natural exponential. Finalized `expanderMatchingProp` has the same form; the constraint `γ ≤ 1` is a benign packaging restriction ([Sri20] uses an absolute constant γ), with no effect on the application.
7. **Rounding m = ⌈αn⌉ upward:** The finalized statement uses `⌈α * n⌉₊` (`Nat.ceil`).
8. **Quantifiers in Corollary 2.8:** “If G is an n-vertex expander graph, then S₊(P_G) ≥ 2^{Ω(n)}” is universal over all expander graphs, with an absolute constant in Ω. Finalized c7 has the same per-graph form, with c/N₀ existentially quantified outside the universal quantifier. ✓

## Result of the retranslation diff

All seven checkpoint statements in the second independent retranslation agree with the finalized versions in mathematical content; differences were only in phrasing and have been incorporated into the final statements (see the table above). The definition-layer concepts (`edgeCount`, `expVec`, `BalancedRectangle`, `BalancedPair`, `IsExpander`, `expanderMatchingProp`) also agree item by item between the second retranslation and the finalized version.
