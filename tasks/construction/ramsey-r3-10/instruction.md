# Task: The Ramsey number R(3,10) — Open Construction

The Ramsey number `R(3,10)` is the smallest `n` such that **every**
red/blue coloring of the edges of the complete graph `K_n` contains
either a red `K3` (a triangle: three vertices whose three mutual edges
are all red) or a blue `K10` (ten vertices whose forty-five mutual edges
are all blue). Equivalently — reading the red edges as a graph `G` and
the blue edges as its complement — `G` has no triangle and no independent
set of size 10. The currently accepted interval is

    40 <= R(3,10) <= 41

- **Lower bound 40** (a valid coloring of `K_39` exists): Geoffrey Exoo,
  *On Two Classical Ramsey Numbers of the Form R(3,n)*, SIAM Journal on
  Discrete Mathematics 2 (1989) 488–490.
- **Upper bound 41**: Angeltveit, Electronic Journal of Combinatorics
  32(4) #P4.30, 2025.
- **Authoritative tracking**: Radziszowski's dynamic survey *Small Ramsey
  Numbers* (Electronic Journal of Combinatorics, Dynamic Survey DS1),
  [revision #18, 2026-04-24](https://www.cs.rit.edu/~spr/ElJC/eline.html),
  Table Ia.

The interval is one wide, and **either direction closes the whole
problem**: a valid coloring of `K_40` proves `R(3,10) = 41`; a refutation
at `N = 40` proves `R(3,10) = 40`. A useful known neighbor: `R(3,9) = 36`
is settled exactly (Grinstead–Roberts 1982), so valid colorings of `K_35`
with no red triangle and no blue `K10` certainly exist — a `(3,9)-free`
coloring is automatically `(3,10)-free`.

## What's in `/app/Task/Basic.lean`

Prove a bound on `R(3,10)` inside Lean 4 + mathlib, in
`/app/Task/Basic.lean`. **Both directions count** — prove at least one of
the two claim theorems that ship in the file, for an `N` of your choice:

```lean
theorem submission_lower : ∃ c : Coloring N, MonoFree c
  -- a construction: R(3,10) >= N + 1

theorem submission_upper : ∀ c : Coloring N, ¬ MonoFree c
  -- a refutation: R(3,10) <= N
```

The definitions (`Coloring`: a symmetric edge 2-coloring of `K_N` on
vertices `Fin N`; `MonoFree`: no 3-vertex set has all three edges red,
and no 10-vertex set has all forty-five edges blue) are fixed in the file
above the line `-- END OF FIXED PART`. There is no given instance, no
witness, and no lemma ladder: you choose the construction or the
refutation argument and you prove it. A verified `submission_lower` at
`N = 40` would prove `R(3,10) = 41`, settling a problem open since 1989;
a verified `submission_upper` at `N = 40` would prove `R(3,10) = 40` from
the other side.

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
   on the whitelisted axioms `propext`, `Classical.choice`, `Quot.sound`,
   `Lean.ofReduceBool`, `Lean.trustCompiler` (`#print axioms` is checked
   by the verifier).
5. Do not close `namespace R310`. Auxiliary definitions/lemmas are free.

## How to work

You have a 12-hour budget and are expected to use it. Matching the
published record (a coloring of `K_39`, or a refutation at `N = 41`) is the beginning of the work, not the end
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
frontier (lower bound: a valid coloring of `K_39`, Exoo 1989; upper
bound: `R(3,10) ≤ 41`, Angeltveit 2025). **A strictly stronger
certified bound is always better, and there is no upper limit** — and
here the interval is one wide, so beating the frontier on either side
**closes the problem**: a construction at `N = 40` proves `R(3,10) = 41`;
a refutation at `N = 40` proves `R(3,10) = 40`. Note the flip side,
honestly: exactly one of the two is mathematically possible — if the true
value is 40, no valid `N = 40` coloring exists; if it is 41, no
refutation at `N = 40` exists. (A lower claim at `N ≥ 41` would
contradict the published upper bound, and an upper claim at `N ≤ 39` the
published lower bound — unprovable territory, do not bother. Warm-up
territory: valid colorings of `K_35` exist for free since `R(3,9) = 36`,
and the textbook Erdős–Szekeres recursion gives `R(3,10) ≤ 55`.)

## Environment

The project builds offline against the mathlib checkout at
`/opt/lean-lib/mathlib4`; use `lake build Task` in `/app` to check.
Agent budget: 12 hours. The container has internet access. A helper `/app/snapshot.sh` mirrors your `/app/Task` workspace into `/logs/artifacts/` every 5 minutes once started — launch it early with `nohup /app/snapshot.sh >/dev/null 2>&1 &` so your work is preserved whatever happens later.

## Notes

- Exhaustive verification of a concrete coloring by `native_decide` at
  `N = 18` takes a few seconds inside this environment and grows like
  `2^N` (all vertex subsets are enumerated); kernel `decide` is orders of
  magnitude slower. At the record scale (`N = 39`, about `6 x 10^8`
  ten-subsets) brute-force kernel or native reduction is infeasible —
  you will need real structure, either in the construction or in the
  proof.
- A certified published record only ties it; aim beyond.
- Known large constructions for small Ramsey numbers are highly
  structured (circulant or nearly-circulant patterns: the color of an
  edge depends on the difference `u - v mod N`). A structural shortcut
  for the blue side: in a triangle-free graph the neighborhood of every
  vertex is an independent set, so any vertex of degree 10 or more hands
  you a blue `K10` for free — valid colorings have maximum degree at
  most 9. See the solver sibling task `ramsey-r3-10` for search
  heuristics (simulated annealing, SAT encodings).
- For the upper direction there is currently no mass-production route:
  the published bound (Angeltveit 2025) comes from research-level
  exhaustive computation, and a fully verified Lean proof at any
  `N <= 54` would be a research artifact in its own right. The textbook
  Erdos–Szekeres recursion `R(s,t) <= R(s-1,t) + R(s,t-1)` yields
  `R(3,10) <= C(11,2) = 55` — the trivial bound; formalizing
  it is a genuinely provable warm-up.
