# Task: The Bose–Nelson problem for 16 wires — Open Construction

A **sorting network** on `n` wires is a fixed sequence of comparators: the
comparator `(a, b)` reads the values on wires `a` and `b` and places the
smaller one on wire `a`. The network is correct if it sorts **every**
input. By the **0-1 principle** (Knuth, *The Art of Computer Programming*
vol. 3, §5.3.4) it suffices to sort the `2^n` Boolean inputs, so a
candidate network is a finite, machine-checkable certificate.

The **Bose–Nelson problem** asks for `S(n)`, the smallest possible number
of comparators in an `n`-wire sorting network. Exact optima are proven
only up to `n = 12` (Codish et al. 2014; Harder 2020/2022); **every
`n >= 13` is open**. For 16 wires:

    57 <= S(16) <= 60

- **Upper bound 60** (a 60-comparator network exists): M. W. Green's
  handcrafted 1969 construction — **57 years old**, the oldest standing
  record in the table.
- **Lower bound 57** (no 56-comparator network exists): as tightened
  2025-04-21 in Bert Dobbelaere's sorting-network
  [table](https://bertdobbelaere.github.io/sorting_networks.html) (page
  marked updated 2025-11-07, values frozen into this task),
  after a suggestion of Jelmer Firet based on Van Voorhis 1972. Older
  sources — including Wikipedia — still transcribe the weaker
  value 55.
- The 13-wire record (45, Juillé 1995, evolutionary search) and the 14/15
  records (51/56, in Knuth's TAOCP vol. 3, 1998) are comparably old; this
  task pins the 16-wire cell, the flagship of the old guard.

A certified network with **59 or fewer comparators is a literature-level
new result**, beating a record that has stood since 1969.

## What's in `/app/Task/Basic.lean`

In `/app/Task/Basic.lean`, below the line `-- END OF FIXED PART`, prove
the claim `submission`:

```lean
theorem submission : ∃ net : List Cmp, wellFormed 16 net ∧ sortsBinary 16 net = true ∧ net.length ≤ k := by ...
```

where **you choose the numeral `k`** — the smaller the better. The width
16 is pinned. You may change **only** the numeral in the claim statement;
the claim body must stay between its `-- CLAIM submission BEGIN/END`
markers.

The fixed definition layer (do not modify the code) gives you:

- `Cmp := Nat × Nat` — a comparator as a pair of wire indices;
- `wellFormed n net : Bool` — every comparator has `a < b < n`
  (computable);
- `runNet n net x : Array Bool` — the output on the single Boolean input
  `x` (bit `i` of `x` = wire `i`);
- `outputSorted v : Bool` — the output wires are non-decreasing;
- `sortsBinary n net : Bool` — the 0-1 principle, direct specification:
  **all** `2^n` Boolean inputs are sorted (computable).

Bring your own network as data — a `List Cmp` literal — and prove the
claim, e.g. `exact ⟨myNet, by native_decide⟩`. **`native_decide` is
allowed and is the intended certificate path**: the judge whitelists
`Lean.ofReduceBool` and `Lean.trustCompiler`, alongside the three standard
axioms. With the frozen direct predicate, checking the record region
(60-odd comparators against 65536 inputs) takes seconds.

**Sanity anchors.** `/app/examples/example_batcher63.json` holds a
Batcher odd-even mergesort network on 16 wires (63 comparators). Proving
`submission` at `k = 63` with it exercises the whole pipeline — fixed
layer, `native_decide`, and the claim interface — before you aim at the
record region.
The sibling solver task `sorting-network-size` ships the Batcher
generator for every width 13..20, if you want to warm up at other widths
first.

## Rules

- Do not change any **code** above the line `-- END OF FIXED PART`; the
  verifier compares it (comments stripped, whitespace-normalized) against
  its reference. Comments and docstrings up there are free to edit — they
  do not affect judging.
- Keep the interface name `submission` and the pinned claim shape; the
  verifier parses `k` from the claim header.
- No `axiom` / `sorryAx` anywhere; `sorry` / `admit` only inside the claim
  body, and a body that still contains one is simply not scored. Every
  scored claim must depend only on the whitelisted axioms (`propext`,
  `Classical.choice`, `Quot.sound`, `Lean.ofReduceBool`,
  `Lean.trustCompiler`) — `#print axioms` is checked.
- The definition layer is pure core Lean 4 (no imports); you may add
  arbitrary auxiliary definitions, lemmas, and search code below the
  fixed part.

## How to work

You have a 12-hour budget and are expected to use it. Matching the
published record (60 comparators) is the beginning of the work, not the end
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

The verifier re-checks your Lean proof, parses `k` from the proven claim,
and independently evaluates it against the published literature frontier
(60 comparators, Green 1969). **A strictly stronger certified bound
is always better, and there is no upper limit** — the published record is
the bar to beat, and beating it (any `k ≤ 59`) is a literature-level new
result. The proven lower bound is 57, so the plausible region is
`57 ≤ k ≤ 60`; a `k = 57` network would settle `S(16)` exactly.

## Environment

The project builds offline with `lake build Task` in `/app`.
Agent budget: 12 hours. The container has internet access. A helper `/app/snapshot.sh` mirrors your `/app/Task` workspace into `/logs/artifacts/` every 5 minutes once started — launch it early with `nohup /app/snapshot.sh >/dev/null 2>&1 &` so your work is preserved whatever happens later.
