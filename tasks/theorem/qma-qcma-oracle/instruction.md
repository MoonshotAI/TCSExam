# Task: Classical-oracle separation of QMA and QCMA

A Lean 4 (with mathlib) project lives in `/app`. `Task/Basic.lean`
contains a definition layer and exactly one theorem, stated in full and
"proved" by `sorry` inside a marked slot. **Prove that theorem.**

The theorem comes from quantum complexity. QMA is the quantum analogue of
NP: a polynomial-time quantum verifier checks a quantum witness state;
QCMA is the variant where the witness must be a classical bit string. The
theorem is a classical oracle separation between the two, stated through a
decision problem called *spectral Forrelation*: the oracle describes two
subsets `S, U` of the boolean hypercube, and the task is to decide whether
there is a quantum state whose standard-basis measurement distribution is
well supported on `S` while its Fourier-basis distribution is well
supported on `U` — equivalently, whether `‖Π_U · H^{⊗n} · Π_S‖²_op` is
large (yes instance, `≥ 59/100`) or small (no instance, `≤ 57/100`). The
theorem states: beyond a size threshold depending only on the resource
bound `a·n^a`, spectral Forrelation at gap `59/100` vs `57/100` has a
constant-query QMA verifier, while every classical-witness query algorithm
within the bound misclassifies some instance. Three proved facts are
packaged as hypotheses of the main theorem: the QMA amplification theorem
(`hMW`), the core-matrix concentration (`hConc`), and the bosonic
compressed-oracle sampling upper bound (`hUB`). The file also defines the
pure-state trace-distance proposition `traceDistanceProp`; the main
theorem does not assume it. Any use of that proposition requires a proof.

## Rules

- Do not modify the given definitions or the theorem statement — the
  grader extracts the statement textually. If you need auxiliary
  definitions or lemmas, add them as separate declarations below the
  `-- END OF FIXED PART` line in `Task/Basic.lean` itself.
- No new `axiom` declarations and no `native_decide`; the verifier
  rejects these lexically. `sorry`/`admit` left in the theorem slot
  score 0. A `sorry` in your own auxiliary lemmas is not scanned for,
  but if the main theorem's proof depends on it, the `#print axioms`
  check fails (`sorryAx` is never allowed) and the score is 0.
- Keep the `-- CHECKPOINT ... BEGIN/END` markers on lines of their own:
  the grader extracts the block textually, and a marker that shares its
  line with other text reads as a missing block.
- The project builds offline against the mathlib checkout at
  `/opt/lean-lib/mathlib4`; use `lake build` in `/app` to check.
- No `notation` / `macro` / `syntax` / `elab` / `macro_rules` /
  `initialize` declarations anywhere in your solution — they are
  rejected as semantic-layer rewriting.
- You may create auxiliary/scratch files (e.g. under `/app/Task/` or
  `/tmp`) for exploration, but do not import them from
  `Task/Basic.lean` — an `import` line at the top of `Task/Basic.lean`
  counts as a change to the fixed part and scores 0. Auxiliary content
  used by the main proof must live below the `-- END OF FIXED PART`
  line in `Task/Basic.lean` itself.

## Scoring

All-or-nothing: the score is 1.0 iff the whole development compiles
unchanged, the checkpoint slot contains no `sorry`/`admit`, and
`#print axioms QmaQcmaOracle.qma_qcma_oracle_separation` stays within the
standard mathlib axioms (`propext`, `Classical.choice`, `Quot.sound`).
Otherwise the score is 0.

## Notes

- Time budget: you have up to **12 hours** of wall-clock time for this task; the run is terminated when it expires.
