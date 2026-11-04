# Task: Hierarchical production

## Background

This task is a deterministic single-player resource-compounding game. You
own a small factory: `N = 10` machine types, each existing at `L = 4`
levels. The game lasts `T = 500` turns, and you start with `K` apples (the
currency; `K = 1` in every instance here).

Each turn has two phases:

1. **Action** — you may buy **one upgrade** or do nothing. Buying one more
   machine of type `id` at level `level` costs
   `C[level][id] * (P[level][id] + 1)` apples, where `P[level][id]` is how
   many you already bought. You must afford the full cost at that moment.
2. **Production** — every machine produces:
   - level 0: for each `id`, `apples += A[id] * B[0][id] * P[0][id]`;
   - level `l > 0`: `B[l-1][id] += B[l][id] * P[l][id]`, i.e. level-`l`
     machines manufacture level-`l-1` machines (which then produce every
     following turn).

`B[l][id]` (machines owned) starts at 1 everywhere, `P` (machines
purchased) at 0. All arithmetic in the judge is **signed 64-bit with
wrap-around**, matching the reference scorer shipped under `/app/tools/`.

Your raw score for an instance is

```
raw = round(100000 * log2(final_apples))      (0 if the run breaks the rules)
```

— logarithmic in the final apple count, so every doubling of your
compounding engine is worth the same fixed increment. An upgrade sequence
that cannot pay for one of its purchases at the moment it runs, or ends
with non-positive apples, scores 0.

The public practice instances and the hidden judged instances are drawn
from the same generator for this problem. The hidden set is constructed so
that verbatim replay of published artifacts does not score on it.

## Your job

Build a solver in `/app`. The shipped baseline, `/app/solver.cpp`, is a
working solver you can modify, wrap, reconfigure, or replace entirely —
it also serves as a living example of the I/O contract below: a
deterministic cheapest-first greedy (every turn, buy the cheapest
affordable upgrade; ties by lower level then lower id; if nothing is
affordable, do nothing).

You have a 12-hour run. When the run ends, the verifier rebuilds the tree
you left in `/app` exactly as described in Hard rules and judges the
resulting solver once on the hidden instances. That single judging is your
final score — nothing is judged while you work.

## Judging

| | |
|---|---|
| **Public practice set** | 105 instances at `/app/instances/`. `/app/public_reference.json` gives two reference values per instance: `B` (the shipped baseline's result) and `K` (a best-known value from stronger reference solvers). |
| **Judging sandbox** | **10 parallel shards**; per instance: **1 core**, 2 s wall clock (instances judged in parallel; shard containers with 4 cores/8 GB RAM are shared across them). This sandbox follows the task's official evaluation specification. |
| **Self-test** | `submit.sh` — unlimited use. The service judges your solver on the public practice set, **in the same judging sandbox, on the same 10 parallel shards, under the same per-instance limits** — and prints per-instance results and validity. Self-tests never affect your score. |
| **Final judging** | Once, after the run ends: the verifier rebuilds `/app` and judges your solver on **45 hidden instances**, again **in the same sandbox, on the same 10 parallel shards**. |
| **Score** | Determined solely by that one final judging. Hidden per-instance results are never returned to you; the formula that aggregates judging results into the final score is not disclosed. |

`submit.sh` is on your `PATH` at `/usr/local/bin/submit.sh` — call it from any working directory.

A self-test and the final judging are the **same measurement** — same
sandbox, same 10 parallel shards, same per-instance limits; only the
instance set differs (public vs hidden). Local runs in this development
environment happen outside the judging sandbox, so local measurements
may not transfer — treat `submit.sh` results as authoritative.

## Input / output format (fixed — do not change the interface)

Your program reads an instance from **stdin**:

- line 1: `N L T K` (always `10 4 500 1` in this task, but read them);
- line 2: `N` integers `A[0..N-1]`;
- next `L` lines: `N` integers each, the cost table `C[level][id]`.

Your program writes exactly **`T` action lines** to **stdout**: each line
is either `-1` (do nothing this turn) or `<level> <id>` (buy one machine
of type `id` at level `level`; `0 <= level < L`, `0 <= id < N`). Blank
lines and lines starting with `#` are ignored by the judge. Nothing else
on stdout. The judge re-simulates your actions from scratch — it does not
trust anything your program claims.

## What's in the environment

- `/app/solver.cpp` — the greedy baseline. Rebuild with
  `bash /app/build.sh`, which produces `/app/solver`.
- `/app/solver` — the currently built solver. Run it as
  `./solver < instance_file`.
- `/app/instances/` — the 105 public practice instances.
- `/app/tools/` — a reference tester package source (generator + scorer +
  visualizer: `src/lib.rs`, `src/bin/gen.rs`, `src/bin/vis.rs`,
  `Cargo.toml`, `seeds.txt`, `README.html`). There is no Rust toolchain in
  this environment; the package is provided as authoritative documentation
  of the generator and the scoring rule. Porting the generator to build
  your own extra practice instances is allowed.
- `/app/public_reference.json` — per public instance: the baseline's raw
  score `B`; the reference best-known raw score `K` is included where a
  measured one exists (`null` otherwise).
- `python3 /app/run_public.py` — rebuilds `/app`, runs your solver on the
  public practice set locally under the same 2 s per-instance limit,
  validates and re-simulates your action sequences, and prints
  per-instance results. It runs on this development box, outside the
  judging sandbox — use `submit.sh` for authoritative measurements.
- `submit.sh` — the self-test client: packs your solver tree, submits it to
  the judging service, and prints per-instance results judged on the public
  practice set in the judging sandbox.

## Hard rules

- When the run ends, the verifier runs `bash /app/build.sh` (10 min limit)
  on the tree you left in `/app`. If the build fails or does not produce an
  executable `/app/solver`, the total score is 0. All top-level `/app/*.cpp`
  files are compiled together by the shipped script; keep extra sources in
  subdirectories if you add many files.
- Your solver gets a **hard per-instance wall-clock budget of 2 seconds**.
  Each judged instance is judged in a separate run; on every run the
  budget is handed to your solver in the environment variable
  `AHC_INSTANCE_SECONDS` (and in the legacy name `AHC_TIME_POOL`, set to
  the same value). The budget is enforced with an OS-level hard kill, so a
  runaway process cannot extend it.
- Your solver only ever sees one instance at a time.
- An invalid action sequence (a purchase you cannot afford at that turn,
  malformed lines, fewer than `T` actions) or a crash/nonzero exit/no
  output scores 0 **for that instance**; the others still count.
- The final score comes from a **fresh run** of your final build on the
  hidden instances, executed after your run ends.
- `submit.sh` uploads everything in `/app` **except** `./instances/`
  (static public assets the judge does not need).
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
