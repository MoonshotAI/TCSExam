# Faithfulness Review: The Log-Rank Conjecture and Its Definition Layer

This note explains the task statement for readers comparing the mathematical definitions with the Lean source. The current scoring statements are `conj` and `refuted`; proving either earns full credit.

This document aligns the literature statement, textbook definitions, and Lean identifiers used by this task, and explains the design choices.

- **Sources:** Lovász–Saks, FOCS 1988 (doi:10.1109/SFCS.1988.21924); journal version, JCSS 47(2), 1993 (doi:10.1016/0022-0000(93)90035-N), for the conjecture; Kushilevitz–Nisan, Communication Complexity (Cambridge, 1997), §1, for the protocol model and textbook definition of D; frontier data follows item 1 in communication-information-complexity.md (upper bound O(√rank), Sudakov–Tomon 2024; lower bound Ω((log rank)²), Pabbaraju 2026-08, arXiv:2608.02533).
- **Released statement:** environment/app/Task/Basic.lean (namespace LogRank).

## 1. Components of the conjecture statement

| Component | Literature | Released Lean statement (LogRankConjecture) |
|---|---|---|
| Quantifiers | “There exists a constant c, for every Boolean function f.” | ∃ c : ℝ, 0<c ∧ ∀ finite X,Y and f : X→Y→Bool, … . X,Y range over all finite types; every finite type is isomorphic to Fin n, so this loses no generality. |
| Left side D(f) | Deterministic communication complexity, the minimum protocol-tree depth. | (D f : ℝ); D is the least reachable depth (sInf), and nonemptiness follows from exists_computes in the fixed region; ℕ is coerced to ℝ. |
| Right side | (log rank)^{O(1)}, understood asymptotically by the community. | (1 + Real.logb 2 rank)^c. See deviation 1: the literal pure-power version is false already at rank 2, so the small-rank degeneracy must be absorbed. |
| Nondegeneracy | Usually implicit; log rank=0 is degenerate. | Explicit hypothesis 2 ≤ (commMatrix f).rank. See deviation 2. |
| Field for rank | Real field in the original Lovász–Saks formulation. | Matrix.rank over ℝ, with commMatrix f : Matrix X Y ℝ. |
| Logarithm base | Base-independent up to a constant factor, absorbed into the exponent. | Base 2 (Real.logb 2), matching the unit of communication bits and the most common convention. |

## 2. Definition layer: textbook and task correspondence

| Concept | Textbook (Kushilevitz–Nisan §1) | Task identifier | Notes |
|---|---|---|---|
| Communication matrix | M_f[x,y]=f(x,y), a 0/1 matrix. | commMatrix f : Matrix X Y ℝ (if f x y then 1 else 0). | Defined directly over ℝ, avoiding an extra coercion. |
| Protocol | Binary tree; each internal node is owned by Alice or Bob and asks for one bit of information from that party. Leaves carry outputs. | Protocol X Y (leaf / alice (g : X→Bool) / bob (g : Y→Bool)). | A textbook node queries one input bit; this model permits any Boolean function of the party’s input, still one bit. The depth and semantics are equivalent. |
| Depth | Worst-case number of communicated bits, equal to tree depth. | Protocol.depth. | |
| Output | Label of the leaf reached along the input path. | Protocol.run. | |
| Computes f | Output equals f on every input. | Protocol.Computes. | |
| D(f) | Minimum depth of a protocol computing f. | D f := sInf {d | ∃ p, p.Computes f ∧ p.depth ≤ d}. | Nonempty by exists_computes: enumerate X with a trivial protocol of depth at most card X+1; hence sInf is attained (exists_protocol_D). |
| Matrix rank | Rank over ℝ. | Matrix.rank (mathlib). | Existing API. |

The fixed region also provides proved APIs for commMatrix_apply, if_bit_eq_self, the pinpoint family (existence and depth bounds), D_le, and exists_protocol_D. They have no sorry or extra axioms; compilation was.

