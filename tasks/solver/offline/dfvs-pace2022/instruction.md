# Task: Directed feedback vertex set

## Background

A **directed feedback vertex set (DFVS)** of a directed graph is a set of
vertices whose removal leaves the graph acyclic: delete the set, and no
directed cycle survives. Finding a *minimum* DFVS is NP-hard (it is one of
Karp's 21 NP-complete problems) and shows up in deadlock breaking, program
analysis, and circuit design.

This is an optimization task: smaller feedback vertex sets are better. The
reference size `K` on file is a best-known value from strong reference
solvers — a proven optimum for most instances, a best-known upper bound
for the rest (so doing **better than the reference is possible** on those).

The 200 judged instances consist of the 100 **public** instances shipped
in this environment and 100 further instances you never see — their files
are not in the environment, and there is no network access to fetch them.
Judged copies are re-labeled (vertex numbers are permuted), so an answer
recorded for a practice file does not answer its judged counterpart —
your solver must compute on the instance it is actually given. All judged
instances span the same families and size range as the public ones (512
to 131072 vertices, sparse to moderately dense).

## Your job

Build a solver in `/app`. The shipped baseline, `/app/solver.cpp` (peel
degree-0 vertices, then repeatedly delete a maximum-degree vertex), is a
working solver you can modify, wrap, reconfigure, or replace entirely — it
also serves as a living example of the I/O contract below, and as the
baseline your final solver is compared against.

You have a 12-hour run. When the run ends, the verifier rebuilds the
tree you left in `/app` exactly as described in Hard rules and judges the
resulting solver once on the hidden instances. That single judging
is your final score — nothing is judged while you work.

## Judging

| | |
|---|---|
| **Public practice set** | 100 instances at `/app/instances/`. `/app/public_reference.json` gives two reference values per instance: `B` (the shipped baseline's result) and `K` (a best-known value from stronger reference solvers). |
| **Judging sandbox** | Per instance: **1 core**, 1800 s wall clock. Each isolated Docker worker reserves 32 GB RAM. Up to 10 workers run concurrently, reduced automatically to fit available host resources. |
| **Local self-test** | Use the public-instance runner described below. It executes in this development environment; local timing can differ from the judging environment. Self-tests never affect your final score. |
| **Final judging** | Once, after the run ends: the verifier rebuilds `/app` and judges your solver on **200 hidden instances**, again **in the same sandbox, on the same 10 parallel shards**. |
| **Score** | Determined solely by that one final judging. Hidden per-instance results are never returned to you; the formula that aggregates judging results into the final score is not disclosed. |

The final verifier runs on the evaluation host through Docker.
Development has no judging-service access. The public-instance
runner below supplies local feedback. Hidden instances are used
only once, after the development run ends.

## Input / output format (fixed — do not change the interface)

Your built program is invoked **once per instance**: it reads a directed
graph from **stdin** and prints a feedback vertex set to **stdout**, with
this run's wall-clock budget (in seconds) handed to your solver in the
environment variable `DFVS_TIME_POOL`.

When the limit expires your process group is hard-killed (SIGKILL) and
that instance's output is discarded — a run that hits the wall scores 0
for the instance no matter what it printed. Only the output of a run that
exits with code 0 in time counts. Print only vertex numbers, and flush
before exit.

The stdin format for each instance:

- lines starting with `%` are comments and may appear anywhere;
- the first non-comment line is `n m 0` (vertices are numbered 1..n);
- the next `n` non-comment lines are the out-adjacency lists: line `u`
  lists the out-neighbors of vertex `u`, space-separated. **A vertex with
  no outgoing edges has an empty line — do not skip empty lines when
  counting vertices.** The graph is simple: no loops, no parallel arcs.

The stdout format:

- one vertex number per line, each in `1..n`, no duplicates, nothing
  else. The empty set (no output) is correct iff the graph is already
  acyclic.

## What's in the environment

- `/app/solver.cpp` — the baseline solver source. Rebuild with
  `bash /app/build.sh`, which produces `/app/solver`. Run it as
  `./solver < instance_file`.
- `/app/instances/` — the 100 public instances (`e_001` … `e_199`,
  odd numbers; 512 to 131072 vertices).
- `/app/examples/` — a demo package: two demo instances, each paired with
  its reference solution (`e_001` + `e_001_solution`, `h_001` +
  `h_001_solution`). (The demo `e_001` shares only its name with the
  public instance `e_001` — different graph.)
- `fvs_verify` — the reference validity checker, on PATH:
  `fvs_verify instance solution.txt` prints `OK` (exit 0) iff the solution
  is a feedback vertex set. Source: `/opt/dfvs/verifier/`. The hidden
  judge uses the same code.
- `/app/public_reference.json` — for each public instance: the baseline's
  FVS size `B` and the best-known size `K` (see the `proven_optimal`
  flag per instance).
- `python3 /app/score_public.py` — rebuilds via `/app/build.sh`, runs
  your solver once per public instance locally with the identical
  per-instance limit the hidden judge uses, validates with `fvs_verify`,
  and prints your results next to the baseline's and the reference
  values. It runs on this development box, outside the judging sandbox —
  allow for differences between development and judging resources.

## Hard rules

- The judge runs `bash /app/build.sh` (10 min limit). If it fails or
  does not produce an executable `/app/solver`, the total score is 0.
  All top-level `/app/*.cpp` files are compiled together by the shipped
  script; keep extra sources in subdirectories if you add many files.
- A crash, a timeout, or an invalid feedback vertex set scores 0 **for
  that instance**; the others still count. The budget is enforced with
  an OS-level hard kill, so a runaway process cannot extend it.
- The output must be a valid feedback vertex set of the input graph
  (checked by the reference verifier). Printing a small number without
  a matching set is worthless.
- Your solver only ever sees one instance at a time.
- The final score comes from a **fresh run** of your final build on the
  hidden instances, executed after your run ends. "It scored well once"
  does not count.
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
