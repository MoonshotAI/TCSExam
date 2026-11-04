/-
Self-contained statement layer for a theorem in property testing: a query
lower bound for monotonicity testing of Boolean functions.

The fixed part (everything above the end-of-fixed-part marker line) is the
definition layer the main theorem's statement needs: the Boolean cube with
monotonicity and the distance to it, multiplexer trees, the unique-activation
walk and the multiplexer map, the multilevel Talagrand function, the `Dyes`
and `Dno` sample spaces and their probabilities, the stronger oracle,
outcomes and their single-query updates, deterministic adaptive algorithms as
functions on query-answer histories, runs and acceptance probabilities, and
the query bound.  Fidelity notes live in `tests/reference/`.
-/

import Mathlib

set_option linter.unusedSectionVars false

namespace MonotonicityLB

/-! ## The Boolean cube, monotonicity, distance -/

/-- The Boolean cube `{0,1}^n`. -/
abbrev Cube (n : ℕ) := Fin n → Bool

/-- The pointwise order on the cube (`x i ≤ y i` for all coordinates
`i`), written with Boolean implications. -/
def CubeLE {n : ℕ} (x y : Cube n) : Prop := ∀ i, x i = true → y i = true

/-- The Hamming weight `|x|`. -/
def wt {n : ℕ} (x : Cube n) : ℕ := (Finset.univ.filter fun i => x i = true).card

/-- Monotonicity of a Boolean function: `x ≼ y` implies `f x ≤ f y`. -/
def IsMonotone {n : ℕ} (f : Cube n → Bool) : Prop :=
  ∀ x y, CubeLE x y → f x = true → f y = true

/-- The number of points on which `f` and `g` disagree; divided by `2^n` this
is the distance `dist(f, g)`. -/
def disagreeCount {n : ℕ} (f g : Cube n → Bool) : ℕ :=
  (Finset.univ.filter fun x => f x ≠ g x).card

/-- `f` is `ε`-far from monotone: every monotone `g` disagrees with `f` on at
least an `ε` fraction of the cube
(`dist(f, monotone) ≥ ε`). -/
def FarFromMono (n : ℕ) (ε : ℝ) (f : Cube n → Bool) : Prop :=
  ∀ g : Cube n → Bool, IsMonotone g → ε * 2 ^ n ≤ (disagreeCount f g : ℝ)

/-! ## Multiplexer trees, the unique-activation walk, and `ΓM` -/

