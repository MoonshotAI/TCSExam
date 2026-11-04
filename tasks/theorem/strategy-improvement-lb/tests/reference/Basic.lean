/-
Self-contained statement layer for a theorem about parity games: symmetric
strategy improvement needs exponentially many iterations in the worst case,
independently of the improvement rule — witnessed by an explicit family
`G_n` of sink parity games.

The fixed part (everything above the end-of-fixed-part marker line) is the
definition layer the main theorem's statement needs: sink parity games,
positional strategies, play values and their total order, valuations, optimal
counterstrategies, improving moves, improvement rules, one SSI iteration as a
step relation, legal iteration chains, and the family `G_n` with its initial
strategy pair. Fidelity notes live in `tests/reference/`.
-/

import Mathlib

namespace StratImprLB

/-! ## Sink parity games -/
/-- A sink parity game: a two-player turn-based game on a finite directed
graph with a distinguished sink node `top` of strictly minimal priority whose
only outgoing edge is a self-loop. Player 0 controls the nodes with
`owner v = false`, player 1 those with `owner v = true`. Every node has at
least one outgoing edge. Priorities are natural numbers (the source text
allows any finite `Q ⊂ ℤ`; for the lower-bound family natural numbers
suffice). -/
structure SinkGame where
  N : ℕ
  owner : Fin N → Bool
  prio : Fin N → ℕ
  succ : Fin N → Finset (Fin N)
  succ_ne : ∀ v, (succ v).Nonempty
  top : Fin N
  top_prio : ∀ v, v ≠ top → prio top < prio v
  top_succ : succ top = {top}

namespace SinkGame

variable (G : SinkGame)

