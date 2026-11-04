/-
Statement layer for the Total Coloring Conjecture (Behzad 1965, Ph.D. thesis,
Michigan State University; Vizing 1968, independently): every finite simple
graph G satisfies χ''(G) ≤ Δ(G) + 2, where χ''(G) (the total chromatic
number) is the least number of colors needed to color the vertices AND the
edges of G so that adjacent vertices, adjacent edges, and each edge together
with each of its endpoints all receive different colors, and Δ(G) is the
maximum degree. The conjecture is open; the best general bound is
χ''(G) ≤ Δ(G) + 10^26 (Molloy–Reed 1998). Complete graphs and complete
bipartite graphs are settled: χ''(K_n) is n for odd n and n + 1 for even n,
and χ''(K_{n,n}) = n + 2 (Behzad–Chartrand–Cooper 1967).

This file is the task's definition zone plus slot zone:
- The definition zone defines adjacent edges, total colorings (a vertex
  coloring together with an edge coloring, with the three compatibility
  conditions), the total chromatic number χ'' for finite graphs, and proves
  the basic API lemmas about them. The definitions live in the `SimpleGraph`
  namespace so that `G.totalChromaticNumber` etc. work as dot notation. The
  maximum degree Δ is mathlib's `SimpleGraph.maxDegree`. Total colorability
  with k colors (`TotalColorable k`) is decidable: claims about small
  concrete graphs can be verified by `decide` (see
  `tests/reference/small-examples.md` of the packaged task). The number χ''
  itself is `Nat.find`-based and not meant to be kernel-computed; pin it down
  via the API lemmas (`totalChromaticNumber_le`, `le_totalChromaticNumber`,
  `TotalColorable.mono`).
- The slot zone states the conjecture (`conj`) and its negation (`refuted`).
  Both proof bodies are left blank.

Fidelity notes (see `tests/reference/concept-ledger.md` of the packaged task):
1. A total coloring is given directly as a pair of color functions
   (vertices / edges), not as a vertex coloring of the total graph; the two
   readings are equivalent, and the direct reading is the one used in the
   literature. Edge colors are assigned to the edges of `G` only (the subtype
   `G.edgeFinset`), which keeps finite enumeration small.
2. Edges are adjacent iff they are distinct and share an endpoint
   (`EdgesAdj`); this is the standard meaning of "adjacent edges".
3. χ''(G) is the least k with `G.TotalColorable k`; existence of some bound
   (every object its own color) is proved in `totalColorable_add_card`, so
   the least such k exists and is attained
   (`totalColorable_totalChromaticNumber`).
-/

import Mathlib

namespace SimpleGraph

section Defs

variable {V : Type*} [Fintype V] [DecidableEq V] (G : SimpleGraph V) [DecidableRel G.Adj]

/-! ### Adjacent edges -/

/-- Two edges are adjacent when they are distinct and share an endpoint. -/
def EdgesAdj (e₁ e₂ : Sym2 V) : Prop :=
  e₁ ≠ e₂ ∧ ∃ v : V, v ∈ e₁ ∧ v ∈ e₂

instance (e₁ e₂ : Sym2 V) : Decidable (EdgesAdj e₁ e₂) := by
  unfold EdgesAdj
  infer_instance

/-! ### Total colorings -/

/-- A total coloring of `G` with colors from `Fin k`: a vertex coloring `c`
together with an edge coloring `f` (on the edges of `G`) such that adjacent
vertices, adjacent edges, and every edge together with each of its endpoints
receive different colors. -/
def IsTotalColoring {k : ℕ} (c : V → Fin k) (f : G.edgeFinset → Fin k) : Prop :=
  (∀ a b : V, G.Adj a b → c a ≠ c b) ∧
    (∀ e₁ e₂ : G.edgeFinset, EdgesAdj e₁.val e₂.val → f e₁ ≠ f e₂) ∧
      (∀ v : V, ∀ e : G.edgeFinset, v ∈ e.val → c v ≠ f e)

instance {k : ℕ} (c : V → Fin k) (f : G.edgeFinset → Fin k) :
    Decidable (G.IsTotalColoring c f) := by
  unfold IsTotalColoring
  infer_instance

/-- `G` admits a total coloring with `k` colors. -/
def TotalColorable (k : ℕ) : Prop :=
  ∃ (c : V → Fin k) (f : G.edgeFinset → Fin k), G.IsTotalColoring c f

instance (k : ℕ) : Decidable (G.TotalColorable k) := by
  unfold TotalColorable
  infer_instance

-- Every finite graph is total colorable: give all vertices distinct colors
-- and all edges distinct colors from a disjoint palette. This backs the
-- existence of the total chromatic number.
omit [DecidableEq V] in
theorem totalColorable_add_card :
    G.TotalColorable (Fintype.card G.edgeFinset + Fintype.card V) := by
  refine ⟨fun v => Fin.natAdd _ (Fintype.equivFin V v),
    fun e => Fin.castAdd _ (Fintype.equivFin G.edgeFinset e), ?_, ?_, ?_⟩
  · intro a b hab heq
    apply G.ne_of_adj hab
    apply (Fintype.equivFin V).injective
    apply Fin.eq_of_val_eq
    have hval := congrArg Fin.val heq
    simp only [Fin.val_natAdd] at hval
    omega
  · intro e₁ e₂ hadj heq
    apply hadj.1
    apply congrArg Subtype.val
    apply (Fintype.equivFin G.edgeFinset).injective
    apply Fin.eq_of_val_eq
    have hval := congrArg Fin.val heq
    simp only [Fin.val_castAdd] at hval
    exact hval
  · intro v e _hv heq
    have hval := congrArg Fin.val heq
    simp only [Fin.val_natAdd, Fin.val_castAdd] at hval
    have hlt : (Fintype.equivFin G.edgeFinset e).val < Fintype.card G.edgeFinset :=
      (Fintype.equivFin G.edgeFinset e).isLt
    omega

