/-
Statement layer for "NP versus ACC": the conjecture that some language in NP
cannot be computed by any ACC circuit family — that is, by no family of
constant-depth, polynomial-size circuits over unbounded-fan-in AND/OR/MOD_m
gates (`MOD_m` outputs 1 iff the number of 1s among its inputs is a multiple
of the fixed modulus `m`). The conjecture became an explicit target with
Williams' "algorithmic method" (algorithm design implies circuit lower
bounds; Williams 2011 proved `NEXP ⊄ ACC`, Murray–Williams 2018 improved it
to `NQP ⊄ ACC`); the textbook statement is in Arora–Barak, *Computational
Complexity: A Modern Approach*, Chapter 14.

This file is the task's definition zone plus slot zone:
- The definition zone defines Boolean circuits over an arbitrary gate basis
  (DAG by topological order, acyclicity built in), evaluation and depth by
  structural recursion (so concrete circuits compute by kernel reduction),
  the AND/OR basis, the ACC basis with modulus `m`, the dense CNF-matrix
  encoding of SAT as a Boolean function family `satFamily`, ACC membership
  (`InACC`), the MOD₂ characteristic family, and a concrete two-input circuit
  over the MOD₃ basis. All API lemmas in this zone are fully proved.
- The slot zone states the conjecture (`conj`: `satFamily` has no ACC
  circuit family) and its negation (`refuted`). Both proof bodies are left
  blank.

Fidelity notes (see `tests/reference/concept-ledger.md` of the packaged task):
1. "Some language in NP" is pinned to the standard NP-complete language SAT
   (dense CNF-matrix encoding). SAT is NP-complete under AC⁰ reductions, and
   ACC is closed under AC⁰ reductions, so `SAT ∉ ACC ⟺ NP ⊄ ACC`; mathlib has
   no polynomial-time predicate to quantify over "all NP languages".
2. A single modulus `m` is quantified existentially (`∃ m`); allowing a
   fixed finite set of moduli gives the same class (MOD_a ∧ MOD_b computes
   MOD_{lcm(a,b)}), so nothing is lost.
3. The circuit layer is adapted from SamuelSchlesinger/circuit-complexity
   (Apache-2.0, see the copyright notice below): `Basis` renamed to
   `CircuitBasis` (mathlib already declares `Basis`), and the
   evaluator/depth functions are re-implemented by structural recursion on
   the number of processed gates (the original uses well-founded recursion
   on the wire index) so that `decide` works on concrete circuits.

The circuit layer (structures `CircuitBasis`, `Gate`, `Circuit` and the
basic evaluation/depth API) is adapted from
https://github.com/SamuelSchlesinger/circuit-complexity
Copyright 2026 Samuel Schlesinger, licensed under the Apache License,
Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0). Changes are listed
in fidelity note 3 above.
-/

import Mathlib

/-! ### Bit strings, Boolean function families, gate bases -/

/-- A BitString of length `n`. -/
abbrev BitString n := Fin n → Bool

/-- A family of Boolean functions indexed by input length `N`.

Each member maps `N`-bit strings to a single output bit. -/
abbrev BoolFunFamily := (N : Nat) → BitString N → Bool

/-- Arity constraint for operations in a basis. -/
inductive Arity where
  | unbounded
  | exactly (k : Nat)
  | upto (k : Nat)
  deriving Repr, DecidableEq

/-- Whether `n` satisfies an arity constraint. -/
def Arity.satisfiedBy : Arity → Nat → Prop
  | .unbounded, _ => True
  | .exactly k, n => n = k
  | .upto k, n => n ≤ k

instance (a : Arity) (n : Nat) : Decidable (a.satisfiedBy n) := by
  cases a <;> simp only [Arity.satisfiedBy] <;> exact inferInstance

/-- A basis of Boolean operations.

