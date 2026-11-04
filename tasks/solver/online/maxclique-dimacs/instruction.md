# Task: Maximum clique

## Background

In the **maximum clique** problem you are given an undirected graph and must
find the largest set of vertices that are pairwise adjacent — a *clique*.
The size of a largest clique is denoted ω(G). Maximum clique is NP-hard, and
it is hard even to approximate: unless NP = ZPP, no polynomial-time algorithm
approximates ω(G) within a factor n^(1−ε) for any ε > 0.

The public practice instances and the hidden judged instances are drawn
from the same public instance collection for this problem. The hidden set
is constructed so that verbatim replay of published artifacts does not
score on it. The witness cliques published alongside the literature values
are not shipped — apart from the practice-subset solutions under
`/app/solutions/`, you have to produce the cliques yourself.

## Your job

Build a solver in `/app`. The shipped baseline (`/app/solver.cpp` +
`/app/mcqd_anytime.h`, GPL-3.0) is an exact branch-and-bound solver wrapped
as an *anytime* solver: it searches until it hits a node budget (default
5,000,000 search steps) or a wall-clock soft limit (default 150 s),
whichever comes first, and then prints the best clique found so far. It is
a working solver you can modify, wrap, reconfigure, or replace entirely —
it also serves as a living example of the I/O contract below.

You have a 12-hour run. When the run ends, the verifier rebuilds the tree
you left in `/app` exactly as described in Hard rules and judges the
resulting solver once on the hidden instances. That single judging is your
final score — nothing is judged while you work.

## Judging

| | |
|---|---|
| **Public practice set** | 44 instances at `/app/instances/`. `/app/public_reference.json` gives two reference values per instance: `B` (the shipped baseline's result) and `K` (a best-known value from stronger reference solvers). |
| **Judging sandbox** | **6 parallel shards**; per instance: **1 core**, 180 s wall clock (instances judged in parallel; shard containers with 4 cores/8 GB RAM are shared across them). This sandbox follows the task's official evaluation specification. |
| **Self-test** | `submit.sh` — unlimited use. The service judges your solver on the public practice set, **in the same judging sandbox, on the same 6 parallel shards, under the same per-instance limits** — and prints per-instance results and validity. Self-tests never affect your score. |
| **Final judging** | Once, after the run ends: the verifier rebuilds `/app` and judges your solver on **24 hidden instances**, again **in the same sandbox, on the same 6 parallel shards**. |
| **Score** | Determined solely by that one final judging. Hidden per-instance results are never returned to you; the formula that aggregates judging results into the final score is not disclosed. |

`submit.sh` is on your `PATH` at `/usr/local/bin/submit.sh` — call it from any working directory.

A self-test and the final judging are the **same measurement** — same
sandbox, same 6 parallel shards, same per-instance limits; only the
instance set differs (public vs hidden). Local runs in this development
environment happen outside the judging sandbox, so local measurements
may not transfer — treat `submit.sh` results as authoritative.

## Input / output format (fixed — do not change the interface)

Your program reads a graph from **stdin** in the DIMACS ASCII format:

- lines starting with `c` are comments;
- one header line `p edge n m` declares `n` vertices (numbered 1..n) and
  `m` edges. Treat `m` as advisory: in some library files it counts both
  directions of every edge. Build the graph from the `e` lines;
- each remaining line `e u v` is one undirected edge between vertices `u`
  and `v` (1-based). Each unordered pair appears at most once and there
  are no self-loops.

Your program writes a clique to **stdout**: the first token is `k` (the
clique size you report), followed by exactly `k` tokens with the 1-based
vertex numbers of the clique (each vertex at most once). Nothing else on
stdout. Validity = `k` vertices, all in `1..n`, all distinct, every pair
adjacent in the graph; the judge then recomputes the clique size itself.

## What's in the environment

- `/app/solver.cpp` + `/app/mcqd_anytime.h` — the anytime baseline.
  Rebuild with `bash /app/build.sh`, which produces `/app/solver`. It
  reads two optional environment variables: `MCQ_STEP_LIMIT` (node
  budget, default 5000000; because this is a step count, the baseline's
  answer is the same on every machine) and `MAXCLIQUE_SECONDS`
  (wall-clock soft limit, default 150).
- `/app/instances/` — the 44 public practice instances.
- `/app/dimacs_table.md` — per-instance table for the shipped public
  instances: size, the baseline's clique size, and the reference value
  where one is established.
- `/app/solutions/` — verified cliques for a practice subset, in exactly
  the solver output format above (each re-checked against its instance).
- `/app/public_reference.json` — per public instance: the baseline's
  clique size `B` and the reference value `K`.
- `python3 /app/run_public.py` — rebuilds via `/app/build.sh`, runs your
  solver on the public practice set locally under the same 180 s
  per-instance limit, validates the cliques, and prints per-instance
  results. It runs on this development box, outside the judging sandbox —
  use `submit.sh` for authoritative measurements.
- `submit.sh` — the self-test client: packs your solver tree, submits
  it to the judging service, and prints per-instance results judged on
  the public practice set in the judging sandbox.

## Hard rules

- When the run ends, the verifier runs `bash /app/build.sh` (10 min
  limit) on the tree you left in `/app`. If the build fails or does not
  produce an executable `/app/solver`, the total score is 0. All top-level
  `/app/*.cpp` files are compiled together by the shipped script; keep
  extra sources in subdirectories.
- Your solver is run once per judged instance with a **wall-clock limit
  of 180 seconds per instance** (the process group is hard-killed at the
  limit). Your solver must print its clique and exit with code 0 before
  the limit — self-limit with margin, like the baseline does. A killed
  run, a crash, a nonzero exit code, or no output at all scores 0 for
  that instance; the others still count. Your solver only ever sees one
  instance at a time.
- An invalid clique (a vertex out of range or repeated, a pair of
  reported vertices not joined by an edge, a malformed output) scores 0
  **for that instance**.
- The final score comes from a **fresh run** of your final build on the
  hidden instances, executed after your run ends.
- `submit.sh` uploads everything in `/app` **except** `./instances/`
  and `./solutions/` (static public assets the judge does not need). The
  pack strips VCS metadata, tool caches, build byproducts and logs at any
  depth; packs over 200 MB are refused (re-run with
  `TCSEXAM_SUBMIT_PRUNE=0` if the filter ever removes a file your solver
  genuinely needs). Keep runtime data files elsewhere in `/app`.
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
