/-
Statement layer for Tuza's conjecture (Tuza 1981, *Finite and Infinite Sets*,
Proc. Colloq. Math. Soc. János Bolyai 37, North-Holland 1984, p. 888):
every finite graph G satisfies τ(G) ≤ 2·ν(G), where ν(G) is the maximum number
of pairwise edge-disjoint triangles of G (the triangle edge packing number)
and τ(G) is the minimum size of an edge set meeting every triangle of G (the
triangle edge cover number). The constant 2 is tight: graphs all of whose
blocks are K₄ attain equality.

This file is the task's definition zone plus slot zone:
- The definition zone defines triangles (as mathlib 3-cliques), the triangle
  edge cover number τ and the triangle edge packing number ν for finite
  graphs, and proves the basic API lemmas about them. The definitions live in
  the `SimpleGraph` namespace so that `G.triangleCoverNumber` etc. work as dot
  notation. Both numbers are computable: small instances can be verified by
  `decide` (see `tests/reference/small-examples.md` of the packaged task).
- The slot zone states the conjecture (`conj`) and its negation (`refuted`).
  Both proof bodies are left blank.

Fidelity notes (see `tests/reference/concept-ledger.md` of the packaged task):
1. Triangles are mathlib 3-cliques (`SimpleGraph.cliqueFinset 3`): vertex sets
   of size 3, pairwise adjacent. This is the standard reading of "triangle" in
   the Tuza literature; covering and packing speak about the three edges of
   each triangle (`triangleEdges`).
2. τ is the minimum cardinality over *all* edge subsets meeting every
   triangle; ν is the maximum cardinality over *all* families of triangles
   whose edge sets are pairwise disjoint. Both extrema range over full
   powersets (of the edge set / of the triangle set), so no choice is
   involved and both numbers are computable (`Finset.min'` / `Finset.max'`).
-/

import Mathlib

namespace SimpleGraph

section Defs

variable {V : Type*} [Fintype V] [DecidableEq V] (G : SimpleGraph V)
  [DecidableRel G.Adj]

/-! ### Triangles and their edges -/

/-- The triangles of `G`: its 3-cliques, represented as vertex finsets. -/
def triangleFinset : Finset (Finset V) :=
  G.cliqueFinset 3

theorem mem_triangleFinset {s : Finset V} :
    s ∈ G.triangleFinset ↔ G.IsNClique 3 s :=
  mem_cliqueFinset_iff

/-- The edges spanned by a vertex set `s`: the non-diagonal unordered pairs of
vertices of `s`. For a triangle these are its three edges. -/
def triangleEdges (s : Finset V) : Finset (Sym2 V) :=
  s.sym2.filter (¬ ·.IsDiag)

omit [Fintype V] in
theorem mem_triangleEdges {s : Finset V} {e : Sym2 V} :
    e ∈ triangleEdges s ↔ e ∈ s.sym2 ∧ ¬e.IsDiag :=
  Finset.mem_filter

/-- Every edge of a triangle of `G` is an edge of `G`. -/
theorem triangleEdges_subset_edgeFinset {s : Finset V} (hs : s ∈ G.triangleFinset) :
    triangleEdges s ⊆ G.edgeFinset := by
  intro e he
  rw [mem_triangleEdges] at he
  obtain ⟨hes, hnd⟩ := he
  induction e using Quot.inductionOn with
  | h p =>
    obtain ⟨a, b⟩ := p
    rw [Finset.mk_mem_sym2_iff] at hes
    rw [Sym2.mk_isDiag_iff] at hnd
    exact G.mem_edgeFinset.mpr
      (G.mem_edgeSet.mpr ((G.mem_triangleFinset.mp hs).isClique hes.1 hes.2 hnd))

/-- Every triangle has at least one edge (in fact three). -/
theorem triangleEdges_nonempty {s : Finset V} (hs : s ∈ G.triangleFinset) :
    (triangleEdges s).Nonempty := by
  have hcard : s.card = 3 := (G.mem_triangleFinset.mp hs).card_eq
  obtain ⟨a, ha, b, hb, hab⟩ := Finset.one_lt_card.mp (by omega : 1 < s.card)
  refine ⟨s(a, b), ?_⟩
  rw [mem_triangleEdges, Finset.mk_mem_sym2_iff, Sym2.mk_isDiag_iff]
  exact ⟨⟨ha, hb⟩, hab⟩

/-! ### Triangle edge covers and the cover number τ -/

