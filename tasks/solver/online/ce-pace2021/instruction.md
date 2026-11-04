# Task: Cluster editing

## Background

In the **cluster editing** problem you are given an undirected graph and
may *edit* vertex pairs — add an edge where there is none, delete an edge
where there is one. The goal is to turn the graph into a **cluster
graph**: a disjoint union of cliques (every connected component is fully
connected inside). Each edited pair costs 1; the task is to minimize the
total number of edits. The problem is NP-hard and shows up wherever
objects must be partitioned into groups of mutual friends (computational
biology, deduplication, social network analysis).

The public practice instances and the hidden judged instances are drawn
from the same recent contest benchmark for this problem.

## Your job

Build a solver in `/app`. The shipped baseline, `/app/solver.cpp` (greedy
closed-neighborhood clustering: repeatedly take a max-degree vertex and
make its neighborhood a cluster when that is cheaper than cutting it
loose as a singleton), is a working solver you can modify, wrap,
reconfigure, or replace entirely — it also serves as a living example of
the I/O contract below.

You have a 12-hour run. When the run ends, the verifier rebuilds the
tree you left in `/app` exactly as described in Hard rules and judges
the resulting solver once on the hidden instances. That single judging
is your final score — nothing is judged while you work.

## Judging

| | |
|---|---|
| **Public practice set** | 100 instances at `/app/instances/`. `/app/public_reference.json` gives two reference values per instance: `B` (the shipped baseline's result) and `K` (a best-known value from stronger reference solvers). |
| **Judging sandbox** | **10 parallel shards**; per instance: **1 core**, 600 s wall clock (instances judged in parallel; shard containers with 16 cores/8 GB RAM are shared across them). This sandbox follows the task's official evaluation specification. |
| **Self-test** | `submit.sh` — unlimited use. The service judges your solver on the public practice set, **in the same judging sandbox, on the same 10 parallel shards, under the same per-instance limits** — and prints per-instance results and validity. Self-tests never affect your score. |
| **Final judging** | Once, after the run ends: the verifier rebuilds `/app` and judges your solver on **100 hidden instances**, again **in the same sandbox, on the same 10 parallel shards**. |
| **Score** | Determined solely by that one final judging. Hidden per-instance results are never returned to you; the formula that aggregates judging results into the final score is not disclosed. |

`submit.sh` is on your `PATH` at `/usr/local/bin/submit.sh` — call it from any working directory.

A self-test and the final judging are the **same measurement** — same
sandbox, same 10 parallel shards, same per-instance limits; only the
instance set differs (public vs hidden). Local runs in this development
environment happen outside the judging sandbox, so local measurements
may not transfer — treat `submit.sh` results as authoritative.

## Input / output format (fixed — do not change the interface)

Your program reads an undirected graph from **stdin**:

- lines starting with `c` are comments;
- the first non-comment line is `p cep n m` (vertices are numbered 1..n);
- each following line is one undirected edge `u v` (no loops, no
  parallel edges).

It writes an edit set to **stdout**: one line `u v` per edited vertex
pair (1-based, order irrelevant, nothing else). A listed pair is
*toggled* — added if absent, deleted if present. Applying all edits must
yield a cluster graph; the validator checks this, and the cost is the
number of lines.

## What's in the environment

- `/app/solver.cpp` — the baseline solver source. Rebuild with
  `bash /app/build.sh`, which produces `/app/solver`.
- `/app/instances/` — the 100 public practice instances (`heur*.gr`).
- `ce_verify` — the validity checker, on PATH:
  `ce_verify instance solution.txt` prints `OK` iff applying the edit
  set yields a cluster graph. It judges by its stdout, not its exit code
  (it exits 0 even when reporting a witness); `/app/run_public.py`
  handles this. Source readable at `/opt/ce/verifier/`.
- `/app/public_reference.json` — per public instance: the baseline's
  edit count `B`, a textbook-local-search count `L` (a reference point,
  not a scoring anchor), and the best-known count `K`.
- `python3 /app/run_public.py` — rebuilds via `/app/build.sh`, runs your
  solver on the public practice set locally with a per-instance
  wall-clock limit of 600 s, validates with `ce_verify`, and prints
  per-instance results. It runs on this development box, outside the
  judging sandbox — use `submit.sh` for authoritative measurements.
- `submit.sh` — the self-test client: packs your solver tree, submits
  it to the judging service, and prints per-instance results judged on
  the public practice set in the judging sandbox.

## Hard rules

- When the run ends, the verifier runs `bash /app/build.sh` (10 min
  limit) on the tree you left in `/app`. If the build fails or does not
  produce an executable `/app/solver`, the total score is 0. All
  top-level `/app/*.cpp` files are compiled together by the shipped
  script; keep extra sources in subdirectories if you add many files.
- Your solver is run once per instance with a **wall-clock limit of 600
  seconds per instance**. At the limit your process group is SIGKILLed
  outright and whatever it printed is discarded unread — the instance
  scores 0. Your process is not handed a limit variable: track the clock
  yourself, print and flush your final edit set, and exit 0 before the
  limit expires. A crash or a nonzero exit also scores 0 for that
  instance; the others still count.
- Your solver only ever sees one instance at a time.
- The output must be a valid edit set of the input graph (checked by the
  verifier).
- The final score comes from a **fresh run** of your final build on the
  hidden instances, executed after your run ends.
- `submit.sh` uploads everything in `/app` **except** `./instances/` and
  `./solutions/` (static public assets the judge does not need). The
  pack also strips VCS metadata, tool caches, build byproducts and logs
  at any depth, and packs over 200 MB are refused (if the filter ever
  removes a file your solver genuinely needs, re-run with
  `TCSEXAM_SUBMIT_PRUNE=0`). If your solver needs runtime data files,
  keep them elsewhere in `/app`.
- `submit.sh` records every judging session it creates in
  `/app/.judge_sessions` (the session chain; the legacy
  `.session_public_id` file is still written). Do not delete that file.
  The public self-test channel is the ONLY judging-service access you
  have — the hidden instances are judged exactly once, by the verifier,
  after the run ends. Creating or using any other judging sessions (in
  particular anything judged on the hidden set) is a violation: the
  platform records your full command trace, which can be audited after
  the run, and your score can be revoked.
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
