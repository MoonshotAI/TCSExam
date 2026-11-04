/-
Self-contained statement layer for a theorem in the theory of threshold
budgets in energy discrete-bidding games: existence of a compact
budget-agnostic winning strategy for Pres with an explicit energy bound.

The fixed part (everything above the end-of-fixed-part marker line) is the
definition layer the main theorem's statement needs: the budget domain `N*`
with its operators and tie-breaking advantage, arenas, configurations,
strategies, plays, the energy objective, the value-iteration recursion
`mu_n`, the post-truncated sequence, the recursively trimmed operator
iterate and its fixed point `mu`, the threshold
budget `Th`, `Trim` and the budget-agnostic predicate, and the explicit
energy bound of the main theorem. The determinacy of reachability
discrete-bidding games is packaged as the proposition
`ReachabilityDetermined` and appears as a hypothesis of the main theorem.

Fidelity deviations from the source text are documented in
`tests/reference/concept-ledger.md` of the packaged task.
-/

import Mathlib

namespace DiscreteBidding

/-! ## Budgets with the tie-breaking advantage (the set `ℕ*`) -/

/-- A budget in `ℕ* = {0, 0*, 1, 1*, ...}`: `⟨n, false⟩` is the plain budget
`n` and `⟨n, true⟩` is `n*`, i.e. `n` together with the tie-breaking
advantage. The natural order is `0 ≺ 0* ≺ 1 ≺ 1* ≺ ...`. -/
structure Bdg where
  val : ℕ
  star : Bool
deriving DecidableEq

namespace Bdg

/-- The doubled value: `dbl ⟨n, false⟩ = 2n`, `dbl ⟨n, true⟩ = 2n + 1`. The
order on `ℕ*` is the pullback of the order on `ℕ` along `dbl`. -/
def dbl (b : Bdg) : ℕ := 2 * b.val + b.star.toNat

theorem dbl_injective : Function.Injective dbl := by
  intro a b h
  obtain ⟨av, as⟩ := a
  obtain ⟨bv, bs⟩ := b
  simp only [dbl] at h
  cases as <;> cases bs <;> simp only [Bool.toNat_false, Bool.toNat_true] at h
  · have : av = bv := by omega
    subst this; rfl
  · omega
  · omega
  · have : av = bv := by omega
    subst this; rfl

instance instLE : LE Bdg where le a b := dbl a ≤ dbl b
instance instLT : LT Bdg where lt a b := dbl a < dbl b

theorem le_iff_dbl (a b : Bdg) : a ≤ b ↔ dbl a ≤ dbl b := Iff.rfl
theorem lt_iff_dbl (a b : Bdg) : a < b ↔ dbl a < dbl b := Iff.rfl

instance : DecidableRel (· ≤ · : Bdg → Bdg → Prop) :=
  fun a b => inferInstanceAs (Decidable (dbl a ≤ dbl b))
instance : DecidableRel (· < · : Bdg → Bdg → Prop) :=
  fun a b => inferInstanceAs (Decidable (dbl a < dbl b))

instance : LinearOrder Bdg where
  le_refl a := Nat.le_refl _
  le_trans a b c := Nat.le_trans
  lt_iff_le_not_ge a b := by
    show dbl a < dbl b ↔ dbl a ≤ dbl b ∧ ¬dbl b ≤ dbl a
    omega
  le_antisymm a b hab hba := dbl_injective (Nat.le_antisymm hab hba)
  le_total a b := Nat.le_total _ _
  toDecidableLE := inferInstance

/-- Addition on `ℕ*`: `x* ⊕ y = x ⊕ y* = (x+y)*`,
`x ⊕ y = x+y` (plain) and `x* ⊕ y* = x+y+1` (plain). -/
def add (a b : Bdg) : Bdg :=
  if a.star && b.star then ⟨a.val + b.val + 1, false⟩ else ⟨a.val + b.val, a.star || b.star⟩

/-- Subtraction on `ℕ*`: `x* ⊖ y = (x−y)*`, `x* ⊖ y* = x−y`,
`x ⊖ y = x−y`, `x ⊖ y* = (x−y−1)*`. Subtraction of naturals is truncated at
`0`; the source text only uses `⊖` when the result is a genuine element of
`ℕ*`, i.e. when `dbl b ≤ dbl a` (see `dbl_sub`). -/
def sub (a b : Bdg) : Bdg :=
  ⟨a.val - b.val - (if !a.star && b.star then 1 else 0), a.star != b.star⟩

