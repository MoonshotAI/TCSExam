# Independent Retranslation Cross-Check: Discrete-Bidding Games by Avni and Sadhukhan

This third provenance record independently re-translates the mathematical statements of each checkpoint and core definition from the paper, then cross-checks them against the finalized Lean statements. It records matches, disagreements, and adjudications. The intended readers are the authors and reviewers of `lean-discrete-bidding-games`; they are assumed to be theoretical computer science graduate students who have not read this project's history.

- Shipped Lean statements: `environment/app/Task/Basic.lean`, byte-identical to `tests/reference/Basic.lean`.
- Paper: Guy Avni and Suman Sadhukhan, *Mean-Payoff and Energy Discrete-Bidding Games*, CSL 2026 (EACSL Annual Conference on Computer Science Logic, LIPIcs 363, 32:1–32:18), abbreviated AS26; cross-checked against arXiv 2509.00506v1.
- Source of the model: Avni and Sadhukhan, *Computing threshold budgets in discrete-bidding games*, TheoretiCS 2025 (arXiv 2210.02773), cited below as [12].

## Method and evidence

- First, the statements were retranslated using only the paper text (`paper.txt`, extracted with pdftotext); only then were they compared with the finalized Lean statements.
- Page images were checked for Definition 2 (XX:5); trump and equations (1)–(3) (XX:7); Definitions 16 and 18 (XX:9–10); Theorem 19 (XX:10); Definitions 20–22 and Lemma 23 (XX:10–11); Definition 26 and Theorem 27 (XX:12); Observation 3 (XX:29).
- Executable small examples also cross-check all claims about game values and thresholds (`small-examples.md`). This report focuses on the statement forms.

## Retranslation of the definitions

| Object | Independent translation from the source | Comparison with finalized Lean | Finding |
|---|---|---|---|
| ⊕ (Definition 2) | x*⊕y = x⊕y* = (x+y)*; x⊕y = x+y; x*⊕y* = x+y+1 | `Bdg.add` agrees in every branch. | Match |
| ⊖ (Definition 2) | x*⊖y = (x−y)*; x*⊖y* = x−y; x⊖y = x−y; x⊖y* = (x−y−1)* | `Bdg.sub` agrees in every branch. The finalized definition makes subtraction total by truncating at 0; on its legal domain, the equations follow from `dbl_sub`. | Match (truncation is a convention, recorded) |
| trump (§3.1) | B ∈ ℕ*\ℕ and b ∈ ℕ imply trump = b; otherwise trump = b⊕0* | `Bdg.trump` agrees. | Match |
| Equations (1), (2), (3) | ewin takes the minimum over neighbors, elose takes the maximum; truncate at max{·,0}; when B⊕trump ≤ k*, take max, otherwise take ewin; µ_n = min_{b≤B} | `enWinN`/`enLoseN`/`enNextN`/`muN` agree. **The minimum ranges over the legal bid set** (disagreement R5 below). | Conditions match |
| Equation (4) | µ̃_n = µ_n if µ_n ≤ |V|kW, and ∞ otherwise | `muTilde` has the same shape; **the printed truncation bound is too small** (disagreement R4). | Conditions match |
| Definition 16 | Th(v) = min{B ∈ [k] : Energy(v,B) < ∞}; k+1 if there is no such B | `Th` + `Th_spec` agree (Energy is stated using the fixed point µ; the equivalence in Theorem 13 is covered by c4 and c5). | Match |
| Definition 18 | T(v) = ⌊(|T(v⁺)|+|T(v⁻)|)/2⌋ + ε; ε is 0 for even + ordinary, 1 for odd + starred, and * otherwise | `avgVal`/`AverageProperty` implement the dbl equation dbl(T(v)) = |T(v⁺)|+|T(v⁻)|+star(T(v⁻)). The two forms agree in all four cases after adjudicating R1/R2. | Match |
| Definition 20 | Trim(v,B) selects Th(v) or Th(v)⊕0* with the same star status as B; budget-agnostic means same type yields same bid (printed formal clause). | `Trim` agrees. `IsBudgetAgnostic` uses the stronger Trim form: the bid depends only on v and Trim(v,B), following the informal description in that passage and the uses in Definition 26/Remark 39. | Strengthened (recorded as deviation 5) |
| Definition 21 | If T(v⁻) ∈ ℕ, bT = T(v)⊖T(v⁻); otherwise bT = T(v)⊖(|T(v⁻)|+1). `bidT` matches the star status, and on a mismatch is bT⊕0*. | `bT`/`bidT` agree verbatim. | Match |
| Definition 22 | If T(v⁻) ∈ ℕ, A = {u : T(u) = T(v⁻)}; otherwise A = {u : T(u) ≤ T(v⁻)⊕0*}. | `allowedT` agrees verbatim. | Match |

## Retranslation of the checkpoints

