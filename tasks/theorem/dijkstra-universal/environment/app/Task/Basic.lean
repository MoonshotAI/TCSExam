/-
Self-contained statement layer for a theorem in algorithms: the universal
optimality of Dijkstra's algorithm with a working-set-bound heap.

The fixed part (everything above the end-of-fixed-part marker line) is the
definition layer the main theorem's statement needs: directed graphs with a
source, walks, simple paths and the true distance `trueDist`; vertex orders
(as permutations of `Fin n`), distance orders and the counts `numDistOrders`
(D) and `maxForwardArcs` (F); arc lengths and the true-distance-order
predicate; the comparison model as linear-function decision trees; the time
model as decision trees over a bare vertex set with incidence-list access
nodes (correctness is quantified over every graph on that vertex set with
that source), with the projection of a time tree to a comparison tree;
Dijkstra traces as structured scan-block event logs with the working-set
size `W` and the time/comparison cost functions; and an interval-DAG bound
packaged as the hypothesis `IntervalDAGBound`. Fidelity notes live in
`tests/reference/`.
-/

import Mathlib

namespace DijkstraUniversal

/-! ## List helpers (last-element access on appended lists) -/

theorem getLast?_append_single {α : Type*} : ∀ (l : List α) (a : α),
    (l ++ [a]).getLast? = some a := by
  intro l
  induction l with
  | nil => intro a; rfl
  | cons x l' ih =>
    intro a
    cases hr : l' ++ [a] with
    | nil => exact absurd hr (List.append_ne_nil_of_right_ne_nil _ (List.cons_ne_nil _ _))
    | cons z s =>
      rw [List.cons_append, hr, List.getLast?_cons_cons, ← hr, ih a]

theorem getLast?_append_pair {α : Type*} : ∀ (l : List α) (a b : α),
    (l ++ [a, b]).getLast? = some b := by
  intro l
  induction l with
  | nil => intro a b; rfl
  | cons x l' ih =>
    intro a b
    cases hr : l' ++ [a, b] with
    | nil => exact absurd hr (List.append_ne_nil_of_right_ne_nil _ (List.cons_ne_nil _ _))
    | cons z s =>
      rw [List.cons_append, hr, List.getLast?_cons_cons, ← hr, ih a b]

theorem getLast?_append_cons {α : Type*} : ∀ (l : List α) (x : α) (r : List α),
    (l ++ x :: r).getLast? = (x :: r).getLast? := by
  intro l
  induction l with
  | nil => intros; rfl
  | cons y l' ih =>
    intro x r
    cases hr : l' ++ x :: r with
    | nil => exact absurd hr (List.append_ne_nil_of_right_ne_nil _ (List.cons_ne_nil _ _))
    | cons z s =>
      rw [List.cons_append, hr, List.getLast?_cons_cons, ← hr, ih x r]

/-- A list of length at least 2 ends in two elements. -/
theorem list_split_last_two {α : Type*} : ∀ {p : List α}, 2 ≤ p.length →
    ∃ l a b, p = l ++ [a, b] := by
  intro p
  induction p with
  | nil => simp
  | cons x t iht =>
    intro h
    cases t with
    | nil => simp at h
    | cons y t' =>
      cases t' with
      | nil => exact ⟨[], x, y, rfl⟩
      | cons z t'' =>
        obtain ⟨l, a, b, hl⟩ := iht (by simp)
        exact ⟨x :: l, a, b, by simp [hl]⟩

/-- Splitting a list at the first occurrence of a member. -/
theorem list_split_first {α : Type*} [DecidableEq α] {x : α} {t : List α} (h : x ∈ t) :
    ∃ B C, t = B ++ x :: C ∧ x ∉ B := by
  induction t with
  | nil => simp at h
  | cons y t' iht =>
    by_cases hxy : x = y
    · exact ⟨[], t', by simp [hxy], by simp⟩
    · have hmem : x ∈ t' := by
        rcases List.mem_cons.mp h with h' | h'
        · exact absurd h' hxy
        · exact h'
      obtain ⟨B, C, hB, hBx⟩ := iht hmem
      exact ⟨y :: B, C, by simp [hB], by simp [hBx, hxy]⟩

/-! ## Adjacency chaining on lists (self-contained `List.Chain'` replacement) -/

/-- Adjacent-pair chaining under a relation, as an inductive predicate so
that case analysis and construction are fully under our control. -/
inductive ChainAdj {α : Type*} (R : α → α → Prop) : List α → Prop
  | nil : ChainAdj R []
  | singleton (a : α) : ChainAdj R [a]
  | cons {a b : α} {t : List α} : R a b → ChainAdj R (b :: t) → ChainAdj R (a :: b :: t)

theorem ChainAdj.tail {α : Type*} {R : α → α → Prop} {a : α} {l : List α}
    (h : ChainAdj R (a :: l)) : ChainAdj R l := by
  cases l with
  | nil => exact ChainAdj.nil
  | cons b t => cases h with | cons _ h' => exact h'

theorem ChainAdj.head_arc {α : Type*} {R : α → α → Prop} {a b : α} {t : List α}
    (h : ChainAdj R (a :: b :: t)) : R a b := by
  cases h with
  | cons h1 _ => exact h1

theorem ChainAdj.append_iff {α : Type*} {R : α → α → Prop} :
    ∀ (l₁ l₂ : List α) (a b : α), l₁.getLast? = some a → l₂.head? = some b →
      (ChainAdj R (l₁ ++ l₂) ↔ ChainAdj R l₁ ∧ R a b ∧ ChainAdj R l₂) := by
  intro l₁
  induction l₁ with
  | nil => intro l₂ a b h1 h2; simp at h1
  | cons x t ih =>
    intro l₂ a b h1 h2
    cases t with
    | nil =>
      simp only [List.getLast?_singleton, Option.some.injEq] at h1
      subst h1
      cases l₂ with
      | nil => simp at h2
      | cons y r =>
        simp only [List.head?_cons, Option.some.injEq] at h2
        subst h2
        constructor
        · intro h
          cases h with
          | cons h1 h2 => exact ⟨ChainAdj.singleton _, h1, h2⟩
        · intro h
          exact ChainAdj.cons h.2.1 h.2.2
    | cons y t' =>
      have h1' : (y :: t').getLast? = some a := by rwa [List.getLast?_cons_cons] at h1
      have ihh := ih l₂ a b h1' h2
      constructor
      · intro h
        have e : (x :: y :: t') ++ l₂ = x :: y :: (t' ++ l₂) := rfl
        rw [e] at h
        cases h with
        | cons h1 h2 =>
          have hh := ihh.mp h2
          exact ⟨ChainAdj.cons h1 hh.1, hh.2⟩
      · intro h
        obtain ⟨hc, hr⟩ := h
        cases hc with
        | cons h1 h2 =>
          exact ChainAdj.cons h1 (ihh.mpr ⟨h2, hr⟩)

theorem ChainAdj.of_append_left {α : Type*} {R : α → α → Prop} :
    ∀ {l₁ l₂ : List α}, ChainAdj R (l₁ ++ l₂) → ChainAdj R l₁ := by
  intro l₁
  induction l₁ with
  | nil => intro l₂ h; exact ChainAdj.nil
  | cons x t ih =>
    intro l₂ h
    cases t with
    | nil => exact ChainAdj.singleton _
    | cons y t' =>
      have e : (x :: y :: t') ++ l₂ = x :: y :: (t' ++ l₂) := rfl
      rw [e] at h
      cases h with
      | cons h1 h2 => exact ChainAdj.cons h1 (ih h2)

theorem ChainAdj.of_append_right {α : Type*} {R : α → α → Prop} :
    ∀ {l₁ l₂ : List α}, ChainAdj R (l₁ ++ l₂) → ChainAdj R l₂ := by
  intro l₁
  induction l₁ with
  | nil => intro l₂ h; exact h
  | cons x t ih => intro l₂ h; exact ih (ChainAdj.tail h)

