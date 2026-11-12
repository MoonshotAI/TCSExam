# Task: Packing 100 equal circles in the unit square — Open Construction

A Lean 4 project lives in `/app`. `Task/Basic.lean` contains a
definition layer and a claim slot (`submission_lower`) — prove the
strongest claim you can. The verifier independently evaluates your best
proven claim against the published literature frontier when the budget
ends; stronger is better, with no upper limit.

**Packing equal circles in a square**: place `n` non-overlapping circles of
equal radius `r` inside the unit square `[0, 1] x [0, 1]`, making `r` as
large as you can. A century-old problem, deceptively simple to state and
brutally hard to settle.

What is known:

- **Proven optima exist only for `n <= 30` and `n = 36`.** The classical
  cases `n <= 27` were settled one by one by many authors over decades; the
  last holdouts `n = 28, 29, 30` fell to Markót and Csendes (2005), *A New
  Verified Optimization Technique for the "Packing Circles in a Unit Square"
  Problems*, SIAM J. Optimization 16:193–219, using interval arithmetic. For
  every other `n >= 31` the problem is **open**: there are only best-known
  constructions, no optimality proofs.
- **The de-facto record table is maintained by Eckard Specht** (Packomania,
  *The best known packings of equal circles in a square*,
  `https://www.packomania.com/csq/csq.html`). The table header reads "Last
  update: 22-Aug-2022" ( — untouched for three years). The
  `n = 100` row stands at

  ```
  r = 0.0514010717743403  (216 touching pairs; the PECS repository value —
                           see the next bullet)
  ```

  For comparison, the naive **10x10 grid** achieves only `r = 1/20 =
  0.05` — the record is about 2.8% above the grid, and every last digit of
  it is fought for.

- **Where the record coordinates live.** The printed table value
  `0.051401071774` (12 digits) is rounded; Specht's own 12-digit coordinate
  file only supports `0.0514010717739` in exact checks (a hair below the
  print). The record-holders' own data repository — the PECS algorithm
  paper's companion repository (INFORMSJoC/2022.0004,
  `results/best_solutions/PECS/100_Sol.txt`) — holds the construction at
  full precision: the square side `L = 19.45484725280000049` with
  `r = 1/L = 0.0514010717743403`, independently recomputed from its
  coordinates. **The standing record is the PECS repository value
  `0.0514010717743403`** (full precision; it supersedes the rounded
  print, not the literature).

Only the lower-bound direction is constructible: every valid configuration
is an explicit certificate. A certified radius strictly above the PECS
repository value is a literature-level new result, beating a record that
has stood since at least 2022.

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).** The fixed definition layer gives
  you:

  - `distSq p q : Rat` — the squared Euclidean distance `‖p − q‖²` between
    two rational points (exact rational arithmetic, no floating point);
  - `isCircleConfig r S : Bool` — the computable predicate "the list `S` of
    rational centers with common radius `r` is a valid packing in the unit
    square": the radius is positive (`0 < r`), every center `(x, y)` sits in
    `[r, 1−r]²` (the boundary condition), and every pair of distinct
    positions satisfies `4r² ≤ ‖p_i − p_j‖²` (the non-overlap condition,
    checked in squared space so no square roots appear);
  - `CircleConfig r S : Prop` — `isCircleConfig r S = true`, the packaged
    certificate.

  **Why the condition certifies a packing.** A circle of radius `r` around
  `(x, y)` stays inside `[0, 1]²` exactly when `r ≤ x ≤ 1−r` and
  `r ≤ y ≤ 1−r`; two circles of radius `r` do not overlap exactly when their
  centers are at distance `≥ 2r`, i.e. (squaring the nonnegative inequality)
  at squared distance `≥ 4r²`. With `r > 0` the boundary clause also forces
  `0 < x, y < 1`, and duplicate centers are rejected automatically — two
  copies of the same point sit at squared distance `0 < 4r²`. This is the
  same constraint set as the checker of the solver sibling task
  `circles-in-square-n100`, clause for clause; the premise "exactly 100
  centers" is pinned in the claim as `S.length = 100`.
- **Claim slot.** Below the line `-- END OF FIXED PART`, prove the claim
  `submission_lower`:

  ```lean
  theorem submission_lower : ∃ S : List (Rat × Rat), S.length = 100 ∧ CircleConfig 0.05 S := by
  ```

  where **you choose the decimal literal `r`** (here `0.05`) — the larger the
  better. You may change **only** that decimal literal in the claim statement
  (write it as a plain decimal: digits with at most one decimal point, no
  exponent notation); the claim body must stay between its
  `-- CLAIM submission_lower BEGIN/END` markers.

  Bring your own point set as data — typically a `List (Rat × Rat)` of
  decimal literals, or a programmatic generator — and prove the claim, e.g.
  `exact ⟨myPoints, by native_decide, by native_decide⟩`.
  **`native_decide` is allowed and is the intended certificate path**: the
  judge whitelists `Lean.ofReduceBool` and `Lean.trustCompiler`, alongside
  the three standard axioms. The judge automatically lets `native_decide`'s
  generated internal axioms (`._native.native_decide.ax_*`) through;
  `native_decide` can be used directly.

  **Representation is not the bottleneck here.** At the record region the
  check scans 10000 ordered position pairs at a handful of rational
  operations each — any `List (Rat × Rat)` representation evaluates fast
  under `native_decide`. Every decimal literal is an exact rational: `d`
  digits after the point mean a denominator of `10^d`, and 30-digit
  coordinates are fine. (Only avoid exotic non-computable encodings:
  everything must reduce by compilation.)