theorem dbl_add (a b : Bdg) : dbl (add a b) = dbl a + dbl b := by
  obtain ⟨av, as⟩ := a
  obtain ⟨bv, bs⟩ := b
  cases as <;> cases bs <;> simp [add, dbl] <;> omega

theorem dbl_sub (a b : Bdg) (h : dbl b ≤ dbl a) : dbl (sub a b) = dbl a - dbl b := by
  obtain ⟨av, as⟩ := a
  obtain ⟨bv, bs⟩ := b
  simp only [dbl] at h
  cases as <;> cases bs <;> simp only [Bool.toNat_false, Bool.toNat_true] at h <;>
    simp [sub, dbl] <;> omega

/-- The zero budget `0` (plain). -/
def zero : Bdg := ⟨0, false⟩
/-- The starred zero `0*`: the successor/predecessor step of the `ℕ*`
order. -/
def zeroStar : Bdg := ⟨0, true⟩

theorem dbl_zero : dbl zero = 0 := rfl
theorem dbl_zeroStar : dbl zeroStar = 1 := rfl

/-- Successor in the `ℕ*` order: `B ⊕ 0*`. -/
def succB (b : Bdg) : Bdg := add b zeroStar
/-- Predecessor in the `ℕ*` order: `B ⊖ 0*`. -/
def predB (b : Bdg) : Bdg := sub b zeroStar

theorem dbl_succB (b : Bdg) : dbl (succB b) = dbl b + 1 := by
  rw [succB, dbl_add, dbl_zeroStar]

theorem dbl_predB (b : Bdg) (h : 1 ≤ dbl b) : dbl (predB b) = dbl b - 1 := by
  rw [predB, dbl_sub b zeroStar (by rw [dbl_zeroStar]; exact h), dbl_zeroStar]

theorem le_add_right (a b : Bdg) : a ≤ add a b := by
  rw [le_iff_dbl, dbl_add]; omega

/-- The minimal bid that lets the opponent "trump" a bid `b` when the bidder's
budget is `B`: if the bidder holds the advantage (`B` starred)
and did not use it (`b` plain), the trump bid is `b` itself (a tie is won by
the player without the advantage); otherwise it is `b ⊕ 0*`. -/
def trump (B b : Bdg) : Bdg := if B.star && !b.star then b else add b zeroStar

theorem dbl_trump (B b : Bdg) :
    dbl (trump B b) = if B.star && !b.star then dbl b else dbl b + 1 := by
  unfold trump
  split_ifs with h
  · rfl
  · rw [dbl_add, dbl_zeroStar]

theorem dbl_le_trump (B b : Bdg) : dbl b ≤ dbl (trump B b) := by
  rw [dbl_trump]; split_ifs <;> omega

/-- The finite set of budgets `≤ B` (the legal bids of a player whose budget
is `B`). -/
def budgetsLE (B : Bdg) : Finset Bdg :=
  (((Finset.range (B.val + 1)) ×ˢ ({false, true} : Finset Bool)).image
    (fun p => ⟨p.1, p.2⟩)).filter (· ≤ B)

theorem mem_budgetsLE {B b : Bdg} : b ∈ budgetsLE B ↔ b ≤ B := by
  simp only [budgetsLE, Finset.mem_filter, Finset.mem_image, Finset.mem_product,
    Finset.mem_range, Finset.mem_insert, Finset.mem_singleton]
  constructor
  · rintro ⟨⟨⟨i, s⟩, ⟨_, _⟩, hieq⟩, hle⟩
    subst hieq
    exact hle
  · intro h
    obtain ⟨bv, bs⟩ := b
    obtain ⟨Bv, Bs⟩ := B
    have hd : dbl ⟨bv, bs⟩ ≤ dbl ⟨Bv, Bs⟩ := h
    have hval : bv ≤ Bv := by
      simp only [dbl] at hd
      cases bs <;> cases Bs <;>
        simp only [Bool.toNat_false, Bool.toNat_true] at hd ⊢ <;> omega
    refine ⟨⟨⟨bv, bs⟩, ⟨by simp; omega, by cases bs <;> simp⟩, rfl⟩, h⟩

theorem budgetsLE_nonempty (B : Bdg) : (budgetsLE B).Nonempty :=
  ⟨zero, mem_budgetsLE.mpr (by rw [le_iff_dbl, dbl_zero]; omega)⟩

