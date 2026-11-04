# Task: The dimension-7 cap set problem — Open Construction

A Lean 4 project lives in `/app`. `Task/Basic.lean` contains a
definition layer and a claim slot (`capset_d7_main`) — prove the
strongest claim you can. The verifier independently evaluates your best
proven claim against the published literature frontier when the budget
ends; stronger is better, with no upper limit.

A **cap set** (or **cap**) in the affine geometry `AG(n, 3)` is a set of
points of `(Z/3Z)^n` containing **no three distinct collinear points** —
equivalently, no three distinct points `x, y, z` with `x + y + z = 0`. This
is the "no SET" condition of the card game SET; tracking the maximum size
`a(n)` of a cap in dimension `n` is a central problem of additive
combinatorics (OEIS [A090245](https://oeis.org/A090245)).

The exact value of `a(n)` is known only for `n ≤ 6`
(`1, 2, 4, 9, 20, 45, 112`; the `n = 6` value is due to Potechin 2008, the
`n = 5` value to Edel–Ferret–Landjev–Storme 2002). **Dimension 7 is open.**
The published bounds are

```
236 ≤ a(7) ≤ 288
```

- the lower bound `236` is a construction usually attributed to Y. Edel
  (*Extensions of generalized product caps*, Des. Codes Cryptogr. 31, 2004)
  and has stood for about twenty years;
- the upper bound `288` is due to M. Thackeray (*A new upper bound for cap
  sets in dimension 7*, arXiv:2206.09804, 2022), who showed that no cap on
  289 points exists;
- beating either side is a publishable new result (FunSearch's improvement
  of the dimension-8 lower bound, Romera-Paredes et al., *Nature* 625,
  2024, is the recent precedent that search + verification can move these
  numbers).

## What's in `/app/Task/Basic.lean`

The file has two zones:

- **Definition zone (do not modify).** Points are functions
  `Fin 7 → ZMod 3` (mathlib's `ZMod 3` is the field `Z/3Z`), and

  ```lean
  def IsCap (S : Finset (Fin 7 → ZMod 3)) : Prop :=
    ∀ x ∈ S, ∀ y ∈ S, x ≠ y → - (x + y) ∉ S
  ```

  says that `S` is a cap: for any two distinct points `x, y` of `S`, the
  midpoint of the segment `xy` — which over `ZMod 3` is `(x + y) / 2 =
  - (x + y)`, the third point on the line through `x` and `y` — is not in `S`.
  (For distinct `x, y` this third point differs from both, so this is exactly
  "no three collinear points".)
- **Claim slot.** **State and prove a theorem named `capset_d7_main`**
  below the `-- END OF FIXED PART` line, in **exactly one** of these two
  shapes, with a literal decimal numeral `k` of your choice:

  - **Construction direction** (you exhibit a cap on `k` points):

    ```lean
    theorem capset_d7_main : ∃ S : Finset (Fin 7 → ZMod 3), IsCap S ∧ S.card ≥ k := ...
    ```

  - **Upper bound direction** (you prove no cap on `k` points exists):

    ```lean
    theorem capset_d7_main : ¬ ∃ S : Finset (Fin 7 → ZMod 3), IsCap S ∧ S.card ≥ k := ...
    ```

  Both directions count. No instance, no witness, no lemma ladder, and no
  solution are provided: finding the construction or the upper-bound argument,
  and driving it through the Lean kernel, is the task. You may add any
  auxiliary definitions and lemmas below the fixed line.

## Rules

- Do not change any **code** above the line `-- END OF FIXED PART` (the
  import and the `IsCap` definition are frozen); the verifier compares it
  (comments stripped, whitespace-normalized) against the reference.
  Comments and docstrings up there are free to edit — they do not affect
  judging.
- The statement of `capset_d7_main` must match one of the two templates
  above verbatim (up to whitespace), at the top level of the file (not
  inside a `namespace`), with a literal numeral `k`.
- No `sorry`, no `admit`, no `axiom`/`sorryAx` declarations, and no
  redefinition tricks: the tokens `notation`, `macro`, `syntax`, `elab`,
  `opaque`, `unsafe`, `extern`, `implemented_by`, `initialize` and the option
  `skipKernelTC` are forbidden everywhere in the file. The verifier scans
  for this lexically (comments stripped) and then checks
  `#print axioms capset_d7_main`: only `propext`, `Classical.choice`,
  `Quot.sound` and `Lean.ofReduceBool` (i.e. `native_decide`, which **is**
  allowed) may appear. The judge automatically lets `native_decide`'s
  generated internal axioms (`._native.native_decide.ax_*`) through;
  `native_decide` can be used directly.

## How to work

You have a 12-hour budget and are expected to use it. Matching the
published record (a 236-point cap, or the exclusion of 289 points) is the beginning of the work, not the end
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
is untouched, (3) parses your `capset_d7_main` statement to extract the
direction and `k`, (4) compiles the file together with a consistency
check that re-states your claim from the fixed definitions, and (5)
verifies the axiom whitelist. It then independently evaluates your proven
claim against the published literature frontier (a cap on 236 points,
Edel 2004; no cap on 289 points, Thackeray 2022). **A strictly
stronger certified bound is always better, and there is no upper limit**
— the published frontier is the bar to beat, and beating it (a cap on
`k ≥ 237` points, or a proof that no cap on `k ≤ 288` points exists) is a
literature-level new result.

## Environment

The project builds offline against the mathlib checkout at
`/opt/lean-lib/mathlib4`; use `lake build Task` in `/app` to check.
Agent budget: 12 hours. The container has internet access. A helper `/app/snapshot.sh` mirrors your `/app/Task` workspace into `/logs/artifacts/` every 5 minutes once started — launch it early with `nohup /app/snapshot.sh >/dev/null 2>&1 &` so your work is preserved whatever happens later.