/-- A triangle edge cover of `G`: a set of edges of `G` meeting every
triangle. -/
def IsTriangleCover (F : Finset (Sym2 V)) : Prop :=
  F ⊆ G.edgeFinset ∧ ∀ s ∈ G.triangleFinset, ¬Disjoint (triangleEdges s) F

instance (F : Finset (Sym2 V)) : Decidable (G.IsTriangleCover F) := by
  unfold IsTriangleCover
  infer_instance

/-- All triangle edge covers of `G`. -/
def coverCandidates : Finset (Finset (Sym2 V)) :=
  G.edgeFinset.powerset.filter G.IsTriangleCover

/-- The full edge set is a triangle edge cover. -/
theorem isTriangleCover_edgeFinset : G.IsTriangleCover G.edgeFinset := by
  refine ⟨Finset.Subset.refl _, fun s hs => ?_⟩
  obtain ⟨e, he⟩ := G.triangleEdges_nonempty hs
  rw [Finset.not_disjoint_iff]
  exact ⟨e, he, G.triangleEdges_subset_edgeFinset hs he⟩

theorem edgeFinset_mem_coverCandidates : G.edgeFinset ∈ G.coverCandidates := by
  rw [coverCandidates, Finset.mem_filter, Finset.mem_powerset]
  exact ⟨Finset.Subset.refl _, G.isTriangleCover_edgeFinset⟩

/-- τ(G): the triangle edge cover number — the minimum size of an edge set
meeting every triangle of `G`. -/
def triangleCoverNumber : ℕ :=
  (G.coverCandidates.image Finset.card).min'
    ⟨G.edgeFinset.card,
      Finset.mem_image.mpr ⟨G.edgeFinset, G.edgeFinset_mem_coverCandidates, rfl⟩⟩

/-- Any triangle edge cover gives an upper bound on τ. -/
theorem triangleCoverNumber_le {F : Finset (Sym2 V)} (hF : G.IsTriangleCover F) :
    G.triangleCoverNumber ≤ F.card := by
  show (G.coverCandidates.image Finset.card).min' _ ≤ F.card
  apply Finset.min'_le
  rw [Finset.mem_image]
  exact ⟨F, by
    rw [coverCandidates, Finset.mem_filter, Finset.mem_powerset]
    exact ⟨hF.1, hF⟩, rfl⟩

/-- A lower bound on all triangle edge covers gives a lower bound on τ. -/
theorem le_triangleCoverNumber {k : ℕ}
    (h : ∀ F : Finset (Sym2 V), G.IsTriangleCover F → k ≤ F.card) :
    k ≤ G.triangleCoverNumber := by
  show k ≤ (G.coverCandidates.image Finset.card).min' _
  apply Finset.le_min'
  intro y hy
  rw [Finset.mem_image] at hy
  obtain ⟨F, hF, rfl⟩ := hy
  rw [coverCandidates, Finset.mem_filter] at hF
  exact h F hF.2

/-- τ is attained: some triangle edge cover has exactly τ edges. -/
theorem exists_isTriangleCover_card_eq :
    ∃ F : Finset (Sym2 V), G.IsTriangleCover F ∧ F.card = G.triangleCoverNumber := by
  have h := Finset.min'_mem _
    ⟨G.edgeFinset.card,
      Finset.mem_image.mpr ⟨G.edgeFinset, G.edgeFinset_mem_coverCandidates, rfl⟩⟩
  rw [Finset.mem_image] at h
  obtain ⟨F, hF, hcard⟩ := h
  rw [coverCandidates, Finset.mem_filter] at hF
  exact ⟨F, hF.2, hcard⟩

/-- τ(G) is at most the number of edges of G. -/
theorem triangleCoverNumber_le_card : G.triangleCoverNumber ≤ G.edgeFinset.card :=
  G.triangleCoverNumber_le G.isTriangleCover_edgeFinset

/-! ### Triangle packings and the packing number ν -/

/-- A triangle packing of `G`: a family of triangles of `G` whose edge sets
are pairwise disjoint. -/
def IsTrianglePacking (T : Finset (Finset V)) : Prop :=
  T ⊆ G.triangleFinset ∧
    ∀ s ∈ T, ∀ t ∈ T, s ≠ t → Disjoint (triangleEdges s) (triangleEdges t)

instance (T : Finset (Finset V)) : Decidable (G.IsTrianglePacking T) := by
  unfold IsTrianglePacking
  infer_instance

/-- All triangle packings of `G`. -/
def packingCandidates : Finset (Finset (Finset V)) :=
  G.triangleFinset.powerset.filter G.IsTrianglePacking

