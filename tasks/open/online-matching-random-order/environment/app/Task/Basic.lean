/-
Statement layer for the competitive ratio of online bipartite matching under
random arrival order (online bipartite matching: Karp–Vazirani–Vazirani, STOC
1990; random arrival order model: Goel–Mehta, SODA 2008). One side of a
bipartite graph (the *offline* vertices) is known in advance; the vertices of
the other side (the *online* vertices) arrive one at a time in a uniformly
random permutation, each revealing its incident edges on arrival, and an online
algorithm must match each arriving vertex immediately and irrevocably (or leave
it unmatched). The value of an algorithm on a graph is the expected size of the
matching it produces (the expectation is over the arrival permutation and the
algorithm's own randomness), and its competitive ratio is this expectation
divided by the maximum matching size, minimized over graphs. The best possible
competitive ratio is open: it is at least 0.696 (Mahdian–Yan, STOC 2011,
analysis of the Ranking algorithm) and at most 0.823 (Manshadi–Oveis
Gharan–Saberi, SODA 2011 / Math. Oper. Res. 2012), improved to 1 − e/e^e ≈
0.82062 by Chierichetti, Giacchini, Panconesi and Vattani (ICALP 2025).

This file is the task's definition zone plus slot zone:
- The definition zone defines bipartite graphs on `n + n` vertices (as edge
  finsets), matchings and the maximum matching number, randomized online
  matching algorithms (a deterministic decision rule fed by a random tape of
  `t` uniformly random bits), the execution of an algorithm along an arrival
  permutation and a tape, the expected matching size (a finite double average
  over all `n!` permutations and all `2^t` tapes), and the greedy algorithm.
  API lemmas (the execution always produces a matching of the graph, its size
  is at most the maximum matching size, and so is the expectation) are fully
  proved. All notions are computable, so claims about small concrete instances
  are provable by `decide`.
- The slot zone states the two main theorems (`conj`: from some size `N` on,
  some randomized online algorithm guarantees expected matching size at least
  `3/4` of the maximum matching at every size; `refuted`: its negation). Both
  proof bodies are left blank.

Fidelity notes (see `tests/reference/concept-ledger.md` of the packaged task):
1. The open problem is asymptotic (`n → ∞`), and so are the Lean statements:
   `conj` says that from some size threshold `N` on, at *every* size `n ≥ N`
   some randomized algorithm guarantees ratio `3/4` on all graphs (the shape
   of a lower-bound theorem; proving it improves the literature lower bound
   `0.696` to `0.75`), and `refuted` is its exact negation — for *every*
   threshold `N` there is a size `n ≥ N` at which *no* randomized algorithm
   guarantees ratio `3/4` (the shape of an upper-bound theorem: every
   algorithm is beaten at infinitely many sizes, hence no algorithm has
   asymptotic guarantee `3/4`; proving it improves the literature upper bound
   `0.82062…` to `0.75`). The threshold `3/4` lies strictly inside the
   currently known interval `(0.696, 0.82062…]`, so either proof is a new
   result.
2. Randomized algorithms are modeled as deterministic decision rules with
   access to a *random tape* of `t` uniform bits (`OnlineAlg n t`); the
   expectation averages uniformly over the tape as well as over the arrival
   permutation. This class is equivalent, for the per-size minimax value, to
   the literature's class of arbitrary randomized algorithms: at a fixed size
   `n` every randomized algorithm is a distribution over deterministic ones,
   the set of graphs is finite, and tape algorithms realize exactly the
   distributions whose probabilities are dyadic rationals `k / 2^t` — which
   approximate any distribution simultaneously on all graphs — while every
   tape algorithm is a randomized algorithm, so the suprema coincide. The
   Ranking algorithm (sample a uniform ordering of the ads, then match each
   arrival to its first available neighbor) uses a uniform permutation as its
   random source, which a bit tape cannot sample *exactly* (`n!` need not
   divide `2^t`); but it is approximated to any precision by tape algorithms
   (group the `2^t` tape values as evenly as possible over the `n!`
   orderings), so a lower-bound analysis through Ranking transfers to this
   model with the same asymptotic threshold. Deterministic algorithms are the
   sub-class `t = 0` (see `expectedCard_tape_zero`).
3. The expectation is a finite average over `Equiv.Perm (Fin n)` (the uniform
   distribution on arrival orders) and `Fin t → Bool` (the uniform tape), a
   rational number; no measure theory is involved. Graphs with maximum
   matching number `0` satisfy the guarantee trivially (`0 ≤ 0`), which is
   the standard convention for the degenerate case.
-/

import Mathlib

namespace OnlineMatching

/-! ### Bipartite graphs, matchings, and the maximum matching number -/

/-- A bipartite graph on `n` offline and `n` online vertices, represented as a
finset of edges. Edge `(u, v)` joins offline vertex `u` to online vertex `v`. -/
abbrev BipGraph (n : ℕ) := Finset (Fin n × Fin n)

/-- The offline neighborhood of an online vertex `v`: the offline vertices
joined to `v` by an edge of `G`. -/
def nbrs {n : ℕ} (G : BipGraph n) (v : Fin n) : Finset (Fin n) :=
  (G.filter fun e => e.2 = v).image Prod.fst

theorem mem_nbrs {n : ℕ} {G : BipGraph n} {u v : Fin n} :
    u ∈ nbrs G v ↔ (u, v) ∈ G := by
  rw [nbrs, Finset.mem_image]
  constructor
  · rintro ⟨e, he, hfe⟩
    rw [Finset.mem_filter] at he
    rw [← hfe, ← he.2, Prod.eta]
    exact he.1
  · intro h
    exact ⟨(u, v), by rw [Finset.mem_filter]; exact ⟨h, rfl⟩, rfl⟩

/-- A matching: a set of edges no two of which share an offline or an online
endpoint (each projection is injective on the set, expressed via cardinals). -/
def IsMatching {n : ℕ} (M : Finset (Fin n × Fin n)) : Prop :=
  (M.image Prod.fst).card = M.card ∧ (M.image Prod.snd).card = M.card

instance {n : ℕ} (M : Finset (Fin n × Fin n)) : Decidable (IsMatching M) := by
  unfold IsMatching
  infer_instance

/-- The empty edge set is a matching. -/
theorem isMatching_empty {n : ℕ} : IsMatching (∅ : Finset (Fin n × Fin n)) := by
  constructor <;> simp

/-- All matchings of `G`. -/
def matchings {n : ℕ} (G : BipGraph n) : Finset (Finset (Fin n × Fin n)) :=
  G.powerset.filter IsMatching

theorem empty_mem_matchings {n : ℕ} (G : BipGraph n) : ∅ ∈ matchings G := by
  rw [matchings, Finset.mem_filter, Finset.mem_powerset]
  exact ⟨Finset.empty_subset _, isMatching_empty⟩

/-- ν(G): the maximum matching number — the largest size of a matching of
`G`. -/
def matchingNumber {n : ℕ} (G : BipGraph n) : ℕ :=
  ((matchings G).image Finset.card).max'
    ⟨0, Finset.mem_image.mpr ⟨∅, empty_mem_matchings G, Finset.card_empty⟩⟩

/-- Any matching of `G` gives a lower bound on ν(G). -/
theorem le_matchingNumber {n : ℕ} {G : BipGraph n} {M : Finset (Fin n × Fin n)}
    (hsub : M ⊆ G) (hM : IsMatching M) : M.card ≤ matchingNumber G := by
  show M.card ≤ ((matchings G).image Finset.card).max' _
  apply Finset.le_max'
  rw [Finset.mem_image]
  exact ⟨M, by rw [matchings, Finset.mem_filter, Finset.mem_powerset]; exact ⟨hsub, hM⟩, rfl⟩

/-- ν(G) is attained: some matching of `G` has exactly ν(G) edges. -/
theorem exists_isMatching_card_eq {n : ℕ} (G : BipGraph n) :
    ∃ M : Finset (Fin n × Fin n), M ⊆ G ∧ IsMatching M ∧ M.card = matchingNumber G := by
  have h := Finset.max'_mem _
    ⟨0, Finset.mem_image.mpr ⟨∅, empty_mem_matchings G, Finset.card_empty⟩⟩
  rw [Finset.mem_image] at h
  obtain ⟨M, hM, hcard⟩ := h
  rw [matchings, Finset.mem_filter, Finset.mem_powerset] at hM
  exact ⟨M, hM.1, hM.2, hcard⟩

/-! ### Online matching algorithms and their execution -/

/-- A randomized online matching algorithm for graphs on `n + n` vertices,
equipped with a random tape of `t` uniformly random bits. At step `k` the
algorithm is shown its tape, the history (each of the `k` earlier arrivals
together with its offline neighborhood), the set of offline vertices it has
already matched, the arriving online vertex, and that vertex's offline
neighborhood; it answers `some u` to match the arrival to offline vertex `u`,
or `none` to leave it unmatched. The tape is the algorithm's only randomness:
conditioned on a tape value, the behavior is deterministic. Deterministic
algorithms are the case `t = 0` (the tape type `Fin 0 → Bool` has a single
element). -/
def OnlineAlg (n t : ℕ) : Type :=
  (Fin t → Bool) → (k : Fin n) → (Fin k → Fin n × Finset (Fin n)) → Finset (Fin n) →
    Fin n → Finset (Fin n) → Option (Fin n)

/- The randomized algorithms with a fixed tape length form a finite type
(the function space is over finite types throughout). The tape layer makes
the type one arrow deeper than the deterministic version, which exceeds the
default typeclass-synthesis size budget, so the budget is raised locally
here (fixed-zone line). -/
set_option synthInstance.maxSize 512 in
instance {n t : ℕ} : Fintype (OnlineAlg n t) := by
  unfold OnlineAlg
  infer_instance

/-- The history available to the algorithm at step `k`: the `k` earlier
arrivals, each paired with its offline neighborhood. -/
def hist {n : ℕ} (G : BipGraph n) (π : Equiv.Perm (Fin n)) (k : Fin n) :
    Fin k → Fin n × Finset (Fin n) :=
  fun i => (π ⟨i.1, Nat.lt_trans i.2 k.2⟩, nbrs G (π ⟨i.1, Nat.lt_trans i.2 k.2⟩))

/-- One step of the execution along tape `τ`: the `k`-th arrival `π k` is
presented; the algorithm's answer is accepted only if it names a neighbor of
`π k` that is still unmatched (otherwise the arrival is left unmatched). -/
def step {n t : ℕ} (A : OnlineAlg n t) (G : BipGraph n) (π : Equiv.Perm (Fin n))
    (τ : Fin t → Bool) (M : Finset (Fin n × Fin n)) (k : Fin n) : Finset (Fin n × Fin n) :=
  match A τ k (hist G π k) (M.image Prod.fst) (π k) (nbrs G (π k)) with
  | some u => if u ∈ nbrs G (π k) ∧ u ∉ M.image Prod.fst then insert (u, π k) M else M
  | none => M

/-- The matching produced after the first `k` arrivals along tape `τ` (steps
beyond `n` are impossible and leave the matching unchanged). -/
def execUpTo {n t : ℕ} (A : OnlineAlg n t) (G : BipGraph n) (π : Equiv.Perm (Fin n))
    (τ : Fin t → Bool) : ℕ → Finset (Fin n × Fin n)
  | 0 => ∅
  | k + 1 => if h : k < n then step A G π τ (execUpTo A G π τ k) ⟨k, h⟩ else execUpTo A G π τ k

/-- Unfolding one execution step. -/
theorem execUpTo_succ {n t : ℕ} (A : OnlineAlg n t) (G : BipGraph n) (π : Equiv.Perm (Fin n))
    (τ : Fin t → Bool) {k : ℕ} (h : k < n) :
    execUpTo A G π τ (k + 1) = step A G π τ (execUpTo A G π τ k) ⟨k, h⟩ := by
  simp only [execUpTo]
  rw [dif_pos h]

/-- The full execution along tape `τ`: the matching produced after all `n`
arrivals. -/
def exec {n t : ℕ} (A : OnlineAlg n t) (G : BipGraph n) (π : Equiv.Perm (Fin n))
    (τ : Fin t → Bool) : Finset (Fin n × Fin n) :=
  execUpTo A G π τ n

/-- The number of matched edges after the full execution along tape `τ`. -/
def execCard {n t : ℕ} (A : OnlineAlg n t) (G : BipGraph n) (π : Equiv.Perm (Fin n))
    (τ : Fin t → Bool) : ℕ :=
  (exec A G π τ).card

/-- The expected matching size of `A` on `G`: the average of `execCard` over
all `n!` uniformly random arrival permutations and all `2^t` uniformly random
tapes. This is the literature's expectation (arrival order and the algorithm's
own randomness) as a finite double average; the denominator is `n! * 2^t`. -/
def expectedCard {n t : ℕ} (A : OnlineAlg n t) (G : BipGraph n) : ℚ :=
  (∑ π : Equiv.Perm (Fin n), ∑ τ : Fin t → Bool, (execCard A G π τ : ℚ)) /
    (Nat.factorial n * 2 ^ t)

