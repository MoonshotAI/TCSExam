/-
Statement layer for Ryser's conjecture (attributed to Herbert Ryser, c. 1970;
standard reference: DeBiasio–Kamel–McCourt–Sheats, *Generalizations and
strengthenings of Ryser's conjecture*, Electronic Journal of Combinatorics
2021): for every integer r ≥ 2 and every r-partite r-uniform hypergraph H,
the vertex cover number τ(H) (minimum size of a vertex set meeting every
edge) and the matching number ν(H) (maximum number of pairwise disjoint
edges) satisfy τ(H) ≤ (r−1)·ν(H). For r = 2 this is Kőnig's theorem
(τ = ν on bipartite graphs); r = 3 was proved by Aharoni (2001); the
conjecture is open for all r ≥ 4 (DeBiasio–Girão–Haxell–Stein 2024,
arXiv:2409.18250). The constant r−1 cannot be lowered: the truncated
projective plane of order r−1 (when it exists) is intersecting (ν = 1) with
τ = r−1.

This file is the task's definition zone plus slot zone:
- The definition zone defines r-partite r-uniform hypergraphs (as finsets of
  transversals `Fin r → V`, the parts being `r` disjoint copies of one type
  `V`), vertex covers and the cover number τ, matchings and the matching
  number ν, and proves the basic API lemmas about them. Both numbers are
  computable: small instances can be verified by `decide` (see
  `tests/reference/small-examples.md` of the packaged task).
- The slot zone states the conjecture (`conj`) and its negation (`refuted`).
  Both proof bodies are left blank.

Fidelity notes (see `tests/reference/concept-ledger.md` of the packaged task):
1. The parts of an r-partite hypergraph are modelled as `r` disjoint copies
   of a single vertex type `V`: vertex `(i, v) : Fin r × V` is vertex `v` of
   part `i`, and an edge is the function `e : Fin r → V` recording its vertex
   in each part. Every r-partite r-uniform hypergraph in the literature is
   isomorphic to one of this form (take `V` to be the disjoint union of the
   parts), and τ, ν are isomorphism-invariant, so quantifying over this form
   loses nothing.
2. τ is the minimum cardinality over *all* vertex subsets meeting every edge;
   ν is the maximum cardinality over *all* families of pairwise disjoint
   edges. Both extrema range over full powersets (of the vertex set / of the
   edge set), so no choice is involved and both numbers are computable
   (`Finset.min'` / `Finset.max'`).
-/

import Mathlib

namespace RyserConjecture

/-- An `r`-partite `r`-uniform hypergraph on a vertex type `V`: the parts are
`r` disjoint copies of `V` (vertex `(i, v) : Fin r × V` is vertex `v` of part
`i`), and each edge contains exactly one vertex from each part, recorded as
the function `e : Fin r → V` picking vertex `e i` in part `i`. Two edges share
a vertex iff they agree in some part. -/
structure RPartiteHypergraph (r : ℕ) (V : Type*) [Fintype V] [DecidableEq V] where
  /-- The edge set: a finset of transversals `Fin r → V`. -/
  edges : Finset (Fin r → V)

namespace RPartiteHypergraph

section Defs

variable {r : ℕ} {V : Type*} [Fintype V] [DecidableEq V] (H : RPartiteHypergraph r V)

/-! ### Vertex covers and the cover number τ -/

/-- A vertex cover of `H`: a set of vertices meeting every edge. Edge `e`
meets `C` when some part-`i` vertex `(i, e i)` of `e` lies in `C`. -/
def IsCover (C : Finset (Fin r × V)) : Prop :=
  ∀ e ∈ H.edges, ∃ i : Fin r, (i, e i) ∈ C

instance (C : Finset (Fin r × V)) : Decidable (H.IsCover C) := by
  unfold IsCover
  infer_instance

/-- All vertex covers of `H`. -/
def coverCandidates : Finset (Finset (Fin r × V)) :=
  (Finset.univ : Finset (Fin r × V)).powerset.filter H.IsCover

/-- The full vertex set is a cover (needs `r ≥ 1`). -/
theorem isCover_univ [NeZero r] : H.IsCover Finset.univ := by
  intro e _
  exact ⟨⟨0, Nat.pos_of_ne_zero (NeZero.ne r)⟩, Finset.mem_univ _⟩

theorem univ_mem_coverCandidates [NeZero r] :
    (Finset.univ : Finset (Fin r × V)) ∈ H.coverCandidates := by
  rw [coverCandidates, Finset.mem_filter, Finset.mem_powerset]
  exact ⟨Finset.subset_univ _, H.isCover_univ⟩

