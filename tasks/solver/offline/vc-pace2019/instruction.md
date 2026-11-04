# Task: Vertex cover — exact solving

## Background

A **vertex cover** of an undirected graph is a set of vertices that
touches every edge: delete the set, and no edge survives with both
endpoints outside it. Finding a *minimum* vertex cover is one of Karp's
21 original NP-complete problems. It is the textbook flagship of
parameterized complexity: after kernelization, bounded-search-tree
algorithms solve it in O*(2^k) (FPT in the solution size k). On the
approximation side, a maximal matching gives a factor-2 approximation
in linear time, and beating 2 is essentially impossible: Dinur and
Safra proved NP-hardness of approximating within 1.3606, and Khot and
Regev showed factor (2 − ε) is hard under the Unique Games Conjecture.

This is the **exact** edition: an instance counts only when your cover
is valid **and its size matches or beats the reference value on file**.
One vertex too many counts exactly the same as no output. The reference is
the known-best value: a proven optimum for most judged instances, a
best-known upper bound for the rest (some reference values are not
proven exact, so doing **better than the reference is possible** —
that still counts as solved, and is flagged as a broken record).

The public practice instances and the hidden judged instances are drawn
from the same recent contest benchmark for this problem. No cover files
are shipped — you have to produce the covers yourself.

## Your job

Build a solver in `/app`. The shipped baseline, `/app/solver.cpp` (a
branch-and-reduce with degree-0/1 reductions, a maximal-matching lower
bound, and maximum-degree branching), is a working solver you can
modify, wrap, reconfigure, or replace entirely — it also serves as a
living example of the I/O contract below.

You have a 12-hour run. When the run ends, the verifier rebuilds the
tree you left in `/app` exactly as described in Hard rules and judges
the resulting solver once on the hidden instances. That single judging
is your final score — nothing is judged while you work.

## Judging

| | |
|---|---|
| **Public practice set** | 100 instances at `/app/instances/`. `/app/public_reference.json` gives two reference values per instance: `B` (the shipped baseline's result) and `K` (a best-known value from stronger reference solvers). |
| **Judging sandbox** | Per instance: **1 core**, 1800 s wall clock. Each isolated Docker worker reserves 8 GB RAM. Up to 10 workers run concurrently, reduced automatically to fit available host resources. |
| **Local self-test** | Use the public-instance runner described below. It executes in this development environment; local timing can differ from the judging environment. Self-tests never affect your final score. |
| **Final judging** | Once, after the run ends: the verifier rebuilds `/app` and judges your solver on **100 hidden instances**, again **in the same sandbox, on the same 10 parallel shards**. |
| **Score** | Determined solely by that one final judging. Hidden per-instance results are never returned to you; the formula that aggregates judging results into the final score is not disclosed. |

The final verifier runs on the evaluation host through Docker.
Development has no judging-service access. The public-instance
runner below supplies local feedback. Hidden instances are used
only once, after the development run ends.

## Input / output format (fixed — do not change the interface)

Your built program is invoked **once per instance**, exactly as:

```
solver < instance.gr > instance.vc
```

with this run's wall-clock budget (in seconds) handed to your solver in
the environment variable `VC_TIME_LIMIT`.

When the limit expires we send SIGTERM to your process group; 10
seconds later, SIGKILL. Whatever your solver has printed to stdout is
then validated. Only printed output counts — a cover still held in
memory is lost. An exact search that has not finished has proven
nothing: printing an unproven cover earns the same as printing nothing.

The `.gr` format for each instance:

- lines starting with `c` are comments and may appear anywhere;
- the first non-comment line is `p td <n> <m>` (the `td` token is a
  format label; vertices are numbered 1..n);
- then `m` lines `u v` describe the undirected edges.

The `.vc` file you print:

- one header line `s vc <n> <k>` — n = number of vertices of the input
  graph, k = size of your cover;
- then exactly `k` lines, one vertex number each (1..n);
- comment lines starting with `c` are allowed anywhere.

The reference checker enforces all of this: header present exactly
once, declared k equal to the number of vertex lines, vertices in
range, every edge covered.

## What's in the environment

- `/app/solver.cpp` — the baseline solver source. Rebuild with
  `bash /app/build.sh`, which produces `/app/solver`. Run it as
  `./solver < instance.gr > out.vc`.
- `/app/instances/` — the 100 public instances (`vc-exact_*.gr`),
  disjoint from the judged ones.
- `vc_validate` — the cover validity checker, on PATH:
  `vc_validate instance.gr out.vc` prints a verdict line ending in
  `|SUCCESS` iff the cover is valid. Source: `/opt/vc/vc_validate.cpp`.
- `/app/public_reference.json` — for each public instance: `K`, the
  reference value: a proven optimum for most, a best-known upper bound
  for the rest (see `k_source`).
- `python3 /app/run_public.py` — rebuilds via `/app/build.sh`, runs
  your solver once per public instance locally with the identical
  per-instance protocol the hidden judge uses, validates with
  `vc_validate`, and prints per-instance results. It runs on this
  development box, outside the judging sandbox — allow for differences between development and judging resources.

## Hard rules

- The judge runs `bash /app/build.sh` (10 min limit). If it fails or
  does not produce an executable `/app/solver`, the total score is 0.
  All top-level `/app/*.cpp` files are compiled together by the shipped
  script; keep extra sources in subdirectories if you add many files.
- A crash, a timeout with no output, an invalid cover, or a valid cover
  larger than the reference value all count that instance as unsolved;
  the others still count. The budget is enforced with an OS-level hard
  kill.
- The output must be a valid vertex cover of the input graph (checked
  by the reference checker). Claiming a small size without a matching
  cover is worthless.
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