theorem ChainAdj.concat_arc {α : Type*} {R : α → α → Prop} :
    ∀ {l : List α} {a b : α}, ChainAdj R (l ++ [a, b]) → R a b := by
  intro l
  induction l with
  | nil =>
    intro a b h
    cases h with
    | cons h1 _ => exact h1
  | cons x t ih =>
    intro a b h
    cases t with
    | nil =>
      cases h with
      | cons _ h2 => cases h2 with | cons h3 _ => exact h3
    | cons y t' =>
      have e : (x :: y :: t') ++ [a, b] = x :: y :: (t' ++ [a, b]) := rfl
      rw [e] at h
      cases h with
      | cons _ h2 => exact ih h2

/-! ## Directed graphs with a source -/

/-- A finite directed graph with a distinguished source vertex `src` such that
every vertex is reachable from `src`. Arcs are a finset of ordered pairs;
there are no self-loops and no multiple arcs. Reachability is packaged as the
existence of a *simple* path. -/
structure Digraph where
  n : ℕ
  arcs : Finset (Fin n × Fin n)
  loopless : ∀ a ∈ arcs, a.1 ≠ a.2
  src : Fin n
  reach : ∀ v : Fin n, ∃ p : List (Fin n),
    p.Nodup ∧ ChainAdj (fun a b => (a, b) ∈ arcs) p ∧ p.head? = some src ∧
      p.getLast? = some v

namespace Digraph

/-- The number of arcs. -/
def m (G : Digraph) : ℕ := G.arcs.card