/-- τ(H): the vertex cover number — the minimum size of a vertex set meeting
every edge of `H`. -/
def coverNumber [NeZero r] : ℕ :=
  (H.coverCandidates.image Finset.card).min'
    ⟨(Finset.univ : Finset (Fin r × V)).card,
      Finset.mem_image.mpr ⟨_, H.univ_mem_coverCandidates, rfl⟩⟩

/-- Any vertex cover gives an upper bound on τ. -/
theorem coverNumber_le [NeZero r] {C : Finset (Fin r × V)} (hC : H.IsCover C) :
    H.coverNumber ≤ C.card := by
  show (H.coverCandidates.image Finset.card).min' _ ≤ C.card
  apply Finset.min'_le
  rw [Finset.mem_image]
  exact ⟨C, by
    rw [coverCandidates, Finset.mem_filter, Finset.mem_powerset]
    exact ⟨Finset.subset_univ _, hC⟩, rfl⟩

/-- A lower bound on all vertex covers gives a lower bound on τ. -/
theorem le_coverNumber [NeZero r] {k : ℕ}
    (h : ∀ C : Finset (Fin r × V), H.IsCover C → k ≤ C.card) :
    k ≤ H.coverNumber := by
  show k ≤ (H.coverCandidates.image Finset.card).min' _
  apply Finset.le_min'
  intro y hy
  rw [Finset.mem_image] at hy
  obtain ⟨C, hC, rfl⟩ := hy
  rw [coverCandidates, Finset.mem_filter] at hC
  exact h C hC.2

/-- τ is attained: some vertex cover has exactly τ vertices. -/
theorem exists_isCover_card_eq [NeZero r] :
    ∃ C : Finset (Fin r × V), H.IsCover C ∧ C.card = H.coverNumber := by
  have h := Finset.min'_mem _
    ⟨(Finset.univ : Finset (Fin r × V)).card,
      Finset.mem_image.mpr ⟨_, H.univ_mem_coverCandidates, rfl⟩⟩
  rw [Finset.mem_image] at h
  obtain ⟨C, hC, hcard⟩ := h
  rw [coverCandidates, Finset.mem_filter] at hC
  exact ⟨C, hC.2, hcard⟩

/-- τ(H) is at most the number of vertices. -/
theorem coverNumber_le_card [NeZero r] :
    H.coverNumber ≤ (Finset.univ : Finset (Fin r × V)).card :=
  H.coverNumber_le H.isCover_univ

/-! ### Matchings and the matching number ν -/

/-- A matching of `H`: a family of pairwise disjoint edges — distinct edges
share no vertex, i.e. differ in every part. -/
def IsMatching (M : Finset (Fin r → V)) : Prop :=
  M ⊆ H.edges ∧ ∀ e ∈ M, ∀ e' ∈ M, e ≠ e' → ∀ i : Fin r, e i ≠ e' i

instance (M : Finset (Fin r → V)) : Decidable (H.IsMatching M) := by
  unfold IsMatching
  infer_instance

/-- All matchings of `H`. -/
def matchingCandidates : Finset (Finset (Fin r → V)) :=
  H.edges.powerset.filter H.IsMatching

/-- The empty family is a matching. -/
theorem isMatching_empty : H.IsMatching ∅ := by
  refine ⟨Finset.empty_subset _, fun e he => ?_⟩
  exact (Finset.notMem_empty e he).elim

theorem empty_mem_matchingCandidates : ∅ ∈ H.matchingCandidates := by
  rw [matchingCandidates, Finset.mem_filter, Finset.mem_powerset]
  exact ⟨Finset.empty_subset _, H.isMatching_empty⟩

/-- ν(H): the matching number — the maximum size of a family of pairwise
disjoint edges of `H`. -/
def matchingNumber : ℕ :=
  (H.matchingCandidates.image Finset.card).max'
    ⟨0, Finset.mem_image.mpr ⟨∅, H.empty_mem_matchingCandidates, Finset.card_empty⟩⟩

/-- Any matching gives a lower bound on ν. -/
theorem le_matchingNumber {M : Finset (Fin r → V)} (hM : H.IsMatching M) :
    M.card ≤ H.matchingNumber := by
  show M.card ≤ (H.matchingCandidates.image Finset.card).max' _
  apply Finset.le_max'
  rw [Finset.mem_image]
  exact ⟨M, by
    rw [matchingCandidates, Finset.mem_filter, Finset.mem_powerset]
    exact ⟨hM.1, hM⟩, rfl⟩

