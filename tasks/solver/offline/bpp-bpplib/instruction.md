# Task: One-dimensional bin packing

## Background

The **one-dimensional bin packing problem (BPP)**: you are given `n` items
with integer weights `w_1 .. w_n` and an unlimited supply of identical bins
of integer capacity `C`. Pack every item into bins so that no bin's total
weight exceeds `C`, using as few bins as possible. BPP is NP-hard — it is
NP-complete to decide whether two bins suffice.

The public practice instances and the hidden judged instances are drawn
from the same public bin-packing benchmark library; for every judged
instance a **proven optimal number of bins** is on record. The hidden set
is constructed so that verbatim replay of published artifacts does not
score on it.

## Your job

Build a solver in `/app`. The shipped baseline, `/app/solver.cpp` (plain
First-Fit Decreasing: sort by nonincreasing weight, place each item into
the first bin that still fits it), is a working solver you can modify,
wrap, reconfigure, or replace entirely — it also serves as a living
example of the I/O contract below.

You have a 12-hour run. When the run ends, the verifier rebuilds the tree
you left in `/app` exactly as described in Hard rules and judges the
resulting solver once on the hidden instances. That single judging is your
final score — nothing is judged while you work.

## Judging

| | |
|---|---|
| **Public practice set** | 90 instances at `/app/instances/`. `/app/public_reference.json` gives two reference values per instance: `B` (the shipped baseline's result) and `K` (a best-known value from stronger reference solvers). |
| **Judging sandbox** | **1 shard**; per instance: 4 cores, 8 GB RAM; one shared time pool of 1170 seconds covers all judged instances (30 s per instance x instance count) — no per-instance limit. This sandbox follows the task's official evaluation specification. |
| **Local self-test** | `python3 /app/run_public.py` — unlimited use. It rebuilds via `/app/build.sh`, runs your solver on the public practice set on this development box under the same shared time pool of 1170 seconds, validates every output, and prints per-instance results. Self-tests never affect your score. |
| **Final judging** | Once, after the run ends: the verifier rebuilds `/app` and judges your solver on **39 hidden instances** in the judging sandbox described above. |
| **Score** | Determined solely by that one final judging. Hidden per-instance results are never returned to you; the formula that aggregates judging results into the final score is not disclosed. |

Nothing is submitted anywhere while you work — this environment has no
judging-service access at all. Your only feedback loop is the local
self-test above, which runs on this development box, outside the judging
sandbox: local wall-clock measurements may not transfer, so keep margin
in your local time budget instead of tuning to the edge of your local
timings.

## Input / output format (fixed — do not change the interface)

Your program reads an instance from **stdin**:

- the first token is `n` (number of items);
- the second token is `C` (bin capacity);
- the next `n` tokens are the integer item weights, one per line in the
  file (whitespace is arbitrary).

Your program writes a packing to **stdout**: the first token is `B` (the
number of bins you use), followed by exactly `n` tokens where token `j`
is the bin of item `j` (1-based, every bin index in `1..B`, items in
input order). Nothing else on stdout. Validity = every item assigned,
bin indices in range, no bin over capacity; the judge then recomputes the
bin count itself. All weights are positive integers not exceeding `C`.

## What's in the environment

- `/app/solver.cpp` — the baseline solver source. Rebuild with
  `bash /app/build.sh`, which produces `/app/solver`.
- `/app/instances/` — the 90 public practice instances.
- `/app/library/` — 6,216 additional instances from the same library, for
  development and stress-testing; they overlap neither the public practice
  set nor the hidden set.
- `/app/bpplib_table.md` — per-instance table for every shipped instance:
  sizes, the library's registered best value, and the baseline's bin count.
- `/app/solutions/` — verified optimal packings for a few practice-level
  instances, in exactly the solver output format above (each re-checked
  against its instance). Useful for testing your own checker.
- `/app/public_reference.json` — per public instance: the baseline's bin
  count `B` and the proven optimum `K`.
- `python3 /app/run_public.py` — rebuilds `/app` via `build.sh`, runs your
  solver on the public practice set locally under one shared total time
  pool (same budget rule as the judge), validates the packings, recomputes
  bin counts, and prints per-instance results next to `B` and `K`. It runs
  on this development box, outside the judging sandbox — treat timings as estimates, not authoritative measurements.

## Hard rules

- When the run ends, the verifier runs `bash /app/build.sh` (10 min limit)
  on the tree you left in `/app`. If it fails or does not produce an
  executable `/app/solver`, the total score is 0. All top-level `/app/*.cpp`
  files are compiled together by the shipped script; keep extra sources in
  subdirectories if you add many files.
- Your solver gets **one total time pool** covering the judged instances —
  2700 s over the 90 public instances in a self-test, 1170 s over the 39
  hidden instances in the final judging (30 s per instance x instance
  count, as in the Judging table). There is **no per-instance limit** — you
  decide how to distribute the pool; on every run the remaining pool is
  handed to your solver in the environment variable `BPP_TIME_POOL`
  (seconds) and hard-killed when it is used up — right at the limit, with
  no grace period. A run killed at the limit, a crash, a nonzero exit, or
  an invalid solution scores 0 for that instance; the others still count.
- The output must be a valid packing (every item assigned exactly once,
  bin indices in range, no bin over capacity); the judge recomputes its
  bin count and compares.
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
