# Task: QBF solving

## Background

**QBF** (quantified Boolean formula) extends SAT with quantifiers: a
formula in prenex CNF like `∀x ∃y: (x ∨ y) ∧ (¬x ∨ ¬y)` is a two-player
game — the universal player picks `x`, the existential player answers
with `y`, and the formula is **true** if the existential player has a
winning strategy for every universal move. Deciding QBF is the canonical
PSPACE-complete problem.

The public practice instances and the hidden judged instances are drawn
from the same recent contest benchmark for this problem.

## Your job

Build a solver in `/app`. The shipped baseline is the source of **Qute**
(`/app/qute`), a QCDCL solver with partial expansion written in C++
(MIT license), driven by the wrapper `/app/build.sh` emits — a working
solver you can modify, wrap, reconfigure, or replace entirely — it also
serves as a living example of the I/O contract below.

You have a 12-hour run. When the run ends, the verifier rebuilds the
tree you left in `/app` exactly as described in Hard rules and judges
the resulting solver once on the hidden instances. That single judging
is your final score — nothing is judged while you work.

## Judging

| | |
|---|---|
| **Public practice set** | 13 instances at `/opt/qbf-public100`. `/app/public_reference.json` gives two reference values per instance: `B` (the shipped baseline's result) and `K` (a best-known value from stronger reference solvers). |
| **Judging sandbox** | **10 parallel shards**; per instance: **1 core**, 900 s wall clock (instances judged in parallel; shard containers with 4 cores/16 GB RAM are shared across them). This sandbox follows the task's official evaluation specification. |
| **Self-test** | `submit.sh` — unlimited use. The service judges your solver on the public practice set, **in the same judging sandbox, on the same 10 parallel shards, under the same per-instance limits** — and prints per-instance results and validity. Self-tests never affect your score. |
| **Final judging** | Once, after the run ends: the verifier rebuilds `/app` and judges your solver on **57 hidden instances**, again **in the same sandbox, on the same 10 parallel shards**. |
| **Certificate** | every answer must be backed by a certificate: Q-resolution proof (qrp2rup + drat-trim chain). An answer without a verified certificate scores 0 for that instance. |
| **Score** | Determined solely by that one final judging. Hidden per-instance results are never returned to you; the formula that aggregates judging results into the final score is not disclosed. |

`submit.sh` is on your `PATH` at `/usr/local/bin/submit.sh` — call it from any working directory.

A self-test and the final judging are the **same measurement** — same
sandbox, same 10 parallel shards, same per-instance limits; only the
instance set differs (public vs hidden). Local runs in this development
environment happen outside the judging sandbox, so local measurements
may not transfer — treat `submit.sh` results as authoritative.

## Input / output format (fixed — do not change the interface)

Your program reads a formula from **stdin** in QDIMACS format:

- lines starting with `c` are comments;
- the header line is `p cnf <nvars> <nclauses>`;
- then the quantifier prefix: lines `a <vars...> 0` (universal) and
  `e <vars...> 0` (existential), outermost block first;
- then the clauses: integers in `[-nvars, nvars]`, each clause
  terminated by `0`.

It writes the answer to **stdout**:

- a status line: `s TRUE` or `s FALSE` (any other status — `s UNKNOWN`,
  or silence — scores 0 for the instance);
- nothing else is needed on stdout, but the certificate must be written
  to the file whose path is in the environment variable
  **`QBF_PROOF_PATH`** (the judge sets it on every run). Accepted
  formats: **Qute's compact QRP-style trace** (what `qute --trace`
  emits on stdout — the stock `build.sh` shows the idiom: this Qute
  edition prints the proof on stdout and reports the verdict through
  its exit code, and the wrapper routes both) or **classic ASCII QRP**
  with an `r SAT` / `r UNSAT` trailer line (what `depqbf --trace`
  emits). When `QBF_PROOF_PATH` is unset (e.g. your own quick tests)
  proof production may be skipped.

Lines starting with `c` in your output are ignored.

