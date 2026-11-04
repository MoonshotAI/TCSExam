/-
Statement layer for the **constant-width ROBP PRG problem** (width 4):
does there exist an *explicit* family of pseudorandom generators `G n :
{0,1}^(s n) → {0,1}^n` that fools every width-4 length-`n` standard-order
read-once branching program with error `1/n`, with seed length
`s n = o(log² n)`?

Background: Nisan (Combinatorica 12, 1992, 449–461) gave explicit generators
with seed `O(log² n)` for all polynomial widths. For width 2 the problem is
solved with optimal seed `O(log(n/ε))` (small-bias spaces, via
Bogdanov–Dvir–Verbin–Yehudayoff, Theory Comput. 9, 2013, 283–293). For
width 3, Meka–Reingold–Tal (STOC 2019, 626–637) give seed
`Õ(log n · log(1/ε))` — at error `ε = 1/n` this is `Õ(log² n)`, no
asymptotic improvement over Nisan at that error. For width 4 no explicit
generator with seed `o(log² n)` at error `1/n` is known (Doron–Hoza,
APPROX/RANDOM 2025, 28: "for width-4 ROBPs, there are no known explicit
PRGs, WPRGs, or HSGs with seed length o(log² n)").

This file is the task's definition zone plus slot zone:
- The definition zone defines standard-order ROBPs (layered, width `w`,
  length `n`, layer `i` reads input bit `i`), the acceptance probability
  over uniform inputs, the fooled probability under a generator output, the
  `ε`-fooling relation, and a notion of explicitness for generator families
  (bit-wise computation by a single-tape Turing machine in polynomially
  many steps). All definitions are computable: claims about small concrete
  programs are provable by `decide`.
- The slot zone states the conjecture (`conj`) and its negation (`refuted`).
  Both proof bodies are left blank.

Fidelity notes (see `tests/reference/concept-ledger.md` of the packaged task):
1. "Width `w`" is normalized to *exactly* `w` states per layer with a
   designated start state in layer 0. Any program with `≤ w` states per
   layer embeds (unreachable dummy states), so the computed class — and
   hence the fooling question — is unchanged.
2. "Explicit" is pinned down: (1) the seed-length schedule `s` is uniformly
   polynomial-time computable (a fixed machine outputs `s n` from the unary
   `n` within a polynomial step bound), and (2) a single-tape Turing machine
   (over the alphabet `Option Bool`, blank `none`), given the unary encoding
   of `(n, y, i)`, computes the output bit `G n y i` within `k·n^c` steps
   for fixed constants `c k`. This is the standard "computable in time
   polynomial in `n`" reading of explicitness for PRGs (Hatami–Hoza 2024,
   §1.4; `n` in unary, since the output has length `n`), with the uniformity
   of the seed schedule made explicit — without clause (1), a constant
   machine could "compute" any sequence from a `{0,1}`-length seed, which is
   not the open problem's intent.
3. The seed bound `o(log² n)` is stated as `s n / (log n)² → 0` over `ℝ`
   (any log base is equivalent up to a constant factor).
-/

import Mathlib

/-! ### Read-once branching programs, acceptance probability, fooling -/

/-- A **read-once branching program** (ROBP) of length `n` and width `w` in
standard order: layers `0, …, n`, exactly `w` states per layer (`Fin w`),
a designated start state in layer 0, and a set of accepting states in the
final layer. Every state of layer `i` has one outgoing edge per bit value,
and layer `i` reads input bit `x i`: on input `x : Fin n → Bool` the
program walks from the start state, at layer `i` following the edge
labelled `x i`, and accepts iff the reached state of layer `n` is
accepting. -/
structure ROBP (n w : ℕ) where
  /-- Transition function: layer, current state, read bit → next state. -/
  step : Fin n → Fin w → Bool → Fin w
  /-- The start state (layer 0). -/
  start : Fin w
  /-- The accepting states of the final layer. -/
  accept : Fin w → Bool

namespace ROBP

variable {n w s : ℕ} (B : ROBP n w)

/-- The state reached after reading the whole input `x`. -/
def run (x : Fin n → Bool) : Fin w :=
  (List.finRange n).foldl (fun st i => B.step i st (x i)) B.start

/-- The `j`-th `n`-bit string (for `j < 2^n`): bit `i` is the `i`-th bit of
`j`. The map `j ↦ inputOf n j` is a bijection between `{0, …, 2^n - 1}`
and `Fin n → Bool`; it is used to enumerate the input space with plain
list operations (the kernel reduces these quickly; a `Finset.univ.filter`
over a function type does not reduce for this size). -/
def inputOf (n j : ℕ) : Fin n → Bool :=
  fun i => j.testBit i.val

