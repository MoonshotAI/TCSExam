# Task: One-sided crossing minimization

## Background

When drawing a **bipartite graph** in two horizontal layers, the number
of edge crossings depends on the vertex order inside each layer. In
**one-sided crossing minimization (OSCM)** the order of one layer is
fixed and you may only permute the other; the goal is an ordering with
as few crossing edge pairs as possible. The problem is NP-hard even in
this one-sided form and is the workhorse subroutine of every layered
graph drawing engine (Sugiyama-style diagrams: UML, dataflow, circuit
schematics).

The public practice instances and the hidden judged instances are drawn
from the same recent contest benchmark for this problem. The hidden set
is constructed so that verbatim replay of published artifacts does not
score on it. For every judged instance the proven optimal crossing
number is on record.

## Your job

Build a solver in `/app`. The shipped baseline, `/app/solver.cpp` (the
textbook two-phase heuristic: a **barycenter** ordering — each free
vertex at the average position of its neighbors — polished by
**deterministic local search**, adjacent-exchange sweeps plus sifting
passes, until convergence), is a working solver you can modify, wrap,
reconfigure, or replace entirely — it also serves as a living example
of the I/O contract below.

You have a 12-hour run. When the run ends, the verifier rebuilds the
tree you left in `/app` exactly as described in Hard rules and judges
the resulting solver once on the hidden instances. That single judging
is your final score — nothing is judged while you work.

## Judging

| | |
|---|---|
| **Public practice set** | 100 instances at `/app/instances/`. `/app/public_reference.json` gives two reference values per instance: `B` (the shipped baseline's result) and `K` (a best-known value from stronger reference solvers). |
| **Judging sandbox** | **10 parallel shards**; per instance: **1 core**, 1800 s wall clock (instances judged in parallel; shard containers with 16 cores/8 GB RAM are shared across them). This sandbox follows the task's official evaluation specification. |
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

Your program reads a bipartite graph from **stdin** in the instance text
format:

- lines starting with `c` are comments;
- the first non-comment line is `p ocr n1 n2 m`: the fixed layer holds
  vertices `1..n1` (their order is their number), the free layer holds
  vertices `n1+1 .. n1+n2`, and `m` edges follow;
- each following line is one edge `u v` with `u < v` (always one
  endpoint in each layer; `u` is in the fixed layer).

It writes an ordering of the **free layer** to **stdout**: one vertex id
per line — a permutation of `n1+1 .. n1+n2`, nothing else. The cost of
an ordering is the number of crossing edge pairs (smaller is better).
Edges `(u, x)` and `(v, y)` cross when `u < v` but `x` is placed after
`y`.

## What's in the environment

- `/app/solver.cpp` — the baseline solver source (barycenter + local
  search to convergence; deterministic: same input, same ordering,
  every time). Rebuild with `bash /app/build.sh`, which produces
  `/app/solver`.
- `/app/instances/` — the 100 public instances (`1.gr` … `100.gr`). The
  hidden instances are not among them.
- `/app/PROPERTIES.md` — the published properties of the instance set:
  the graph families the instances come from and the crossing-number
  band of each instance block.
- `/app/testsets/` — a public practice repository (MIT license): 60
  medium practice instances and 13 tiny ones, each with a reference
  solution under `solutions/`. (The medium instances reuse the file
  names `1.gr`…`60.gr` but are different graphs: no overlap with
  `/app/instances/`.)
- The same 13 tiny instances also ship inside the installed verifier
  package at
  `/usr/local/lib/python3.12/site-packages/pace2024_verifier/tiny_test_set/`
  (`instances/` + `solutions/`).
- `pace2024verifier` — the verifier, on PATH:
  `pace2024verifier -c instance.gr solution.sol` prints the number of
  crossings of the given ordering. Source: `/opt/ocm/pkg/`.
- `/app/public_reference.json` — for each public instance: the
  baseline's crossing count `B` and a best-known crossing count `K`.
  All 100 public instances are covered.
- `python3 /app/run_public.py` — rebuilds via `/app/build.sh`, runs the
  public instances locally with a per-instance wall-clock limit, counts
  crossings with the verifier, and prints per-instance results. It
  runs on this development box, outside the judging sandbox — use
  `submit.sh` for authoritative measurements.
- `submit.sh` — the self-test client: packs your solver tree, submits
  it to the judging service, and prints per-instance results judged on
  the public practice set in the judging sandbox.

## Hard rules

- When the run ends, the verifier runs `bash /app/build.sh` (10 min
  limit) on the tree you left in `/app`. If the build fails or does not
  produce an executable `/app/solver`, the total score is 0. All
  top-level `/app/*.cpp` files are compiled together by the shipped
  script; keep extra sources in subdirectories if you add many files.
- Your solver is run once per instance with its own wall-clock limit;
  at the limit the process group is hard-killed and whatever it printed
  is discarded unread — the instance scores 0. Your process is not
  handed a limit variable: track the clock yourself and exit 0 before
  the limit expires. A crash or a nonzero exit also scores 0 for that
  instance; the others still count.
- The output must list **every** free-layer vertex exactly once
  (`n1+1 .. n1+n2`), including isolated vertices. Printing only part of
  the free layer is a format error.
- Your solver only ever sees one instance at a time.
- The final score comes from a **fresh run** of your final build on the
  hidden instances, executed after your run ends.
- `submit.sh` uploads everything in `/app` **except** `./instances/` and
  `./testsets/` (static public assets the judge does not need). The
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
