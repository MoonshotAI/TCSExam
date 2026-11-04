# Independent Retranslation Cross-Check — `lean-strategy-improvement-lb`

This note re-translates eight checkpoint statements from the original paper without consulting the written Lean statements, then compares them point by point with the shipped version. Ambiguities and rulings are recorded at the end.

Method: the written Lean statements were hidden, and each conclusion was rewritten as a formal mathematical statement using only arXiv 2309.02223v1; the result was then compared point by point with the shipped statements.

## c1 `initial_strategies_admissible`

- **Retranslation** (paper §4, paragraph 3 + Definition 2): G_n satisfies the three conditions for a sink game: (i) a_{n+1} is a sink (strictly minimum priority and only a self-loop); (ii) there is a player 0 strategy under which every cycle (except ⊤) has an even maximum priority—σ₀ is such a strategy: once a token enters any a_i it must eventually reach the sink, while player 1 can only trap it among d_1…d_n, whose cycles have even maximum priority; (iii) τ₀ is the dual strategy.
- **Shipped:** `Admissible0 (σ0strat n) ∧ Admissible1 (τ0strat n) ∧ IsSinkGame (Gn n)`. For (ii)/(iii), explicit witnesses σ₀/τ₀ are given (stronger than “there exists,” and retaining the source meaning); (i) is a structural field of `Gn` (proved during construction). Agree.

## c2 `optimal_strategies_char`

- **Retranslation** (paper §4, paragraph 4): For player 0 to maximize the value, from every start a_i the token must pass through d_{n+1} (the unique maximum even priority 2n+4; passing through it is equivalent to the 2n+4 coordinate of the value vector being 1). There is exactly one strategy achieving this from every a_i: σ(a_i)=a_{i+1} (i<n), σ(a_n)=d_{n+1}. For player 1 to minimize, from every d_i it must avoid d_{n+1}; the unique such strategy is τ(d_i)=d_{i+1} (i<n), τ(d_n)=a_{n+1}.
- **Shipped:** `IsOpt0 σ ↔ ∀ v, owner v = false → σ.1 v = (σstar n).1 v` (and the dual for τ). The definition of IsOpt (pointwise maximum/minimum value) matches the paper's “optimal strategy (maximizing Ξ pointwise)” (§2). “Only one strategy achieves this from every start” plus “achieving it is optimal” is combined into an iff. σ*/τ* take the unique legal outgoing edge at ⊤ and d_{n+1} (omitted in the paper because it is unique).
- **Correction on 2026-08-21** (after an adversarial falsification scan confirmed the defect): the original shipped statement expressed uniqueness as subtype equality `σ = σstar n`, which is literally false. Strategies here are total functions, so values at opponent-owned nodes are unconstrained and never read; changing σ at a d-node gives an optimal strategy unequal to σ*. The paper defines a strategy only on the player's own nodes, so uniqueness holds under its convention. The statement was fixed to require pointwise equality only on nodes owned by that player, matching the paper's reading. See deviation 8 in concept-ledger.

## c3 `exists_improving_edge` (Lemma 5)

- **Retranslation** (Lemma 5, verbatim in content): Let σ be a non-optimal strategy for player 0 or τ a non-optimal strategy for player 1; let σ̄ and τ̄ be their respective optimal counterstrategies. Then at least one of the sets I_σ ∩ {(v, τ̄(v)) | v ∈ V_0} and I_τ ∩ {(v, σ̄(v)) | v ∈ V_1} is nonempty.
- **Shipped:** Nonemptiness of the two sets is expressed in the form `∃ e ∈ improving0 σ, τb.1 e.1 = e.2` (expanding e = (v, τ̄(v))). Premises are made explicit: sink game + both strategies admissible (the context of Lemma 5, where SSI runs); optimal counterstrategy means attaining the value pointwise (existence is cited in the paper via [22, equation (11)] and proved in the definition layer). Agree.

## c4 `counter_edges_mem_J` (Lemma 6)

