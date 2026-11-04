# Task: Radiation therapy planning

## Background

In **intensity-modulated radiation therapy (IMRT)** planning, the
radiation field is discretized into an `m × n` grid of cells, and each
cell must receive a prescribed total dose — an integer **intensity
matrix** `Intensity[i,j]`. The dose is delivered through a multileaf
collimator that can form **shape matrices**: binary patterns in which
the exposed cells of every row form one contiguous interval (rows are
independent of each other). A shape matrix delivered for `b` time units
contributes `b` to every cell it exposes. The planning problem is to
decompose the intensity matrix into shape matrices and their beam-on
times so that the delivered dose matches the prescription exactly, while
using as little total beam-on time and as few shapes as possible. This
matrix-decomposition problem (multileaf collimator sequencing) is
NP-hard and a classical benchmark of constraint programming.

The judged set has **47 instances**: the full candidate pool of 24 hard
generated instances plus the 23 instances published in the MiniZinc
benchmarks repository. 36 of them are **hidden** — their files are not
in this environment, and there is no network access, so the first time
your solver sees them is at judging time. The 11 published instances
already shipped under `/app/instances/` are judged too. The environment
also ships 4 further generated practice instances (not in the hidden
judged set; the self-test channel still judges them), and
verified solutions for 6 of the practice instances under `/app/solutions/`.

## Your job

Build a solver in `/app`. The shipped baseline, `/app/solve.sh` (it
prints the deterministic unit-time construction from
`/app/construct_lb.py` — every cell `(i,j)` covered by exactly
`Intensity[i,j]` shape matrices of beam-on time 1, with `N[1] = LB`),
is a working solver you can modify, wrap, reconfigure, or replace
entirely — it also serves as a living example of the I/O contract
below.

You have a 12-hour run. When the run ends, the verifier rebuilds the
tree you left in `/app` exactly as described in Hard rules and judges
the resulting solver once on the hidden instances. That single judging
is your final score — nothing is judged while you work.

## Judging

