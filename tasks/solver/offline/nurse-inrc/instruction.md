# Task: Nurse rostering

## Background

The **nurse rostering problem**: you are given a planning period for one
hospital ward, a set of shift types (e.g. Early/Late/Day/Night), a team
of nurses each working under a contract (work regulations), a daily
demand (how many nurses are needed per shift type per day), and the
nurses' day-off and shift-off requests. Assign at most one shift per
nurse per day so that the demand is covered **exactly**, and minimize
the total penalty for broken soft constraints (contract violations such
as too many working days in a row, incomplete weekends, unwanted shift
successions, and unmet requests).

The benchmark behind this task is the field's reference instance set.
The complete library is judged, but the instance files were physically
removed from this environment, and there is no network access. The
environment ships the official practice (`hint`) instances at
`/app/instances/` (they are outside the judged library), plus the
complete per-instance results table (`/app/inrc_table.md`).

## Your job

Build a solver in `/app`. The shipped baseline, `/app/solver.cpp`
(penalty-aware greedy construction followed by a short simulated
annealing over four coverage-preserving move types, fixed seed, fixed
iteration count), is a working solver you can modify, wrap, reconfigure,
or replace entirely — it also serves as a living example of the I/O
contract below.

You have a 12-hour run. When the run ends, the verifier rebuilds the
tree you left in `/app` exactly as described in Hard rules and judges
the resulting solver once on the hidden instances. That single judging
is your final score — nothing is judged while you work.

## Judging

