# Task: Logic synthesis

## Background

A completely specified Boolean function with `n` inputs and `m` outputs
is given as a **truth table**. Your job: synthesize a **combinational
circuit** that computes exactly this function, built from **two-input
AND gates and inverters** (an and-inverter graph, AIG), using **as few
AND gates as possible**. Inverters are free.

This is the engineering face of the minimum circuit size problem —
NP-hard, and the daily work of logic synthesis tools in chip design.

The 100 public functions and the 100 hidden judged functions come from
the same logic-synthesis contest benchmark series. The hidden set is
constructed so that verbatim replay of published contest artifacts does
not score on it. For every instance, `K` is the best published value
known for that function; you get the AND counts, not the circuits.

## Your job

Build a solver in `/app`. The shipped baseline is the **ABC logic
synthesis system** (source in `/app/abc`, prebuilt binary at
`/app/abc/abc`) driven by one fixed script in `/app/build.sh` (BDD
collapse, then `dc2` on the AIG) — a deterministic, working solver you
can modify, wrap, reconfigure, or replace entirely — it also serves as a
living example of the I/O contract below.

You have a 12-hour run. When the run ends, the verifier rebuilds the
tree you left in `/app` exactly as described in Hard rules and judges
the resulting solver once on the hidden instances. That single judging
is your final score — nothing is judged while you work.

## Judging

| | |
|---|---|
| **Public practice set** | 100 instances at `/app/instances/`. `/app/public_reference.json` gives two reference values per instance: `B` (the shipped baseline's result) and `K` (a best-known value from stronger reference solvers). |
| **Judging sandbox** | **One local Docker worker**; per instance: 4 cores, 8 GB RAM; one shared time pool of 4000 seconds covers all judged instances (40 s per instance x instance count) — no per-instance limit. This sandbox follows the task's official evaluation specification. |
| **Local self-test** | Use the public-instance runner described below. It executes in this development environment; local timing can differ from the judging environment. Self-tests never affect your final score. |
| **Final judging** | Once, after the run ends: the verifier rebuilds `/app` and judges your solver on **100 hidden instances**, again **in the same sandbox**. |
| **Score** | Determined solely by that one final judging. Hidden per-instance results are never returned to you; the formula that aggregates judging results into the final score is not disclosed. |

The final verifier runs on the evaluation host through Docker.
Development has no judging-service access. The public-instance
runner below supplies local feedback. Hidden instances are used
only once, after the development run ends.

## Input / output format (fixed — do not change the interface)

Your program is invoked as

```
solver TRUTH_FILE OUTPUT_AIGER
```

with the remaining time pool (in seconds) in the environment variable
`LS_TIME_POOL`.

**Truth table** (`TRUTH_FILE`, ASCII): one line per output; every line
has exactly `2^n` characters over `{0,1}`. The leftmost character is the
value at the all-ones input assignment; the rightmost is the value at
the all-zeros assignment — i.e. the character at position `p` from the
left is the value at minterm `2^n − 1 − p`, where minterm `t` has input
`x_i` as bit `i` of `t` (`x_0` = least significant bit). Example: a line
`1000` (with 2 inputs) means the output is 1 exactly at the all-ones
assignment `x_1 = x_0 = 1`. All lines have the same length; `n` and `m`
are implied by the file.

**Circuit** (`OUTPUT_AIGER`, **binary AIGER**): the standard
`aig M I L O A` format — header line, `O` output literals (ASCII, one
per line), then `A` AND gates in binary delta encoding. Hard
requirements:

- `L = 0` (combinational only — latches are rejected), no
  bad/constraint/justice/fairness sections;
- `I` must equal the instance's input count `n`, `O` must equal its
  output count `m`;
- literal `2v` / `2v+1` denotes variable `v` / its negation; inputs are
  variables `1..I`; constant 0 is literal 0 (constant 1 is literal 1);
- AND gates must be in topological order (fanin literals strictly
  smaller than the gate's own literal).

The cost `A` your circuit is measured on is the number of AND gates in
the header (the judge recounts them from the file itself).
`/app/aiglib.py` contains the exact parser (`parse_aiger`), writer
(`write_aiger`), and simulator the judge uses, and the baseline solver
emits valid files via ABC's `write_aiger`.

The judge re-validates everything: your circuit is simulated
exhaustively over all `2^n` input patterns and compared against the
reference truth table bit for bit. A functionally different circuit
scores 0 for that instance, whatever your solver claims.

## What's in the environment

- `/app/abc/` — the ABC synthesis system (Berkeley ABC, pinned commit,
  BSD style license), already compiled. Command line:
  `abc -c "command1; command2; ..."`. Classic script names like
  `resyn2`, `resyn2rs`, `compress2rs`, `choice` are **aliases defined in
  `/app/abc/abc.rc`, not built-in commands** — load them first when
  abc's working directory is not the source tree:
  `abc -c "source /app/abc/abc.rc; ..."`. ABC's own help
  (`abc -c "help"`) lists everything.
- `/app/build.sh` — the build script the judge runs. It compiles ABC
  (incrementally) and emits `/app/solver`. Edit freely.
- `/app/aiglib.py` — the judge's own AIGER parser / truth-table parser /
  exhaustive simulator / equivalence checker, shared with you so you can
  validate candidates exactly the way the judge does
  (`check_circuit(aig, n, masks)` returns `None` iff the circuit
  computes the reference function).
- `/app/instances/` — the 100 public practice instances (`ex*.truth`).
  The hidden truth tables are not among them.
- `/app/public_reference.json` — for the public set: the baseline's AND
  count `B` and the reference best-known AND count `K` per instance.
- `python3 /app/run_public.py` — rebuilds via `/app/build.sh`, runs the
  public set locally under one shared total time pool (the same budget
  rule the hidden judge uses — per-instance seconds × instance count,
  no per-instance limit), validates every produced circuit by exhaustive
  simulation, and prints per-instance results. It runs on this
  development box, outside the judging sandbox — allow for differences between development and judging resources.

## Hard rules

- When the run ends, the verifier runs `bash /app/build.sh` (10 min
  limit) on the tree you left in `/app`. If the build fails or does not
  produce an executable `/app/solver`, the total score is 0.
- Your solver gets **one total time pool** covering all judged
  instances (wall clock). There is **no per-instance limit** — you
  decide how to distribute the pool (on every run the remaining pool is
  handed to your solver in `LS_TIME_POOL`). When the pool runs out,
  every instance without a verified circuit scores 0. The budget is
  enforced with an OS-level hard kill.
- If your solver is killed mid-instance, whatever it already wrote to
  `OUTPUT_AIGER` is still checked — a valid equivalent circuit on disk
  counts.
- A crash, a nonzero exit code, a malformed AIGER file, or a
  **functionally different** circuit scores 0 **for that instance**; the
  others still count. Exhaustive simulation decides equivalence; the
  judge never trusts your solver's own claims.
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