| | |
|---|---|
| **Public practice set** | 15 instances at `/app/instances/` — **11 of them are also part of the judged set**. `/app/public_reference.json` gives two reference values per instance: `B` (the shipped baseline's result) and `K` (a best-known value from stronger reference solvers). |
| **Judging sandbox** | **6 parallel shards**; per instance: 1 core, 16 GB RAM, 1200 s wall clock. This sandbox follows the task's official evaluation specification. |
| **Self-test** | `submit.sh` — unlimited use. The service judges your solver on the public practice set, **in the same judging sandbox, on the same 6 parallel shards, under the same per-instance limits** — and prints per-instance results and validity. Self-tests never affect your score. |
| **Final judging** | Once, after the run ends: the verifier rebuilds `/app` and judges your solver on **36 hidden instances plus 11 instances shipped in your environment**, again **in the same sandbox, on the same 6 parallel shards**. |
| **Score** | Determined solely by that one final judging. Hidden per-instance results are never returned to you; the formula that aggregates judging results into the final score is not disclosed. |

`submit.sh` is on your `PATH` at `/usr/local/bin/submit.sh` — call it from any working directory.

A self-test and the final judging are the **same measurement** — same
sandbox, same 6 parallel shards, same per-instance limits; only the
instance set differs (public vs hidden). Local runs in this development
environment happen outside the judging sandbox, so local measurements
may not transfer — treat `submit.sh` results as authoritative.

## Input / output format (fixed — do not change the interface)

A decomposition is fully described by two integer arrays (this is
exactly the formulation of the shipped reference model
`radiation.mzn`):

- `N[b]` — how many shape matrices are delivered with beam-on time `b`
  (for `b = 1 .. Bt_max`, where `Bt_max` is the largest intensity
  value);
- `Q[i,j,b]` — how many of those `N[b]` shapes expose cell `(i,j)`.

Feasibility is precisely:

- **(C1)** every cell receives its prescribed dose:
  `Intensity[i,j] = Σ_b b · Q[i,j,b]` for all `i, j`;
- **(C2)** every row can be realized with the available shapes:
  `N[b] ≥ Q[i,1,b] + Σ_{j≥2} max(Q[i,j,b] − Q[i,j−1,b], 0)` for all
  `i, b`.

(The right-hand side of C2 is the number of contiguous intervals a row
needs at level `b`; one shape supplies one interval per row
simultaneously, so `N[b]` must cover the need of every row.)

Every feasible decomposition obeys a structural lower bound on the total
beam-on time. Weighting condition C2 by `b` and summing over `b` gives,
for every row `i`,

```
Beamtime = Σ_b b·N[b]  ≥  t_i = Intensity[i,1] + Σ_{j≥2} max(Intensity[i,j] − Intensity[i,j−1], 0)
```

so `Beamtime ≥ LB`, where `LB = max_i t_i` is the maximum per-row total
positive gradient of the intensity matrix. The judged instances (and the
shipped practice instances) are verified to admit a decomposition with
`Beamtime = LB`, so on them the bound is exactly attainable.

The per-instance objective has two aspects:

1. **Admission.** A solution with `Beamtime > LB` counts as invalid for
   that instance. (`Beamtime < LB` is impossible.)
2. **Shape count.** A solution with `Beamtime = LB` is measured on its
   number of shapes alone: smaller is better. The value reported to the
   judge is

```
objective = Σ_b N[b]        (number of shape matrices, at Beamtime = LB)
```

Your solver is invoked as

```
/app/solver INSTANCE_PATH
```

with the path of a `.dzn` instance file as its only argument. The
instance file assigns `m`, `n`, and `Intensity` (a row-major
`[| ... |]` array), exactly like the shipped public instances. Your
solver writes its answer to **stdout** as one or more solution blocks in
the format the shipped model's output statement produces:

```
objective = <int>;
Beamtime = <int>;
K = <int>;
N = [<Bt_max comma-separated integers>];
Q = array3d(<rows>, <cols>, <btimes>, [<m*n*Bt_max comma-separated integers>]);
```

The judge only reads the `N = [...];` and `Q = array3d(..., [...]);`
parts — everything else (including any self-declared `objective`) is
ignored. Q is flattened in the same order the model prints it. The judge
reads the **LAST complete** N/Q block on stdout. Validity = C1 and C2
above hold, all entries are nonnegative integers, and the array lengths
match the instance; the judge then **recomputes the beam-on time, the
shape count, and the structural lower bound itself**.

## What's in the environment

- `/app/radiation.mzn` — the reference model (the original
  lexicographic objective; kept for reference).
- `/app/radiation_lb.mzn` — the same feasibility constraints plus the
  hard `Beamtime ≤ LB` constraint, minimizing the shape count: the
  objective rule expressed as a model.
- `/app/solve.sh`, `/app/solve.py`, `/app/construct_lb.py` — the
  baseline pipeline (the unit-time constructor). Rebuild with
  `bash /app/build.sh`, which produces `/app/solver`.
- `/app/construct_binary.py` — an alternative constructor whose beam-on
  time exceeds `LB`, so its output counts as invalid under the admission
  rule.
- `/app/solver` — the currently built solver. Run it as
  `./solver instances/01.dzn`.
- `minizinc` (2.10.0) with solvers **CP-SAT** (`--solver cp-sat`),
  **Chuffed** (`--solver chuffed`), **Gecode**, **CBC**, **HiGHS**; plus
  `python3` and `g++`.
- `/app/instances/` — the 15 shipped instances (the small `01`–`09`,
  `m06_15_15` and `m07_07_20`, and the larger `pub*` instances): 11 of
  them are also in the judged set (see Background); the other 4 are
  practice-only.
- `/app/instances_table.md` — per-instance table for the shipped
  instances: size, the baseline's objective, and the best known value.
- `/app/solutions/` — verified solutions for 6 of the practice instances,
  in exactly the output format above.
- `/app/public_reference.json` — for each shipped instance: the
  baseline's objective `B` and the reference value `K`.
- `python3 /app/run_public.py` — rebuilds via `/app/build.sh`, runs the
  public instances locally with a hard per-instance wall-clock limit
  (60 s by default for quick iteration — set `PER_INSTANCE_SECONDS` to
  override; the judging sandbox uses its own per-instance budget),
  validates the solutions, recomputes the objectives, and prints
  per-instance results. It runs on this development box, outside the
  judging sandbox — use `submit.sh` for authoritative measurements.
- `submit.sh` — the self-test client: packs your solver tree, submits
  it to the judging service, and prints per-instance results judged on
  the public practice set in the judging sandbox.

## Hard rules

- When the run ends, the verifier runs `bash /app/build.sh` (10 min
  limit) on the tree you left in `/app`. If the build fails or does not
  produce an executable `/app/solver`, the total score is 0.
- Each instance is judged in a separate run with its own hard wall-clock
  limit, handed to your solver in the environment variable
  `RADIATION_TIME_LIMIT` (seconds). The limit is enforced with an
  OS-level hard kill; a killed solver keeps whatever complete solution
  blocks it already printed — the last one counts.
- An invalid solution (wrong array length, a negative entry, a violated
  C1/C2 condition, a missing or truncated final block) scores 0 **for
  that instance**; so does a valid solution whose beam-on time exceeds
  the structural lower bound `LB`. The other instances still count. A
  nonzero exit code with no usable output is handled the same way.
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
