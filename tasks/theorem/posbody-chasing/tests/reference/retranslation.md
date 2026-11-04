# Independent Retranslation — `lean-posbody-chasing`

This note records a second derivation and cross-check of the statement layer for `lean-posbody-chasing`, the third leg of the three-way fidelity check.

- Method: After the definition layer was finalized, the task-authoring agent independently derived the intended form of each of the eight checkpoints from `paper.txt`, without consulting the finalized Lean statements, then cross-checked each result against the Lean statement and adjudicated disagreements. Its independence is weaker than a retranslation by a different agent; this remains an open item (handled the same way for `lean-three-taxi`).

## Results of the second derivation and cross-check

| Checkpoint | Form from the second derivation | Cross-check against Lean statement |
|---|---|---|
| c1 | Sum the dual constraint multiplied by x'^t_i and apply Abel summation; boundary conditions must include x'⁰ = 0 and r'^{T+1} = 0 | Agree (see D3) |
| c2 | Σ_i w_i(x^t_i − x^{t−1}_i)⁺ ≤ (1+ε/4)y^t, t ∈ C | Agree |
| c3 | (1+ε/4)Σ_C y − (1+ε)Σ_P z ≥ 0 | Agree (see D5) |
| c4 | ((2+ε)(1+ε)/ε)(Σỹ − Σz) (explicit constant from the proof, α = 1/10) | Agree (see D2) |
| c5 | (1/w_i)(Σ_S c y − Σ_{P∩[s,t]} p z) ≤ log(1 + 4d·cmax_i(S)·x^t_i/ε) | Agree (see D7) |
| c6 | ∃ ỹ ∈ [0, y], (3.11) (∀ 1≤s≤t≤T ∀i) ∧ (3.12) (1−ε/10) | Agree |
| c7 | (ỹ/A, z/A, r̄) ∈ (D), with r̄ the max-prefix | Agree (see D4) |
| c8 | recourse ≤ K·baseline recourse, K = (2+ε)(1+ε)A/ε | Agree (see D2) |

## Disagreements and adjudications

- **D1 (scope of packaged KKT).** The first translation followed the paper verbatim and stated (3.4) for all i. During the second derivation, it was found that when x^{t−1}_i = 0 and p^t_i ≠ 0, monotonicity freezes that coordinate at 0. Under Lean's conventions (0/0 = 0, log 0 = 0), the verbatim equality is equivalent to p^t_i z^t = 0, although z^t > 0 is valid for the simulated algorithm in this case (an instance of this was observed in E5). Adjudication: the paper's statement for all i relies on convention (2.1), which covers a complete KL term with coefficients but not the bare log ratio. The two uses in the proof (the weighted form and the ≤ form) are both safe on degenerate coordinates. Therefore, Lean adds the premise 0 < x^{t−1}_i (concept-ledger, deviation 3). **The first translation was wrong and has been corrected.**
- **D2 (main-theorem constant).** The first translation stated the c8 conclusion as ∃ K (matching the paper's O(·) statement). On the second pass, the proof was checked and found to give a fully explicit chain of constants; the task statement should also avoid a vague “there exists a constant.” Adjudication: use explicit constants in both c4/c8: (2+ε)(1+ε)/ε and K = (2+ε)(1+ε)A/ε (concept-ledger, deviation 6). **The first translation was too weak and has been corrected.**
- **D3 (dual boundary).** The first translation's `DualFeas` omitted r'^{T+1} = 0. Abel summation in the second derivation showed this boundary condition is necessary; otherwise the final term x'^T·r'^{T+1} cannot be absorbed. Adjudication: add the condition (consistent with the definition that `rbar` is zero for s > T). **The first translation omitted it and has been corrected.**
- **D4 (degenerate case d = 0).** The first translation allowed d = 0. The second derivation found that Aconst = log 1 = 0 makes scaling ȳ/z̄/r̄ meaningless; also, d = 0 ⟺ no covering constraints ⟹ upward recourse is always 0, so the main theorem is trivial. Adjudication: add `hd : 0 < d` (concept-ledger, deviation 5). **The first translation omitted it and has been corrected.**
- **D5 (sign in (3.7)).** The final term in paper equation (3.7) is printed as “−w_i(x^T_i + x⁰_i),” while a term-by-term derivation in the second translation gives −w_i(x^T_i − x⁰_i). Adjudication: when x⁰ = 0 the two are equal, so this is a typesetting ambiguity in the paper and does not affect this task's statement, which assumes x⁰ = 0; recorded in §4.2 of concept-ledger. **No change to the statement.**
- **D6 (summation range in c2).** Both translations agree: sum over all i; coordinates outside the support contribute 0 by freezing, matching the paper. **No disagreement.**
- **D7 (range on the P side of c5).** The first translation incorrectly restricted the packaged summation to S. The second translation corrected this from the source text (“τ ∈ P : τ ∈ [s, t]”, independent of S, where S ⊆ C). **The first translation was wrong and has been corrected.**

## Remaining item

Both translations were done by the same agent, so independence is limited. If stronger assurance is needed, another agent could check the key calculations in §4 of concept-ledger (4.1–4.6) and the degenerate-coordinate argument in D1.
