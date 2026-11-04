/-
Statement layer for the GNRS conjecture (Gupta–Newman–Rabinovich–Sinclair,
FOCS 1999; journal version *Cuts, trees and ℓ₁-embeddings of graphs*,
Combinatorica 24(2): 233–269, 2004): is there a universal constant C such
that the shortest-path metric of every planar graph embeds into ℓ₁ with
distortion at most C?

This file is the task's definition zone plus slot zone:
- The definition zone defines a computable shortest-path distance `spDist`
  (with a fully proved bridge `spDist_eq_dist` to mathlib's
  `SimpleGraph.dist`), the ℓ₁ distance on `Fin k → ℝ`, the embedding
  predicate `EmbedsIntoL1`, graph minors via branch sets, and planarity in
  Wagner form (no K₅ minor, no K₃,₃ minor). API lemmas are fully proved.
- The slot zone states the conjecture (`conj`) and its negation (`refuted`).
  Both proof bodies are left blank.

Fidelity notes (see `tests/reference/concept-ledger.md` of the packaged task):
1. Planarity is defined in Wagner form: no K₅ minor and no K₃,₃ minor
   (branch-set minors). By Wagner's theorem (1937) this is equivalent to the
   topological definition of planarity; the equivalence is cited, not proved.
2. `spDist` is computable (minimum walk length below the vertex count, `0`
   when no walk exists — matching `SimpleGraph.dist`'s convention); on
   reachable pairs it coincides with `SimpleGraph.dist` (`spDist_eq_dist`),
   hence on connected graphs it is the literature's shortest-path metric.
3. ℓ₁ targets are finite-dimensional: `Fin k → ℝ` with the sum-of-|·|
   distance. For a finite metric, embedding into ℓ₁ and embedding into some
   finite-dimensional ℓ₁ are equivalent (cut cone; see ledger).
4. Distortion uses the non-contracting normalization `d ≤ ‖·‖₁ ≤ C·d`; the
   literature's `C/c` ratio convention is equivalent by rescaling.
-/

import Mathlib

namespace SimpleGraph

section Defs

variable {V : Type*} [Fintype V] [DecidableEq V] (G : SimpleGraph V)
  [DecidableRel G.Adj]

/-! ### A computable shortest-path distance -/

/-- `G.WalkSeq u v n`: there is a walk of length `n` from `u` to `v` in `G`,
witnessed by a vertex sequence `f 0, f 1, …, f n`. This is a finite search
object, decidable on finite graphs. -/
def WalkSeq (u v : V) (n : ℕ) : Prop :=
  ∃ f : Fin (n + 1) → V,
    f 0 = u ∧ f (Fin.last n) = v ∧ ∀ i : Fin n, G.Adj (f i.castSucc) (f i.succ)

instance (u v : V) (n : ℕ) : Decidable (G.WalkSeq u v n) := by
  unfold WalkSeq
  infer_instance

omit [Fintype V] [DecidableEq V] [DecidableRel G.Adj] in
/-- A walk gives a vertex sequence. -/
theorem walkSeq_of_walk {u v : V} (w : G.Walk u v) : G.WalkSeq u v w.length := by
  refine ⟨fun i => w.getVert i, ?_, ?_, ?_⟩
  · show w.getVert 0 = u
    exact w.getVert_zero
  · show w.getVert w.length = v
    exact w.getVert_length
  · intro i
    show G.Adj (w.getVert i.val) (w.getVert (i.val + 1))
    exact w.adj_getVert_succ i.isLt

omit [Fintype V] [DecidableEq V] [DecidableRel G.Adj] in
/-- A vertex sequence gives a walk. -/
theorem walk_of_walkSeq {u v : V} {n : ℕ} (h : G.WalkSeq u v n) :
    ∃ w : G.Walk u v, w.length = n := by
  induction n generalizing u v with
  | zero =>
    obtain ⟨f, h0, hn, -⟩ := h
    have huv : u = v := h0 ▸ hn
    subst huv
    exact ⟨Walk.nil, rfl⟩
  | succ n ih =>
    obtain ⟨f, h0, hn, hadj⟩ := h
    have he : G.Adj u (f (0 : Fin (n + 1)).succ) := by
      have h1 := hadj 0
      rwa [Fin.castSucc_zero, h0] at h1
    have hg : G.WalkSeq (f (0 : Fin (n + 1)).succ) v n := by
      refine ⟨fun i => f i.succ, rfl, ?_, fun i => ?_⟩
      · show f (Fin.last n).succ = v
        rw [Fin.succ_last]
        exact hn
      · show G.Adj (f (i.castSucc).succ) (f (i.succ).succ)
        rw [← Fin.castSucc_succ]
        exact hadj i.succ
    obtain ⟨w, hw⟩ := ih hg
    exact ⟨Walk.cons he w, by rw [Walk.length_cons, hw]⟩

omit [Fintype V] [DecidableEq V] [DecidableRel G.Adj] in
/-- Vertex sequences and walks of length `n` coincide. -/
theorem walkSeq_iff {u v : V} {n : ℕ} :
    G.WalkSeq u v n ↔ ∃ w : G.Walk u v, w.length = n :=
  ⟨fun h => G.walk_of_walkSeq h, fun ⟨w, hw⟩ => hw ▸ G.walkSeq_of_walk w⟩

/-- The shortest-path distance, computably: the minimum walk length below
`card V` (a shortest walk is a path, hence shorter than `card V`), and `0`
when no walk exists (matching `SimpleGraph.dist`'s convention). -/
def spDist (u v : V) : ℕ :=
  if h : ((Finset.range (Fintype.card V)).filter (G.WalkSeq u v)).Nonempty then
    ((Finset.range (Fintype.card V)).filter (G.WalkSeq u v)).min' h
  else 0

/-- Any walk sequence gives an upper bound on `spDist`. -/
theorem spDist_le_of_walkSeq {u v : V} {m : ℕ} (hm : m < Fintype.card V)
    (h : G.WalkSeq u v m) : G.spDist u v ≤ m := by
  unfold spDist
  rw [dif_pos ⟨m, Finset.mem_filter.mpr ⟨Finset.mem_range.mpr hm, h⟩⟩]
  exact Finset.min'_le _ _ (Finset.mem_filter.mpr ⟨Finset.mem_range.mpr hm, h⟩)

/-- `spDist` is attained by a walk sequence whenever one exists. -/
theorem walkSeq_of_spDist {u v : V}
    (h : ∃ m ∈ Finset.range (Fintype.card V), G.WalkSeq u v m) :
    G.WalkSeq u v (G.spDist u v) ∧ G.spDist u v < Fintype.card V := by
  obtain ⟨m, hm, hw⟩ := h
  have hne : ((Finset.range (Fintype.card V)).filter (G.WalkSeq u v)).Nonempty :=
    ⟨m, Finset.mem_filter.mpr ⟨hm, hw⟩⟩
  unfold spDist
  rw [dif_pos hne]
  have hmem := Finset.min'_mem _ hne
  rw [Finset.mem_filter] at hmem
  exact ⟨hmem.2, Finset.mem_range.mp hmem.1⟩

/-- The distance from a vertex to itself is `0`. -/
theorem spDist_self (u : V) : G.spDist u u = 0 := by
  haveI : Nonempty V := ⟨u⟩
  apply Nat.le_antisymm _ (Nat.zero_le _)
  apply G.spDist_le_of_walkSeq Fintype.card_pos
  exact ⟨fun _ => u, rfl, rfl, fun i => i.elim0⟩

/-- `spDist` is symmetric. -/
theorem spDist_symm (u v : V) : G.spDist u v = G.spDist v u := by
  have h : ∀ m : ℕ, G.WalkSeq u v m ↔ G.WalkSeq v u m := by
    intro m
    constructor
    · intro hw
      obtain ⟨w, rfl⟩ := G.walk_of_walkSeq hw
      rw [← Walk.length_reverse]
      exact G.walkSeq_of_walk w.reverse
    · intro hw
      obtain ⟨w, rfl⟩ := G.walk_of_walkSeq hw
      rw [← Walk.length_reverse]
      exact G.walkSeq_of_walk w.reverse
  unfold spDist
  simp only [h]

/-- On reachable pairs the computable distance agrees with mathlib's
`SimpleGraph.dist` — hence on connected graphs `spDist` is exactly the
shortest-path metric of the literature. -/
theorem spDist_eq_dist {u v : V} (h : G.Reachable u v) : G.spDist u v = G.dist u v := by
  obtain ⟨w, hw⟩ := h.exists_walk_length_eq_dist
  have hbypass : w.bypass.length ≤ w.length := w.length_bypass_le_length
  have hlt : w.bypass.length < Fintype.card V := w.bypass_isPath.length_lt
  have hmem : ∃ m ∈ Finset.range (Fintype.card V), G.WalkSeq u v m :=
    ⟨w.bypass.length, Finset.mem_range.mpr hlt, G.walkSeq_of_walk w.bypass⟩
  apply le_antisymm
  · calc G.spDist u v ≤ w.bypass.length :=
        G.spDist_le_of_walkSeq hlt (G.walkSeq_of_walk w.bypass)
      _ ≤ w.length := hbypass
      _ = G.dist u v := hw
  · obtain ⟨hwseq, -⟩ := G.walkSeq_of_spDist hmem
    obtain ⟨w', hw'⟩ := G.walk_of_walkSeq hwseq
    calc G.dist u v ≤ w'.length := G.dist_le w'
      _ = G.spDist u v := hw'

/-! ### ℓ₁ distances and the embedding predicate -/

/-- The ℓ₁ distance on `Fin k → ℝ`: the sum of coordinatewise absolute
differences. -/
def l1Dist {k : ℕ} (x y : Fin k → ℝ) : ℝ := ∑ i, |x i - y i|

/-- `G.EmbedsIntoL1 C`: the shortest-path metric of `G` embeds into a
finite-dimensional ℓ₁ space with distortion at most `C`, in the
non-contracting normalization: for some dimension `k` and map `φ`,
`d(u,v) ≤ ‖φ u − φ v‖₁ ≤ C · d(u,v)` for all vertices `u v`. -/
def EmbedsIntoL1 (C : ℝ) : Prop :=
  ∃ k : ℕ, ∃ φ : V → Fin k → ℝ, ∀ u v : V,
    (G.spDist u v : ℝ) ≤ l1Dist (φ u) (φ v) ∧
      l1Dist (φ u) (φ v) ≤ C * (G.spDist u v : ℝ)

/-! ### Minors and planarity -/

/-- `G.HasMinor H`: `H` is a minor of `G`, witnessed by branch sets —
pairwise disjoint nonempty connected vertex sets of `G`, one per vertex of
`H`, with an edge of `G` between the branch sets of every two adjacent
vertices of `H`. (Deleting vertices/edges and contracting edges in `G`
yields exactly the minors in this sense; cf. Diestel, *Graph Theory*,
ch. 1.7.) -/
def HasMinor {W : Type*} (H : SimpleGraph W) : Prop :=
  ∃ B : W → Set V,
    (∀ w, (B w).Nonempty) ∧
    (∀ w, (G.induce (B w)).Connected) ∧
    (∀ w₁ w₂, w₁ ≠ w₂ → Disjoint (B w₁) (B w₂)) ∧
    (∀ {w₁ w₂}, H.Adj w₁ w₂ → ∃ u ∈ B w₁, ∃ v ∈ B w₂, G.Adj u v)

/-- The complete bipartite graph K₃,₃ on `Fin 3 ⊕ Fin 3`. -/
def k33 : SimpleGraph (Fin 3 ⊕ Fin 3) where
  Adj
    | .inl _, .inr _ => True
    | .inr _, .inl _ => True
    | .inl _, .inl _ => False
    | .inr _, .inr _ => False
  symm := ⟨fun a b h => by
    cases a <;> cases b <;> exact h⟩
  loopless := ⟨fun a h => by
    cases a <;> exact h⟩

/-- Planarity in Wagner form: `G` has no K₅ minor and no K₃,₃ minor. By
Wagner's theorem (1937) this is equivalent to the topological definition of
planarity for finite graphs; the equivalence is a cited definitional choice
(see `tests/reference/concept-ledger.md` of the packaged task), not proved
here. -/
def IsPlanar : Prop :=
  ¬ G.HasMinor (⊤ : SimpleGraph (Fin 5)) ∧ ¬ G.HasMinor k33

end Defs

end SimpleGraph

namespace GNRSConjecture

/-! ### Concrete instances -/

/-- The 4-cycle on `Fin 4`. -/
def cycle4 : SimpleGraph (Fin 4) where
  Adj i j := (i.val + 1) % 4 = j.val ∨ (j.val + 1) % 4 = i.val
  symm := ⟨fun _ _ h => h.symm⟩
  loopless := ⟨fun i h => by
    rcases h with h | h <;> omega⟩

instance : DecidableRel cycle4.Adj :=
  fun i j => inferInstanceAs (Decidable ((i.val + 1) % 4 = j.val ∨ (j.val + 1) % 4 = i.val))

/-- `K_{2,3}` on `Fin 5`: vertices `0, 1` on one side, `2, 3, 4` on the
other. -/
def k23 : SimpleGraph (Fin 5) where
  Adj i j := (i.val ≤ 1 ∧ 2 ≤ j.val) ∨ (j.val ≤ 1 ∧ 2 ≤ i.val)
  symm := ⟨fun _ _ h => h.symm⟩
  loopless := ⟨fun i h => by
    rcases h with ⟨h1, h2⟩ | ⟨h1, h2⟩ <;> omega⟩

instance : DecidableRel k23.Adj :=
  fun i j => inferInstanceAs (Decidable ((i.val ≤ 1 ∧ 2 ≤ j.val) ∨ (j.val ≤ 1 ∧ 2 ≤ i.val)))

/-- The star on `n + 1` vertices: vertex `0` joined to every other vertex. -/
def starGraph (n : ℕ) : SimpleGraph (Fin (n + 1)) where
  Adj i j := (i = 0 ∧ j ≠ 0) ∨ (i ≠ 0 ∧ j = 0)
  symm := ⟨fun _ _ h => h.elim (fun hh => Or.inr ⟨hh.2, hh.1⟩) (fun hh => Or.inl ⟨hh.2, hh.1⟩)⟩
  loopless := ⟨fun i h => by
    rcases h with ⟨h1, h2⟩ | ⟨h1, h2⟩
    · exact h2 h1
    · exact h1 h2⟩

instance (n : ℕ) : DecidableRel (starGraph n).Adj :=
  fun i j => inferInstanceAs (Decidable ((i = 0 ∧ j ≠ 0) ∨ (i ≠ 0 ∧ j = 0)))

/- The kernel recursion limit is raised so that `decide` can evaluate
`spDist` on small graphs (the bounded walk search exceeds
the default limit). This line is part of the fixed zone. -/
set_option maxRecDepth 32768

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

/-! ## Slot zone: the conjecture and its negation -/

-- @[slot main]
/-- **The GNRS conjecture** (planar case; Gupta–Newman–Rabinovich–Sinclair,
FOCS 1999 / Combinatorica 2004): there is a universal constant `C` such that
the shortest-path metric of every finite connected planar graph embeds into
`ℓ₁` with distortion at most `C`. -/
theorem conj :
    ∃ C : ℝ, ∀ {V : Type*} [Fintype V] [DecidableEq V] (G : SimpleGraph V)
        [DecidableRel G.Adj], G.Connected → G.IsPlanar → G.EmbedsIntoL1 C := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

-- @[slot main]
/-- The negation of the GNRS conjecture: no universal constant bounds the
`ℓ₁`-embedding distortion of all finite connected planar graphs. -/
theorem refuted :
    ¬∃ C : ℝ, ∀ {V : Type*} [Fintype V] [DecidableEq V] (G : SimpleGraph V)
        [DecidableRel G.Adj], G.Connected → G.IsPlanar → G.EmbedsIntoL1 C := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

end GNRSConjecture