/-- An upper bound on all matchings gives an upper bound on ν. -/
theorem matchingNumber_le {k : ℕ}
    (h : ∀ M : Finset (Fin r → V), H.IsMatching M → M.card ≤ k) :
    H.matchingNumber ≤ k := by
  show (H.matchingCandidates.image Finset.card).max' _ ≤ k
  apply Finset.max'_le
  intro y hy
  rw [Finset.mem_image] at hy
  obtain ⟨M, hM, rfl⟩ := hy
  rw [matchingCandidates, Finset.mem_filter] at hM
  exact h M hM.2

/-- ν is attained: some matching has exactly ν edges. -/
theorem exists_isMatching_card_eq :
    ∃ M : Finset (Fin r → V), H.IsMatching M ∧ M.card = H.matchingNumber := by
  have h := Finset.max'_mem _
    ⟨0, Finset.mem_image.mpr ⟨∅, H.empty_mem_matchingCandidates, Finset.card_empty⟩⟩
  rw [Finset.mem_image] at h
  obtain ⟨M, hM, hcard⟩ := h
  rw [matchingCandidates, Finset.mem_filter] at hM
  exact ⟨M, hM.2, hcard⟩

/-! ### The Ryser bound -/

/-- The Ryser bound for `H`: τ(H) ≤ (r−1)·ν(H). Ryser's conjecture states
that this holds for every r-partite r-uniform hypergraph with r ≥ 2. -/
def RyserBound [NeZero r] : Prop :=
  H.coverNumber ≤ (r - 1) * H.matchingNumber

end Defs

end RPartiteHypergraph

/-! ### Concrete instances -/

/-- The König witness: a 2-partite 2-uniform hypergraph (i.e. a bipartite
graph) on two copies of `Fin 3`, with edges a₀b₀, a₀b₁, a₁b₁, a₁b₂, where aᵢ
denotes vertex `i` of part 0 and bⱼ vertex `j` of part 1. -/
def konigWitness : RPartiteHypergraph 2 (Fin 3) where
  edges := {![0, 0], ![0, 1], ![1, 1], ![1, 2]}

/-- The Pasch configuration (the truncated Fano plane): a 3-partite 3-uniform
intersecting hypergraph on three copies of `Fin 2`, edges
{(x, y, x+y mod 2) : x, y ∈ F₂} — four triples on six vertices, pairwise
intersecting, with no single vertex meeting all four. -/
def paschConfig : RPartiteHypergraph 3 (Fin 2) where
  edges := {![0, 0, 0], ![0, 1, 1], ![1, 0, 1], ![1, 1, 0]}

/-- The truncated projective plane of order 3: a 4-partite 4-uniform
intersecting hypergraph on four copies of `Fin 3`, edges
{(x, y, x+y, x+2y) : x, y ∈ F₃} — nine 4-tuples on twelve vertices, pairwise
intersecting (any two distinct tuples agree in exactly one part), with no two
vertices meeting all nine. -/
def truncatedPG3 : RPartiteHypergraph 4 (Fin 3) where
  edges := {![0, 0, 0, 0], ![1, 0, 1, 1], ![2, 0, 2, 2], ![0, 1, 1, 2],
            ![0, 2, 2, 1], ![2, 1, 0, 1], ![1, 2, 0, 2], ![1, 1, 2, 0],
            ![2, 2, 1, 0]}

/- The kernel recursion limit and the elaboration heartbeat budget are raised
so that `decide` can evaluate the cover/matching numbers on small
hypergraphs: the powerset search behind τ (2^12 cover candidates on the
truncated PG(2,3) instance) and ν, and the pairwise intersection checks,
exceed the default limits. These lines are part of the fixed zone. -/
set_option maxRecDepth 1000000
set_option maxHeartbeats 16000000

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

/-! ## Slot zone: the conjecture and its negation -/

-- @[slot main]
/-- **Ryser's conjecture** (c. 1970): for every integer r ≥ 2 and every
r-partite r-uniform hypergraph H, the vertex cover number is at most r−1
times the matching number: τ(H) ≤ (r−1)·ν(H). -/
theorem conj :
    ∀ (r : ℕ) [NeZero r] (_ : 2 ≤ r) (V : Type*) [Fintype V] [DecidableEq V]
      (H : RPartiteHypergraph r V), H.RyserBound := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

-- @[slot main]
/-- The negation of Ryser's conjecture: for some integer r ≥ 2 there is an
r-partite r-uniform hypergraph H with τ(H) > (r−1)·ν(H). -/
theorem refuted :
    ¬∀ (r : ℕ) [NeZero r] (_ : 2 ≤ r) (V : Type*) [Fintype V] [DecidableEq V]
        (H : RPartiteHypergraph r V), H.RyserBound := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

end RyserConjecture
