# Independent Retranslation: NP versus ACC

This record derives a formalization draft from the literature without consulting the shipped Lean file, then compares the two component by component. It is the third fidelity record (independent retranslation).

- Source statements: the Wikipedia “ACC0” page () and the account in Arora–Barak, Chapter 14.

## Step 1: Source statement

ACC⁰: a language is in AC⁰[m] if it is computed by a circuit family C₁, C₂, …, where C_n has n inputs, constant depth, polynomial size in n, and uses unbounded-fan-in AND and OR gates, NOT gates, and unbounded-fan-in MOD_m gates (a MOD_m gate outputs 1 when the number of 1s among its inputs is divisible by m). A language is in ACC⁰ if there is an m for which it is in AC⁰[m]. Conjecture (NP vs. ACC): some language in NP is not in ACC⁰. It is known that NEXP ⊄ ACC⁰ (Williams 2011) and NQP ⊄ ACC⁰ (Murray–Williams 2018).

## Step 2: Natural-language refinement (resolving ambiguities)

- **Language:** a family of Boolean functions indexed by input length, f_N : {0,1}ᴺ → {0,1}.
- **Circuit:** a directed acyclic graph with N input wires; each gate has a type (AND/OR/MOD_m) and some input wires. NOT is free (each gate input may be negated at no cost); size is the number of gates; depth is the longest input-to-output path, counted in gates.
- **MOD_m output convention:** output 1 when the number of 1s is 0 modulo m (Wikipedia / Arora–Barak convention). The alternative convention (output 1 when it is nonzero modulo m) defines the same class because NOT is free.
- **Constant depth and polynomial size:** there are d,c independent of N such that for every N there is a circuit of depth ≤ d and size ≤ N^c.
- **Fixed m:** one modulus m is used throughout the entire circuit family. Allowing finitely many moduli is equivalent, since MOD_a ∧ MOD_b = MOD_{lcm(a,b)}.
- **“A language in NP”:** mathlib has no polynomial-time predicate, so the formalization cannot quantify over one directly. Use the standard NP-complete language SAT. SAT is NP-complete under AC⁰ reductions and ACC is closed under AC⁰ reductions, so SAT ∉ ACC iff NP ⊄ ACC.
- **Encoding SAT:** treat the first 2n² bits as the clause-literal matrix of a CNF with n variables and n clauses (bit (i,2j)/(i,2j+1) indicates whether clause i contains the positive/negative literal of variable j); ignore any remaining bits. Choose the largest integer n with 2n² ≤ N. As N → ∞, every formula can be embedded.

## Step 3: Independently drafted types

```
BitString n := Fin n → Bool;  BoolFunFamily := (N : ℕ) → BitString N → Bool
Basis := gate types + arity constraints + evaluation function
Gate := operation + fanIn + input wires (with a negation bit per input)
Circuit B N M G := gates : Fin G → Gate B (N+G), outputs, acyclic (gate i reads only wires < N+i)
wireValue / wireDepth / depth / eval / size := evaluate gate by gate in topological order (structural recursion)
accBasis m := {AND, OR, MOD_m}, an unbounded-fan-in basis
InACC f := ∃ d c m, ∀ N ≥ 1, ∃ C : Circuit (accBasis m) N 1 G,
             depth C ≤ d ∧ size C ≤ N^c ∧ eval C = f N
satFamily N x := (satisfiability of CNF decoded from the first n·2n bits as a matrix), n = ⌊√(N/2)⌋
Conjecture := ¬ InACC satFamily; its negation := InACC satFamily
```

## Step 4: Component-by-component comparison with the shipped version

| Component | Draft | Shipped version | Finding |
|---|---|---|---|
| Function family | (N : ℕ) → (Fin N → Bool) → Bool | `BoolFunFamily` / `BitString`, same form | Match |
| Gate basis | Operation type + arity + evaluation | `CircuitBasis` (`Basis` in Circ was renamed) | Match (rename rationale in deviation 1 of the component ledger) |
| Circuit | Fin G gates + acyclic topological ordering | `Circuit`, same form | Match |
| Evaluation/depth | Evaluate gate by gate in topological order | Structural recursion through `wireValuesUpTo` / `wireDepthsUpTo` | Match (implementation change explained in deviation 2) |
| MOD_m | Output 1 when the number of 1s is 0 modulo m | `ACCOp.eval .mod`: sum % m == 0 | Match |
| Membership in ACC | ∃ d c m, ∀ N ≥ 1, ∃ circuit with depth ≤ d ∧ size ≤ N^c computing f N | `InACC`, same form | Match |
| SAT encoding | Matrix with n rows and 2n columns, n = ⌊√(N/2)⌋; ignore remainder | `satVars` / `satClause` / `cnfSat` / `satFamily`, same form (positions mapped via `finProdFinEquiv`) | Match |
| Conjecture/negation | ¬InACC satFamily / InACC satFamily | `conj` / `refuted`, same form | Match |

There are no disagreements. The two packaging differences (renaming Basis and structurally recursive evaluation) preserve semantics; see deviations 1/2 of `concept-ledger.md`.

## Notes

- “Free NOT” is implemented by a negation bit on each input rather than a NOT gate, matching Circ and the literature convention that negation has no depth or size cost. Both representations give the same circuit class (an AND/OR gate with a negated single input can simulate NOT).
- The circuit family is not built as a function N ↦ Circuit; it is represented implicitly by a per-length existential quantifier (∀ N, ∃ circuit), the standard nonuniform formulation, matching Circ's `InAC0`.
- Expanding the quantifiers of `conj` gives ∀ d c m, ∃ N, ∀ circuits C within the bounds, C does not compute `satFamily N`. This is the conjecture's only adjustment to the conventional form; no constant is hidden.
