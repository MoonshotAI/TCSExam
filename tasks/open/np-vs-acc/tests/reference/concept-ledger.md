# Statement Ledger: NP Not Contained in ACC

This note explains the task statement for readers comparing the mathematical definitions with the Lean source. The current scoring statements are `conj` and `refuted`; proving either earns full credit.

This ledger compares the literature statement of the conjecture NP ⊄ ACC and its negation with the Lean statement in this proof-conjecture task, and records every deviation and its rationale. It is intended for task authors and reviewers as one of the three fidelity records (the component-by-component ledger).

Sources: definition-layer survey `proof-circuit.md`; textbook formulation in chapter 14 of Arora–Barak; the Wikipedia “ACC⁰” page (, used to check the definition and known bounds); and the circuit encoding source SamuelSchlesinger/circuit-complexity (Apache-2.0).

Shipped statement: `environment/app/Task/Basic.lean` (the fixed region of the scoring copy in `tests/reference/Basic.lean` is identical, character for character).

## 1. Published statement and Lean correspondence

The literature statement (consistent between Arora–Barak, chapter 14, and the Wikipedia summary) defines ACC⁰ as the class of languages computed by circuit families of constant depth and polynomial size, using unbounded-fan-in AND/OR/NOT gates and MOD_m gates for some fixed constant m. A MOD_m gate outputs 1 iff the number of 1s among its inputs is divisible by m. Thus ACC⁰ = ∪_m AC⁰[m]. The conjecture is that some language in NP is not in ACC⁰ (NP ⊄ ACC⁰). Known results include NEXP ⊄ ACC⁰ (Williams 2011) and NQP ⊄ ACC⁰ (Murray–Williams 2018); the NP version remains open.

| Concept | Literature | Lean identifier in this task | Notes |
|---|---|---|---|
| Language indexed by input length | L ⊆ {0,1}*, represented by its characteristic function at each length | `BoolFunFamily := (N : ℕ) → BitString N → Bool`, `BitString N := Fin N → Bool` | Standard encoding borrowed from Circ. |
| Circuit (DAG) | Directed acyclic graph with typed gates and wires connecting gates | `Circuit B N M G`: `gates : Fin G → Gate B (N+G)`, `outputs`, and `acyclic` (gate i reads only wires numbered below N+i) | Topological order is built in, so acyclicity follows by construction; borrowed from Circ. |
| Gate basis | Unbounded-fan-in {AND, OR, MOD_m}, with free NOT | `CircuitBasis` (Op, arity constraints, and evaluation); `accBasis m` | See deviations 1 and 3. |
| Free negation | NOT gates are not counted toward depth or size (or wires can be negated) | `Gate.negated : Fin fanIn → Bool` (one input-negation bit per input) | Matches Circ and the literature convention. |
| Depth | Longest path from an input to an output, measured in gates | `Circuit.depth` (input-wire depth 0; a gate has depth 1 plus the maximum depth of its input wires; same for output gates) | See deviation 6. |
| Size | Number of gates | `Circuit.size := G + M` (internal gates plus output gates) | Matches Circ. |
| MOD_m | Outputs 1 iff the number of input 1s is congruent to 0 modulo m | `ACCOp.eval m .mod n inputs := (Σ toNat) % m == 0` | Matches the Wikipedia/Arora–Barak convention; see deviation 2. |
| Membership in ACC | For some constant depth d, polynomial size, and fixed m | `InACC f := ∃ d c m, ∀ N ≥ 1, ∃ circuit over accBasis m, depth ≤ d ∧ size ≤ N^c ∧ computes f N` | See deviations 3, 4, and 5. |
| Language in NP | There is an L ∈ NP with L ∉ ACC | Specialized to the concrete NP-complete language `satFamily` (dense CNF matrix encoding) | See deviation 7 (key design choice). |
| Conjecture | NP ⊄ ACC | `conj : ¬ InACC satFamily` | Fidelity argument is in deviation 7. |
| Negation | NP ⊆ ACC | `refuted : InACC satFamily` | Literal negation; refuted implies NP ⊆ ACC. |

## 2. Deviations and rationale

1. **Rename `Basis` to `CircuitBasis`.** Mathlib already uses `Basis` for a linear-algebra basis. This is a name-only change; the content is unchanged.

2. **Use structural recursion rather than well-founded recursion for evaluation and depth.** Circ's `wireValue`/`wireDepth` use well-founded recursion on wire indices. This task instead uses structural recursion on the number of gates already processed (`wireValuesUpTo`/`wireDepthsUpTo`). The mathematical content is the same (the one-step unfolding lemma `wireValue_gate` aligns with the equations in the original library), while the change makes kernel computation reliable. Checkpoint c3 and all numerical claims about concrete circuits use `decide`; kernel reduction for the well-founded recursion is unreliable.

