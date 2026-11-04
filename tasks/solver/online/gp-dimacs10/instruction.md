# Task: Balanced graph partitioning

## Background

The **balanced graph partitioning problem**: you are given an undirected,
unweighted graph with `n` vertices. Partition the vertices into `k = 4`
blocks, minimizing the **edge cut** — the number of edges whose two
endpoints land in different blocks — subject to a **balance constraint**:
no block may hold more than `floor(1.03 * n / 4)` vertices (a 3% imbalance
tolerance). Graph partitioning is NP-hard.

The public practice instances and the hidden judged instances are drawn
from the same public benchmark family for this problem and from freshly
generated graphs of the same random models. The hidden set is constructed
so that verbatim replay of published artifacts does not score on it.

## Your job

Build a solver in `/app`. The shipped baseline, `/app/solver.cpp` (a
single call to the vendored partitioning library's `kaffpa()` function in
FAST mode, fixed seed, no restarts), is a working solver you can modify,
wrap, reconfigure, or replace entirely — it also serves as a living
example of the I/O contract below.

You have a 12-hour run. When the run ends, the verifier rebuilds the tree
you left in `/app` exactly as described in Hard rules and judges the
resulting solver once on the hidden instances. That single judging is your
final score — nothing is judged while you work.

## Judging

| | |
|---|---|
| **Public practice set** | 24 instances at `/app/instances/`. `/app/public_reference.json` gives two reference values per instance: `B` (the shipped baseline's result) and `K` (a best-known value from stronger reference solvers). |
| **Judging sandbox** | **1 shard**; per instance: 4 cores, 16 GB RAM; one shared time pool of 780 seconds covers all judged instances (60 s per instance x instance count) — no per-instance limit. This sandbox follows the task's official evaluation specification. |
| **Self-test** | `submit.sh` — unlimited use. The service judges your solver on the public practice set, **in the same judging sandbox, under the same shared time pool** — and prints per-instance results and validity. Self-tests never affect your score. |
| **Final judging** | Once, after the run ends: the verifier rebuilds `/app` and judges your solver on **13 hidden instances**, again **in the same sandbox**. |
| **Score** | Determined solely by that one final judging. Hidden per-instance results are never returned to you; the formula that aggregates judging results into the final score is not disclosed. |

`submit.sh` is on your `PATH` at `/usr/local/bin/submit.sh` — call it from any working directory.

A self-test and the final judging are the **same measurement** — same
judging sandbox and the same shared time pool; only the instance set
differs (public vs hidden). Local runs in this development environment
happen outside the judging sandbox, so local measurements may not
transfer — treat `submit.sh` results as authoritative.

## Input / output format (fixed — do not change the interface)

Your program reads a graph from **stdin** in the METIS graph format:

- optional comment lines starting with `%`;
- a header line: `n m` (`n` vertices, `m` undirected edges);
- then `n` lines: line `i` lists the neighbours of vertex `i` (1-based
  vertex ids, whitespace-separated). Every edge appears twice (once per
  endpoint); all judging graphs are unweighted.

Your program writes a partition to **stdout**: exactly `n` integers from
`{0,1,2,3}` (whitespace-separated, any layout), where token `i` is the
block of vertex `i` (in the input's 1-based vertex order). Nothing else
on stdout. The shipped solver prints one id per line — use that same
layout if you want to cross-check a partition with `/opt/gp/bin/evaluator`,
which expects one id per line. Validity = all `n` tokens present, each in
`{0,1,2,3}`, and every block holding at most `floor(1.03 * n / 4)`
vertices. The judge then recomputes the edge cut from scratch.

## What's in the environment

- `/app/solver.cpp` — the baseline solver source. Rebuild with
  `bash /app/build.sh`, which produces `/app/solver`.
- `/app/kahip/` — the vendored partitioning library (static, with its C
  interface header): `kaffpa(n, vwgt, xadj, adjcwgt, adjncy, nparts,
  imbalance, suppress_output, seed, mode, edgecut, part)` with modes
  `FAST`, `ECO`, `STRONG` (and the `*SOCIAL` variants). The shipped
  `build.sh` links your `/app/*.cpp` against it.
- `/opt/gp/bin/` — the library's command-line tools (on `PATH`):
  `kaffpa` (partitioner), `evaluator` (recomputes cut and balance of a
  partition file), `graphchecker` (validates a graph file).
- `/app/instances/` — the 27 shipped instances: the 24 public practice
  instances plus three small sample graphs (marked
  `-p01`/`-p02`/`-p03`). All 27 are in the public reference and are
  judged by the self-test channel.
- `/app/public_reference.json` — per shipped instance: the baseline's
  cut `B` and the reference best cut `K` (with a `k_source` flag saying
  where each `K` comes from).
- `python3 /app/run_public.py` — rebuilds via `/app/build.sh`, runs your
  solver on the shipped instances locally under one shared time pool
  (same rule as the judge: 60 s per instance x instance count, no
  per-instance limit), validates the partitions, and prints per-instance
  results. It runs on this development box, outside the judging
  sandbox — use `submit.sh` for authoritative measurements.
- `submit.sh` — the self-test client: packs your solver tree, submits
  it to the judging service, and prints per-instance results judged on
  the public practice set in the judging sandbox.

## Hard rules

- When the run ends, the verifier runs `bash /app/build.sh` (10 min
  limit) on the tree you left in `/app`. If the build fails or does not
  produce an executable `/app/solver`, the total score is 0. All
  top-level `/app/*.cpp` files are compiled together by the shipped
  script; keep extra sources in subdirectories.
- Your solver gets **one total time pool** covering all judged
  instances: **60 seconds per instance x instance count** (wall clock).
  There is **no per-instance limit** — you decide how to distribute the
  pool (on every run the remaining pool is handed to your solver in the
  environment variable `GP_TIME_POOL`, in seconds). When the pool runs
  out, every instance without a verified result scores 0. A crash or a
  nonzero exit scores 0 for that instance.
- The final score comes from a **fresh run** of your final build on the
  hidden instances, executed after your run ends.
- `submit.sh` uploads everything in `/app` **except** `./instances/`
  (static public assets the judge does not need). The pack strips VCS
  metadata, tool caches, build byproducts and logs at any depth; packs
  over 200 MB are refused (re-run with `TCSEXAM_SUBMIT_PRUNE=0` if the
  filter ever removes a file your solver genuinely needs). Keep runtime
  data files elsewhere in `/app`.
- `submit.sh` records every judging session it creates in
  `/app/.judge_sessions` (the session chain; the legacy `.session_public_id`
  file is still written). Do not delete that file. The public self-test
  channel is the ONLY judging-service access you have — the hidden
  instances are judged exactly once, by the verifier, after the run ends.
  Creating or using any other judging session (in particular anything
  judged on the hidden set) is a violation: the platform records your full
  command trace, which can be audited after the run, and your score can be
  revoked.
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
