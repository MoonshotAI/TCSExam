# Statement and sources: The Polar-Code Scaling Exponent

This note describes the current mathematical statement and its literature sources. It is for readers comparing the task with the Lean formalization.

The conjecture concerns the **scaling exponent of polar codes** (Arikan
2009, *Channel polarization: a method for constructing capacity-achieving
codes for symmetric binary-input memoryless channels*, IEEE Trans. Inf.
Theory 55(7)), in the form used by the finite-length-scaling literature
(Hassani–Alishahi–Urbanke, IEEE Trans. Inf. Theory 2014;
Mondelli–Hassani–Urbanke, IEEE Trans. Inf. Theory 2016).

Polar codes are the first explicit,
low-complexity codes proved to achieve channel capacity, and they are in the
5G control-channel standard. Send data at rate `R` over a binary memoryless
symmetric (BMS) channel `W` of (symmetric) capacity `I(W)`, with a polar code
of block length `N`, and keep the block error probability below a fixed
target. As `R` approaches `I(W)`, the required block length grows
polynomially in the reciprocal of the gap: `N = Θ((I(W) − R)^(−μ))`. The
number `μ` is the **scaling exponent** of the channel; it measures how fast
the `2^n` synthetic channels produced by the polar recursion polarize to
perfect or useless extremes.

The value of `μ` for the binary erasure channel (BEC) is `3.627`, computed by
Korada–Montanari–Telatar–Urbanke (ISIT 2010). It is conjectured that the same
exponent is **universal**: every BMS channel has scaling exponent `3.627`
(Mondelli–Hassani–Urbanke 2016). What is proved today for general BMS
channels is only `3.579 ≤ μ ≤ 4.63` (Hassani–Alishahi–Urbanke 2014;
Wang–Lin–Vardy–Gabrys 2022, improving `μ ≤ 4.714` of Mondelli–Hassani–Urbanke
2016). Closing this interval is the central open quantitative question of
polar-code theory.

This task uses the **threshold form** of the conjecture at the value 4.0,
which lies strictly inside the proved interval `(3.579, 4.63)`:

- `conj`: every BMS channel has scaling exponent **at most 4**. Proving it
  improves the best proved universal upper bound from 4.63 to 4.0.
- `refuted`: its negation — some BMS channel fails the rate-`2^(−n/4)`
  bound (scaling exponent at least 4). Proving it improves the best proved
  universal lower bound from 3.579 to 4.0.

The exact definition layer and quantified statements are in `environment/app/Task/Basic.lean`, with the scoring copy in `tests/reference/Basic.lean`. The `conj` and `refuted` statements are exact negations; proving either earns full credit. Finite illustrative checks are documented in `small-examples.md`.
