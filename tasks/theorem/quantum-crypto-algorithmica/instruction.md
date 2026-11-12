# Task: Quantum cryptography from algorithmic assumptions

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean`
contains a definition layer and exactly one theorem, stated in full and
"proved" by `sorry` inside a marked slot. **Prove that theorem.**

The theorem comes from pseudorandomness. The *Forrelation distribution*
`F_n` is a distribution over pairs of Boolean functions
`f, g : {±1}ⁿ → {±1}`: first `f` is sampled uniformly at random, and
then, independently for each input `x`, the value `g(x)` is `±1` with
bias `trnc(√(ε2ⁿ)·f̂(x))`, where `ε = 1/(100n)`, `f̂` is the Fourier
coefficient of `f`, and `trnc` truncates to `[−1,1]`. A well-known
consequence of the theorem is pseudorandomness against
`AC⁰[2^poly(n), O(1)]` circuits; the statement packaged here is the more
general bound: for `N = 2ⁿ` and any Boolean `C` on `2N` variables all of
whose `±1`-restrictions have level-2 Fourier mass
`L_{1,2} = ∑_{|S|=2} |Ĉ(S)|` at most `t`,

  |E_{(f,g)∼F_n}[C(tt f, tt g)] − E_{z uniform}[C(z)]| ≤ O(max(t,1)·log N/√N).

Two external facts are **packaged as hypotheses** (deep or textbook
results; your proof may assume them): a Gaussian-fooling theorem for
bounded level-2 Fourier mass (`gaussianFoolingProp`) and explicit Gaussian tail /
truncated-second-moment bounds (`gaussianTailProp`).

The single theorem you must prove:

`forrelation_pseudorandom` — there exists `K > 0` such that for every
`n ≥ 1`, every multilinear `C` on the `2N` variables that is `±1`-valued
on the cube, and every `t ≥ 0` bounding the level-2 Fourier mass of all
`±1`-restrictions of `C`, the displayed bound holds with constant `K`.

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).** The ±1 sign embedding `sgnVal` and the
  Walsh characters `chi`; the truncation `trnc`; the parameter `epsF`
  (`ε = 1/(100n)`); the Fourier coefficient `fhat`, the Forrelation bias
  `biasF`, the product weight `forrWt`, and the expectation functionals
  `forrExp`/`unifExp`; multilinear maps `mlEval` with their level-2 Fourier
  mass `fourierMass2` and `±1`-restrictions `restr`; and the packaged
  propositions `gaussianFoolingProp` and `gaussianTailProp`.
- **Checkpoint zone.** The main theorem stated in full, with proof `sorry`.

## Rules

- For verifier safety, executable commands `#eval`, `#exec`, `#exit`, and
  `#compile` are not allowed in submitted Lean files, including harmless
  diagnostics. Remove these commands before submission; the verifier rejects
  them before compiling the proof.
Replace the `sorry` with a complete proof. The development must compile with
`lake build` and must not use `native_decide` or new `axiom`s (both are
rejected by a lexical scan). A `sorry`/`admit` left in your own auxiliary
lemmas also zeroes the score, because the `#print axioms` check on the main
theorem never allows `sorryAx`. Do not modify the definition zone or the
theorem statement — the grader extracts the statement textually; if you need
auxiliary lemmas, add them as separate declarations below the
`-- END OF FIXED PART` line in `Task/Basic.lean` itself.

No `notation` / `macro` / `syntax` / `elab` / `macro_rules` / `initialize`
declarations anywhere in your solution — they are rejected as semantic-layer
rewriting. You may create auxiliary/scratch files (e.g. under `/app/Task/`
or `/tmp`) for exploration, but do not import them from `Task/Basic.lean` —
an `import` line at the top of `Task/Basic.lean` counts as a change to the
fixed part and scores 0. Auxiliary content used by the main proof must live
below the `-- END OF FIXED PART` line in `Task/Basic.lean` itself.

## Scoring

All-or-nothing: the score is 1 iff the development compiles with the main
theorem's slot free of `sorry`/`admit` and `#print axioms
ForrWalk.forrelation_pseudorandom` reports only the standard mathlib axioms
(`propext`, `Classical.choice`, `Quot.sound`); otherwise the score is 0.

## Environment

Lean 4 toolchain per `/app/lean-toolchain` with a local mathlib4 checkout
(`/opt/lean-lib/mathlib4`, cache pre-fetched). Build with `cd /app && lake
build`. No network access.
