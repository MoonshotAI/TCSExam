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


/- Oracle proof: M. W. Green's 1969 record network (16 wires, 60
comparators; from Bert Dobbelaere's sorting-network table, frozen
2026-09-17, re-verified by the sibling solver task's checker). The claim is
proven at `k = 60`, tying the record: expected reward 1.0
(`record_matched`). -/

/-- Green's network, flattened layer by layer from the table. -/
def greenNet : List Cmp :=
  [(0,13),(1,12),(2,15),(3,14),(4,8),(5,6),(7,11),(9,10),(0,5),(1,7),(2,9),(3,4),(6,13),(8,14),(10,15),(11,12),(0,1),(2,3),(4,5),(6,8),(7,9),(10,11),(12,13),(14,15),(0,2),(1,3),(4,10),(5,11),(6,7),(8,9),(12,14),(13,15),(1,2),(3,12),(4,6),(5,7),(8,10),(9,11),(13,14),(1,4),(2,6),(5,8),(7,10),(9,13),(11,14),(2,4),(3,6),(9,12),(11,13),(3,5),(6,8),(7,9),(10,12),(3,4),(5,6),(7,8),(9,10),(11,12),(6,7),(8,9)]

theorem submission : ∃ net : List Cmp, wellFormed 16 net ∧ sortsBinary 16 net = true ∧ net.length ≤ 60 := by
-- CLAIM submission BEGIN
  exact ⟨greenNet, by native_decide⟩
-- CLAIM submission END

end SN16
