# Task: The Ramsey number R(4,6) — Open Construction

The Ramsey number `R(4,6)` is the smallest `n` such that **every**
red/blue coloring of the edges of the complete graph `K_n` contains
either a red `K4` (four vertices whose six mutual edges are all red) or
a blue `K6` (six vertices whose fifteen mutual edges are all blue).
Equivalently — reading the red edges as a graph `G` and the blue edges as
its complement — `G` has no `K4` and no independent set of size 6.
The currently accepted interval is

    36 <= R(4,6) <= 40

- **Lower bound 36** (a valid coloring of `K_35` exists): Geoffrey
  Exoo, *On the Ramsey Number R(4,6)*, Electronic Journal of
  Combinatorics 19(1) #P66, 2012.
- **Upper bound, two readings**:
  - the strongest **formally published** value is `R(4,6) <= 41`
    (McKay–Radziszowski 1997, *Subgraph Counting Identities and Ramsey
    Numbers*, Journal of Combinatorial Theory B 69:193–209);
  - Radziszowski's dynamic survey (see below), latest revision #18
    (2026-04), reports the sharper `R(4,6) <= 40` from
    Angeltveit–McKay 2024, so far only as a personal communication,
    not yet in print.
- **Authoritative tracking**: Radziszowski's dynamic survey *Small
  Ramsey Numbers* (Electronic Journal of Combinatorics, Dynamic Survey
  DS1), [revision #18, 2026-04-24](https://www.cs.rit.edu/~spr/ElJC/eline.html),
  Table Ib. The true value can be any of 36, 37, 38, 39, 40 — the
  interval is four wide, and every step of it is open.

A useful known neighbor: `R(4,5) = 25` (McKay–Radziszowski 1995), so
valid colorings of `K_24` with no red `K4` and no blue `K6` certainly
exist — a `(4,5)-free` coloring is automatically `(4,6)-free`.

## What's in `/app/Task/Basic.lean`

Prove a bound on `R(4,6)` inside Lean 4 + mathlib, in
`/app/Task/Basic.lean`. **Both directions count** — prove at least one of
the two claim theorems that ship in the file, for an `N` of your
choice:

```lean
theorem submission_lower : ∃ c : Coloring N, MonoFree c
  -- a construction: R(4,6) >= N + 1

theorem submission_upper : ∀ c : Coloring N, ¬ MonoFree c
  -- a refutation: R(4,6) <= N
```

The definitions (`Coloring`: a symmetric edge 2-coloring of `K_N` on
vertices `Fin N`; `MonoFree`: no 4-vertex set has all six edges red,
and no 6-vertex set has all fifteen edges blue) are fixed in the file
above the line `-- END OF FIXED PART`. There is no given instance, no
witness, and no lemma ladder: you choose the construction or the
refutation argument and you prove it. A verified `submission_lower` at
`N = 36` would prove `R(4,6) >= 37`, breaking a record that has stood
since 2012; a verified `submission_upper` at `N = 40` would beat the
formally published record and match the sharpest survey-reported claim.

## Rules

1. Do not change any **code** above the line `-- END OF FIXED PART`; the
   verifier compares it (comments stripped, whitespace-normalized)
   against its reference. Comments and docstrings up there are free to
   edit — they do not affect judging.
2. In each claim statement you may change **only the numeral `N`**
   (`1 <= N <= 64`); the claim body must stay between its
   `-- CLAIM ... BEGIN/END` markers.
3. No `sorry` / `admit` outside the claim bodies; a claim whose body
   still contains one is simply not scored. No `axiom`, no `sorryAx`
   anywhere. Both `decide` and `native_decide` are allowed.
4. The whole file must compile, and every scored claim must depend only
   on the whitelisted axioms `propext`, `Classical.choice`,
   `Quot.sound`, `Lean.ofReduceBool`, `Lean.trustCompiler`
   (`#print axioms` is checked by the verifier).
5. Do not close `namespace R46`. Auxiliary definitions/lemmas are free.

## How to work

You have a 12-hour budget and are expected to use it. Matching the
published record (a coloring of `K_35`, or a refutation at `N = 41`) is the beginning of the work, not the end
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

The verifier re-checks your Lean proof, parses `N` from each proven
claim, and independently evaluates it against the published literature
frontier (lower bound: a valid coloring of `K_35`, Exoo 2012; upper
bound: `R(4,6) ≤ 41` in print, McKay–Radziszowski 1997, with `≤ 40`
reported in the dynamic survey as a personal communication). **A strictly stronger certified bound is always better, and there is no
upper limit** — the published frontier is the bar to beat, and beating it
(a construction at `N ≥ 36`, or a refutation at `N ≤ 40`) is a
literature-level new result. Note the flip side, honestly: a valid
coloring at `N = 40` would contradict the survey-reported upper bound of
40 (though not the formally published 41), and `N ≥ 41` contradicts the
published bound outright; a refutation at `N ≤ 35` contradicts Exoo's
published construction — unprovable territory, do not bother. (Warm-up
territory: valid colorings of `K_24` exist for free since `R(4,5) = 25`,
and the textbook Erdős–Szekeres recursion gives `R(4,6) ≤ 56`.)

## Environment

The project builds offline against the mathlib checkout at
`/opt/lean-lib/mathlib4`; use `lake build Task` in `/app` to check.
Agent budget: 12 hours. The container has internet access. A helper `/app/snapshot.sh` mirrors your `/app/Task` workspace into `/logs/artifacts/` every 5 minutes once started — launch it early with `nohup /app/snapshot.sh >/dev/null 2>&1 &` so your work is preserved whatever happens later.

## Notes

- Exhaustive verification of a concrete coloring by `native_decide`,
  phrased over 4- and 6-subsets (`Finset.powersetCard`), is cheap only
  at small sizes — a few thousand target subsets compile in seconds
  (measured: `N = 14`, about 4,000 subsets, 16 s), while `N = 24`
  (134,596 six-subsets) exceeded 40 minutes in this environment and
  anything near the record scale (`N = 35`, about `1.6 x 10^6`
  six-subsets) is flatly infeasible by brute-force kernel or native
  reduction — reaching the record zone needs real structure, either in
  the construction or in the proof. Evaluating the fixed definition as
  written enumerates all `2^N` vertex subsets and is impractical even
  sooner — rephrase concrete checks over the relevant subset sizes.
  Kernel `decide` is orders of magnitude slower than `native_decide`.
- A certified published record only ties it; aim beyond.
- Known large constructions for small Ramsey numbers are highly
  structured (circulant or nearly-circulant patterns: the color of an
  edge depends on the difference `u - v mod N`). A structural shortcut
  for the blue side: in a `K4`-free red graph, the red neighborhood of
  any vertex is triangle-free, so a vertex of red degree 18 or more
  forces an independent set of size 6 inside its neighborhood (since
  `R(3,6) = 18`) — valid colorings have maximum red degree at most 17.
  See the solver sibling task `ramsey-r46` for search heuristics
  (simulated annealing, SAT encodings).
- For the upper direction there is currently no mass-production route:
  the published bound (McKay–Radziszowski 1997) and the sharper
  survey-reported value (Angeltveit–McKay 2024) come from research-level
  exhaustive computation over graph classes, which cannot be replayed
  inside the Lean kernel within the verifier budget. The textbook
  Erdos–Szekeres recursion `R(s,t) <= R(s-1,t) + R(s,t-1)` yields
  `R(4,6) <= C(8,3) = 56` — the trivial bound; formalizing it
  is a genuinely provable warm-up, and a fully verified
  Lean proof at any `N <= 55` would be a research artifact in its own
  right. This door is left open for models that far exceed expectations.
