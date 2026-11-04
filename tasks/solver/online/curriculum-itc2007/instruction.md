# Task: Curriculum-based course timetabling

## Background

The **curriculum-based course timetabling problem (CB-CTT)**: a
university publishes curricula (sets of courses that students of a
programme take together), and every course has a teacher, a number of
weekly lectures, a minimum number of days those lectures should spread
over, and a student count. Assign every lecture to a **room** and a
**period** (day × timeslot) of the week.

A timetable is **feasible** only if it violates none of the four hard
constraints:

- **Lectures**: every lecture of every course is scheduled (no missing, no
  extra lectures);
- **Conflicts**: no two lectures share a period if they have the same
  teacher or belong to the same curriculum;
- **Availability**: no lecture sits in a period declared unavailable for
  its course;
- **RoomOccupation**: no two lectures share a room in the same period.

Among feasible timetables, quality is the **soft-constraint penalty**
(lower is better):

- **RoomCapacity**: for each lecture, 1 point per student above the room's
  seat count;
- **MinimumWorkingDays**: 5 points per day below the course's minimum
  spread;
- **CurriculumCompactness**: 2 points per lecture of a curriculum that is
  isolated (no adjacent lecture of the same curriculum on the same day);
- **RoomStability**: 1 point per additional distinct room used by a
  course.

CB-CTT is NP-hard. The instances are real university data.

The public practice instances and the hidden judged instances are drawn
from the same public competition benchmark for this problem. The hidden
set is constructed so that verbatim replay of published artifacts does
not score on it.

## Your job

Build a solver in `/app`. The shipped baseline is a working solver you can
modify, wrap, reconfigure, or replace entirely — it also serves as a
living example of the I/O contract below. It is a strong reference solver
for this problem (CPSolver, vendored under its LGPL-3 license, see
`/app/lgpl.txt`), with the wall-clock timeout replaced by a fixed
**iteration budget** (`Termination.MaxIters` in `/app/ctt.properties`)
and a fixed seed — that makes the baseline perfectly reproducible on any
machine.

You have a 12-hour run. When the run ends, the verifier rebuilds the tree
you left in `/app` exactly as described in Hard rules and judges the
resulting solver once on the hidden instances. That single judging is your
final score — nothing is judged while you work.

## Judging