## 3. Deviations and design decisions

1. **Replace the pure power with 1+log₂(rank), the key statement-shape decision.** The textbook wording is D ≤ (log rank)^c. Taken literally, it is false: for EQ on one bit the communication matrix is I₂, rank=2, log₂ rank=1, and D=2 (Alice’s bit and Bob’s answer each need one transmission; the protocol tree has two 1-leaves and at least one 0-leaf, so 2^d≥3). Thus 1^c=1<2 for every c. For rank 1, u∧v with nonconstant u,v also gives log₂(rank)=0 and D=2. The community uses big-O, where constant factors are immaterial. Lean needs a literally true proposition, so the task uses 1+log₂(rank). It is asymptotically equivalent to the original form: for any c′>c and sufficiently large rank, (1+L)^c ≤ L^c′, while L^c ≤ (1+L)^c always. Thus the two conjectures imply each other with an arbitrarily small exponent change. Numerical checks are in small-examples.md S6.

2. **Make 2≤rank explicit.** As above, when rank≤1 the conjecture’s logarithmic term is degenerate and the literature convention excludes it. The 1+log₂ form handles rank 2, but for rank 1, u∧v still requires D≤1^c=1, which is false because D=2. The hypothesis cannot be omitted.

3. **Use a protocol tree that branches on an arbitrary Boolean function of one party’s input.** Another formalization could send alternating individual bits and track message history. The tree model is textbook-standard and shortest to define (an inductive type plus three recursive functions); it directly matches the definition of D as minimum depth. See Kushilevitz–Nisan §1.

4. **Define D using sInf instead of choosing a minimum protocol.** This avoids a choice operator. Nonemptiness follows from the trivial protocol proved in the fixed region: pinpoint successively excludes elements of X and has depth at most card X+1. Nat.sInf_mem then gives attainability. pinpoint also proves that every function on a finite type is computable by a protocol, preventing the definition from becoming vacuous.

5. **For the ip2 checkpoint, use the 0/1 matrix (rank 3), not the ±1 Hadamard matrix (full rank 4).** The conjecture concerns the rank of the 0/1 communication matrix. The 0/1 IP₂ matrix has an all-zero row and rank 3=2²−1 (script S2 checks n=1..3 and obtains rank 2^n−1). Checkpoint (b) uses exponent 3 because (log₂3)²≈2.51<3≤(log₂3)³≈3.98.

6. **Use a concrete exponent in checkpoint inequalities instead of the conjecture’s shape.** The three checkpoint statements give a stronger concrete numeric bound for each instance (for example, (log₂4)²), not the general expression (1+log₂ rank)^c. Each stands independently, neither depends on the conjecture, and neither follows directly from the conjecture’s injection axiom; the special cases test the definition layer rather than assuming the conjecture.


8. **Forbidden-token and metaprogram-declaration scans.** The lexical scan forbids axiom/sorryAx/native_decide/admitGoal/byAsSorry/skipKernelTC/implemented_by everywhere after comments are stripped. A declaration-level scan also checks the writable region and forbids notation/macro/syntax/elab/macro_rules/initialize declarations, preventing semantic changes through metaprogramming without editing the protected text. This is the same design as the alon-jaeger-tarsi pilot. decide is allowed because it is kernel computation and adds no trust assumption. The checkpoint rank proofs and protocol checks need no computation beyond decide; the reference proofs use rfl-level reduction and fin_cases.

9. **The exfalso-harvest scan detects declarations of both False and ¬ forms.** It scans helper declarations with type False and theorem X : ¬ …; use of either in a scored slot sets the score to 0 and marks it SUSPECT. instruction.md says helper lemmas must state positive propositions and gives a positive example. The refuted slot itself is a negated theorem and is therefore included in the scan. Any slot referring to refuted triggers the same check; that route is already rejected by the axiom whitelist, so both mechanisms score it 0. The alon-jaeger-tarsi pilot has the same behavior, recorded in this package’s score.py docstring.