- **Retranslation** (Lemma 6): For any strategy pair σ, τ, every edge (v, σ̄(v)) belongs to J_τ(σ), and every edge (v, τ̄(v)) belongs to J_σ(τ). Expanding the definition in §3: when v ∈ V_1, Ξ_σ(σ̄(v)) ⊴ Ξ_σ(τ(v)); when v ∈ V_0, Ξ_τ(τ̄(v)) ⊵ Ξ_τ(σ(v)).
- **Shipped:** `memJ1 G σ τ v (σb.1 v)` expands to `owner v = true ∧ xi0 σ (σb.1 v) ≤ xi0 σ (τ.1 v)`. ✓ `memJ0` is dual. ✓ Premises are also explicit (Lemma 6's proof uses Ξ_σ = Θ_{σ,σ̄}, requiring existence of an optimal counterstrategy and the sink-game framework). Agree.

## c5 `counterstrategy_reset` (Observations 8 and 9)

- **Retranslation** (Observation 8): If σ(a_j) = a_{j+1}, then σ̄(d_j) = d_1 (from d_j, player 1 going through a_{j+1} makes the 2j+1 coordinate 0; going through d_1 and then a_j makes it 1, which is worse for player 1—a lower value). Dually, if τ(d_j) = d_{j+1}, then τ̄(a_j) = a_1. (Observation 9): under both phase conditions, Ξ_σ(a_j) ◁ Ξ_σ(d_j) and Ξ_τ(a_j) ◁ Ξ_τ(d_j); both comparisons differ at coordinates q ≥ 2j+1.
- **Shipped:** conjunction of three clauses, with j ∈ [2,n], phase conditions along the whole chain above j (σ(a_i) = a_{i+1} and τ(d_i) = d_{i+1} for every j ≤ i ≤ n), and both strategies admissible. Rulings: (a) the paper's σ̄ is an arbitrary fixed optimal counterstrategy; the argument gives a strictly lower value, so the universal quantifier is valid and used in the shipped version. ✓ (b) In the source, each reset clause needs only one phase condition; shipped version uses their union (merged with Observation 9), recorded as a weakening. (c) “differing coordinates ≥ 2j+1” is omitted, recorded as scope trimming. The lower bound j ≥ 2 is necessary (at j = 1, d_1 has no edge to d_1, so the reset clause is false as written; the paper's j is an induction level and always ≥ 2).
- **Correction on 2026-08-22**: the original shipped premise specified only the two single-edge phase conditions σ(a_j) = a_{j+1}, τ(d_j) = d_{j+1}, and was literally false. The argument in Observation 8 assumes the SSI phase-invariant context: the a-chain above j remains unbroken (σ(a_i) = a_{i+1} all the way to a_n → ⊤, without going through d_{n+1}); the claim that “player 1 aims to reach a_{j+1} without passing through d_{j+1}” holds only in that context. Counterexample (n = 3, j = 2; model-constructed and compilation-confirmed): σ takes a_1→a_2→a_3→d_4 (the single-edge premise holds). From d_2, player 1 strictly prefers following the d-chain d_2→d_3→⊤ (accumulating only even priorities 6 and 8) over the reset route or route through a_3 (both are forced by σ through d_4 and accumulate the graph's maximum even priority 10). Thus an optimal counterstrategy need not reset, and the first conjunct is false. The dual mechanism also falsifies the second conjunct: if τ sends d_3 directly to ⊤, player 0 from a_2 passes through a_3→d_4 and sees maximum even priority 10, strictly preferring it to reset. Repair: strengthen both single-edge premises to the full chain above j (∀ i, j ≤ i → i ≤ n → …), the actual phase invariant maintained in the induction for Proposition 7. The phase strategies in the induction (including the initial pair σ₀/τ₀) satisfy this premise. See deviation 9 in concept-ledger.

## c6 `improving_edge_gate` (Observation 10)

- **Retranslation** (Observation 10): Suppose σ(a_j) = a_{j+1} and τ(d_j) = d_{j+1}. The edge (a_j, a_1) can be improving only if σ(a_i) = a_{i+1} for every i < j−1 and σ(a_{j−1}) = d_j (otherwise switching this edge lets player 1 create an odd cycle with maximum priority 2j+1, making the new strategy inadmissible, so the edge cannot improve). The edge (d_j, d_1) can never be improving (dually, player 0 can create an even cycle with maximum priority 2j+2).
- **Shipped:** conjunction of the two conclusions, under the phase conditions and admissibility for both players. With 1-based node indices, “i < j−1” is translated as `1 ≤ i → i < j − 1` (for j = 2 the range is empty, leaving only the clause σ(a_1) = d_2, matching the paper's reading at j=2). Agree.

## c7 `switch_all_lower_bound` (lower-bound direction of Proposition 7)

- **Retranslation** (Proposition 7): If SSI starts from (σ₀, τ₀) on G_n using SWITCH-ALL, it finds an optimal strategy pair after 2^{n+1}−3 iterations, and that pair does not occur at any earlier iteration.
- **Shipped:** For any rule f that chooses an edge at every node with an improving edge, and any legal chain from (σ₀,τ₀), length ≤ 2^{n+1}−3 implies the endpoint pair is not simultaneously optimal. Differences: (a) only the lower bound is translated; the upper-bound claim “reaches it exactly then” is omitted because Theorem 1 does not need it; (b) SWITCH-ALL is universalized (the paper does not specify which edge to choose when there is a choice); (c) iterations and chain length differ by 1 (chain length = iteration count + 1). Agree on the lower-bound direction.

## c8 `ssi_exponential_lower_bound` (parity-game content of Theorem 1)

- **Retranslation** (Theorem 1): In the worst case, the number of iterations of symmetric strategy improvement on parity games (and mean-payoff/discounted-payoff games) is exponential in the numbers of vertices and edges, regardless of the improvement rule; this holds for all value functions currently used in the literature.
- **Shipped:** On G_n (2n+2 vertices, 6n edges), for any improvement rule there is no legal chain from the initial pair to an optimal pair of length ≤ 2^{n+1}−3; equivalently, the number of iterations is at least 2^{n+1}−3 = 2^{Θ(|V|)}. Scope trimming omits the mean-payoff/discounted-payoff and “all currently used value functions” cases (the paper obtains these by cited equivalence arguments). Agree for the parity-game result.

## Ambiguities and rulings

1. **Simultaneous optimality of “optimal counterstrategy”:** the paper's σ̄ simultaneously attains the minimum at all nodes (citing [22], equation (11)). Ruling: the definition layer proves existence of greedy counterstrategies (`counter1_isCounter`/`counter0_isCounter`) and defines IsCounter by “pointwise equal to the value,” matching the source and giving satisfiable premises.
2. **Range of j in Observation 8:** the paper does not explicitly state j ≥ 2, but at j = 1, σ̄(d_1) = d_1 is not a legal edge. Ruling: j ∈ [2, n], matching the induction level in Proposition 7.
3. **“i < j − 1” in Observation 10:** node indices start at 1, so use 1 ≤ i < j−1. At j = 2 this range is empty, as in the source.
4. **Choosing among multiple SWITCH-ALL edges:** the paper says “selects one improving edge for every node.” Ruling: quantify over every choice (small example E9 confirms the transferred direction is independent of the choice).
5. **Whether the self-loop at ⊤ counts as a “cycle” in a sink game:** Definition 2 explicitly says “except ⊤.” Ruling: plays reaching ⊤ have a finite count vector under `playVal` (not the cycle branch); negated Admissible predicates correspond only to non-⊤ odd/even cycles. ✓
6. **“Exponential in the numbers of vertices and edges” in Theorem 1:** G_n has 2n+2 vertices and 6n edges; the lower bound 2^{n+1}−3 = 2^{(|V|−2)/2+1}−3, hence 2^{Ω(|V|)}. Ruling: Lean states an explicit lower bound for each n and records vertex/edge counts in the docstring, without introducing separate asymptotic notation.