theorem mem_budgetsLE_self (B : Bdg) : B ∈ budgetsLE B := mem_budgetsLE.mpr (le_refl B)

/-- The legal bids of a player whose budget is `B`: the elements of the
`ℕ*`-interval `[0, B]` that are plain whenever `B` is plain. Only the player
holding the tie-breaking advantage can bid starred values — bidding `b*`
means "bid `b` and use the advantage in case of a tie". -/
def legalBids (B : Bdg) : Finset Bdg := (budgetsLE B).filter (fun b => !b.star || B.star)

theorem mem_legalBids {B b : Bdg} : b ∈ legalBids B ↔ b ≤ B ∧ (!b.star || B.star) := by
  simp only [legalBids, Finset.mem_filter]
  constructor
  · intro h; exact ⟨mem_budgetsLE.mp h.1, h.2⟩
  · intro h; exact ⟨mem_budgetsLE.mpr h.1, h.2⟩

theorem legalBids_nonempty (B : Bdg) : (legalBids B).Nonempty :=
  ⟨zero, mem_legalBids.mpr ⟨by rw [le_iff_dbl, dbl_zero]; omega, by simp [zero]⟩⟩

/-- Who wins a bidding at Player-1 budget `B` with bids `b1`, `b2`: `true` iff
Player 1 wins. Bids are compared as elements of `ℕ*`; a tie is won by the
player *not* holding the tie-breaking advantage (Player 1 holds it iff `B` is
starred). -/
def presWinsBid (B b1 b2 : Bdg) : Bool :=
  if b2 < b1 then true else if b1 < b2 then false else !B.star

end Bdg

/-! ## The arena -/

/-- An energy bidding game arena `⟨V, E, k, w⟩`: a finite
directed graph with `N ≥ 1` vertices (each vertex has at least one outgoing
edge), total budget `k ∈ ℕ` (so Player 1's budget ranges over `[k]`, and
Player 2's budget is the complement), and integer edge weights bounded in
absolute value by `W`. -/
structure BArena where
  N : ℕ
  hN : 0 < N
  succ : Fin N → Finset (Fin N)
  hsucc : ∀ v, (succ v).Nonempty
  k : ℕ
  W : ℕ
  w : Fin N → Fin N → ℤ
  hw : ∀ u v, |w u v| ≤ W

namespace BArena

/-- The maximal element `k*` of the budget range `[k]`. -/
def kStar (G : BArena) : Bdg := ⟨G.k, true⟩
/-- The overflow threshold value `k + 1` (plain): the threshold budget of a
vertex from which no budget suffices. -/
def kPlus (G : BArena) : Bdg := ⟨G.k + 1, false⟩

theorem dbl_kStar (G : BArena) : Bdg.dbl (kStar G) = 2 * G.k + 1 := by simp [kStar, Bdg.dbl]
theorem dbl_kPlus (G : BArena) : Bdg.dbl (kPlus G) = 2 * G.k + 2 := by
  simp [kPlus, Bdg.dbl]; omega

theorem kStar_lt_kPlus (G : BArena) : kStar G < kPlus G := by
  rw [Bdg.lt_iff_dbl, dbl_kStar, dbl_kPlus]; omega

/-- A configuration `⟨v, B⟩`: the token is at vertex `v` and Player 1's
(Pres/Max) budget is `B`; Player 2's budget is implicitly `k* ⊖ B`. -/
structure Config (G : BArena) where
  v : Fin G.N
  B : Bdg
deriving DecidableEq

/-- The transition of the bidding game: the higher bidder moves the token
to their chosen vertex and pays their bid to the opponent; ties are won by
the player without the advantage. -/
def trans (G : BArena) (c : Config G) (a1 a2 : Bdg × Fin G.N) : Config G :=
  if Bdg.presWinsBid c.B a1.1 a2.1 then ⟨a1.2, Bdg.sub c.B a1.1⟩ else ⟨a2.2, Bdg.add c.B a2.1⟩

/-- A strategy: a history-dependent choice of a bid and a next vertex
(strategies are functions from histories to actions). -/
def Strategy (G : BArena) := List (Config G) → Bdg × Fin G.N

/-- Legality of a Player-1 (Pres) strategy: the bid stays within Player 1's
budget, is plain unless Player 1 holds the advantage, and the chosen vertex
is a neighbor of the current one. -/
def PresLegal (G : BArena) (σ : Strategy G) : Prop :=
  ∀ h c, h.getLast? = some c →
    (σ h).1 ≤ c.B ∧ ((σ h).1.star → c.B.star) ∧ (σ h).2 ∈ G.succ c.v

/-- Legality of a Player-2 (Cons) strategy: the bid stays within Player 2's
budget `k* ⊖ B`, is plain unless Player 2 holds the advantage (i.e. `B` is
plain), and the chosen vertex is a neighbor. -/
def ConsLegal (G : BArena) (τ : Strategy G) : Prop :=
  ∀ h c, h.getLast? = some c →
    (τ h).1 ≤ Bdg.sub (kStar G) c.B ∧ ((τ h).1.star → !(c.B.star)) ∧ (τ h).2 ∈ G.succ c.v

/-- The state of the play after `n` turns: the current configuration together
with the history (the list of configurations visited so far, oldest
first). -/
def playState (G : BArena) (σ τ : Strategy G) (c0 : Config G) (n : ℕ) :
    Config G × List (Config G) :=
  Nat.rec (motive := fun _ => Config G × List (Config G)) (c0, [c0])
    (fun _ p =>
      let c' := G.trans p.1 (σ p.2) (τ p.2)
      (c', p.2 ++ [c'])) n

