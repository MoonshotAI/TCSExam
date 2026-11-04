# Task: SyGuS program synthesis

## Background

**Syntax-guided synthesis (SyGuS)** is the problem of automatically
writing a program: given a logical *specification* over unknown
functions ("the output must satisfy these constraints for all inputs")
and, optionally, a *grammar* restricting the shape of candidate
programs, find a function definition that satisfies the specification.
It is the standard formulation of program synthesis. Benchmarks in this
area span several families: conditional linear integer arithmetic
(CLIA), bit-vector programming-by-examples (PBE_BV), string
transformations from input/output examples (PBE_SLIA), invariant
synthesis (Inv), and a general family.

The public practice instances and the hidden judged instances are drawn
from the same public synthesis benchmark collection; their files are not
in this environment. No network access is provided. Benchmarks in the environment were mechanically converted from
the collection's original notation into the SyGuS-IF v2 dialect that
cvc5 1.3.x parses (the conversion is semantics-preserving).

## Your job

Build a solver in `/app`. The shipped baseline, `/app/naive_sygus.py`
(a naive enumerative synthesizer: bottom-up grammar enumeration, asking
the task's own machine check about each candidate until something
verifies), is a working solver you can modify, wrap, reconfigure, or
replace entirely — it also serves as a living example of the I/O
contract below. A full **cvc5 1.3.4** binary ships in the environment
as a tool.

You have a 12-hour run. When the run ends, the verifier rebuilds the
tree you left in `/app` exactly as described in Hard rules and judges
the resulting solver once on the hidden instances. That single judging
is your final score — nothing is judged while you work.

## Judging

| | |
|---|---|
| **Public practice set** | 100 instances at `/app/instances/`. `/app/public_reference.json` gives two reference values per instance: `B` (the shipped baseline's result) and `K` (a best-known value from stronger reference solvers). |
| **Judging sandbox** | Per instance: **1 core**, 3600 s wall clock. Each isolated Docker worker reserves 32 GB RAM. Up to 10 workers run concurrently, reduced automatically to fit available host resources. |
| **Local self-test** | Use the public-instance runner described below. It executes in this development environment; local timing can differ from the judging environment. Self-tests never affect your final score. |
| **Final judging** | Once, after the run ends: the verifier rebuilds `/app` and judges your solver on **60 hidden instances**, again **in the same sandbox, on the same 10 parallel shards**. |
| **Score** | Determined solely by that one final judging. Hidden per-instance results are never returned to you; the formula that aggregates judging results into the final score is not disclosed. |

The final verifier runs on the evaluation host through Docker.
Development has no judging-service access. The public-instance
runner below supplies local feedback. Hidden instances are used
only once, after the development run ends.

## Input / output format (fixed — do not change the interface)

Your program is invoked as **`/app/solver INSTANCE.sl`** (the benchmark
file path is the first argument) and must write its answer to **stdout**.
The benchmark is a SyGuS-IF v2 problem: `set-logic`, optional
`define-fun` macros, `synth-fun` (or `synth-inv` for invariant problems)
with an optional grammar, `declare-var`, `constraint` (or
`inv-constraint`), `check-synth`.

The answer is the synthesized function(s) in define-fun form, e.g.

```
(
(define-fun max2 ((x Int) (y Int)) Int (ite (<= y x) x y))
)
```

Accepted output forms: one parenthesized list of define-funs (cvc5's
style), a bare sequence of define-funs, or — for single-synth-fun
benchmarks — just the body term. Printing `fail` (or nothing, or
garbage) counts as not solved. Every synth-fun of the benchmark must be
defined with the right name, arity, and return sort; parameter *names*
may differ from the header (they are bound positionally).

**How solutions are checked (two-step machine check).** A printed
solution only counts if it passes **both** checks, run by the judge with
a pristine cvc5 that you cannot influence:

1. **Grammar check** — if the synth-fun has a grammar, the body must be
   derivable from the grammar's start non-terminal (after expanding any
   `let` bindings in your output). Benchmarks without a grammar skip
   this step.
2. **Semantic check** — your define-fun is substituted into the
   specification, the negation of the constraint conjunction is handed
   to cvc5 as an SMT query, and it must be **unsat** (i.e. no
   counterexample input exists). For `inv-constraint` benchmarks the
   three invariant implications (initiation, consecution, safety) are
   each checked this way. A `sat`, `unknown`, timeout, or verifier
   error means the instance is not solved.

Nothing your solver prints beyond the candidate definition is trusted.
The machine check runs on its own budget beside your solver's budget,
not inside it.

## What's in the environment

- `/app/naive_sygus.py` — the baseline source.
- `/app/cvc5` — the cvc5 1.3.4 binary (modified BSD license).
  `cvc5 --lang=sygus2 --tlimit=MS FILE` synthesizes with a millisecond
  time limit; `cvc5 --help` documents the synthesis options.
- `/app/build.sh` — produces `/app/solver`; the judge runs exactly this
  on every hidden instance. The baseline just copies the wrapper; if you
  add sources (C++, Rust, Python, whatever), edit `build.sh` to
  build/install them. `g++` is available; the build gets 10 minutes.
- `sygus_check` — the same machine checker the judge uses, on PATH:
  `sygus_check BENCHMARK.sl SOLUTION_FILE` prints VALID or the rejection
  reason. Source: `/opt/sygus/sygus_check.py`.
- `/app/instances/` — the 100 public practice instances (5 families).
  The judging instances are not among them.
- `/app/instances_table.md` — per-instance table for all 100 public
  instances: track, whether the baseline solves it within the judging
  budget (`B`), whether the reference run solves it (`K`), and the
  baseline's solve time.
- `/app/public_reference.json` — the machine-readable B/K reference for
  the 100 public instances.
- `python3 /app/run_public.py` — rebuilds via `/app/build.sh`, runs the
  public instances locally with the same per-instance budget
  rule as the hidden judge, machine-checks every solution, and prints
  per-instance results. Set `PER_INSTANCE_SECONDS` smaller for quick
  iterations. It runs on this development box, outside the judging
  sandbox — allow for differences between development and judging resources.

## Hard rules

- When the run ends, the verifier runs `bash /app/build.sh` (10 min
  limit) on the tree you left in `/app`. If the build fails or does not
  produce an executable `/app/solver`, the total score is 0.
- Each instance is judged in a separate run with its own wall-clock
  budget, handed to your solver in the environment variable
  `SYGUS_INSTANCE_SECONDS`; there is **no shared pool** — your solver
  sees one instance at a time and may spend the whole budget on it. The
  budget is enforced with an OS-level hard kill.
- A solution that fails the machine check scores 0 **for that
  instance**; the others still count. A crash, a nonzero exit code, or
  no output at all is handled the same way. There is no additional
  wrong-answer penalty — every claim is fully checked anyway.
- The judge's semantic check runs a pristine cvc5 whose integrity is
  verified against hashes pinned outside your reach; replacing or
  wrapping it is detected and scores 0.
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