/-- The parameters of the construction: `L = 2ℓ` levels, arity `N`, label size
`s = √n`, and cube dimension `n` (the construction's standing assumptions). -/
structure Params where
  L : ℕ
  N : ℕ
  s : ℕ
  n : ℕ
  hL : 0 < L
  hN : 0 < N

/-- The parameters used for the distributions and the main theorem: `n = m²`,
`s = m = √n`, `N = 2^m`, `L = 2ℓ`. -/
def Params.of (m ℓ : ℕ) (hℓ : 1 ≤ ℓ) : Params where
  L := 2 * ℓ
  N := 2 ^ m
  s := m
  n := m ^ 2
  hL := by omega
  hN := by positivity

/-- The canonical default node entry. -/
def Params.zeroPt (par : Params) : Fin par.N := ⟨0, par.hN⟩

/-- A label tuple: `s` coordinate indices, repetition allowed (so there are
`n^s` tuples; clauses likewise).  A tuple on an odd-level edge is read as a
term, on an even-level edge as a clause. -/
abbrev Lab (n s : ℕ) := Fin s → Fin n

/-- A multiplexer tree: a label tuple for every edge,
indexed by the level `j` and the target node of the edge.  A node at level
`j` is represented by a length-`L` tuple whose entries at positions `≥ j` all
equal the default `zeroPt` (the walk below only ever produces such normalized
tuples); the edge into the level-`j` node `u` is labelled `M ⟨j, _⟩ u`.
Labels at level `0` and on non-normalized tuples are never used. -/
abbrev MTree (L N s n : ℕ) := Fin (L + 1) → (Fin L → Fin N) → Lab n s

/-- The activation bit of level `j`: terms sit on odd levels and are activated
when all label bits are `1`; clauses sit on even levels and are activated
when all label bits are `0`. -/
def edgeBit (j : ℕ) : Bool := j % 2 == 1

/-- Edge activation: the edge into the level-`j` node `u`
is activated by `x` iff every label bit of `x` equals the level's activation
bit. -/
def edgeAct (par : Params) (M : MTree par.L par.N par.s par.n) (j : Fin (par.L + 1))
    (u : Fin par.L → Fin par.N) (x : Cube par.n) : Prop :=
  ∀ k, x (M j u k) = edgeBit j

/-- Truncation to level `j`: keep the first `j` entries, reset the rest to the
default.  The level-`j` node on the path to `u` is `trunc par j u`; the
parent of the level-`(j+1)` node `u` is `trunc par j u`. -/
def trunc (par : Params) (j : ℕ) (u : Fin par.L → Fin par.N) : Fin par.L → Fin par.N :=
  fun i => if (i : ℕ) < j then u i else par.zeroPt

/-- What stopped the walk: the walk reaches a
leaf, or stops at a node with no activated child edge (`none`) or at least
two (`multi`); the two truncation kinds are used by the oracle for query
points outside the middle layers, where the function value is already
known. -/
inductive StopKind where
  | leaf | none | multi | trunc0 | trunc1
  deriving DecidableEq

/-- The result of walking `x` down the multiplexer tree: `k` the level where
the walk stops, `node` the normalized node reached (the unique activation
path consists of its truncations), and `a₁ a₂` the two smallest activated
child indices in the `multi` case (junk otherwise). -/
structure WalkRes (L N : ℕ) where
  k : ℕ
  node : Fin L → Fin N
  kind : StopKind
  a₁ : Fin N
  a₂ : Fin N

/-- One step of the walk, iterated: from the level-`j` node `u`, count the
activated child edges;
if exactly one is activated, move down along it; if none or at least two,
stop.  Starting from the root at level `0` with fuel `L`, the walk stops at
level `k ≤ L`, and `k = L` means a leaf was reached. -/
def walkAux (par : Params) (M : MTree par.L par.N par.s par.n) (x : Cube par.n) :
    ℕ → ℕ → (Fin par.L → Fin par.N) → WalkRes par.L par.N
  | 0, j, u => ⟨j, u, .leaf, par.zeroPt, par.zeroPt⟩
  | fuel + 1, j, u =>
      if h : j < par.L then
        let act : Finset (Fin par.N) := Finset.univ.filter fun a =>
          ∀ k, x (M ⟨j + 1, by omega⟩ (Function.update u ⟨j, h⟩ a) k) = edgeBit (j + 1)
        if h1 : act.card = 1 then
          walkAux par M x fuel (j + 1)
            (Function.update u ⟨j, h⟩ (act.min' (Finset.card_pos.mp (by omega))))
        else if h0 : act.card = 0 then
          ⟨j, u, .none, par.zeroPt, par.zeroPt⟩
        else
          have hne : act.Nonempty := Finset.card_pos.mp (by omega)
          have hne₂ : (act.erase (act.min' hne)).Nonempty := Finset.card_pos.mp (by
            rw [Finset.card_erase_of_mem (Finset.min'_mem act hne)]; omega)
          ⟨j, u, .multi, act.min' hne, (act.erase (act.min' hne)).min' hne₂⟩
      else
        ⟨j, u, .leaf, par.zeroPt, par.zeroPt⟩

/-- The unique-activation walk of `x`: iterate the step `L` times from the
root. -/
def walk (par : Params) (M : MTree par.L par.N par.s par.n) (x : Cube par.n) :
    WalkRes par.L par.N :=
  walkAux par M x par.L 0 fun _ => par.zeroPt

/-- The value of the multiplexer map: the leaf reached, or one of the two
star labels. -/
inductive MuxVal (L N : ℕ) where
  | leaf (u : Fin L → Fin N) | star0 | star1

/-- The multiplexer map `ΓM`: the walk's leaf, or the star
label of the node where the walk stops — at an even (term) level, no
activated child edge gives `0*` and at least two give `1*`; at an odd
(clause) level the roles swap. -/
def gamma (par : Params) (M : MTree par.L par.N par.s par.n) (x : Cube par.n) :
    MuxVal par.L par.N :=
  let r := walk par M x
  match r.kind with
  | .leaf => .leaf r.node
  | .none => if r.k % 2 = 0 then .star0 else .star1
  | .multi => if r.k % 2 = 0 then .star1 else .star0
  | .trunc0 => .star0
  | .trunc1 => .star1

/-! ## The multilevel Talagrand function and the two distributions -/

/-- The (2ℓ)-level Talagrand function `f_{M,H}`: truncated
to `1` above the middle layers and to `0` below them; in the middle layers it
follows `ΓM`, evaluating `h_u` at a reached leaf `u`. -/
def talagrandFn (par : Params) (M : MTree par.L par.N par.s par.n)
    (H : (Fin par.L → Fin par.N) → Cube par.n → Bool) (x : Cube par.n) : Bool :=
  if par.n / 2 + par.s < wt x then true
  else if wt x < par.n / 2 - par.s then false
  else match gamma par M x with
    | .leaf u => H u x
    | .star0 => false
    | .star1 => true

/-- The yes-side leaf functions: every `h_u` is a constant function. -/
def yesH (par : Params) (c : (Fin par.L → Fin par.N) → Bool) :
    (Fin par.L → Fin par.N) → Cube par.n → Bool :=
  fun u _ => c u

/-- The no-side leaf functions: a global secret
variable `s` and, independently for each leaf, the dictatorship `x ↦ x_s`
(`σ u = true`) or the anti-dictatorship `x ↦ ¬x_s` (`σ u = false`). -/
def noH (par : Params) (s : Fin par.n) (σ : (Fin par.L → Fin par.N) → Bool) :
    (Fin par.L → Fin par.N) → Cube par.n → Bool :=
  fun u x => if σ u then x s else !(x s)

/-- The sample space of `Dyes`: a multiplexer tree and one constant bit per
leaf, both uniform and independent. -/
abbrev YesSample (par : Params) :=
  MTree par.L par.N par.s par.n × ((Fin par.L → Fin par.N) → Bool)

/-- The sample space of `Dno`: a multiplexer tree, a secret variable, and
one sign bit per leaf, all uniform and independent. -/
abbrev NoSample (par : Params) :=
  MTree par.L par.N par.s par.n × Fin par.n × ((Fin par.L → Fin par.N) → Bool)

/-- The function drawn from a yes-sample. -/
def yesFn (par : Params) (S : YesSample par) : Cube par.n → Bool :=
  talagrandFn par S.1 (yesH par S.2)

/-- The function drawn from a no-sample. -/
def noFn (par : Params) (S : NoSample par) : Cube par.n → Bool :=
  talagrandFn par S.1 (noH par S.2.1 S.2.2)

open Classical in
/-- The probability of an event under `Dyes`, as a ratio of cardinalities over
the finite sample space (events are predicates on samples). -/
noncomputable def yesProb (par : Params) (E : YesSample par → Prop) : ℝ :=
  ((Finset.univ.filter E).card : ℝ) / (Fintype.card (YesSample par) : ℝ)

open Classical in
/-- The probability of an event under `Dno`. -/
noncomputable def noProb (par : Params) (E : NoSample par → Prop) : ℝ :=
  ((Finset.univ.filter E).card : ℝ) / (Fintype.card (NoSample par) : ℝ)

/-! ## The stronger oracle, answers, and outcomes -/

/-- The strong oracle's answer to a query: the walk
result, the function value `b`, and the two leaf bits `b₁ b₂` revealed in the
multi case at level `L − 1` (junk in all other cases). -/
structure Answer (L N : ℕ) where
  res : WalkRes L N
  b : Bool
  b₁ : Bool
  b₂ : Bool

/-- The stronger oracle: for a query in the middle layers
it returns the unique activation path, the stop kind, the two smallest
activated child indices in the multi case, the value `f(x)`, and the two leaf
bits when the children of the stop node are leaves; for a query outside the
middle layers it returns the (already known) truncated value of `f`. -/
def oracle (par : Params) (M : MTree par.L par.N par.s par.n)
    (H : (Fin par.L → Fin par.N) → Cube par.n → Bool) (x : Cube par.n) :
    Answer par.L par.N :=
  if par.n / 2 + par.s < wt x then
    ⟨⟨0, fun _ => par.zeroPt, .trunc1, par.zeroPt, par.zeroPt⟩, true, true, true⟩
  else if wt x < par.n / 2 - par.s then
    ⟨⟨0, fun _ => par.zeroPt, .trunc0, par.zeroPt, par.zeroPt⟩, false, false, false⟩
  else
    let r := walk par M x
    let fv : Bool := match r.kind with
      | .leaf => H r.node x
      | .none => if r.k % 2 = 0 then false else true
      | .multi => if r.k % 2 = 0 then true else false
      | .trunc0 => false
      | .trunc1 => true
    if h : r.kind = .multi ∧ r.k + 1 = par.L then
      ⟨r, fv, H (Function.update r.node ⟨r.k, by omega⟩ r.a₁) x,
        H (Function.update r.node ⟨r.k, by omega⟩ r.a₂) x⟩
    else
      ⟨r, fv, true, true⟩

/-- An outcome: the query set `Q`; for every level `j` and
node `u`, the sets `P j u` of points known to activate the edge into `u` and
`R j u` of points known not to activate it; and for every leaf `u` the
revealed values `ρ u` of `h_u`. -/
structure Outcome (par : Params) where
  Q : Finset (Cube par.n)
  P : ℕ → (Fin par.L → Fin par.N) → Finset (Cube par.n)
  R : ℕ → (Fin par.L → Fin par.N) → Finset (Cube par.n)
  ρ : (Fin par.L → Fin par.N) → Cube par.n → Option Bool

/-- The path membership of the outcome construction: `x` is added to
`P j u` for every node `u` on its unique activation path beyond the root. -/
def memPath (par : Params) (r : WalkRes par.L par.N) (j : ℕ)
    (u : Fin par.L → Fin par.N) : Prop :=
  1 ≤ j ∧ j ≤ r.k ∧ u = trunc par j r.node

/-- The multi-case membership: `x` is also added to `P` of the two smallest
activated children of the stop node. -/
def memMultiChild (par : Params) (r : WalkRes par.L par.N) (j : ℕ)
    (u : Fin par.L → Fin par.N) : Prop :=
  r.kind = .multi ∧ j = r.k + 1 ∧
    ∃ h : r.k < par.L,
      u = Function.update r.node ⟨r.k, h⟩ r.a₁ ∨
        u = Function.update r.node ⟨r.k, h⟩ r.a₂

/-- Membership in `P j u` for a point with walk result `r`. -/
def memP (par : Params) (r : WalkRes par.L par.N) (j : ℕ)
    (u : Fin par.L → Fin par.N) : Prop :=
  memPath par r j u ∨ memMultiChild par r j u

/-- The sibling-edge membership: `x` is added to `R` of every sibling edge
of its path edges. -/
def memSibling (par : Params) (r : WalkRes par.L par.N) (j : ℕ)
    (u : Fin par.L → Fin par.N) : Prop :=
  ∃ j₀ : ℕ, j₀ < r.k ∧ j = j₀ + 1 ∧
    ∃ hj₀ : j₀ < par.L, ∃ a : Fin par.N, a ≠ r.node ⟨j₀, hj₀⟩ ∧
      u = Function.update (trunc par j₀ r.node) ⟨j₀, hj₀⟩ a

/-- The no-activation-case membership: with no activated child edge, `x` is
added to `R` of every child edge of the stop node. -/
def memStopChildNone (par : Params) (r : WalkRes par.L par.N) (j : ℕ)
    (u : Fin par.L → Fin par.N) : Prop :=
  r.kind = .none ∧ j = r.k + 1 ∧
    ∃ h : r.k < par.L, ∃ a : Fin par.N, u = Function.update r.node ⟨r.k, h⟩ a

/-- The multi-case membership into `R`: `x` is added to `R` of every child
edge `a < a₂` with `a ≠ a₁` of the stop node. -/
def memStopChildMulti (par : Params) (r : WalkRes par.L par.N) (j : ℕ)
    (u : Fin par.L → Fin par.N) : Prop :=
  r.kind = .multi ∧ j = r.k + 1 ∧
    ∃ h : r.k < par.L, ∃ a : Fin par.N,
      (a : ℕ) < (r.a₂ : ℕ) ∧ a ≠ r.a₁ ∧ u = Function.update r.node ⟨r.k, h⟩ a

/-- Membership in `R j u` for a point with walk result `r`. -/
def memR (par : Params) (r : WalkRes par.L par.N) (j : ℕ)
    (u : Fin par.L → Fin par.N) : Prop :=
  memSibling par r j u ∨ memStopChildNone par r j u ∨ memStopChildMulti par r j u

/-- The `ρ` membership: the value `h_u(x)` is revealed when `u` is the
reached leaf, or when the walk stops one level above the leaves and `u` is one
of the two smallest activated children. -/
def memRho (par : Params) (r : WalkRes par.L par.N) (u : Fin par.L → Fin par.N) : Prop :=
  (r.kind = .leaf ∧ u = r.node) ∨
    (r.kind = .multi ∧ r.k + 1 = par.L ∧
      ∃ h : r.k < par.L,
        u = Function.update r.node ⟨r.k, h⟩ r.a₁ ∨
          u = Function.update r.node ⟨r.k, h⟩ r.a₂)

open Classical in
/-- The outcome of `f_{M,H}` on a query set `Q`. -/
noncomputable def outcomeOf (par : Params) (M : MTree par.L par.N par.s par.n)
    (H : (Fin par.L → Fin par.N) → Cube par.n → Bool) (Q : Finset (Cube par.n)) :
    Outcome par where
  Q := Q
  P := fun j u => Q.filter fun x => memP par (walk par M x) j u
  R := fun j u => Q.filter fun x => memR par (walk par M x) j u
  ρ := fun u x => if x ∈ Q ∧ memRho par (walk par M x) u then some (H u x) else none

/-- The bit of `h_u(x)` revealed by an answer: the
function value in the leaf case, and the two leaf bits in the multi case at
level `L − 1`. -/
def answerBit (par : Params) (ans : Answer par.L par.N) (u : Fin par.L → Fin par.N) :
    Bool :=
  if ans.res.kind = .multi ∧
      ∃ h : ans.res.k < par.L, u = Function.update ans.res.node ⟨ans.res.k, h⟩ ans.res.a₁ then
    ans.b₁
  else if ans.res.kind = .multi ∧
      ∃ h : ans.res.k < par.L, u = Function.update ans.res.node ⟨ans.res.k, h⟩ ans.res.a₂ then
    ans.b₂
  else ans.b

/-- The truncation kinds carry no tree information. -/
def isTrunc (k : StopKind) : Prop := k = .trunc0 ∨ k = .trunc1

open Classical in
/-- The outcome update after one query: insert `x` into
the sets selected by the answer's walk result.  A truncation answer (the
query is outside the middle layers) leaves the outcome unchanged. -/
noncomputable def addPoint (par : Params) (O : Outcome par) (x : Cube par.n)
    (ans : Answer par.L par.N) : Outcome par where
  Q := if isTrunc ans.res.kind then O.Q else insert x O.Q
  P := fun j u => if isTrunc ans.res.kind then O.P j u
    else if memP par ans.res j u then insert x (O.P j u) else O.P j u
  R := fun j u => if isTrunc ans.res.kind then O.R j u
    else if memR par ans.res j u then insert x (O.R j u) else O.R j u
  ρ := fun u y => if isTrunc ans.res.kind then O.ρ u y
    else if y = x ∧ memRho par ans.res u then some (answerBit par ans u) else O.ρ u y

/-- The empty outcome (the root of the algorithm tree). -/
def emptyOutcome (par : Params) : Outcome par where
  Q := ∅
  P := fun _ _ => ∅
  R := fun _ _ => ∅
  ρ := fun _ _ => none

/-! ## Algorithms, runs, and acceptance probabilities -/

/-- A deterministic adaptive query algorithm against the strong oracle, viewed
as a depth-`q` tree: the next query and the final verdict are functions of
the history of query-answer pairs (the vertices of the algorithm tree are the
histories). -/
structure DetAlg (par : Params) where
  depth : ℕ
  next : List (Cube par.n × Answer par.L par.N) → Cube par.n
  decide : List (Cube par.n × Answer par.L par.N) → Bool

/-- The history of a run (the path from the root in the algorithm tree). -/
def runHist (par : Params) (M : MTree par.L par.N par.s par.n)
    (H : (Fin par.L → Fin par.N) → Cube par.n → Bool) (A : DetAlg par) :
    ℕ → List (Cube par.n × Answer par.L par.N)
  | 0 => []
  | t + 1 =>
      let h := runHist par M H A t
      h ++ [(A.next h, oracle par M H (A.next h))]

/-- The outcome at the end of a run. -/
noncomputable def runOutcome (par : Params) (M : MTree par.L par.N par.s par.n)
    (H : (Fin par.L → Fin par.N) → Cube par.n → Bool) (A : DetAlg par) : Outcome par :=
  (runHist par M H A A.depth).foldl
    (fun O qa => addPoint par O qa.1 qa.2) (emptyOutcome par)

/-- The run accepts. -/
def runAccepts (par : Params) (M : MTree par.L par.N par.s par.n)
    (H : (Fin par.L → Fin par.N) → Cube par.n → Bool) (A : DetAlg par) : Bool :=
  A.decide (runHist par M H A A.depth)

open Classical in
/-- The acceptance probability of a deterministic algorithm under `Dyes`. -/
noncomputable def yesAcc (par : Params) (A : DetAlg par) : ℝ :=
  yesProb par fun S : YesSample par => runAccepts par S.1 (yesH par S.2) A = true

open Classical in
/-- The acceptance probability of a deterministic algorithm under `Dno`. -/
noncomputable def noAcc (par : Params) (A : DetAlg par) : ℝ :=
  noProb par fun S : NoSample par => runAccepts par S.1 (noH par S.2.1 S.2.2) A = true

open Classical in
/-- The joint probability, under `Dno`, that a deterministic algorithm accepts
and the drawn function is `ε`-far from monotone. -/
noncomputable def noAccFar (par : Params) (A : DetAlg par) (ε : ℝ) : ℝ :=
  noProb par fun S : NoSample par =>
    runAccepts par S.1 (noH par S.2.1 S.2.2) A = true ∧ FarFromMono par.n ε (noFn par S)

/-- The acceptance probability under `Dyes` of a randomized algorithm, a
finite weighted family of deterministic algorithms. -/
noncomputable def yesAccMix (par : Params) {ι : Type} [Fintype ι] (A : ι → DetAlg par)
    (w : ι → ℝ) : ℝ :=
  ∑ i, w i * yesAcc par (A i)

/-- The joint accept-and-far probability under `Dno` of a randomized
algorithm. -/
noncomputable def noAccFarMix (par : Params) {ι : Type} [Fintype ι] (A : ι → DetAlg par)
    (w : ι → ℝ) (ε : ℝ) : ℝ :=
  ∑ i, w i * noAccFar par (A i) ε

/-- The query bound: `q = n^{1/2−1/(4ℓ+2)} / log₂ n` with `n = m²`. -/
noncomputable def qbound (m ℓ : ℕ) : ℝ :=
  ((m : ℝ) ^ 2) ^ ((1 : ℝ) / 2 - 1 / (4 * ℓ + 2)) / Real.logb 2 ((m : ℝ) ^ 2)

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- but the fixed part above and the main-theorem statement must not be
-- modified.

/-- The main theorem, in the distribution-tester form: for every `ℓ ≥ 1`
there are a testing distance `ε > 0`, an error `δ > 0`, and a threshold `m₀`
such that for all `m ≥ m₀` no randomized algorithm whose deterministic
members all have depth at most `q = n^{1/2−1/(4ℓ+2)}/log₂ n` (with `n = m²`)
can both accept with `Dyes`-probability at least `1 − δ` and, jointly under
`Dno`, accept an `ε`-far-from-monotone function with probability at most
`δ`. -/
theorem monotonicity_testing_lb (ℓ : ℕ) (hℓ : 1 ≤ ℓ) :
    ∃ ε : ℝ, 0 < ε ∧ ∃ δ : ℝ, 0 < δ ∧ ∃ m₀ : ℕ, ∀ m : ℕ, m₀ ≤ m →
      ∀ (ι : Type) [Fintype ι] (A : ι → DetAlg (Params.of m ℓ hℓ)) (w : ι → ℝ),
        (∀ i, 0 ≤ w i) → (∑ i, w i = 1) →
          (∀ i, ((A i).depth : ℝ) ≤ qbound m ℓ) →
            ¬ (1 - δ ≤ yesAccMix (Params.of m ℓ hℓ) A w ∧
               noAccFarMix (Params.of m ℓ hℓ) A w ε ≤ δ) := by
  -- CHECKPOINT monotonicity_testing_lb BEGIN
  sorry
  -- CHECKPOINT monotonicity_testing_lb END

end MonotonicityLB
