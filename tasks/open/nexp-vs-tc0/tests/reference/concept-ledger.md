# Faithfulness Review: NEXP versus TC⁰

This note explains the task statement for readers comparing the mathematical definitions with the Lean source. The current scoring statements are `conj` and `refuted`; proving either earns full credit.

This review compares the literature statement of “NEXP is not contained in TC⁰” and its negation with the Lean statement used by this proof-oriented open-problem task. It records each modeling choice and its rationale.

- **Definition-layer survey:** `proof-circuit.md`.
- **Other sources:** Wikipedia’s “TC0” page (; definitions and known results checked); Chen–Tell, ECCC TR18-199 (abstract); Wikipedia’s “NEXPTIME” page (; succinct completeness); circuit encoding from SamuelSchlesinger/circuit-complexity (Apache-2.0), adapted through the sibling problem np-vs-acc.
- **Released statement:** `environment/app/Task/Basic.lean`; its fixed region matches that of the scoring model `tests/reference/Basic.lean` word for word.

## 1. Literature statement and Lean correspondence

The Wikipedia “TC0” page () defines TC⁰ as the class of languages decided by circuit families of constant depth and polynomial size, using unbounded-fanin AND/OR/NOT gates and MAJORITY gates. Equivalently, one can use threshold gates with integer weights and integer thresholds bounded by a polynomial. TC⁰ contains integer multiplication, integer division, sorting, and the Dyck language with multiple bracket types; AC⁰ ⊊ AC⁰[p] ⊊ TC⁰ ⊆ NC¹. The conjecture is that some language in NEXP is not in TC⁰ (NEXP ⊄ TC⁰; the page says, “It is also an open question whether NEXP ⊆ TC⁰”). It is known that NEXP ⊄ ACC (Williams 2011) and ACC ⊆ TC⁰ (MOD_m is in TC⁰), so the TC⁰ version is strictly stronger and remains open. Chen–Tell (STOC 2019) showed that any mild improvement to known lower bounds or derandomization results would imply NEXP ⊄ TC⁰, identifying it as an explicit next target for algorithmic methods.

| Concept | Literature | Lean identifier in this task | Notes |
|---|---|---|---|
| Language by input length | L ⊆ {0,1}*, represented by its characteristic function at every length. | `BoolFunFamily := (N : ℕ) → BitString N → Bool`; `BitString N := Fin N → Bool` | Standard encoding inherited from Circ through np-vs-acc. |
| Circuit (DAG) | A directed acyclic graph whose gates have types and whose wires connect gates. | `Circuit B N M G`: `gates : Fin G → Gate B (N+G)`, `outputs`, `acyclic` (gate i reads only wires with index < N+i) | Topological order is built into the representation, so acyclicity follows by construction; inherited from Circ. |
| Gate basis | {MAJ} or {THR} with unbounded fan-in; NOT is free. | `CircuitBasis` (operations, arity constraints, and evaluation); `tc0Basis` (operation `TC0Op.thr k`) | See deviation 3. |
| Threshold gate | Outputs 1 iff the number of 1 inputs is at least the threshold. | `TC0Op.eval (.thr k) n inputs := Nat.ble k (Σ toNat)` | Unweighted threshold; see deviation 3 for integer weights. |
| Free negation | NOT gates do not count toward depth or size. | `Gate.negated : Fin fanIn → Bool` (a per-input negation bit) | Same as Circ and standard convention. |
| Depth | Number of gates on the longest input-to-output path. | `Circuit.depth` (input wires have depth 0; a gate has depth 1 plus the maximum depth of its input wires) | See deviation 6. |
| Size | Number of gates. | `Circuit.size := G + M` | Same as Circ. |
| Membership in TC⁰ | There exist a constant depth d and polynomial size bound. | `InTC0 f := ∃ d c, ∀ N ≥ 1, ∃ circuit over tc0Basis, depth ≤ d ∧ size ≤ N^c ∧ computes f N` | See deviations 4, 5, and 6. |
| A language in NEXP | Some L ∈ NEXP with L ∉ TC⁰. | Instantiated by the NEXP-complete language `succinctSatFamily` (dense circuit-description encoding). | See deviation 7, the key decision. |
| Conjecture | NEXP ⊄ TC⁰. | `conj : ¬ InTC0 succinctSatFamily` | Faithfulness argument in deviation 7. |
| Negation | NEXP ⊆ TC⁰. | `refuted : InTC0 succinctSatFamily` | Literal negation for this complete language; `refuted` implies NEXP ⊆ TC⁰. |

## 2. Deviations and rationale

1. **Rename `Basis` to `CircuitBasis`** (following np-vs-acc). mathlib already uses `Basis` for a linear-algebra basis. This is a name change only.

2. **Define evaluation and depth by structural recursion rather than well-founded recursion** (following np-vs-acc). The original Circ uses well-founded recursion on wire indices. This package recurses structurally on the number of processed gates (`wireValuesUpTo`/`wireDepthsUpTo`). The mathematics is the same, aligned by the one-step expansion lemma `wireValue_gate`; the change makes the definitions kernel-computable. Checkpoint c3 and all concrete circuit-value claims can therefore use `decide`.