/-! ### The execution always produces a matching of the graph -/

/-- A step never removes edges. -/
theorem step_self_subset {n t : ℕ} (A : OnlineAlg n t) (G : BipGraph n)
    (π : Equiv.Perm (Fin n)) (τ : Fin t → Bool)
    (M : Finset (Fin n × Fin n)) (k : Fin n) : M ⊆ step A G π τ M k := by
  unfold step
  split
  · rename_i u _
    split
    · exact Finset.subset_insert _ _
    · exact Finset.Subset.refl _
  · exact Finset.Subset.refl _

/-- Single-step invariant: if `M` is a matching of `G` whose online endpoints
do not include the fresh arrival `π k`, then the next state is still a
matching of `G`, with online endpoints among the old ones plus `π k`. -/
theorem step_spec {n t : ℕ} (A : OnlineAlg n t) (G : BipGraph n) (π : Equiv.Perm (Fin n))
    (τ : Fin t → Bool) (M : Finset (Fin n × Fin n)) (k : Fin n)
    (hM : IsMatching M) (hsub : M ⊆ G) (hfresh : π k ∉ M.image Prod.snd) :
    IsMatching (step A G π τ M k) ∧ step A G π τ M k ⊆ G ∧
      (step A G π τ M k).image Prod.snd ⊆ insert (π k) (M.image Prod.snd) := by
  unfold step
  split
  · rename_i u hA
    by_cases hu : u ∈ nbrs G (π k) ∧ u ∉ M.image Prod.fst
    · rw [if_pos hu]
      have huv : (u, π k) ∈ G := mem_nbrs.mp hu.1
      have hnotMem : (u, π k) ∉ M := by
        intro hmem
        exact hfresh (Finset.mem_image.mpr ⟨(u, π k), hmem, rfl⟩)
      refine ⟨?_, ?_, ?_⟩
      · constructor
        · rw [Finset.image_insert, Finset.card_insert_of_notMem hu.2, hM.1,
            Finset.card_insert_of_notMem hnotMem]
        · rw [Finset.image_insert, Finset.card_insert_of_notMem hfresh, hM.2,
            Finset.card_insert_of_notMem hnotMem]
      · rw [Finset.insert_subset_iff]
        exact ⟨huv, hsub⟩
      · rw [Finset.image_insert]
    · rw [if_neg hu]
      exact ⟨hM, hsub, Finset.Subset.trans (Finset.Subset.refl _) (Finset.subset_insert _ _)⟩
  · rename_i hA
    exact ⟨hM, hsub, Finset.Subset.trans (Finset.Subset.refl _) (Finset.subset_insert _ _)⟩