/-- A (positional) strategy of player 0: a choice of one outgoing edge at every
node controlled by player 0. -/
def Strat0 := { f : Fin G.N → Fin G.N // ∀ v, G.owner v = false → f v ∈ G.succ v }

/-- A (positional) strategy of player 1. -/
def Strat1 := { f : Fin G.N → Fin G.N // ∀ v, G.owner v = true → f v ∈ G.succ v }

noncomputable instance : Fintype G.Strat0 := by
  classical exact Subtype.fintype _

noncomputable instance : Fintype G.Strat1 := by
  classical exact Subtype.fintype _

instance : Nonempty G.Strat0 := by
  classical
  refine ⟨⟨fun v => if h : G.owner v = false then Classical.choose (G.succ_ne v) else G.top, ?_⟩⟩
  intro v h
  show (if h : G.owner v = _ then Classical.choose (G.succ_ne v) else G.top) ∈ G.succ v
  rw [dif_pos h]
  exact Classical.choose_spec (G.succ_ne v)

instance : Nonempty G.Strat1 := by
  classical
  refine ⟨⟨fun v => if h : G.owner v = true then Classical.choose (G.succ_ne v) else G.top, ?_⟩⟩
  intro v h
  show (if h : G.owner v = _ then Classical.choose (G.succ_ne v) else G.top) ∈ G.succ v
  rw [dif_pos h]
  exact Classical.choose_spec (G.succ_ne v)

/-- The number of nodes is positive (the sink exists). -/
theorem N_pos : 0 < G.N := Fin.pos G.top

/-- The largest priority of the game. -/
noncomputable def maxP : ℕ :=
  (Finset.univ.image G.prio).max' (Finset.image_nonempty.mpr ⟨G.top, Finset.mem_univ _⟩)

theorem prio_le_maxP (v : Fin G.N) : G.prio v ≤ G.maxP :=
  Finset.le_max' _ _ (Finset.mem_image.mpr ⟨v, Finset.mem_univ _, rfl⟩)

/-! ## Play values and their total order -/
/-- The value of a play: either a count vector over the
priorities (the pebble reaches the sink; component `q` counts how often
priority `q` occurs on the path before the sink), or `−∞` / `+∞` when the play
stays in a cycle whose largest priority is odd / even. -/
inductive PlayVal (Q : ℕ) : Type
  | negInf : PlayVal Q
  | fin : (Fin (Q + 1) → ℕ) → PlayVal Q
  | posInf : PlayVal Q

/-- Strict comparison of finite count vectors: `x` is strictly
worse than `y` for player 0 iff at the highest priority `q` where they differ,
either `q` is even and `x q < y q`, or `q` is odd and `y q < x q`. -/
def vecLt {Q : ℕ} (x y : Fin (Q + 1) → ℕ) : Prop :=
  ∃ q : Fin (Q + 1), (∀ q' : Fin (Q + 1), q < q' → x q' = y q') ∧
    ((Even (q : ℕ) ∧ x q < y q) ∨ (Odd (q : ℕ) ∧ y q < x q))

theorem vecLt_irrefl {Q : ℕ} (x : Fin (Q + 1) → ℕ) : ¬ vecLt x x := by
  rintro ⟨q, _, h⟩
  rcases h with ⟨_, h⟩ | ⟨_, h⟩ <;> exact lt_irrefl _ h

theorem vecLt_trans {Q : ℕ} {x y z : Fin (Q + 1) → ℕ} (h1 : vecLt x y) (h2 : vecLt y z) :
    vecLt x z := by
  obtain ⟨q1, hq1, h1'⟩ := h1
  obtain ⟨q2, hq2, h2'⟩ := h2
  rcases lt_trichotomy q1 q2 with h | h | h
  · refine ⟨q2, fun q' hq' => ?_, ?_⟩
    · rw [hq1 q' (show q1 < q' from lt_trans h hq'), hq2 q' hq']
    · have hx : x q2 = y q2 := hq1 q2 h
      rcases h2' with ⟨he, hlt⟩ | ⟨ho, hlt⟩
      · exact Or.inl ⟨he, by rw [hx]; exact hlt⟩
      · exact Or.inr ⟨ho, by rw [hx]; exact hlt⟩
  · subst h
    refine ⟨q1, fun q' hq' => ?_, ?_⟩
    · rw [hq1 q' hq', hq2 q' hq']
    · rcases h1' with ⟨e1, l1⟩ | ⟨o1, l1⟩ <;> rcases h2' with ⟨e2, l2⟩ | ⟨o2, l2⟩
      · exact Or.inl ⟨e1, lt_trans l1 l2⟩
      · obtain ⟨r, hr⟩ := e1; obtain ⟨s, hs⟩ := o2; omega
      · obtain ⟨r, hr⟩ := o1; obtain ⟨s, hs⟩ := e2; omega
      · exact Or.inr ⟨o1, lt_trans l2 l1⟩
  · refine ⟨q1, fun q' hq' => ?_, ?_⟩
    · rw [hq1 q' hq', hq2 q' (show q2 < q' from lt_trans h hq')]
    · have hy : y q1 = z q1 := hq2 q1 h
      rcases h1' with ⟨he, hlt⟩ | ⟨ho, hlt⟩
      · exact Or.inl ⟨he, by rw [← hy]; exact hlt⟩
      · exact Or.inr ⟨ho, by rw [← hy]; exact hlt⟩

theorem vecLt_trich {Q : ℕ} (x y : Fin (Q + 1) → ℕ) : vecLt x y ∨ x = y ∨ vecLt y x := by
  by_cases h : x = y
  · exact Or.inr (Or.inl h)
  · have hex : ∃ q : Fin (Q + 1), x q ≠ y q := by
      by_contra hc
      push Not at hc
      exact h (funext hc)
    let S := Finset.univ.filter (fun q => x q ≠ y q)
    have hS : S.Nonempty := by
      obtain ⟨q, hq⟩ := hex
      exact ⟨q, Finset.mem_filter.mpr ⟨Finset.mem_univ _, hq⟩⟩
    have hq : x (S.max' hS) ≠ y (S.max' hS) := (Finset.mem_filter.mp (S.max'_mem hS)).2
    have hmax : ∀ q' : Fin (Q + 1), S.max' hS < q' → x q' = y q' := by
      intro q' hqq
      by_contra hc
      have hq'S : q' ∈ S := Finset.mem_filter.mpr ⟨Finset.mem_univ _, hc⟩
      exact absurd (Finset.le_max' S q' hq'S) (not_le.mpr hqq)
    rcases lt_or_gt_of_ne hq with hlt | hgt
    · rcases Nat.even_or_odd (S.max' hS : ℕ) with he | ho
      · exact Or.inl ⟨S.max' hS, hmax, Or.inl ⟨he, hlt⟩⟩
      · exact Or.inr (Or.inr ⟨S.max' hS, fun q' hqq => (hmax q' hqq).symm, Or.inr ⟨ho, hlt⟩⟩)
    · rcases Nat.even_or_odd (S.max' hS : ℕ) with he | ho
      · exact Or.inr (Or.inr ⟨S.max' hS, fun q' hqq => (hmax q' hqq).symm, Or.inl ⟨he, hgt⟩⟩)
      · exact Or.inl ⟨S.max' hS, hmax, Or.inr ⟨ho, hgt⟩⟩

namespace PlayVal

/-- The total order on play values: `−∞` is the minimum, `+∞`
the maximum, and finite vectors are compared by `vecLt`. -/
def lt {Q : ℕ} : PlayVal Q → PlayVal Q → Prop
  | negInf, negInf => False
  | negInf, _ => True
  | fin x, fin y => vecLt x y
  | fin _, posInf => True
  | fin _, negInf => False
  | posInf, _ => False

def le {Q : ℕ} (a b : PlayVal Q) : Prop := lt a b ∨ a = b

theorem lt_irrefl' {Q : ℕ} (a : PlayVal Q) : ¬ lt a a := by
  cases a
  · exact id
  · exact vecLt_irrefl _
  · exact id

theorem lt_trans' {Q : ℕ} {a b c : PlayVal Q} (h1 : lt a b) (h2 : lt b c) : lt a c := by
  cases a <;> cases b <;> cases c <;> simp_all [lt]
  exact vecLt_trans h1 h2

theorem lt_asymm' {Q : ℕ} {a b : PlayVal Q} (h1 : lt a b) : ¬ lt b a := by
  intro h2
  exact lt_irrefl' _ (lt_trans' h1 h2)

theorem lt_trich' {Q : ℕ} (a b : PlayVal Q) : lt a b ∨ a = b ∨ lt b a := by
  cases a <;> cases b <;> simp_all [lt]
  rename_i x y
  rcases vecLt_trich x y with h | h | h
  · exact Or.inl h
  · exact Or.inr (Or.inl h)
  · exact Or.inr (Or.inr h)

end PlayVal

noncomputable instance {Q : ℕ} : LinearOrder (PlayVal Q) where
  le := PlayVal.le
  lt := PlayVal.lt
  le_refl := fun a => Or.inr rfl
  le_trans := by
    intro a b c hab hbc
    rcases hab with hab | rfl
    · rcases hbc with hbc | rfl
      · exact Or.inl (PlayVal.lt_trans' hab hbc)
      · exact Or.inl hab
    · exact hbc
  lt_iff_le_not_ge := by
    intro a b
    constructor
    · intro h
      refine ⟨Or.inl h, ?_⟩
      rintro (h' | rfl)
      · exact PlayVal.lt_asymm' h h'
      · exact PlayVal.lt_irrefl' _ h
    · rintro ⟨h1, h2⟩
      rcases h1 with h | rfl
      · exact h
      · exact absurd (Or.inr rfl) h2
  le_antisymm := by
    intro a b hab hba
    rcases hab with hab | rfl
    · rcases hba with hba | hba
      · exact absurd (PlayVal.lt_trans' hab hba) (PlayVal.lt_irrefl' a)
      · exact hba.symm
    · rfl
  le_total := by
    intro a b
    rcases PlayVal.lt_trich' a b with h | h | h
    · exact Or.inl (Or.inl h)
    · exact Or.inr (Or.inr h.symm)
    · exact Or.inr (Or.inl h)
  toDecidableLE := fun _ _ => Classical.dec _

/-- The priority of a node as an element of `Fin (maxP + 1)`. -/
abbrev prioFin (G : SinkGame) (v : Fin G.N) : Fin (G.maxP + 1) :=
  ⟨G.prio v, Nat.lt_succ_of_le (G.prio_le_maxP v)⟩

/-! ## Orbits and play values -/
/-- The single-step move under a strategy pair: at a player-0 node follow `σ`,
at a player-1 node follow `τ`. -/
def step (G : SinkGame) (σ : G.Strat0) (τ : G.Strat1) (v : Fin G.N) : Fin G.N :=
  if G.owner v = false then σ.1 v else τ.1 v

/-- The orbit of the pebble starting at `v`. -/
def orbit (G : SinkGame) (σ : G.Strat0) (τ : G.Strat1) (v : Fin G.N) : ℕ → Fin G.N :=
  fun k => (step G σ τ)^[k] v

open Classical in
/-- The priorities occurring infinitely often on the orbit (the priorities of
the cycle the pebble eventually follows). -/
noncomputable def infOccPrio (G : SinkGame) (σ : G.Strat0) (τ : G.Strat1) (v : Fin G.N) :
    Finset (Fin (G.maxP + 1)) :=
  Finset.univ.filter (fun q => ∀ K : ℕ, ∃ k : ℕ, K ≤ k ∧ G.prio (orbit G σ τ v k) = (q : ℕ))

open Classical in
/-- The play value of a strategy pair from a starting node:
if the pebble reaches the sink within `N` steps, the count vector of the
priorities seen before the sink; otherwise `+∞`/`−∞` according to the parity
of the largest priority occurring infinitely often. -/
noncomputable def playVal (G : SinkGame) (σ : G.Strat0) (τ : G.Strat1) (v : Fin G.N) :
    PlayVal G.maxP :=
  if h : ∃ k : ℕ, k ≤ G.N ∧ orbit G σ τ v k = G.top then
    PlayVal.fin (fun q => ∑ i ∈ Finset.range (Nat.find h),
      if G.prio (orbit G σ τ v i) = (q : ℕ) then 1 else 0)
  else
    if Even ((infOccPrio G σ τ v).sup (fun q => (q : ℕ))) then
      PlayVal.posInf
    else PlayVal.negInf

/-! ## Valuations -/
/-- The valuation of a player-0 strategy: the pointwise minimum over all
player-1 strategies of the play value (the source text's `Ξ_σ`). -/
noncomputable def xi0 (G : SinkGame) (σ : G.Strat0) (v : Fin G.N) : PlayVal G.maxP :=
  (Finset.univ.image (fun τ : G.Strat1 => playVal G σ τ v)).min'
    (Finset.image_nonempty.mpr Finset.univ_nonempty)

/-- The valuation of a player-1 strategy: the pointwise maximum (the source
text's `Ξ_τ`). -/
noncomputable def xi1 (G : SinkGame) (τ : G.Strat1) (v : Fin G.N) : PlayVal G.maxP :=
  (Finset.univ.image (fun σ : G.Strat0 => playVal G σ τ v)).max'
    (Finset.image_nonempty.mpr Finset.univ_nonempty)

/-- `σb` is an optimal counterstrategy to `σ`: it attains the minimum of the
play value simultaneously at every node (the source text's `σ̄`). -/
def IsCounter1 (G : SinkGame) (σ : G.Strat0) (σb : G.Strat1) : Prop :=
  ∀ v, playVal G σ σb v = xi0 G σ v

/-- `τb` is an optimal counterstrategy to `τ` (player 0's side, the source
text's `τ̄`). -/
def IsCounter0 (G : SinkGame) (τ : G.Strat1) (τb : G.Strat0) : Prop :=
  ∀ v, playVal G τb τ v = xi1 G τ v

/-- At every node there is an outgoing edge attaining the minimum
valuation. -/
theorem argmin1_exists (G : SinkGame) (σ : G.Strat0) (v : Fin G.N) :
    ∃ w ∈ G.succ v, xi0 G σ w =
      ((G.succ v).image (xi0 G σ)).min' (Finset.image_nonempty.mpr (G.succ_ne v)) :=
  Finset.mem_image.mp (Finset.min'_mem _ _)

/-- At every node there is an outgoing edge attaining the maximum
valuation. -/
theorem argmax0_exists (G : SinkGame) (τ : G.Strat1) (v : Fin G.N) :
    ∃ w ∈ G.succ v, xi1 G τ w =
      ((G.succ v).image (xi1 G τ)).max' (Finset.image_nonempty.mpr (G.succ_ne v)) :=
  Finset.mem_image.mp (Finset.max'_mem _ _)

/-! ## Improvement moves, improvement rules, and one SSI step -/
open Classical in
/-- The set of improving moves of a player-0 strategy (the source text's
`I_σ`):
edges `(v, w)` with `v` controlled by player 0 and `Ξ_σ(w) ▷ Ξ_σ(σ(v))`. -/
noncomputable def improving0 (G : SinkGame) (σ : G.Strat0) : Finset (Fin G.N × Fin G.N) :=
  Finset.univ.filter (fun e => G.owner e.1 = false ∧ e.2 ∈ G.succ e.1 ∧
    xi0 G σ (σ.1 e.1) < xi0 G σ e.2)

open Classical in
/-- The set of improving moves of a player-1 strategy (the source text's
`I_τ`):
`Ξ_τ(w) ◁ Ξ_τ(τ(v))`. -/
noncomputable def improving1 (G : SinkGame) (τ : G.Strat1) : Finset (Fin G.N × Fin G.N) :=
  Finset.univ.filter (fun e => G.owner e.1 = true ∧ e.2 ∈ G.succ e.1 ∧
    xi1 G τ e.2 < xi1 G τ (τ.1 e.1))

/-- Optimality of a player-0 strategy: the valuation is pointwise maximal
(the source text's "optimal strategy"). -/
def IsOpt0 (G : SinkGame) (σ : G.Strat0) : Prop :=
  ∀ (σ' : G.Strat0) (v : Fin G.N), xi0 G σ' v ≤ xi0 G σ v

/-- Optimality of a player-1 strategy: the valuation is pointwise minimal. -/
def IsOpt1 (G : SinkGame) (τ : G.Strat1) : Prop :=
  ∀ (τ' : G.Strat1) (v : Fin G.N), xi1 G τ v ≤ xi1 G τ' v

/-- An improvement rule (the source text's three conditions: nonempty
selection,
subset, at most one outgoing edge per node). -/
def ImpRule (G : SinkGame) :=
  { f : Finset (Fin G.N × Fin G.N) → Finset (Fin G.N × Fin G.N) //
    ∀ S, f S ⊆ S ∧ (S.Nonempty → (f S).Nonempty) ∧
      ∀ v, ((f S).filter (fun e => e.1 = v)).card ≤ 1 }

/-- Applying a set of edges (at most one per node) to a player-0 strategy. -/
noncomputable def applyEdges0 (G : SinkGame) (σ : G.Strat0)
    (I : Finset (Fin G.N × Fin G.N)) (hI : ∀ e ∈ I, e.2 ∈ G.succ e.1) : G.Strat0 :=
  ⟨fun v => if h : ∃ w, (v, w) ∈ I then Classical.choose h else σ.1 v, by
    intro v hv
    show (if h : ∃ w, (v, w) ∈ I then Classical.choose h else σ.1 v) ∈ G.succ v
    by_cases h : ∃ w, (v, w) ∈ I
    · rw [dif_pos h]
      exact hI _ (Classical.choose_spec h)
    · rw [dif_neg h]
      exact σ.2 v hv⟩

/-- Applying a set of edges to a player-1 strategy. -/
noncomputable def applyEdges1 (G : SinkGame) (τ : G.Strat1)
    (I : Finset (Fin G.N × Fin G.N)) (hI : ∀ e ∈ I, e.2 ∈ G.succ e.1) : G.Strat1 :=
  ⟨fun v => if h : ∃ w, (v, w) ∈ I then Classical.choose h else τ.1 v, by
    intro v hv
    show (if h : ∃ w, (v, w) ∈ I then Classical.choose h else τ.1 v) ∈ G.succ v
    by_cases h : ∃ w, (v, w) ∈ I
    · rw [dif_pos h]
      exact hI _ (Classical.choose_spec h)
    · rw [dif_neg h]
      exact τ.2 v hv⟩

open Classical in
/-- The improving-edge set offered to the improvement rule in one SSI
iteration: the improving moves of `σ` along the edges of
`τ̄` united with those of `τ` along the edges of `σ̄`. -/
noncomputable def ssiOfferSet (G : SinkGame) (s : G.Strat0 × G.Strat1)
    (σb : G.Strat1) (τb : G.Strat0) : Finset (Fin G.N × Fin G.N) :=
  ((improving0 G s.1).filter (fun e => τb.1 e.1 = e.2)) ∪
    ((improving1 G s.2).filter (fun e => σb.1 e.1 = e.2))

theorem ssiOfferSet_mem_succ (G : SinkGame) (s : G.Strat0 × G.Strat1)
    (σb : G.Strat1) (τb : G.Strat0) {e : Fin G.N × Fin G.N}
    (he : e ∈ ssiOfferSet G s σb τb) : e.2 ∈ G.succ e.1 := by
  rw [ssiOfferSet] at he
  rcases Finset.mem_union.mp he with h2 | h2
  · rw [improving0] at h2
    exact (Finset.mem_filter.mp (Finset.mem_filter.mp h2).1).2.2.1
  · rw [improving1] at h2
    exact (Finset.mem_filter.mp (Finset.mem_filter.mp h2).1).2.2.1

/-- One iteration of symmetric strategy improvement under
improvement rule `f`, as a non-deterministic step relation (the optimal
counterstrategies σ̄ and τ̄ are existentially quantified). -/
def SSIStep (G : SinkGame) (f : ImpRule G) (s s' : G.Strat0 × G.Strat1) : Prop :=
  ∃ (σb : G.Strat1) (τb : G.Strat0),
    IsCounter1 G s.1 σb ∧ IsCounter0 G s.2 τb ∧
    s'.1 = applyEdges0 G s.1 (f.1 (ssiOfferSet G s σb τb))
      (fun e he => ssiOfferSet_mem_succ G s σb τb ((f.2 _).1 he)) ∧
    s'.2 = applyEdges1 G s.2 (f.1 (ssiOfferSet G s σb τb))
      (fun e he => ssiOfferSet_mem_succ G s σb τb ((f.2 _).1 he))

/-- A legal iteration chain: a nonempty list of strategy pairs starting at the
initial pair, linked by `SSIStep`. -/
def LegalChain (G : SinkGame) (f : ImpRule G) (s₀ : G.Strat0 × G.Strat1)
    (l : List (G.Strat0 × G.Strat1)) : Prop :=
  l ≠ [] ∧ l.head? = some s₀ ∧ l.Chain' (fun s s' => SSIStep G f s s')

/-! ## The lower-bound family `G_n` -/
/-- Node ownership in `G_n`: the `a`-nodes (indices `0 … n`) belong to
player 0, the `d`-nodes (indices `n+1 … 2n+1`) to player 1. -/
def gnOwner (n : ℕ) (v : Fin (2 * n + 2)) : Bool := decide (n < (v : ℕ))

/-- Priorities of `G_n`: `p(a_i) = 2i+1` for `i ≤ n`, the sink `a_{n+1}` has
priority `1`, `p(d_i) = 2i+2` for `i ≤ n`, and `p(d_{n+1}) = 2n+4`. -/
def gnPrio (n : ℕ) (v : Fin (2 * n + 2)) : ℕ :=
  if (v : ℕ) ≤ n then
    if (v : ℕ) = n then 1 else 2 * ((v : ℕ) + 1) + 1
  else
    if (v : ℕ) = 2 * n + 1 then 2 * n + 4 else 2 * ((v : ℕ) - n) + 2

/-- Edges of `G_n`: `a_1 → {a_2, d_2}`, `a_i → {a_1, a_{i+1},
d_{i+1}}` for `2 ≤ i ≤ n`, the sink `a_{n+1}` has only the self-loop, `d_1 →
{a_2, d_2}`, `d_i → {d_1, a_{i+1}, d_{i+1}}` for `2 ≤ i ≤ n`, and
`d_{n+1} → {a_{n+1}}`. (The `min`-clamps are immaterial off the intended
ranges.) -/
def gnSucc (n : ℕ) (v : Fin (2 * n + 2)) : Finset (Fin (2 * n + 2)) :=
  if (v : ℕ) ≤ n then
    if (v : ℕ) = n then {⟨n, by omega⟩}
    else if (v : ℕ) = 0 then {⟨1, by omega⟩, ⟨min (n + 2) (2 * n + 1), by
      have h := Nat.min_le_right (n + 2) (2 * n + 1)
      omega⟩}
    else {⟨0, by omega⟩, ⟨min ((v : ℕ) + 1) n, by
      have h := Nat.min_le_right ((v : ℕ) + 1) n
      omega⟩, ⟨min (n + (v : ℕ) + 2) (2 * n + 1), by
      have h := Nat.min_le_right (n + (v : ℕ) + 2) (2 * n + 1)
      omega⟩}
  else
    if (v : ℕ) = 2 * n + 1 then {⟨n, by omega⟩}
    else if (v : ℕ) = n + 1 then {⟨1, by omega⟩, ⟨min (n + 2) (2 * n + 1), by
      have h := Nat.min_le_right (n + 2) (2 * n + 1)
      omega⟩}
    else {⟨n + 1, by omega⟩, ⟨(v : ℕ) - n, by omega⟩, ⟨min ((v : ℕ) + 1) (2 * n + 1), by
      have h := Nat.min_le_right ((v : ℕ) + 1) (2 * n + 1)
      omega⟩}

/-- The game `G_n`. -/
abbrev Gn (n : ℕ) : SinkGame where
  N := 2 * n + 2
  owner := gnOwner n
  prio := gnPrio n
  succ := gnSucc n
  succ_ne := by
    intro v
    unfold gnSucc
    split_ifs <;> simp
  top := ⟨n, by omega⟩
  top_succ := by
    show gnSucc n ⟨n, by omega⟩ = {⟨n, by omega⟩}
    unfold gnSucc
    rw [if_pos (le_refl n), if_pos rfl]
  top_prio := by
    intro v hv
    show gnPrio n ⟨n, by omega⟩ < gnPrio n v
    have hvne : (v : ℕ) ≠ n := by
      intro hcc
      exact hv (Fin.ext hcc)
    unfold gnPrio
    rw [if_pos (le_refl n), if_pos rfl]
    by_cases h1 : (v : ℕ) ≤ n
    · rw [if_pos h1, if_neg hvne]
      omega
    · by_cases h2 : (v : ℕ) = 2 * n + 1
      · rw [if_neg h1, if_pos h2]
        omega
      · rw [if_neg h1, if_neg h2]
        omega

/-- The initial player-0 strategy `σ₀`: `σ₀(a_i) = a_{i+1}` for `i ≤ n` and
`σ₀(a_{n+1}) = a_{n+1}`. -/
def σ0fun (n : ℕ) (v : Fin (2 * n + 2)) : Fin (2 * n + 2) :=
  if (v : ℕ) ≤ n then ⟨min ((v : ℕ) + 1) n, by
    have h := Nat.min_le_right ((v : ℕ) + 1) n
    omega⟩
  else ⟨n, by omega⟩

/-- The initial player-1 strategy `τ₀`: `τ₀(d_i) = d_{i+1}` for `i ≤ n` and
`τ₀(d_{n+1}) = a_{n+1}`. -/
def τ0fun (n : ℕ) (v : Fin (2 * n + 2)) : Fin (2 * n + 2) :=
  if (v : ℕ) ≤ n then ⟨n, by omega⟩
  else if (v : ℕ) = 2 * n + 1 then ⟨n, by omega⟩
  else ⟨min ((v : ℕ) + 1) (2 * n + 1), by
    have h := Nat.min_le_right ((v : ℕ) + 1) (2 * n + 1)
    omega⟩

/-- The initial player-0 strategy as a strategy. -/
def σ0strat (n : ℕ) : (Gn n).Strat0 :=
  ⟨σ0fun n, by
    intro v h
    have hv : (v : ℕ) ≤ n := by
      have h2 := h
      change decide (n < (v : ℕ)) = false at h2
      rw [decide_eq_false_iff_not] at h2
      omega
    show σ0fun n v ∈ gnSucc n v
    unfold σ0fun gnSucc
    rw [if_pos hv, if_pos hv]
    by_cases h2 : (v : ℕ) = n
    · rw [if_pos h2, Finset.mem_singleton]
      apply Fin.ext
      show min ((v : ℕ) + 1) n = n
      rw [h2]
      exact Nat.min_eq_right (by omega)
    · rw [if_neg h2]
      by_cases h3 : (v : ℕ) = 0
      · rw [if_pos h3, Finset.mem_insert]
        apply Or.inl
        apply Fin.ext
        show min ((v : ℕ) + 1) n = 1
        rw [h3]
        exact Nat.min_eq_left (by omega)
      · rw [if_neg h3, Finset.mem_insert, Finset.mem_insert, Finset.mem_singleton]
        exact Or.inr (Or.inl (Fin.ext rfl))
  ⟩

/-- The initial player-1 strategy as a strategy. -/
def τ0strat (n : ℕ) : (Gn n).Strat1 :=
  ⟨τ0fun n, by
    intro v h
    have hv : n < (v : ℕ) := by
      have h2 := h
      change decide (n < (v : ℕ)) = true at h2
      exact of_decide_eq_true h2
    have hnv : ¬ (v : ℕ) ≤ n := by omega
    show τ0fun n v ∈ gnSucc n v
    unfold τ0fun gnSucc
    rw [if_neg hnv, if_neg hnv]
    by_cases h2 : (v : ℕ) = 2 * n + 1
    · rw [if_pos h2, if_pos h2]
      exact Finset.mem_singleton_self _
    · rw [if_neg h2, if_neg h2]
      by_cases h3 : (v : ℕ) = n + 1
      · rw [if_pos h3, Finset.mem_insert, Finset.mem_singleton]
        apply Or.inr
        apply Fin.ext
        show min ((v : ℕ) + 1) (2 * n + 1) = min (n + 2) (2 * n + 1)
        rw [h3]
      · rw [if_neg h3, Finset.mem_insert, Finset.mem_insert, Finset.mem_singleton]
        exact Or.inr (Or.inr (Fin.ext rfl))
  ⟩

/-- The initial strategy pair. -/
def σ0τ0pair (n : ℕ) : (Gn n).Strat0 × (Gn n).Strat1 := (σ0strat n, τ0strat n)

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- but the fixed part above and the main-theorem statement must not be
-- modified.

/-- The main theorem, parity-game content: symmetric strategy improvement
needs exponentially many iterations on the family `G_n`, independently of the
improvement rule — from the initial pair `(σ₀, τ₀)`, no legal iteration
chain of length at most `2^{n+1} − 3` ends at the optimal strategy pair
(`G_n` has `2n+2` nodes and `6n` edges, so the bound is exponential in the
graph size). -/
theorem ssi_exponential_lower_bound (n : ℕ) (hn : 1 ≤ n)
    (f : ImpRule (Gn n))
    (l : List ((Gn n).Strat0 × (Gn n).Strat1))
    (hl : LegalChain (Gn n) f (σ0τ0pair n) l)
    (hlen : l.length ≤ 2 ^ (n + 1) - 3) :
    ¬ (IsOpt0 (Gn n) (l.getLast hl.1).1 ∧
      IsOpt1 (Gn n) (l.getLast hl.1).2) := by
  -- CHECKPOINT ssi_exponential_lower_bound BEGIN
  sorry
  -- CHECKPOINT ssi_exponential_lower_bound END

end SinkGame

end StratImprLB
