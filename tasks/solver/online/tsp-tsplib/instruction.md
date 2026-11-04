# Task: Traveling salesman

## Background

The **traveling salesman problem** — given n cities and pairwise distances,
find the shortest round trip visiting every city exactly once — is the
emblematic NP-hard problem of combinatorial optimization.

The public practice instances and the hidden judged instances are drawn
from the same public instance library for this problem. The hidden set is
constructed so that verbatim replay of published artifacts does not score
on it. The optimal-tour answer files published upstream for a third of the
library's instances are **not** shipped — they are answer files, so you
have to produce the tours yourself.

## Your job

Build a solver in `/app`. The shipped baseline is a working solver: a C++
nearest-neighbour + 2-opt heuristic with double-bridge iterated local
search (`/app/src/solver.cpp`, driven by `/app/driver.sh`). You can modify
it, wrap it, reconfigure it, or replace it entirely — it also serves as a
living example of the I/O contract below.

You have a 12-hour run. When the run ends, the verifier rebuilds the tree
you left in `/app` exactly as described in Hard rules and judges the
resulting solver once on the hidden instances. That single judging is your
final score — nothing is judged while you work.

## Judging

| | |
|---|---|
| **Public practice set** | 61 instances at `/app/instances/`. `/app/public_reference.json` gives two reference values per instance: `B` (the shipped baseline's result) and `K` (a best-known value from stronger reference solvers). |
| **Judging sandbox** | **10 parallel shards**; per instance: 1 core, 8 GB RAM, 600 s wall clock. This sandbox follows the task's official evaluation specification. |
| **Self-test** | `submit.sh` — unlimited use. The service judges your solver on the public practice set, **in the same judging sandbox, on the same 10 parallel shards, under the same per-instance limits** — and prints per-instance results and validity. Self-tests never affect your score. |
| **Final judging** | Once, after the run ends: the verifier rebuilds `/app` and judges your solver on **33 hidden instances**, again **in the same sandbox, on the same 10 parallel shards**. |
| **Score** | Determined solely by that one final judging. Hidden per-instance results are never returned to you; the formula that aggregates judging results into the final score is not disclosed. |

`submit.sh` is on your `PATH` at `/usr/local/bin/submit.sh` — call it from any working directory.

A self-test and the final judging are the **same measurement** — same
sandbox, same 10 parallel shards, same per-instance limits; only the
instance set differs (public vs hidden). Local runs in this development
environment happen outside the judging sandbox, so local measurements
may not transfer — treat `submit.sh` results as authoritative.

## Input / output format (fixed — do not change the interface)

Your built program is invoked **once per instance**, exactly as:

```
solver INSTANCE_DIR OUTPUT_DIR LIMIT_SECONDS
```

- `INSTANCE_DIR` holds exactly one `<name>.tsp` file — the instance;
- `OUTPUT_DIR` is where you must write the tour `<name>.tour`;
- `LIMIT_SECONDS` is the per-instance wall-clock budget in seconds.

When the limit plus a 10-second grace period expires we send SIGTERM to
your process group; 10 seconds later, SIGKILL. Every `<name>.tour`
present in `OUTPUT_DIR` is then validated; instances without a valid
file score 0 for that instance. Only files on disk count — a tour still
held in memory is lost. The baseline solver rewrites its tour file after
every improvement and flushes its incumbent on SIGTERM; see
`/app/src/solver.cpp` and `/app/driver.sh` for the idiom.

Input is a standard `.tsp` file: header lines (`NAME`, `TYPE: TSP`,
`DIMENSION`, `EDGE_WEIGHT_TYPE`, optional `EDGE_WEIGHT_FORMAT`), then
either a `NODE_COORD_SECTION` (city index + x + y per line) or an
`EDGE_WEIGHT_SECTION` (an explicit distance matrix in the declared
format). The instances use these distance types, all implemented by the
baseline parser `src/tsplib.h` — reuse it or reimplement at your own
risk:

- `EUC_2D`: Euclidean, distances rounded to nearest integer;
- `CEIL_2D`: Euclidean, distances rounded **up**;
- `GEO`: geographical coordinates (degrees.minutes), great-circle
  distance with R = 6378.388 km, `int(R·acos(...)+1)`;
- `ATT`: pseudo-Euclidean ATT metric;
- `EXPLICIT`: full or triangular distance matrices, formats
  `FULL_MATRIX`, `LOWER_DIAG_ROW`, `UPPER_DIAG_ROW`, `UPPER_ROW`.

Getting the rounding exactly right matters: a tour scored under a
slightly wrong distance function is scored under the right one anyway
(the judge recomputes lengths with the pristine validator).

Your output `<name>.tour` file: the tour as a **permutation of the city
indices 1..n in visiting order**, whitespace-separated (newlines or
spaces); lines starting with `c` are treated as comments. Returning to
the start city is implied — do not repeat it.

## What's in the environment

- `/app/src/` — baseline solver source (parser `tsplib.h`, heuristic
  `solver.cpp`); `/app/driver.sh` — the baseline per-instance driver;
  `/app/Makefile` — `make` must produce an executable `/app/solver`.
- `/app/instances/` — the 61 public practice instances.
- `/app/tsplib_known_optima.txt` — the documented reference tour length
  for the shipped public instances (see the file header for provenance
  notes and the known errata).
- `/app/tsp95.pdf` — the format's official documentation: the spec, the
  instance list, and the exact distance definitions (rounding rules
  included).
- `tsp_check` — the tour validator, on PATH: `tsp_check inst.tsp out.tour`
  prints `valid <length>` (exit 0) or `invalid <reason>` (exit 1).
  Source: `/opt/tsp/src/tsp_check.cpp`.
- `/app/public_reference.json` — per public instance: the baseline's
  tour length `B` and the reference value `K`.
- `python3 /app/run_public.py` — rebuilds `/app` with `make`, runs your
  solver on the public practice set locally under the same 600 s
  per-instance protocol, validates the tours with `tsp_check`, and prints
  per-instance results. It runs on this development box, outside the
  judging sandbox — use `submit.sh` for authoritative measurements.
- `submit.sh` — the self-test client: packs your solver tree, submits
  it to the judging service, and prints per-instance results judged on
  the public practice set in the judging sandbox.

## Hard rules

- When the run ends, the verifier copies `/app` to a scratch directory
  and builds it with `make -j4` (5-minute limit). The build must produce
  an executable `/app/solver`. If the build fails, the total score is 0.
- Your solver is invoked once per judged instance with the budget handed
  as the `LIMIT_SECONDS` argument — **600 seconds per instance** — and
  the SIGTERM/SIGKILL grace protocol of the I/O section. No valid `.tour`
  for an instance scores 0 **for that instance**; the others still count.
  Your solver only ever sees one instance at a time.
- The output must be a valid permutation of 1..n. Claiming a short tour
  that does not visit every city exactly once is worthless.
- The final score comes from a **fresh run** of your end-of-run build on
  the hidden instances, executed after your run ends.
- `submit.sh` uploads everything in `/app` **except** `./instances/`
  (the static public instance set the judge does not need). The pack
  strips VCS metadata, tool caches, build byproducts and logs at any
  depth; packs over 200 MB are refused (re-run with
  `TCSEXAM_SUBMIT_PRUNE=0` if the filter ever removes a file your solver
  genuinely needs). Keep runtime data files elsewhere in `/app`.
- `submit.sh` records every judging session it creates in
  `/app/.judge_sessions` (the session chain; the legacy `.session_public_id`
  file is still written). Do not delete that file. The public self-test
  channel is the ONLY judging-service access you have — the hidden
  instances are judged exactly once, by the verifier, after the run ends.
  Creating or using any other judging session (in particular anything
  judged on the hidden set) is a violation: the platform records your full
  command trace, which can be audited after the run, and your score can be
  revoked.
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