/-- The bit encodings of all `n`-bit strings. -/
def allInputs (n : ℕ) : List ℕ :=
  List.finRange (2 ^ n)

/-- The number of inputs `x : Fin n → Bool` accepted by `B`: the inputs are
enumerated by their bit encodings `0, …, 2^n - 1` (see `inputOf`). -/
def acceptCount : ℕ :=
  (allInputs n).countP fun j => B.accept (B.run (inputOf n j))

/-- The acceptance probability of `B` on a uniform random input, as a
rational number. -/
def acceptProb : ℚ :=
  (B.acceptCount : ℚ) / 2 ^ n

/-- The number of seeds `y : Fin s → Bool` for which `B` accepts the
generator output `G y`. -/
def fooledCount (G : (Fin s → Bool) → (Fin n → Bool)) : ℕ :=
  (allInputs s).countP fun j => B.accept (B.run (G (inputOf s j)))

/-- The acceptance probability of `B` on `G y` for a uniform random seed
`y`, as a rational number. -/
def fooledProb (G : (Fin s → Bool) → (Fin n → Bool)) : ℚ :=
  (B.fooledCount G : ℚ) / 2 ^ s

/-- `G` **ε-fools** `B`: the acceptance probabilities on generator output
(uniform seed) and on uniform input differ by at most `ε`. -/
def Fools (ε : ℚ) (G : (Fin s → Bool) → (Fin n → Bool)) : Prop :=
  |B.fooledProb G - B.acceptProb| ≤ ε

/-- Division inequality in `ℚ`, cross-multiplied to `ℤ`: `Z/2^t ≤ c` iff
`Z·c.den ≤ c.num·2^t`. Used to give `Fools` a kernel-computable reading:
`Rat` arithmetic itself is opaque to the kernel (`Rat.normalize` uses
well-founded `Nat.gcd`), so `decide` evaluates integer forms instead. -/
theorem rat_div_pow_le_iff (Z : ℤ) (c : ℚ) {t : ℕ} (ht : 0 < (2 : ℚ) ^ t) :
    (Z : ℚ) / 2 ^ t ≤ c ↔ Z * (c.den : ℤ) ≤ c.num * 2 ^ t := by
  have hq : (0 : ℚ) < (c.den : ℚ) := by exact_mod_cast c.pos
  rw [div_le_iff₀ ht]
  conv_lhs => rw [← Rat.num_div_den c, div_mul_eq_mul_div]
  rw [le_div_iff₀ hq]
  norm_cast

/-- Common-denominator form of the acceptance-probability gap. -/
theorem rat_div_sub_div_pow (A C : ℕ) (s n : ℕ) :
    (A : ℚ) / 2 ^ s - (C : ℚ) / 2 ^ n =
      (((A : ℤ) * 2 ^ n - (C : ℤ) * 2 ^ s : ℤ) : ℚ) / 2 ^ (s + n) := by
  rw [pow_add]
  push_cast
  field_simp

/-- Cross-multiplied form of `Fools`: with `A = fooledCount G` and
`C = acceptCount`, the inequality `|A/2^s - C/2^n| ≤ ε` over `ℚ` is
equivalent to the single integer inequality
`|A·2^n - C·2^s|·ε.den ≤ ε.num·2^(s+n)`.
`Fools` keeps the faithful `|· - ·| ≤ ε` shape; this equivalent integer
form is what the kernel evaluates (see `rat_div_pow_le_iff`). -/
theorem fools_iff (ε : ℚ) (G : (Fin s → Bool) → (Fin n → Bool)) :
    B.Fools ε G ↔
      |(B.fooledCount G : ℤ) * 2 ^ n - (B.acceptCount : ℤ) * 2 ^ s| * (ε.den : ℤ) ≤
        ε.num * 2 ^ (s + n) := by
  have h2sn : (0 : ℚ) < (2 : ℚ) ^ (s + n) := by positivity
  unfold Fools fooledProb acceptProb
  rw [rat_div_sub_div_pow, abs_div, abs_of_pos h2sn, ← Int.cast_abs]
  exact rat_div_pow_le_iff _ ε h2sn

/-- Fooling is decidable: via `fools_iff` it reduces to integer
inequalities over the (finite, computable) acceptance counts, so `decide`
checks fooling claims — including quantified claims over finite families
of programs — by kernel computation. -/
instance (ε : ℚ) (G : (Fin s → Bool) → (Fin n → Bool)) :
    Decidable (B.Fools ε G) :=
  decidable_of_iff _ (B.fools_iff ε G).symm

