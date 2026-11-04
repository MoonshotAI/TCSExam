# Task: The van der Waerden number W(2,7) — Open Construction

The **van der Waerden number** `W(2,7)` is the smallest `N` such that every
red/blue coloring of the integers `1 .. N` contains a monochromatic 7-term
arithmetic progression. `W(2,6) = 1132` was settled by Kouril–Paul (2008);
`W(2,7)` is the first open case:

- **The record construction is `W(2,7) > 3703`** (a valid 2-coloring of
  `1 .. 3703`): J. R. Rabung & Mark Lotts, *Improving the use of cyclic
  zippers in finding lower bounds for van der Waerden numbers*, Electronic
  Journal of Combinatorics 19 (2012), #P35
  ([DOI 10.37236/2363](https://doi.org/10.37236/2363)), built with a cyclic
  power-residue method ("cyclic zippers").
- **That method is saturated**: D. Monroe (JCMCC 128, published 2025-12)
  pushed the same search through every prime up to 9.5e8 — about 500
  CPU-years of distributed computation — without improving on 3703.
- **Upper bounds are not constructive territory**: the proven upper bounds
  on `W(2,7)` are Gowers-type towers. Only the lower-bound direction is
  constructible: every valid coloring is an explicit certificate.

A certified coloring of `1 .. 3704` or beyond is a literature-level new
result, beating a record that survived a 500-CPU-year search.

## What's in `/app/Task/Basic.lean`

In `/app/Task/Basic.lean`, below the line `-- END OF FIXED PART`, prove the
claim `submission`:

```lean
theorem submission : ∃ c : Nat → Fin 2, APFree c N := by ...
```

where **you choose the numeral `N`** — the larger the better. You may change
**only** the numeral in the claim statement; the claim body must stay
between its `-- CLAIM submission BEGIN/END` markers.

The fixed definition layer (do not modify the code) gives you:

- `hasMonoAP c a d : Bool` — the seven values `c a, c (a+d), …, c (a+6d)`
  are all equal (computable);
- `isAPFree c N : Bool` — the integers `1 .. N` (read off the total function
  `c`) carry **no** monochromatic 7-term AP (computable, scans every
  `a + 6 * d < N`);
- `APFree c N : Prop` — `isAPFree c N = true`, the packaged certificate.

Bring your own coloring as data — typically an `Array (Fin 2)` table plus a
lookup function — and prove the claim, e.g.
`exact ⟨myColoring, by native_decide⟩`. **`native_decide` is allowed and is
the intended certificate path**: the judge whitelists `Lean.ofReduceBool`
and `Lean.trustCompiler`, alongside the three standard axioms. The judge
automatically lets `native_decide`'s generated internal axioms
(`._native.native_decide.ax_*`) through; `native_decide` can be used
directly.

**Representation matters.** The record region is `N ≈ 3700`, where the
checker scans ~1.1 million arithmetic progressions, each doing 7 table
lookups. An `Array` gives O(1) lookups; a long `List` costs one traversal
per lookup and will not scale.

**Sanity anchors.** The sibling solver task `vdw-w27` ships an example
coloring of `1 .. 400` (found in seconds by min-conflicts local search).
Proving `APFree` for it exercises the whole pipeline — fixed layer, table
representation, `native_decide`, and the claim interface. Sanity-check
your pipeline on it (or any `N ≤ 400` construction) before aiming at the
record region.

## Rules

- Do not change any **code** above the line `-- END OF FIXED PART`; the
  verifier compares it (comments stripped, whitespace-normalized) against
  its reference. Comments and docstrings up there are free to edit — they
  do not affect judging.
- Keep the interface name `submission` and the pinned claim shape; the
  verifier parses `N` from the claim header.
- No `axiom` / `sorryAx` anywhere; `sorry` / `admit` only inside the claim
  body, and a body that still contains one is simply not scored. Every
  scored claim must depend only on the whitelisted axioms (`propext`,
  `Classical.choice`, `Quot.sound`, `Lean.ofReduceBool`,
  `Lean.trustCompiler`) — `#print axioms` is checked.

## How to work

You have a 12-hour budget and are expected to use it. Matching the
published record (a coloring of `1 .. 3703`) is the beginning of the work, not the end
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

The verifier re-checks your Lean proof, parses `N` from the proven claim,
and independently evaluates it against the published literature frontier
(`W(2,7) > 3703`, Rabung–Lotts 2012). **A strictly stronger
certified bound is always better, and there is no upper limit** — the
published record is the bar to beat, and beating it (any `N ≥ 3704`) is a
literature-level new result. (Claims at `N < 7` are vacuous: `1 .. N` has
no 7-term AP at all.)

## Environment

The project builds offline with `lake build Task` in `/app`.
Agent budget: 12 hours. A helper `/app/snapshot.sh` mirrors your `/app/Task` workspace into `/logs/artifacts/` every 5 minutes once started — launch it early with `nohup /app/snapshot.sh >/dev/null 2>&1 &` so your work is preserved whatever happens later.