/-- The total chromatic number χ''(G): the least number of colors in a total
coloring of `G`. Not meant to be kernel-computed; use the API lemmas below. -/
noncomputable def totalChromaticNumber : ℕ :=
  Nat.find ⟨_, G.totalColorable_add_card⟩

/-- χ''(G) colors always suffice: the minimum is attained. -/
theorem totalColorable_totalChromaticNumber : G.TotalColorable G.totalChromaticNumber :=
  Nat.find_spec _

/-- Any total coloring with `k` colors gives the upper bound χ''(G) ≤ k. -/
theorem totalChromaticNumber_le {k : ℕ} (h : G.TotalColorable k) :
    G.totalChromaticNumber ≤ k :=
  Nat.find_le h

/-- If every number of colors with which `G` is total colorable is at least
`m`, then χ''(G) ≥ m. -/
theorem le_totalChromaticNumber {m : ℕ} (h : ∀ k : ℕ, G.TotalColorable k → m ≤ k) :
    m ≤ G.totalChromaticNumber :=
  h _ G.totalColorable_totalChromaticNumber

-- Total colorability is monotone in the number of colors.
omit [DecidableEq V] in
theorem TotalColorable.mono {k l : ℕ} (h : G.TotalColorable k) (hkl : k ≤ l) :
    G.TotalColorable l := by
  obtain ⟨c, f, h1, h2, h3⟩ := h
  refine ⟨fun v => Fin.castLE hkl (c v), fun e => Fin.castLE hkl (f e), ?_, ?_, ?_⟩
  · intro a b hab heq
    exact h1 a b hab (Fin.castLE_injective hkl heq)
  · intro e₁ e₂ hadj heq
    exact h2 e₁ e₂ hadj (Fin.castLE_injective hkl heq)
  · intro v e hv heq
    exact h3 v e hv (Fin.castLE_injective hkl heq)

/-- The Total Coloring Conjecture bound for one graph: χ''(G) ≤ Δ(G) + 2,
where Δ(G) is mathlib's `SimpleGraph.maxDegree` (the maximum vertex degree,
`0` on the empty graph). -/
def TotalColorBound : Prop :=
  G.totalChromaticNumber ≤ G.maxDegree + 2

end Defs

end SimpleGraph

namespace TotalColoringConjecture

/-! ### Concrete instances -/

/-- The star K_{1,3} on `Fin 4`: vertex `0` is the center, adjacent to the
three leaves; the leaves are pairwise non-adjacent. -/
def starK13 : SimpleGraph (Fin 4) where
  Adj a b := a ≠ b ∧ (a = 0 ∨ b = 0)
  symm := ⟨fun _a _b h => ⟨h.1.symm, h.2.symm⟩⟩
  loopless := ⟨fun _a h => h.1 rfl⟩

instance : DecidableRel starK13.Adj :=
  fun a b => inferInstanceAs (Decidable (a ≠ b ∧ (a = 0 ∨ b = 0)))

/-- The complete bipartite graph K_{2,2} on `Fin 4`: the parts are {0, 1} and
{2, 3}. As a graph this is the 4-cycle. -/
def k22 : SimpleGraph (Fin 4) where
  Adj a b := (a.val < 2 ∧ 2 ≤ b.val) ∨ (b.val < 2 ∧ 2 ≤ a.val)
  symm := ⟨fun _a _b h => h.symm⟩
  loopless := ⟨fun _a h => by rcases h with ⟨h1, h2⟩ | ⟨h1, h2⟩ <;> omega⟩

instance : DecidableRel k22.Adj :=
  fun a b => inferInstanceAs (Decidable ((a.val < 2 ∧ 2 ≤ b.val) ∨ (b.val < 2 ∧ 2 ≤ a.val)))

/- The kernel recursion limit is raised so that `decide` can evaluate total
colorability on small graphs (their function enumeration
exceeds the default limit). This line is part of the fixed zone. -/
set_option maxRecDepth 8192

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

/-! ## Slot zone: the conjecture and its negation -/

-- @[slot main]
/-- **The Total Coloring Conjecture** (Behzad 1965; Vizing 1968): every
finite simple graph G satisfies χ''(G) ≤ Δ(G) + 2 — vertices and edges
together can be colored with at most Δ(G) + 2 colors so that adjacent
vertices, adjacent edges, and each edge with its endpoints all differ. -/
theorem conj :
    ∀ {V : Type*} [Fintype V] [DecidableEq V] (G : SimpleGraph V) [DecidableRel G.Adj],
      G.TotalColorBound := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

-- @[slot main]
/-- The negation of the Total Coloring Conjecture: some finite simple graph
G has χ''(G) > Δ(G) + 2. -/
theorem refuted :
    ¬∀ {V : Type*} [Fintype V] [DecidableEq V] (G : SimpleGraph V) [DecidableRel G.Adj],
        G.TotalColorBound := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

end TotalColoringConjecture