/-- The identity generator (seed length `n`) fools every ROBP with zero
error: the two acceptance probabilities coincide by definition. -/
theorem fooledProb_id : B.fooledProb id = B.acceptProb := rfl

end ROBP

/-! ### Explicitness: single-tape Turing machines with a step bound -/

/-- Tape movement directions: left, right, stay. -/
inductive Dir | L | R | S

/-- A deterministic single-tape Turing machine over the alphabet
`Option Bool` (`none` is the blank symbol): `q` states, a start state, and
a transition function mapping `(state, symbol under the head)` to `none`
(halt) or `some (next state, symbol to write, direction)`. -/
structure TM where
  q : ℕ
  start : Fin q
  step : Fin q → Option Bool → Option (Fin q × Option Bool × Dir)

namespace TM

/-- A machine configuration: control state, the tape cells strictly left of
the head (nearest first), the cell under the head, and the cells strictly
right of the head (in order). Cells beyond the stored lists are blank. -/
structure Cfg (M : TM) where
  state : Fin M.q
  left : List (Option Bool)
  cur : Option Bool
  right : List (Option Bool)

/-- One transition step; `none` means the machine has halted. -/
def next (M : TM) (c : M.Cfg) : Option M.Cfg :=
  match M.step c.state c.cur with
  | none => none
  | some ⟨q', w, Dir.L⟩ => some ⟨q', c.left.tail, c.left.headD none, w :: c.right⟩
  | some ⟨q', w, Dir.R⟩ => some ⟨q', w :: c.left, c.right.headD none, c.right.tail⟩
  | some ⟨q', w, Dir.S⟩ => some ⟨q', c.left, w, c.right⟩

/-- Run for at most `fuel` steps; returns the halted configuration, or
`none` if the machine did not halt within `fuel` steps. -/
def run (M : TM) (fuel : ℕ) (c : M.Cfg) : Option M.Cfg :=
  match fuel with
  | 0 => none
  | fuel + 1 =>
    match M.next c with
    | none => some c
    | some c' => M.run fuel c'

/-- The initial configuration for a given tape contents: the head sits on
the first tape cell. -/
def initCfg (M : TM) (input : List (Option Bool)) : M.Cfg :=
  ⟨M.start, [], input.headD none, input.tail⟩

/-- `M` on the given tape contents halts within `fuel` steps with bit `b`
under the head. -/
def ComputesBit (M : TM) (input : List (Option Bool)) (fuel : ℕ) (b : Bool) : Prop :=
  (M.run fuel (M.initCfg input)).map Cfg.cur = some (some b)

end TM

/-- The tape encoding of `(n, y, i)`: `n` in unary, a blank, the seed bits,
a blank, then `i` in unary. -/
def encodeInput (n m : ℕ) (y : Fin m → Bool) (i : Fin n) : List (Option Bool) :=
  List.replicate n (some true) ++
    none :: ((List.ofFn fun j : Fin m => some (y j)) ++
    none :: List.replicate i.val (some true))

/-- The size parameter alone, in unary; the remaining tape is blank. -/
def unaryInput (n : ℕ) : List (Option Bool) :=
  List.replicate n (some true)

/-- Unary output begins at the halted head; the first non-`true` cell
terminates it. Implicit cells beyond the stored tape are blank. -/
def unaryOutput {M : TM} (cfg : M.Cfg) : ℕ :=
  ((cfg.cur :: cfg.right).takeWhile (fun b => b == some true)).length

/-- A halted computation producing a natural number, under the unary output
convention above. -/
def ComputesNat (M : TM) (input : List (Option Bool)) (fuel value : ℕ) : Prop :=
  (M.run fuel (M.initCfg input)).map unaryOutput = some value

/-- One fixed machine computes the seed *length* from the public size alone,
within a shifted polynomial number of steps (the shift handles `n = 0`
without a special case). This is the uniformity clause the generator's
explicitness requires on the seed-length schedule itself (Hatami–Hoza 2024,
§1.4, Definition 1.4 and §1.4.1); it constrains the arity `s n`, never the
random seed values, which remain inputs averaged over by `ROBP.Fools`. -/
def UniformSeedLength (s : ℕ → ℕ) : Prop :=
  ∃ (M : TM) (c k : ℕ), ∀ n : ℕ,
    ComputesNat M (unaryInput n) (k * (n + 1) ^ c) (s n)

