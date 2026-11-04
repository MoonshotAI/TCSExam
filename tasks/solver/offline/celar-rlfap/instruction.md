# Task: Radio link frequency assignment

## Background

In the **radio link frequency assignment problem**, a set of radio links
must each be assigned one transmit frequency. Every link has its own allowed
set of discrete frequencies, and interference between links is modelled by
two kinds of binary constraints on the assigned frequencies `f[x]`, `f[y]`:

- **hard equality constraints** `|f[x] − f[y]| = k` — must hold exactly
  (they typically pair a link with a frequency-shifted duplicate);
- **soft separation constraints** `|f[x] − f[y]| > k` — each violated one
  costs `costs[w]`, where `w` is the constraint's weight class; the
  objective is the total weighted violation, smaller is better.

This weighted partial constraint satisfaction problem is NP-hard.

A solution is fully described by one integer array (exactly the formulation
of the shipped model): `f[j]` = frequency of link `j`, which must lie in the
allowed set of link `j`. The judge recomputes the objective itself; nothing
you print besides the `f` array is trusted.

The public practice instances and the hidden judged instances are drawn
from the same public instance library for this problem. The hidden set is
constructed so that verbatim replay of published artifacts does not score
on it.

## Your job

Build a solver in `/app`. The shipped baseline, `/app/solve.sh`, is a
working solver you can modify, wrap, reconfigure, or replace entirely — it
also serves as a living example of the I/O contract below. It prints a
feasible assignment from a deterministic min-conflicts constructor (pure
Python, seconds), then runs a reference model through **OR-Tools CP-SAT**
pinned to a *single search worker*, a fixed random seed, and a small
**deterministic-time budget** (a machine-independent operation count), and
keeps the better of the two.

You have a 12-hour run. When the run ends, the verifier rebuilds the tree
you left in `/app` exactly as described in Hard rules and judges the
resulting solver once on the hidden instances. That single judging is your
final score — nothing is judged while you work.

## Judging

| | |
|---|---|
| **Public practice set** | 13 instances at `/app/instances/`. `/app/public_reference.json` gives two reference values per instance: `B` (the shipped baseline's result) and `K` (a best-known value from stronger reference solvers). |
| **Judging sandbox** | Per instance: **1 core**, 1200 s wall clock. Each isolated Docker worker reserves 16 GB RAM. Up to 10 workers run concurrently, reduced automatically to fit available host resources. |
| **Local self-test** | Use the public-instance runner described below. It executes in this development environment; local timing can differ from the judging environment. Self-tests never affect your final score. |
| **Final judging** | Once, after the run ends: the verifier rebuilds `/app` and judges your solver on **8 hidden instances**, again **in the same sandbox, on the same 10 parallel shards**. |
| **Score** | Determined solely by that one final judging. Hidden per-instance results are never returned to you; the formula that aggregates judging results into the final score is not disclosed. |

The final verifier runs on the evaluation host through Docker.
Development has no judging-service access. The public-instance
runner below supplies local feedback. Hidden instances are used
only once, after the development run ends.

## Input / output format (fixed — do not change the interface)

Your solver is invoked as

```
/app/solver INSTANCE_PATH
```

with the path of a `.dzn` instance file as its only argument. The instance
file assigns `costs`, `categories` (the allowed frequency sets), `domains`
(the category index per link), `hardctrx/hardctry/hardctrk` (the equality
constraints) and `softctrx/softctry/softctrk/softctrw` (the weighted soft
constraints), exactly like the shipped public instances. Your solver writes
its answer to **stdout** as one or more solution blocks in the format the
shipped model's output statement produces:

```
f = [<n comma-separated integers>];
```

The judge only reads the `f = [...];` part — everything else (including any
self-declared `objective`) is ignored. The judge scores the **LAST
complete** `f` block on stdout. Validity = every `f[j]` lies in its allowed
set, every hard equality holds exactly; the judge then **recomputes the
objective itself** as the sum of `costs[w]` over soft constraints with
`|f[x] − f[y]| ≤ k`.

## What's in the environment

- `/app/celar.mzn` — the reference model.
- `/app/solve.sh`, `/app/solve.py`, `/app/construct.py` — the baseline
  pipeline. Rebuild with `bash /app/build.sh`, which produces
  `/app/solver`. The baseline parses and validates instances through
  `/opt/celar/public_runner.py` (readable).
- `minizinc` (2.10.0) with solvers **CP-SAT** (`--solver cp-sat`),
  **Chuffed** (`--solver chuffed`), **Gecode**, **CBC**, **HiGHS**; plus
  `python3` and `g++`.
- `/app/instances/` — the 13 public practice instances.
- `/app/instances_table.md` — per-instance table for the public practice
  instances: size, the baseline's objective, and the best known value.
- `/app/public_reference.json` — per public instance: the baseline's
  objective `B` and the reference best-known value `K`.
- `python3 /app/run_public.py` — rebuilds `/app`, runs your solver on the
  public practice set locally under the same 1200 s per-instance limit,
  validates with the checker, and prints per-instance results. It runs on
  this development box, outside the judging sandbox — allow for differences between development and judging resources.

## Hard rules

- When the run ends, the verifier runs `bash /app/build.sh` (10 min limit)
  on the tree you left in `/app`. If the build fails or does not produce an
  executable `/app/solver`, the total score is 0.
- Each judged instance is judged with a **hard per-instance wall-clock
  limit of 1200 seconds** (the limit is handed to your solver in the
  environment variable `CELAR_TIME_LIMIT`, in seconds). The limit is
  enforced with an OS-level hard kill; a killed solver keeps whatever
  complete solution blocks it already printed — the last one counts.
- Your solver only ever sees one instance at a time.
- An invalid solution (wrong array length, a value outside the allowed
  set, a violated hard equality, a missing or truncated final block)
  scores 0 **for that instance**; the others still count. A nonzero exit
  code with no usable output is handled the same way.
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
