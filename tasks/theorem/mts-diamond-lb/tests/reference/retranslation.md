# Independent Retranslation Comparison — The BCR23 Recursive Diamond-Graph Lower-Bound Chain

This note compares two “translations,” records how their differences were adjudicated, and gives the conclusions. It is one of three fidelity records for the L2 tier.

- Materials: Version A (shipped, `environment/app/Task/Basic.lean`, namespace `MTSDiamondLB`) contains Lean statements written by the task authors after checking each item against the full text of arXiv 2211.05753v2 (`bcr23.txt`). Version B is `retranslation-independent.md` (nine statement cards, independently retranslated by another subagent using only the full paper text, before seeing any Lean files or checkpoint design). Adjudication uses the original arXiv 2211.05753v2.

## Sources and independence of the two versions

- Version B used only the full paper text; its task required recovering each premise, quantifier, and boundary condition and marking possible OCR errors. When Version B was written, its author had not seen the Lean statements in Version A (neither side had seen the other's work).
- Version A used the same full paper text and was written before Version B was completed.
- The comparison is therefore independent in both directions: neither version knew the other's specific formulation.

## Item-by-item comparison

Each row covers one decision point; the adjudication column gives the conclusion and evidence.

| Decision point | Version A (shipped) | Version B (retranslation cards) | Adjudication |
|---|---|---|---|
| Construction base case and recurrence | M₀ = single edge (Bool, d=1); M_{w+1} is a cycle of 6m_w copies, with adjacent copies sharing special vertices | Same in card 1 | ✓ Verbatim agreement (small examples E1/E2 verify formula = graph shortest-path distance) |
| s/t antipodality | c1(i): diam(M_w) = d_w(s,t) for every w | Same in card 1; notes that the paper directly asserts this as a construction choice for general w without proof | ✓ Agree; Version A proves it by induction using geodesicity (numerically confirmed by small examples E2/E3); the property is included in c1 |
| Vertex-count recurrence | c1(iii) uses exact form 6m_w·(|M_w|−1) | Cards 1/8: the paper gives only the ≤ form; the exact form is Version B's own completion of the construction count | ✓ Both versions independently derive the exact form; the paper's ≤ form is looser than the exact expansion by at most a factor of 6m₀−1; recorded |
| Diameter recurrence | c1(ii): DD(w+1) = 3·m_w·DD(w) | Same in card 1, cross-checked by §3.5's “2·diam·C = 6m_w·C” | ✓ Agree (small example E2) |
| Notation and orientation for (S,S′,i,j) | `pairSet` = S in left copy i ∪ S′ in right copy j; the right-path copy is reversed by `swapW` (its own s faces global s) | Same notation in card 2; paper does not discuss orientation | ✓ Agree; the correct orientation is fixed by small-example evidence (reversing it gives c_opt > d(s,t), as recorded in the failed first version of E6); Version B's note that “stage 3 symmetry is passed over in one sentence” points to `swapW` |
| Sample space | Ω₀ is a singleton; Ω_{w+1} = (Ω_w)^{m_w}×(Ω_w)^{m_w}×(Ω_w)^{2m_w}×{0,1}^{m_w} | Card 2: one list of i.i.d. copies (usage ≤ 4m_w) plus m_w Bernoulli bits | ✓ Agree (the component decompositions package the same object in two ways) |
| Parameter of ε_i | Bernoulli(1/2) (uniform Bool sample) | Card 2: parameter omitted where §3.2 defines it; filled in as 1/2 from the introduction's “equal probability” and §3.3's “with probability 1/2” | ✓ Both versions independently make the same ruling |
| Base case ρ₀ and T₀ | ρ₀ = [{s},{t}], T₀ = 2, C₀ = 1 | Same in cards 2/7 (both fill values omitted from paper) | ✓ Both versions independently make the same ruling |
| Three-stage formulas | `stage1/2/3Seq` itemized, including `left(i)`/`right(i)` and `(∅,S,1,right(m_w)+i)` | Card 2 itemizes the same formulas, including `left+right = 2m_w+i` and the stage-3 number of terms = max{left,right} | ✓ Verbatim agreement (small example E5 executes the first and last terms and checks nonemptiness) |
| Padding | Pad with `{t}` to T_{w+1} = 4·m_w·T_w | Same in card 2 (same construction: max{left,right} ≤ 2m_w ⟹ total length ≤ 4m_wT_w; dummy set `{t}` has no extra cost) | ✓ Both versions independently make the same choice |
| Characterization of c_opt | c2: pointwise equality optCost = DD w (≥ from triangle inequality; ≤ by clearing the surviving path) | Same in card 3, with both directions expanded; notes that the paper gives only one line for ≥ | ✓ Agree (verified over all samples in E6) |
| Stage 1 lower bound | c3: E ≥ m_w·C_w·DD w, under premise EscLB w (C_w) | Same scaled form m_w·C_w in card 4; notes the paper only says “by induction” | ✓ Agree; Version A's comparison of the two switching options (same realization ⟹ actual cost ≥ induced cost) is an author-side proof and is recorded in the guided docstring (numerical direction agrees in E7) |
| Stage 2 lower bound and conditioning | c4: E ≥ (m_w/2)·C_w·DD w, under EscLB w (C_w) (repair using the escape price) | Same in card 4, which also copies the paper's acknowledged non-strict step and the repair in §3.5 | ✓ Agree |
| Cost of taking the alternate route | c4 docstring: ≥ (2·m_w+1)·DD w ≥ 2·C_w·DD w | Card 4 records both paper forms (§3.3 “2m_w ≥ C_w,” §3.5 “2m_w ≥ 2C_w”) | ✓ Agree; Version A uses the pointwise exact value (2m_w+1)·D_w, compatible with both paper expressions |
| Stage 3 probability input | c5: E|S−m/2| ≥ √m/4 (elementary expectation form, m ≥ 1) | Card 5: the paper invokes Berry–Esseen to obtain a constant-probability anti-concentration bound; the expectation form suffices for the accounting; “with high probability” is imprecise in the paper and is copied as stated | ✓ Agree (E8 numerically checked for m ≤ 60); Version A uses the stronger elementary mean-deviation form |
| Stage 3 lower bound | c6: E ≥ (3m_w/2 + γ₀√m_w)·C_w·DD w | Same in card 4, in the scaled form (3m_w/2 + Ω(√m_w))·C_w | ✓ Agree; both derive the identity for the number of blocks 3m/2 + |S−m/2| |
| Escape-price rule | `escCost`: pay p to stop the process, then pay nothing for the current or later steps; inductive invariant EscLB w C (escape price 2·C·DD w) | Same in card 6 (rule verbatim, p_w = 2·diam·C_w, and each term in the accounting (2+3.5m_w)C_w ≤ 6m_wC_{w+1} is explained) | ✓ Agree |
| Solving the recurrence | In c8 proof: C_{w+1} ≥ C_w + (γ₀/(3√2))√C_w ⟹ C_w ≥ w²/2592 | Card 7: sufficient induction condition a ≤ (c′/3)², C₀ = 1, and m_w = ⌈C_w⌉ jointly ensure monotonicity and rounding | ✓ Agree (numerical range checked in E9 for w ≤ 200) |
| Asymptotic size and inversion | log₂|M_w| ≤ 2w·log₂w (w ≥ 48) ⟹ w = Ω(log n/loglog n) | Card 8: |M_w| = exp(O(w·log w)), and flags exp(O(w²log w)) in the brief as a typo | ✓ Agree (Version A's design doc uses the paper's form; the typo in the brief did not enter any shipped statement) |
| Extension to n vertices | Cluster construction `ExtSpace` (new vertices at distance D_w and pairwise distance 2D_w); feasibility implies new vertices are never visited | Card 8: the paper says “extend arbitrarily / ignored in the request sequence” and gives the same expanded reason (distances are preserved and detours via new vertices are not cheaper) | ✓ Agree; Version A's cluster parameters (D_w/2D_w) are the simplest provably valid choice |
| Quantifier structure of the main theorem | ∃ c > 0 ∃ n₀ ∀ n ≥ n₀: distribution-witness form | Card 8: no numbered theorem in §3; Definition 2's κ quantifier is not eliminated in §3 | ✓ Agree on the distribution-witness form; both versions rule that the κ-absorption argument (repeating the round trip) is absent from §3 and should not enter the task |

## Analysis of disagreements (results of this check)

1. **No unresolved disagreements.** All nine cards agree item by item with the shipped statements on objects, quantifier structure, constants, and boundaries.
2. **Version B independently confirms four completions:** ε has parameter 1/2; base case ρ₀ and T₀; C₀ = 1; and fixed-length padding with {t} to 4m_wT_w. Version A reaches the same conclusions. Getting any of these wrong would directly change the truth of c2/c6.
3. **Version B flags four non-rigorous points in the paper:** the conditional expectation in stage 2, the “with high probability” wording, the lack of a proof for antipodality, and the unresolved κ. Version A's handling corresponds to each in order: repair the escape-price induction premise (c4/c7), use the elementary expectation form (c5), prove geodesicity by induction within the c1 proof, and use the distribution-witness form (c8).
4. Version B notes that the brief (task assignment) says |M_w| = exp(O(w²log w)), unlike the paper's exp(O(w·log w)). This was confirmed as an error in the assignment brief; Version A's shipped statements and design document use the paper's form, so it has no effect.

## Conclusion

The two versions agree on all statement-level decisions; the disagreement list is empty. Version A's Lean statements provide the faithful formalization of the BCR23 chain in §3.