| | |
|---|---|
| **Public practice set** | 12 instances at `/app/instances/`. `/app/public_reference.json` gives two reference values per instance: `B` (the shipped baseline's result) and `K` (a best-known value from stronger reference solvers). |
| **Judging sandbox** | **10 parallel shards**; per instance: 1 core, 8 GB RAM, 240 s wall clock. This sandbox follows the task's official evaluation specification. |
| **Self-test** | `submit.sh` — unlimited use. The service judges your solver on the public practice set, **in the same judging sandbox, on the same 10 parallel shards, under the same per-instance limits** — and prints per-instance results and validity. Self-tests never affect your score. |
| **Final judging** | Once, after the run ends: the verifier rebuilds `/app` and judges your solver on **6 hidden instances**, again **in the same sandbox, on the same 10 parallel shards**. |
| **Score** | Determined solely by that one final judging. Hidden per-instance results are never returned to you; the formula that aggregates judging results into the final score is not disclosed. |

`submit.sh` is on your `PATH` at `/usr/local/bin/submit.sh` — call it from any working directory.

A self-test and the final judging are the **same measurement** — same
sandbox, same 10 parallel shards, same per-instance limits; only the
instance set differs (public vs hidden). Local runs in this development
environment happen outside the judging sandbox, so local measurements
may not transfer — treat `submit.sh` results as authoritative.

## Input / output format (fixed — do not change the interface)

Your program reads an instance from **stdin** in the `.ctt` text format:
a header (`Name:`, `Courses:`, `Rooms:`, `Days:`, `Periods_per_day:`,
`Curricula:`, `Constraints:`), then four sections `COURSES:`, `ROOMS:`,
`CURRICULA:`, `UNAVAILABILITY_CONSTRAINTS:`, then `END.` Each course line
is `<CourseID> <Teacher> <#Lectures> <MinWorkingDays> <#Students>`; each
room line is `<RoomID> <Capacity>`; each curriculum line is
`<CurriculumID> <#Courses> <MemberID> ...`; each constraint line is
`<CourseID> <Day> <Day_Period>`. Days and periods are 0-based.

Your program writes a timetable to **stdout**: exactly one line per
lecture, in any order:

```
<CourseID> <RoomID> <Day> <Day_Period>
```

Nothing else on stdout. A course with `L` lectures must appear on exactly
`L` lines. Validity = zero hard-constraint violations as recomputed by
the reference validator (feasibility), and the judge then recomputes the
soft penalty itself.

## What's in the environment

- `/app/solver` — the currently built solver. Run it as
  `./solver < instance.ctt > my.out`.
- `/app/cpsolver-src`, `/app/lib`, `/app/ctt.properties` — the reference
  solver's sources, bundled jars, and configuration. Rebuild with
  `bash /app/build.sh`.
- `/opt/ctt/validator` — the **reference validator** (source
  `/opt/ctt/validator.cc`). Run `/opt/ctt/validator instance.ctt my.out`:
  it lists every violation and ends with the four hard-constraint counts
  and `Total Cost = <penalty>`. The judge uses this same binary.
- `/app/instances/` — the 12 public practice instances.
- `/app/itc2007_table.md` — per-instance table for the public practice
  instances: size, the baseline's penalty `B`, and the best-known
  penalty `K`.
- `/app/solutions/` — verified best-known timetables for four of the
  practice instances, in exactly the output format above (each re-checked
  with the reference validator: feasible, cost exactly `K`).
- `/app/public_reference.json` — per public instance: the baseline's
  penalty `B` and the reference best-known penalty `K`.
- `python3 /app/run_public.py` — rebuilds `/app`, runs your solver on the
  public practice set locally under the same 240 s per-instance limit,
  validates with the reference validator, and prints per-instance
  results. It runs on this development box, outside the judging sandbox —
  use `submit.sh` for authoritative measurements.
- `submit.sh` — the self-test client: packs your solver tree, submits it to
  the judging service, and prints per-instance results judged on the public
  practice set in the judging sandbox.

## Hard rules

- When the run ends, the verifier runs `bash /app/build.sh` (10 min limit)
  on the tree you left in `/app`. If the build fails or does not produce an
  executable `/app/solver`, the total score is 0.
- Your solver gets a **hard per-instance wall-clock limit of 240 seconds**
  on every judged instance (the limit is handed to your solver in the
  environment variable `CTT_TIME_LIMIT`, in seconds). The limit is
  enforced with an OS-level hard kill; an instance that hits the limit
  scores 0 **for that instance**, and the remaining instances are
  unaffected.
- Your solver only ever sees one instance at a time.
- An infeasible timetable (any hard-constraint violation), malformed
  output, a crash, a nonzero exit code, or no output at all scores 0 **for
  that instance**; the others still count.
- The final score comes from a **fresh run** of your final build on the
  hidden instances, executed after your run ends.
- `submit.sh` uploads everything in `/app` **except** `./instances/`
  and `./solutions/` (static public assets the judge does not need).
  The pack also strips VCS metadata, tool caches, build byproducts and logs
  at any depth, and packs over 200 MB are refused (if the filter ever
  removes a file your solver genuinely needs, re-run with
  `TCSEXAM_SUBMIT_PRUNE=0`). If your
  solver needs runtime data files, keep them elsewhere in `/app`.
- `submit.sh` records every judging session it creates in
  `/app/.judge_sessions` (the session chain; the legacy `.session_public_id`
  file is still written). Do not delete that file.
  The public self-test channel is the ONLY judging-service access you
  have — the hidden instances are judged exactly once, by the verifier,
  after the run ends. Creating or using any other judging sessions (in
  particular anything judged on the hidden set) is a violation: the
  platform records your full command trace, which can be audited after the
  run, and your score can be revoked.
- No internet access except the judging service.
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