/-- Main invariant: after any `k ≤ n` arrivals, the state is a matching of
`G`, and its online endpoints are among the first `k` arrivals. -/
theorem execUpTo_spec {n t : ℕ} (A : OnlineAlg n t) (G : BipGraph n) (π : Equiv.Perm (Fin n))
    (τ : Fin t → Bool) (k : ℕ) (hk : k ≤ n) :
    IsMatching (execUpTo A G π τ k) ∧ execUpTo A G π τ k ⊆ G ∧
      (execUpTo A G π τ k).image Prod.snd ⊆
        (((Finset.univ : Finset (Fin n)).filter fun i => i.val < k)).image π := by
  induction k with
  | zero =>
    refine ⟨isMatching_empty, Finset.empty_subset _, ?_⟩
    rw [execUpTo]
    simp
  | succ k ih =>
    have hkn : k < n := Nat.lt_of_succ_le hk
    obtain ⟨hM, hsub, hsnd⟩ := ih (Nat.le_of_lt hkn)
    have hfresh : π ⟨k, hkn⟩ ∉ (execUpTo A G π τ k).image Prod.snd := by
      intro hmem
      have h := hsnd hmem
      rw [Finset.mem_image] at h
      obtain ⟨i, hi, hii⟩ := h
      rw [Finset.mem_filter] at hi
      have hik : i = ⟨k, hkn⟩ := by
        have h1 : π.symm (π i) = π.symm (π ⟨k, hkn⟩) := congrArg π.symm hii
        rw [Equiv.symm_apply_apply, Equiv.symm_apply_apply] at h1
        exact h1
      rw [hik] at hi
      exact absurd hi.2 (lt_irrefl k)
    rw [execUpTo_succ A G π τ hkn]
    obtain ⟨h1, h2, h3⟩ := step_spec A G π τ _ ⟨k, hkn⟩ hM hsub hfresh
    refine ⟨h1, h2, Finset.Subset.trans h3 ?_⟩
    rw [Finset.insert_subset_iff]
    constructor
    · rw [Finset.mem_image]
      exact ⟨⟨k, hkn⟩, by rw [Finset.mem_filter]; exact ⟨Finset.mem_univ _, Nat.lt_succ_self k⟩, rfl⟩
    · apply Finset.Subset.trans hsnd
      apply Finset.image_subset_image
      intro i hi
      rw [Finset.mem_filter] at hi ⊢
      exact ⟨hi.1, Nat.lt_succ_of_lt hi.2⟩

