# Task: The kissing number in dimension 13 — Open Construction

The **kissing number** in dimension `d` is the largest number of unit
spheres that can simultaneously touch a central unit sphere in `R^d`
without overlapping one another. Equivalently, it is the largest number
of points that can be placed on the unit sphere `S^{d-1}` with every pair
separated by an angle of at least 60°.

Exact kissing numbers are known only in dimensions 1, 2, 3, 4, 8 and 24
(dimension 3 is the classic "thirteen spheres problem", settled by
Schütte and van der Waerden 1953; dimension 4 by Musin 2008; dimensions
8 and 24 by Odlyzko–Sloane and Levenshtein 1979, via the E8 and Leech
lattices). From dimension 5 up, everything is open. In dimension 13 the
accepted interval is

    1154 <= kissing number <= 2064

- **Lower bound 1154** (a 1154-sphere configuration exists): V. A.
  Zinoviev and T. Ericson, *New lower bounds for contact numbers in
  small dimensions*, Problemy Peredachi Informatsii 35 (1999), 3–11;
  English translation in Problems of Information Transmission 35 (1999),
  287–294. This is the **current record**, and it has stood **unimproved
  for 27 years**: while the AI search community has been moving other
  dimensions (dimension 11's lower bound moved twice in the last 15
  months, from 592 to 593 by AlphaEvolve 2025, then to 604 by the
  EinsteinArena collaboration in 2026), dimension 13 has seen no
  progress since 1999.
- **Upper bound 2064** (no 2065-sphere configuration exists): D. de Laat
  and N. Leijenhorst, *Solving clustered low-rank semidefinite programs
  arising from polynomial optimization*, Mathematical Programming
  Computation 16 (2024), 503–534 — a semidefinite-programming bound.
- **Authoritative tracking**: Henry Cohn's kissing-number table,
  <https://cohn.mit.edu/kissing-numbers/> (: the
  dimension-13 row still reads 1154 / 2064).

Only the lower-bound direction is constructible: every valid
configuration is an explicit certificate. A certified configuration of
1155 points or more is a literature-level new result, beating a record
that has stood since 1999.

## What's in `/app/Task/Basic.lean`

In `/app/Task/Basic.lean`, below the line `-- END OF FIXED PART`, prove
the claim `submission_lower`:

```lean
theorem submission_lower : ∃ S : List (Fin 13 → Int), S.length ≥ n ∧ KissingConfig S := by
```

where **you choose the numeral `n`** — the larger the better. You may
change **only** the numeral in the claim statement; the claim body must
stay between its `-- CLAIM submission_lower BEGIN/END` markers.

The fixed definition layer (do not modify the code) gives you:

- `normSq x : Int` — the squared norm `‖x‖²` of an integer vector in `Z^13`
  (sum of the thirteen squared coordinates, exact integer arithmetic);
- `distSq x y : Int` — the squared distance `‖x − y‖²`;
- `isKissingConfig S : Bool` — the computable predicate "the list `S` is
  a valid kissing configuration": `S` is nonempty, every point is
  nonzero, and every pair of distinct positions satisfies
  `max ‖x‖² ≤ ‖x_i − x_j‖²` (computable, scans all position pairs);
- `KissingConfig S : Prop` — `isKissingConfig S = true`, the packaged
  certificate.

**Why the condition certifies a kissing configuration.** Write
`M = max ‖x‖²` and `m = min ‖x−y‖²`, with `M ≤ m`, and rescale all
points by `1/sqrt(m)`: then every pairwise distance is `≥ 1` and every
norm is `≤ 1`. For two points with `a = ‖x‖ ≤ b = ‖y‖ ≤ 1`,

    cos(angle(x, y)) = (a² + b² − ‖x−y‖²) / (2ab)
                     ≤ (a² + b² − 1) / (2ab) ≤ 1/2,

where the last step uses `a² − ab + b² = b² − a(b − a) ≤ b² ≤ 1`. So
every pairwise angle is at least 60°, and projecting the `S.length`
nonzero points radially onto the unit sphere places `S.length`
non-overlapping unit spheres around a central one.

Boundary behavior, aligned with the solver sibling task `kissing-d13`:
the zero vector is rejected (the projection argument needs nonzero
vectors), and duplicate points are rejected automatically — two copies
of the same nonzero point sit at squared distance `0 < max ‖x‖²`.