3. **Use unweighted threshold gates `thr k` (with threshold k as a gate parameter), rather than MAJ gates or weighted threshold gates.** The literature uses equivalent formulations (as the Wikipedia “TC0” page states). MAJ is `thr ⌈n/2⌉`, so majority circuits are a special case of threshold circuits. Conversely, `thr k` can be simulated using MAJ and constants, with constant depth and linear size overhead. Constants can be made from zero-input gates: `thr 0` on empty fan-in is always true and `thr 1` on empty fan-in is always false; negation is free. Integer-weight threshold gates with polynomially bounded weights also give TC⁰. Here `Gate.inputs : Fin fanIn → Fin W` allows the same wire to be connected more than once; multiplicity represents an integer weight, so unweighted thresholds with repeated wires express polynomially bounded weights. Wikipedia likewise notes that polynomial bounds on weights and thresholds can be relaxed without changing the class. These three bases define the same class, and the simplest one is used.

4. **Use the nonuniform version** (as in deviation 4 for np-vs-acc; both versions are open, and the task follows convention). Uniform TC⁰ requires time or space bounds for a Turing machine generating the circuit family. mathlib’s Turing machine model has no step-count measure, so that version cannot be stated here. The main lower-bound targets in Williams and Chen–Tell use nonuniform statements; nonuniform classes are stronger, making separation from them a stronger claim that can rule out NEXP.

5. **Constrain only N ≥ 1** (`∀ N [NeZero N]`, as in Circ’s `InAC0`). Length 0 is unconstrained by convention in the literature.

6. **Allow constant offsets in depth and size** (following np-vs-acc). Input wires have depth 0 and output gates count toward depth; size is G+M. Conventions in the literature may differ by ±1, which does not change class membership.

7. **Instantiate “some language in NEXP” by SUCCINCT-SAT (the key decision).** mathlib has no time-bounded machine model, so the statement cannot quantify over every language in NEXP. Instead it uses the standard NEXP-complete language SUCCINCT-SAT: `conj = ¬ InTC0 succinctSatFamily`.

   **Faithfulness argument.** SUCCINCT-SAT asks whether a CNF formula described by a circuit and having exponentially many clauses is satisfiable. It is NEXP-complete (Papadimitriou–Yannakakis 1986; Papadimitriou textbook, Theorem 20.2; the Wikipedia “NEXPTIME” page explains how succinct representations lift NP-completeness to NEXP-completeness). Its completeness reduction is AC⁰, by local checkability of the Cook–Levin tableau (textbook result). TC⁰ is closed under AC⁰ reductions: composing constant-depth circuits preserves constant depth, and composing polynomial-size circuits preserves polynomial size. Thus SUCCINCT-SAT ∉ TC⁰ iff NEXP ⊄ TC⁰, and SUCCINCT-SAT ∈ TC⁰ implies NEXP ⊆ TC⁰.

   **Why `succinctSatFamily ∈ NEXP`.** On an input of length N, the encoded level n satisfies 2ⁿ ≤ N: for n ≥ 1, the encoding length `(n+1)(6n+3)` is at least 2ⁿ, and the remaining small cases are direct. Guess an assignment of 2ⁿ bits, then check all 2ⁿ clauses and 2ⁿ⁺¹ literal slots. Each check evaluates a description circuit with at most n+1 gates. Total time is 2^O(n)=N^O(1), hence at most 2^poly(N), as required for NEXP (indeed 2^O(n) ≤ 2^O(log N)).

   **Encoding scheme (dense circuit-description encoding, defined here).** A level-n instance is a string of `succLen n = (n+1)(6n+3)` bits describing an AND/OR circuit with free negation and unbounded fan-in. It has 2n+1 primary inputs (n bits for the clause index, n bits for the variable index, and one sign bit), n internal gates, and one output gate. Each gate has a description block: one type bit (0=AND, 1=OR), 3n+1 connection bits, and 3n+1 negation bits. Gate g scans only connection indices < 2n+1+g; out-of-range wires are ignored. Acyclicity is guaranteed by construction, so every bit string decodes to a valid circuit and there are no invalid instances.

   The described CNF has 2ⁿ clauses and 2ⁿ variables. Clause c contains literal (v,s) exactly when the description circuit accepts the packed input (c,v,s), where (v,false)=x_v and (v,true)=¬x_v. For input length N, choose the largest n with `succLen n ≤ N` (`succSatVars` uses a computable counting definition); ignore the remaining bits, the standard dense-encoding convention.

   **Embedding argument.** Any standard SUCCINCT-SAT instance with k inputs and an s-gate description circuit embeds at level n=max(⌈(k−1)/2⌉,s). Unused primary inputs can be left unconnected (the described CNF repeats clauses according to low-order indices, preserving satisfiability); unused internal gates receive all-zero blocks (an empty-fanin AND is true and the gates are unread). The description circuit generated from a Cook–Levin tableau has size linear in the formula-index length (the tableau circuit uses O(1) bitwise comparisons/increments on indices), and G(n)=n leaves sufficient room. The encoding length `(n+1)(6n+3)` is polynomial in the original instance length, and each reduction output bit is a projection or local lookup of the original description (AC⁰, in fact projection-level). Hence this encoding remains NEXP-complete under AC⁰ reductions.

   **Degeneracy check.** The risk that a weakened existential statement becomes trivial, as in the PRG-ROBP task, does not arise. The constraints on a circuit family here—constant depth, polynomial size, and existence at each input length—are the original literature formulation. The concrete SUCCINCT-SAT instance is also the structure used in literature for NEXP lower bounds (Williams 2011 uses succinct complete problems).

