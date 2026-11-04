set_option maxRecDepth 100000
set_option maxHeartbeats 0
set_option synthInstance.maxSize 512

/-!
# ex(n, {C3, C4}): edge-maximal graphs with no triangle and no 4-cycle

Fixed definition layer for the task `ex-c3c4-maxedges-lean-open`. Everything
from the top of this file down to the line `-- END OF FIXED PART` is part of
the problem statement. The judge checks it verbatim; do not edit, move, or
delete it. Your work (auxiliary definitions, the witness edge list, and the
proof of the claim) goes below the mark.

The extremal function `ex(n, {C3, C4})` is the largest number of edges in a
graph on `n` vertices with **no triangle (`C3`) and no 4-cycle (`C4`)** —
equivalently, with girth (shortest cycle length) at least 5. The function is
known exactly only up to `n = 53` (Afzaly–McKay data page,
<https://users.cecs.anu.edu.au/~bdm/data/extremal.html>); for every `n ≥ 54`
only construction records exist, with no upper-bound proofs. The standing
records were computed by J. Goedgebeur, J. Jooken, G. Joret and
J. Van den Eede (2025, [arXiv:2508.05562](https://arxiv.org/abs/2508.05562);
to appear in Experimental Mathematics) with roughly 380 CPU-days of local
search, and are published in machine-readable form at
<https://github.com/AGT-Kulak/searchMaxSizeMinGirth>.

On the main order of this task, `n = 124`, the published record is **629
edges**. A certified graph with 630 edges or more is a literature-level new
result: it improves the best known lower bound on `ex(124, {C3,C4})`.
-/

namespace ExC3C4

/-- A graph on `n` vertices given by an adjacency function. Values outside
`{0, ..., n-1}²` are don't-care: every predicate below only inspects
vertices `< n`. Data only; well-formedness is a checked predicate. -/
structure Gph (n : Nat) where
  adj : Nat → Nat → Bool

/-- Adjacency matrix built from an edge list (symmetric closure, loops kept
as listed so that `WellFormed` can reject them). -/
def ofEdges (n : Nat) (es : List (Nat × Nat)) : Gph n :=
  let mat := Id.run do
    let mut a := Array.replicate n (Array.replicate n false)
    for e in es do
      if e.1 < n && e.2 < n then
        a := a.set! e.1 ((a[e.1]!).set! e.2 true)
        a := a.set! e.2 ((a[e.2]!).set! e.1 true)
    return a
  ⟨fun i j => mat[i]![j]!⟩

/-- `WellFormed n g`: the adjacency function is symmetric and loopless on the
relevant range. Matches the solver sibling's format checks (an edge list is
always symmetric by construction of `ofEdges`; a listed self-loop `(i, i)`
sets `adj i i = true` and is rejected here). -/
def WellFormed (n : Nat) (g : Gph n) : Bool :=
  (List.range n).all fun i => (List.range n).all fun j =>
    (g.adj i j == g.adj j i) && (!(i == j) || !(g.adj i j))

/-- `edgeCount n g`: the number of edges, counted as pairs `i < j`. Matches
the solver sibling's edge count exactly (its checker stores each listed pair
once in both directions and counts `|E|`; here the `i < j` count of a
symmetric loopless adjacency is the same number). -/
def edgeCount (n : Nat) (g : Gph n) : Nat :=
  (List.range n).foldl (fun acc i =>
    (List.range n).foldl (fun acc2 j =>
      if i < j && g.adj i j then acc2 + 1 else acc2) acc) 0

/-- `NoC3 n g`: no triangle — for every triple `(i, j, k)`, the three
adjacencies are not all true. This is the solver checker's "for every edge
`(u,v)`, the neighbourhoods of `u` and `v` are disjoint", quantified over
triples instead: a triangle is exactly an edge plus a common neighbour. -/
def NoC3 (n : Nat) (g : Gph n) : Bool :=
  (List.range n).all fun i => (List.range n).all fun j => (List.range n).all fun k =>
    !(g.adj i j && g.adj j k && g.adj i k)

/-- `NoC4 n g`: no 4-cycle — any two distinct vertices have **at most one
common neighbour**. Two distinct length-2 paths between the same pair of
vertices are exactly a 4-cycle, so this counting formulation is the same
constraint as the solver checker's two-path scan, with no notion of path or
cycle needed. (The diagonal `i = j` is excluded: a length-2 path from a
vertex back to itself is not a 4-cycle.) -/
def NoC4 (n : Nat) (g : Gph n) : Bool :=
  (List.range n).all fun i => (List.range n).all fun j =>
    i == j || (((List.range n).filter fun k => g.adj i k && g.adj j k).length ≤ 1)

/-- `C3C4Free n g`: girth at least 5 — no `C3` and no `C4`. -/
def C3C4Free (n : Nat) (g : Gph n) : Bool := NoC3 n g && NoC4 n g

-- END OF FIXED PART

/- Your work goes below. Prove the claim.

Rules (machine-checked):
- You may change only the numeral `m` at the end of the claim statement;
  every other token of the claim lines (including the three `124`s) must
  remain exactly as written, and the claim body must stay between its
  `-- CLAIM submission_lower BEGIN/END` markers.
- No `sorry` / `admit` outside the claim body (a claim whose body still
  contains one simply does not score), no `axiom` / `sorryAx`, and the
  fixed part above must stay verbatim. `native_decide` is allowed (the
  judge whitelists `Lean.ofReduceBool` and `Lean.trustCompiler`).
- Auxiliary definitions between the fixed part and the claim (or after it)
  are free. Do not close `namespace ExC3C4`.
- Representation hint: bring your graph as an edge list
  `def myEdges : List (Nat × Nat) := [(u₁, v₁), ...]` and prove the claim
  by `exact ⟨ofEdges 124 myEdges, by native_decide, by native_decide, by
  native_decide⟩`. At the record region (m ≈ 630) the native evaluation
  takes seconds. -/

/-- Lower-bound (construction) claim: there exists a graph on 124 vertices
with no `C3` and no `C4` and at least `m` edges, certifying
`ex(124, {C3,C4}) ≥ m`. `m = 629` ties the published record (Goedgebeur,
Jooken, Joret, Van den Eede 2025); `m = 630` is a literature-level new
result. Pick your `m`. -/
theorem submission_lower : ∃ g : Gph 124, WellFormed 124 g = true ∧ C3C4Free 124 g = true ∧ edgeCount 124 g ≥ 483 := by
-- CLAIM submission_lower BEGIN
  sorry
-- CLAIM submission_lower END

end ExC3C4