/-- The execution of any online algorithm along any tape produces a matching
of `G`. -/
theorem exec_isMatching {n t : ℕ} (A : OnlineAlg n t) (G : BipGraph n)
    (π : Equiv.Perm (Fin n)) (τ : Fin t → Bool) :
    IsMatching (exec A G π τ) :=
  (execUpTo_spec A G π τ n le_rfl).1

/-- The execution only uses edges of `G`. -/
theorem exec_subset {n t : ℕ} (A : OnlineAlg n t) (G : BipGraph n) (π : Equiv.Perm (Fin n))
    (τ : Fin t → Bool) :
    exec A G π τ ⊆ G :=
  (execUpTo_spec A G π τ n le_rfl).2.1

/-- The produced matching is at most the maximum matching. -/
theorem execCard_le_matchingNumber {n t : ℕ} (A : OnlineAlg n t) (G : BipGraph n)
    (π : Equiv.Perm (Fin n)) (τ : Fin t → Bool) : execCard A G π τ ≤ matchingNumber G :=
  le_matchingNumber (exec_subset A G π τ) (exec_isMatching A G π τ)

/-- The expected matching size is at most the maximum matching (competitive
ratios never exceed `1`). -/
theorem expectedCard_le_matchingNumber {n t : ℕ} (A : OnlineAlg n t) (G : BipGraph n) :
    expectedCard A G ≤ (matchingNumber G : ℚ) := by
  have hdenom : (0 : ℚ) < (Nat.factorial n : ℚ) * 2 ^ t := by
    apply mul_pos
    · exact_mod_cast Nat.factorial_pos n
    · exact pow_pos (by norm_num) t
  unfold expectedCard
  rw [div_le_iff₀ hdenom]
  have hcardπ : (Fintype.card (Equiv.Perm (Fin n)) : ℚ) = Nat.factorial n := by
    rw [Fintype.card_perm, Fintype.card_fin]
  have hcardτ : (Fintype.card (Fin t → Bool) : ℚ) = 2 ^ t := by
    rw [Fintype.card_fun, Fintype.card_bool, Fintype.card_fin]
    norm_num
  calc (∑ π : Equiv.Perm (Fin n), ∑ τ : Fin t → Bool, (execCard A G π τ : ℚ))
      ≤ ∑ _π : Equiv.Perm (Fin n), ∑ _τ : Fin t → Bool, (matchingNumber G : ℚ) := by
        apply Finset.sum_le_sum
        intro π _
        apply Finset.sum_le_sum
        intro τ _
        exact_mod_cast execCard_le_matchingNumber A G π τ
    _ = (matchingNumber G : ℚ) * ((Nat.factorial n : ℚ) * 2 ^ t) := by
        rw [Finset.sum_const, Finset.sum_const, nsmul_eq_mul, nsmul_eq_mul, Finset.card_univ,
          Finset.card_univ, hcardπ, hcardτ]
        ring

