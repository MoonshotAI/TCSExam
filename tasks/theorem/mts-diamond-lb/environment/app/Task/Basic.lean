/-
Self-contained statement layer for a theorem in online algorithms: a
distributional lower bound of Ω((log n / log log n)²) for small-set
chasing (MSS) on n-point metric spaces.

The fixed part (everything above the end-of-fixed-part marker line)
contains only the online game framework the main theorem's statement
needs: deterministic online algorithms for small-set chasing with a
feasibility field, movement costs, the offline optimal cost, uniform
expectations over finite sample spaces, and the distributional
lower-bound predicate.  The full construction (the recursive diamond
family, the three-stage hard random request sequence, the escape-price
induction) is not provided.  Fidelity notes live in `tests/reference/`.
-/

import Mathlib

set_option linter.unusedSectionVars false

namespace MTSDiamondLB

/-! ## The online game framework -/

/-- A deterministic online algorithm for small-set chasing on `M` from
`start`: `next hist S` is the point the algorithm moves to when the request
history is `hist` and the current request is `S`; feasibility (the response
lies in the request set) is a structure field. -/
structure DetAlg (M : Type) [Fintype M] [MetricSpace M] (start : M) where
  next : List (Finset M) → Finset M → M
  next_mem : ∀ hist S, S.Nonempty → next hist S ∈ S

/-- The partial cost of `A` serving `rest`, started at position `cur` with
request history `hist`. -/
def costAux {M : Type} [Fintype M] [MetricSpace M] {start : M}
    (A : DetAlg M start) (hist : List (Finset M)) (cur : M) :
    List (Finset M) → ℝ
  | [] => 0
  | S :: rest =>
    dist cur (A.next hist S) + costAux A (hist ++ [S]) (A.next hist S) rest

/-- The final position of `A` after serving `rest` from `cur`. -/
def endPos {M : Type} [Fintype M] [MetricSpace M] {start : M}
    (A : DetAlg M start) (hist : List (Finset M)) (cur : M) :
    List (Finset M) → M
  | [] => cur
  | S :: rest => endPos A (hist ++ [S]) (A.next hist S) rest

/-- The total cost of `A` on the request sequence `ρ` from `start`. -/
def algCost {M : Type} [Fintype M] [MetricSpace M] {start : M}
    (A : DetAlg M start) (ρ : List (Finset M)) : ℝ :=
  costAux A [] start ρ

lemma costAux_append {M : Type} [Fintype M] [MetricSpace M] {start : M}
    (A : DetAlg M start) (hist : List (Finset M)) (cur : M)
    (l₁ l₂ : List (Finset M)) :
    costAux A hist cur (l₁ ++ l₂) =
      costAux A hist cur l₁ +
        costAux A (hist ++ l₁) (endPos A hist cur l₁) l₂ := by
  induction l₁ generalizing hist cur with
  | nil => simp [costAux, endPos]
  | cons S rest ih =>
    simp only [List.cons_append, costAux, endPos]
    rw [ih]
    rw [List.append_assoc, List.singleton_append]
    ring

open Classical in
/-- The offline optimal cost: the minimum, over all valid trajectories, of
the total movement.  Written as a recursion on the request list (dynamic
programming over positions). -/
noncomputable def optCost {M : Type} [Fintype M] [MetricSpace M] :
    M → List (Finset M) → ℝ
  | _, [] => 0
  | cur, S :: rest =>
    if h : S.Nonempty then
      S.inf' h (fun x => dist cur x + optCost x rest)
    else 0

lemma optCost_nil {M : Type} [Fintype M] [MetricSpace M] (cur : M) :
    optCost cur [] = 0 := rfl

lemma optCost_cons {M : Type} [Fintype M] [MetricSpace M] (cur : M)
    (S : Finset M) (rest : List (Finset M)) (hS : S.Nonempty) :
    optCost cur (S :: rest) =
      S.inf' hS (fun x => dist cur x + optCost x rest) := by
  simp only [optCost]
  rw [dif_pos hS]

