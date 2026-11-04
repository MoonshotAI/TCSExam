# Task: 2D guillotine glass cutting

## Background

Flat glass plates are cut into ordered rectangular pieces. Plates are
6000 × 3210 mm and arrive **in a fixed order**; each plate carries
**defects** (small rectangles that no produced piece may overlap).
Pieces are grouped in **stacks**, and the pieces of each stack must come
off the line **in the given sequence** (rebuilt from the cutting
patterns by a depth-first traversal). Cuts are **guillotine cuts**: a
piece must be obtainable with at most 3 cuts, plus at most one extra
"trimming" cut inside each sub-plate left after a 3-cut (a branch at cut
depth 3 or 4 has at most 2 children). First cuts are always vertical,
with widths between 100 and 3500 mm (wastes excepted); second-cut
heights are at least 100 mm; every waste rectangle is at least
20 × 20 mm. Pieces may be rotated 90°.

The **objective** is to minimize glass waste: with `m` used plates of
size `W × H`, item areas `wᵢhᵢ`, and the reusable **residual** of width
`r` on the last used plate (the full-height strip right of the last
1-cut),

```
waste = m·W·H − H·r − Σᵢ wᵢ·hᵢ          (minimize)
```

The public practice instances and the hidden judged instances are drawn
from the same recent cutting-stock contest benchmark.

## Your job

Build a solver in `/app`. The shipped baseline, `/app/naive_shelf.py`
(a deterministic single-pass shelf-packing constructor, installed as
`/app/solver` by `/app/build.sh`), is a working solver you can modify,
wrap, reconfigure, or replace entirely — it also serves as a living
example of the I/O contract below.

You have a 12-hour run. When the run ends, the verifier rebuilds the
tree you left in `/app` exactly as described in Hard rules and judges
the resulting solver once on the hidden instances. That single judging
is your final score — nothing is judged while you work.

## Judging

| | |
|---|---|
| **Public practice set** | 35 instances at `/app/instances/`. `/app/public_reference.json` gives two reference values per instance: `B` (the shipped baseline's result) and `K` (a best-known value from stronger reference solvers). |
| **Judging sandbox** | Per instance: **1 core**, two consecutive runs of 180 s and 3600 s. Each isolated Docker worker reserves 32 GB RAM. Up to 10 workers run concurrently, reduced automatically to fit available host resources. |
| **Local self-test** | Use the public-instance runner described below. It executes in this development environment; local timing can differ from the judging environment. Self-tests never affect your final score. |
| **Final judging** | Once, after the run ends: the verifier rebuilds `/app` and judges your solver on **15 hidden instances**, again **in the same sandbox, on the same 10 parallel shards**. |
| **Score** | Determined solely by that one final judging. Hidden per-instance results are never returned to you; the formula that aggregates judging results into the final score is not disclosed. |

The final verifier runs on the evaluation host through Docker.
Development has no judging-service access. The public-instance
runner below supplies local feedback. Hidden instances are used
only once, after the development run ends.

## Input / output format (fixed — do not change the interface)

Your program is called as

```
/app/solver <instance_prefix> <output_csv>
```

with this run's time limit (seconds) in environment variable
`GLASSCUT_TIME_LIMIT`. For every judged instance the judge calls your
program **twice, in two independent invocations**: once with a
**3-minute** limit and once with a **1-hour** limit (the official final
format of the contest benchmark; see Hard rules).

Three files describe the instance:

- `<instance_prefix>_batch.csv` — header, then
  `ITEM_ID;LENGTH_ITEM;WIDTH_ITEM;STACK;SEQUENCE` per piece;
- `<instance_prefix>_defects.csv` — header, then
  `DEFECT_ID;PLATE_ID;X;Y;WIDTH;HEIGHT` per defect (values may carry
  decimals; the judge truncates them toward zero like the reference
  checker);
- `global_param.csv` next to them — the plate count limit (100), plate
  dimensions, and the cut limits `min1Cut`/`max1Cut`/`min2Cut`/`minWaste`.

Your program writes the cutting patterns to `<output_csv>` in the
solution format: one header line
(`PLATE_ID;NODE_ID;X;Y;WIDTH;HEIGHT;TYPE;CUT;PARENT`), then rows that
form one tree per used plate:

- rows are numbered by `NODE_ID` 0..N−1 **in file order** (plate rows
  included);
- a **plate row** has an empty `PARENT`, `PLATE_ID` 0,1,2,… in order,
  the plate dimensions, `CUT` 0; all rows of a plate directly follow
  their plate row (one contiguous block per plate);
- a **node row** has `TYPE` = the item id (≥ 0) for a produced piece,
  `-1` waste, `-2` branch, `-3` residual; `CUT` = parent's `CUT` + 1;
  the children of a plate or branch tile its rectangle exactly and in
  order — odd cut levels are vertical strips side by side along x, even
  cut levels horizontal strips along y (first child at the parent's
  origin, last child reaching the parent's far edge);
- a branch with `CUT` ≥ 3 has at most 2 children (the trimming rule);
  the deepest allowed cut level is 4;
- at most one **residual**: a 1-cut child of the *last* used plate, and
  the last row of that plate's block. A *waste* in exactly that position
  is treated as the residual.

Validity is recomputed by the judge (nothing you print is trusted):
every batch item produced exactly once with the right dimensions
(rotation allowed), per-stack sequence respected in depth-first order,
no item overlapping a defect, no cut through a defect (every defect lies
entirely inside one leaf rectangle), all size limits above respected, at
most 100 plates. The objective is recomputed from the valid pattern.

## What's in the environment

- `/app/naive_shelf.py` — the baseline solver source (its module
  docstring describes the exact layout rules). `/app/build.sh` installs
  it as `/app/solver`.
- `/app/instances/` — the 35 public instances (sets A and B) plus
  `global_param.csv`. The judged instances are not among them.
- `/app/instances_table.md` — per-instance table for the shipped
  instances: size (items / defects / stacks), the baseline's waste `B`,
  and the best-known waste `K`.
- `/app/solutions/` — verified best-known cutting patterns for 8 of the
  practice instances, in exactly the solution format above.
- `/app/public_reference.json` — for each public instance: the baseline's
  waste `B` and the best-known waste `K`.
- `python3 /app/run_public.py` — rebuilds via `/app/build.sh`, runs the
  public instances locally under the same dual-run protocol (a 3-minute
  run and a 1-hour run per instance), validates the patterns, recomputes
  waste, and prints per-instance results (both runs' waste values, the
  official composite, validity). It runs on this development box,
  outside the judging sandbox — allow for differences between development and judging resources.

## Hard rules

- The judge runs `bash /app/build.sh` (10 min limit). If it fails or
  does not produce an executable `/app/solver`, the total score is 0.
- Every judged instance is evaluated under the official final format of
  the contest benchmark: your solver runs **twice** on the instance —
  first with a **3-minute** wall-clock limit, then, in a separate fresh
  invocation, with a **1-hour** wall-clock limit — and the instance's
  judged value is the official weighted composite of the two runs' waste
  values: **0.1 × (3-minute waste) + 0.9 × (1-hour waste)**. Each run's
  limit is handed to your solver in `GLASSCUT_TIME_LIMIT` (seconds) and
  enforced with an OS-level hard kill: a process still running at the
  limit is killed and that run counts as failed — each run must exit
  cleanly and have written its output file before its limit.
- By the official rule, a run that fails (killed at the limit, crash,
  invalid pattern, missing output) does not zero the instance: the
  shipped baseline's value stands in for that run in the composite. Only
  when **both** runs of an instance fail does the instance score 0; the
  other instances still count.
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
