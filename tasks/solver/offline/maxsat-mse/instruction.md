# Task: Weighted MaxSAT

## Background

In **weighted MaxSAT** you are given a Boolean formula in conjunctive
normal form — an AND of OR-clauses over variables `x1..xn` — split into
**hard** clauses, which must all be satisfied, and **soft** clauses,
each carrying a positive integer weight. The cost of an assignment is
the sum of the weights of the soft clauses it falsifies; the task is to
find a hard-satisfying assignment of minimum cost. MaxSAT is NP-hard,
and it is the workhorse encoding for a long list of applied optimization
problems (planning, scheduling, verification, data analysis).

The benchmark behind this task is the anytime weighted track of a recent
competitive event, all of whose instances are "truly weighted" (soft
clause weights vary within every instance). Final judging uses **200
instances**, with variable relabeling applied to the source formulas. This
set excludes the 11 public practice instances shipped at `/app/instances/`,
including their relabeled versions. The final judging files are kept outside
this development environment, which has no network access.

## Your job

Build a solver in `/app`. The shipped baseline is **Open-WBO 2.1** (MIT
license, vendored in `/app/openwbo`), a classic SAT-based MaxSAT solver,
wrapped as an *anytime* solver: it searches until a wall-clock soft
limit, then prints the best answer it found and exits. It is a working
solver you can modify, wrap, reconfigure, or replace entirely — it also
serves as a living example of the I/O contract below.

You have a 12-hour run. When the run ends, the verifier rebuilds the
tree you left in `/app` exactly as described in Hard rules and judges
the resulting solver once on the hidden instances. That single judging
is your final score — nothing is judged while you work.

## Judging

| | |
|---|---|
| **Public practice set** | 11 instances at `/app/instances/` — **all excluded from final judging**. `/app/public_reference.json` gives two reference values per instance: `B` (the shipped baseline's result) and `K` (a best-known value from stronger reference solvers). |
| **Judging sandbox** | Per instance: **1 core**, 300 s wall clock. Each isolated Docker worker reserves 32 GB RAM. Up to 10 workers run concurrently, reduced automatically to fit available host resources. |
| **Local self-test** | Use the public-instance runner described below. It executes in this development environment; local timing can differ from the judging environment. Self-tests never affect your final score. |
| **Final judging** | Once, after the run ends: the verifier rebuilds `/app` and judges your solver on **200 hidden instances**, disjoint from the public practice set, using isolated Docker workers with the per-instance limits above. |
| **Score** | Determined solely by that one final judging. Hidden per-instance results are never returned to you; the formula that aggregates judging results into the final score is not disclosed. |

The final verifier runs on the evaluation host through Docker.
Development has no judging-service access. The public-instance
runner below supplies local feedback. Hidden instances are used
only once, after the development run ends.

## Input / output format (fixed — do not change the interface)

Your program reads an instance from **stdin** in the classic WCNF
format:

- lines starting with `c` are comments;
- one header line `p wcnf n m top` declares `n` variables (numbered
  1..n), `m` clauses, and the hard threshold `top`. Treat `m` as
  advisory;
- each remaining line `w l1 l2 ... 0` is one clause: an integer weight
  `w`, then the literals (1-based; negative means negation), terminated
  by `0`. A clause with `w >= top` is **hard**; any other clause is
  **soft** with weight `w`.

Your program writes the answer to **stdout**, following the `s`/`o`/`v`
line structure documented in the Open-WBO README, with a bitstring
v-line:

- lines starting with `c` are comments and ignored;
- one status line: `s OPTIMUM FOUND`, `s SATISFIABLE`, or `s UNKNOWN`;
- at least one cost line `o <cost>` (a nonnegative integer) — print one
  each time you find a better assignment;
- assignment lines `v <bits>` where `<bits>` is a string of exactly `n`
  characters from `{0,1}`; the i-th character is the value of variable
  `i` (the bitstring v-line format — note this differs from the
  signed-literal list shown in the Open-WBO README; the vendored
  baseline already prints the bitstring form). One line per answer you
  report; the last one counts.

When several `o`/`v` lines are printed, the **last** ones count. The
answer is valid iff the assignment satisfies every hard clause and its
recomputed cost equals the last declared `o` value. The judge recomputes
everything itself and trusts nothing your solver merely claims.

## What's in the environment

- `/app/openwbo/` — the baseline source (Open-WBO 2.1 with the task's
  anytime wrapper patches; see `/app/openwbo/TCSEXAM-PATCHES.md`).
  Rebuild with `bash /app/build.sh`, which produces `/app/solver`.
- `/app/solver` — the currently built solver. Run it as
  `./solver < instance.wcnf`. It reads one optional environment
  variable: `MAXSAT_SECONDS` (wall-clock soft limit, default 285).
- `/app/instances/` — the 11 public practice instances, all excluded from
  final judging.
- `/app/mse_table.md` — per-instance table for the shipped instances:
  size, family, the baseline's cost `B`, and the reference value `K`.
- `/app/solutions/` — verified optimal answers for 6 of the practice
  instances, in exactly the solver output format above.
- `/app/public_reference.json` — for each public instance: the baseline's
  cost `B` and the reference value `K`.
- `python3 /app/run_public.py` — rebuilds via `/app/build.sh`, runs the
  public instances locally with a per-instance wall-clock limit,
  validates the answers, recomputes costs, and prints per-instance
  results. It runs on this development box, outside the judging
  sandbox — allow for differences between development and judging resources.

## Hard rules

- When the run ends, the verifier runs `bash /app/build.sh` (10 min
  limit) on the tree you left in `/app`. If the build fails or does not
  produce an executable `/app/solver`, the total score is 0.
- Each instance is run separately with its own wall-clock limit (the
  process group is hard-killed at the limit). Your solver must print its
  answer and exit with code 0 before the limit. A killed run, a crash, a
  nonzero exit code, or no usable output at all scores 0 for that
  instance; the others still count.
- An invalid answer (a hard clause falsified, a malformed or truncated
  v-line, a declared cost that does not match the printed assignment, an
  `s UNSATISFIABLE` claim — the hard clauses of every judged instance
  are satisfiable) scores 0 **for that instance**.
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
