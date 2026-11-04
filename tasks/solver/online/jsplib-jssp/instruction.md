# Task: Job-shop scheduling

## Background

In the **job-shop scheduling problem (JSSP)** you are given `n` jobs and
`m` machines. Each job is a fixed chain of `m` operations; every operation
occupies one specific machine for a given processing time. A machine runs
at most one operation at a time; a job's operations must run in their
given order. The goal is to minimize the **makespan** — the moment the
last operation finishes.

JSSP is one of the classical NP-hard problems of scheduling theory.

The public practice instances and the hidden judged instances are drawn
from the same public JSSP benchmark library and its classic families
(ft, la, abz, orb, swv, yn, ta, dmu, tai), plus a set of freshly generated
instances in the same style. The hidden set is constructed so that
verbatim replay of published artifacts does not score on it.

## Your job

Build a solver in `/app`. The shipped baseline, `/app/solver.cpp`
(priority-rule Giffler–Thompson active-schedule construction plus a
critical-path local search, deterministic, any-time), is a working solver
you can modify, wrap, reconfigure, or replace entirely — it also serves as
a living example of the I/O contract below.

You have a 12-hour run. When the run ends, the verifier rebuilds the tree
you left in `/app` exactly as described in Hard rules and judges the
resulting solver once on the hidden instances. That single judging is your
final score — nothing is judged while you work.

## Judging

