# Task: The Ramsey number R(5,5) — Open Construction

The Ramsey number `R(5,5)` is the smallest `n` such that **every** red/blue
coloring of the edges of the complete graph `K_n` contains a monochromatic
`K5` (five vertices whose ten mutual edges all share one color). Its exact
value is one of the best-known open problems in combinatorics; the accepted
interval is

    43 <= R(5,5) <= 46

- **Lower bound 43** (a valid coloring of `K_42` exists): Geoffrey Exoo,
  *A lower bound for R(5,5)*, Journal of Graph Theory 13(1):97–98, 1989.
  This construction has stood for 37 years.
- **Upper bound 46**: Angeltveit–McKay, Journal of Graph Theory 2026
  ([arXiv:2409.15709](https://arxiv.org/abs/2409.15709), DOI
  10.1002/jgt.70029).
- **Authoritative tracking**: Radziszowski's dynamic survey *Small Ramsey
  Numbers* (Electronic Journal of Combinatorics, Dynamic Survey DS1),
  [revision #18, 2026-04-24](https://www.cs.rit.edu/~spr/ElJC/eline.html).
  The common conjecture is `R(5,5) = 43`.

## What's in `/app/Task/Basic.lean`

Prove a bound on `R(5,5)` inside Lean 4 + mathlib, in `/app/Task/Basic.lean`.
**Both directions count** — prove at least one of the two claim theorems
that ship in the file, for an `N` of your choice:

```lean
theorem submission_lower : ∃ c : Coloring N, MonoFree c
  -- a construction: R(5,5) >= N + 1

theorem submission_upper : ∀ c : Coloring N, ¬ MonoFree c
  -- a refutation: R(5,5) <= N
```

The definitions (`Coloring`: a symmetric edge 2-coloring of `K_N` on
vertices `Fin N`; `MonoFree`: no 5-vertex set has all ten edges in one
color) are fixed in the file above the line `-- END OF FIXED PART`. There
is no given instance, no witness, and no lemma ladder: you choose the
construction or the refutation argument and you prove it. A verified
`submission_lower` at `N = 43` would prove `R(5,5) >= 44`, breaking a
37-year-old record; a verified `submission_upper` at `N = 43` would prove
the conjectured exact value `R(5,5) = 43`.

## Rules

- For verifier safety, executable commands `#eval`, `#exec`, `#exit`, and
  `#compile` are not allowed in submitted Lean files, including harmless
  diagnostics. Remove these commands before submission; the verifier rejects
  them before compiling the proof.
  `native_decide` remains allowed as described in this task.
1. Do not change any **code** above the line `-- END OF FIXED PART`; the
   verifier compares it (comments stripped, whitespace-normalized)
   against its reference. Comments and docstrings up there are free to
   edit — they do not affect judging.
2. In each claim statement you may change **only the numeral `N`**
   (`1 <= N <= 64`); the claim body must stay between its
   `-- CLAIM ... BEGIN/END` markers.
3. No `sorry` / `admit` outside the claim bodies; a claim whose body still
   contains one is simply not scored. No `axiom`, no `sorryAx`, no
   `native_decide` anywhere. (`decide` is allowed.)
4. The whole file must compile, and every scored claim must depend only on
   the standard axioms `propext`, `Classical.choice`, `Quot.sound`
   (`#print axioms` is checked by the verifier).
5. Do not close `namespace R55`. Auxiliary definitions/lemmas are free.

## How to work

You have a 12-hour budget and are expected to use it. Matching the
published record (a coloring of `K_42`, or a refutation at `N = 46`) is the beginning of the work, not the end
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
frontier (lower bound: a valid coloring of `K_42`, Exoo 1989; upper
bound: `R(5,5) ≤ 46`, Angeltveit–McKay 2026). **A strictly stronger
certified bound is always better, and there is no upper limit** — the
published frontier is the bar to beat, and beating it (a construction at
`N ≥ 43`, or a refutation at `N ≤ 45`) is a literature-level new result.
(Vacuous lower claims at `N < 5`, where `K_N` has no 5-subsets, carry no
content; the textbook Erdős–Szekeres recursion gives `R(5,5) ≤ 70` — an
upper claim at that level is a warm-up, not a frontier result.)

## Environment

The project builds offline against the mathlib checkout at
`/opt/lean-lib/mathlib4`; use `lake build Task` in `/app` to check.
Agent budget: 12 hours. The container has internet access. A helper `/app/snapshot.sh` mirrors your `/app/Task` workspace into `/logs/artifacts/` every 5 minutes once started — launch it early with `nohup /app/snapshot.sh >/dev/null 2>&1 &` so your work is preserved whatever happens later.

## Notes

- A `decide`-based verification of a concrete coloring at `N = 13` takes
  about one minute inside this environment; budget your kernel computation
  accordingly.
- A certified published record only ties it; aim beyond.
- Known large constructions are highly structured (circulant or
  nearly-circulant patterns; see the solver sibling's instruction for
  search heuristics). Proving `MonoFree` at the record scale by brute-force
  kernel reduction is infeasible — you will need real structure, either in
  the construction or in the proof.