**Sanity anchors.** A worked example ships in the container as a JSON
decimal point list (the same file as in the solver sibling task
`circles-in-square-n100`), together with its deterministic generator:

- `/app/examples/example_grid10.json` — the 10x10 grid at `r = 0.05`:
  centers `((2i+1)/20, (2j+1)/20)`, every constraint tight-but-exact
  (adjacent centers are `0.1 = 2r` apart, the outer ring sits exactly `r`
  from the boundary). Formalizing it exercises the whole pipeline —
  fixed layer, point representation, `native_decide`, and the claim
  interface.
- `/app/examples/gen_grid.py` — regenerates it; it can also produce
  overclaimed-radius variants to see how exact verification rejects them
  (an overclaimed `r` fails `4r² ≤ ‖p_i − p_j‖²` on the tight pairs, so
  such a claim simply does not prove here).

## Rules

- For verifier safety, executable commands `#eval`, `#exec`, `#exit`, and
  `#compile` are not allowed in submitted Lean files, including harmless
  diagnostics. Remove these commands before submission; the verifier rejects
  them before compiling the proof.
  `native_decide` remains allowed as described in this task.
- Do not change any **code** above the line `-- END OF FIXED PART`; the
  verifier compares it (comments stripped, whitespace-normalized) against
  its reference. Comments and docstrings up there are free to edit — they
  do not affect judging.
- Keep the interface name `submission_lower` and the pinned claim shape;
  the verifier parses `r` from the claim header.
- No `axiom` / `sorryAx` anywhere; `sorry` / `admit` only inside the
  claim body, and a body that still contains one is simply not scored.
  Every scored claim must depend only on the whitelisted axioms
  (`propext`, `Classical.choice`, `Quot.sound`, `Lean.ofReduceBool`,
  `Lean.trustCompiler`) — `#print axioms` is checked.

## How to work

You have a 12-hour budget and are expected to use it. Matching the
published record (`r = 0.0514010717743403`) is the beginning of the work, not the end
of it — do not submit early with only a tied record. Stronger is
better, with no upper limit.

Work in this order:
1. **Anchor check.** Verify the frontier values in the Background
   against the linked sources — if an anchor looks stale or wrong, say
   so in your final summary rather than trusting it blindly.
2. **Bank a claim early, then keep improving.** Get one certified
   claim on the board (a sanity cell exercises the pipeline; a fetched
   published construction ties the record), then keep pushing:
   improve your construction, try a different method, or attack a
   harder cell. Every strictly stronger certified bound counts for
   more. Keep going as long as you can generate distinct ideas —
   do not stop at a fixed count.
3. **Use the internet.** Look up the literature (constructions,
   records, techniques) rather than trusting training memory. Certifying
   a published record ties it; going beyond it takes a strictly
   stronger object the literature does not have.

The floor rules never change: a scored claim must not contain `sorry`,
planted axioms or redefinition tricks are rejected. Never fabricate a
proof.

## Scoring

The verifier re-checks your Lean proof, parses `r` from the proven claim,
and independently evaluates it against the published literature frontier
(`r = 0.0514010717743403`, the PECS repository value — see Background).
**A strictly stronger certified bound is always better, and there
is no upper limit** — the published record is the bar to beat, and
beating it (any certified `r` strictly above) is a literature-level new
result. Mind the precision game: Specht's own 12-digit coordinate file
supports only `0.0514010717739` in exact checks, a hair below the PECS
value, so reproducing the record takes the full-precision PECS
coordinates — every last digit is fought for.

## Environment

The project builds offline with `lake build Task` in `/app`.
Agent budget: 12 hours. A helper `/app/snapshot.sh` mirrors your `/app/Task` workspace into `/logs/artifacts/` every 5 minutes once started — launch it early with `nohup /app/snapshot.sh >/dev/null 2>&1 &` so your work is preserved whatever happens later.

## Notes

- The record packing has **216 touching pairs** — a rigid contact graph.
  The game is not finding a roughly-right layout (hexagonal-ish
  arrangements get you to ~0.0505 quickly) but squeezing out the last
  1e-9: simulated annealing or basin-hopping on the "maximize the minimum
  pairwise distance" objective, then LP-polishing the near-tight contacts,
  is the standard playbook (Specht's table credits exactly such methods).
- Everything here is exact rational arithmetic. If your optimizer runs in
  float64, its last few digits are noise: write coordinates with enough
  digits (15+ is cheap), and shrink `r` to within the last decimal digit
  of your coordinate precision — a claim whose coordinates do not support
  `r` exactly does not prove at all.
- A verbatim re-download of the published coordinate file lands a hair
  below the record (see Background): tying the record requires
  coordinates good to the last printed digit, and beating it requires a
  genuinely better construction than the published contact graph.
- The final check itself is seconds at these sizes.
