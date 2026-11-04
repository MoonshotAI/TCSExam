# Task: Near-optimal alphabet-soundness tradeoff for two-query PCP

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean`
contains a definition layer and exactly one theorem, stated in full and
"proved" by `sorry` inside a marked slot. **Prove that theorem.**

The theorem comes from PCP combinatorics. An inner PCP encodes a linear
function `f : F_q^n → F_q` by its restrictions to subspaces, and the
soundness analysis works with *zoom-out function pairs* `(W, g)`: a
subspace `W` and a linear `g : W → F_q` agreeing with the encoding table
on a noticeable fraction of the `2ℓ`-dimensional subspaces `L` with
`Q ⊆ L ⊆ W`. A pair is `(C, ζ)`-*maximal* if no proper extension reaches
agreement `ζ·C`. The theorem states: under two packaged hypotheses (a
many-zoomouts refinement and a generic-family sampling bound), for every
`δ > 0` there is `ℓ₀` such that for all `ℓ ≥ ℓ₀` and all ambient
dimensions `n ≥ 2^{100}·q^ℓ`, for every table `T` on `F_q^n`, every
subspace `Q` of dimension `r₁ ≤ 10/δ`, and every `C ≥ q^{-2(1-δ³)ℓ}`, the
number of `(C, 1/5)`-maximal zoom-out function pairs with respect to `T`
on `Q` of ambient codimension at most `10/δ` is at most
`(160/δ)·C^{-2}·q^{100(t-1)!(10/δ)²ℓ/ξ}` (with `ξ = δ⁵` and
`t = ⌈2^{2+10/δ₂}⌉!`, `δ₂ = ξ/100`).

## Rules

- Do not modify the given definitions or the theorem statement — the
  grader extracts the statement textually. If you need auxiliary
  definitions or lemmas, add them as separate declarations below the
  `-- END OF FIXED PART` line in `Task/Basic.lean` itself.
- No `sorry` or `admit` anywhere in the final submission, no new `axiom`
  declarations, and no `native_decide`. The verifier checks this
  lexically and with `#print axioms`.
- The project builds offline against the mathlib checkout at
  `/opt/lean-lib/mathlib4`; use `lake build` in `/app` to check.
- No `notation` / `macro` / `syntax` / `elab` / `macro_rules` /
  `initialize` declarations anywhere in your solution — they are
  rejected as semantic-layer rewriting.
- You may create auxiliary/scratch files (e.g. under `/app/Task/` or
  `/tmp`) for exploration, but do not import them from `Task/Basic.lean`
  — an `import` line at the top of `Task/Basic.lean` counts as a change
  to the fixed part and scores 0. Auxiliary content used by the main
  proof must live below the `-- END OF FIXED PART` line in
  `Task/Basic.lean` itself.

## Scoring

All-or-nothing: `1.0` iff the project compiles with the main theorem
proved (its slot free of `sorry`/`admit`) and `#print axioms` of
`maximal_zoomout_count` stays within the standard axioms (`propext`,
`Classical.choice`, `Quot.sound`); otherwise `0.0`.

## Notes

- Time budget: you have up to **12 hours** of wall-clock time for this task; the run is terminated when it expires.