/-- A tape of length `0` degenerates to determinism: the double average
collapses to the single average over the arrival permutations, since
`Fin 0 → Bool` has exactly one element and `2 ^ 0 = 1`. Hence the
deterministic algorithms are exactly the randomized ones with a zero-length
tape, and the `∃` in `conj` covers them. -/
theorem expectedCard_tape_zero {n : ℕ} (A : OnlineAlg n 0) (G : BipGraph n) :
    expectedCard A G =
      (∑ π : Equiv.Perm (Fin n), (execCard A G π (fun i => i.elim0) : ℚ)) / Nat.factorial n := by
  have hτ : ∀ τ : Fin 0 → Bool, τ = (fun i => i.elim0) :=
    fun τ => funext fun i => i.elim0
  have hsum : ∀ f : (Fin 0 → Bool) → ℚ,
      (∑ τ : Fin 0 → Bool, f τ) = f (fun i => i.elim0) := by
    intro f
    have huniv : (Finset.univ : Finset (Fin 0 → Bool)) = {fun i => i.elim0} := by
      ext τ
      simp only [Finset.mem_univ, Finset.mem_singleton, true_iff]
      exact hτ τ
    rw [huniv, Finset.sum_singleton]
  have hdouble : (∑ π : Equiv.Perm (Fin n), ∑ τ : Fin 0 → Bool, (execCard A G π τ : ℚ)) =
      ∑ π : Equiv.Perm (Fin n), (execCard A G π (fun i => i.elim0) : ℚ) := by
    apply Finset.sum_congr rfl
    intro π _
    exact hsum _
  unfold expectedCard
  rw [hdouble, pow_zero, mul_one]

