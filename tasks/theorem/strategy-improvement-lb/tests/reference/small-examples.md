# Small examples — lean-strategy-improvement-lb

This record checks the definition-layer predicates and test-point values by executing the definitions on small instances.

- Script: `ssi_sim.py` (pure Python mirror of the definition layer: G_n, game values, evaluations, optimal counter-strategies, and SSI iterations).

each row gives one example, its result, and what it checks. E1–E7 check definition behavior and test-point assumptions/conclusions at small scale; E8 checks the main theorem's value 2^{n+1}−3; E9 checks the direction of the “arbitrary improvement rule” transfer. At n = 1, 2, 3, the strategy spaces are small (|Strat| is on the order of 2·3^{n−1}·1), so all cases were exhaustively checked.

| Example | Result | What it checks |
|---|---|---|
| E1 | Passed (n=1,2,3) | Shape of the sink in G_n (`p(a_{n+1})=1` is a strict minimum, with a self-loop) and c1: σ₀/τ₀ are admissible (exhaust all opponent strategies and starting states; no game value is −∞ or +∞). |
| E2 | Passed (n=1,2,3) | c2: enumerate all strategies; the pointwise maximizing/minimizing evaluation strategies are **unique** and are exactly σ*/τ* (matching the characterization in section 4 of the paper). |
| E3 | Passed (n=1,2,3) | c3 (Lemma 5) at the initial strategy pair: the restricted improvement edge set is nonempty and computes to `S = {(a_1,d_2), (d_1,a_2)}` (matching Lemma 12's statement that “opening a₁ and d₁ opens both edges at once”). |
| E4 | Passed (n=1,2,3) | c4 (Lemma 6) at the initial strategy pair: every counter-strategy edge lies in J, checked point by point in both directions. |
| E5 | Passed (n=2, j=2; n=3, j=2,3, at every layer along the SWITCH-ALL trajectory) | Part of Observation 8 in c5: when the phase assumption holds, exhaustively check every pointwise optimal counter-strategy; at d_j it chooses d₁, and at a_j it chooses a₁ (both universally quantified clauses). |
| E6 | Passed (same phase points as E5) | Part of Observation 9 in c5: `Ξ_σ(a_j) ◁ Ξ_σ(d_j)` and `Ξ_τ(a_j) ◁ Ξ_τ(d_j)`. |
| E7 | Passed (same phase points as E5) | c6 (Observation 10): `(d_j,d_1)` never belongs to I_τ; whenever `(a_j,a_1) ∈ I_σ`, the alignment assumption `σ(a_i)=a_{i+1}` for 1≤i<j−1 and `σ(a_{j−1})=d_j` holds (the necessary direction of the gate condition). |
| E8 | Passed (n=1,2,3) | Numerical value in c7: SWITCH-ALL SSI from `(σ₀,τ₀)` takes exactly 1, 5, and 13 = 2^{n+1}−3 iterations to reach an optimal pair, with no earlier iteration optimal. The five-phase trajectory agrees phase by phase with the induction proof of Proposition 7. |
| E9 | Passed (n=2,3) | Direction of Lemma 12 used by c8: an improvement rule that skips irrelevant d₁ switches takes 5 and 13 steps, no fewer than SWITCH-ALL's 5 and 13 steps (“can only increase”). |

Additional notes:

- E8's exact arrival time also checks the chain-length conversion: k iterations correspond to chain length k+1. Thus the main statement “chain length ≤ 2^{n+1}−3 implies the endpoint is nonoptimal” is equivalent to “for ≤2^{n+1}−4 iterations the pair is nonoptimal,” and to the paper's statement that the optimal pair does not occur before iteration 2^{n+1}−3.
- The simulator also checks that the greedy counter-strategy (argmin/argmax evaluation) is pointwise optimal, as required by the definition-layer predicates `counter1_isCounter` / `counter0_isCounter`; it exhaustively checks the initial pair at n=1.
- n ≥ 4 was not run because the strategy space grows exponentially and exhaustive checking becomes infeasible. n ≤ 3 covers every structural branch, including the degenerate prefix at j=2 and the full phase at j≥3.
