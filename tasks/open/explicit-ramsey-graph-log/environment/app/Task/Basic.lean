/-
Self-contained statement layer for the explicit-Ramsey-graph problem
("explicit-ramsey-graph-log"), pinned to the canonical candidate
construction: the Paley-graph Ramsey conjecture, in its polylogarithmic
form — clique number and independence number of the Paley graph on q
vertices are (log q)^{O(1)}.

Background: Erdős (1947) proved by the probabilistic method that graphs
with clique number and independence number at most 2·log₂ N exist; the
open problem is an *explicit* (polynomial-time constructible) family, with
the current frontier K = (log N)^{O(1)} (Xin Li, FOCS 2023).  The Paley
graph family is the canonical candidate: adjacency is a quadratic-residue
test, so the graphs are trivially explicit, and the conjecture below is
exactly the statement that they achieve a polylogarithmic Ramsey bound.

Why the polylogarithmic form: the stronger O(log q) bound is known to be
FALSE for the Paley family.  Graham & Ringrose (1990) proved that for
infinitely many primes p ≡ 1 (mod 4) the least quadratic non-residue n(p)
satisfies n(p) ≥ c·log p·log log log p; the set {0,…,n(p)−1} is then a
clique in the Paley graph P_p, so ω(P_p) ≥ c·log p·log log log p exceeds
every C·⌊log₂ p⌋.  The genuinely open question is the polylogarithmic
upper bound: the best known unconditional upper bound is ~√q
(Hanson–Petridis 2021; Yip 2020, arXiv:2004.01175), while the best known
lower bounds (Graham–Ringrose 1990, log p·log log log p; Montgomery 1971
under GRH, log p·log log p) fall short of any (log p)^{1+ε} — so both
proving and refuting the statement below would be new.  Following the
pool's reflow decision (reflow-a.json), "explicit" is pinned to this
candidate family — see `tests/reference/concept-ledger.md`.

The fixed part (everything above the end-of-fixed-part marker line) is the
definition layer the statements need.  Fidelity notes live in
`tests/reference/`.
-/

import Mathlib

-- Kernel `decide` over larger finite checks recurses deeper than the
-- default limit; raise it for the whole file (definition layer and all
-- slots).
set_option maxRecDepth 8192

namespace ExplicitRamsey

/-! ## The Paley graph -/

/-- The Paley graph on `ZMod q`, for `q` a prime with `q ≡ 1 (mod 4)`:
vertices are the field elements, and two distinct vertices are adjacent iff
their difference is a square.  The condition `q ≡ 1 (mod 4)` makes `-1` a
square in `ZMod q`, so adjacency is symmetric. -/
def paleyGraph (q : ℕ) (hqp : q.Prime) (hq4 : q % 4 = 1) : SimpleGraph (ZMod q) where
  Adj x y := x ≠ y ∧ IsSquare (x - y)
  symm := by
    refine ⟨fun x y h => ?_⟩
    obtain ⟨hne, hsq⟩ := h
    haveI := Fact.mk hqp
    haveI : NeZero q := ⟨hqp.pos.ne'⟩
    refine ⟨hne.symm, ?_⟩
    have hneg : IsSquare (-1 : ZMod q) := by
      rw [FiniteField.isSquare_neg_one_iff, ZMod.card, hq4]
      decide
    have hflip : y - x = (-1) * (x - y) := by ring
    rw [hflip]
    exact hneg.mul hsq
  loopless := ⟨fun x h => h.1 rfl⟩

/-! ## Cheap decidability via a Boolean residue test -/

/-- Quadratic-residue test on `ZMod q` as a Bool: scans canonical
representatives.  The bridge to `IsSquare` makes Paley adjacency cheap to
decide. -/
def qrBool (q : ℕ) (a : ZMod q) : Bool :=
  (List.range q).any fun n => a.val = (n * n) % q

/-- The bridge: a Boolean scan decides the `IsSquare` predicate. -/
theorem isSquare_iff_qrBool (q : ℕ) [NeZero q] (a : ZMod q) :
    IsSquare a ↔ qrBool q a = true := by
  unfold qrBool
  rw [List.any_eq_true]
  constructor
  · rintro ⟨r, rfl⟩
    exact ⟨r.val, List.mem_range.mpr (ZMod.val_lt r), by simp [ZMod.val_mul]⟩
  · rintro ⟨n, hn, hval⟩
    refine ⟨(n : ZMod q), ?_⟩
    have hval' : a.val = (n * n) % q := of_decide_eq_true hval
    have h1 : (a.val : ZMod q) = a := by
      simp [ZMod.natCast_val]
    rw [← h1, hval', ZMod.natCast_mod]
    push_cast
    ring

/-- Adjacency in a Paley graph is decidable, via the cheap Bool residue
test (kernel evaluation goes through `qrBool`, not the `IsSquare`
existential). -/
instance paleyAdjDecidable (q : ℕ) (hqp : q.Prime) (hq4 : q % 4 = 1) :
    DecidableRel (paleyGraph q hqp hq4).Adj := fun x y =>
  haveI : NeZero q := ⟨hqp.pos.ne'⟩
  decidable_of_iff _ (and_congr_right' (isSquare_iff_qrBool q (x - y))).symm

/-! ## The conjecture -/

/-- The Paley-graph Ramsey conjecture, polylogarithmic form: there is a
universal exponent `k` such that for every prime `q ≡ 1 (mod 4)`, the
Paley graph on `q` vertices has neither a clique nor an independent set of
size `(⌊log₂ q⌋ + 1)^k + 1` — equivalently, its clique number and
independence number are both at most `(⌊log₂ q⌋ + 1)^k`.  The `+ 1` in
the base keeps the bound away from 1 for small `q` (q = 5 has
`Nat.log 2 5 = 2`, so the base is 3); the outer `+ 1` is the usual
`CliqueFree (B + 1)` ↔ `ω ≤ B` translation.  With `k = 0` the bound is 1,
which asks for an edgeless graph and is false for every Paley graph — the
existential content lives in large `k`, so `k = 0` neither vacuously
satisfies nor trivializes the statement. -/
def PaleyPolylogRamsey : Prop :=
  ∃ k : ℕ, ∀ q : ℕ, ∀ hqp : q.Prime, ∀ hq4 : q % 4 = 1,
    (paleyGraph q hqp hq4).CliqueFree ((Nat.log 2 q + 1)^k + 1) ∧
    (paleyGraph q hqp hq4)ᶜ.CliqueFree ((Nat.log 2 q + 1)^k + 1)

/-! ## `CliqueFree` in checked form -/

/-- `CliqueFree` unfolds to the checked `∀`-form: rewrite with this (or
`show` the `∀`-form) before calling `decide`, which cannot see through the
definition on its own. -/
theorem cliqueFree_def {V : Type} [Fintype V] (G : SimpleGraph V) (n : ℕ) :
    G.CliqueFree n ↔ ∀ t : Finset V, ¬ G.IsNClique n t := Iff.rfl

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- but the fixed part above and the theorem statements must not be modified.

/-- Main slot (proof): the conjecture itself. -/
theorem conj : PaleyPolylogRamsey := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

/-- Main slot (disproof): the negation of the conjecture. -/
theorem refuted : ¬ PaleyPolylogRamsey := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

end ExplicitRamsey
