# Task: The largest binary code A(22,10) — Open Construction

A Lean 4 project lives in `/app`. `Task/Basic.lean` contains a
definition layer and two claim slots (`submission_lower` and
`submission_upper`) — prove the strongest claim you can. The verifier
independently evaluates your best proven claim against the published
literature frontier when the budget ends; stronger is better, with no
upper limit.

A **binary error-correcting code** of length 22 and minimum Hamming
distance 10 is a set `S` of 22-bit words such that **every two distinct
codewords differ in at least 10 positions**. The largest possible size,
denoted `A(22,10)`, is unknown; the accepted interval is

```
64 ≤ A(22,10) ≤ 84
```

- the **lower bound 64** (a 64-word code exists) is due to P. R. J.
  Östergård, *Two new four-error-correcting binary codes* (Designs, Codes
  and Cryptography 36(3):327–329, 2005), found by a maximum-clique search. It has
  stood for two decades;
- the **upper bound 84** (no 85-word code exists) is due to D. C.
  Gijswijt, H. D. Mittelmann and A. Schrijver, *Semidefinite code bounds
  based on quadruple distances* (IEEE Transactions on Information Theory
  58(5):2697–2705, 2012), a semidefinite-programming strengthening of the
  Delsarte linear-programming bound;
- the bounds are tracked by A. E. Brouwer's
  [*Table of A(n,d)*](https://www.win.tue.nl/~aeb/codes/binary-1.html)
  (the table gives `64 ≤ A(22,10) ≤ 84` — the most
  recent improvement recorded anywhere in the table dates from 2019).

This is an **open proof task** with two independent directions:

- **construction (lower bound)**: any verified code with at least 65
  codewords is a literature-level new result;
- **upper bound**: any verified proof that every such code has at most 83
  codewords is a literature-level new result. Note there is currently
  **no mass-production route** for this direction — the published bound
  comes from a semidefinite-programming computation, not from a
  verifiable certificate scheme, so expect this direction to be
  research-level hard.

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).** Words are functions
  `Fin 22 → Fin 2`, a code is presented as a **list** of words, and

  ```lean
  def isMinDist10Code (S : List (Fin 22 → Fin 2)) : Bool :=
    decide (0 < S.length) &&
      S.zipIdx.all fun (x, i) =>
        S.zipIdx.all fun (y, j) =>
          i == j || decide (hammingDist x y ≥ 10)

  def MinDist10Code (S : List (Fin 22 → Fin 2)) : Prop := isMinDist10Code S = true
  ```

  checks computably that `S` is nonempty and that the words at every two
  **distinct positions** differ in at least 10 coordinates (`hammingDist`
  is mathlib's, counting the coordinates on which two words differ);
  `MinDist10Code S` packages the check as a proposition. Duplicate words
  are rejected automatically: two positions carrying the same word are at
  distance `0 < 10`.
- **Claim slot.** Below the `-- END OF FIXED PART` line the file already
  states two claims, each with a placeholder numeral and a `sorry` body
  between `-- CLAIM ... BEGIN/END` markers:

  ```lean
  theorem submission_lower :
      ∃ S : List (Fin 22 → Fin 2), MinDist10Code S ∧ 2 ≤ S.length := ...

  theorem submission_upper :
      ∀ S : List (Fin 22 → Fin 2), MinDist10Code S → S.length ≤ 460 := ...
  ```

  **Prove at least one of the two claims**, after replacing its numeral
  with the best literal you can certify:

  - `submission_lower` certifies `A(22,10) ≥ k` — the larger your `k`,
    the better;
  - `submission_upper` certifies `A(22,10) ≤ m` — the smaller your `m`,
    the better.

  No instance, no witness, no lemma ladder, and no solution are provided:
  finding the construction (or the nonexistence argument) and driving it
  through the Lean kernel is the task. You may add any auxiliary
  definitions and lemmas below the fixed line. A claim left with `sorry`
  simply does not count; your best proven claim across the two directions
  is what gets evaluated.

## Rules

- Do not change any **code** above the line `-- END OF FIXED PART` (the
  import, the options, and the `isMinDist10Code` / `MinDist10Code`
  definitions are frozen); the verifier compares it (comments stripped,
  whitespace-normalized) against the reference. Comments and docstrings
  up there are free to edit — they do not affect judging.
- In each claim statement you may change **only the numeral**; every other
  token must remain exactly as written (up to whitespace), each claim must
  stay at the top level of the file (not inside a `namespace`), and each
  claim body must stay between its `-- CLAIM ... BEGIN/END` markers.
- No `sorry` / `admit` outside the claim bodies, no `axiom`/`sorryAx`
  declarations, and no redefinition tricks: the tokens `notation`,
  `macro`, `syntax`, `elab`, `opaque`, `unsafe`, `extern`,
  `implemented_by`, `initialize` and the option `skipKernelTC` are
  forbidden everywhere in the file. The verifier scans for this lexically
  (comments stripped) and then checks `#print axioms`: only `propext`,
  `Classical.choice`, `Quot.sound`, `Lean.ofReduceBool` and
  `Lean.trustCompiler` (i.e. `native_decide`, which **is** allowed) may
  appear. The judge automatically lets `native_decide`'s generated
  internal axioms (`._native.native_decide.ax_*`) through;
  `native_decide` can be used directly.

## How to work

You have a 12-hour budget and are expected to use it. Matching the
published record (a 64-word code, or an 84-word upper bound) is the beginning of the work, not the end
of it — do not submit early with only a tied record. Stronger is
better, with no upper limit.

Work in this order:
1. **Anchor check.** Verify the frontier values in the Background
   against the linked sources — if an anchor looks stale or wrong, say
   so in your final summary rather than trusting it blindly.
2. **Bank a claim early, then keep improving.** Get one certified
   claim on the board (a sanity cell exercises the pipeline; a fetched
   published construction ties the record), then keep pushing:
   improve your construction, try a different method, or attack a
   harder cell. Every strictly stronger certified bound counts for
   more. Keep going as long as you can generate distinct ideas —
   do not stop at a fixed count.
3. **Use the internet.** Look up the literature (constructions,
   records, techniques) rather than trusting training memory. Certifying
   a published record ties it; going beyond it takes a strictly
   stronger object the literature does not have.

The floor rules never change: a scored claim must not contain `sorry`,
planted axioms or redefinition tricks are rejected. Never fabricate a
proof.

## Scoring

The verifier (1) scans lexically, (2) checks the frozen definition layer
is untouched, (3) parses each proven claim to extract its numeral,
(4) compiles the file together with a consistency check that re-states
each proven claim from the fixed definitions, and (5) verifies the axiom
whitelist. It then independently evaluates your best proven claim against
the published literature frontier (a 64-word code, Östergård 2005; the
upper bound 84, Gijswijt–Mittelmann–Schrijver 2012). **A strictly
stronger certified bound is always better, and there is no upper limit**
— the published frontier is the bar to beat: a construction with
`k ≥ 65` words, or a verified upper bound `m ≤ 83`, is a literature-level
new result. A construction claim above 84 contradicts the published upper
bound; an upper-bound claim below 64 contradicts the published
construction.

## Environment

The project builds offline against the mathlib checkout at
`/opt/lean-lib/mathlib4`; use `lake build Task` in `/app` to check.
Agent budget: 12 hours. The container has internet access. A helper `/app/snapshot.sh` mirrors your `/app/Task` workspace into `/logs/artifacts/` every 5 minutes once started — launch it early with `nohup /app/snapshot.sh >/dev/null 2>&1 &` so your work is preserved whatever happens later.

## Notes

- `native_decide` is allowed and is the realistic way to verify a concrete
  code: the distance check is a finite computation (your code squared,
  times 22 coordinates), and the sanity oracle (`solution/`, the 48-word
  punctured Paley–Hadamard code) proves `MinDist10Code` and the
  length bound this way. Kernel-side `decide` at this scale is too
  slow.
- A verified `k = 64` means you formalized Östergård's record construction
  (or found your own); the codeword table is not in the container —
  fetch it from the literature or build your own (either ties the record;
  the goal is beyond). Known good constructions are
  highly structured: Hadamard codes (as in the oracle), shortened or
  punctured classical codes, constant-weight codes glued together, and
  unions of cosets of linear codes.
- For the upper-bound direction there is no analogous finite certificate:
  `∀ S, MinDist10Code S → S.length ≤ m` quantifies over all word lists,
  and a valid list has pairwise distinct words, so this is a bound on
  every subset of the cube. The published route is the
  quadruple-distance semidefinite program of
  Gijswijt–Mittelmann–Schrijver; formalizing even `m = 459` in the kernel
  is a real formalization effort — treat any progress on this side as
  research-level work.
- The final verification is fast: a `native_decide` distance check of a
  code of a few dozen words compiles and evaluates in seconds.
