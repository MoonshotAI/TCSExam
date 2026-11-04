set_option maxRecDepth 100000
set_option maxHeartbeats 0
set_option synthInstance.maxSize 512

/-!
# The cage problem: small k-regular graphs of girth at least g

Fixed definition layer for the task `cage-girth-lean-open`. Everything from
the top of this file down to the line `-- END OF FIXED PART` is part of the
problem statement. The judge checks it verbatim; do not edit, move, or
delete it. Your work (auxiliary definitions, lemmas, the graph data, and
the proof of the claim) goes below the mark.

A **(k,g)-cage** is a smallest `k`-regular graph whose **girth** (length of
a shortest cycle) is `g`; its order is the cage number `n(k,g)`. Only
girth `≥ g` is required of a candidate: by a theorem of Sachs
(Erdős–Sachs 1963, Theorem 4), a minimum-order `k`-regular graph of girth
`≥ g` automatically has girth exactly `g`, so the relaxation changes
nothing at the optimum. Exact cage numbers are rare; the evaluated cells of
this task are open intervals, e.g.

    202 <= n(3,13) <= 272

(lower bound: McKay–Myrvold–Nadon, SODA 1998, computer proof; upper bound:
the Cayley graph of the affine group AGL(1,17) found by Hoare, reported in
Biggs 1989, still the record after 37 years). A valid `k`-regular graph of
girth `≥ g` on `N` vertices certifies `n(k,g) ≤ N`; matching the record
(`N = 272` for `(3,13)`) ties the standing record, and any smaller `N` is a
literature-level new result.
-/

namespace Cage

/-- A finite simple graph on `n` vertices, adjacency as a Nat-indexed Bool
function (meaningful only for arguments `< n`). -/
structure CageGraph where
  n : Nat
  adj : Nat → Nat → Bool

/-- symmetric and irreflexive on the vertex range -/
def wellFormed (G : CageGraph) : Bool :=
  (List.range G.n).all fun u =>
    (G.adj u u == false) && (List.range G.n).all fun v => G.adj u v == G.adj v u

/-- neighbor lists, precomputed once -/
def neighbors (G : CageGraph) : Array (Array Nat) := Id.run do
  let mut out : Array (Array Nat) := #[]
  for u in List.range G.n do
    let mut ns : Array Nat := #[]
    for v in List.range G.n do
      if G.adj u v then ns := ns.push v
    out := out.push ns
  return out

/-- every vertex has exactly `k` neighbors -/
def isKRegular (G : CageGraph) (k : Nat) : Bool :=
  let nb := neighbors G
  nb.all fun ns => ns.size == k

/-- girth ≥ g: BFS from every root to depth `(g-1)/2`, flagging any
back/cross edge closing a cycle of length `< g`. A non-tree edge `(x,y)`
with `depth y ≥ depth x` closes a cycle of length `depth x + depth y + 1`
through the root; scanning every root detects exactly the cycles shorter
than `g`. -/
def girthGE (G : CageGraph) (g : Nat) : Bool := Id.run do
  let nb := neighbors G
  let maxDepth := (g - 1) / 2
  for root in List.range G.n do
    let mut depth : Array Int := Array.replicate G.n (-1)
    depth := depth.set! root 0
    let mut frontier : Array Nat := #[root]
    let mut bad := false
    for d in List.range (maxDepth + 1) do
      if bad || frontier.isEmpty then break
      let mut next : Array Nat := #[]
      for x in frontier do
        for y in nb[x]! do
          let dy := depth[y]!
          if dy < 0 then
            depth := depth.set! y (Int.ofNat (d + 1))
            next := next.push y
          else if dy ≥ Int.ofNat d then
            if d + dy.toNat + 1 < g then bad := true
      frontier := next
    if bad then return false
  return true

/-- Prop-level wrappers (abbrev so typeclass resolution sees through them;
`native_decide` can then check concrete graphs directly). -/
abbrev WellFormed (G : CageGraph) : Prop := wellFormed G = true
abbrev IsKRegular (G : CageGraph) (k : Nat) : Prop := isKRegular G k = true
abbrev GirthGE (G : CageGraph) (g : Nat) : Prop := girthGE G g = true

-- END OF FIXED PART

/- Your work goes below. Prove the claim.

Rules (machine-checked):
- You may change only the numerals `3`, `13` and `272` in the claim
  statement — the cell `(k, g)` you target and the claimed order bound `N`;
  every other token of the claim line must remain exactly as written, and
  the claim body must stay between its `-- CLAIM submission_lower BEGIN/END`
  markers. The evaluated cells are `(3,5)` (sanity check only — it does
  not count), `(3,13)`, `(4,10)`, `(3,16)`, `(4,11)` and `(3,17)`; any
  other `(k,g)` is not evaluated.
- No `sorry` / `admit` outside the claim body (a claim whose body still
  contains one simply does not score), no `axiom` / `sorryAx`, and the
  fixed part above must stay verbatim. `native_decide` is allowed (the
  judge whitelists `Lean.ofReduceBool` and `Lean.trustCompiler`).
- Auxiliary definitions and lemmas between the fixed part and the claim
  (or after it) are free. Do not close `namespace Cage`.
- Representation hint: define the graph by a rule (group multiplication,
  congruences, ...) instead of a giant literal table — the `(3,13)` record
  graph needs only three group elements of `AGL(1,17)`; see
  `/app/examples/petersen_snippet.lean.txt` for the worked Petersen example.
  At the record scales (`N ≤ 2048`) the BFS predicate evaluates under
  `native_decide` in seconds. -/

theorem submission_lower : ∃ G : CageGraph, WellFormed G ∧ IsKRegular G 3 ∧
    GirthGE G 13 ∧ G.n ≤ 272 := by
-- CLAIM submission_lower BEGIN
  sorry
-- CLAIM submission_lower END

end Cage
