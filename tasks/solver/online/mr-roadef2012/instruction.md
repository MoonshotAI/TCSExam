# Task: Machine reassignment

## Background

In the **machine reassignment problem** a set of *processes* runs on a
set of *machines*. Each process consumes an amount of several
*resources* (CPU, RAM, ...), and each machine has a finite capacity per
resource. Every process starts on an initial machine. Your job: produce
a **new assignment** of processes to machines that lowers the total cost
while respecting every hard constraint.

**Hard constraints** (all checked by the reference checker):

- **Capacity** — per machine and resource, total usage must not exceed
  capacity. *Transient usage*: a process moved away from its initial
  machine still occupies its **transient** resources on the origin
  machine (during the reassignment both machines are charged). This
  ghost usage matters for the capacity check only; the objective's
  load/balance terms below use current usage only.
- **Conflict** — two processes of the same *service* cannot share a
  machine.
- **Spread** — the processes of a service must occupy at least
  `spreadMin` distinct *locations*.
- **Dependency** — if service A depends on service B, every process of A
  must run in a *neighborhood* where at least one process of B runs.

**Objective** (weighted sum, all weights given in the model file):

- **load cost** — per machine/resource:
  `weight_r * max(0, usage - safetyCapacity)`;
- **balance cost** — per balance triple `(r1, r2, target, weight)` and
  machine: `weight * max(0, target * remaining(r1) - remaining(r2))`;
- **process move cost** — per moved process: `moveCost_p * weightPMC`;
- **service move cost** — `weightSMC * (max over services of the number
  of moved processes in that service)`;
- **machine move cost** — per moved process, a machine-to-machine cost
  from a full matrix, times `weightMMC`.

The problem is NP-hard (it contains vector bin packing as a special
case). The full specification is in `/app/problem_definition_v1_1.pdf`.
The public practice instances and the hidden judged instances are drawn
from the same published instance set of the contest benchmark.

## Your job

Build a solver in `/app`. The shipped baseline, `/app/solver.cpp`
(feasibility-preserving hill climb with shift and swap moves, exact
incremental deltas, fixed seed, fixed work budget), is a working solver
you can modify, wrap, reconfigure, or replace entirely — it also serves
as a living example of the I/O contract below.

You have a 12-hour run. When the run ends, the verifier rebuilds the
tree you left in `/app` exactly as described in Hard rules and judges
the resulting solver once on the hidden instances. That single judging
is your final score — nothing is judged while you work.

## Judging

| | |
|---|---|
| **Public practice set** | 20 instances at `/app/instances/`. `/app/public_reference.json` gives two reference values per instance: `B` (the shipped baseline's result) and `K` (a best-known value from stronger reference solvers). |
| **Judging sandbox** | **10 parallel shards**; per instance: **1 core**, 300 s wall clock (instances judged in parallel; shard containers with 4 cores/8 GB RAM are shared across them). This sandbox follows the task's official evaluation specification. |
| **Self-test** | `submit.sh` — unlimited use. The service judges your solver on the public practice set, **in the same judging sandbox, on the same 10 parallel shards, under the same per-instance limits** — and prints per-instance results and validity. Self-tests never affect your score. |
| **Final judging** | Once, after the run ends: the verifier rebuilds `/app` and judges your solver on **10 hidden instances**, again **in the same sandbox, on the same 10 parallel shards**. |
| **Score** | Determined solely by that one final judging. Hidden per-instance results are never returned to you; the formula that aggregates judging results into the final score is not disclosed. |

`submit.sh` is on your `PATH` at `/usr/local/bin/submit.sh` — call it from any working directory.

A self-test and the final judging are the **same measurement** — same
sandbox, same 10 parallel shards, same per-instance limits; only the
instance set differs (public vs hidden). Local runs in this development
environment happen outside the judging sandbox, so local measurements
may not transfer — treat `submit.sh` results as authoritative.

## Input / output format (fixed — do not change the interface)

Your program is invoked as

```
solver MODEL_FILE INITIAL_ASSIGNMENT_FILE OUTPUT_FILE
```

with the per-instance wall-clock budget (in seconds) in the environment
variable `MR_INSTANCE_SECONDS` (the legacy name `MR_TIME_POOL` is set to
the same value). The model file format is the text format documented in
the PDF and the checker source (whitespace-separated integers; see them
for the exact layout, or read `/app/solver.cpp`'s parser). The
assignment format is `P` integers: token `p` is the machine that process
`p` is assigned to (machine ids are `0..M-1`). Your program writes the
new assignment in the same format to `OUTPUT_FILE`. Exit code 0.

## What's in the environment

- `/app/solver.cpp` — the baseline solver source. Rebuild with
  `bash /app/build.sh`, which produces `/app/solver`.
- `/app/instances/` — the 20 public instances (`model_*.txt` +
  `assignment_*.txt` pairs): the 10 small practice-size ones (`a1`,
  `a2`) and the 10 larger ones (`b_*`). The judged instances are not
  among them.
- `/app/checker-src/` + `/opt/mr/checker` — the reference checker
  (source, and a prebuilt binary). Usage:
  `checker MODEL INITIAL_ASSIGNMENT NEW_ASSIGNMENT` — it prints whether
  the new assignment is valid and its exact objective cost.
- `/app/problem_definition_v1_1.pdf` — the full problem specification.
- `/app/public_reference.json` — for each of the 20 public instances:
  the baseline's cost `B` and the reference best-known cost `K`.
- `python3 /app/run_public.py` — rebuilds via `/app/build.sh`, runs the
  practice set locally with the same per-instance budget rule the hidden
  judge uses, validates every produced assignment with the reference
  checker, and prints per-instance results. It runs on this development
  box, outside the judging sandbox — use `submit.sh` for authoritative
  measurements.
- `/app/roadef2012_final_results.md` — the final standings of the event
  these instances come from: every finalist's per-instance objective on
  the two larger instance sets, all produced under the same 300 s
  budget.
- `submit.sh` — the self-test client: packs your solver tree, submits
  it to the judging service, and prints per-instance results judged on
  the public practice set in the judging sandbox.

## Hard rules

- When the run ends, the verifier runs `bash /app/build.sh` (10 min
  limit) on the tree you left in `/app`. If the build fails or does not
  produce an executable `/app/solver`, the total score is 0. All
  top-level `/app/*.cpp` files are compiled together by the shipped
  script; keep extra sources in subdirectories if you add many files.
- Each instance is judged in a separate run with its own wall-clock
  budget; on every run the budget is handed to your solver in
  `MR_INSTANCE_SECONDS` (and in the legacy name `MR_TIME_POOL`, set to
  the same value). The budget is enforced with an OS-level hard kill.
- If your solver is killed mid-instance, whatever it already wrote to
  `OUTPUT_FILE` is still checked — a valid assignment on disk counts.
- A crash, a nonzero exit code, or an **invalid** assignment (any hard
  constraint violated, malformed file) scores 0 **for that instance**;
  the others still count. The reference checker decides validity; the
  judge never trusts your solver's own output claims.
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