| | |
|---|---|
| **Public practice set** | 9 instances at `/app/instances/`. `/app/public_reference.json` gives two reference values per instance: `B` (the shipped baseline's result) and `K` (a best-known value from stronger reference solvers). |
| **Judging sandbox** | Per instance: **1 core**, 600 s wall clock. Each isolated Docker worker reserves 8 GB RAM. Up to 10 workers run concurrently, reduced automatically to fit available host resources. |
| **Local self-test** | Use the public-instance runner described below. It executes in this development environment; local timing can differ from the judging environment. Self-tests never affect your final score. |
| **Final judging** | Once, after the run ends: the verifier rebuilds `/app` and judges your solver on **60 hidden instances**, again **in the same sandbox, on the same 10 parallel shards**. |
| **Score** | Determined solely by that one final judging. Hidden per-instance results are never returned to you; the formula that aggregates judging results into the final score is not disclosed. |

The final verifier runs on the evaluation host through Docker.
Development has no judging-service access. The public-instance
runner below supplies local feedback. Hidden instances are used
only once, after the development run ends.

## Input / output format (fixed — do not change the interface)

Your program reads an instance from **stdin** in the instance XML format
(a `<SchedulingPeriod>` document; see any file in `/app/instances/` for
the exact schema) and writes a roster to **stdout** in the solution XML
format shown here:

```xml
<?xml version="1.0" encoding="utf-8"?>
<Solution>
  <SchedulingPeriodID>sprint02</SchedulingPeriodID>
  <Competitor>you</Competitor>
  <SoftConstraintsPenalty>0</SoftConstraintsPenalty>
  <Assignment><Date>2010-01-01</Date><Employee>3</Employee><ShiftType>E</ShiftType></Assignment>
  ...
</Solution>
```

One `<Assignment>` per (nurse, day) worked; days with no assignment are
days off. Nothing else on stdout. The judge re-parses the roster, checks
the hard rules, and **recomputes the penalty from scratch** — the
`SoftConstraintsPenalty` you print is informational only.

**Validity (hard rules — an invalid roster scores 0 for that
instance):**

1. Every assignment names a known employee, a known shift type, and a
   date inside the planning period; `SchedulingPeriodID` matches the
   instance.
2. **Exact coverage**: for every (day, shift type), the number of
   assigned nurses equals the required number given in the instance
   (`CoverRequirements`). Under-covering *and* over-covering are both
   invalid (this matches the reference evaluator).
3. **One shift per nurse per day.**

**Soft constraints (what the penalty counts).** The penalty is the sum,
over all nurses, of per-contract violations. Each contract switches
constraints on/off and sets limits and weights; different contracts
differ. In the order they appear in the instance files:

- **MaxNumAssignments / MinNumAssignments** (on, weight, limit): total
  worked days beyond/short of the limit, `weight x excess`.
- **MaxConsecutiveWorkingDays / MinConsecutiveWorkingDays**: per maximal
  run of consecutive worked days of length `L`,
  `weight x max(0, L - max)` resp. `weight x max(0, min - L)`; runs
  touching the horizon edges count.
- **MaxConsecutiveFreeDays / MinConsecutiveFreeDays**: same accounting
  over maximal runs of free days; a leading/trailing free run counts
  too.
- **MaxConsecutiveWorkingWeekends / MinConsecutiveWorkingWeekends**:
  same accounting over runs of *worked weekends* (a weekend counts as
  worked if at least one of its days is worked; the weekend definition —
  `SaturdaySunday` or `FridaySaturdaySunday` — is per contract).
- **CompleteWeekends** (weight): each partially worked weekend is
  charged `weight x (weekend length - run length)` per maximal worked
  run inside it (e.g. working only Saturday of a Sat-Sun weekend costs
  `weight`).
- **IdenticalShiftTypesDuringWeekend** (weight): within a worked
  weekend, every shift type worked on `c < weekend length` days is
  charged `weight x (weekend length - c)`.
- **AlternativeSkillCategory** (weight): per assignment where the nurse
  lacks a skill the shift type requires, `weight`.
- **Unwanted patterns** (weight per pattern): per occurrence of a listed
  shift-type sequence on consecutive days (e.g. `N-D`, `D-E-D`),
  `weight`; and the fixed-day pattern
  `None(Friday)-Any(Saturday)-Any(Sunday)` — working a weekend while
  free on its Friday — `weight` per occurrence.
- **DayOff requests** (weight): working on a requested day off,
  `weight` per violation. **ShiftOff requests** (weight): working the
  requested-off shift type on that date, `weight`.

The judge's evaluator is a faithful port of the reference evaluator
published with the instances (validated against it on thousands of
rosters). Two contract elements appear in the files but are *not*
scored — matching the reference evaluator:
`NoNightShiftBeforeFreeWeekend` and `MaxWorkingWeekendsInFourWeeks`.
(The instances contain no `DayOn`/`ShiftOn` requests and no
`DateSpecificCover` either.)

## What's in the environment

- `/app/solver.cpp` — the baseline solver source. Rebuild with
  `bash /app/build.sh`, which produces `/app/solver`.
- `/app/instances/` — the official practice (`hint`) instances, spanning
  all three tracks (`sprint*`, `medium*`, `long*`). They are outside the
  judged library.
- `/app/inrc_table.md` — the consolidated per-instance table for the
  whole library: track, size, the published best-known value, and who
  found it when.
- `/app/public_reference.json` — for the hint instances: the baseline's
  penalty `B` and a reference penalty `K` produced at task construction.
- `python3 /app/run_public.py` — rebuilds via `/app/build.sh`, runs the
  practice instances locally with the same per-instance budget rule the
  hidden judge uses, validates the rosters, recomputes penalties, and
  prints per-instance results. It runs on this development box, outside
  the judging sandbox — allow for differences between development and judging resources.

## Hard rules

- When the run ends, the verifier runs `bash /app/build.sh` (10 min
  limit) on the tree you left in `/app`. If the build fails or does not
  produce an executable `/app/solver`, the total score is 0.
- Each instance is judged in a separate run with its own wall-clock
  limit, handed to your solver in the environment variable
  `NURSE_INSTANCE_SECONDS` (seconds); there is no shared pool and no way
  to carry time between instances. The budget is enforced with an
  OS-level hard kill. An instance killed before printing a valid roster
  scores 0 for that instance. A crash, a nonzero exit code, or an
  invalid roster scores 0 **for that instance**; the others still count.
- The output must satisfy the three validity rules above; the penalty is
  then recomputed.
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