3. **Use one modulus, ∃m, rather than an arbitrary finite set of moduli.** The literature uses both conventions: a union over single-modulus classes AC⁰[m], or circuits that may mix finitely many MOD gates. The conjunction of MOD_a and MOD_b is MOD_lcm(a,b): (a|s ∧ b|s ⟺ lcm(a,b)|s). A circuit using multiple moduli can therefore be simulated by one using a single modulus, with constant depth and polynomially larger size; the two classes coincide, so `∃ m` loses no generality. The alternative convention in which the modulus can vary with N is not standard in the literature and is not used.

4. **Use the nonuniform version.** Uniform ACC requires a time or space measure for a Turing machine generating the circuit family; mathlib's Turing-machine library has no step-count measure, so that version cannot be expressed here. Also, the conjecture in its nonuniform form is stronger: a lower bound against the nonuniform class is needed to exclude NP. The main literature (including Williams and Arora–Barak) uses the nonuniform formulation. The uniform version is outside this task, consistent with the survey.

5. **Impose the condition N ≥ 1** (`∀ N [NeZero N]`, following Circ's `InAC0`). There is no constraint at input length 0, following the literature convention that membership of the empty string does not affect the class.

6. **Depth and size include fixed additive offsets.** Input wires have depth 0, and output gates count (a single-gate circuit has depth 1); size counts G+M, including output gates. This matches Circ. Some sources differ by ±1, but this does not affect membership in constant-depth, polynomial-size classes.

7. **Reduce “there exists a language in NP” to SAT (key design choice).** Mathlib has no predicate for polynomial-time computation, so the task cannot quantify over all NP languages. It uses the standard NP-complete language SAT: `conj = ¬ InACC satFamily`. Fidelity argument: SAT is NP-complete under AC⁰ reductions (local checkability of the Cook–Levin tableau, as in standard textbooks), and ACC is closed under AC⁰ reductions (constant-depth circuits compose to constant depth and polynomial size remains polynomial). Hence SAT ∉ ACC iff NP ⊄ ACC, and SAT ∈ ACC implies NP ⊆ ACC. The encoding is a dense CNF matrix: n = ⌊√(N/2)⌋ variables and n clauses; positions (i,2j)/(i,2j+1) record whether clause i contains the positive/negative literal for variable j, and unused positions are ignored. Any 3-SAT instance with v variables and k clauses embeds by taking n = max(v,k) and padding with tautological clauses; the encoding length 2n² is polynomially bounded, and each output bit of the reduction can be computed in AC⁰ (in fact it is a projection). Thus the language remains NP-complete under this encoding and AC⁰ reductions. Ignoring unused positions is standard for dense encodings. **Known pitfall checked:** the risk that an existential weakening might make the statement trivial by counting or probabilistic methods (the prg-robp lesson) does not arise here. The constraint on the circuit family (constant depth, polynomial size, and existence at each length) is the original literature formulation, with no weakening. Specializing to SAT uses exactly the completeness structure employed in literature proving the NEXP/NQP versions.

8. **Define MOD_m to output 1 when the count is congruent to 0** (matching Wikipedia and Arora–Barak). Another common convention outputs 1 when the count is not congruent to 0, making MOD₂ parity/XOR. Since NOT is free (an AND/OR gate with one negated input acts as a NOT gate), the two conventions simulate each other with at most one extra gate layer and define the same circuit classes. The convention does not affect the truth of `conj`/`refuted`.

## 3. Distinguishing related problems

- **NEXP ⊄ ACC (Williams 2011) and NQP ⊄ ACC (Murray–Williams 2018):** these are proved and are “upstream” results; the current conjecture is the open version that brings the lower bound down to NP, not the same statement.
- **AC⁰ lower bounds (parity ∉ AC⁰, Razborov–Smolensky):** proved; they provide the background for checkpoint c2 (MOD₂ is easy in ACC[2] but not in AC⁰), and do not overlap with `conj`.
- **ACC⁰ versus TC⁰ (whether majority is in ACC⁰):** also open, but concerns majority/threshold gates rather than modular gates and is outside this task.
- **cslib and other Lean circuit libraries:** the circuits in kw-games-lean are inductive trees with no sharing, so their size cannot express DAG circuit size; `Std.Sat.AIG` is an execution structure and the survey explicitly chose not to reuse it. This task uses Circ's DAG encoding, the only existing formalization here suitable for discussing size.

## 4. Current bounds and source checks

Checked for task authoring.

- NEXP ⊄ ACC (Williams 2011, STOC; foundational “algorithmic method”) and NQP ⊄ ACC (Murray–Williams 2018, STOC).
- NP ⊄ ACC remains open. The Wikipedia ACC⁰ page lists the Williams and Murray–Williams results as the latest bounds and no resolution of the NP version; an arXiv search found no claimed resolution.
- Conversely, NP ⊆ ACC (the `refuted` direction) would also be a collapse-level result. Either direction would resolve the problem, matching the task family's requirement that proving or refuting counts as a solution.
