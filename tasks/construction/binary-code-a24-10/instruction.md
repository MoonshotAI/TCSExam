# Task: The largest binary code A(24,10) — Open Construction

A Lean 4 project lives in `/app`. `Task/Basic.lean` contains a
definition layer and two claim slots (`submission_construction` and
`submission_upper`) — prove the strongest claim you can. The verifier
independently evaluates your best proven claim against the published
literature frontier when the budget ends; stronger is better, with no
upper limit.

A **binary error-correcting code** of length 24 and minimum Hamming
distance 10 is a set `S` of 24-bit words such that **every two distinct
codewords differ in at least 10 positions**. The largest possible size,
denoted `A(24,10)`, is unknown; the accepted interval is

```
136 ≤ A(24,10) ≤ 268
```

- the **lower bound 136** (a 136-word code exists) is due to
  A. Laaksonen and P. R. J. Östergård, *Constructing error-correcting
  binary codes using transitive permutation groups*
  ([arXiv:1604.06022](https://arxiv.org/abs/1604.06022), 2016) — a search
  over codes invariant under transitive permutation groups; the preprint
  attaches the explicit codes;
- the **upper bound 268** (no 269-word code exists) is due to
  D. C. Gijswijt, H. D. Mittelmann and A. Schrijver, *Semidefinite code
  bounds based on quadruple distances*, IEEE Trans. Inf. Theory
  58(5):2697–2705, 2012 — semidefinite programming strengthening the
  Delsarte linear-programming bound;
- the bounds are tracked by A. E. Brouwer's
  [*Table of A(n,d)*](https://www.win.tue.nl/~aeb/codes/binary-1.html)
  (the table gives `136 ≤ A(24,10) ≤ 268` — the most
  recent improvement recorded anywhere in the table dates from 2019).

This is an **open task in both directions**: a verified code with at
least 137 codewords, or a verified proof that every such code has at most
267, is a literature-level new result.

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).** Words are functions
  `Fin 24 → Fin 2`, and

  ```lean
  def MinDist10 (S : Finset (Fin 24 → Fin 2)) : Prop :=
    ∀ x ∈ S, ∀ y ∈ S, x ≠ y → 10 ≤ hammingDist x y
  ```

  says the code `S` has minimum distance at least 10 (`hammingDist` is
  mathlib's, counting the coordinates on which two words differ).
- **Claim slot.** Below the line `-- END OF FIXED PART` the file ships
  **two claim theorems**. Prove at least one of them, for a numeral of
  your choice:

  ```lean
  theorem submission_construction :
      ∃ S : Finset (Fin 24 → Fin 2), MinDist10 S ∧ m ≤ S.card := ...
    -- a construction: A(24,10) ≥ m (the larger m, the better)

  theorem submission_upper :
      ∀ S : Finset (Fin 24 → Fin 2), MinDist10 S → S.card ≤ k := ...
    -- an upper bound: A(24,10) ≤ k (the smaller k, the better)
  ```

  No instance, no witness, no lemma ladder, and no solution are provided:
  finding the construction (or the upper-bound argument) and driving it
  through the Lean kernel is the task. You may add any auxiliary
  definitions and lemmas between the fixed part and the claims, or after
  them.

## Rules

- For verifier safety, executable commands `#eval`, `#exec`, `#exit`, and
  `#compile` are not allowed in submitted Lean files, including harmless
  diagnostics. Remove these commands before submission; the verifier rejects
  them before compiling the proof.
  `native_decide` remains allowed as described in this task.
- Do not change any **code** above the line `-- END OF FIXED PART` (the
  import and the `MinDist10` definition are frozen); the verifier
  compares it (comments stripped, whitespace-normalized) against the
  reference. Comments and docstrings up there are free to edit — they do
  not affect judging.
- In each claim statement you may change **only the numeral** (`m`,
  respectively `k`; both between 1 and 16777216); every other token must
  remain exactly as written, the claims must stay at the top level of
  the file (not inside a `namespace`), and each claim body must stay
  between its `-- CLAIM ... BEGIN/END` markers.
- No `sorry` / `admit` outside the claim bodies — a claim whose body
  still contains one is simply not scored, and one anywhere else
  invalidates the whole submission. No `axiom` / `sorryAx` declarations,
  and no redefinition tricks:
  the tokens `notation`, `macro`, `syntax`, `elab`, `opaque`, `unsafe`,
  `extern`, `implemented_by`, `initialize` and the option `skipKernelTC`
  are forbidden everywhere in the file. The verifier scans for this
  lexically (comments stripped).
- The whole file must compile, and every scored claim is re-stated by
  the verifier from the frozen `MinDist10` definition and proved from
  your theorem (a consistency check); `#print axioms` of that check may
  only list `propext`, `Classical.choice`, `Quot.sound`,
  `Lean.ofReduceBool` (i.e. `native_decide`, which **is** allowed) and
  `Lean.trustCompiler`. The judge automatically lets `native_decide`'s
  generated internal axioms (`._native.native_decide.ax_*`) through;
  `native_decide` can be used directly.

## How to work

You have a 12-hour budget and are expected to use it. Matching the
published record (a 136-word code, or a 268-word upper bound) is the beginning of the work, not the end
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

The verifier parses the numeral from each proven claim, re-states it from
the frozen `MinDist10` definition (a consistency check), and verifies the
axiom whitelist. It then independently evaluates your best proven claim
against the published literature frontier (a 136-word code,
Laaksonen–Östergård 2016; the upper bound 268,
Gijswijt–Mittelmann–Schrijver 2012). **A strictly stronger
certified bound is always better, and there is no upper limit** — the
published frontier is the bar to beat: a construction with `m ≥ 137`
words, or a verified upper bound `k ≤ 267`, is a literature-level new
result. Note that the 2016 preprint attaches the explicit 136-word code,
so tying the record can be achieved by extraction from the paper —
beating it is where the frontier lies. A construction claim above 268
contradicts the published upper bound; an upper-bound claim below 136
contradicts the published construction.

## Environment

The project builds offline against the mathlib checkout at
`/opt/lean-lib/mathlib4`; use `lake build Task` in `/app` to check.
Agent budget: 12 hours. The container has internet access. A helper `/app/snapshot.sh` mirrors your `/app/Task` workspace into `/logs/artifacts/` every 5 minutes once started — launch it early with `nohup /app/snapshot.sh >/dev/null 2>&1 &` so your work is preserved whatever happens later.

## Notes

- `native_decide` is allowed and is the realistic way to verify a
  concrete code: the distance check is a finite computation (your code,
  all pairs), and the sanity oracle (`solution/`, the 136-word record
  code) proves `MinDist10` and the cardinality this way.
  Kernel-side `decide` at this scale is too slow.
- One engineering pitfall: a direct `by native_decide` on the claim's
  `∀ x ∈ S, ∀ y ∈ S, …` shape makes `Decidable` instance synthesis
  reach for the whole-type `Fintype` enumerator of `Fin 24 → Fin 2`
  (16,777,216 functions) and does not finish within budget. Evaluate a
  Boolean pair check over a concrete codeword **list** instead
  (`List.all` over your words — 136 × 136 concrete distance checks run
  in seconds) and glue it back to the finset claim; the sanity oracle
  demonstrates exactly this pattern.
- A verified `m = 136` means you formalized the Laaksonen–Östergård
  record construction (or found your own); the codeword table is not in
  the container — fetch it (the preprint is public) or build your own
  (either ties the record; the goal is beyond). The solver sibling task `binary-code-a24-10`
  documents the classical constructions (Paley–Hadamard codes, group-
  invariant codes, local search) if you need a starting point.
- The upper-bound direction currently has **no mass-production route**:
  the published 268 is a semidefinite-programming computation
  (Gijswijt–Mittelmann–Schrijver 2012), not a verifiable certificate
  scheme, so expect this direction to be research-level hard. Even the
  sphere-packing bound `k = 1295` needs a real counting proof in Lean (the radius-4
  Hamming balls around the codewords are disjoint, each of size
  `1 + 24 + 276 + 2024 + 10626 = 12951`, inside a cube of `2^24` words).
  Treat this direction as a research problem in its own right.
- The final verification is fast: a `native_decide` distance check of a
  few hundred codewords compiles and evaluates in seconds.
