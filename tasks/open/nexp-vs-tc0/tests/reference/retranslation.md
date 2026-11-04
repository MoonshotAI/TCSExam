# Independent Retranslation: NEXP versus TC⁰

This record derives a formalization draft from the literature without consulting the shipped Lean file, then compares the two component by component. It is the third fidelity record (independent retranslation).

- Source statements: the Wikipedia “TC0” page () and the Chen–Tell TR18-199 abstract ().
- Method: first refine the source in natural language, draft the types, then compare with the shipped version.

## Step 1: Source statement

TC⁰: a language belongs to TC⁰ if it is decided by a circuit family C₁, C₂, …, where C_n has n inputs, constant depth, polynomial size in n, and uses unbounded-fan-in AND, OR, NOT, and MAJ gates. Equivalently, threshold gates with integer weights and integer thresholds bounded by a polynomial can be used (the Wikipedia “TC0” page gives both definitions and notes that the polynomial bounds on weights and thresholds can be relaxed without changing the class).

Conjecture (NEXP versus TC⁰): some language in NEXP is not in TC⁰. The Wikipedia page states, “It is also an open question whether NEXP ⊆ TC⁰.” It is known that NEXP ⊄ ACC (Williams 2011) and ACC ⊆ TC⁰. Chen–Tell (STOC 2019) prove that even a mild improvement to a known TC⁰ lower bound or to a quantified derandomization algorithm would imply NEXP ⊄ TC⁰.

## Step 2: Natural-language refinement (resolving ambiguities)

- **Language:** a family of Boolean functions indexed by input length, f_N : {0,1}ᴺ → {0,1}.
- **Circuit:** a directed acyclic graph with N input wires; each gate has a type and some input wires. NOT is free (each gate input may be negated at no cost); size is the number of gates; depth is the longest input-to-output path, counted in gates.
- **Threshold gate:** `thr k` outputs 1 iff at least k inputs are 1. MAJ_n = thr ⌈n/2⌉; AND_n = thr n; OR_n = thr 1; constants are thr 0 (true) and thr 1 (false) on zero inputs. A threshold gate with integer weights is represented by repeating each wire according to its weight.
- **Constant depth and polynomial size:** there are d,c independent of N such that for every N there is a circuit of depth ≤ d and size ≤ N^c.
- **“A language in NEXP”:** mathlib has no time-bounded machine model, so the formalization cannot quantify over one directly. Use the standard NEXP-complete language SUCCINCT-SAT: an instance is a circuit C describing a CNF with 2^n variables and 2^n clauses (clause c contains literal (v,s) iff C(c,v,s) = 1); ask whether the CNF is satisfiable. SUCCINCT-SAT is NEXP-complete under AC⁰ reductions (Cook–Levin with locally checkable tableau plus Papadimitriou–Yannakakis 1986), and TC⁰ is closed under AC⁰ reductions. Thus SUCCINCT-SAT ∉ TC⁰ iff NEXP ⊄ TC⁰.
- **Encoding SUCCINCT-SAT:** encode the describing circuit as bits. At level n, the circuit has 2n+1 inputs (n clause bits + n variable bits + one sign bit), n internal gates, and one output gate. Each gate has a description block: one type bit (AND/OR), then one connection bit and one negation bit for every candidate wire. Gate g reads only wires numbered < 2n+1+g (out-of-range bits are ignored). Choose the largest n such that (n+1)(6n+3) ≤ N; ignore the remaining input bits.

## Step 3: Independently drafted types

```
BitString n := Fin n → Bool;  BoolFunFamily := (N : ℕ) → BitString N → Bool
Basis := gate types + arity constraints + evaluation function
Gate := operation + fanIn + input wires (with a negation bit per input)
Circuit B N M G := gates : Fin G → Gate B (N+G), outputs, acyclic (gate i reads only wires < N+i)
wireValue / wireDepth / depth / eval / size := evaluate gate by gate in topological order (structural recursion)
tc0Basis := {thr k | k : ℕ}, an unbounded-fan-in basis; eval = (number of 1s ≥ k)
InTC0 f := ∃ d c, ∀ N ≥ 1, ∃ C : Circuit tc0Basis N 1 G,
             depth C ≤ d ∧ size C ≤ N^c ∧ eval C = f N
succinctSatFamily N x := (satisfiability of the CNF described by the circuit decoded from the first succLen n bits),
  where n is the largest value with (n+1)(6n+3) ≤ N
Conjecture := ¬ InTC0 succinctSatFamily; its negation := InTC0 succinctSatFamily
```

## Step 4: Component-by-component comparison with the shipped version

| Component | Draft | Shipped version | Finding |
|---|---|---|---|
| Function family | (N : ℕ) → (Fin N → Bool) → Bool | `BoolFunFamily` / `BitString`, same form | Match |
| Gate basis | Operation type + arity + evaluation | `CircuitBasis` (`Basis` in Circ was renamed) | Match (rename rationale in deviation 1 of the component ledger) |
| Circuit | Fin G gates + acyclic topological ordering | `Circuit`, same form | Match |
| Evaluation/depth | Evaluate gate by gate in topological order | Structural recursion through `wireValuesUpTo` / `wireDepthsUpTo` | Match (implementation change explained in deviation 2) |
| Threshold gate | Output 1 when number of 1s ≥ k | `TC0Op.eval (.thr k)`: `Nat.ble k` applied to the sum of `toNat` values | Match |
| Membership in TC⁰ | ∃ d c, ∀ N ≥ 1, ∃ circuit with depth ≤ d ∧ size ≤ N^c computing f N | `InTC0`, same form | Match |
| SUCCINCT-SAT encoding | Level n: 2n+1 inputs, n internal gates; block = type bit + connection bits + negation bits; gate g reads wires < 2n+1+g; maximal n with (n+1)(6n+3) ≤ N | `descWires` / `succBlock` / `succLen` / `markedWires` / `descGate` / `descCircuit` / `clauseInput` / `succClauseSat` / `succCnfSat` / `succSatVars` / `succinctSatFamily`, same shape and parameters | Match |
| Conjecture/negation | ¬InTC0 succinctSatFamily / InTC0 succinctSatFamily | `conj` / `refuted`, same form | Match |

There are no disagreements. The two packaging differences (renaming Basis and evaluating by structural recursion) preserve semantics; see deviations 1/2 in `concept-ledger.md`. The concrete encoding (block layout and level function) is a convention that this draft and the shipped version independently chose and then confirmed to match; it is recorded as deviation 7 in `concept-ledger.md`.

## Notes

- “Free NOT” is implemented using a negation bit on each input rather than explicit NOT gates, matching Circ and a literature convention. The two readings give the same circuit class (a threshold gate can simulate a NOT gate using its single-input negation bit).
- The circuit family is not built as a function N ↦ Circuit; it is represented implicitly by a per-length existential quantifier (∀ N, ∃ circuit), the standard formulation without a uniformity requirement, matching Circ's `InAC0`.
- Expanding the nested quantifiers of `conj` gives ∀ d c, ∃ N, ∀ circuits C within the bounds, C does not compute succinctSatFamily N. This is the only quantifier rearrangement in the conjecture; no hidden constant is involved.
- Comparison with np-vs-acc: the two tasks share the circuit layer. The ACC basis (with an existential modulus m parameter) is replaced with the TC⁰ basis (threshold parameter k on each gate and no basis parameter), so `InTC0` has one fewer existential quantifier than `InACC`. The dense-matrix encoding of SAT is replaced with the dense circuit-description encoding of SUCCINCT-SAT; the latter “circuitizes” the former, with a circuit evaluating each clause (matrix row) at its index.
