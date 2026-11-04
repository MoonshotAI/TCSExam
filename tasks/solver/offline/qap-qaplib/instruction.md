# Task: Quadratic assignment problem

## Background

The **quadratic assignment problem (QAP)**: you are given `n` facilities and
`n` locations, a flow matrix `F` (flow between facilities) and a distance
matrix `D` (distance between locations). Assign each facility to a distinct
location — a permutation `p` where `p[i]` is the location of facility `i` —
minimizing the total flow-by-distance cost

```
cost(p) = sum_{i,j} F[i][j] * D[p[i]][p[j]]
```

QAP is NP-hard (it contains TSP as a special case) and, unless P = NP, no
constant-factor approximation exists (Sahni–Gonzalez 1976).

The public practice instances and the hidden judged instances are drawn from
the same public QAP benchmark library. The hidden set is constructed so that
verbatim replay of published artifacts does not score on it.

## Your job

Build a solver in `/app`. The shipped baseline, `/app/solver.cpp` (random
restarts + first-improvement 2-swap local search, fixed seed, small time
cap), is a working solver you can modify, wrap, reconfigure, or replace
entirely — it also serves as a living example of the I/O contract below.

You have a 12-hour run. When the run ends, the verifier rebuilds the tree
you left in `/app` exactly as described in Hard rules and judges the
resulting solver once on the hidden instances. That single judging is your
final score — nothing is judged while you work.

## Judging

| | |
|---|---|
| **Public practice set** | 75 instances at `/app/instances/`. `/app/public_reference.json` gives two reference values per instance: `B` (the shipped baseline's result) and `K` (a best-known value from stronger reference solvers). |
| **Judging sandbox** | **One local Docker worker**; per instance: 4 cores, 8 GB RAM; one shared time pool of 1230 seconds covers all judged instances (30 s per instance x instance count) — no per-instance limit. This sandbox follows the task's official evaluation specification. |
| **Local self-test** | Use the public-instance runner described below. It executes in this development environment; local timing can differ from the judging environment. Self-tests never affect your final score. |
| **Final judging** | Once, after the run ends: the verifier rebuilds `/app` and judges your solver on **41 hidden instances**, again **in the same sandbox**. |
| **Score** | Determined solely by that one final judging. Hidden per-instance results are never returned to you; the formula that aggregates judging results into the final score is not disclosed. |

The final verifier runs on the evaluation host through Docker.
Development has no judging-service access. The public-instance
runner below supplies local feedback. Hidden instances are used
only once, after the development run ends.

## Input / output format (fixed — do not change the interface)

Your program reads a QAP from **stdin** in the instance text format:

- the first token is `n`;
- the next `n*n` tokens are the flow matrix `F`, row by row;
- the next `n*n` tokens are the distance matrix `D`, row by row.

All tokens are integers, separated by arbitrary whitespace. Your program
writes a permutation to **stdout**: exactly `n` integers from `1..n`
(whitespace-separated, any layout), where token `i` is the location
assigned to facility `i`. Nothing else on stdout. Validity = being a
permutation of `1..n`; the judge then recomputes the cost from scratch.

## What's in the environment

- `/app/solver.cpp` — the baseline solver source. Rebuild with
  `bash /app/build.sh`, which produces `/app/solver`.
- `/app/instances/` — the 75 public practice instances.
- `/app/public_reference.json` — per public instance: the baseline's
  cost `B` and the registered best-known cost `K` (see the
  `proven_optimal` flag per instance).
- `python3 /app/run_public.py` — rebuilds `/app` via `build.sh`, runs your
  solver on the public practice set locally under one shared total time
  pool (same budget rule as the judge), validates the permutations,
  recomputes costs, and prints per-instance results next to `B` and `K`.
  It runs on this development box, outside the judging sandbox — allow for differences between development and judging resources.

## Hard rules

- When the run ends, the verifier runs `bash /app/build.sh` (10 min limit)
  on the tree you left in `/app`. If it fails or does not produce an
  executable `/app/solver`, the total score is 0. All top-level `/app/*.cpp`
  files are compiled together by the shipped script; keep extra sources in
  subdirectories if you add many files.
- Your solver gets **one total time pool** covering the judged instances —
  2250 s over the 75 public instances in a self-test, 1230 s over the 41
  hidden instances in the final judging (30 s per instance x instance
  count, as in the Judging table). There is **no per-instance limit** — you
  decide how to distribute the pool; on every run the remaining pool is
  handed to your solver in the environment variable `QAP_TIME_POOL`
  (seconds) and hard-killed when it is used up — right at the limit, with
  no grace period. A run killed at the limit, a crash, a nonzero exit, or
  an invalid solution scores 0 for that instance; the others still count.
- The output must be a permutation of `1..n` (checked by the judge; the
  cost is then recomputed and compared).
- The final score comes from a **fresh run** of your final build on the
  hidden instances, executed after your run ends.
- No network access during solver development or judging.
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
