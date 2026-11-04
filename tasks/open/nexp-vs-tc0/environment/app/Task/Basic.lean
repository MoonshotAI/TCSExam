/-
Statement layer for "NEXP versus TC⁰": the conjecture that some language in
nondeterministic exponential time cannot be computed by any TC⁰ circuit
family — that is, by no family of constant-depth, polynomial-size circuits
over unbounded fan-in threshold gates (a `thr k` gate outputs 1 iff the
number of 1s among its inputs is at least `k`; majority is `thr ⌈n/2⌉`).
Williams 2011 proved `NEXP ⊄ ACC`; since `MOD_m` gates are computable in
TC⁰, `ACC ⊆ TC⁰` and the TC⁰ statement is the stronger one. Chen–Tell
(STOC 2019, "Bootstrapping Results for Threshold Circuits 'Just Beyond'
Known Lower Bounds") made `NEXP ⊄ TC⁰` the explicit next goal of the
algorithmic method: even mild improvements of the best-known TC⁰ lower
bounds or of quantified-derandomization algorithms would already imply it.
The statement remains open, in the uniform and the nonuniform reading alike;
this task takes the customary nonuniform reading.

This file is the task's definition zone plus slot zone:
- The definition zone defines Boolean circuits over an arbitrary gate basis
  (DAG by topological order, acyclicity built in), evaluation and depth by
  structural recursion (so concrete circuits compute by kernel reduction),
  the AND/OR basis, the TC⁰ (threshold) basis, the dense
  description-circuit encoding of SUCCINCT-SAT as a Boolean function family
  `succinctSatFamily`, TC⁰ membership (`InTC0`), the AND and OR
  characteristic families, and a concrete two-input XOR circuit over the
  threshold basis. All API lemmas in this zone are fully proved.
- The slot zone states the conjecture (`conj`: `succinctSatFamily` has no
  TC⁰ circuit family) and its negation (`refuted`). Both proof bodies are
  left blank.

Fidelity notes (see `tests/reference/concept-ledger.md` of the packaged task):
1. "Some language in NEXP" is pinned to the standard NEXP-complete language
   SUCCINCT-SAT: an instance is a circuit describing an exponentially large
   CNF formula (clause `c` contains literal `(v, s)` iff the circuit accepts
   the packed input `(c, v, s)`), and the question is whether the described
   formula is satisfiable. SUCCINCT-SAT is NEXP-complete (Papadimitriou–
   Yannakakis 1986, polynomial-time reductions; the strengthening to AC⁰
   reductions is standard folklore) and TC⁰ is closed under AC⁰
   reductions, so `SUCCINCT-SAT ∉ TC⁰ ⟺ NEXP ⊄ TC⁰`; mathlib has no
   time-bounded machine model to quantify over "all NEXP languages".
2. The TC⁰ basis is instantiated with threshold gates `thr k` (unbounded
   fan-in, the threshold `k` a parameter of the gate) rather than majority
   gates only: `MAJ = thr ⌈n/2⌉`, and conversely `thr k` is computed by a
   majority gate padded with constants (available as 0-fan-in gates), so
   both presentations give the same class. AND is `thr n`, OR is `thr 1`.
3. The circuit layer is adapted from SamuelSchlesinger/circuit-complexity
   (Apache-2.0, see the copyright notice below), as packaged by the sister
   task np-vs-acc: `Basis` renamed to `CircuitBasis` (mathlib already
   declares `Basis`), and the evaluator/depth functions are re-implemented
   by structural recursion on the number of processed gates (the original
   uses well-founded recursion on the wire index) so that `decide` works on
   concrete circuits.

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

/-! ### The AND/OR basis -/

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

/-! ### The TC⁰ (threshold) basis -/

/-- Operations of a threshold basis: `thr k` outputs 1 iff the number of 1s
among its inputs is at least `k`. Majority on `n` inputs is `thr ⌈n/2⌉`,
AND is `thr n`, OR is `thr 1`, and the constants are the 0-input gates
`thr 0` (true) and `thr 1` (false). -/
inductive TC0Op where
  | thr (k : Nat)
  deriving Repr, DecidableEq

/-- Evaluate a threshold operation on `n` input bits: count the 1s and
compare against the threshold. -/
def TC0Op.eval : (op : TC0Op) → (n : Nat) → BitString n → Bool
  | .thr k, n, inputs => Nat.ble k (Fin.foldl n (fun acc i => acc + (inputs i).toNat) 0)

/-- The TC⁰ basis: unbounded fan-in threshold gates, negation free
(per-input flags). Threshold gates with polynomially bounded integer weights
give the same class (weights are simulated by wiring the same wire several
times; a threshold `thr k` is simulated by a majority gate padded with
constants, and constants are available as 0-input gates), so this
presentation coincides with the usual majority-gate definition of TC⁰. -/
def tc0Basis : CircuitBasis where
  Op := TC0Op
  arity _ := .unbounded
  eval op n _ inputs := op.eval n inputs

/-! ### SUCCINCT-SAT as a Boolean function family (dense description-circuit encoding) -/

/-- Wire count of a level-`n` description circuit: `2n+1` primary inputs
plus `n` internal gates. -/
def descWires (n : Nat) : Nat := 2 * n + 1 + n

/-- Per-gate description-block size at level `n`: one op bit, `descWires n`
wiring bits and `descWires n` negation bits. -/
def succBlock (n : Nat) : Nat := 1 + 2 * descWires n

theorem succBlock_eq (n : Nat) : succBlock n = 1 + 2 * descWires n := rfl

/-- Bit length of a level-`n` SUCCINCT-SAT instance: `n` internal gates plus
one output gate, one block each. -/
def succLen (n : Nat) : Nat := (n + 1) * succBlock n

/-- The wires among `0, …, lim-1` whose wiring bit is set in the gate block
at offset `off` of the instance `x`. Structural recursion on `lim`, so the
kernel evaluates it on concrete instances. Wiring bits beyond `lim` are
ignored (padding convention): internal gate `g` only ever scans wires below
`2n+1+g`, so the described circuit is acyclic by construction. -/
def markedWires {M : Nat} (x : BitString M) (off : Nat) : (lim : Nat) → List Nat
  | 0 => []
  | w + 1 =>
    markedWires x off w ++
      (if h : off + 1 + w < M then
         if x ⟨off + 1 + w, h⟩ then [w] else []
       else [])

theorem markedWires_succ {M : Nat} (x : BitString M) (off l : Nat) :
    markedWires x off (l + 1) =
      markedWires x off l ++
        (if h : off + 1 + l < M then
           if x ⟨off + 1 + l, h⟩ then [l] else []
         else []) := rfl

/-- Every marked wire lies below the scan bound. -/
theorem mem_markedWires_lt {M : Nat} (x : BitString M) (off : Nat) :
    ∀ {lim : Nat} {w : Nat}, w ∈ markedWires x off lim → w < lim := by
  intro lim
  induction lim with
  | zero =>
    intro w h
    simp [markedWires] at h
  | succ l ih =>
    intro w h
    rw [markedWires_succ] at h
    rcases List.mem_append.mp h with h | h
    · exact Nat.lt_succ_of_lt (ih h)
    · by_cases hm : off + 1 + l < M
      · rw [dif_pos hm] at h
        by_cases hb : x ⟨off + 1 + l, hm⟩ = true
        · rw [if_pos hb] at h
          rcases List.mem_singleton.mp h with rfl
          exact Nat.lt_succ_self _
        · rw [if_neg hb] at h
          simp at h
      · rw [dif_neg hm] at h
        simp at h

/-- The gate described by the block at offset `off` of the instance `x`,
reading only wires below `lim` (internal gate `g` uses `lim = 2n+1+g`, so
the described circuit is acyclic by construction; the output gate uses
`lim = descWires n`). Op bit: `false` = AND, `true` = OR; then `descWires n`
wiring bits and `descWires n` negation bits. -/
def descGate {n : Nat} (x : BitString (succLen n)) (off lim : Nat)
    (hoff : off + succBlock n ≤ succLen n) (hlim : lim ≤ descWires n) :
    Gate aonBasis (descWires n) where
  op := if x ⟨off, by have hB := succBlock_eq n; omega⟩ then .or else .and
  fanIn := (markedWires x off lim).length
  arityOk := trivial
  inputs := fun i =>
    ⟨(markedWires x off lim)[i.val]'i.isLt,
      Nat.lt_of_lt_of_le (mem_markedWires_lt x off (List.getElem_mem i.isLt)) hlim⟩
  negated := fun i =>
    x ⟨off + 1 + descWires n + (markedWires x off lim)[i.val]'i.isLt, by
      have hw := mem_markedWires_lt x off (List.getElem_mem i.isLt)
      have hB := succBlock_eq n
      omega⟩

/-- The description circuit decoded from a level-`n` instance `x`: `n`
internal gates over the AND/OR basis with `2n+1` primary inputs and one
output gate; internal gate `g` reads block `g`, the output gate reads block
`n`. -/
def descCircuit {n : Nat} [NeZero (2 * n + 1)] (x : BitString (succLen n)) :
    Circuit aonBasis (2 * n + 1) 1 n where
  gates := fun g => descGate x (g.val * succBlock n) (2 * n + 1 + g.val)
    (by
      have hg := g.isLt
      have e1 : g.val * succBlock n + succBlock n = (g.val + 1) * succBlock n :=
        (Nat.succ_mul _ _).symm
      have e2 : (g.val + 1) * succBlock n ≤ n * succBlock n :=
        Nat.mul_le_mul_right _ (Nat.succ_le_of_lt hg)
      have e3 : n * succBlock n ≤ (n + 1) * succBlock n :=
        Nat.mul_le_mul_right _ (Nat.le_succ n)
      exact e1.le.trans (e2.trans e3))
    (by
      have hg := g.isLt
      have hW : descWires n = 2 * n + 1 + n := rfl
      omega)
  outputs := fun _ => descGate x (n * succBlock n) (descWires n)
    (by
      have e : n * succBlock n + succBlock n = succLen n := (Nat.succ_mul _ _).symm
      exact e.le)
    (Nat.le_refl _)
  acyclic := by
    intro g k
    have h := mem_markedWires_lt x (g.val * succBlock n)
      (lim := 2 * n + 1 + g.val)
      (List.getElem_mem (l := markedWires x (g.val * succBlock n) (2 * n + 1 + g.val))
        (n := k.val) k.isLt)
    exact h

/-- The input fed to the description circuit for clause `c` and literal slot
`(v, s)`: bits `0, …, n-1` carry the clause index, bits `n, …, 2n-1` carry
the variable index, bit `2n` carries the sign (`true` = negative literal). -/
def clauseInput (n : Nat) (c v : Fin (2 ^ n)) (s : Bool) : BitString (2 * n + 1) :=
  fun w =>
    if w.val < n then c.val.testBit w.val
    else if w.val < 2 * n then v.val.testBit (w.val - n)
    else s

/-- Clause `c` of the CNF described by `C` is satisfied by assignment `σ`:
some literal slot `(v, s)` is present in clause `c` — the description
circuit accepts the packed input `(c, v, s)` — and true under `σ`. -/
def succClauseSat {n : Nat} [NeZero (2 * n + 1)] (C : Circuit aonBasis (2 * n + 1) 1 n)
    (σ : Fin (2 ^ n) → Bool) (c : Fin (2 ^ n)) : Prop :=
  ∃ (v : Fin (2 ^ n)) (s : Bool),
    (C.eval (clauseInput n c v s)) 0 = true ∧ (if s then !(σ v) else σ v) = true

instance {n : Nat} [NeZero (2 * n + 1)] (C : Circuit aonBasis (2 * n + 1) 1 n)
    (σ : Fin (2 ^ n) → Bool) (c : Fin (2 ^ n)) : Decidable (succClauseSat C σ c) := by
  unfold succClauseSat; infer_instance

/-- The CNF described by `C` is satisfiable: some assignment satisfies every
clause. -/
def succCnfSat {n : Nat} [NeZero (2 * n + 1)] (C : Circuit aonBasis (2 * n + 1) 1 n) :
    Prop :=
  ∃ σ : Fin (2 ^ n) → Bool, ∀ c : Fin (2 ^ n), succClauseSat C σ c

instance {n : Nat} [NeZero (2 * n + 1)] (C : Circuit aonBasis (2 * n + 1) 1 n) :
    Decidable (succCnfSat C) := by
  unfold succCnfSat; infer_instance

/-- Auxiliary for `succSatVars`: starting from `acc`, keep incrementing (at
most `fuel` times) while the next level's encoding still fits into `N` bits.
Structural recursion on `fuel`, so the kernel evaluates it on concrete
lengths. -/
def succSatVarsGo (N : Nat) : Nat → Nat → Nat
  | 0, acc => acc
  | fuel + 1, acc =>
    if succLen (acc + 1) ≤ N then succSatVarsGo N fuel (acc + 1)
    else succSatVarsGo N fuel acc

theorem succSatVarsGo_succ (N fuel acc : Nat) :
    succSatVarsGo N (fuel + 1) acc =
      if succLen (acc + 1) ≤ N then succSatVarsGo N fuel (acc + 1)
      else succSatVarsGo N fuel acc := rfl

/-- Every reachable value of `succSatVarsGo` still satisfies the invariant:
its encoding fits into `N` bits, or it is level 0 (which always decodes,
with reads beyond `N` handled by the zero-padding convention). -/
theorem succSatVarsGo_inv (N : Nat) :
    ∀ (fuel acc : Nat), succLen acc ≤ N ∨ acc = 0 →
      succLen (succSatVarsGo N fuel acc) ≤ N ∨ succSatVarsGo N fuel acc = 0 := by
  intro fuel acc h
  induction fuel generalizing acc with
  | zero => exact h
  | succ fuel ih =>
    rw [succSatVarsGo_succ]
    split
    · next hle => exact ih (acc + 1) (Or.inl hle)
    · next _ => exact ih acc h

/-- The level available at input length `N`: the largest `n` with
`succLen n ≤ N` (counting up keeps the function kernel-computable). -/
def succSatVars (N : Nat) : Nat := succSatVarsGo N N 0

/-- The level-`succSatVars N` encoding fits into `N` bits, or the level is
0. -/
theorem succSatVars_spec (N : Nat) :
    succLen (succSatVars N) ≤ N ∨ succSatVars N = 0 :=
  succSatVarsGo_inv N N 0 (Or.inr rfl)

/-- The SUCCINCT-SAT family under the dense description-circuit encoding:
at input length `N`, with `n = succSatVars N`, the first `succLen n` bits of
the input encode a level-`n` description circuit (reads beyond `N` are
`false`, a zero-padding convention relevant only for `N < succLen 0`).
`succinctSatFamily N x` decides whether the CNF described by that circuit —
`2^n` clauses over `2^n` variables, clause `c` containing literal `(v, s)`
iff the circuit accepts the packed input `(c, v, s)` — is satisfiable. -/
def succinctSatFamily : BoolFunFamily := fun N x =>
  haveI : NeZero (2 * succSatVars N + 1) := ⟨Nat.succ_ne_zero _⟩
  decide (succCnfSat (descCircuit (n := succSatVars N)
    (fun w => if h : w.val < N then x ⟨w.val, h⟩ else false)))

/-! ### TC⁰ membership -/

/-- A Boolean function family is in **TC⁰** (the nonuniform class): there
exist a depth bound `d` and a size exponent `c` such that for every input
length `N ≥ 1`, some circuit over the threshold basis of depth at most `d`
and size at most `N ^ c` computes `f N`. -/
def InTC0 (f : BoolFunFamily) : Prop :=
  ∃ (d c : Nat), ∀ (N : Nat) [NeZero N],
    ∃ (G : Nat) (C : Circuit tc0Basis N 1 G),
      C.depth ≤ d ∧ C.size ≤ N ^ c ∧ (fun x => (C.eval x) 0) = f N

/-- The AND-of-all-inputs family: `true` iff every input bit is `true`.
Computed in TC⁰ by a single `thr N` gate. -/
def andFamily : BoolFunFamily := fun N x =>
  Fin.foldl N (fun acc i => acc && x i) true

/-- The OR-of-all-inputs family: `true` iff some input bit is `true`.
Computed in TC⁰ by a single `thr 1` gate. -/
def orFamily : BoolFunFamily := fun N x =>
  Fin.foldl N (fun acc i => acc || x i) false

/-! ### A concrete small circuit over the TC⁰ basis -/

/-- A 2-input circuit over the threshold basis: one internal `thr 1` gate
computing OR of the primary inputs, one internal `thr 2` gate computing
AND, and an output `thr 2` gate reading the OR wire and the negated AND
wire — so the circuit computes `OR(x₀, x₁) ∧ ¬AND(x₀, x₁) = x₀ ⊕ x₁`. -/
def sampleXorCircuit : Circuit tc0Basis 2 1 2 where
  gates := fun i =>
    { op := if i.val = 0 then .thr 1 else .thr 2,
      fanIn := 2, arityOk := trivial,
      inputs := fun j => ⟨j.val, by omega⟩,
      negated := fun _ => false }
  outputs _ :=
    { op := .thr 2, fanIn := 2, arityOk := trivial,
      inputs := fun j => ⟨2 + j.val, by omega⟩,
      negated := fun j => j.val = 1 }
  acyclic := by
    intro i k
    exact Nat.lt_of_lt_of_le k.isLt (Nat.le_add_right 2 i.val)

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

/-! ## Slot zone: the conjecture and its negation -/

namespace NexpVsTc0

-- @[slot main]
/-- **NEXP versus TC⁰** (belief direction): the SUCCINCT-SAT family (dense
description-circuit encoding; SUCCINCT-SAT is NEXP-complete under AC⁰
reductions, so this is equivalent to `NEXP ⊄ TC⁰`) is computed by no TC⁰
circuit family — for every depth bound and every size exponent, some input
length defeats all threshold circuits within the bounds. -/
theorem conj : ¬ InTC0 succinctSatFamily := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

-- @[slot main]
/-- The negation of the conjecture: SUCCINCT-SAT does have TC⁰ circuits —
there exist a depth bound and a size exponent such that every input length
has a threshold circuit within the bounds (this would imply
`NEXP ⊆ TC⁰`). -/
theorem refuted : InTC0 succinctSatFamily := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

end NexpVsTc0