8. **Zero-padding convention for small input lengths.** If N < `succLen 0 = 3`, even level 0 does not fit. Then `succSatVars N = 0`, and out-of-range bits are read as false (zero padding). There are only finitely many such lengths, so the asymptotic statement is unaffected. Level 0 has one clause, one variable, and a description circuit with just one primary input (the sign bit); this is degenerate but well-defined.

9. **Use unbounded-fanin AND/OR gates in the description circuit.** Standard definitions often use fan-in 2. The unbounded-fanin version contains the fan-in-2 version (for hardness, each standard instance is still a valid instance), and evaluation remains polynomial in the description length (for membership), so NEXP-completeness is unchanged. The scoring instances in this package have no notion of an “invalid fan-in,” consistent with the dense convention that every bit string is a valid instance.

## 3. Distinction from nearby problems

- **NEXP ⊄ ACC (Williams 2011) / NQP ⊄ ACC (Murray–Williams 2018):** These are proved. Since ACC ⊆ TC⁰, the present conjecture is strictly stronger than Williams’s theorem and directly continues that line. MOD_m gates have constant-depth polynomial-size threshold constructions: `MOD_m(x) = ∨_{k≡0 (m)}(thr k(x) ∧ ¬thr (k+1)(x))`.
- **NP ⊄ TC⁰:** This is also open and weaker, since NP ⊆ NEXP. The present problem is the NEXP version; algorithmic methods currently reach NEXP/NQP scale, which is why Chen–Tell identify it as a next target.
- **TC⁰ versus NC¹ / TC⁰ versus P/poly:** These are open questions on a different line (Chen–Tell’s bootstrapping result also targets TC⁰ ≠ NC¹). Neither NEXP ⊄ TC⁰ nor TC⁰ ≠ NC¹ implies the other; they are distinct.
- **Size/wire lower bounds for depth-2/3 threshold circuits (Kane–Williams, STOC 2016):** These are proved quantitative bounds (n^{3/2} gates / n^{5/2} wires for explicit functions in P), useful as a “still far from the goal” reference. They are not class separations and do not overlap with `conj`.
- **np-vs-acc (sibling task):** NP versus ACC, with different objects (modular gates rather than threshold gates; SAT rather than SUCCINCT-SAT). It shares the Circ circuit-definition layer and scoring template, so it is a related but distinct problem.

## 4. Known frontier

- NEXP ⊄ ACC (Williams 2011, STOC); NQP ⊄ ACC (Murray–Williams 2018, STOC).
- Chen–Tell (STOC 2019; ECCC TR18-199, abstract): any mild improvement to known TC⁰ lower bounds (slightly superlinear wire count) or quantitative derandomization would imply TC⁰ ≠ NC¹ or **NEXP ⊄ TC⁰**. The paper states NEXP ⊄ TC⁰ as an unproved target, indirectly confirming its open status.
- Wikipedia’s “TC0” page (): TC⁰ definition (MAJ or equivalent threshold gates; includes integer multiplication/division, sorting, and Dyck language), AC⁰ ⊊ AC⁰[p] ⊊ TC⁰ ⊆ NC¹, and “It is also an open question whether NEXP ⊆ TC⁰.”
- Kane–Williams (STOC 2016): depth-2/3 threshold-circuit lower bounds of n^{3/2} gates / n^{5/2} wires (bibliographic entry checked in DBLP).
- arXiv search for “NEXP” with “threshold circuits” and “circuit lower bounds,” sorted by submission date: the latest related entries were from 2024-05 (“From Proof Complexity to Circuit Complexity via Interactive Protocols”) and 2023-03 (“On the Consistency of Circuit Lower Bounds for Non-Deterministic Time”); none claimed to resolve NEXP versus TC⁰.
- SUCCINCT-SAT is NEXP-complete: Papadimitriou–Yannakakis 1986 (*Information and Control* 71); Papadimitriou, *Computational Complexity*, Theorem 20.2 (SUCCINCT 3SAT is NEXP-complete); and the succinct section of Wikipedia’s “NEXPTIME” page (), which gives the same account.
- Symmetrically, NEXP ⊆ TC⁰ (the `refuted` direction) would be a collapse-level result (NP ⊆ TC⁰ and the exponential hierarchy contained in nonuniform constant-depth circuits). Either direction would resolve the problem, as required by the “prove or refute” task family.