/-- The arcs of `G` as a subtype. -/
abbrev Arc (G : Digraph) := {a : Fin G.n × Fin G.n // a ∈ G.arcs}

instance (G : Digraph) : Fintype G.Arc := Finset.Subtype.fintype G.arcs

/-- An arc-length assignment: a real value for every ordered pair of
vertices; only the values on arcs matter. -/
abbrev ArcLen (G : Digraph) := Fin G.n → Fin G.n → ℝ

/-- Non-negativity of an arc-length assignment. -/
def ArcLen.Nonneg {G : Digraph} (w : G.ArcLen) : Prop := ∀ u v : Fin G.n, 0 ≤ w u v

/-! ## Walks, simple paths and the true distance -/

/-- A walk from `u` to `v`: a vertex list starting at `u`, ending at `v`, with
consecutive vertices joined by arcs. -/
structure IsWalkFromTo (G : Digraph) (u v : Fin G.n) (p : List (Fin G.n)) : Prop where
  chain : ChainAdj (fun a b => (a, b) ∈ G.arcs) p
  head : p.head? = some u
  last : p.getLast? = some v

/-- A simple path from `u` to `v`: a walk that repeats no vertex. -/
structure IsSPathFromTo (G : Digraph) (u v : Fin G.n) (p : List (Fin G.n)) : Prop
    extends IsWalkFromTo G u v p where
  nodup : p.Nodup

/-- The length of a vertex list under an arc-length assignment: the sum of the
lengths of its consecutive pairs. -/
def pathLen {G : Digraph} (w : G.ArcLen) : List (Fin G.n) → ℝ
  | [] => 0
  | [_] => 0
  | a :: b :: t => w a b + pathLen w (b :: t)

theorem pathLen_nonneg {G : Digraph} (w : G.ArcLen) (hw : w.Nonneg) :
    ∀ p : List (Fin G.n), 0 ≤ pathLen w p := by
  intro p
  induction p with
  | nil => rfl
  | cons x t ih =>
    cases t with
    | nil => rfl
    | cons y t' =>
      show 0 ≤ w x y + pathLen w (y :: t')
      exact add_nonneg (hw x y) ih

theorem pathLen_append {G : Digraph} (w : G.ArcLen) (p q : List (Fin G.n)) (a b : Fin G.n)
    (hp : p.getLast? = some a) (hq : q.head? = some b) :
    pathLen w (p ++ q) = pathLen w p + w a b + pathLen w q := by
  induction p generalizing q with
  | nil => simp at hp
  | cons x t ih =>
    cases t with
    | nil =>
      simp only [List.getLast?_singleton, Option.some.injEq] at hp
      subst hp
      cases q with
      | nil => simp at hq
      | cons y q' =>
        simp only [List.head?_cons, Option.some.injEq] at hq
        subst hq
        show pathLen w ([x] ++ y :: q') = pathLen w [x] + w x y + pathLen w (y :: q')
        rw [List.singleton_append]
        show w x y + pathLen w (y :: q') = 0 + w x y + pathLen w (y :: q')
        ring
    | cons y t' =>
      have hp' : (y :: t').getLast? = some a := by
        rwa [List.getLast?_cons_cons] at hp
      have ihq := ih q hp' hq
      have e1 : (x :: y :: t') ++ q = x :: ((y :: t') ++ q) := rfl
      rw [e1]
      obtain ⟨z, r, hzr⟩ : ∃ z r, (y :: t') ++ q = z :: r := by
        cases h : (y :: t') ++ q with
        | nil => exact absurd h (List.append_ne_nil_of_left_ne_nil (by simp) _)
        | cons z r => exact ⟨z, r, rfl⟩
      have hz : z = y := by
        have h2 := congrArg List.head? hzr
        rw [List.cons_append, List.head?_cons, List.head?_cons] at h2
        exact (Option.some.inj h2).symm
      subst hz
      rw [hzr]
      show w x z + pathLen w (z :: r) = (w x z + pathLen w (z :: t')) + w a b + pathLen w q
      rw [← hzr, ihq]
      ring

/-- Every walk contains a simple path with the same endpoints whose weighted
length is no larger (for non-negative weights): the loop-erasure argument.
The conclusion also records that the vertices of the simple path are vertices
of the walk. -/
theorem exists_spath_of_walk {G : Digraph} :
    ∀ (k : ℕ) (u v : Fin G.n) (p : List (Fin G.n)),
      p.length ≤ k → G.IsWalkFromTo u v p →
      ∃ q : List (Fin G.n), G.IsSPathFromTo u v q ∧ (∀ a : Fin G.n, a ∈ q → a ∈ p) ∧
        ∀ w : G.ArcLen, w.Nonneg → pathLen w q ≤ pathLen w p := by
  intro k
  induction k with
  | zero =>
    intro u v p hlen hw
    have h0 : p = [] := by
      cases p with
      | nil => rfl
      | cons x t => simp at hlen
    subst h0
    have h1 := hw.head
    simp at h1
  | succ k ihk =>
    intro u v p hlen hw
    by_cases hnd : p.Nodup
    · exact ⟨p, ⟨hw, hnd⟩, fun _ h => h, fun _ _ => le_refl _⟩
    · cases p with
      | nil => simp at hnd
      | cons x t =>
        have hxu : x = u := by
          have h0 := hw.head
          simp only [List.head?_cons, Option.some.injEq] at h0
          exact h0
        subst hxu
        by_cases hx : x ∈ t
        · obtain ⟨B, C, ht, hBx⟩ := list_split_first hx
          have hw' : G.IsWalkFromTo x v (x :: C) := by
            refine ⟨?_, rfl, ?_⟩
            · have htmp := hw.chain
              rw [ht] at htmp
              exact ChainAdj.of_append_right (ChainAdj.tail htmp)
            · cases C with
              | nil =>
                have hgl : (x :: (B ++ [x])).getLast? = some x := by
                  rw [show (x :: (B ++ [x])) = (x :: B) ++ [x] from by simp]
                  exact getLast?_append_single _ _
                have h2 := hw.last
                rw [ht, hgl] at h2
                exact h2
              | cons y C' =>
                have h2 := hw.last
                rw [ht, show (x :: (B ++ x :: y :: C')) = (x :: B) ++ (x :: y :: C') from rfl,
                  getLast?_append_cons, List.getLast?_cons_cons] at h2
                rwa [List.getLast?_cons_cons]
          obtain ⟨q, hqwalk, hqsub, hqle⟩ :=
            ihk x v (x :: C) (by
              have hlt : C.length < t.length := by
                rw [ht]
                simp only [List.length_append, List.length_cons]
                omega
              have hlen' : t.length ≤ k := by
                simp only [List.length_cons] at hlen
                omega
              simp only [List.length_cons]
              omega) hw'
          refine ⟨q, hqwalk, fun a ha => ?_, fun w hw'' =>
            le_trans (hqle w hw'') ?_⟩
          · have ha' : a ∈ x :: C := hqsub a ha
            rw [ht]
            rcases List.mem_cons.mp ha' with rfl | ha'
            · exact List.mem_cons_self
            · exact List.mem_cons_of_mem _ (List.mem_append_right _ (List.mem_cons_of_mem _ ha'))
          · have hsplit : (x :: t) = (x :: B) ++ (x :: C) := by rw [ht]; simp
            rw [hsplit]
            rw [pathLen_append w (x :: B) (x :: C) ((x :: B).getLast (List.cons_ne_nil x B)) x
              (List.getLast?_eq_getLast (List.cons_ne_nil x B)) rfl]
            have h1 : 0 ≤ pathLen w (x :: B) := pathLen_nonneg w hw'' _
            have h2 : 0 ≤ w ((x :: B).getLast (List.cons_ne_nil x B)) x := hw'' _ _
            linarith
        · have htnd : ¬t.Nodup := fun h => hnd ((List.nodup_cons).mpr ⟨hx, h⟩)
          cases t with
          | nil => exact absurd List.nodup_nil htnd
          | cons y t' =>
            have hwt : G.IsWalkFromTo y v (y :: t') := by
              refine ⟨ChainAdj.tail hw.chain, rfl, ?_⟩
              have h2 := hw.last
              rwa [List.getLast?_cons_cons] at h2
            obtain ⟨q, hqwalk, hqsub, hqle⟩ :=
              ihk y v (y :: t') (by
                simp only [List.length_cons] at hlen ⊢
                omega) hwt
            have hxq : x ∉ q := fun hmem => hx (hqsub x hmem)
            have hxy : (x, y) ∈ G.arcs := ChainAdj.head_arc hw.chain
            have hqchain : ChainAdj (fun a b => (a, b) ∈ G.arcs) (x :: q) := by
              cases q with
              | nil =>
                have h1 := hqwalk.head
                simp at h1
              | cons z q' =>
                have hhead : (z :: q').head? = some y := hqwalk.head
                simp only [List.head?_cons, Option.some.injEq] at hhead
                subst hhead
                exact ChainAdj.cons hxy hqwalk.chain
            have hqgl : (x :: q).getLast? = some v := by
              cases q with
              | nil =>
                have h1 := hqwalk.head
                simp at h1
              | cons z q' =>
                rw [List.getLast?_cons_cons]
                exact hqwalk.last
            refine ⟨x :: q, ⟨⟨hqchain, rfl, hqgl⟩, List.nodup_cons.mpr ⟨hxq, hqwalk.nodup⟩⟩,
              fun a ha => ?_, fun w hw'' => ?_⟩
            · rcases List.mem_cons.mp ha with rfl | ha
              · exact List.mem_cons_self
              · exact List.mem_cons_of_mem _ (hqsub a ha)
            · cases q with
              | nil =>
                have h1 := hqwalk.head
                simp at h1
              | cons z q' =>
                have hhead : (z :: q').head? = some y := hqwalk.head
                simp only [List.head?_cons, Option.some.injEq] at hhead
                subst hhead
                show w x z + pathLen w (z :: q') ≤ w x z + pathLen w (z :: t')
                exact add_le_add_right (hqle w hw'') _

/-- The finite type of duplicate-free vertex lists (inject into bounded
index functions). -/
noncomputable instance nodupListFintype (n : ℕ) : Fintype {p : List (Fin n) // p.Nodup} := by
  classical
  have hinj : Function.Injective
      (fun p : {p : List (Fin n) // p.Nodup} =>
        (⟨⟨p.1.length, Nat.lt_succ_of_le (by simpa using p.2.length_le_card)⟩,
          fun i => p.1.get i⟩ : Σ k : Fin (n + 1), (Fin k → Fin n))) := by
    intro ⟨p, hp⟩ ⟨q, hq⟩ h
    have hpq : p = q := by
      have h1 := congrArg (fun s : (Σ k : Fin (n + 1), Fin k → Fin n) => List.ofFn s.2) h
      simpa [List.ofFn_get] using h1
    exact Subtype.ext hpq
  haveI : Finite {p : List (Fin n) // p.Nodup} := Finite.of_injective _ hinj
  exact Fintype.ofFinite _

/-- The finite type of simple paths from the source to `v`. -/
noncomputable instance spathFintype (G : Digraph) (v : Fin G.n) :
    Fintype {p : List (Fin G.n) // G.IsSPathFromTo G.src v p} := by
  classical
  have hinj : Function.Injective
      (fun p : {p : List (Fin G.n) // G.IsSPathFromTo G.src v p} =>
        (⟨p.1, p.2.nodup⟩ : {p : List (Fin G.n) // p.Nodup})) := by
    intro ⟨p, hp⟩ ⟨q, hq⟩ h
    rw [Subtype.mk.injEq] at h
    exact Subtype.ext h
  haveI : Finite {p : List (Fin G.n) // G.IsSPathFromTo G.src v p} :=
    Finite.of_injective _ hinj
  exact Fintype.ofFinite _

/-- The nonempty type witness of simple paths, from the reachability field. -/
theorem nonempty_spath (G : Digraph) (v : Fin G.n) :
    Nonempty {p : List (Fin G.n) // G.IsSPathFromTo G.src v p} := by
  obtain ⟨p, hnd, hch, hh, hl⟩ := G.reach v
  exact ⟨⟨p, ⟨⟨hch, hh, hl⟩, hnd⟩⟩⟩

/-- The true distance `d*(v)`: the minimum length of a simple path from the
source. The minimum is attained because the set of simple
paths is finite and nonempty (reachability is a `Digraph` field). -/
noncomputable def trueDist (G : Digraph) (w : G.ArcLen) (v : Fin G.n) : ℝ :=
  ((Finset.univ (α := {p : List (Fin G.n) // G.IsSPathFromTo G.src v p})).image
    (fun p => pathLen w p.1)).min' (by
      obtain ⟨p, hnd, hch, hh, hl⟩ := G.reach v
      refine ⟨pathLen w p, ?_⟩
      exact Finset.mem_image.mpr ⟨⟨p, ⟨⟨hch, hh, hl⟩, hnd⟩⟩, Finset.mem_univ _, rfl⟩)

theorem trueDist_le_pathLen {G : Digraph} (w : G.ArcLen) {v : Fin G.n}
    {p : List (Fin G.n)} (hp : G.IsSPathFromTo G.src v p) :
    G.trueDist w v ≤ pathLen w p := by
  apply Finset.min'_le
  apply Finset.mem_image.mpr
  exact ⟨⟨p, hp⟩, Finset.mem_univ _, rfl⟩

theorem exists_path_trueDist {G : Digraph} (w : G.ArcLen) (v : Fin G.n) :
    ∃ p : List (Fin G.n), G.IsSPathFromTo G.src v p ∧ pathLen w p = G.trueDist w v := by
  have hmem : G.trueDist w v ∈ ((Finset.univ (α := {p : List (Fin G.n) //
      G.IsSPathFromTo G.src v p})).image (fun p => pathLen w p.1)) :=
    Finset.min'_mem _ _
  obtain ⟨⟨p, hp⟩, -, hpeq⟩ := Finset.mem_image.mp hmem
  exact ⟨p, hp, hpeq⟩

theorem trueDist_le_concat {G : Digraph} (w : G.ArcLen) (hw : w.Nonneg)
    {u v : Fin G.n} (huv : (u, v) ∈ G.arcs) :
    G.trueDist w v ≤ G.trueDist w u + w u v := by
  obtain ⟨p, hp, hpeq⟩ := exists_path_trueDist w (G := G) u
  have hwalk : G.IsWalkFromTo G.src v (p ++ [v]) := by
    refine ⟨?_, ?_, ?_⟩
    · rw [ChainAdj.append_iff p [v] u v hp.last rfl]
      exact ⟨hp.chain, huv, ChainAdj.singleton _⟩
    · cases p with
      | nil =>
        have h1 := hp.head
        simp at h1
      | cons x t =>
        have e : (x :: t) ++ [v] = x :: (t ++ [v]) := rfl
        rw [e]
        simp only [List.head?_cons]
        exact hp.head
    · exact getLast?_append_single _ _
  obtain ⟨q, hq, -, hqle⟩ := exists_spath_of_walk (p ++ [v]).length G.src v (p ++ [v])
    (le_refl _) hwalk
  calc G.trueDist w v ≤ pathLen w q := trueDist_le_pathLen w hq
    _ ≤ pathLen w (p ++ [v]) := hqle w hw
    _ = pathLen w p + w u v := by
        rw [pathLen_append w p [v] u v hp.last rfl]
        have h0 : pathLen w [v] = 0 := rfl
        rw [h0]
        ring
    _ = G.trueDist w u + w u v := by rw [← hpeq]

/-- The last-arc decomposition of the true distance. -/
theorem exists_last_arc {G : Digraph} (w : G.ArcLen) (hw : w.Nonneg)
    {v : Fin G.n} (hv : v ≠ G.src) :
    ∃ u : Fin G.n, (u, v) ∈ G.arcs ∧ G.trueDist w v = G.trueDist w u + w u v := by
  obtain ⟨p, hp, hpeq⟩ := exists_path_trueDist w (G := G) v
  have hlen : 2 ≤ p.length := by
    cases p with
    | nil =>
      have h1 := hp.head
      simp at h1
    | cons x t =>
      cases t with
      | nil =>
        have h1 := hp.head
        have h2 := hp.last
        simp only [List.head?_singleton, Option.some.injEq] at h1
        simp only [List.getLast?_singleton, Option.some.injEq] at h2
        rw [h1] at h2
        exact absurd h2.symm hv
      | cons y t' => simp
  obtain ⟨l, a, b, hab⟩ := list_split_last_two hlen
  have hbv : v = b := by
    have h2 := hp.last
    rw [hab, getLast?_append_pair] at h2
    exact (Option.some.inj h2).symm
  subst hbv
  have huv : (a, v) ∈ G.arcs := by
    have hch := hp.chain
    rw [hab] at hch
    exact ChainAdj.concat_arc hch
  refine ⟨a, huv, ?_⟩
  have hspa : G.IsSPathFromTo G.src a (l ++ [a]) := by
    have hp' := hp
    rw [hab] at hp'
    have e2 : l ++ [a, v] = (l ++ [a]) ++ [v] := (List.append_assoc l [a] [v]).symm
    refine ⟨⟨?_, ?_, getLast?_append_single _ _⟩, ?_⟩
    · have hch := hp'.chain
      rw [e2] at hch
      exact (ChainAdj.append_iff (l ++ [a]) [v] a v (getLast?_append_single l a) rfl).mp hch |>.1
    · cases l with
      | nil => exact hp'.head
      | cons x l' =>
        rw [List.cons_append] at hp' ⊢
        exact hp'.head
    · have hnd := hp'.nodup
      rw [e2] at hnd
      exact (List.nodup_append.mp hnd).1
  have hle : G.trueDist w a ≤ pathLen w (l ++ [a]) := trueDist_le_pathLen w hspa
  have hconcat : G.trueDist w v ≤ G.trueDist w a + w a v := trueDist_le_concat w hw huv
  have hlen' : pathLen w p = pathLen w (l ++ [a]) + w a v := by
    rw [hab]
    have e : l ++ [a, v] = (l ++ [a]) ++ [v] := (List.append_assoc l [a] [v]).symm
    rw [e, pathLen_append w (l ++ [a]) [v] a v (getLast?_append_single l a) rfl]
    have h0 : pathLen w [v] = 0 := rfl
    rw [h0]
    ring
  rw [hpeq] at hlen'
  linarith

end Digraph

namespace Digraph

/-! ## Vertex orders, distance orders, D and F -/

/-- The number of vertices on a shortest simple path: the level of a vertex,
used to construct a distance order. -/
noncomputable def level (G : Digraph) (v : Fin G.n) : ℕ :=
  ((Finset.univ (α := {p : List (Fin G.n) // G.IsSPathFromTo G.src v p})).image
    (fun p => p.1.length)).min' (by
      obtain ⟨p, hnd, hch, hh, hl⟩ := G.reach v
      refine ⟨p.length, ?_⟩
      exact Finset.mem_image.mpr ⟨⟨p, ⟨⟨hch, hh, hl⟩, hnd⟩⟩, Finset.mem_univ _, rfl⟩)

theorem level_le (G : Digraph) {v : Fin G.n} {p : List (Fin G.n)}
    (hp : G.IsSPathFromTo G.src v p) : G.level v ≤ p.length := by
  apply Finset.min'_le
  apply Finset.mem_image.mpr
  exact ⟨⟨p, hp⟩, Finset.mem_univ _, rfl⟩

theorem exists_spath_level (G : Digraph) (v : Fin G.n) :
    ∃ p : List (Fin G.n), G.IsSPathFromTo G.src v p ∧ p.length = G.level v := by
  have hmem : G.level v ∈ ((Finset.univ (α := {p : List (Fin G.n) //
      G.IsSPathFromTo G.src v p})).image (fun p => p.1.length)) :=
    Finset.min'_mem _ _
  obtain ⟨⟨p, hp⟩, -, hpeq⟩ := Finset.mem_image.mp hmem
  exact ⟨p, hp, hpeq⟩

theorem exists_incoming_arc_level (G : Digraph) {v : Fin G.n} (hv : v ≠ G.src) :
    ∃ u : Fin G.n, (u, v) ∈ G.arcs ∧ G.level u < G.level v := by
  obtain ⟨p, hp, hlen⟩ := G.exists_spath_level v
  have hlen2 : 2 ≤ p.length := by
    cases p with
    | nil =>
      have h1 := hp.head
      simp at h1
    | cons x t =>
      cases t with
      | nil =>
        have h1 := hp.head
        have h2 := hp.last
        simp only [List.head?_singleton, Option.some.injEq] at h1
        simp only [List.getLast?_singleton, Option.some.injEq] at h2
        rw [h1] at h2
        exact absurd h2.symm hv
      | cons y t' => simp
  obtain ⟨l, a, b, hab⟩ := list_split_last_two hlen2
  have hbv : v = b := by
    have h2 := hp.last
    rw [hab, getLast?_append_pair] at h2
    exact (Option.some.inj h2).symm
  subst hbv
  refine ⟨a, ?_, ?_⟩
  · have hch := hp.chain
    rw [hab] at hch
    exact ChainAdj.concat_arc hch
  · have hspa : G.IsSPathFromTo G.src a (l ++ [a]) := by
      have hp' := hp
      rw [hab] at hp'
      have e2 : l ++ [a, v] = (l ++ [a]) ++ [v] := (List.append_assoc l [a] [v]).symm
      refine ⟨⟨?_, ?_, getLast?_append_single _ _⟩, ?_⟩
      · have hch := hp'.chain
        rw [e2] at hch
        exact (ChainAdj.append_iff (l ++ [a]) [v] a v (getLast?_append_single l a) rfl).mp hch |>.1
      · cases l with
        | nil => exact hp'.head
        | cons x l' =>
          rw [List.cons_append] at hp' ⊢
          exact hp'.head
      · have hnd := hp'.nodup
        rw [e2] at hnd
        exact (List.nodup_append.mp hnd).1
    have hle : G.level a ≤ (l ++ [a]).length := G.level_le hspa
    have hlen' : (l ++ [a]).length = p.length - 1 := by rw [hab]; simp
    omega

/-- A full vertex list (no duplicates, length `n`) induces a vertex order as a
permutation: `permOfList l` maps each vertex to its position in `l`. -/
def permOfList {n : ℕ} (l : List (Fin n)) (hn : l.Nodup) (hl : l.length = n) :
    Equiv.Perm (Fin n) where
  toFun v := ⟨l.idxOf v, by
    have hcard : l.toFinset = Finset.univ := by
      apply Finset.eq_univ_of_card
      rw [List.toFinset_card_of_nodup hn, hl, Fintype.card_fin]
    have hmem : v ∈ l := by
      have h1 : v ∈ l.toFinset := by rw [hcard]; exact Finset.mem_univ _
      rwa [List.mem_toFinset] at h1
    have hlt := List.idxOf_lt_length_iff.mpr hmem
    omega⟩
  invFun i := l.get ⟨i.1, by rw [hl]; exact i.2⟩
  left_inv v := by
    show l.get ⟨l.idxOf v, _⟩ = v
    exact List.idxOf_get _
  right_inv i := by
    ext
    show l.idxOf (l.get ⟨i.1, _⟩) = i.1
    exact List.get_idxOf hn _

/-! ## Insertion sort by level (self-contained; used to build a distance
order) -/

/-- Insertion by non-decreasing level. -/
noncomputable def insertByLevel (G : Digraph) (v : Fin G.n) : List (Fin G.n) → List (Fin G.n)
  | [] => [v]
  | x :: t => if G.level v ≤ G.level x then v :: x :: t else x :: insertByLevel G v t

/-- Insertion sort by level. -/
noncomputable def sortByLevel (G : Digraph) : List (Fin G.n) → List (Fin G.n)
  | [] => []
  | x :: t => insertByLevel G x (sortByLevel G t)

theorem mem_insertByLevel (G : Digraph) (v u : Fin G.n) :
    ∀ l : List (Fin G.n), u ∈ insertByLevel G v l ↔ u = v ∨ u ∈ l := by
  intro l
  induction l with
  | nil => simp [insertByLevel]
  | cons x t ih =>
    by_cases h : G.level v ≤ G.level x
    · simp only [insertByLevel]
      rw [if_pos h, List.mem_cons]
    · simp only [insertByLevel]
      rw [if_neg h, List.mem_cons, ih, List.mem_cons]
      tauto

theorem pairwise_insertByLevel (G : Digraph) (v : Fin G.n) :
    ∀ l : List (Fin G.n), l.Pairwise (fun a b => G.level a ≤ G.level b) →
      (insertByLevel G v l).Pairwise (fun a b => G.level a ≤ G.level b) := by
  intro l
  induction l with
  | nil => intro _; simp [insertByLevel]
  | cons x t ih =>
    intro h
    rw [List.pairwise_cons] at h
    by_cases hvx : G.level v ≤ G.level x
    · simp only [insertByLevel]
      rw [if_pos hvx, List.pairwise_cons]
      refine ⟨?_, List.pairwise_cons.mpr h⟩
      intro y hy
      rcases List.mem_cons.mp hy with rfl | hy
      · exact hvx
      · exact le_trans hvx (h.1 y hy)
    · simp only [insertByLevel]
      rw [if_neg hvx, List.pairwise_cons]
      refine ⟨?_, ih h.2⟩
      intro y hy
      rw [mem_insertByLevel] at hy
      rcases hy with rfl | hyt
      · exact le_of_lt (Nat.lt_of_not_ge hvx)
      · exact h.1 y hyt

theorem pairwise_sortByLevel (G : Digraph) :
    ∀ l : List (Fin G.n), (sortByLevel G l).Pairwise (fun a b => G.level a ≤ G.level b) := by
  intro l
  induction l with
  | nil => simp [sortByLevel]
  | cons x t ih =>
    show (insertByLevel G x (sortByLevel G t)).Pairwise _
    exact pairwise_insertByLevel G x _ ih

theorem perm_insertByLevel (G : Digraph) (v : Fin G.n) :
    ∀ l : List (Fin G.n), List.Perm (insertByLevel G v l) (v :: l) := by
  intro l
  induction l with
  | nil => simp [insertByLevel]
  | cons x t ih =>
    by_cases h : G.level v ≤ G.level x
    · simp only [insertByLevel]; rw [if_pos h]
    · simp only [insertByLevel]; rw [if_neg h]
      exact (List.Perm.cons x ih).trans (List.Perm.swap v x t)

theorem perm_sortByLevel (G : Digraph) :
    ∀ l : List (Fin G.n), List.Perm (sortByLevel G l) l := by
  intro l
  induction l with
  | nil => simp [sortByLevel]
  | cons x t ih =>
    show List.Perm (insertByLevel G x (sortByLevel G t)) (x :: t)
    exact (perm_insertByLevel G x _).trans (List.Perm.cons x ih)

/-- Positions in a `Pairwise`-sorted list respect the relation. -/
theorem Pairwise.get_le {α : Type*} {R : α → α → Prop} {l : List α} (h : l.Pairwise R) :
    ∀ (i j : Fin l.length), i.1 < j.1 → R (l.get i) (l.get j) := by
  induction l with
  | nil => intro i; exact absurd i.2 (by simp)
  | cons x t ih =>
    intro i j hij
    rw [List.pairwise_cons] at h
    cases i with
    | mk in' hilen =>
      cases j with
      | mk jn hjlen =>
        cases in' with
        | zero =>
          cases jn with
          | zero => exact absurd hij (by simp)
          | succ jn' =>
            have hmem : t.get ⟨jn', by simp at hjlen; omega⟩ ∈ t :=
              List.get_mem _ _
            exact h.1 _ hmem
        | succ in' =>
          cases jn with
          | zero => exact absurd hij (by simp)
          | succ jn' =>
            have hij' : in' < jn' := by
              simp only [Fin.mk_lt_mk] at hij
              omega
            exact ih h.2 ⟨in', by simp at hilen; omega⟩ ⟨jn', by simp at hjlen; omega⟩ hij'

/-- A total order of the vertices: a permutation of `Fin G.n`;
`L v` is the position of `v` in the order. -/
abbrev VertexOrder (G : Digraph) := Equiv.Perm (Fin G.n)

/-- The combinatorial characterization of distance orders, taken here as
the definition: every vertex other than the source has an
incoming forward arc (an arc from a vertex that precedes it in the order). -/
def IsDistOrder (G : Digraph) (L : VertexOrder G) : Prop :=
  ∀ v : Fin G.n, v ≠ G.src → ∃ u : Fin G.n, (u, v) ∈ G.arcs ∧ L u < L v

instance (G : Digraph) (L : VertexOrder G) : Decidable (G.IsDistOrder L) :=
  inferInstanceAs (Decidable (∀ v : Fin G.n, v ≠ G.src →
    ∃ u : Fin G.n, (u, v) ∈ G.arcs ∧ L u < L v))

/-- The set of distance orders of `G`. -/
def distOrders (G : Digraph) : Finset (VertexOrder G) := Finset.univ.filter G.IsDistOrder

/-- The number of distance orders. -/
def numDistOrders (G : Digraph) : ℕ := G.distOrders.card

/-- The forward arcs of a vertex order: arcs whose tail precedes their head
in the order. -/
def forwardArcs (G : Digraph) (L : VertexOrder G) : Finset (Fin G.n × Fin G.n) :=
  G.arcs.filter (fun a => L a.1 < L a.2)

/-- The maximum number of forward arcs of any distance order. (`Finset.sup`
returns `0` on the empty set; the distance orders are in fact always nonempty,
see `exists_distOrder`.) -/
def maxForwardArcs (G : Digraph) : ℕ :=
  G.distOrders.sup (fun L => (G.forwardArcs L).card)

/-- Every graph (with all vertices reachable from the source) has at least one
distance order: sort the vertices by their level; every non-source vertex has
an incoming arc from a vertex of strictly smaller level, hence a forward
arc. -/
theorem exists_distOrder (G : Digraph) :
    ∃ L : VertexOrder G, G.IsDistOrder L := by
  classical
  let l := sortByLevel G (List.finRange G.n)
  have hperm : List.Perm l (List.finRange G.n) := perm_sortByLevel G _
  have hnodup : l.Nodup := hperm.nodup_iff.mpr (List.nodup_finRange _)
  have hlen : l.length = G.n := by rw [hperm.length_eq, List.length_finRange]
  refine ⟨permOfList l hnodup hlen, ?_⟩
  intro v hv
  obtain ⟨u, huv, hul⟩ := G.exists_incoming_arc_level hv
  refine ⟨u, huv, ?_⟩
  have hsort := pairwise_sortByLevel G (List.finRange G.n)
  have hmem_u : u ∈ l := by
    rw [hperm.mem_iff]
    exact List.mem_finRange _
  have hmem_v : v ∈ l := by
    rw [hperm.mem_iff]
    exact List.mem_finRange _
  show (⟨l.idxOf u, _⟩ : Fin G.n) < ⟨l.idxOf v, _⟩
  by_contra h
  push_neg at h
  have hle : G.level v ≤ G.level u := by
    rcases eq_or_lt_of_le h with heq | hlt
    · have huv' : u = v := by
        have h2 : (⟨l.idxOf u, List.idxOf_lt_length_iff.mpr hmem_u⟩ : Fin l.length) =
            ⟨l.idxOf v, List.idxOf_lt_length_iff.mpr hmem_v⟩ := by
          apply Fin.ext
          show l.idxOf u = l.idxOf v
          exact (Fin.ext_iff.mp heq).symm
        have h1 : l.get ⟨l.idxOf u, List.idxOf_lt_length_iff.mpr hmem_u⟩ =
            l.get ⟨l.idxOf v, List.idxOf_lt_length_iff.mpr hmem_v⟩ := by rw [h2]
        rwa [List.idxOf_get, List.idxOf_get] at h1
      subst huv'
      exact le_refl _
    · have hs := Pairwise.get_le hsort ⟨l.idxOf v, List.idxOf_lt_length_iff.mpr hmem_v⟩
        ⟨l.idxOf u, List.idxOf_lt_length_iff.mpr hmem_u⟩ hlt
      rwa [List.idxOf_get, List.idxOf_get] at hs
  omega

theorem numDistOrders_pos (G : Digraph) : 0 < G.numDistOrders := by
  obtain ⟨L, hL⟩ := G.exists_distOrder
  apply Finset.card_pos.mpr
  exact ⟨L, Finset.mem_filter.mpr ⟨Finset.mem_univ _, hL⟩⟩

/-- A true distance order for arc lengths `w`: the vertices are in
non-decreasing order by true distance, and every vertex other than the source
has an incoming forward arc. -/
def IsTrueDistOrder (G : Digraph) (w : G.ArcLen) (L : VertexOrder G) : Prop :=
  (∀ u v : Fin G.n, L u < L v → G.trueDist w u ≤ G.trueDist w v) ∧ G.IsDistOrder L

/-! ## The comparison model: linear-function decision trees -/

/-- A comparison-model algorithm for the distance order problem: a decision
tree whose internal nodes compare a linear function of the arc lengths with
zero (three outcomes), and whose leaves output a vertex order. -/
inductive CompTree (G : Digraph) where
  | leaf (out : VertexOrder G) : CompTree G
  | node (a : G.Arc → ℝ) (lt eq gt : CompTree G) : CompTree G

namespace CompTree

/-- The execution of a comparison tree on arc lengths `w`: the output order
together with the number of comparisons performed (the path length). -/
noncomputable def eval {G : Digraph} : CompTree G → G.ArcLen → VertexOrder G × ℕ
  | leaf out, _ => (out, 0)
  | node a l e g, w =>
      if ∑ x : G.Arc, a x * w x.1.1 x.1.2 < 0 then ((eval l w).1, (eval l w).2 + 1)
      else if 0 < ∑ x : G.Arc, a x * w x.1.1 x.1.2 then ((eval g w).1, (eval g w).2 + 1)
      else ((eval e w).1, (eval e w).2 + 1)

/-- Correctness: on every non-negative arc-length assignment the tree outputs
a true distance order. -/
def Correct {G : Digraph} (T : CompTree G) : Prop :=
  ∀ w : G.ArcLen, w.Nonneg → G.IsTrueDistOrder w (T.eval w).1

end CompTree

/-! ## The time model: decision trees over a vertex set with incidence-list
access -/

/-- A graph representation: for each vertex, an incidence list of its
outgoing arcs, given as a list of head vertices. -/
abbrev Rep (G : Digraph) := Fin G.n → List (Fin G.n)

/-- Legality of a representation: each incidence list is a duplicate-free
enumeration of the outgoing arcs. -/
def Rep.Legal {G : Digraph} (rep : G.Rep) : Prop :=
  ∀ v : Fin G.n, (rep v).Nodup ∧ ∀ w : Fin G.n, w ∈ rep v ↔ (v, w) ∈ G.arcs

/-- A time-model algorithm: a decision tree over a bare vertex set `Fin n`,
with two kinds of internal nodes. `cmp a` compares the linear function
`∑ a(p)·w(p)` over ordered pairs of vertices with zero (one time unit);
`access v br` accesses the next arc on the incidence list of `v` and branches
on the answer (`none` for the end of the list, `some w` for the arc `vw`; one
time unit). The tree is indexed by the vertex set only, not by a graph: in
the time model the algorithm is given the vertex set and the source and must
*discover* the arcs by traversing the incidence lists, so the same tree is
run on every graph on that vertex set. -/
inductive TimeTree (n : ℕ) where
  | leaf (out : Equiv.Perm (Fin n)) : TimeTree n
  | cmp (a : Fin n × Fin n → ℝ) (lt eq gt : TimeTree n) : TimeTree n
  | access (v : Fin n) (br : Option (Fin n) → TimeTree n) : TimeTree n

namespace TimeTree

/-- The execution of a time tree on arc lengths `w` and representation `rep`,
starting from the access counter `cnt` (the number of times each incidence
list has already been accessed): the output order and the time spent. -/
noncomputable def exec {n : ℕ} (w : Fin n → Fin n → ℝ) (rep : Fin n → List (Fin n)) :
    TimeTree n → (Fin n → ℕ) → Equiv.Perm (Fin n) × ℕ
  | leaf out, _ => (out, 0)
  | cmp a l e g, cnt =>
      if ∑ x : Fin n × Fin n, a x * w x.1 x.2 < 0 then
        ((exec w rep l cnt).1, (exec w rep l cnt).2 + 1)
      else if 0 < ∑ x : Fin n × Fin n, a x * w x.1 x.2 then
        ((exec w rep g cnt).1, (exec w rep g cnt).2 + 1)
      else ((exec w rep e cnt).1, (exec w rep e cnt).2 + 1)
  | access v br, cnt =>
      ((exec w rep (br (rep v)[cnt v]?) (Function.update cnt v (cnt v + 1))).1,
       (exec w rep (br (rep v)[cnt v]?) (Function.update cnt v (cnt v + 1))).2 + 1)

/-- The full execution from a fresh start. -/
noncomputable def run {n : ℕ} (A : TimeTree n) (w : Fin n → Fin n → ℝ)
    (rep : Fin n → List (Fin n)) : Equiv.Perm (Fin n) × ℕ :=
  A.exec w rep (fun _ => 0)

/-- Well-formedness: on every path, the linear functions compared only involve
pairs of vertices that have previously been accessed (all arc lengths in a
comparison must be of previously accessed arcs). The second argument is the
set of pairs accessed so far. -/
def WF {n : ℕ} : TimeTree n → Finset (Fin n × Fin n) → Prop
  | leaf _, _ => True
  | cmp a l e g, seen =>
      (∀ x : Fin n × Fin n, a x ≠ 0 → x ∈ seen) ∧ WF l seen ∧ WF e seen ∧ WF g seen
  | access v br, seen =>
      WF (br none) seen ∧
      ∀ w : Fin n, WF (br (some w)) (insert (v, w) seen)

/-- Correctness: well-formed, and on *every* digraph on the same
vertex set with the same source — the algorithm is not given the arcs, it
discovers them through the incidence lists — on every non-negative arc-length
assignment and every legal representation the tree outputs a true distance
order. (The graph with arcs `arcs`, source `s` and the packaged reachability
is reassembled as a `Digraph` so that the true-distance-order predicate of
the statement layer applies.) -/
def Correct {n : ℕ} (s : Fin n) (A : TimeTree n) : Prop :=
  A.WF ∅ ∧ ∀ (arcs : Finset (Fin n × Fin n))
    (hloop : ∀ a ∈ arcs, a.1 ≠ a.2)
    (hreach : ∀ v : Fin n, ∃ p : List (Fin n), p.Nodup ∧
      ChainAdj (fun a b => (a, b) ∈ arcs) p ∧ p.head? = some s ∧
        p.getLast? = some v)
    (w : Fin n → Fin n → ℝ), (∀ u v : Fin n, 0 ≤ w u v) →
    ∀ (rep : Fin n → List (Fin n)),
      (∀ v : Fin n, (rep v).Nodup ∧ ∀ u : Fin n, u ∈ rep v ↔ (v, u) ∈ arcs) →
      (Digraph.mk n arcs hloop s hreach).IsTrueDistOrder w (A.run w rep).1

/-- Projecting a time tree to a comparison tree along a fixed representation
of a graph `G`: access nodes are replaced by the branch their answer
dictates, and comparisons over pairs of vertices are restricted to the arcs
of `G`. -/
noncomputable def project {G : Digraph} (rep : G.Rep) :
    TimeTree G.n → (Fin G.n → ℕ) → CompTree G
  | leaf out, _ => .leaf out
  | cmp a l e g, cnt =>
      .node (fun x : G.Arc => a x.1) (project rep l cnt) (project rep e cnt)
        (project rep g cnt)
  | access v br, cnt => project rep (br (rep v)[cnt v]?) (Function.update cnt v (cnt v + 1))

/-- Along the execution on a legal representation of `G`, the projection
outputs the same order and does no more comparisons than the tree spends
time: a well-formed tree compares only previously accessed pairs (the second
argument `seen`, an invariant of the execution), which on a legal
representation are arcs of `G`, so each comparison has the same outcome after
restriction to the arcs. -/
theorem project_eval_fst_le {G : Digraph} (w : G.ArcLen) (rep : G.Rep) (hrep : rep.Legal) :
    ∀ (A : TimeTree G.n) (seen : Finset (Fin G.n × Fin G.n)) (cnt : Fin G.n → ℕ),
      A.WF seen → (∀ x ∈ seen, x ∈ G.arcs) →
      ((A.project rep cnt).eval w).1 = (A.exec w rep cnt).1 ∧
      ((A.project rep cnt).eval w).2 ≤ (A.exec w rep cnt).2 := by
  intro A
  induction A with
  | leaf out =>
    intro seen cnt _ _
    simp only [project, CompTree.eval, exec]
    exact ⟨trivial, le_refl _⟩
  | cmp a l e g ihl ihe ihg =>
    intro seen cnt hwf hseen
    obtain ⟨ha, hwfl, hwfe, hwfg⟩ := hwf
    have hsub : (∑ x ∈ G.arcs, a x * w x.1 x.2) =
        ∑ x : Fin G.n × Fin G.n, a x * w x.1 x.2 := by
      apply Finset.sum_subset (Finset.subset_univ _)
      intro x _ hx
      have ha0 : a x = 0 := by
        by_contra hne
        exact hx (hseen _ (ha _ hne))
      rw [ha0, zero_mul]
    have hatt : (∑ x : G.Arc, a x.1 * w x.1.1 x.1.2) =
        ∑ x ∈ G.arcs, a x * w x.1 x.2 :=
      Finset.sum_coe_sort G.arcs (fun p : Fin G.n × Fin G.n => a p * w p.1 p.2)
    have hsum : (∑ x : Fin G.n × Fin G.n, a x * w x.1 x.2) =
        ∑ x : G.Arc, a x.1 * w x.1.1 x.1.2 := by rw [hatt, hsub]
    simp only [project, CompTree.eval, exec]
    rw [hsum]
    by_cases h1 : (∑ x : G.Arc, a x.1 * w x.1.1 x.1.2) < 0
    · simp only [h1, if_true]
      obtain ⟨h1', h2'⟩ := ihl seen cnt hwfl hseen
      exact ⟨h1', Nat.succ_le_succ h2'⟩
    · by_cases h2 : 0 < (∑ x : G.Arc, a x.1 * w x.1.1 x.1.2)
      · simp only [h1, h2, if_false, if_true]
        obtain ⟨h1', h2'⟩ := ihg seen cnt hwfg hseen
        exact ⟨h1', Nat.succ_le_succ h2'⟩
      · simp only [h1, h2, if_false, if_true]
        obtain ⟨h1', h2'⟩ := ihe seen cnt hwfe hseen
        exact ⟨h1', Nat.succ_le_succ h2'⟩
  | access v br ih =>
    intro seen cnt hwf hseen
    obtain ⟨hwf_none, hwf_some⟩ := hwf
    simp only [project, exec]
    cases h : (rep v)[cnt v]? with
    | none =>
      obtain ⟨h1', h2'⟩ := ih none seen _ hwf_none hseen
      exact ⟨h1', Nat.le_succ_of_le h2'⟩
    | some u =>
      have hmem : u ∈ rep v := List.mem_of_getElem? h
      have harc : (v, u) ∈ G.arcs := ((hrep v).2 u).mp hmem
      obtain ⟨h1', h2'⟩ := ih (some u) (insert (v, u) seen) _ (hwf_some u) (by
        intro x hx
        rcases Finset.mem_insert.mp hx with rfl | hx
        · exact harc
        · exact hseen x hx)
      exact ⟨h1', Nat.le_succ_of_le h2'⟩

theorem project_correct {G : Digraph} (rep : G.Rep) (hrep : rep.Legal) (A : TimeTree G.n)
    (hA : A.Correct G.src) : (A.project rep (fun _ => 0)).Correct := by
  intro w hw
  rw [(project_eval_fst_le w rep hrep A ∅ (fun _ => 0) hA.1 (by simp)).1]
  exact hA.2 G.arcs G.loopless G.reach w hw rep hrep

end TimeTree

end Digraph

/-! ## Dijkstra traces: runs as scan-block event logs -/

/-- One arc-processing event inside a scanning step. Scanning vertex `u`
processes each outgoing arc `uv` exactly once: `ins v` inserts an unlabeled
vertex into the heap; `relax v` records the comparison
`d(u) + c(uv) < d(v)` for a labeled, unscanned vertex, whether or not it
succeeds (possibly followed by a decrease-key); `skip v` records an arc to
an already scanned vertex, with no distance comparison or heap operation.
These are the three vertex states in Section 4 of the source paper. -/
inductive BlockEv (n : ℕ) where
  | ins (v : Fin n) : BlockEv n
  | relax (v : Fin n) : BlockEv n
  | skip (v : Fin n) : BlockEv n
  deriving BEq, DecidableEq

/-- The vertex an event refers to. -/
def BlockEv.v {n : ℕ} : BlockEv n → Fin n
  | .ins v => v
  | .relax v => v
  | .skip v => v

namespace Digraph

/-- A Dijkstra trace: the run is a list of scan blocks
`(u, evs)`, one per vertex, where `u` is the vertex deleted from the heap at
the beginning of the step and `evs` records exactly one arc-processing event
for each outgoing arc of `u`. The source is inserted into the
heap initially (an implicit event, counted in `cumIns`), so the first block
scans the source.

The constraints are the invariants of the high-level algorithm: every
vertex is scanned exactly once, the source first; events of a
block follow outgoing arcs of the scanned vertex and cover every such arc
exactly once; every vertex other than the source is inserted exactly once,
before it is scanned; a relax event refers to a vertex that is labeled but
not yet scanned (inserted in an earlier block, scanned in a later one);
a skip event refers to an already scanned vertex. Thus each forward arc is
an insertion or a comparison, and every backward arc is a skip. The scan
order is a true distance order
(the textbook correctness of Dijkstra's algorithm, kept here as a
trace constraint — see the concept ledger). -/
structure DijkstraTrace (G : Digraph) (w : G.ArcLen) where
  blocks : List (Fin G.n × List (BlockEv G.n))
  scan_nodup : (blocks.map Prod.fst).Nodup
  scan_len : (blocks.map Prod.fst).length = G.n
  src_first : (blocks.map Prod.fst).head? = some G.src
  arc_ok : ∀ u evs, (u, evs) ∈ blocks → ∀ e ∈ evs, (u, e.v) ∈ G.arcs
  block_nodup : ∀ u evs, (u, evs) ∈ blocks → (evs.map BlockEv.v).Nodup
  arc_covered : ∀ u evs, (u, evs) ∈ blocks → ∀ v, (u, v) ∈ G.arcs →
    ∃ e ∈ evs, e.v = v
  ins_count : ∀ v : Fin G.n,
    ((blocks.flatMap Prod.snd).filter (· == BlockEv.ins v)).length =
      if v = G.src then 0 else 1
  ins_block_lt : ∀ v u evs, BlockEv.ins v ∈ evs → (u, evs) ∈ blocks →
    (blocks.map Prod.fst).idxOf u < (blocks.map Prod.fst).idxOf v
  relax_valid : ∀ u evs v, BlockEv.relax v ∈ evs → (u, evs) ∈ blocks →
    (∃ u' evs', BlockEv.ins v ∈ evs' ∧ (u', evs') ∈ blocks ∧
      (blocks.map Prod.fst).idxOf u' < (blocks.map Prod.fst).idxOf u) ∧
    (blocks.map Prod.fst).idxOf u < (blocks.map Prod.fst).idxOf v
  skip_valid : ∀ u evs v, BlockEv.skip v ∈ evs → (u, evs) ∈ blocks →
    (blocks.map Prod.fst).idxOf v < (blocks.map Prod.fst).idxOf u
  scan_dist_order : G.IsTrueDistOrder w (permOfList (blocks.map Prod.fst) scan_nodup scan_len)

namespace DijkstraTrace

variable {G : Digraph} {w : G.ArcLen} (tr : DijkstraTrace G w)

/-- The scan index of a vertex (its position in the scan order). -/
def scanIdx (v : Fin G.n) : ℕ := (tr.blocks.map Prod.fst).idxOf v

/-- The number of insert events in one block. -/
def insCount (evs : List (BlockEv G.n)) : ℕ :=
  evs.countP (fun e => match e with | .ins _ => true | _ => false)

/-- The cumulative number of insertions up to the beginning of block `k`,
counting the initial insertion of the source. -/
def cumIns (k : ℕ) : ℕ := 1 + ((tr.blocks.take k).map (fun b => insCount b.2)).sum

/-- All insert events in order. -/
def insEvents : List (BlockEv G.n) :=
  (tr.blocks.flatMap Prod.snd).filter
    (fun e => match e with | .ins _ => true | _ => false)

/-- The insertion rank of a vertex: the source has rank 0 (the implicit
initial insertion); any other vertex is inserted by one of the events. -/
def insRank (v : Fin G.n) : ℕ :=
  if v = G.src then 0 else 1 + tr.insEvents.idxOf (.ins v)

/-- The working-set size of a vertex: the number of vertices
inserted into the heap from the time `v` is inserted until the time it is
deleted, including `v` itself. -/
def W (v : Fin G.n) : ℕ := tr.cumIns (tr.scanIdx v) - tr.insRank v

/-- The number of relax events: every comparison performed outside the
heap, including unsuccessful relaxations. Exact arc coverage prevents their
omission; skip events require no distance comparison and contribute zero. -/
def relaxCount : ℕ :=
  (tr.blocks.map (fun b => b.2.countP
    (fun e => match e with | .relax _ => true | _ => false))).sum

/-- The total time of the run with a working-set-bound heap: `O(m)` for
the arc processing plus `O(1)` per insertion and
decrease-key and `O(log W(v))` for the delete-min of `v`; the constant
factors are normalized to `1` (they are absorbed by the existential constant
of the main theorem). -/
noncomputable def timeCost : ℝ := G.m + ∑ v : Fin G.n, (1 + Real.logb 2 (tr.W v))

/-- The total number of comparisons of the run with a working-set-bound heap:
the comparisons outside the heap (relax events) plus `O(1)` per heap
operation other than delete-min and `O(log W(v))` per delete-min. -/
noncomputable def compCost : ℝ := tr.relaxCount + ∑ v : Fin G.n, (1 + Real.logb 2 (tr.W v))

end DijkstraTrace

/-! ## An interval-DAG bound, packaged as a hypothesis -/

/-- A family of `k` integer intervals, each a subset of `[1, k]`. -/
structure IntervalFamily (k : ℕ) where
  a : Fin k → ℕ
  b : Fin k → ℕ
  lo : ∀ i, 1 ≤ a i
  le : ∀ i, a i ≤ b i
  hi : ∀ i, b i ≤ k

/-- The number of topological orders of the DAG associated with an interval
family (the vertices are the intervals, with an arc `i → j` iff `bᵢ < aⱼ`). -/
def IntervalFamily.numTopOrders {k : ℕ} (F : IntervalFamily k) : ℕ :=
  (Finset.univ.filter (fun π : Equiv.Perm (Fin k) =>
    ∀ i j : Fin k, F.b i < F.a j → π i < π j)).card

/-- The interval-DAG bound: for the DAG `I` associated with a family of `k`
intervals inside `[1, k]`, `∑ log₂(bᵢ − aᵢ + 1) = O(log D(I))`. Packaged as
a hypothesis (an external fact); the `+ 1` absorbs the degenerate small cases
of the asymptotic notation. -/
def IntervalDAGBound : Prop :=
  ∃ C : ℝ, 0 < C ∧ ∀ (k : ℕ) (F : IntervalFamily k),
    (∑ i : Fin k, Real.logb 2 ((F.b i - F.a i + 1 : ℕ) : ℝ)) ≤
      C * (1 + Real.logb 2 (IntervalFamily.numTopOrders F))

end Digraph

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

namespace Digraph



-- @[checkpoint c8 difficulty=hard]
/-- The main theorem. There is a constant `C > 0` such that on every graph
with `n > 2`: (i) Dijkstra's algorithm is runnable (a trace exists on every
non-negative arc-length assignment); (ii) implemented with a heap having the
working-set bound, it runs in time at most `C·(m + log₂ D)`; (iii) it does
at most `C·(F + log₂ D)` comparisons; (iv) every correct time-model
algorithm takes time at least `(m + log₂ D)/C` on some choice of arc lengths
and representation; and (v) every correct comparison-model algorithm does at
least `(F − n + 1 + log₂ D)/C` comparisons on some choice of arc lengths.
Conjuncts (ii) and (iv) say Dijkstra's algorithm is universally optimal in
time; (iii) and (v) say it is universally optimal in comparisons up to an
additive term in `n`. -/
theorem dijkstra_universally_optimal (hidag : IntervalDAGBound) :
    ∃ C : ℝ, 0 < C ∧ ∀ (G : Digraph) (hG : 2 < G.n),
      (∀ w : G.ArcLen, w.Nonneg → Nonempty (DijkstraTrace G w)) ∧
      (∀ (w : G.ArcLen) (hw : w.Nonneg) (tr : DijkstraTrace G w),
        tr.timeCost ≤ C * (G.m + Real.logb 2 G.numDistOrders)) ∧
      (∀ (w : G.ArcLen) (hw : w.Nonneg) (tr : DijkstraTrace G w),
        tr.compCost ≤ C * (G.maxForwardArcs + Real.logb 2 G.numDistOrders)) ∧
      (∀ A : TimeTree G.n, A.Correct G.src →
        ∃ (w : G.ArcLen) (hw : w.Nonneg) (rep : G.Rep) (hrep : rep.Legal),
          G.m + Real.logb 2 G.numDistOrders ≤ C * (A.run w rep).2) ∧
      (∀ T : CompTree G, T.Correct →
        ∃ (w : G.ArcLen) (hw : w.Nonneg),
          (G.maxForwardArcs : ℝ) - G.n + 1 + Real.logb 2 G.numDistOrders ≤
            C * (T.eval w).2) := by
  -- CHECKPOINT dijkstra_universally_optimal BEGIN
  sorry
  -- CHECKPOINT dijkstra_universally_optimal END

end Digraph

end DijkstraUniversal