/-- A generator family `G` with seed-length function `s` is **explicit**:
(1) the seed-length schedule `s` is uniformly polynomial-time computable
(`UniformSeedLength`), and (2) some single-tape Turing machine computes each
output bit `G n y i` from the encoding of `(n, y, i)` within `k · n ^ c`
steps, for fixed constants `c k` and every `n ≥ 1`. This is the standard
"computable in time polynomial in `n`" reading of explicitness for
pseudorandom generators (Hatami–Hoza 2024, §1.4), with the uniformity of the
seed schedule made explicit — without clause (1), a constant machine could
"compute" any sequence from a `{0,1}`-length seed, which is not the open
problem's intent. -/
def Explicit (s : ℕ → ℕ) (G : ∀ n, (Fin (s n) → Bool) → (Fin n → Bool)) : Prop :=
  UniformSeedLength s ∧
    ∃ (M : TM) (c k : ℕ), ∀ (n : ℕ) (_ : 1 ≤ n) (y : Fin (s n) → Bool) (i : Fin n),
      M.ComputesBit (encodeInput n (s n) y i) (k * n ^ c) (G n y i)

namespace ConstWidthPRG

/-! ### Concrete instances -/

/-- The length-4 width-2 ROBP computing the parity of its input: the state
is the running parity, and the program accepts iff the total parity is
odd. -/
def parityROBP : ROBP 4 2 where
  step := fun _ st b => st + (if b then 1 else 0)
  start := 0
  accept := fun st => st == 1

/-- The "AND generator" `{0,1}² → {0,1}³`, `(a, b) ↦ (a, a ∧ b, b)`. -/
def andGen : (Fin 2 → Bool) → (Fin 3 → Bool) :=
  fun y => ![y 0, y 0 && y 1, y 1]

/-- Transition tables of width-2 length-3 **permutation** programs,
encoded by `k < 2^6`: bit `(i·2 + b)` of `k` selects, for layer `i` and
read bit `b`, whether the transition swaps the two states or stays. (A
permutation ROBP has a permutation of the states on every layer-bit — for
width 2 the choices are stay or swap.) The map `k ↦ tableOfPerm k` is a
bijection between `{0, …, 63}` and the permutation tables; it enumerates
them with plain bit operations (the kernel reduces these quickly; a
`Finset.univ` over the nested function type does not reduce for this
size). -/
def tableOfPerm (k : ℕ) : Fin 3 → Fin 2 → Bool → Fin 2 :=
  fun i st b =>
    if k.testBit (i.val * 2 + (if b then 1 else 0)) then (if st = 0 then 1 else 0) else st

/-- The rational `1/4` as a structure literal — definitionally the reduced
form of `1/4` — so the kernel can project its numerator and denominator.
(`(1/4 : ℚ)` is `1 * 4⁻¹`, whose `Rat.normalize` does not reduce in the
kernel.) -/
def quarter : ℚ :=
  ⟨1, 4, by decide, Nat.coprime_one_left 4⟩

/- The kernel recursion limit is raised so that `decide` can evaluate the
acceptance/fooled probabilities on the small instances (their
enumeration exceeds the default limit). This line is part of the fixed
zone. -/
set_option maxRecDepth 8192

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

/-! ## Slot zone: the conjecture and its negation -/

-- @[slot main]
/-- **The constant-width PRG conjecture at width 4**: there exists an
explicit family of generators `G n : {0,1}^(s n) → {0,1}^n` fooling every
width-4 length-`n` standard-order ROBP with error `1/n`, with seed length
`s n = o(log² n)`. Open (Nisan 1992 gives seed `O(log² n)`; no
`o(log² n)`-seed explicit generator is known for any width `≥ 4`). -/
theorem conj :
    ∃ s : ℕ → ℕ, ∃ G : ∀ n, (Fin (s n) → Bool) → (Fin n → Bool),
      Explicit s G ∧
      (∀ n : ℕ, 1 ≤ n → ∀ B : ROBP n 4, B.Fools (1 / (n : ℚ)) (G n)) ∧
      Filter.Tendsto (fun n : ℕ => (s n : ℝ) / (Real.log n) ^ 2)
        Filter.atTop (nhds 0) := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

-- @[slot main]
/-- The negation of the conjecture: no explicit generator family with seed
length `o(log² n)` fools all width-4 length-`n` ROBPs with error `1/n`. -/
theorem refuted :
    ¬∃ s : ℕ → ℕ, ∃ G : ∀ n, (Fin (s n) → Bool) → (Fin n → Bool),
        Explicit s G ∧
        (∀ n : ℕ, 1 ≤ n → ∀ B : ROBP n 4, B.Fools (1 / (n : ℚ)) (G n)) ∧
        Filter.Tendsto (fun n : ℕ => (s n : ℝ) / (Real.log n) ^ 2)
          Filter.atTop (nhds 0) := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

end ConstWidthPRG
