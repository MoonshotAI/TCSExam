# Task: MaxCut

## Background

In the **maximum cut** problem you are given an undirected graph with a
(possibly negative, possibly fractional) weight on every edge, and you must
split the vertices into two sides so that the total weight of the edges
*crossing* the split — endpoints on different sides — is as large as
possible. MaxCut is one of Karp's 21 NP-complete problems. Its most famous
algorithmic result is the Goemans–Williamson 0.878-approximation, optimal
under the Unique Games Conjecture.

The public practice instances and the hidden judged instances are drawn
from the same public instance library for this problem. The hidden set is
constructed so that verbatim replay of published artifacts does not score
on it. The library publishes objective *values* only, never solution
vectors — there are no answer files to consult, so your solver has to
produce the cuts itself.

## Your job

Build a solver in `/app`. The shipped baseline, `/app/solver.cpp` (a
mid-strength tabu search from the vendored library), is a working solver
you can modify, wrap, reconfigure, or replace entirely — it also serves as
a living example of the I/O contract below. The full library source is
vendored at `/app/mqlib`.

You have a 12-hour run. When the run ends, the verifier rebuilds the tree
you left in `/app` exactly as described in Hard rules and judges the
resulting solver once on the hidden instances. That single judging is your
final score — nothing is judged while you work.

## Judging

| | |
|---|---|
| **Public practice set** | 105 instances at `/app/instances/`. `/app/public_reference.json` gives two reference values per instance: `B` (the shipped baseline's result) and `K` (a best-known value from stronger reference solvers). |
| **Judging sandbox** | **10 parallel shards**; per instance: **1 core**, 600 s wall clock (instances judged in parallel; shard containers with 16 cores/16 GB RAM are shared across them). This sandbox follows the task's official evaluation specification. |
| **Local self-test** | `python3 /app/run_public.py` — unlimited use. It rebuilds via `/app/build.sh`, runs your solver on the public practice set on this development box under the same 600 s per-instance limit, validates every output, and prints per-instance results. Self-tests never affect your score. |
| **Final judging** | Once, after the run ends: the verifier rebuilds `/app` and judges your solver on **45 hidden instances** in the judging sandbox described above. |
| **Score** | Determined solely by that one final judging. Hidden per-instance results are never returned to you; the formula that aggregates judging results into the final score is not disclosed. |

Nothing is submitted anywhere while you work — this environment has no
judging-service access at all. Your only feedback loop is the local
self-test above, which runs on this development box, outside the judging
sandbox: local wall-clock measurements may not transfer, so keep margin
below the per-instance limit instead of tuning to the edge of your local
timings.

## Input / output format (fixed — do not change the interface)

Your program reads a weighted undirected graph from **stdin** in the
library's instance format:

- lines starting with `#` (and empty lines) are comments;
- the first remaining line is `n m` (vertices are numbered 1..n);
- each of the following `m` lines is one undirected edge `u v w` with edge
  weight `w` (integer or fractional, possibly negative). Each edge appears
  at most once; there are no self-loops.

It writes a cut to **stdout**: exactly `n` lines, line `i` containing `0`
or `1` — the side of vertex `i`. Nothing else on stdout. The validator
checks that the output is a well-formed 0/1 assignment and recomputes the
objective by summing crossing edges (on fractional-weight families the
last digits depend on summation order; value comparisons use a small
relative tolerance).

## What's in the environment

- `/app/solver.cpp` — the baseline solver source. Rebuild with
  `bash /app/build.sh`, which produces `/app/solver`. The baseline's
  heuristic, budget, and seed can be overridden through environment
  variables (`MAXCUT_HEURISTIC`, `MAXCUT_SECONDS`, `MAXCUT_SEED`).
- `/app/mqlib` — the vendored library source (MIT), with its own CLI at
  `/app/mqlib/bin/MQLib` (`-l` lists heuristic codes), docs under
  `bin/` and `src/`, and the library paper under `paper/`. The
  library's evaluation data tables under `data/` are trimmed to the
  shipped 105 instances (see `data/README.md`).
- `/app/instances/` — the 105 public practice instances, already
  decompressed and ready to run.
- `mc_check` — the cut validator/evaluator, on PATH:
  `mc_check instance solution.txt` prints `OK <cut weight>` iff the
  solution is a well-formed 0/1 assignment; the weight is recomputed by
  summing crossing edges. The judge uses the same code. Source:
  `/opt/maxcut/mc_check.cpp`.
- `/app/public_reference.json` — per public instance: the baseline's
  cut value `B` and the reference best-known value `K`.
- `python3 /app/run_public.py` — rebuilds via `/app/build.sh`, runs your
  solver on the public practice set locally under the same 600 s
  per-instance limit, validates with `mc_check`, and prints per-instance
  results. It runs on this development box, outside the judging sandbox —
  treat timings as estimates, not authoritative measurements.

## Hard rules

- When the run ends, the verifier runs `bash /app/build.sh` (10 min
  limit) on the tree you left in `/app`. If the build fails or does not
  produce an executable `/app/solver`, the total score is 0. All top-level
  `/app/*.cpp` files are compiled together by the shipped script and
  linked against the library's static archive; keep extra sources in
  subdirectories.
- Your solver is run once per judged instance with a **wall-clock limit
  of 600 seconds per instance**, and it must **self-limit below 600 s** —
  the shipped baseline uses a 540 s internal budget (`MAXCUT_SECONDS`) to
  leave room for reading the instance and printing the cut. A run killed
  at the limit, a crash, a nonzero exit, or an unverifiable output scores
  0 for that instance; the others still count. Your solver only ever sees
  one instance at a time.
- The output must be exactly `n` lines of `0`/`1`. The validator
  recomputes the objective from the printed cut; printing a large number
  without a matching cut is worthless.
- The final score comes from a **fresh run** of your final build on the
  hidden instances, executed after your run ends.
- No network access.
- Do not try to read `/tests` — it is only mounted after your run ends.

## Fair play: live computation at judging time

At judging time your solver is rebuilt from source and run on the
judged instances under the stated per-instance limits. **It must
compute its solutions live, within those limits.** Submitting a solver
that emits answers precomputed during your development session —
embedded lookup tables of final answers, hard-coded "optimal"
solutions, or replayed stored results — instead of computing them is a
rule violation, whether or not the answers are valid. We audit the
submitted code and the session trajectory; if this task's final score
relies on embedded precomputed answers, the task is scored 0. Auxiliary
data produced in your session (bounds, intermediate incumbents, tuned
parameters) may be embedded only when the judged run still performs
genuine solving that produces the reported solution; simply printing a
stored final answer is never allowed.
