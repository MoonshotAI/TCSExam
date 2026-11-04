# Task: Set covering

## Background

The **set covering problem (SCP)**: you are given `m` rows and `n`
columns. Every column `j` covers a fixed subset of the rows and costs an
integer `c_j > 0`. Choose a set of columns so that every row is covered by
at least one chosen column, at minimum total cost.

SCP is NP-hard, and unless P = NP no polynomial-time algorithm achieves an
approximation ratio of `(1 - o(1)) * ln m` (Feige's threshold; Dinur and
Steurer proved the tight form).

The public practice instances and the hidden judged instances are drawn
from the same public set-covering benchmark library. The hidden set is
constructed so that verbatim replay of published artifacts does not score
on it.

## Your job

Build a solver in `/app`. The shipped baseline, `/app/solver.cpp`
(Chvatal's greedy: repeatedly take the column with the smallest cost per
newly covered row, then a redundancy-removal pass), is a working solver
you can modify, wrap, reconfigure, or replace entirely — it also serves as
a living example of the I/O contract below.

You have a 12-hour run. When the run ends, the verifier rebuilds the tree
you left in `/app` exactly as described in Hard rules and judges the
resulting solver once on the hidden instances. That single judging is your
final score — nothing is judged while you work.

## Judging

| | |
|---|---|
| **Public practice set** | 48 instances at `/app/instances/`. `/app/public_reference.json` gives two reference values per instance: `B` (the shipped baseline's result) and `K` (a best-known value from stronger reference solvers). |
| **Judging sandbox** | **One local Docker worker**; per instance: 4 cores, 8 GB RAM; one shared time pool of 780 seconds covers all judged instances (30 s per instance x instance count) — no per-instance limit. This sandbox follows the task's official evaluation specification. |
| **Local self-test** | Use the public-instance runner described below. It executes in this development environment; local timing can differ from the judging environment. Self-tests never affect your final score. |
| **Final judging** | Once, after the run ends: the verifier rebuilds `/app` and judges your solver on **26 hidden instances**, again **in the same sandbox**. |
| **Score** | Determined solely by that one final judging. Hidden per-instance results are never returned to you; the formula that aggregates judging results into the final score is not disclosed. |

The final verifier runs on the evaluation host through Docker.
Development has no judging-service access. The public-instance
runner below supplies local feedback. Hidden instances are used
only once, after the development run ends.

## Input / output format (fixed — do not change the interface)

Your program reads an instance from **stdin** as a stream of integers
(whitespace is arbitrary):

- the first two tokens are `m` (rows) and `n` (columns);
- the next `n` tokens are the integer column costs `c_1 .. c_n`;
- then, for each row `i = 1..m`: a count `k_i` followed by the `k_i`
  column indices (1-based) that cover row `i`.

Your program writes a cover to **stdout**: the selected column indices
(1-based, whitespace-separated, each at most once), nothing else. Validity
= every index in `1..n`, no index repeated, and every row covered by at
least one selected column; the judge then recomputes the total cost
itself. Every shipped instance is feasible (every row is covered by at
least one column, every column covers at least one row).

## What's in the environment

- `/app/solver.cpp` — the baseline solver source. Rebuild with
  `bash /app/build.sh`, which produces `/app/solver`.
- `/app/instances/` — the 48 public practice instances.
- `/app/solutions/` — verified covers at exactly `K` for a few public
  practice instances, in exactly the solver output format above (each
  re-checked against its instance). Useful for testing your own checker.
- `/app/public_reference.json` — per public instance: the baseline's
  cover cost `B` and the reference value `K`.
- `python3 /app/run_public.py` — rebuilds `/app` via `build.sh`, runs your
  solver on the public practice set locally under one shared total time
  pool (same budget rule as the judge), validates the covers, recomputes
  costs, and prints per-instance results next to `B` and `K`. It runs on
  this development box, outside the judging sandbox — allow for differences between development and judging resources.

## Hard rules

- When the run ends, the verifier runs `bash /app/build.sh` (10 min limit)
  on the tree you left in `/app`. If it fails or does not produce an
  executable `/app/solver`, the total score is 0. All top-level `/app/*.cpp`
  files are compiled together by the shipped script; keep extra sources in
  subdirectories if you add many files.
- Your solver gets **one total time pool** covering the judged instances —
  1440 s over the 48 public instances in a self-test, 780 s over the 26
  hidden instances in the final judging (30 s per instance x instance
  count, as in the Judging table). There is **no per-instance limit** — you
  decide how to distribute the pool; on every run the remaining pool is
  handed to your solver in the environment variable `SCP_TIME_POOL`
  (seconds) and hard-killed when it is used up — right at the limit, with
  no grace period. A run killed at the limit, a crash, a nonzero exit, or
  an invalid solution scores 0 for that instance; the others still count.
- The output must be a valid cover (indices in `1..n`, none repeated,
  every row covered); the judge recomputes its cost and compares.
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
