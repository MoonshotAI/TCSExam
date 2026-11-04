# Task: Treewidth — heuristic solving

## Background

The **treewidth** of a graph measures how far it is from being a tree: a
**tree decomposition** arranges subsets of the vertices ("bags") into a
tree so that (i) every edge of G lies inside at least one bag, and (ii)
the bags containing any vertex v form a connected subtree. The **width**
of a decomposition is its largest bag size minus one; the treewidth of G
is the minimum width over all decompositions. Deciding treewidth is
NP-complete, and good decompositions are the workhorse of parameterized
algorithms, probabilistic inference, and compiler register allocation.

The public practice instances and the hidden judged instances are drawn
from the same recent contest benchmark for this problem. The hidden set
is constructed so that verbatim replay of published artifacts does not
score on it. These instances were **never fully solved**: the reference
widths are the **best known**, not proven optima. No decomposition files
are shipped — you have to produce the decompositions yourself.

## Your job

Build a solver in `/app`. The shipped baseline is **FlowCutter** (BSD
license), a working, strong solver, driven by a naive scheduler that
splits one run per instance (`/app/driver.sh`) — you can modify it, wrap
it, reconfigure it, or replace it entirely — it also serves as a living
example of the I/O contract below.

You have a 12-hour run. When the run ends, the verifier rebuilds the
tree you left in `/app` exactly as described in Hard rules and judges
the resulting solver once on the hidden instances. That single judging
is your final score — nothing is judged while you work.

## Judging

| | |
|---|---|
| **Public practice set** | 100 instances at `/app/instances/`. `/app/public_reference.json` gives two reference values per instance: `B` (the shipped baseline's result) and `K` (a best-known value from stronger reference solvers). |
| **Judging sandbox** | **10 parallel shards**; per instance: **1 core**, 1800 s wall clock (within each shard, instances are judged one at a time; shard containers have 16 cores/8 GB RAM). This sandbox follows the task's official evaluation specification. |
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

Your built program is invoked **once per instance**, exactly as:

```
solver INSTANCE_DIR OUTPUT_DIR LIMIT_SECONDS
```

- `INSTANCE_DIR` holds exactly one `<name>.gr` file — the instance;
- `OUTPUT_DIR` is where you must write the decomposition `<name>.td`;
- `LIMIT_SECONDS` is this run's per-instance wall-clock budget.

When the limit plus a 10-second grace period expires we send SIGTERM to
your process group; 10 seconds later, SIGKILL. Every `<name>.td` present
in `OUTPUT_DIR` is then validated; instances without a valid file score
0. Only files on disk count — a decomposition still held in memory is
lost. The baseline driver (`/app/driver.sh`) implements the protocol;
see it and `/app/src/pace.cpp` for the idiom.

The `.gr` format for each instance file:

- lines starting with `c` are comments;
- the first non-comment line is `p tw <n> <m>` (vertices are numbered
  1..n);
- then `m` lines `u v` describe the undirected edges.

Each `.td` file you write:

- one solution line `s td <N> <W> <n>` — N bags, largest bag size W
  (so the width is W−1), n = number of vertices of the input graph;
- for each bag i (1..N) one line `b i v1 v2 ...` (bags may be empty);
- N−1 lines `i j` (i < j) giving the tree edges between bags;
- comment lines starting with `c` are allowed anywhere.

The FlowCutter core binary reads one `.gr` on stdin and, on SIGTERM (or
when finished), prints its best `.td` to stdout; `-s <seed>` selects its
random seed (the baseline uses seed 0). You may keep this core, wrap it
differently, or replace it entirely.

## What's in the environment

- `/app/src/` — the FlowCutter source (BSD license).
- `/app/driver.sh` — the baseline equal-split driver.
- `/app/Makefile` — `make` must produce an executable `/app/solver`.
- `/app/instances/` — the 100 public instances (`he*.gr`), disjoint from
  the judged ones.
- `td-validate` — the decomposition validity checker, on PATH:
  `td-validate graph.gr out.td` prints `valid` (exit 0) or an error.
  Source: `/opt/tw/td-validate.cpp`.
- `/app/public_reference.json` — for each public instance: the
  baseline's width `B` and the best-known reference width `K`, both
  under the same per-instance budget as the hidden judging.
- `python3 /app/run_public.py` — rebuilds `/app` with `make`, runs your
  solver once per public instance locally with the identical
  per-instance protocol the hidden judge uses, validates with
  `td-validate`, and prints per-instance results. It runs on this
  development box, outside the judging sandbox — use `submit.sh` for
  authoritative measurements.
- `submit.sh` — the self-test client: packs your solver tree, submits
  it to the judging service, and prints per-instance results judged on
  the public practice set in the judging sandbox.

## Hard rules

- When the run ends, the verifier copies `/app` to a scratch directory
  and builds it with `make -j4` (5-minute limit). The build must produce
  an executable `/app/solver`. If the build fails, the total score is 0.
- No valid `.td` for an instance scores 0 **for that instance**; the
  others still count.
- The output must be a valid tree decomposition of the input graph
  (checked by the reference verifier). Printing a great width without a
  matching decomposition is worthless.
- Your solver only ever sees one instance at a time.
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
