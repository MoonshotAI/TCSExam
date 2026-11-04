# Task: Capacitated vehicle routing

## Background

In the **capacitated vehicle routing problem** (CVRP) you are given a depot,
a set of customers with integer demands, and a fleet of identical vehicles
with a fixed capacity. You must design routes that start and end at the depot
and together visit every customer exactly once, such that the total demand
served by any route never exceeds the vehicle capacity, **minimizing the
total travel length**. CVRP is NP-hard (it contains TSP as a special case).

The public practice instances and the hidden judged instances are drawn from
the same public CVRP benchmark library. The hidden set is constructed so
that verbatim replay of published artifacts does not score on it.

## Problem definition (fixed — read carefully)

- **Distances** are Euclidean, rounded to the nearest integer:
  `d(i,j) = floor(hypot(xi - xj, yi - yj) + 0.5)` (the `EUC_2D`
  convention the reference values use).
- **Fleet size**: every instance name ends with `-kK` (e.g. `X-n261-k13`),
  meaning **at most K routes** may be used. A solution using more routes
  than K is invalid, even if it is otherwise feasible. (This is the
  convention under which the reference values for these instances were
  established.)
- **Capacity**: the total demand of the customers on any single route must
  not exceed the vehicle capacity given in the instance file.
- Every customer must be visited exactly once; the depot must not appear
  inside a route; routes are traveled in the order you print them.

## Your job

Build a solver in `/app`. The shipped baseline, `/app/solver.cpp`
(Clarke–Wright parallel savings followed by a deterministic local search:
2-opt and Or-opt inside routes, relocate and swap between routes, with a
greedy route-dissolution step whenever the construction uses more routes
than the fleet allows), is a working solver you can modify, wrap,
reconfigure, or replace entirely — it also serves as a living example of
the I/O contract below.

You have a 12-hour run. When the run ends, the verifier rebuilds the tree
you left in `/app` exactly as described in Hard rules and judges the
resulting solver once on the hidden instances. That single judging is your
final score — nothing is judged while you work.

## Judging

| | |
|---|---|
| **Public practice set** | 80 instances at `/app/instances/`. `/app/public_reference.json` gives two reference values per instance: `B` (the shipped baseline's result) and `K` (a best-known value from stronger reference solvers). |
| **Judging sandbox** | Per instance: **1 core**, 180 s wall clock. Each isolated Docker worker reserves 8 GB RAM. Up to 10 workers run concurrently, reduced automatically to fit available host resources. |
| **Local self-test** | Use the public-instance runner described below. It executes in this development environment; local timing can differ from the judging environment. Self-tests never affect your final score. |
| **Final judging** | Once, after the run ends: the verifier rebuilds `/app` and judges your solver on **34 hidden instances**, again **in the same sandbox, on the same 10 parallel shards**. |
| **Score** | Determined solely by that one final judging. Hidden per-instance results are never returned to you; the formula that aggregates judging results into the final score is not disclosed. |

The final verifier runs on the evaluation host through Docker.
Development has no judging-service access. The public-instance
runner below supplies local feedback. Hidden instances are used
only once, after the development run ends.

## Input / output format (fixed — do not change the interface)

Your program reads an instance from **stdin** in the standard CVRP text
format:

- header lines `KEY : value` (`NAME`, `TYPE : CVRP`, `COMMENT`,
  `DIMENSION`, `EDGE_WEIGHT_TYPE : EUC_2D`, `CAPACITY`);
- `NODE_COORD_SECTION`: one line per node `id x y` (1-based ids);
- `DEMAND_SECTION`: one line per node `id demand` (the depot has demand 0);
- `DEPOT_SECTION`: the depot node id, then `-1`; the file ends with `EOF`.

Your program writes the solution to **stdout**: the first token is `R` (the
number of routes, at most the fleet size `K` from the name suffix), then for
each route a token `m` followed by the `m` 1-based node ids of the customers
on that route in visit order. Nothing else on stdout. Example for two routes
of 3 and 4 customers: `2  3 5 12 7  4 9 3 21 14`. The judge re-validates
everything itself (route count vs the fleet limit, coverage, capacity) and
recomputes the total length from the coordinates — nothing your program
prints beyond the routes is trusted.

## What's in the environment

- `/app/solver.cpp` — the baseline solver source. Rebuild with
  `bash /app/build.sh`, which produces `/app/solver`.
- `/app/instances/` — the 80 public practice instances.
- `/app/library/` — 76 additional instances from the same library, for
  development and stress-testing; they overlap neither the public practice
  set nor the hidden set.
- `/app/cvrplib_table.md` — per-instance table for every shipped instance:
  size, fleet, capacity, the baseline's total length, and the best known
  value with its proven-optimal flag.
- `/app/solutions/` — verified best known solutions for a few
  practice-level instances, in exactly the solver output format above
  (each re-checked against its instance). Useful for testing your own
  checker.
- `/app/public_reference.json` — per public instance: the baseline's
  total length `B` and the best known value `K`.
- `python3 /app/run_public.py` — rebuilds `/app` via `build.sh`, runs your
  solver on the public practice set locally under the same per-instance
  wall-clock limit the judge uses, validates the routes, recomputes
  lengths, and prints per-instance results next to `B` and `K`. It runs on
  this development box, outside the judging sandbox — allow for differences between development and judging resources.

## Hard rules

- When the run ends, the verifier runs `bash /app/build.sh` (10 min limit)
  on the tree you left in `/app`. If it fails or does not produce an
  executable `/app/solver`, the total score is 0. All top-level `/app/*.cpp`
  files are compiled together by the shipped script; keep extra sources in
  subdirectories if you add many files.
- The judging runs your solver once per instance with a
  **per-instance wall-clock limit of 180 seconds**, each instance pinned
  to a single core (evaluated in parallel on the judge's shards). The
  process group is hard-killed at the limit — right at the limit, with no
  grace period. A run killed at the limit, a crash, a nonzero exit, or an
  invalid solution scores 0 for that instance; the others still count.
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
