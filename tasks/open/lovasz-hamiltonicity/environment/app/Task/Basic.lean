/-
Statement layer for Lovász's Hamiltonicity conjecture (L. Lovász, research
problem posed in 1969 at the Calgary conference; published in *Combinatorial
Structures and Their Applications*, Proc. Calgary Internat. Conf. 1969,
Gordon and Breach, 1970): every finite connected vertex-transitive graph has
a Hamiltonian path. The conjecture asks for a *path*, not a cycle: the
Petersen graph is vertex-transitive and has a Hamiltonian path but no
Hamiltonian cycle (it is hypohamiltonian), and only five connected
vertex-transitive graphs without a Hamiltonian cycle are known (K₂, the
Petersen graph, the Coxeter graph, and the truncations of the latter two) —
all five have Hamiltonian paths. The conjecture is open; the best lower
bound on the circumference of a connected vertex-transitive graph on n
vertices, Θ(√n) since Babai 1979, was improved by DeVos (2023) and then by
Groenland–Longbrake–Steiner–Turcotte–Yepremyan (2025) to n^(13/21).

This file is the task's definition zone plus slot zone:
- The definition zone defines vertex-transitivity (`G.IsVertexTransitive`,
  via automorphisms `G ≃g G`) and the existence of a Hamiltonian path
  (`G.HasHamiltonianPath`, via mathlib's `Walk.IsHamiltonian`: a walk
  visiting every vertex exactly once), and packages the Petersen graph on
  `Fin 10` together with an explicit Hamiltonian path through it. The
  definitions live in the `SimpleGraph` namespace so that
  `G.IsVertexTransitive` etc. work as dot notation.
- The slot zone states the conjecture (`conj`) and its negation (`refuted`).
  Both proof bodies are left blank.

Fidelity notes (see `tests/reference/concept-ledger.md` of the packaged task):
1. Hamiltonian paths use mathlib's `Walk.IsHamiltonian`
   (`∀ v, p.support.count v = 1`): every vertex visited exactly once. This is
   the standard meaning of "Hamiltonian path" in the literature; mathlib
   reserves `IsHamiltonianCycle` / `SimpleGraph.IsHamiltonian` for cycles.
2. Vertex-transitivity is formulated with mathlib's graph isomorphisms
   (`G ≃g G`, i.e. `RelIso G.Adj G.Adj`): for any two vertices some
   automorphism maps the first to the second.
3. The Petersen graph is given by its standard edge list (outer pentagon,
   inner pentagram, spokes) on `Fin 10`; mathlib has no Petersen graph.
-/

import Mathlib

namespace SimpleGraph

section Defs

variable {V : Type*} [DecidableEq V] (G : SimpleGraph V)

/-- A graph is **vertex-transitive** when for any two vertices there is an
automorphism of `G` mapping the first to the second. -/
def IsVertexTransitive (G : SimpleGraph V) : Prop :=
  ∀ u v : V, ∃ e : G ≃g G, e u = v

/-- `G` **has a Hamiltonian path**: some walk visits every vertex exactly
once (mathlib's `Walk.IsHamiltonian`). -/
def HasHamiltonianPath : Prop :=
  ∃ (u v : V) (p : G.Walk u v), p.IsHamiltonian

/-- Every graph on at most one vertex has a Hamiltonian path: the trivial
walk visits the only vertex. -/
theorem hasHamiltonianPath_of_subsingleton [Subsingleton V] (v : V) :
    G.HasHamiltonianPath :=
  ⟨v, v, Walk.nil, Walk.IsHamiltonian.of_subsingleton⟩

/-- Decidability of `Walk.IsHamiltonian` over a finite vertex type (backs
`decide` proofs of Hamiltonicity claims about concrete walks). -/
instance decWalkIsHamiltonian {u v : V} [Fintype V] (p : G.Walk u v) :
    Decidable p.IsHamiltonian :=
  inferInstanceAs (Decidable (∀ w, p.support.count w = 1))

end Defs

end SimpleGraph

namespace LovaszHamiltonicity

open SimpleGraph (Walk)

/-! ### The Petersen graph and its Hamiltonian path -/

/-- The edges of the Petersen graph on `Fin 10`: the outer pentagon
`0-1-2-3-4-0`, the inner pentagram `5-7-9-6-8-5`, and the spokes `i ~ i+5`. -/
def petersenEdges : Finset (Sym2 (Fin 10)) :=
  {s(0, 1), s(1, 2), s(2, 3), s(3, 4), s(4, 0),
   s(5, 7), s(7, 9), s(9, 6), s(6, 8), s(8, 5),
   s(0, 5), s(1, 6), s(2, 7), s(3, 8), s(4, 9)}

/-- The Petersen graph: two vertices are adjacent when they form one of the
fifteen `petersenEdges`. It is 3-regular, vertex-transitive, and the standard
counterexample showing that the conjecture cannot ask for a cycle. -/
def petersenGraph : SimpleGraph (Fin 10) where
  Adj a b := s(a, b) ∈ petersenEdges
  symm := ⟨fun _a _b h => Sym2.eq_swap ▸ h⟩
  loopless := ⟨fun a h => by
    have key : ∀ v : Fin 10, ¬(s(v, v) ∈ petersenEdges) := by decide
    exact key a h⟩

instance : DecidableRel petersenGraph.Adj :=
  fun a b => inferInstanceAs (Decidable (s(a, b) ∈ petersenEdges))

/-- An explicit Hamiltonian path of the Petersen graph: the walk
`0-1-2-3-4-9-6-8-5-7` (around the outer pentagon, across the spoke `4-9`,
then through the inner pentagram). -/
def petersenHamPath : petersenGraph.Walk 0 7 :=
  Walk.cons (show petersenGraph.Adj 0 1 by decide) <|
  Walk.cons (show petersenGraph.Adj 1 2 by decide) <|
  Walk.cons (show petersenGraph.Adj 2 3 by decide) <|
  Walk.cons (show petersenGraph.Adj 3 4 by decide) <|
  Walk.cons (show petersenGraph.Adj 4 9 by decide) <|
  Walk.cons (show petersenGraph.Adj 9 6 by decide) <|
  Walk.cons (show petersenGraph.Adj 6 8 by decide) <|
  Walk.cons (show petersenGraph.Adj 8 5 by decide) <|
  Walk.cons (show petersenGraph.Adj 5 7 by decide) <|
  Walk.nil

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

/-! ## Slot zone: the conjecture and its negation -/

-- @[slot main]
/-- **Lovász's Hamiltonicity conjecture** (1969): every finite connected
vertex-transitive graph has a Hamiltonian path. -/
theorem conj :
    ∀ {V : Type*} [Fintype V] [DecidableEq V] (G : SimpleGraph V),
      G.Connected → G.IsVertexTransitive → G.HasHamiltonianPath := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

-- @[slot main]
/-- The negation of Lovász's conjecture: some finite connected
vertex-transitive graph has no Hamiltonian path. -/
theorem refuted :
    ¬∀ {V : Type*} [Fintype V] [DecidableEq V] (G : SimpleGraph V),
        G.Connected → G.IsVertexTransitive → G.HasHamiltonianPath := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

end LovaszHamiltonicity
