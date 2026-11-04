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

/- Oracle proof (judge-side; not part of the agent-facing stub): the
published n = 124 record construction — 629 edges, girth 5 (Goedgebeur,
Jooken, Joret, Van den Eede 2025, arXiv:2508.05562), extracted from
AGT-Kulak/searchMaxSizeMinGirth (resultGraphs/iter2UpXtra_150.zip,
n124.g6, first graph). This is the same graph as the oracle of the solver
sibling task `ex-c3c4-maxedges` (solution/record_n124.json), so the two
editions certify the same construction at the same score.

Expected score: ((629 − 483) / 146)³ = 1.0 exactly, milestone
"record_matched". The three `native_decide` steps evaluate, respectively:
symmetry/looplessness of the 124² adjacency matrix, the C3/C4-freeness
scan, and the edge count 629 ≥ 629. -/

def witnessEdges124 : List (Nat × Nat) := [(10, 11), (5, 13), (9, 15), (12, 15), (6, 16), (8, 16), (7, 17), (14, 17), (18, 21), (20, 21), (19, 23), (23, 24), (22, 26), (19, 28), (20, 30), (25, 30), (21, 31), (28, 31), (18, 33), (28, 33), (32, 33), (20, 34), (32, 34), (15, 35), (24, 35), (30, 35), (12, 36), (20, 36), (14, 37), (26, 37), (34, 37), (10, 38), (34, 38), (16, 39), (22, 39), (28, 39), (11, 40), (22, 40), (16, 41), (24, 41), (37, 41), (8, 42), (29, 42), (33, 42), (35, 42), (17, 43), (22, 43), (31, 43), (35, 43), (5, 44), (25, 44), (28, 44), (29, 44), (40, 44), (8, 45), (24, 45), (25, 45), (31, 45), (38, 45), (12, 46), (33, 46), (38, 46), (41, 46), (43, 46), (10, 47), (19, 47), (26, 47), (27, 47), (32, 47), (35, 47), (13, 48), (23, 48), (34, 48), (39, 48), (9, 49), (27, 49), (28, 49), (36, 49), (38, 49), (9, 50), (18, 50), (37, 50), (40, 50), (15, 51), (25, 51), (27, 51), (37, 51), (11, 52), (27, 52), (30, 52), (46, 52), (17, 53), (24, 53), (28, 53), (52, 53), (13, 54), (18, 54), (19, 54), (43, 54), (51, 54), (5, 55), (24, 55), (50, 55), (5, 56), (22, 56), (30, 56), (2, 57), (32, 57), (51, 57), (53, 57), (56, 57), (2, 58), (19, 58), (36, 58), (45, 58), (3, 59), (39, 59), (46, 59), (50, 59), (57, 59), (4, 60), (28, 60), (30, 60), (37, 60), (1, 61), (32, 61), (40, 61), (1, 62), (29, 62), (38, 62), (57, 62), (60, 62), (1, 63), (19, 63), (34, 63), (52, 63), (55, 63), (1, 64), (18, 64), (41, 64), (44, 64), (1, 65), (23, 65), (25, 65), (26, 65), (49, 65), (59, 65), (2, 66), (4, 66), (23, 66), (27, 66), (33, 66), (40, 66), (5, 67), (8, 67), (20, 67), (26, 67), (53, 67), (5, 68), (14, 68), (27, 68), (42, 68), (12, 69), (14, 69), (32, 69), (44, 69), (9, 70), (13, 70), (24, 70), (26, 70), (33, 70), (62, 70), (6, 71), (10, 71), (22, 71), (33, 71), (51, 71), (55, 71), (58, 71), (6, 72), (7, 72), (18, 72), (24, 72), (49, 72), (56, 72), (7, 73), (11, 73), (26, 73), (31, 73), (36, 73), (42, 73), (48, 73), (57, 73), (64, 73), (8, 74), (14, 74), (18, 74), (22, 74), (23, 74), (52, 74), (62, 74), (10, 75), (15, 75), (29, 75), (31, 75), (63, 75), (66, 75), (67, 75), (72, 75), (3, 76), (17, 76), (36, 76), (51, 76), (63, 76), (70, 76), (2, 77), (14, 77), (20, 77), (29, 77), (55, 77), (65, 77), (3, 78), (13, 78), (37, 78), (42, 78), (58, 78), (61, 78), (72, 78), (4, 79), (10, 79), (21, 79), (41, 79), (56, 79), (65, 79), (76, 79), (4, 80), (8, 80), (32, 80), (43, 80), (49, 80), (55, 80), (4, 81), (16, 81), (29, 81), (36, 81), (47, 81), (50, 81), (0, 82), (11, 82), (41, 82), (54, 82), (67, 82), (1, 83), (9, 83), (21, 83), (53, 83), (68, 83), (0, 84), (17, 84), (19, 84), (38, 84), (42, 84), (50, 84), (0, 85), (15, 85), (28, 85), (61, 85), (74, 85), (79, 85), (3, 86), (6, 86), (11, 86), (28, 86), (77, 86), (2, 87), (3, 87), (5, 87), (31, 87), (47, 87), (74, 87), (26, 88), (29, 88), (46, 88), (58, 88), (85, 88), (27, 89), (43, 89), (48, 89), (50, 89), (58, 89), (62, 89), (67, 89), (69, 89), (79, 89), (86, 89), (10, 90), (18, 90), (25, 90), (48, 90), (53, 90), (80, 90), (88, 90), (8, 91), (19, 91), (21, 91), (59, 91), (69, 91), (70, 91), (7, 92), (27, 92), (55, 92), (60, 92), (88, 92), (91, 92), (17, 93), (29, 93), (30, 93), (41, 93), (48, 93), (49, 93), (61, 93), (71, 93), (87, 93), (91, 93), (13, 94), (22, 94), (25, 94), (32, 94), (36, 94), (41, 94), (75, 94), (83, 94), (84, 94), (86, 94), (92, 94), (16, 95), (27, 95), (31, 95), (56, 95), (61, 95), (70, 95), (77, 95), (84, 95), (90, 95), (6, 96), (23, 96), (30, 96), (31, 96), (32, 96), (50, 96), (68, 96), (76, 96), (82, 96), (88, 96), (10, 97), (24, 97), (36, 97), (54, 97), (59, 97), (60, 97), (61, 97), (68, 97), (2, 98), (18, 98), (35, 98), (38, 98), (39, 98), (61, 98), (67, 98), (76, 98), (92, 98), (7, 99), (9, 99), (29, 99), (32, 99), (39, 99), (45, 99), (52, 99), (54, 99), (79, 99), (11, 100), (12, 100), (19, 100), (29, 100), (37, 100), (56, 100), (80, 100), (83, 100), (98, 100), (5, 101), (7, 101), (21, 101), (23, 101), (46, 101), (51, 101), (61, 101), (81, 101), (86, 101), (6, 102), (12, 102), (34, 102), (40, 102), (42, 102), (53, 102), (54, 102), (65, 102), (87, 102), (92, 102), (13, 103), (14, 103), (21, 103), (35, 103), (40, 103), (49, 103), (57, 103), (63, 103), (88, 103), (8, 104), (9, 104), (34, 104), (56, 104), (64, 104), (66, 104), (86, 104), (88, 104), (97, 104), (12, 105), (17, 105), (21, 105), (25, 105), (39, 105), (47, 105), (55, 105), (62, 105), (78, 105), (82, 105), (104, 105), (2, 106), (11, 106), (25, 106), (34, 106), (43, 106), (68, 106), (72, 106), (81, 106), (85, 106), (91, 106), (2, 107), (9, 107), (22, 107), (42, 107), (60, 107), (63, 107), (69, 107), (82, 107), (90, 107), (101, 107), (4, 108), (15, 108), (22, 108), (38, 108), (53, 108), (64, 108), (77, 108), (78, 108), (91, 108), (96, 108), (4, 109), (7, 109), (34, 109), (35, 109), (44, 109), (58, 109), (59, 109), (74, 109), (82, 109), (83, 109), (95, 109), (3, 110), (12, 110), (23, 110), (60, 110), (64, 110), (67, 110), (71, 110), (95, 110), (99, 110), (103, 110), (106, 110), (3, 111), (16, 111), (30, 111), (38, 111), (54, 111), (55, 111), (66, 111), (69, 111), (73, 111), (83, 111), (85, 111), (0, 112), (13, 112), (31, 112), (52, 112), (65, 112), (69, 112), (71, 112), (81, 112), (98, 112), (104, 112), (0, 113), (14, 113), (30, 113), (39, 113), (58, 113), (64, 113), (70, 113), (75, 113), (80, 113), (101, 113), (102, 113), (0, 114), (8, 114), (40, 114), (46, 114), (47, 114), (48, 114), (60, 114), (72, 114), (76, 114), (77, 114), (83, 114), (6, 115), (13, 115), (17, 115), (20, 115), (27, 115), (45, 115), (59, 115), (64, 115), (85, 115), (100, 115), (107, 115), (9, 116), (10, 116), (16, 116), (20, 116), (23, 116), (43, 116), (44, 116), (57, 116), (78, 116), (92, 116), (2, 117), (6, 117), (15, 117), (21, 117), (26, 117), (44, 117), (52, 117), (80, 117), (84, 117), (97, 117), (3, 118), (7, 118), (15, 118), (19, 118), (20, 118), (40, 118), (41, 118), (62, 118), (68, 118), (90, 118), (112, 118), (0, 119), (7, 119), (16, 119), (25, 119), (33, 119), (87, 119), (89, 119), (97, 119), (100, 119), (103, 119), (108, 119), (0, 120), (4, 120), (12, 120), (18, 120), (26, 120), (45, 120), (63, 120), (68, 120), (86, 120), (93, 120), (116, 120), (1, 121), (3, 121), (14, 121), (33, 121), (45, 121), (48, 121), (56, 121), (81, 121), (82, 121), (92, 121), (117, 121), (1, 122), (4, 122), (11, 122), (20, 122), (24, 122), (39, 122), (51, 122), (69, 122), (84, 122), (87, 122), (88, 122), (0, 123), (1, 123), (5, 123), (6, 123), (35, 123), (36, 123), (37, 123), (66, 123), (90, 123), (91, 123), (99, 123)]

/-- Lower-bound (construction) claim: there exists a graph on 124 vertices
with no `C3` and no `C4` and at least `m` edges, certifying
`ex(124, {C3,C4}) ≥ m`. `m = 629` ties the published record (Goedgebeur,
Jooken, Joret, Van den Eede 2025); `m = 630` is a literature-level new
result. Pick your `m`. -/
theorem submission_lower : ∃ g : Gph 124, WellFormed 124 g = true ∧ C3C4Free 124 g = true ∧ edgeCount 124 g ≥ 629 := by
-- CLAIM submission_lower BEGIN
  exact ⟨ofEdges 124 witnessEdges124, by native_decide, by native_decide, by native_decide⟩
-- CLAIM submission_lower END

end ExC3C4
