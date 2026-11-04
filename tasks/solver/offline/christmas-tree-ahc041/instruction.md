# Task: Christmas tree cutting

## Background

You are given a planar graph: `N = 1000` vertices, placed uniformly at
random inside a circle, connected by the **Delaunay triangulation** of
those points (`1000 <= M <= 3000` edges). Every vertex `v` has a positive
integer weight `A[v]` (between 1 and 100). The height limit is `H = 10`.

You must split the vertices into **rooted trees**: for every vertex you
either declare it a **root**, or choose one **parent**, such that

- the parent edge `(v, parent[v])` exists in the given graph,
- following parent pointers never loops (every chain ends at a root), so
  each vertex gets a well-defined **depth** `h[v]` (roots have `h = 0`),
- every depth is at most `H`: `h[v] <= 10`.

Each vertex may appear in exactly one tree, which the parent-pointer
structure guarantees automatically. Your raw score for an instance is

```
raw = 1 + sum_v (h[v] + 1) * A[v]
```

— larger is better. The judge recomputes the score itself; nothing you
print besides the parent array is trusted.

The public practice instances and the hidden judged instances are drawn
from the same generator for this problem. The hidden set is constructed so
that verbatim replay of published artifacts does not score on it.

## Your job

Build a solver in `/app`. The shipped baseline, `/app/solver.cpp`, is a
working solver you can modify, wrap, reconfigure, or replace entirely —
it also serves as a living example of the I/O contract below: it declares
**every vertex a root** (legal, deterministic, and intentionally weak —
score `1 + sum(A)`).

You have a 12-hour run. When the run ends, the verifier rebuilds the tree
you left in `/app` exactly as described in Hard rules and judges the
resulting solver once on the hidden instances. That single judging is your
final score — nothing is judged while you work.

## Judging

| | |
|---|---|
| **Public practice set** | 105 instances at `/app/instances/`. `/app/public_reference.json` gives two reference values per instance: `B` (the shipped baseline's result) and `K` (a best-known value from stronger reference solvers). |
| **Judging sandbox** | Per instance: **1 core**, 2 s wall clock. Each isolated Docker worker reserves 8 GB RAM. Up to 10 workers run concurrently, reduced automatically to fit available host resources. |
| **Local self-test** | Use the public-instance runner described below. It executes in this development environment; local timing can differ from the judging environment. Self-tests never affect your final score. |
| **Final judging** | Once, after the run ends: the verifier rebuilds `/app` and judges your solver on **45 hidden instances**, again **in the same sandbox, on the same 10 parallel shards**. |
| **Score** | Determined solely by that one final judging. Hidden per-instance results are never returned to you; the formula that aggregates judging results into the final score is not disclosed. |

The final verifier runs on the evaluation host through Docker.
Development has no judging-service access. The public-instance
runner below supplies local feedback. Hidden instances are used
only once, after the development run ends.

## Input / output format (fixed — do not change the interface)

Your program reads an instance from **stdin**:

- line 1: `N M H` (always `1000, 1000..3000, 10` in this task, but read
  them);
- line 2: `N` integers `A[0..N-1]`;
- next `M` lines: one edge `u v` each;
- last `N` lines: the point coordinates `x y` of each vertex (part of the
  instance format; the scorer ignores them).

Your program writes **parent ids** to **stdout**: `N` integers in one
block, where the `v`-th value is `-1` (v is a root) or the parent vertex
of `v` (`0 <= parent < N`). The judge accepts **several consecutive
blocks** and uses the **last** one, so you may print improving candidates
as you search. Nothing else on stdout. The judge re-validates everything
from scratch — it does not trust anything your program claims.

## What's in the environment

- `/app/solver.cpp` — the baseline solver. Rebuild with
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
  validates and re-simulates your parent arrays, and prints per-instance
  results. It runs on this development box, outside the judging sandbox —
  allow for differences between development and judging resources.

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
- An invalid parent array (a parent edge missing from the graph, a
  directed cycle, a depth above `H`, a truncated final block) or a
  crash/nonzero exit/no output scores 0 **for that instance**; the others
  still count.
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
