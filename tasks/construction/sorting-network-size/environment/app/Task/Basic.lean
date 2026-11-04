set_option maxRecDepth 100000
set_option maxHeartbeats 0
set_option synthInstance.maxSize 512

/-!
# S(16): sorting networks on 16 wires with as few comparators as possible

Fixed definition layer for the task `sorting-network-size-lean-open`.
Everything from the top of this file down to the line `-- END OF FIXED PART`
is part of the problem statement. The judge checks it verbatim; do not edit,
move, or delete it. Your work (auxiliary definitions, lemmas, the network
data, and the proof of the claim) goes below the mark.

A **comparator network** on `n` wires is a list of comparators `(a, b)`; a
comparator compares the values on wires `a` and `b` and places the smaller
one on wire `a`. The network **sorts** if it sorts every input. By the
**0-1 principle** (Knuth, *The Art of Computer Programming* vol. 3,
§5.3.4), an `n`-wire network sorts all inputs if and only if it sorts the
`2^n` Boolean inputs — `sortsBinary` below is exactly that decidable
check, phrased as direct simulation. The least possible number of
comparators is `S(n)`; `S(16)` is known to lie in `57 ... 60`, where 60 is
M. W. Green's handcrafted 1969 network and 57 is the proven lower bound
(Dobbelaere's table, tightened 2025-04-21). Exact optima are proven only
up to `n = 12`; every `n >= 13` is open.

This file deliberately uses **no imports** (pure core Lean 4): comparator
networks, `Bool` predicates, and `Nat` bit operations all live in the core
library, and skipping the imports leaves the whole verifier budget to
`native_decide`.
-/

namespace SN16

/-- A comparator: a pair of wire indices. -/
abbrev Cmp := Nat × Nat

/-- Well-formedness: every comparator has `a < b < n`. -/
def wellFormed (n : Nat) (net : List Cmp) : Bool :=
  net.all fun (a, b) => a < b && b < n

/-- Run `net` on the single Boolean input `x` (bit `i` of `x` = initial
value on wire `i`); return the output value on every wire. -/
def runNet (n : Nat) (net : List Cmp) (x : Nat) : Array Bool :=
  let v0 := (List.range n).toArray.map fun i => x.testBit i
  net.foldl (fun v (a, b) =>
    let va := v.getD a false
    let vb := v.getD b false
    if va && !vb then (v.setIfInBounds a false).setIfInBounds b true else v) v0

/-- Is an output wire vector non-decreasing? -/
def outputSorted (v : Array Bool) : Bool :=
  (List.range (v.size - 1)).all fun i => !(v.getD i false) || v.getD (i + 1) false

/-- Direct specification (frozen as the judging predicate): the network
sorts every one of the `2^n` Boolean inputs. A computable
`sortsBinary 16 net = true`, packaged with `wellFormed 16 net` and a length
bound in the claim below, is a machine-checkable certificate for
`S(16) <= net.length`. -/
def sortsBinary (n : Nat) (net : List Cmp) : Bool :=
  (List.range (2 ^ n)).all fun x => outputSorted (runNet n net x)

-- END OF FIXED PART

/- Your work goes below. Prove the claim.

Rules (machine-checked):
- You may change only the numeral `k` in the claim statement (the width 16
  is pinned); every other token of the claim lines must remain exactly as
  written, and the claim body must stay between its
  `-- CLAIM submission BEGIN/END` markers.
- No `sorry` / `admit` outside the claim body (a claim whose body still
  contains one simply does not score), no `axiom` / `sorryAx`, and the
  fixed part above must stay verbatim. `native_decide` is allowed (the
  judge whitelists `Lean.ofReduceBool` and `Lean.trustCompiler`).
- Auxiliary definitions and lemmas between the fixed part and the claim
  (or after it) are free. Do not close `namespace SN16`.
- Budget hint: with the frozen direct predicate, `native_decide` on the
  record region (60-odd comparators, 65536 inputs) takes seconds; do not
  hand-roll a faster predicate — an auxiliary fast check only pays off if
  you prove it implies `sortsBinary`. -/

/-- Construction claim: there exists a well-formed sorting network on 16
wires using at most `k` comparators — a machine-checkable certificate for
`S(16) <= k`. `k = 60` ties the published record (Green 1969); `k <= 59`
is a literature-level new result; `k < 57` contradicts the proven lower
bound. The default `k = 63` is the Batcher construction.
Pick your `k`. -/
theorem submission : ∃ net : List Cmp, wellFormed 16 net ∧ sortsBinary 16 net = true ∧ net.length ≤ 63 := by
-- CLAIM submission BEGIN
  sorry
-- CLAIM submission END

end SN16
