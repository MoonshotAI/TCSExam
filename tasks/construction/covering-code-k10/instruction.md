# Task: The smallest binary covering code K(10,1) — Open Construction

A Lean 4 project lives in `/app`. `Task/Basic.lean` contains a
definition layer and a claim slot (`covering_code_k10_main`) — prove the
strongest claim you can. The verifier independently evaluates your best
proven claim against the published literature frontier when the budget
ends; stronger is better, with no upper limit — smaller is better here
(you certify a covering on at most `k` words).

A **binary covering code** of length 10 and radius 1 is a set `S` of
10-bit words such that **every** 10-bit word is within Hamming distance 1
of some codeword — each word of the cube either is a codeword or differs
from one in exactly one bit. Equivalently, `S` is a *dominating set* of
the 10-dimensional hypercube graph `Q_10`. The smallest possible size
`K(10,1)` is unknown; the accepted interval is

```
107 ≤ K(10,1) ≤ 120
```

- the **upper bound 120** is a construction due to Patric Östergård
  (*A new binary code of length 10 and covering radius 1*, IEEE Trans.
  Inf. Theory 37(1):179–180, 1991), found by simulated annealing; Kéri's
  tables also attribute it to L. T. Wille's simulated annealing work
  (1990; IEEE Trans. Inf. Theory 42:300–302, 1996). It has stood for
  35 years;
- the **lower bound 107** (no 106-word covering exists) is due to
  Bertolo–Östergård–Weakley (*An updated table of binary/ternary mixed
  covering codes*, J. Combin. Designs 12:157–176, 2004);
- the bounds are tracked by Gerzson Kéri's
  [*Tables for bounds on covering codes*](https://old.sztaki.hu/~keri/codes/index.htm)
  (last updated 2011); recent work — Gijswijt–Polak's semidefinite lower
  bounds ([arXiv:2504.01932](https://arxiv.org/abs/2504.01932)) and
  DeVivo–Hladký's high-dimensional upper bounds
  ([arXiv:2409.14621](https://arxiv.org/abs/2409.14621)) — has not moved
  the `n = 10` endpoints ().

This is an **open construction task**: any verified covering with at most
119 codewords is a literature-level new result.

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).** Words are functions
  `Fin 10 → Fin 2`, and

  ```lean
  def Covers (S : Finset (Fin 10 → Fin 2)) : Prop :=
    ∀ w : Fin 10 → Fin 2, ∃ c ∈ S, hammingDist w c ≤ 1
  ```

  says that the radius-1 Hamming balls around the codewords of `S` cover the
  whole cube (`hammingDist` is mathlib's, counting the coordinates on which
  two words differ).
- **Claim slot.** **State and prove a theorem named
  `covering_code_k10_main`** below the `-- END OF FIXED PART` line, in
  exactly this shape, with a literal decimal numeral `k` of your choice
  (the smaller the better):

  ```lean
  theorem covering_code_k10_main : ∃ S : Finset (Fin 10 → Fin 2), Covers S ∧ S.card ≤ k := ...
  ```

  No instance, no witness, no lemma ladder, and no solution are provided:
  finding the construction and driving it through the Lean kernel is the
  task. You may add any auxiliary definitions and lemmas below the fixed
  line.

## Rules

- Do not change any **code** above the line `-- END OF FIXED PART` (the
  import and the `Covers` definition are frozen); the verifier compares
  it (comments stripped, whitespace-normalized) against the reference.
  Comments and docstrings up there are free to edit — they do not affect
  judging.
- The statement of `covering_code_k10_main` must match the template above
  verbatim (up to whitespace), at the top level of the file (not inside a
  `namespace`), with a literal numeral `k`.
- No `sorry`, no `admit`, no `axiom`/`sorryAx` declarations, and no
  redefinition tricks: the tokens `notation`, `macro`, `syntax`, `elab`,
  `opaque`, `unsafe`, `extern`, `implemented_by`, `initialize` and the option
  `skipKernelTC` are forbidden everywhere in the file. The verifier scans
  for this lexically (comments stripped) and then checks
  `#print axioms`: only `propext`, `Classical.choice`, `Quot.sound` and
  `Lean.ofReduceBool` (i.e. `native_decide`, which **is** allowed) may
  appear. The judge automatically lets `native_decide`'s generated
  internal axioms (`._native.native_decide.ax_*`) through;
  `native_decide` can be used directly.

## How to work

You have a 12-hour budget and are expected to use it. Matching the
published record (a 120-word covering) is the beginning of the work, not the end
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
is untouched, (3) parses your `covering_code_k10_main` statement to
extract `k`, (4) compiles the file together with a consistency check that
re-states your claim from the fixed definitions, and (5) verifies the
axiom whitelist. It then independently evaluates your proven claim
against the published literature frontier (a covering on 120 words,
Östergård 1991). **A strictly stronger certified bound is always
better, and there is no upper limit** — the published record is the bar
to beat, and beating it (any `k ≤ 119`) is a literature-level new result.
A claim with `k < 107` contradicts the published lower bound
(Bertolo–Östergård–Weakley 2004).

## Environment

The project builds offline against the mathlib checkout at
`/opt/lean-lib/mathlib4`; use `lake build Task` in `/app` to check.
Agent budget: 12 hours. The container has internet access. A helper `/app/snapshot.sh` mirrors your `/app/Task` workspace into `/logs/artifacts/` every 5 minutes once started — launch it early with `nohup /app/snapshot.sh >/dev/null 2>&1 &` so your work is preserved whatever happens later.

## Notes

- `native_decide` is allowed and is the realistic way to verify a concrete
  code: the coverage check is a finite computation (1024 words × your
  code), and the sanity oracle (`solution/`, the 512-word even-weight
  code) proves `Covers` and the cardinality this way. Kernel-side
  `decide` at this scale is too slow.
- A verified `k = 120` means you formalized Östergård's record
  construction (or found your own); the codeword table is not in the
  container — fetch it from the literature or build your own (either ties
  the record; the goal is beyond).
- The final verification is fast: a `native_decide` coverage check of a few
  hundred codewords compiles and evaluates in seconds.
