# Task: Mutually orthogonal Latin squares — Open Construction

A **Latin square** of order `n` is an `n × n` grid over `n` symbols with
every row and every column containing each symbol exactly once. Two Latin
squares are **orthogonal** if superimposing them produces all `n²` ordered
pairs exactly once. A set of pairwise orthogonal Latin squares is called
**MOLS**, and `N(n)` denotes the largest possible size of such a set. At
most `n - 1` MOLS of order `n` can exist (pigeonhole), with equality
exactly when a projective plane of order `n` exists.

`N(q) = q - 1` is known for prime powers (finite fields) and `N(6) = 1`
(Tarry 1900). For every other non-prime-power order the exact value of
`N(n)` is unknown. The published intervals for the ten grid orders of this
task (Handbook of Combinatorial Designs, 2nd ed., chapter III.3, as updated
by Todorov 2012 — four MOLS of order 14 — and Abel 2013 — five MOLS of
order 18; snapshot against Miller–Abel–Valkov–Fraser,
*Constructions for optimal mutually orthogonal Latin squares*, Symmetry
16(12):1678, 2024, Table 1):

    N(10) ∈ [2, 6]    N(12) ∈ [5, 11]   N(14) ∈ [4, 12]   N(15) ∈ [4, 14]
    N(18) ∈ [5, 17]   N(20) ∈ [4, 19]   N(21) ∈ [5, 19]   N(22) ∈ [3, 20]
    N(24) ∈ [7, 23]   N(26) ∈ [4, 25]