/-- States grow along the execution. -/
theorem execUpTo_mono {n t : ℕ} (A : OnlineAlg n t) (G : BipGraph n) (π : Equiv.Perm (Fin n))
    (τ : Fin t → Bool) {k l : ℕ} (hkl : k ≤ l) (hl : l ≤ n) :
    execUpTo A G π τ k ⊆ execUpTo A G π τ l := by
  induction l with
  | zero => rw [Nat.le_zero.mp hkl]
  | succ l ih =>
    by_cases h : k ≤ l
    · have hln : l < n := Nat.lt_of_succ_le hl
      rw [execUpTo_succ A G π τ hln]
      exact Finset.Subset.trans (ih h (Nat.le_of_lt hln)) (step_self_subset A G π τ _ ⟨l, hln⟩)
    · have hkl' : k = l + 1 := le_antisymm hkl (Nat.succ_le_of_lt (Nat.lt_of_not_le h))
      rw [hkl']

/-! ### The greedy algorithm -/

/-- The greedy algorithm: match each arrival to the least still-available
offline neighbor, if any. It ignores its tape (a deterministic algorithm,
presented here with an arbitrary tape length). -/
def greedyAlg {n t : ℕ} : OnlineAlg n t :=
  fun _τ _k _hist used _v Nv =>
    if h : (Nv.filter fun u => u ∉ used).Nonempty then
      some ((Nv.filter fun u => u ∉ used).min' h)
    else none

/- The kernel recursion limit is raised so that `decide` can evaluate the
matching number and executions on small graphs (their powerset
search exceeds the default limit). This line is part of the fixed zone. -/
set_option maxRecDepth 8192

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

/-! ## Slot zone: the two main theorems -/

-- @[slot main]
/-- **The lower-bound direction** (threshold `3/4`, strictly inside the known
interval `(0.696, 0.82062…]`): from some size threshold `N` on, at every size
`n ≥ N` there is a randomized online matching algorithm (a deterministic
decision rule fed by a tape of `t` uniform random bits) whose expected
matching size — averaged over the uniformly random arrival permutation and the
uniform tape — is at least `3/4` of the maximum matching, for every graph.
Proving this improves the best known lower bound `0.696` (Mahdian–Yan 2011)
to `0.75`. -/
theorem conj :
    ∃ N : ℕ, ∀ n ≥ N, ∃ t : ℕ, ∃ A : OnlineAlg n t, ∀ G : BipGraph n,
      3 * (matchingNumber G : ℚ) ≤ 4 * expectedCard A G := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

-- @[slot main]
/-- **The impossibility direction**: the negation of `conj` — for every size
threshold `N` there is a size `n ≥ N` at which no randomized online algorithm
(any tape length, any decision rule) guarantees expected matching size `3/4`
of the maximum matching on every graph. This is the literature's upper-bound
shape: every randomized algorithm is beaten at infinitely many sizes, so no
algorithm has asymptotic guarantee `3/4`. Proving this improves the best
known upper bound (`0.823`, Manshadi–Oveis Gharan–Saberi 2012; improved to
`1 − e/e^e ≈ 0.82062`, Chierichetti et al. 2025) to `0.75`. -/
theorem refuted :
    ¬∃ N : ℕ, ∀ n ≥ N, ∃ t : ℕ, ∃ A : OnlineAlg n t, ∀ G : BipGraph n,
        3 * (matchingNumber G : ℚ) ≤ 4 * expectedCard A G := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

end OnlineMatching