| | |
|---|---|
| **Public practice set** | 198 instances at `/app/instances/`. `/app/public_reference.json` gives two reference values per instance: `B` (the shipped baseline's result) and `K` (a best-known value from stronger reference solvers). |
| **Judging sandbox** | **10 parallel shards**; per instance: **1 core**, 600 s wall clock (instances judged in parallel; shard containers with 4 cores/8 GB RAM are shared across them). This sandbox follows the task's official evaluation specification. |
| **Self-test** | `submit.sh` — unlimited use. The service judges your solver on the public practice set, **in the same judging sandbox, on the same 10 parallel shards, under the same per-instance limits** — and prints per-instance results and validity. Self-tests never affect your score. |
| **Final judging** | Once, after the run ends: the verifier rebuilds `/app` and judges your solver on **85 hidden instances**, again **in the same sandbox, on the same 10 parallel shards**. |
| **Score** | Determined solely by that one final judging. Hidden per-instance results are never returned to you; the formula that aggregates judging results into the final score is not disclosed. |

`submit.sh` is on your `PATH` at `/usr/local/bin/submit.sh` — call it from any working directory.

A self-test and the final judging are the **same measurement** — same
sandbox, same 10 parallel shards, same per-instance limits; only the
instance set differs (public vs hidden). Local runs in this development
environment happen outside the judging sandbox, so local measurements
may not transfer — treat `submit.sh` results as authoritative.

## Input / output format (fixed — do not change the interface)

The judge runs

```
solver INSTANCE_FILE OUTPUT_FILE LIMIT_SECONDS
```

- `INSTANCE_FILE`: a text file. First line `n m`
  (machines are numbered `0..m-1`); then `n` lines, line `j` holding `m`
  pairs `machine duration` — job `j`'s operations in route order.
- `OUTPUT_FILE`: your schedule, as a **start-time matrix**: `n` lines,
  line `j` holding `m` non-negative integers — the start times of job
  `j`'s operations in the same route order as the instance.
- `LIMIT_SECONDS`: the wall-clock budget for this instance (600 in
  judging).

**Any-time discipline (important).** Your solver is *not* expected to
decide when to stop on its own only: at `LIMIT_SECONDS + 10 s` the judge
sends SIGTERM to the process group, and SIGKILL 10 s later. Whatever sits
in `OUTPUT_FILE` at that moment is what gets validated. So: **write your
current best schedule to `OUTPUT_FILE` every time you improve it**, and
write it *atomically* (write a temp file, then `rename`) so a signal
mid-write can never leave a torn file. The shipped baseline and the
shipped CP-SAT example both implement exactly this protocol; the baseline
stops searching at `0.92 * LIMIT` for the same reason.

## What's in the environment

- `/app/solver.cpp` — the baseline solver. Rebuild with
  `bash /app/build.sh`, which produces `/app/solver`.
- `/app/tabu/tabu.cpp` — a tabu search over machine sequences
  (critical-block swaps, tabu tenure, stagnation kicks), same command-line
  contract, also prebuilt on PATH as `tabu` (`tabu INSTANCE OUT LIMIT
  [SEED]`). It lives in a subdirectory so the shipped `build.sh` (which
  compiles all top-level `/app/*.cpp` together) does not pick up its `main`.
- `/app/cpsat_example.py` — the stock CP-SAT model for this problem
  wrapped in the any-time output protocol: `python3 /app/cpsat_example.py
  INSTANCE OUT LIMIT`; the `ortools` Python package is installed. An
  executable script that execs it satisfies the `/app/solver` contract.
- `/app/instances/` — the 198 public practice instances.
- `/app/jsplib/` — the library's public reference data (see its README):
  `bks.json`, the best-known-solutions archive with per-instance
  **lower and upper bounds** and open/closed status; and the four
  `results_*.json` tables of the library's standardized 10-minute engine
  runs (including CP-SAT — the exact version installed here). The `K`
  column of `public_reference.json` is the `upper_bound` from this archive
  for the library's instances.
- `jssp_check` — the validity checker, on PATH:
  `jssp_check INSTANCE SOLUTION` prints `OK <makespan>` iff the schedule
  is feasible (right shape, job precedence respected, no machine
  overlap); the makespan is recomputed from your start times. Source:
  `/opt/jssp/jssp_check.cpp`. The judge uses the same binary.
- `/app/public_reference.json` — per public instance: the baseline's
  makespan `B`, the stock CP-SAT level `L` (a reference point), and the
  best-known value `K`.
- `python3 /app/run_public.py` — rebuilds `/app` via `build.sh`, runs your
  solver on the public practice set locally under the same 600 s
  per-instance limit, validates with `jssp_check`, and prints per-instance
  results next to `B`, `L` and `K`. It runs on this development box,
  outside the judging sandbox — use `submit.sh` for authoritative
  measurements.
- `submit.sh` — the self-test client: packs your solver tree, submits it
  to the judging service, and prints per-instance results judged on the
  public practice set in the judging sandbox.

## Hard rules

- The judge runs `bash /app/build.sh` (10 min limit). If it fails or does
  not produce an executable `/app/solver`, the total score is 0. All
  top-level `/app/*.cpp` files are compiled together by the shipped
  script (it excludes `jssp_check.cpp`, which has its own `main`); keep
  extra sources in subdirectories if you add many files.
- The judging runs your solver once per instance with a
  **per-instance wall-clock limit of 600 seconds**, each instance pinned
  to a single core (evaluated in parallel on the judge's shards). At
  `LIMIT_SECONDS + 10 s` the judge sends SIGTERM to the process group,
  and SIGKILL 10 s later; whatever schedule sits in `OUTPUT_FILE` at that
  moment is what gets validated. A crash, a nonzero exit, or an invalid
  schedule scores 0 for that instance; the others still count.
- The final score comes from a **fresh run** of your final build on the
  hidden instances, executed after your run ends.
- `submit.sh` uploads everything in `/app` **except** `./instances/`
  (static public assets the judge does not need — its public channel
  carries the same set). The pack also strips VCS metadata, tool caches,
  build byproducts and logs at any depth, and packs over 200 MB are refused
  (if the filter ever removes a file your solver genuinely needs, re-run
  with `TCSEXAM_SUBMIT_PRUNE=0`). If your solver needs runtime data
  files, keep them elsewhere in `/app`.
- `submit.sh` records every judging session it creates in
  `/app/.judge_sessions` (the session chain; the legacy `.session_public_id`
  file is still written). Do not delete that file.
  The public self-test channel is the ONLY judging-service access you
  have — the hidden instances are judged exactly once, by the verifier,
  after the run ends. Creating or using any other judging sessions (in
  particular anything judged on the hidden set) is a violation: the
  platform records your full command trace, which can be audited after the
  run, and your score can be revoked.
- No network access except the judging service.
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