/-- The empty family is a triangle packing. -/
theorem isTrianglePacking_empty : G.IsTrianglePacking ∅ := by
  refine ⟨Finset.empty_subset _, fun s hs => ?_⟩
  exact (Finset.notMem_empty s hs).elim

theorem empty_mem_packingCandidates : ∅ ∈ G.packingCandidates := by
  rw [packingCandidates, Finset.mem_filter, Finset.mem_powerset]
  exact ⟨Finset.empty_subset _, G.isTrianglePacking_empty⟩

/-- ν(G): the triangle edge packing number — the maximum size of a family of
pairwise edge-disjoint triangles of `G`. -/
def trianglePackingNumber : ℕ :=
  (G.packingCandidates.image Finset.card).max'
    ⟨0, Finset.mem_image.mpr ⟨∅, G.empty_mem_packingCandidates, Finset.card_empty⟩⟩

/-- Any triangle packing gives a lower bound on ν. -/
theorem le_trianglePackingNumber {T : Finset (Finset V)} (hT : G.IsTrianglePacking T) :
    T.card ≤ G.trianglePackingNumber := by
  show T.card ≤ (G.packingCandidates.image Finset.card).max' _
  apply Finset.le_max'
  rw [Finset.mem_image]
  exact ⟨T, by
    rw [packingCandidates, Finset.mem_filter, Finset.mem_powerset]
    exact ⟨hT.1, hT⟩, rfl⟩

/-- An upper bound on all triangle packings gives an upper bound on ν. -/
theorem trianglePackingNumber_le {k : ℕ}
    (h : ∀ T : Finset (Finset V), G.IsTrianglePacking T → T.card ≤ k) :
    G.trianglePackingNumber ≤ k := by
  show (G.packingCandidates.image Finset.card).max' _ ≤ k
  apply Finset.max'_le
  intro y hy
  rw [Finset.mem_image] at hy
  obtain ⟨T, hT, rfl⟩ := hy
  rw [packingCandidates, Finset.mem_filter] at hT
  exact h T hT.2

/-- ν is attained: some triangle packing has exactly ν triangles. -/
theorem exists_isTrianglePacking_card_eq :
    ∃ T : Finset (Finset V), G.IsTrianglePacking T ∧ T.card = G.trianglePackingNumber := by
  have h := Finset.max'_mem _
    ⟨0, Finset.mem_image.mpr ⟨∅, G.empty_mem_packingCandidates, Finset.card_empty⟩⟩
  rw [Finset.mem_image] at h
  obtain ⟨T, hT, hcard⟩ := h
  rw [packingCandidates, Finset.mem_filter] at hT
  exact ⟨T, hT.2, hcard⟩

/-! ### The Tuza bound -/

/-- The Tuza bound for `G`: τ(G) ≤ 2·ν(G). Tuza's conjecture states that this
holds for every finite graph. -/
def TuzaBound : Prop :=
  G.triangleCoverNumber ≤ 2 * G.trianglePackingNumber

end Defs

end SimpleGraph

namespace TuzaConjecture

/-! ### Concrete instances -/

/-- Two vertex-disjoint triangles on `Fin 6`: the components {0,1,2} and
{3,4,5}. -/
def twoTriangles : SimpleGraph (Fin 6) where
  Adj a b := a.val / 3 = b.val / 3 ∧ a ≠ b
  symm := ⟨fun _a _b h => ⟨h.1.symm, h.2.symm⟩⟩
  loopless := ⟨fun _a h => h.2 rfl⟩

instance : DecidableRel twoTriangles.Adj :=
  fun a b => inferInstanceAs (Decidable (a.val / 3 = b.val / 3 ∧ a ≠ b))

/- The kernel recursion limit is raised so that `decide` can evaluate the
cover/packing numbers on small graphs (their powerset search
exceeds the default limit). This line is part of the fixed zone. -/
set_option maxRecDepth 8192

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

/-! ## Slot zone: the conjecture and its negation -/

-- @[slot main]
/-- **Tuza's conjecture** (1981): every finite graph G satisfies τ(G) ≤ 2·ν(G)
— the triangle edge cover number is at most twice the triangle edge packing
number. -/
theorem conj :
    ∀ {V : Type*} [Fintype V] [DecidableEq V] (G : SimpleGraph V) [DecidableRel G.Adj],
      G.TuzaBound := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

-- @[slot main]
/-- The negation of Tuza's conjecture: some finite graph G has
τ(G) > 2·ν(G). -/
theorem refuted :
    ¬∀ {V : Type*} [Fintype V] [DecidableEq V] (G : SimpleGraph V) [DecidableRel G.Adj],
        G.TuzaBound := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

end TuzaConjecture