/-- The configuration reached after `n` turns. -/
def play (G : BArena) (σ τ : Strategy G) (c0 : Config G) (n : ℕ) : Config G :=
  (G.playState σ τ c0 n).1
/-- The history after `n` turns (length `n + 1`, last entry = current). -/
def hist (G : BArena) (σ τ : Strategy G) (c0 : Config G) (n : ℕ) : List (Config G) :=
  (G.playState σ τ c0 n).2

theorem play_zero (G : BArena) (σ τ : Strategy G) (c0 : Config G) :
    G.play σ τ c0 0 = c0 := rfl

theorem play_succ (G : BArena) (σ τ : Strategy G) (c0 : Config G) (n : ℕ) :
    G.play σ τ c0 (n + 1) =
      G.trans (G.play σ τ c0 n) (σ (G.hist σ τ c0 n)) (τ (G.hist σ τ c0 n)) := rfl

theorem hist_length (G : BArena) (σ τ : Strategy G) (c0 : Config G) (n : ℕ) :
    (G.hist σ τ c0 n).length = n + 1 := by
  induction n with
  | zero => rfl
  | succ m ih =>
    show ((G.playState σ τ c0 m).2 ++ [_]).length = m + 1 + 1
    rw [List.length_append, List.length_singleton]
    show (G.hist σ τ c0 m).length + 1 = m + 2
    rw [ih]

theorem hist_getLast (G : BArena) (σ τ : Strategy G) (c0 : Config G) (n : ℕ) :
    (G.hist σ τ c0 n).getLast? = some (G.play σ τ c0 n) := by
  induction n with
  | zero => rfl
  | succ m ih =>
    show ((G.playState σ τ c0 m).2 ++ [_]).getLast? = some _
    rw [List.getLast?_append]
    rfl

/-- The accumulated weight along the first `n` turns of the play:
`sum(π≤n) = Σ_{j<n} w(v_j, v_{j+1})`. -/
def pathWeight (G : BArena) (σ τ : Strategy G) (c0 : Config G) (n : ℕ) : ℤ :=
  ∑ j ∈ Finset.range n, G.w (G.play σ τ c0 j).v (G.play σ τ c0 (j + 1)).v

theorem pathWeight_zero (G : BArena) (σ τ : Strategy G) (c0 : Config G) :
    G.pathWeight σ τ c0 0 = 0 := by simp [pathWeight]

theorem pathWeight_succ (G : BArena) (σ τ : Strategy G) (c0 : Config G) (n : ℕ) :
    G.pathWeight σ τ c0 (n + 1) =
      G.pathWeight σ τ c0 n + G.w (G.play σ τ c0 n).v (G.play σ τ c0 (n + 1)).v := by
  simp [pathWeight, Finset.sum_range_succ]

/-- Pres `M`-wins from `c0` with the explicit strategy `σ` (energy
objective): against every legal Cons strategy, the energy `M + sum(π≤m)`
stays non-negative forever. -/
def PresWinsWith (G : BArena) (σ : Strategy G) (M : ℤ) (c0 : Config G) : Prop :=
  ∀ τ : Strategy G, G.ConsLegal τ → ∀ n, 0 ≤ M + G.pathWeight σ τ c0 n

