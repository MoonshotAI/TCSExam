# Small examples — lean-three-taxi

This record reports executable checks of the lean-three-taxi definition-layer predicates and test-point statements (second track of SOP step 6).

- Script: `small_examples.py` (pure Python recomputation of all definition-layer functions: tripodC / distContrib / matchSum / Mpot / SigmaPot / Phi / passiveB / timeToEdge / moveA2 / moveA3 / movePhase / reorgPhase; each corresponds line by line to a Lean definition; constants are exact fractions for the ε = 1/10 instance)
- Run record: 36/36 passed on the local machine with `python3 small_examples.py` (final line `ALL-OK (36 checks)`)

## Small-example checklist

each item lists the object checked and the result; all values are exact fractions (`Fraction`), with no floating-point error.

- **E1, tripod formula**: for an equilateral triple with edge length 2, the center has edge length 1; for a degenerate path (y lies between x and z), the center is y; the identity `xe+ye = xy` holds.
- **E2, Lemma 2.1 scan**: on 200 random line metrics (4 points with exact fractional coordinates), changes in each of the three corresponding edges are ≤ `d(w1,w2)`.
- **E3, trajectory shape from Appendix A**: use the scenario in Figure 4 of the paper with d1 = 5, u2 = 4, u3 = 2, er = 3, ℓ2 = 1, ℓ3 = 5 (ℓ3 > u3, so the path is fast and q3 passes e). `movePhase` outputs server = x3 (first reaches e, then r), s3 = d3; ℓ3 decays at relative rate 2 under case A; after reorganization, invariant `ℓ2″+ℓ3″ ≤ x1′x2′` holds.
- **E4, case B event sequence**: when ℓ < u, first move at constant speed (q reaches e exactly at t = u−L), then move fast (ℓ = u at synchronization); when ℓ ≥ u, `U = u/(1+b)`. If q turns back before reaching its origin, the remaining ℓ on arrival at e is `L₀−(2+b)U`; at arrival s = u0 and u = 0 (matching the three numerical lemmas for passiveB).
- **E5, case A decay**: when x2 reaches r, update ℓ2 by `max(0, Le − 2T)`; when x1 is near, serve the active taxi and s1 = d1.
- **E6, reorganization formulas**: numerical instances for line 17 (`min(ℓ+x1f, x1x2)`) and line 18 (`max(0, ℓ−x1x3)`); the invariant is preserved.
- **E7, potential values**: Φ is positive; Σ is 0 for disjoint intervals and `min(ℓ2,ℓ3) − q2q3` when they overlap.
- **E8, Lemma 3.2 grid scan**: 162 configurations (dd × center position × ℓ grid, including equality thresholds); minimum-matching comparisons and the iff condition `x₂ĝ ≤ x₂g` all agree (the two matchings have equal value at equality).
- **E9, pairwise Lipschitz scan for c4**: on 2000 random line metrics, moving an offline point by δ increases the distortion contribution by at most δ (numerical confirmation of the analytic tracking in section 4.1 of `concept-ledger.md`).
- **E10, calculation for Corollary 3.6 (not a separate test point)**: in a valid case B segment (`dd = 15.005`, `xie = 10`, `xje = 5.005`, `xjg = 5`, `ℓⱼ = 6`, `τ = 0.5`; matching assumption `xᵢe ≤ xᵢg` holds at equality), the endpoint increase rate for a fixed matching is 0.910 > 0.909 = `cⱼ(1−ψ)`, so the fixed-matching statement is false as written. Along the same trajectory, the contribution matched to r decreases (the `min` form is valid). This confirms that c6 states only the `min` form of Claim 3.4 and treats Corollary 3.6 as part of the proof.
- **E11, one-request telescoping smoke check**: cost and offline cost on a one-request trajectory are finite and nonnegative, and the semantic functions are computable.

## Issues caught by the small examples

- Initial counterexample parameters for E10 (`dd = 10`, `ℓ = 9`) used an incorrect hand calculation of ℓ's evolution (the “q turns back” rate −(2+b) was extended past the time q returned to its origin). Exact recomputation corrected the parameters to the current values (the violation occurs when ℓ falls below `xⱼg`); the conclusion that the fixed-matching version fails did not change. Deviation 5 in `concept-ledger.md` was updated accordingly.
- The first E2 version used floating-point values converted to fractions, losing precision and falsely failing an equality case for a degenerate line metric. Replacing them with exact fractional coordinates passed (no change to the task statement).
