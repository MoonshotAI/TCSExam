# Task: Exponential worst-case lower bound for symmetric strategy improvement

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean`
contains a definition layer and exactly one theorem, stated in full and
"proved" by `sorry` inside a marked slot. **Prove that theorem.**

The theorem is about parity games. A parity game is played by two
players on a finite directed graph: a pebble moves along edges, the
owner of the current node chooses the move, and the winner is decided by
the parity of the largest priority seen infinitely often. *Strategy
improvement* evaluates a positional strategy by playing it against an
optimal counterstrategy and recording, for every start node, the *play
value* — the vector counting how often each priority occurs on the way
to the sink — and then switches to edges with a better valuation.
*Symmetric* strategy improvement (SSI) improves the strategies of both
players simultaneously, using each player's optimal counterstrategy to
select the other player's improving moves. The theorem states: an
explicit family of games `G_n` (with `2n+2` nodes) forces `2^{n+1} − 3`
iterations for **every** improvement rule — SSI needs exponentially many
iterations on `G_n` independently of the improvement rule. Formally: for
every `n ≥ 1` and every improvement rule `f`, no legal SSI iteration
chain on `G_n` starting from the initial strategy pair `(σ₀, τ₀)` whose
length is at most `2^{n+1} − 3` ends at a pair of optimal strategies.

## What's in `/app/Task/Basic.lean`

The fixed definition zone (do not modify) contains sink parity games
(`SinkGame`, positional strategies `Strat0`/`Strat1`), play values and their
total order (`PlayVal`; the `LinearOrder` instance is provided), valuations
(`xi0`/`xi1`), optimal counterstrategies (`IsCounter0`/`IsCounter1`),
improving moves (`improving0`/`improving1`), optimality
(`IsOpt0`/`IsOpt1`), improvement rules (`ImpRule`), one SSI iteration as a
step relation (`SSIStep`), legal iteration chains (`LegalChain`), and the
family `G_n` (`Gn`, `σ0strat`/`τ0strat`, `σ0τ0pair`). The main-theorem
statement follows the end-of-fixed-part marker.

## Rules

Replace the blank proof body of the main theorem with a complete proof. The
development must compile with `lake build` and must not use `native_decide`
or new `axiom`s (both are rejected by a lexical scan). Leftover
`sorry`/`admit` are scored, not rejected outright: the theorem slot must be
`sorry`-free to score, and a `sorry` in your own auxiliary lemmas zeroes the
score if the main theorem's proof depends on it (`#print axioms` never
allows `sorryAx`). Do not modify the definition zone or the theorem
statement — the grader extracts the statement textually; if you need
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

All-or-nothing: the score is 1 iff the whole development compiles with the
main-theorem slot filled and the main theorem depends only on the standard
mathlib axioms (`propext`, `Classical.choice`, `Quot.sound`); otherwise 0.

## Environment

Lean 4 toolchain per `/app/lean-toolchain` with a local mathlib4 checkout
(`/opt/lean-lib/mathlib4`, cache pre-fetched). Build with `cd /app && lake
build`. No network access.

## Notes

- Time budget: you have up to **12 hours** of wall-clock time for this task; the run is terminated when it expires.
