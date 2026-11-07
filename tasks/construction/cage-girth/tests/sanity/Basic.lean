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
nothing at the optimum. Exact cage numbers are rare; the scoring cells of
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

/-- nonempty, symmetric and irreflexive on the vertex range -/
def wellFormed (G : CageGraph) : Bool :=
  decide (0 < G.n) && (List.range G.n).all fun u =>
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

/- Sanity fixture content (judge-side): the Petersen graph, the (3,5)-cage
(n(3,5) = 10, the only scoring cell whose exact answer is known), as the
Kneser graph K(5,2): vertices = 2-subsets of {0..4}, adjacency = disjointness,
encoded as 5-bit masks. Expected judge result: valid, reward 0.0, milestone
"sanity" (the (3,5) cell is closed and always scores 0). -/

def petersen : CageGraph where
  n := 10
  adj := fun u v =>
    let mu := #[1+2, 1+4, 1+8, 1+16, 2+4, 2+8, 2+16, 4+8, 4+16, 8+16][u]!
    let mv := #[1+2, 1+4, 1+8, 1+16, 2+4, 2+8, 2+16, 4+8, 4+16, 8+16][v]!
    mu &&& mv == 0

theorem petersen_wf : WellFormed petersen := by native_decide
theorem petersen_reg : IsKRegular petersen 3 := by native_decide
theorem petersen_girth : GirthGE petersen 5 := by native_decide

theorem submission_lower : ∃ G : CageGraph, WellFormed G ∧ IsKRegular G 3 ∧
    GirthGE G 5 ∧ G.n ≤ 10 := by
-- CLAIM submission_lower BEGIN
  exact ⟨petersen, petersen_wf, petersen_reg, petersen_girth, by decide⟩
-- CLAIM submission_lower END

end Cage
