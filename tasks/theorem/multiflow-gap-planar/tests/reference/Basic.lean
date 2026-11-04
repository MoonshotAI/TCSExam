/-
Self-contained statement layer for a lower bound on multiflow–multicut
gaps, in a pure graph-theoretic form: if the cactus family is
`SDD(2w, p)`-acceptable then `8/7 ≤ w · p` — via the gap–SDD equivalence
(not formalized here), the `16/7` multiflow–multicut gap lower bound for
cactus (and hence planar) graphs.

The fixed part (everything above the end-of-fixed-part marker line) is the
definition layer the main theorem's statement needs: `t`-diameter
decompositions of a finite graph, small-diameter decomposition
distributions, the cactus predicate, and SDD-acceptability of the cactus
family. The multicut LP, its integrality gap and the gap–SDD equivalence
are not part of the task. Fidelity notes live in `tests/reference/`.
-/

import Mathlib

namespace MultiflowGapPlanar

open Finset

variable {V : Type} [Fintype V] [DecidableEq V]

/-- A `t`-diameter decomposition of `G` (`F` forms a `t`-diameter
decomposition iff `diam(F) < t`; the family of all of them is `F_t(G)`): a
set of edges whose removal leaves connected components whose pairs of
vertices are at `G`-distance `< t`. Distances are always measured in the
ambient graph `G`, never in the component. -/
def IsDiamDecomp (G : SimpleGraph V) (F : Finset (Sym2 V)) (t : ℕ) : Prop :=
  ∀ u v : V, (G.deleteEdges (F : Set (Sym2 V))).Reachable u v → G.dist u v < t

/-- The finset of all `t`-diameter decompositions of `G` (`F_t(G)`). -/
noncomputable def decomps (G : SimpleGraph V) [DecidableRel G.Adj] (t : ℕ) :
    Finset (Finset (Sym2 V)) := by
  classical exact G.edgeFinset.powerset.filter fun F => IsDiamDecomp G F t

/-- A small-diameter decomposition distribution `SDD(G, 2w, p)`:
a probability distribution on the `2w`-diameter decompositions
of `G` under which every edge is cut with probability at most `p`. -/
structure IsSDD (G : SimpleGraph V) [DecidableRel G.Adj] (w : ℕ) (p : ℝ)
    (y : Finset (Sym2 V) → ℝ) : Prop where
  /-- Pointwise non-negativity. -/
  nonneg : ∀ F, 0 ≤ y F
  /-- The distribution is supported on `2w`-diameter decompositions. -/
  support : ∀ F, y F ≠ 0 → F ∈ decomps G (2 * w)
  /-- Total mass one. -/
  total : ∑ F ∈ decomps G (2 * w), y F = 1
  /-- Every edge is cut with probability at most `p`. -/
  edge_le : ∀ e ∈ G.edgeFinset,
    ∑ F ∈ (decomps G (2 * w)).filter fun F => e ∈ F, y F ≤ p

/-- The cactus predicate: every edge lies on at most one cycle —
any two cycles sharing an edge have the same edge set. -/
def IsCactus (G : SimpleGraph V) : Prop :=
  ∀ (v₁ v₂ : V) (c₁ : G.Walk v₁ v₁) (c₂ : G.Walk v₂ v₂), c₁.IsCycle → c₂.IsCycle →
    (∃ e : Sym2 V, e ∈ c₁.edges ∧ e ∈ c₂.edges) →
    ∀ e : Sym2 V, e ∈ c₁.edges ↔ e ∈ c₂.edges

/-- SDD-acceptability of the cactus family:
every finite cactus graph admits an `SDD(·, 2w, p)`. -/
def CactusAcceptable (w : ℕ) (p : ℝ) : Prop :=
  ∀ (W : Type) [Fintype W] [DecidableEq W] (G : SimpleGraph W) [DecidableRel G.Adj],
    IsCactus G → ∃ y, IsSDD G w p y

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- but the fixed part above and the main-theorem statement must not be modified.

/-- The main theorem: if the cactus
family is `SDD(2w, p)`-acceptable for an even `w ≥ 2` and `0 < p < 1`, then
`8/7 ≤ w·p`. (Via the gap–SDD equivalence, not formalized here, this is the
`16/7` lower bound on the multiflow–multicut gap of cactus — and hence
planar — graphs.) -/
theorem cactus_sdd_gap_lower_bound {w : ℕ} (hw : Even w) (hw2 : 2 ≤ w) {p : ℝ}
    (hpo : 0 < p) (hp1 : p < 1) (hacc : CactusAcceptable w p) :
    (8 : ℝ) / 7 ≤ (w : ℝ) * p := by
  -- CHECKPOINT cactus_sdd_gap_lower_bound BEGIN
  sorry
  -- CHECKPOINT cactus_sdd_gap_lower_bound END

end MultiflowGapPlanar