The flagship order is `n = 10`: E. T. Parker's orthogonal pair of 1959 (the
Bose–Shrikhande–Parker refutation of Euler's 1782 conjecture) has never
been extended to a triple — the record has stood for **66 years**. The
upper bound 6 combines Lam–Thiel–Swiercz's 1989 computer exclusion of a
projective plane of order 10 with Bruck's completion theorem; recent SAT
work ([arXiv:2503.10504](https://arxiv.org/abs/2503.10504),
[arXiv:2509.09633](https://arxiv.org/abs/2509.09633),
[arXiv:2605.02132](https://arxiv.org/abs/2605.02132)) re-verifies
exclusions and finds new orthogonal *pairs* — never a third square.

## What's in `/app/Task/Basic.lean`

In `/app/Task/Basic.lean`, below the line `-- END OF FIXED PART`, prove
the claim `submission_lower`:

```lean
theorem submission_lower : ∃ Ss : List (Fin n → Fin n → Fin n), MolsSet n Ss ∧ Ss.length ≥ k := by
```

where **you choose the two numerals `n` (the order, appearing four times)
and `k` (the family size)** — the claim certifies `N(n) ≥ k`. You may
change **only** these two numerals in the claim statement; the claim body
must stay between its `-- CLAIM submission_lower BEGIN/END` markers. The
judge parses `(n, k)` from the claim header and evaluates it against
the per-order records in the Background.

The fixed definition layer (do not modify the code) gives you:

- `isLatin n L : Bool` — the computable predicate "the `n × n` table `L`
  over `Fin n` is a Latin square": every row and every column contains
  each symbol exactly once (`O(n³)` comparisons);
- `areOrthogonal n L M : Bool` — the computable predicate "the squares
  `L`, `M` are orthogonal": every ordered pair `(a, b)` occurs at some
  cell (with `n²` cells and `n²` pairs, "every pair occurs" is the same as
  "no pair repeats");
- `AllMOLS n Ss : Bool` — every table in `Ss` is Latin and every two are
  orthogonal (scans the list);
- `MolsSet n Ss : Prop` — `AllMOLS n Ss = true`, the packaged certificate.

Boundary behavior, aligned with the solver sibling task `mols-n10`:
duplicate squares are rejected automatically (two copies of the same
square are never orthogonal for `n ≥ 2`); the empty list satisfies the
predicate vacuously but can never meet `Ss.length ≥ k` for `k ≥ 1`.

Bring your own family as data — typically a list of squares built by a
small helper, e.g. `def sq (rows : List (List Nat)) : Fin n → Fin n →
Fin n := fun r c => ⟨(rows.getD r.val []).getD c.val 0 % n, by omega⟩` with
the matrices as literal data, or a programmatic generator (finite-field
squares, product constructions, difference-matrix developments) — and
prove the claim, e.g. `exact ⟨mySquares, by native_decide, by native_decide⟩`.
**`native_decide` is allowed and is the intended certificate path**: the
judge whitelists `Lean.ofReduceBool` and `Lean.trustCompiler`, alongside
the three standard axioms.

**Sanity anchors.**

- **n = 3, k = 2** (off-grid sanity): the cyclic pair
  `L1(r,c) = (r+c) mod 3`, `L2(r,c) = (r+2c) mod 3`. Proving
  `MolsSet 3 [L1, L2]` exercises the whole pipeline — fixed layer, square
  representation, `native_decide`, and the claim interface.
- **n = 10, k = 2** (record): the published orthogonal pair of order 10
  (Parker 1959; machine-readable inside SageMath's `MOLS_10_2()`). Any
  valid pair of order 10 ties the 66-year-old record; a SAT
  solver finds such pairs in seconds, so this cell is deliberately
  reachable — the open frontier starts at the third square.

## Rules

- For verifier safety, executable commands `#eval`, `#exec`, `#exit`, and
  `#compile` are not allowed in submitted Lean files, including harmless
  diagnostics. Remove these commands before submission; the verifier rejects
  them before compiling the proof.
  `native_decide` remains allowed as described in this task.
- Do not change any **code** above the line `-- END OF FIXED PART`; the
  verifier compares it (comments stripped, whitespace-normalized) against
  its reference. Comments and docstrings up there are free to edit — they
  do not affect judging.
- Keep the interface name `submission_lower` and the pinned claim shape;
  the verifier parses `(n, k)` from the claim header (the order `n` must
  be the same numeral in all four positions).
- No `axiom` / `sorryAx` anywhere; `sorry` / `admit` only inside the claim
  body, and a body that still contains one is simply not scored. Every
  scored claim must depend only on the whitelisted axioms (`propext`,
  `Classical.choice`, `Quot.sound`, `Lean.ofReduceBool`,
  `Lean.trustCompiler`) — `#print axioms` is checked.

## How to work

You have a 12-hour budget and are expected to use it. Matching the
published record (the per-order records in the Background) is the beginning of the work, not the end
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

The verifier re-checks your Lean proof, parses `(n, k)` from the proven
claim, and independently evaluates it against the published literature
frontier (the per-order records in the Background: 2 at `n = 10`, 5 at
`n = 12`, 4 at `n = 14`, 4 at `n = 15`, 5 at `n = 18`, 4 at `n = 20`, 5
at `n = 21`, 3 at `n = 22`, 7 at `n = 24`, 4 at `n = 26`). **A strictly
stronger certified bound is always better, and there is no upper limit**
— the record at your chosen order is the bar to beat, and beating it (a
family with `k` above the published value at that order) is a
literature-level new result: at `n = 10`, `k = 3` certifies `N(10) ≥ 3`,
settling a 66-year-old open problem. The claim interface accepts
`2 ≤ n ≤ 30`, `1 ≤ k ≤ 29`; orders outside the ten grid orders serve as
sanity checks, and a claim with `k ≥ n` contradicts the pigeonhole bound
`N(n) ≤ n − 1`.

## Environment

The project builds offline with `lake build Task` in `/app`.
Agent budget: 12 hours. The container has internet access. A helper `/app/snapshot.sh` mirrors your `/app/Task` workspace into `/logs/artifacts/` every 5 minutes once started — launch it early with `nohup /app/snapshot.sh >/dev/null 2>&1 &` so your work is preserved whatever happens later.

## Notes

- Where record families come from: finite-field squares and the MacNeish
  product for prime powers and their products; Wilson's transversal-design
  constructions; difference matrices and quasi-difference matrices over
  abelian groups — the Handbook III.3 table entries for the grid orders
  are exactly of these kinds, and several record families ship inside
  SageMath's `sage.combinat.designs` database (`MOLS_12_5`, `MOLS_14_4`,
  `MOLS_15_4`, `OA_7_18`, and friends). Re-deriving a published family
  ties the record; going beyond it requires a *new* square the
  literature does not have.
- Search toolbox for a larger `k`: SAT/CP encodings for "is there a k-th
  square orthogonal to given ones", exact-cover formulations (each
  superimposed pair must appear once), simulated annealing on constraint
  violations. A third order-10 square is a famous SAT benchmark.
- The final verification is fast (a full compile plus the `native_decide`
  checks; the n = 10 pair compiles in about a second).