Bring your own point set as data — typically a `List (Fin 13 → Int)` built
by a small helper, e.g. `def pt (v : List Int) : Fin 13 → Int := fun k =>
v.getD k.val 0`, or a programmatic generator — and prove the claim, e.g.
`exact ⟨myPoints, by native_decide, by native_decide⟩`.
**`native_decide` is allowed and is the intended certificate path**: the
judge whitelists `Lean.ofReduceBool` and `Lean.trustCompiler`, alongside
the three standard axioms. The judge automatically lets `native_decide`'s
generated internal axioms (`._native.native_decide.ax_*`) through;
`native_decide` can be used directly.

**Representation is not the bottleneck here.** At the record region
`n ≈ 1154` the check scans ~1.3M ordered point pairs at thirteen integer
operations each — any `List` representation evaluates in seconds under
`native_decide`. (Only avoid exotic non-computable encodings: everything
must reduce by compilation.)

**Sanity anchors.** Two worked examples ship in the container as JSON
integer point lists (the same files as in the solver sibling task
`kissing-d13`), together with their deterministic generator:

- `/app/examples/example_cross26.json` — the 26-point cross polytope
  `{+-e_i}`: squared norms 1, pairwise squared distances 2 or 4, so the
  kissing condition holds. Proving `KissingConfig` for it exercises the
  whole pipeline — fixed layer, point representation, `native_decide`,
  and the claim interface.
- `/app/examples/example_d13_roots312.json` — the 312-point D13 root
  system `{+-e_i +- e_j}`: squared norm 2, pairwise squared distance
  `≥ 2`.
- `/app/examples/gen_examples.py` — regenerates both.

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
  the verifier parses `n` from the claim header.
- No `axiom` / `sorryAx` anywhere; `sorry` / `admit` only inside the
  claim body, and a body that still contains one is simply not scored.
  Every scored claim must depend only on the whitelisted axioms
  (`propext`, `Classical.choice`, `Quot.sound`, `Lean.ofReduceBool`,
  `Lean.trustCompiler`) — `#print axioms` is checked.

## How to work

You have a 12-hour budget and are expected to use it. Matching the
published record (1154 points) is the beginning of the work, not the end
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

The verifier re-checks your Lean proof, parses `n` from the proven claim,
and independently evaluates it against the published literature frontier
(1154 points, Zinoviev–Ericson 1999). **A strictly stronger
certified bound is always better, and there is no upper limit** — the
published record is the bar to beat, and beating it (any `n ≥ 1155`) is a
literature-level new result. The claim interface accepts `1 ≤ n ≤ 4000`;
a claim with `n > 2064` contradicts the published
semidefinite-programming upper bound (de Laat–Leijenhorst 2024).

## Environment

The project builds offline with `lake build Task` in `/app`.
Agent budget: 12 hours. The container has internet access. A helper `/app/snapshot.sh` mirrors your `/app/Task` workspace into `/logs/artifacts/` every 5 minutes once started — launch it early with `nohup /app/snapshot.sh >/dev/null 2>&1 &` so your work is preserved whatever happens later.

## Notes

- Known construction ladder in dimension 13: cross polytope 26 → D13
  roots 312 → the laminated lattice Λ13 with 906 minimal vectors → the
  record 1154 of Zinoviev–Ericson (1999), built from error-correcting
  codes. Code-based constructions have small integer coordinates, so the
  restriction to `Z^13` is not what stands between you and the record.
- **This frontier has been quiet for 27 years.** Recent AI-search work
  on kissing numbers concentrated on dimension 11 (AlphaEvolve 2025
  raised its lower bound from 592 to 593; the EinsteinArena
  collaboration reports 604, now reflected in Cohn's table). Dimension
  13 has not been in the line of fire: no improvement since 1999, and
  the gap to the upper bound (2064 / 1154 ≈ 1.79) is wider than in
  dimension 11 (868 / 604 ≈ 1.44). The next move is genuinely open.
- Tying the record means reproducing the 1154-point configuration of
  Zinoviev–Ericson 1999. The paper is published and available, but no
  machine-readable point list ships with it — a from-memory
  reconstruction is unlikely; treat a tie as already
  requiring real work. The result that matters is 1155 and above.
- Heuristics worth trying: greedy growth plus local swaps under a norm
  budget; Construction-A style gluing from binary/ternary codes;
  annealing on integer shells of fixed squared norm.
- The final check itself is seconds at these sizes.
