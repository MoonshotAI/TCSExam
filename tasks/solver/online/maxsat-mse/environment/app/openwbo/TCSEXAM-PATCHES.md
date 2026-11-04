# TCSExam patches to Open-WBO 2.1

This tree is Open-WBO (sat-group/open-wbo, commit `80f3073`, release 2.1,
September 2018; MIT license — see `LICENSE`) with the following minimal
patches applied for the TCSExam `maxsat-mse` task. The search algorithms
themselves are untouched.

1. **`Main.cc` — wall-clock soft limit.** On startup the solver installs a
   `SIGALRM` handler via `alarm(MAXSAT_SECONDS)` (environment variable,
   default 285; `0` disables). When it fires, the handler prints the best
   answer found so far and exits with code 0. The existing `SIGTERM` handler
   now behaves identically (print best answer, exit 0).
2. **`Main.cc` — exit code.** A finished search returns exit code 0
   (upstream returns the status code, e.g. 30 for OPTIMUM). Nonzero is
   reserved for genuine failures (bad input, out of memory).
3. **`MaxSAT.cc` — `printAnswer()` prints a final `o` line.** Before the
   `s` line, the cost of the very model about to be printed is recomputed
   with `computeCostModel()` and printed as `o <cost>`, so the declared cost
   and the printed assignment are consistent by construction.
4. **`MaxSAT.cc` — `printModel()` emits the MSE 2022+ bitstring v-line**
   (`v 0110...`: the i-th character is the value of variable i) instead of
   the pre-2022 signed-literal list.
5. **`MaxSAT.cc` — signal-safe model handling.** `saveModel()` builds the
   trimmed model copy on the side and swaps it in, and `printAnswer()`
   treats a model whose size differs from the number of initial variables
   (possible only if the soft-limit signal interrupted `saveModel()`) as
   "no model", printing `s UNKNOWN` instead of a truncated assignment.
