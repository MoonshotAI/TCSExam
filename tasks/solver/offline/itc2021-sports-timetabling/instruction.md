# Task: Sports timetabling

## Background

In **sports timetabling** you are given an even number of teams and must
build a **compact double round-robin schedule** — every pair of teams
plays twice (once at each home venue), every team plays exactly one game
in every round. On top of this backbone, the instance imposes constraints
from nine classes — capacity (CA1–CA4: how many home/away games given
teams play in given slot sets, against given opponent groups, in any
window of consecutive slots), game (GA1: how many listed games a slot set
hosts), breaks (BR1/BR2: home streaks / away streaks), fairness (FA2:
teams must have played a similar number of games by every round) and
separation (SE1: minimum distance between the two legs of a pair). Some
are marked HARD in the instance; the rest are soft, and each violated soft
constraint adds its penalty to the objective. The goal: **minimize the
total soft penalty while keeping every hard constraint satisfied**. A
schedule with any hard violation is worthless (that instance scores 0).

Sports timetabling is NP-hard.

The public practice instances and the hidden judged instances are drawn
from the same public competition benchmark for this problem. The hidden
set is constructed so that verbatim replay of published artifacts does
not score on it.

## Your job

Build a solver in `/app`. The shipped baseline, `/app/solver.cpp`, is a
working solver you can modify, wrap, reconfigure, or replace entirely —
it also serves as a living example of the I/O contract below. It builds a
mirrored compact double round robin by the circle method, then improves it
by simulated annealing over two compactness-preserving moves, with an
exact in-house port of the nine constraint classes as the objective. It
runs with a fixed seed and a pinned iteration budget, so its results are
reproducible on any machine.

You have a 12-hour run. When the run ends, the verifier rebuilds the tree
you left in `/app` exactly as described in Hard rules and judges the
resulting solver once on the hidden instances. That single judging is your
final score — nothing is judged while you work.

## Judging

| | |
|---|---|
| **Public practice set** | 29 instances at `/app/instances/`. `/app/public_reference.json` gives two reference values per instance: `B` (the shipped baseline's result) and `K` (a best-known value from stronger reference solvers). |
| **Judging sandbox** | **One local Docker worker**; per instance: 4 cores, 8 GB RAM; one shared time pool of 960 seconds covers all judged instances (60 s per instance x instance count) — no per-instance limit. This sandbox follows the task's official evaluation specification. |
| **Local self-test** | Use the public-instance runner described below. It executes in this development environment; local timing can differ from the judging environment. Self-tests never affect your final score. |
| **Final judging** | Once, after the run ends: the verifier rebuilds `/app` and judges your solver on **16 hidden instances**, again **in the same sandbox**. |
| **Score** | Determined solely by that one final judging. Hidden per-instance results are never returned to you; the formula that aggregates judging results into the final score is not disclosed. |

The final verifier runs on the evaluation host through Docker.
Development has no judging-service access. The public-instance
runner below supplies local feedback. Hidden instances are used
only once, after the development run ends.

## Input / output format (fixed — do not change the interface)

Your program reads an instance from **stdin** in the RobinX XML format (an
`<Instance>` document; see any file in `/app/instances/` for the exact
schema) and writes a schedule to **stdout** in the RobinX solution XML
format:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Solution>
  <MetaData>
    <InstanceName>Early_1</InstanceName>
    <Contributor>you</Contributor>
  </MetaData>
  <Games>
    <ScheduledMatch home="0" away="1" slot="0"/>
    ...
  </Games>
</Solution>
```

One `<ScheduledMatch>` per game (every ordered pair of teams must appear
exactly once across the whole schedule: `n * (n - 1)` games). Nothing else
on stdout. The judge re-parses the schedule with the RobinX validator and
**recomputes every constraint from scratch** — any metadata you print
about objective values is ignored.

**Validity (an invalid schedule scores 0 for that instance):** the
validator reports its objective as two columns `(hard violations, soft
penalty)`. The first column must be 0. It includes: every game scheduled
exactly once; at most one game per team per round (compactness); the
phased structure on phased instances (each half of the season is a
complete round robin); and every constraint marked `HARD` in the
instance.

## What's in the environment

- `/app/solver.cpp` — the baseline solver. Rebuild with
  `bash /app/build.sh`, which produces `/app/solver`.
- `/app/budgets.tsv` — the baseline's pinned per-instance iteration
  budgets (looked up by instance hash).
- `/app/instances/` — the 29 public practice instances (with an md5
  manifest `instances.md5`).
- `/app/itc2021_table.md` — per-instance published best-known results
  for the public practice instances.
- `/app/public_reference.json` — per public instance: the baseline's
  penalty `B` and the reference best-known penalty `K`.
- `/opt/itc2021/RobinX` — the RobinX Validator 2.0 binary, the same build
  the judge uses; run it directly
  (`RobinX -i instance.xml -s solution.xml`) to validate any schedule
  during development.
- `python3 /app/run_public.py` — rebuilds `/app`, runs your solver on the
  public practice set locally under the same shared time pool protocol,
  validates with the reference validator, and prints per-instance
  results. It runs on this development box, outside the judging sandbox —
  allow for differences between development and judging resources.

## Hard rules

- When the run ends, the verifier runs `bash /app/build.sh` (10 min limit)
  on the tree you left in `/app`. If the build fails or does not produce an
  executable `/app/solver`, the total score is 0.
- **One shared time pool covers all judged instances — there is no
  per-instance limit.** On every run the remaining pool is handed to your
  solver in the environment variable `ITC2021_TIME_POOL` (seconds). When
  the pool is used up, the running instance is hard-killed and every
  instance without a verified result scores 0 for that instance. Your
  solver decides how to divide the pool across instances.
- Your solver only ever sees one instance at a time.
- An invalid schedule (any hard-constraint violation), malformed output,
  a crash, or a nonzero exit code scores 0 **for that instance**; the
  others still count.
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