/-- Pres `M`-wins from `c0`: she has a legal strategy by which she
`M`-wins. -/
def PresWins (G : BArena) (M : ℤ) (c0 : Config G) : Prop :=
  ∃ σ, G.PresLegal σ ∧ G.PresWinsWith σ M c0

/-- Cons `M`-wins from `c0`: he has a legal strategy by which, against every
legal Pres strategy, the energy `M + sum(π≤m)` is negative at some
prefix. -/
def ConsWins (G : BArena) (M : ℤ) (c0 : Config G) : Prop :=
  ∃ τ, G.ConsLegal τ ∧ ∀ σ : Strategy G, G.PresLegal σ → ∃ n, M + G.pathWeight σ τ c0 n < 0

/-- Pres `M`-wins from `c0` in the truncated game `G_n`: the
energy stays non-negative for the first `n` turns. -/
def PresWinsTrunc (G : BArena) (n : ℕ) (M : ℤ) (c0 : Config G) : Prop :=
  ∃ σ, G.PresLegal σ ∧ ∀ τ : Strategy G, G.ConsLegal τ → ∀ m ≤ n,
    0 ≤ M + G.pathWeight σ τ c0 m

/-- Cons `M`-wins from `c0` in the truncated game `G_n`. -/
def ConsWinsTrunc (G : BArena) (n : ℕ) (M : ℤ) (c0 : Config G) : Prop :=
  ∃ τ, G.ConsLegal τ ∧ ∀ σ : Strategy G, G.PresLegal σ → ∃ m ≤ n,
    M + G.pathWeight σ τ c0 m < 0

end BArena

/-- Determinacy of reachability discrete-bidding games: in every bidding
arena, for every target set of vertices and every initial configuration,
either Cons can force a visit to the target or Pres can force avoiding it
forever. This is a proved result of the reviewed literature; it is packaged
as a hypothesis of the checkpoints that need it. -/
def ReachabilityDetermined : Prop :=
  ∀ (A : BArena) (T : Finset (Fin A.N)) (c0 : BArena.Config A),
    (∃ τ, BArena.ConsLegal A τ ∧ ∀ σ : BArena.Strategy A, BArena.PresLegal A σ →
        ∃ n, (BArena.play A σ τ c0 n).v ∈ T) ∨
      (∃ σ, BArena.PresLegal A σ ∧ ∀ τ : BArena.Strategy A, BArena.ConsLegal A τ →
        ∀ n, (BArena.play A σ τ c0 n).v ∉ T)

namespace BArena

/-! ## The value-iteration recursion -/

/-- `enwin(v, B, b)`: the energy Pres needs if she bids `b` at
`⟨v, B⟩` and wins the bidding, moving to the best neighbor, given the
previous-stage values `prev`. -/
def enWinN (G : BArena) (prev : Fin G.N → Bdg → ℕ) (v : Fin G.N) (B b : Bdg) : ℕ :=
  ((G.succ v).image (fun u => Int.toNat ((prev u (Bdg.sub B b) : ℤ) - G.w v u))).min'
    (Finset.image_nonempty.mpr (G.hsucc v))

/-- `enlose(v, B, b)`: the energy Pres needs if she bids `b`
and loses the bidding (Cons trumps and moves to the worst neighbor). Only
meaningful when `B ⊕ trump(B, b) ≤ k*` (Cons can afford the trump bid). -/
def enLoseN (G : BArena) (prev : Fin G.N → Bdg → ℕ) (v : Fin G.N) (B b : Bdg) : ℕ :=
  ((G.succ v).image
    (fun u => Int.toNat ((prev u (Bdg.add B (Bdg.trump B b)) : ℤ) - G.w v u))).max'
    (Finset.image_nonempty.mpr (G.hsucc v))

/-- `ennext(v, B, b)`: the maximum of the win and lose cases
when Cons can afford to trump (`B ⊕ trump(B, b) ≤ k*`, equivalently
`< k + 1`), and only the win case otherwise. -/
def enNextN (G : BArena) (prev : Fin G.N → Bdg → ℕ) (v : Fin G.N) (B b : Bdg) : ℕ :=
  if Bdg.add B (Bdg.trump B b) ≤ kStar G
  then max (G.enWinN prev v B b) (G.enLoseN prev v B b)
  else G.enWinN prev v B b

