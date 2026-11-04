/-
Self-contained statement layer for a theorem in graph reconfiguration:
independent set reconfiguration under token jumping (ISR-TJ) admits a
kernel of size linear in `k` on `K_{3,r}`-minor-free graphs, with an
explicit kernel constant.

The fixed part (everything above the end-of-fixed-part marker line) is the
definition layer the main theorem's statement needs: finite simple graphs,
independent sets (mathlib's `SimpleGraph.IsIndepSet`), one token-jumping step
and its reflexive-transitive closure (reconfiguration sequences, possibly
restricted to a vertex set `W`), connectedness of a vertex set via walks,
`K_{3,r}` minors via branch sets, proper colorings, the `X`-projection class
counts `N2`/`N3`, and the explicit constants. Fidelity notes live in
`tests/reference/`.

Two facts the source text cites without proof are packaged as hypotheses of
the main theorem: the coloring bound `χ ≤ max{r,6300}+3` enters as a given
proper coloring, and the neighborhood-complexity bound
`N2 + N3 ≤ 2^{5r+13}·(r+3)^{2r+5}·k` enters as a numeric hypothesis on the
instance. The kernel is stated as a vertex set `W` containing the key
vertices, with `|W| ≤ K(r)·k` for the explicit constant `K(r)` and with
equivalence of the reconfiguration predicates; polynomial-time computability
of `W` is not formalized.
-/

import Mathlib

namespace PlanarISReconfigKernel

variable {V : Type*} [Fintype V] [DecidableEq V]

/-! ## Token jumping and reconfiguration -/

/-- One token-jumping step (the TJ model):
remove the token at `v` and place it on any vertex `w` outside the current
set; the resulting arrangement must again be an independent set. The
cardinality is preserved automatically. -/
def TJStep (G : SimpleGraph V) (I J : Finset V) : Prop :=
  G.IsIndepSet ↑J ∧ ∃ v ∈ I, ∃ w ∉ I, J = insert w (I.erase v)

/-- Reconfigurability of two independent sets under token jumping: a sequence
of token jumps transforming `Is` into `It` (ISR-TJ). -/
def Reconf (G : SimpleGraph V) (Is It : Finset V) : Prop :=
  Relation.ReflTransGen (TJStep G) Is It

/-- One token-jumping step with both endpoints inside `W`. -/
def TJStepIn (G : SimpleGraph V) (W I J : Finset V) : Prop :=
  I ⊆ W ∧ J ⊆ W ∧ TJStep G I J

/-- Reconfiguration using only vertices of `W` (the kernelized instance
`ISR-TJ(G[W], Is, It)`, stated without a subgraph API). -/
def ReconfIn (G : SimpleGraph V) (W Is It : Finset V) : Prop :=
  Relation.ReflTransGen (TJStepIn G W) Is It

/-! ## Minors via branch sets -/

/-- Connectedness of a vertex set: any two of its vertices are joined by a
walk whose support stays inside the set. -/
def ConnectedIn (G : SimpleGraph V) (S : Finset V) : Prop :=
  ∀ u ∈ S, ∀ v ∈ S, ∃ w : G.Walk u v, ∀ z ∈ w.support, z ∈ S

/-- `G` contains a `K_{3,r}` minor, in branch-set form: `3 + r` pairwise
disjoint nonempty connected vertex sets, with an edge between every one of
the `3` branch sets and every one of the `r` branch sets. -/
def HasK3rMinor (G : SimpleGraph V) (r : ℕ) : Prop :=
  ∃ (A : Fin 3 → Finset V) (B : Fin r → Finset V),
    (∀ i, (A i).Nonempty) ∧ (∀ j, (B j).Nonempty) ∧
    (∀ i, ConnectedIn G (A i)) ∧ (∀ j, ConnectedIn G (B j)) ∧
    (∀ i i' : Fin 3, i ≠ i' → Disjoint (A i) (A i')) ∧
    (∀ j j' : Fin r, j ≠ j' → Disjoint (B j) (B j')) ∧
    (∀ i : Fin 3, ∀ j : Fin r, Disjoint (A i) (B j)) ∧
    (∀ i : Fin 3, ∀ j : Fin r, ∃ u ∈ A i, ∃ v ∈ B j, G.Adj u v)

/-- `G` has no `K_{3,r}` minor (the graph-class restriction of the main
theorem). -/
def K3rMinorFree (G : SimpleGraph V) (r : ℕ) : Prop := ¬ HasK3rMinor G r

/-- A proper coloring of `G` with `q` colors (adjacent vertices differ). -/
def ProperColoring (G : SimpleGraph V) {q : ℕ} (c : V → Fin q) : Prop :=
  ∀ v w : V, G.Adj v w → c v ≠ c w

/-! ## The `X`-projection class counts -/

/-- The key vertices: `X := Is ∪ It`. -/
def keySet (Is It : Finset V) : Finset V := Is ∪ It

/-- The `X`-projection class `C_Y`: vertices outside `X`
whose neighborhood inside `X` is exactly `Y`. -/
def projClass (G : SimpleGraph V) [DecidableRel G.Adj] (X Y : Finset V) : Finset V :=
  (Finset.univ \ X).filter fun v => G.neighborFinset v ∩ X = Y

/-- The number of nonempty 2-classes (`N2(G)`). -/
def N2 (G : SimpleGraph V) [DecidableRel G.Adj] (X : Finset V) : ℕ :=
  (X.powerset.filter fun Y => Y.card = 2 ∧ projClass G X Y ≠ ∅).card

/-- The number of nonempty classes on at least 3 key vertices (`N3(G)`). -/
def N3 (G : SimpleGraph V) [DecidableRel G.Adj] (X : Finset V) : ℕ :=
  (X.powerset.filter fun Y => 3 ≤ Y.card ∧ projClass G X Y ≠ ∅).card

/-! ## The explicit constants -/

/-- The neighborhood-complexity bound (an external bound quoted without
proof, packaged as a hypothesis of the main theorem):
`N2 + N3 ≤ B(r)·k`. -/
def nbrComplBound (r : ℕ) : ℕ := 2 ^ (5 * r + 13) * (r + 3) ^ (2 * r + 5)

/-- The coloring bound (an external result quoted without proof, packaged
as a given coloring): `q = max{r, 6300} + 3`. -/
def colorBound (r : ℕ) : ℕ := max r 6300 + 3

/-- The explicit kernel constant `K(r)`:
`|X| + |C1| + |C3| + |C2′| ≤ 2k + (q + (r−1)·B)·k + q·(B·(4r−1)+1)·k`. -/
def kernelBound (r : ℕ) : ℕ :=
  2 + colorBound r + (r - 1) * nbrComplBound r +
    colorBound r * (nbrComplBound r * (4 * r - 1) + 1)

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- but the fixed part above and the main-theorem statement must not be
-- modified.

/-- The main theorem, explicit-constant form. Fix `r ≥ 1`;
let `G` be a `K_{3,r}`-minor-free graph, given together with a proper
coloring with `max{r,6300} + 3` colors (an external coloring bound,
packaged as a hypothesis) and with the neighborhood-complexity bound
`N2(G) + N3(G) ≤ 2^{5r+13}·(r+3)^{2r+5}·k` (an external bound quoted
without proof, packaged as a hypothesis). Then ISR-TJ on `G` admits a kernel
of size at most `K(r)·k`: there is a vertex set `W ⊇ X` with
`|W| ≤ K(r)·k` such that `Is` reconfigures to `It` in `G` iff it does so
using only vertices of `W`. -/
theorem isr_tj_linear_kernel (G : SimpleGraph V) [DecidableRel G.Adj]
    {r k : ℕ} (hr : 1 ≤ r) (hk : 1 ≤ k)
    {Is It : Finset V} (hIs : G.IsIndepSet ↑Is ∧ Is.card = k)
    (hIt : G.IsIndepSet ↑It ∧ It.card = k)
    (hminor : K3rMinorFree G r)
    (c : V → Fin (colorBound r)) (hc : ProperColoring G c)
    (hn23 : N2 G (keySet Is It) + N3 G (keySet Is It) ≤ nbrComplBound r * k) :
    ∃ W : Finset V, keySet Is It ⊆ W ∧ W.card ≤ kernelBound r * k ∧
      (Reconf G Is It ↔ ReconfIn G W Is It) := by
  -- CHECKPOINT isr_tj_linear_kernel BEGIN
  sorry
  -- CHECKPOINT isr_tj_linear_kernel END

end PlanarISReconfigKernel