Each operation has an arity constraint and an evaluation function that
computes the output bit from any valid number of input bits. (Adapted from
`Basis` in SamuelSchlesinger/circuit-complexity, renamed to avoid colliding
with mathlib's linear-algebra `Basis`.) -/
structure CircuitBasis where
  /-- The type of operations (e.g., AND, OR, MOD_m). -/
  Op : Type
  /-- The arity constraint for each operation. -/
  arity : Op → Arity
  /-- Evaluate an operation on `n` input bits, given that `n` satisfies the arity. -/
  eval : (op : Op) → (n : Nat) → (arity op).satisfiedBy n → BitString n → Bool

/-- A gate in a circuit over basis `B` with `W` wires available as inputs.
The gate's fan-in must satisfy the arity constraint of its operation, and
each input is wired to one of the `W` available wires and carries a free
negation flag (negations are free in circuit complexity). -/
structure Gate (B : CircuitBasis) (W : Nat) where
  op : B.Op
  fanIn : Nat
  arityOk : (B.arity op).satisfiedBy fanIn
  inputs : Fin fanIn → Fin W
  /-- Per-input negation flag. -/
  negated : Fin fanIn → Bool

/-- Evaluate a gate given a wire-value assignment. -/
def Gate.eval (g : Gate B W) (wireVal : BitString W) : Bool :=
  B.eval g.op g.fanIn g.arityOk (fun i => (g.negated i).xor (wireVal (g.inputs i)))

/-- A Boolean circuit over basis `B` with `N` input wires, `M` output gates
and `G` internal gates.

All gates reference wires from `Fin (N + G)`. The `acyclic` field forces
internal gate `i` to read only wires `0, …, N + i − 1`, so the wires come in
topological order and the circuit is a DAG by construction. -/
structure Circuit (B : CircuitBasis) (N M G : Nat) [NeZero N] [NeZero M] where
  gates : Fin G → Gate B (N + G)
  outputs : Fin M → Gate B (N + G)
  acyclic : ∀ (i : Fin G) (k : Fin (gates i).fanIn),
    ((gates i).inputs k).val < N + i.val

namespace Circuit

variable {B : CircuitBasis} {N M G : Nat} [NeZero N] [NeZero M]

/-- Values of the first `N + k` wires when the circuit is fed `input`: the
first `N` wires carry the primary inputs, and wire `N + i` (for `i < k`)
carries internal gate `i` evaluated on the values of the earlier wires.
Structural recursion on `k`, so concrete circuits evaluate by kernel
reduction. -/
def wireValuesUpTo (c : Circuit B N M G) (input : BitString N) :
    (k : Nat) → BitString (N + k)
  | 0 => input
  | k + 1 => fun w =>
      if h : w.val < N + k then
        c.wireValuesUpTo input k ⟨w.val, h⟩
      else
        if hk : k < G then
          B.eval (c.gates ⟨k, hk⟩).op (c.gates ⟨k, hk⟩).fanIn
            (c.gates ⟨k, hk⟩).arityOk
            (fun j => ((c.gates ⟨k, hk⟩).negated j).xor
              (c.wireValuesUpTo input k
                ⟨((c.gates ⟨k, hk⟩).inputs j).val, c.acyclic ⟨k, hk⟩ j⟩))
        else
          false

theorem wireValuesUpTo_zero (c : Circuit B N M G) (input : BitString N) :
    c.wireValuesUpTo input 0 = input := rfl

theorem wireValuesUpTo_succ (c : Circuit B N M G) (input : BitString N) (k : Nat)
    (w : Fin (N + (k + 1))) :
    c.wireValuesUpTo input (k + 1) w =
      if h : w.val < N + k then
        c.wireValuesUpTo input k ⟨w.val, h⟩
      else
        if hk : k < G then
          B.eval (c.gates ⟨k, hk⟩).op (c.gates ⟨k, hk⟩).fanIn
            (c.gates ⟨k, hk⟩).arityOk
            (fun j => ((c.gates ⟨k, hk⟩).negated j).xor
              (c.wireValuesUpTo input k
                ⟨((c.gates ⟨k, hk⟩).inputs j).val, c.acyclic ⟨k, hk⟩ j⟩))
        else
          false := rfl

/-- Wire values computed after processing `l ≥ k` gates agree, on the first
`N + k` wires, with those computed after `k` gates: later gates only append
new wires. -/
theorem wireValuesUpTo_agree (c : Circuit B N M G) (input : BitString N) :
    ∀ {k l : Nat} (hkl : k ≤ l) (w : Fin (N + k)) (hl : w.val < N + l),
      c.wireValuesUpTo input l ⟨w.val, hl⟩ = c.wireValuesUpTo input k w := by
  intro k l
  induction l generalizing k with
  | zero =>
    intro hkl w hl
    cases Nat.eq_zero_of_le_zero hkl
    rfl
  | succ l ih =>
    intro hkl w hl
    rcases Nat.eq_or_lt_of_le hkl with rfl | hlt
    · rfl
    · have hkl' : k ≤ l := Nat.lt_succ_iff.mp hlt
      have hw : w.val < N + l :=
        Nat.lt_of_lt_of_le w.isLt (Nat.add_le_add_left hkl' N)
      rw [wireValuesUpTo_succ, dif_pos hw]
      exact ih hkl' w hw

/-- Value of wire `w` when the circuit is fed `input`. The first `N` wires
carry the primary inputs; wire `N + i` carries the output of internal gate
`i`. -/
def wireValue (c : Circuit B N M G) (input : BitString N) (w : Fin (N + G)) : Bool :=
  c.wireValuesUpTo input G w

/-- Primary input wires (index < N) carry the input bits. -/
theorem wireValue_lt (c : Circuit B N M G) (input : BitString N)
    (w : Fin (N + G)) (h : w.val < N) :
    c.wireValue input w = input ⟨w.val, h⟩ := by
  have hag := c.wireValuesUpTo_agree input (Nat.zero_le G) ⟨w.val, h⟩ w.isLt
  rw [wireValuesUpTo_zero] at hag
  exact hag

/-- Internal wire `N + i` carries gate `i` evaluated on the full wire-value
vector. This is the one-step unfolding equation for the evaluator. -/
theorem wireValue_gate (c : Circuit B N M G) (input : BitString N) (i : Fin G) :
    c.wireValue input ⟨N + i.val, Nat.add_lt_add_left i.isLt N⟩ =
      Gate.eval (c.gates i) (c.wireValue input) := by
  show c.wireValuesUpTo input G ⟨N + i.val, Nat.add_lt_add_left i.isLt N⟩ =
    Gate.eval (c.gates i) (c.wireValue input)
  rw [c.wireValuesUpTo_agree input (Nat.succ_le_of_lt i.isLt)
      ⟨N + i.val, Nat.add_lt_add_left (Nat.lt_succ_self i.val) N⟩
      (Nat.add_lt_add_left i.isLt N),
    wireValuesUpTo_succ,
    dif_neg (Nat.lt_irrefl (N + i.val)), dif_pos i.isLt]
  show B.eval _ _ _ _ = B.eval _ _ _ _
  congr 1
  funext j
  congr 1
  exact (c.wireValuesUpTo_agree input (Nat.le_of_lt i.isLt)
    ⟨((c.gates i).inputs j).val, c.acyclic i j⟩ ((c.gates i).inputs j).isLt).symm

/-- Depths of the first `N + k` wires: primary inputs have depth 0, and wire
`N + i` (internal gate `i`, for `i < k`) has depth one more than the maximum
depth of its input wires. Structural recursion on `k`. -/
def wireDepthsUpTo (c : Circuit B N M G) : (k : Nat) → Fin (N + k) → Nat
  | 0 => fun _ => 0
  | k + 1 => fun w =>
      if h : w.val < N + k then
        c.wireDepthsUpTo k ⟨w.val, h⟩
      else
        if hk : k < G then
          1 + Fin.foldl (c.gates ⟨k, hk⟩).fanIn
            (fun acc j => max acc
              (c.wireDepthsUpTo k
                ⟨((c.gates ⟨k, hk⟩).inputs j).val, c.acyclic ⟨k, hk⟩ j⟩)) 0
        else
          0

theorem wireDepthsUpTo_zero (c : Circuit B N M G) :
    c.wireDepthsUpTo 0 = fun _ => 0 := rfl

theorem wireDepthsUpTo_succ (c : Circuit B N M G) (k : Nat) (w : Fin (N + (k + 1))) :
    c.wireDepthsUpTo (k + 1) w =
      if h : w.val < N + k then
        c.wireDepthsUpTo k ⟨w.val, h⟩
      else
        if hk : k < G then
          1 + Fin.foldl (c.gates ⟨k, hk⟩).fanIn
            (fun acc j => max acc
              (c.wireDepthsUpTo k
                ⟨((c.gates ⟨k, hk⟩).inputs j).val, c.acyclic ⟨k, hk⟩ j⟩)) 0
        else
          0 := rfl

/-- Wire depths computed after processing `l ≥ k` gates agree, on the first
`N + k` wires, with those computed after `k` gates. -/
theorem wireDepthsUpTo_agree (c : Circuit B N M G) :
    ∀ {k l : Nat} (hkl : k ≤ l) (w : Fin (N + k)) (hl : w.val < N + l),
      c.wireDepthsUpTo l ⟨w.val, hl⟩ = c.wireDepthsUpTo k w := by
  intro k l
  induction l generalizing k with
  | zero =>
    intro hkl w hl
    cases Nat.eq_zero_of_le_zero hkl
    rfl
  | succ l ih =>
    intro hkl w hl
    rcases Nat.eq_or_lt_of_le hkl with rfl | hlt
    · rfl
    · have hkl' : k ≤ l := Nat.lt_succ_iff.mp hlt
      have hw : w.val < N + l :=
        Nat.lt_of_lt_of_le w.isLt (Nat.add_le_add_left hkl' N)
      rw [wireDepthsUpTo_succ, dif_pos hw]
      exact ih hkl' w hw

/-- Depth of wire `w` in the circuit DAG. Primary inputs have depth 0. -/
def wireDepth (c : Circuit B N M G) (w : Fin (N + G)) : Nat :=
  c.wireDepthsUpTo G w

/-- Primary input wires (index < N) have depth 0. -/
theorem wireDepth_lt (c : Circuit B N M G) (w : Fin (N + G)) (h : w.val < N) :
    c.wireDepth w = 0 := by
  have hag := c.wireDepthsUpTo_agree (Nat.zero_le G) ⟨w.val, h⟩ w.isLt
  rw [wireDepthsUpTo_zero] at hag
  exact hag

/-- Depth contributed by a single output gate: one layer for the gate itself
plus the maximum `wireDepth` of its inputs. Always ≥ 1. -/
def outputDepth (c : Circuit B N M G) (j : Fin M) : Nat :=
  1 + Fin.foldl (c.outputs j).fanIn
    (fun acc i => max acc (c.wireDepth ((c.outputs j).inputs i))) 0

/-- Depth of a circuit: the maximum `outputDepth` over all output gates. -/
def depth (c : Circuit B N M G) : Nat :=
  Fin.foldl M (fun acc j => max acc (c.outputDepth j)) 0

/-- Evaluate a circuit: map an `N`-bit input to an `M`-bit output. -/
def eval (c : Circuit B N M G) (input : BitString N) : BitString M :=
  fun j => (c.outputs j).eval (c.wireValue input)

/-- The size of a circuit is its total number of gates (internal + output). -/
def size (_ : Circuit B N M G) : Nat := G + M

end Circuit

/-! ### The AND/OR basis and the ACC basis -/

/-- Operations in an AND/OR basis. Negation is handled by per-input flags on
gates, so only AND and OR need explicit representation. -/
inductive AONOp where
  | and
  | or
  deriving Repr, DecidableEq

/-- Evaluate an AND or OR operation on `n` input bits by folding.
AND folds with `&&` starting from `true`; OR folds with `||` from `false`. -/
def AONOp.eval : (op : AONOp) → (n : Nat) → BitString n → Bool
  | .and, n, inputs => Fin.foldl n (fun acc i => acc && inputs i) true
  | .or, n, inputs => Fin.foldl n (fun acc i => acc || inputs i) false

/-- AND/OR basis with unbounded fan-in. Negation is free (per-input flags). -/
def aonBasis : CircuitBasis where
  Op := AONOp
  arity _ := .unbounded
  eval op n _ inputs := op.eval n inputs

/-- Operations of an ACC basis: AND, OR (unbounded fan-in) and MOD_m, where
the modulus `m` is a parameter of the basis (`accBasis m`). -/
inductive ACCOp where
  | and
  | or
  | mod
  deriving Repr, DecidableEq

/-- Evaluate an ACC operation on `n` input bits: AND/OR by folding; MOD_m
returns `true` iff the number of `true` inputs is a multiple of `m`. -/
def ACCOp.eval (m : Nat) : (op : ACCOp) → (n : Nat) → BitString n → Bool
  | .and, n, inputs => Fin.foldl n (fun acc i => acc && inputs i) true
  | .or, n, inputs => Fin.foldl n (fun acc i => acc || inputs i) false
  | .mod, n, inputs => (Fin.foldl n (fun acc i => acc + (inputs i).toNat) 0) % m == 0

/-- The ACC basis with modulus `m`: unbounded fan-in AND, OR and MOD_m gates,
negation free (per-input flags). -/
def accBasis (m : Nat) : CircuitBasis where
  Op := ACCOp
  arity _ := .unbounded
  eval op n _ inputs := ACCOp.eval m op n inputs

/-! ### SAT as a Boolean function family (dense CNF-matrix encoding) -/

/-- The variable indexed by literal slot `s`: slots `2j` and `2j+1` hold the
positive and negative literal of variable `j`. -/
def litVar {n : Nat} (s : Fin (2 * n)) : Fin n :=
  ⟨s.val / 2, by have h := s.isLt; omega⟩

/-- Literal slot `s` is true under assignment `σ`: even slots are positive
literals, odd slots negative literals. -/
def litSat {n : Nat} (σ : Fin n → Bool) (s : Fin (2 * n)) : Bool :=
  if s.val % 2 = 0 then σ (litVar s) else !σ (litVar s)

/-- Clause `i` of an encoded CNF formula is satisfied by assignment `σ`:
some literal slot of the clause is present in the formula (matrix bit set)
and true under `σ`. Position `(i, s)` of the `n × 2n` clause–literal matrix
is bit `finProdFinEquiv (i, s)` of the encoding. -/
def satClause {n : Nat} (x : BitString (n * (2 * n))) (σ : Fin n → Bool)
    (i : Fin n) : Prop :=
  ∃ s : Fin (2 * n), x (finProdFinEquiv (i, s)) = true ∧ litSat σ s = true

instance {n : Nat} (x : BitString (n * (2 * n))) (σ : Fin n → Bool) (i : Fin n) :
    Decidable (satClause x σ i) := by
  unfold satClause; infer_instance

/-- The CNF formula encoded by `x` is satisfiable: some assignment satisfies
every clause. -/
def cnfSat {n : Nat} (x : BitString (n * (2 * n))) : Prop :=
  ∃ σ : Fin n → Bool, ∀ i : Fin n, satClause x σ i

instance {n : Nat} (x : BitString (n * (2 * n))) : Decidable (cnfSat x) := by
  unfold cnfSat; infer_instance

/-- Auxiliary for `satVars`: starting from `acc`, keep incrementing (at most
`fuel` times) while the next value still satisfies `n * (2 * n) ≤ N`.
Structural recursion on `fuel`, so the kernel evaluates it on concrete
lengths (`Nat.sqrt` does not reduce in the kernel). -/
def satVarsGo (N : Nat) : Nat → Nat → Nat
  | 0, acc => acc
  | fuel + 1, acc =>
    if (acc + 1) * (2 * (acc + 1)) ≤ N then satVarsGo N fuel (acc + 1)
    else satVarsGo N fuel acc

theorem satVarsGo_succ (N fuel acc : Nat) :
    satVarsGo N (fuel + 1) acc =
      if (acc + 1) * (2 * (acc + 1)) ≤ N then satVarsGo N fuel (acc + 1)
      else satVarsGo N fuel acc := rfl

/-- Every reachable value of `satVarsGo` still satisfies the bound. -/
theorem satVarsGo_le (N : Nat) :
    ∀ (fuel acc : Nat), acc * (2 * acc) ≤ N →
      satVarsGo N fuel acc * (2 * satVarsGo N fuel acc) ≤ N := by
  intro fuel acc h
  induction fuel generalizing acc with
  | zero => exact h
  | succ fuel ih =>
    rw [satVarsGo_succ]
    split
    · next hle => exact ih (acc + 1) hle
    · next _ => exact ih acc h

/-- The number of variables (and clauses) available at input length `N`:
the largest `n` with `n · (2n) ≤ N` (equivalently `⌊√(N/2)⌋`; counting up
keeps the function kernel-computable). -/
def satVars (N : Nat) : Nat := satVarsGo N N 0

/-- The matrix of `satVars N` variables and clauses fits into `N` bits. -/
theorem satVars_mul_le (N : Nat) : satVars N * (2 * satVars N) ≤ N :=
  satVarsGo_le N N 0 (Nat.zero_le N)

/-- The SAT family under the dense CNF-matrix encoding: the first
`satVars N · (2 · satVars N)` bits of the input encode a CNF formula with
`satVars N` variables and `satVars N` clauses — bit `(i, 2j)` of the matrix
records whether clause `i` contains the positive literal of variable `j`,
bit `(i, 2j+1)` the negative literal; the remaining bits are ignored
(padding). `satFamily N x` decides whether that formula is satisfiable. -/
def satFamily : BoolFunFamily := fun N x =>
  decide (cnfSat (n := satVars N)
    (x := fun w => x ⟨w.val, Nat.lt_of_lt_of_le w.isLt (satVars_mul_le N)⟩))

/-! ### ACC membership -/

/-- A Boolean function family is in **ACC** (the nonuniform class, single
modulus): there exist a depth bound `d`, a size exponent `c` and a modulus
`m` such that for every input length `N ≥ 1`, some circuit over the
AND/OR/MOD_m basis of depth at most `d` and size at most `N ^ c` computes
`f N`. (A fixed finite set of moduli would give the same class, since
MOD_a and MOD_b together compute MOD_{lcm(a,b)} with one extra layer.) -/
def InACC (f : BoolFunFamily) : Prop :=
  ∃ (d c m : Nat), ∀ (N : Nat) [NeZero N],
    ∃ (G : Nat) (C : Circuit (accBasis m) N 1 G),
      C.depth ≤ d ∧ C.size ≤ N ^ c ∧ (fun x => (C.eval x) 0) = f N

/-- The MOD₂ characteristic family: `true` iff the number of `true` input
bits is a multiple of 2 (even parity). A single MOD₂ gate computes it. -/
def mod2Family : BoolFunFamily := fun N x =>
  (Fin.foldl N (fun acc i => acc + (x i).toNat) 0) % 2 == 0

/-! ### A concrete small circuit over the ACC basis -/

/-- A 2-input circuit over the MOD₃ basis: one internal MOD₃ gate reading
the two primary inputs, and an output AND gate reading the MOD₃ wire through
a negation flag. MOD₃(x₀, x₁) = "x₀ + x₁ ≡ 0 (mod 3)" = NOR(x₀, x₁), so the
circuit computes OR of its inputs. -/
def sampleModCircuit : Circuit (accBasis 3) 2 1 1 where
  gates _ :=
    { op := .mod, fanIn := 2, arityOk := trivial,
      inputs := fun j => ⟨j.val, by omega⟩,
      negated := fun _ => false }
  outputs _ :=
    { op := .and, fanIn := 1, arityOk := trivial,
      inputs := fun _ => ⟨2, by omega⟩,
      negated := fun _ => true }
  acyclic := by
    intro i k
    obtain ⟨iv, hiv⟩ := i
    rw [Nat.lt_one_iff] at hiv
    subst hiv
    exact k.isLt

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

/-! ## Slot zone: the conjecture and its negation -/

namespace NpVsAcc

-- @[slot main]
/-- **NP versus ACC** (belief direction): the SAT family (dense CNF-matrix
encoding; SAT is NP-complete under AC⁰ reductions, so this is equivalent to
`NP ⊄ ACC`) is computed by no ACC circuit family — for every depth bound,
every size exponent and every modulus, some input length defeats all
circuits within the bounds. -/
theorem conj : ¬ InACC satFamily := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

-- @[slot main]
/-- The negation of the conjecture: SAT does have ACC circuits — there exist
a depth bound, a size exponent and a modulus such that every input length
has a circuit within the bounds (this would imply `NP ⊆ ACC`). -/
theorem refuted : InACC satFamily := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

end NpVsAcc