/-- The value-iteration recursion `µ_n`: `µ_0 ≡ 0` and
`µ_{n+1}(v, B) = min_{b} ennext(v, B, b)` over the legal bids of the budget
`B` (the source text writes `b ≤ B`; the legal set excludes starred bids for
the player without the advantage, per the model's source convention). -/
def muN (G : BArena) : ℕ → Fin G.N → Bdg → ℕ
  | 0, _, _ => 0
  | n + 1, v, B =>
      ((Bdg.legalBids B).image (fun b => G.enNextN (G.muN n) v B b)).min'
        (Finset.image_nonempty.mpr (Bdg.legalBids_nonempty B))

/-- The trimming threshold of the trimmed sequence: the number of
configurations `|V|·(2k+2)` times `W`. -/
def cap (G : BArena) : ℕ := G.N * (2 * G.k + 2) * G.W

/-- The post-truncated sequence `µ̃_n`: `µ_n` while `µ_n ≤ cap`,
else `∞`. This does not feed truncated values back into the recursion;
the operator iterate used to define `mu` is `muC`. -/
def muTilde (G : BArena) (n : ℕ) (v : Fin G.N) (B : Bdg) : WithTop ℕ :=
  if G.muN n v B ≤ G.cap then (G.muN n v B : WithTop ℕ) else ⊤

/-- An a priori stabilization horizon for the recursively trimmed operator
iterate `muC` on the `N·(2k+2)` legal configurations. Each coordinate has
values in `{0, ..., cap} ∪ {∞}` and can strictly increase at most `cap + 2`
times. An unchanged iterate stays unchanged, so this bounds stabilization.
This argument does not apply to the post-truncated sequence `muTilde`. -/
def stabSteps (G : BArena) : ℕ := G.N * (2 * G.k + 2) * (G.cap + 2) + 1

theorem stabSteps_pos (G : BArena) : 0 < G.stabSteps := by
  unfold stabSteps; omega

theorem muTilde_le_cap_or_top (G : BArena) (n : ℕ) (v : Fin G.N) (B : Bdg) :
    G.muTilde n v B ≤ (G.cap : WithTop ℕ) ∨ G.muTilde n v B = ⊤ := by
  unfold muTilde
  split_ifs with h
  · exact Or.inl (WithTop.coe_le_coe.mpr h)
  · exact Or.inr rfl

end BArena

/-- Subtracting an edge weight from a possibly-infinite value: `⊤` stays `⊤`;
on finite values it is the truncated subtraction `max{m − w, 0}` used in
the recursion. -/
def subW (x : WithTop ℕ) (w : ℤ) : WithTop ℕ :=
  WithTop.recTopCoe ⊤ (fun m => ((Int.toNat ((m : ℤ) - w) : ℕ) : WithTop ℕ)) x

theorem subW_top (w : ℤ) : subW ⊤ w = ⊤ := rfl
theorem subW_coe (m : ℕ) (w : ℤ) :
    subW (m : WithTop ℕ) w = ((Int.toNat ((m : ℤ) - w) : ℕ) : WithTop ℕ) := rfl

namespace BArena

/-- `enwin` over possibly-infinite values (for the fixed-point equation). -/
def enWinT (G : BArena) (f : Fin G.N → Bdg → WithTop ℕ) (v : Fin G.N) (B b : Bdg) :
    WithTop ℕ :=
  (G.succ v).inf' (G.hsucc v) (fun u => subW (f u (Bdg.sub B b)) (G.w v u))

/-- `enlose` over possibly-infinite values. -/
def enLoseT (G : BArena) (f : Fin G.N → Bdg → WithTop ℕ) (v : Fin G.N) (B b : Bdg) :
    WithTop ℕ :=
  (G.succ v).sup' (G.hsucc v) (fun u => subW (f u (Bdg.add B (Bdg.trump B b))) (G.w v u))

/-- `ennext` over possibly-infinite values. -/
def enNextT (G : BArena) (f : Fin G.N → Bdg → WithTop ℕ) (v : Fin G.N) (B b : Bdg) :
    WithTop ℕ :=
  if Bdg.add B (Bdg.trump B b) ≤ kStar G
  then max (G.enWinT f v B b) (G.enLoseT f v B b)
  else G.enWinT f v B b

/-- The one-step value-iteration operator on `ℕ∞`-valued functions. -/
def phi (G : BArena) (f : Fin G.N → Bdg → WithTop ℕ) (v : Fin G.N) (B : Bdg) :
    WithTop ℕ :=
  (Bdg.legalBids B).inf' (Bdg.legalBids_nonempty B) (fun b => G.enNextT f v B b)

/-- Truncate a possibly-infinite energy value at `cap`, preserving infinity. -/
def trim (G : BArena) (x : WithTop ℕ) : WithTop ℕ :=
  if x ≤ (G.cap : WithTop ℕ) then x else ⊤

theorem trim_le_cap_or_top (G : BArena) (x : WithTop ℕ) :
    G.trim x ≤ (G.cap : WithTop ℕ) ∨ G.trim x = ⊤ := by
  unfold trim
  split_ifs with h
  · exact Or.inl h
  · exact Or.inr rfl

/-- Algorithm 1's recursively trimmed value iteration: `muC 0 = 0` and
`muC (n+1) = trim (phi (muC n))` pointwise. The Bellman step reads the
previous trimmed values, and `subW` keeps infinity sticky. -/
def muC (G : BArena) : ℕ → Fin G.N → Bdg → WithTop ℕ
  | 0, _, _ => 0
  | n + 1, v, B => G.trim (G.phi (G.muC n) v B)

theorem muC_le_cap_or_top (G : BArena) (n : ℕ) (v : Fin G.N) (B : Bdg) :
    G.muC n v B ≤ (G.cap : WithTop ℕ) ∨ G.muC n v B = ⊤ := by
  cases n with
  | zero => exact Or.inl (WithTop.coe_le_coe.mpr (Nat.zero_le _))
  | succ n => exact G.trim_le_cap_or_top (G.phi (G.muC n) v B)

/-- The fixed-point value `µ`: the recursively trimmed operator iterate
at the stabilization horizon, as in Algorithm 1. -/
def mu (G : BArena) (v : Fin G.N) (B : Bdg) : WithTop ℕ :=
  G.muC G.stabSteps v B

theorem mu_eq_muC (G : BArena) (v : Fin G.N) (B : Bdg) :
    G.mu v B = G.muC G.stabSteps v B := rfl

theorem mu_le_cap_or_eq_top (G : BArena) (v : Fin G.N) (B : Bdg) :
    G.mu v B ≤ (G.cap : WithTop ℕ) ∨ G.mu v B = ⊤ :=
  G.muC_le_cap_or_top G.stabSteps v B

end BArena

namespace BArena

/-! ## Threshold budgets -/

/-- The budgets with finite fixed-point energy threshold at `v`. -/
def finiteMu (G : BArena) (v : Fin G.N) : Finset Bdg :=
  (Bdg.budgetsLE (kStar G)).filter (fun B => G.mu v B ≠ ⊤)

/-- The threshold budget `Th(v)`: the minimal budget with
finite energy threshold, or `k + 1` if every budget has threshold `∞`. -/
def Th (G : BArena) (v : Fin G.N) : Bdg :=
  if h : (G.finiteMu v).Nonempty then (G.finiteMu v).min' h else kPlus G

/-- The defining property of `Th`: it is the minimal budget whose fixed-point
energy is finite, and it is `k + 1` iff no budget has finite energy. -/
theorem Th_spec (G : BArena) (v : Fin G.N) :
    (G.Th v ≤ kStar G → G.mu v (G.Th v) ≠ ⊤) ∧
    (∀ B, B ≤ kStar G → B < G.Th v → G.mu v B = ⊤) ∧
      (G.Th v = kPlus G ↔ ∀ B, B ≤ kStar G → G.mu v B = ⊤) := by
  unfold Th finiteMu
  split_ifs with h
  · have hmem := Finset.min'_mem ((Bdg.budgetsLE (kStar G)).filter fun B => G.mu v B ≠ ⊤) h
    rw [Finset.mem_filter] at hmem
    obtain ⟨hmemle, hmu⟩ := hmem
    have hk : ((Bdg.budgetsLE (kStar G)).filter fun B => G.mu v B ≠ ⊤).min' h ≤ kStar G :=
      Bdg.mem_budgetsLE.mp hmemle
    refine ⟨fun _ => hmu, ?_, ?_⟩
    · intro B hB hlt
      by_contra hne
      have hBS : B ∈ (Bdg.budgetsLE (kStar G)).filter (fun B => G.mu v B ≠ ⊤) :=
        Finset.mem_filter.mpr ⟨Bdg.mem_budgetsLE.mpr hB, hne⟩
      exact absurd (Finset.min'_le _ _ hBS) (not_le.mpr hlt)
    · constructor
      · intro heq
        have h1 : kStar G < kPlus G := kStar_lt_kPlus G
        rw [← heq] at h1
        exact absurd hk (not_le.mpr h1)
      · intro hall
        exact absurd (hall _ hk) hmu
  · push Not at h
    refine ⟨?_, ?_, ?_⟩
    · intro hle
      exact absurd hle (not_le.mpr (kStar_lt_kPlus G))
    · intro B hB _
      by_contra hne
      have hmem : B ∈ (Bdg.budgetsLE (kStar G)).filter (fun B => G.mu v B ≠ ⊤) :=
        Finset.mem_filter.mpr ⟨Bdg.mem_budgetsLE.mpr hB, hne⟩
      rw [h] at hmem
      exact Finset.notMem_empty B hmem
    · constructor
      · intro _ B hB
        by_contra hne
        have hmem : B ∈ (Bdg.budgetsLE (kStar G)).filter (fun B => G.mu v B ≠ ⊤) :=
          Finset.mem_filter.mpr ⟨Bdg.mem_budgetsLE.mpr hB, hne⟩
        rw [h] at hmem
        exact Finset.notMem_empty B hmem
      · intro _; rfl


/-- `Trim(v, B)`: whichever of `Th(v)` or `Th(v) ⊕ 0*` agrees
with `B` on the tie-breaking advantage. -/
def Trim (G : BArena) (v : Fin G.N) (B : Bdg) : Bdg :=
  if B.star == (G.Th v).star then G.Th v else Bdg.add (G.Th v) Bdg.zeroStar

/-- Budget-agnostic strategies (in the trimmed form): the bid chosen at a
history ending in `⟨v, B⟩` with `B ≥ Th(v)` depends only on `v` and
`Trim(v, B)`. -/
def IsBudgetAgnostic (G : BArena) (σ : Strategy G) : Prop :=
  ∀ (h1 h2 : List (Config G)) (v : Fin G.N) (B1 B2 : Bdg),
    h1.getLast? = some ⟨v, B1⟩ → h2.getLast? = some ⟨v, B2⟩ →
    B1 ≤ kStar G → B2 ≤ kStar G → G.Th v ≤ B1 → G.Th v ≤ B2 →
    G.Trim v B1 = G.Trim v B2 → (σ h1).1 = (σ h2).1

/-- `max_v Energy(v, Th(v))`: the largest finite energy threshold at a
threshold budget (vertices with `Th(v) = k + 1` contribute `0`). -/
def maxThEnergy (G : BArena) : ℕ :=
  Finset.univ.sup (fun v =>
    if h : G.Th v ≤ kStar G then (G.mu v (G.Th v)).untop ((G.Th_spec v).1 h) else 0)

/-- The explicit initial energy bound of the main theorem:
`(k + 1)·(W + max_v Energy(v, Th(v)))`. -/
def mainEnergyBound (G : BArena) : ℕ := (G.k + 1) * (G.W + G.maxThEnergy)

end BArena

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- but the fixed part above and the main-theorem statement must not be modified.

namespace BArena

-- @[checkpoint c8 difficulty=hard]
/-- The main theorem: there is a legal, budget-agnostic Pres strategy that
`M`-wins from every configuration `⟨v, B⟩` with `B ≥ Th(v)`, with the
explicit initial energy `M = (k + 1)·(W + max_v Energy(v, Th(v)))` (the
fixed-point energy `µ` at the threshold budget). Determinacy of
reachability discrete-bidding games is given as the hypothesis `hdet`. -/
theorem budget_agnostic_strategy_exists (G : BArena) (hdet : ReachabilityDetermined) :
    ∃ σ : Strategy G, PresLegal G σ ∧ IsBudgetAgnostic G σ ∧
      ∀ (v : Fin G.N) (B : Bdg) (hB : B ≤ kStar G), G.Th v ≤ B →
        PresWinsWith G σ ((G.mainEnergyBound : ℕ) : ℤ) ⟨v, B⟩ := by
  -- CHECKPOINT budget_agnostic_strategy_exists BEGIN
  sorry
  -- CHECKPOINT budget_agnostic_strategy_exists END

end BArena

end DiscreteBidding