**Certificates.** Every answer must be backed by a (long-distance)
Q-resolution proof. For a FALSE formula this is a refutation (a proof of
the empty clause); for a TRUE formula it is a cube proof from which the
existential player's winning strategy is extracted. The judge does not
trust your solver and never consults source labels. Instead it runs a
two-stage verification (both checkers are in this environment):

1. **qrp2rup** parses your proof, checks its resolution structure,
   extracts the winning strategy, and produces a CNF combining the
   strategy with the *actual matrix of the instance being judged*, plus
   a DRUP proof that this combined CNF is unsatisfiable.
2. **drat-trim** (the standard DRAT proof checker) verifies that DRUP
   proof — i.e. it recomputes from scratch that your strategy really
   wins on *this* instance.

A proof made for a different instance, a fabricated proof, or a blind
`s TRUE` / `s FALSE` guess cannot pass this chain. Certificate checking
gets its own budget beyond the per-instance limit, and oversized proofs
are rejected — the exact bounds are enforced by `/opt/qbf/verify_qbf.py`
(readable in the environment).

## What's in the environment

- `/app/qute/` — the baseline source (Qute). Builds with
  `bash /app/build.sh`, which produces the wrapper `/app/solver`.
- `/app/solver` — the currently built solver. Run it as
  `./solver < instance.qdimacs` (set `QBF_PROOF_PATH` if you want a
  certificate).
- `/opt/qbf-public100/` — the 13 public instances:
  `<name>.qdimacs.xz` per instance (decompress with `xz -dc`) plus
  `manifest.tsv`, one row per instance with the columns: `name`,
  `family` (the benchmark family), `vresult` (the established verdict
  label — `true` / `false`; `unknown` means no established answer), and
  `winner_solved` (whether the stronger reference solver solved it at
  the same budget, `1` / `0`, as recorded in the set's result table).
  These 13 are disjoint from the judged instances — the same
  distribution, but not the same instances.
- `qbf_verify` — the answer checker, on PATH:
  `qbf_verify instance.qdimacs solver_output.txt proof.qrp` prints
  `SUCCEED` or `FAILED: <reason>`. Source: `/opt/qbf/verify_qbf.py`.
- `/opt/qbf/qrp2rup` and `/opt/qbf/drat-trim` — the two checkers
  themselves, in case you want to run them by hand.
- `/app/public_reference.json` — for each public instance: whether the
  baseline solved it within the judging budget (`B`, 0/1) and whether
  the reference solver did (`K`, 0/1), plus its verdict label.
- `python3 /app/run_public.py` — rebuilds via `/app/build.sh`, runs the
  public instances locally with the same per-instance budget rule as the
  hidden judge, verifies certificates, and prints per-instance results.
  To iterate on a few instances, set `QBF_ONLY` to a comma-separated
  list of instance names, and set `PER_INSTANCE_SECONDS` smaller for
  quick iterations. It runs on this development box, outside the judging
  sandbox — use `submit.sh` for authoritative measurements.
- `submit.sh` — the self-test client: packs your solver tree, submits
  it to the judging service, and prints per-instance results judged on
  the public practice set in the judging sandbox.

## Hard rules

- When the run ends, the verifier runs `bash /app/build.sh` (10 min
  limit) on the tree you left in `/app`. If the build fails or does not
  produce an executable `/app/solver`, the total score is 0.
- Each instance is judged in a separate run with its own wall-clock
  budget, handed to your solver in the environment variable
  `QBF_INSTANCE_SECONDS`; there is **no shared pool** — your solver sees
  one instance at a time and may spend the whole budget on it. The
  budget is enforced with an OS-level hard kill. When the budget runs
  out, the instance scores 0. A crash, a missing status line, or a
  certificate that fails the verification chain scores 0 **for that
  instance**; the others still count.
- The final score comes from a **fresh run** of your final build on the
  hidden instances, executed after your run ends.
- `submit.sh` uploads your whole `/app` tree (the judge has its own
  copies of the public assets and does not need yours). The pack strips
  VCS metadata, tool caches, build byproducts and logs at any depth, and
  packs over 200 MB are refused (if the filter ever removes a file your
  solver genuinely needs, re-run with `TCSEXAM_SUBMIT_PRUNE=0`). If
  your solver needs runtime data files, keep them somewhere in `/app`.
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