/-- Any trajectory serving a sequence that ends with the singleton `{v}` pays
at least `dist cur v` (iterated triangle inequality). -/
lemma optCost_ge_dist {M : Type} [Fintype M] [MetricSpace M] :
    ∀ (ρ : List (Finset M)) (cur v : M),
      (∀ S ∈ ρ, S.Nonempty) → ρ.getLast? = some {v} →
        dist cur v ≤ optCost cur ρ := by
  intro ρ
  induction ρ with
  | nil =>
    intro cur v _ h
    simp at h
  | cons S rest ih =>
    intro cur v hne hlast
    have hS : S.Nonempty := hne S (by simp)
    rcases rest with _ | ⟨S', rest'⟩
    · -- ρ = [S], so the last request forces S = {v}
      have hSv : S = {v} := by
        have e : ([S] : List (Finset M)).getLast? = some S := rfl
        rw [e] at hlast
        exact Option.some.inj hlast
      subst hSv
      rw [optCost_cons cur {v} [] hS]
      rw [Finset.inf'_singleton, optCost_nil]
      have hd : 0 ≤ dist cur v := dist_nonneg
      linarith
    · -- induct on the tail S' :: rest'
      have hlast' : (S' :: rest').getLast? = some {v} := by
        have e : (S :: S' :: rest').getLast? = (S' :: rest').getLast? := rfl
        rw [e] at hlast
        exact hlast
      have hne' : ∀ T ∈ S' :: rest', T.Nonempty :=
        fun T hT => hne T (by simp [hT])
      rw [optCost_cons cur S (S' :: rest') hS]
      apply Finset.le_inf'
      intro x hx
      have h1 : dist x v ≤ optCost x (S' :: rest') := ih x v hne' hlast'
      have h2 : dist cur v ≤ dist cur x + dist x v := dist_triangle _ _ _
      linarith

/-- The uniform expectation over a finite sample space. -/
noncomputable def Expect {Ω : Type} [Fintype Ω] (f : Ω → ℝ) : ℝ :=
  (∑ ω, f ω) / (Fintype.card Ω : ℝ)

/-- The distributional lower-bound predicate (the finite witness form of the
printed definition): there is a finite sample space and a distribution of
request sequences with positive expected optimal cost such that every
deterministic online algorithm pays, in expectation, at least `C` times the
expected optimal cost. -/
def DistLB (M : Type) [Fintype M] [MetricSpace M] (start : M) (C : ℝ) : Prop :=
  ∃ (Ω : Type) (finΩ : Fintype Ω) (_ : Nonempty Ω) (ρ : Ω → List (Finset M)),
    letI := finΩ
    (∀ ω, ∀ S ∈ ρ ω, S.Nonempty) ∧
    0 < Expect (fun ω => optCost start (ρ ω)) ∧
    ∀ A : DetAlg M start,
      Expect (fun ω => algCost A (ρ ω)) ≥ C * Expect (fun ω => optCost start (ρ ω))

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

/-! ## Checkpoint zone -/

-- @[checkpoint main difficulty=hard]
/-- The main theorem: there is a constant `c > 0` such that for all
sufficiently large `n` there is an `n`-point metric space on which
small-set chasing admits a distributional lower bound of
`c·(log₂ n / log₂ log₂ n)²`. -/
theorem mss_loglog_lower :
    ∃ c : ℝ, 0 < c ∧ ∃ n₀ : ℕ, ∀ n : ℕ, n₀ ≤ n →
      ∃ (M : Type) (finM : Fintype M) (metM : MetricSpace M) (_ : Nonempty M) (start : M),
        @Fintype.card M finM = n ∧
        @DistLB M finM metM start
          (c * (Real.logb 2 (n : ℝ) / Real.logb 2 (Real.logb 2 (n : ℝ))) ^ 2) := by
  -- CHECKPOINT mss_loglog_lower BEGIN
  sorry
  -- CHECKPOINT mss_loglog_lower END
