# Task: Dominating set

## Background

A **dominating set** of an undirected graph is a set of vertices D such
that every vertex outside D has at least one neighbor in D. The goal:
find a dominating set as **small** as possible. The decision version is
NP-complete, and getting a good approximation in polynomial time is
believed to be hard, so in practice heuristic solvers matter.

The public practice instances and the hidden judged instances are drawn
from the same recent contest benchmark for this problem.

## Your job

Build a solver in `/app`. The shipped baseline, `/app/solver.cpp`
(single-pass set-cover greedy), is a working solver you can modify,
wrap, reconfigure, or replace entirely — it also serves as a living
example of the I/O contract below.

You have a 12-hour run. When the run ends, the verifier rebuilds the
tree you left in `/app` exactly as described in Hard rules and judges
the resulting solver once on the hidden instances. That single judging
is your final score — nothing is judged while you work.

## Judging

| | |
|---|---|
| **Public practice set** | 100 instances at `/app/instances/`. `/app/public_reference.json` gives two reference values per instance: `B` (the shipped baseline's result) and `K` (a best-known value from stronger reference solvers). |
| **Judging sandbox** | Per instance: **1 core**, 300 s wall clock. Each isolated Docker worker reserves 16 GB RAM. Up to 10 workers run concurrently, reduced automatically to fit available host resources. |
| **Local self-test** | Use the public-instance runner described below. It executes in this development environment; local timing can differ from the judging environment. Self-tests never affect your final score. |
| **Final judging** | Once, after the run ends: the verifier rebuilds `/app` and judges your solver on **100 hidden instances**, again **in the same sandbox, on the same 10 parallel shards**. |
| **Score** | Determined solely by that one final judging. Hidden per-instance results are never returned to you; the formula that aggregates judging results into the final score is not disclosed. |

The final verifier runs on the evaluation host through Docker.
Development has no judging-service access. The public-instance
runner below supplies local feedback. Hidden instances are used
only once, after the development run ends.

## Input / output format (fixed — do not change the interface)

Your program reads a graph from **stdin** in `.gr` format:

- lines starting with `c` are comments;
- the first non-comment line is `p ds <n> <m>` (vertices are numbered
  1..n);
- then `m` lines `u v` describe the undirected edges.

It writes a solution to **stdout**:

- line 1: `k`, the number of vertices you selected;
- the next `k` lines: one vertex id per line.

The output must be a valid dominating set of the input graph; the
validator checks validity and recomputes its size.

## What's in the environment

- `/app/solver.cpp` — the baseline solver source. Compiles with
  `g++ -O2 -std=c++17 -o solver solver.cpp`.
- `/app/instances/` — the 100 public practice instances
  (`heuristic_*.gr`).
- `/app/test-instances/` — an additional small-instance test set
  (classic and random graphs, plus a `large/` subdirectory of
  7z-compressed bigger ones; `p7zip` is installed). These overlap
  neither the public practice set nor the hidden set, so you can use
  them freely for development.
- `/opt/ds2025/ds_verifier.jar` — the validity checker (Java):
  `java -jar /opt/ds2025/ds_verifier.jar graph.gr solution.txt` prints
  `Solution of size <k> is valid!` for a valid solution. Source readable
  at `/opt/ds2025/verifier-src/`.
- `/app/public_reference.json` — per public instance: the baseline's
  size `B` and the reference best-known size `K`.
- `python3 /app/run_public.py` — rebuilds `/app/*.cpp`, runs your solver
  on the public practice set locally under the same 300 s per-instance
  limit, validates with the checker, and prints per-instance results.
  It runs on this development box, outside the judging sandbox — allow for differences between development and judging resources.

## Hard rules

- All top-level `/app/*.cpp` / `/app/*.cc` files are compiled together
  with `g++ -O2 -std=c++17`. If compilation fails, the total score is 0.
- Your solver is run once per instance with a **wall-clock limit of 300
  seconds per instance**. Before each run the judge hands your process
  the limit in the environment variable **`DS_TIME_POOL`** (seconds,
  float) and hard-kills the process when it is used up — right at the
  limit, with no grace period. A run killed at the limit, a crash, a
  nonzero exit, or an invalid solution scores 0 for that instance; the
  others still count.
- Your solver only ever sees one instance at a time.
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
