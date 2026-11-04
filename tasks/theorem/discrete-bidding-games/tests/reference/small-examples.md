# Executable Small Examples — `lean-discrete-bidding-games`

These small examples test the behavior of the task's definition-layer predicates and checkpoint statements.

- Script: `small_examples.py`, a pure-Python implementation of the definition layer: ℕ* budget arithmetic, bidding semantics, value iteration, threshold budget, average property, and a state-space fixed point for computing true game values. All checks E1–E10 passed when.

Each row gives a conclusion and what was checked. E1–E3 check core definition-layer arithmetic and rules; E4/E9/E10 use a state-space fixed point (controllable predecessor) independent of the paper's recurrence to cross-check checkpoint statements; E6/E7 check c7/c6 against the computed Th; E8 checks the paper's own numerical example (Figure 2 / Example 24).

| Example | Result | What was checked |
|---|---|---|
| E1 | Pass | `Bdg.add`/`Bdg.sub` match all eight starred combinations in Definition 2 value by value (exhaustive over 0..4), including `dbl(a⊖b) = dbl a − dbl b` on the valid domain |
| E2 | Pass | Ordering is 0≺0*≺1≺1*≺…; successor = ⊕0* and predecessor = ⊖0* are inverses (away from zero) |
| E3 | Pass | `trump` matches the paper's rule verbatim and, for each budget, is indeed Cons's least legal winning bid (minimality checked over the set of legal bids) |
| E4 | Pass | For the n = 1 truncated game, the true threshold (computed directly by ∀∃ over action sets) equals the `muN` recurrence value (Figure 1 + 30 random games, all configurations). This checks the n=1 content of c1/c2. |
| E5 | Pass | µ̃_n is monotone in n and antimonotone in budget (40 random games, n ≤ 5); first two statements in c3. |
| E6 | Pass | The computed Th satisfies the average property (Figure 2 + 60 random games), in the form dbl(Th(v)) = |Th(v⁺)| + |Th(v⁻)| + star(Th(v⁻)); this is c7. **During development, this example caught that the printed truncation bound |V|kW fails at k=0.** Counterexample: v1→v0 with weight −2, and a self-loop at v0 with weight 0; true threshold 2 > 0 = |V|kW. Replacing it with |V|(2k+2)W passes. |
| E7 | Pass | With T := Th, both inequalities of Lemma 23 and all five identities of Observation 3 hold (61 games); this checks c6. |
| E8 | Pass | Paper Figure 2 (Example 24, k=5): µ(v1, 1) = 2, matching the paper's statement that “σVI from ⟨v1,1⟩ requires only initial energy 2.” |
| E9 | Pass | `muN` recurrence equals the true value in the truncated game (state-space controllable-predecessor fixed point, restricted legal-bid semantics), with zero mismatches over 27 games × layers 1–3 × all configurations. This is the core cross-check of c1/c2. **During development, this determined the legal-bid convention:** allowing non-owner star bids literally under the ℕ* interval caused mismatches (1 case under LIT semantics, 5 under R12 semantics); the restricted semantics had no mismatches. |
| E10 | Pass | Fixed point µ equals the true unbounded energy threshold (greatest fixed point), over all configurations in 27 games; µ = ∞ exactly when the true threshold exceeds the cap. This checks c4/c5 and the safety of the corrected truncation bound. |

Additional notes:

- E9/E10 compute “true values” without using the paper's value iteration: on the finite state space (vertex × budget × energy × remaining rounds), they compute a controllable-predecessor fixed point (∃ move by our side, ∀ moves by the opponent). This is sufficiently independent to serve as a cross-check. Determinism of the reachability bidding game is the packaging premise `hdet`; E9/E10 compare values under that deterministic semantics (determinism itself is a theorem for the reviewed literature).
- Scale limits: because of the state-space size, E9 ran only through layer 3, |V| ≤ 3, k ≤ 3; E10 used the same scale. Larger-scale validation is handled by actual compilation on the remote builder.