| Checkpoint | Independent retranslation from the source | Comparison | Finding |
|---|---|---|---|
| c1 | “For every ⟨v, B⟩ and n ∈ N, Pres µ_n(v, B)-wins from ⟨v, B⟩ in G_n.” (verbatim from Lemma 6) | `PresWinsTrunc G n (muN n v B) ⟨v, B⟩`; expanding `PresWinsTrunc` gives “there exists a legal σ, for every legal τ, for every m ≤ n, M + sum(π≤m) ≥ 0,” exactly the G_n winning condition in §3.1. | Match |
| c2 | “Cons (µ_n(v, B) − 1)-wins from ⟨v, B⟩ in G_n.” (verbatim from Lemma 7) | Same shape as above; `hdet` (determinacy of reachable bidding games) is packaged as a premise, following the appendix's citations to [19]/[1]. | Match (packaging recorded) |
| c3 | The two monotonicity claims in Lemma 9, the fixed point in Definition 10, and budget antimonotonicity in Corollary 14. | Four-way conjunction; the Bellman equation `µ = phi µ` also holds at coordinates with µ = ∞ (the paper only uses finite coordinates). | Match (the stronger ∞-coordinate clause is recorded as deviation 3) |
| c4 | “If µ(v, B) < ∞, then σVI is a Pres' strategy by which she µ(v, B)-wins from ⟨v, B⟩ in G.” (verbatim from Lemma 11) | Existential form: there is a legal strategy that wins for Pres at value µ(v,B); the concrete construction of σVI belongs to the proof. | Match (existential form recorded as deviation 10) |
| c5 | “If µ(v, B) < ∞, then Cons (µ(v, B)−1)-wins from ⟨v, B⟩ in G. If µ(v, B) = ∞, then for every e ∈ N, Cons e-wins from ⟨v, B⟩ in G.” (verbatim from Lemma 12) | The two branches agree. At µ = 0, “µ−1” is −1 in ℤ, and Cons wins at −1 trivially when m = 0, matching the appendix's base case. | Match |
| c6 | The two inequalities in Lemma 23 plus all identities in Observation 3 (page images confirm: in the ordinary case T(v)⊖bT(v) = T(v⁻), in the starred case it equals |T(v⁻)|+1; T(v)⊕(bT(v)⊕0*) = |T(v⁺)|*; (T(v)⊕0*)⊖(bT(v)⊕0*) = T(v)⊖bT(v); (T(v)⊕0*)⊕(bT(v)⊕1) = |T(v⁺)|*+1). | The seven-way conjunction agrees. The finalized version adds premises that T's range is bounded by k+1 and T(v) ≤ k* (the paper's use context). | Match (premises are made explicit) |
| c7 | “The threshold budget Th : V → [k] ∪ {k+1} satisfies the average property.” (verbatim from Theorem 19) | `AverageProperty G G.Th` means ∀ v, Th v = avgVal Th v. | Match |
| c8 | Theorem 27 (checked against the page image): if B ≥ Th(v), there is a finite-energy M = (k+1)·(W + max_v Energy(v, Th(v))) such that σagn wins for M; σagn is budget-agnostic (constructed in Definition 26). | Single-strategy universal form: ∃ σ, legal and budget-agnostic, and for all ⟨v,B⟩ with B ≤ k* and B ≥ Th(v), σ wins for M; M is `mainEnergyBound`. | Match (domain of the maximum recorded as deviation 6) |

## Disagreements and adjudications

- **R1 (floor vs. ceiling):** pdftotext rendered the floor in Definition 18 as a ceiling; the page image (XX:10) confirms it is a floor. Adjudication: floor. A ceiling would add 1 in the odd and starred cases, contrary to the actual analysis in Appendix F.
- **R2 (“T(v⁻) ∈ ℕ*” in case (2) of Definition 18):** Read literally as the whole set, case (3), “otherwise,” is empty. Based on Appendix F (Case II is starred, Case IV ordinary), read it as “starred” (ℕ* \ ℕ). Adjudication: starred.
- **R3 (domain of the maximum in Theorem 27):** The printed formula is max_{v∈V} Energy(v, Th(v)), but Energy is ∞ when Th(v) = k+1. Adjudication: take the maximum only over vertices with Th(v) ≤ k*; treat all others as contributing 0.
- **R4 (truncation bound in equation (4)):** The printed bound is |V|kW, but the number of configurations is actually |V|(2k+2), with a concrete counterexample when k = 0 (true threshold 2 > 0). Adjudication: use cap |V|(2k+2)W; small example E10 verifies the corrected bound.
- **R5 (“{0, …, B}” in λ):** A literal interval in ℕ* would permit a non-owner to make a starred bid. Reading it under the explicit convention in [12] (non-owners bid ordinary integers only) makes value iteration agree exactly with the actual game value (small example E9). Adjudication: legal bids are ≤ B and, if starred, require a starred budget.
- **R6 (ewin/elose labels in Appendix F):** Several places print the elose form (maximum over neighbors, using B⊕trump) as ewin. Following the form of equation (2), interpret these as elose. No statements are affected.

## Conclusion

The eight checkpoints and all core definitions agree after independent retranslation. All six disagreements have been adjudicated and recorded in the deviation table in `concept-ledger`. No unresolved issues remain.
