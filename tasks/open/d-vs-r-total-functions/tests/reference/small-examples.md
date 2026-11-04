# Executable Small Examples — `d-vs-r-total-functions`

Small examples check the definition layer (decision trees, D, randomized decision-tree distribution semantics, Rc) and the three special-case statements.

- Script: `dvr_sim.py`, a pure-Python implementation of the definition layer. D is computed exactly by subcube recurrence; R is computed exactly by linear programming: enumerate behavior pairs (output vector, per-input cost vector) for all depth-bounded decision trees, deduplicate and prune, then minimize the worst-case expected cost subject to per-input error rate ≤ 1/3. This matches the semantics of Lean's `Rc`. The quantities s and bs are included for comparison. All checks passed when; complete output is in `sim-output.log`. LP solver: HiGHS (`highspy`).

## 1. Definition-layer checks (exact small-instance values of D and Rc)

Each row is one function. D is computed exactly by recurrence, R by linear programming (with per-input error tolerance 1/3); s/bs are comparison values. The final column D/R² is only a reference: at n ≤ 4, allowing a constant error budget of 1/3 can make R far below 1 (e.g. R = 1/3 for id_1), so these small-scale values carry no asymptotic information. The conjecture's quadratic-versus-cubic question concerns n → ∞; known quadratic separation constructions (pointer-function families) are far beyond the exactly computable range.

| Function | n | D | R (exact) | s | bs | Notes |
|---|---|---|---|---|---|---|
| id_1 | 1 | 1 | 1/3 | 1 | 1 | Smallest nonconstant function |
| OR_2 / AND_2 / XOR_2 | 2 | 2 | 2/3 | 2 | 2 | |
| OR_3 / AND_3 | 3 | 3 | 1 | 3 | 3 | R = bs/3; tight in Nisan's lower bound |
| MAJ_3 | 3 | 3 | 8/9 | 2 | 2 | This is Lean's `majFn 3`; reconciliation value for c2 |
| PARITY_3 | 3 | 3 | 1 | 3 | 3 | |
| EXACT1_3 | 3 | 3 | 1 | 2 | 2 | |
| OR_4 | 4 | 4 | 4/3 | 4 | 4 | R = bs/3, tight |
| MAJ_4 (strict majority) | 4 | 4 | 14/9 | 3 | 3 | |
| PARITY_4 | 4 | 4 | 4 (LP infeasible for depth ≤ 3) | 4 | 4 | Any tree with depth < n is correct on at most half the uniform inputs, so some input has error rate ≥ 1/2 |
| AND-OR tree 2×2 | 4 | 4 | 16/15 | 2 | 2 | |
| OR-AND 2×2 (= Rubinstein n=4) | 4 | 4 | 16/15 | 2 | 2 | Rubinstein's family separates bs from s; here bs = s = 2, so it has not separated them. It does not separate D from R. |

Exhaustive enumeration of all 256 functions at n = 3: D ∈ {0,1,2,3}, with corresponding R ∈ {0, 1/3, 2/3, 0.8333…, 8/9, 1}; no anomalous distribution. All values are consistent with Nisan's lemma R ≥ bs/3.

## 2. Checks of the special cases

Each row gives one special case, how it was checked, and the conclusion.

| Special case | Result | Check |
|---|---|---|
| c1 `symmetric_evasive` | Pass (all cases n = 1..5) | For all nonconstant symmetric functions with n ≤ 5 (enumerated by weight table; 62 functions at n=5), D = n by subcube recurrence, supporting the statement that every nonconstant symmetric function is evasive. |
| c2 `maj3_gap` | Pass | D(MAJ_3) = 3 by recurrence. A zero-error mixture of three rotations (query two variables; if they agree, output that value, otherwise query the third) was evaluated pointwise on all 8 inputs: expected cost 2 on 000/111 and 8/3 on each other input, so worst-case cost 8/3 and error 0. Thus Rc(MAJ_3) ≤ 8/3 < 3, proving the statement. Linear programming gives the exact R(MAJ_3) = 8/9 (the optimum under the bounded-error definition); 8/3 is an upper bound witnessed by a zero-error algorithm, so the statement uses a looser but cleanly provable form. |
| c3 `compose_D_le` | Pass (five pairs) | Verify D(f∘g) ≤ D(f)·D(g) pointwise for OR2∘MAJ3 (6 = 2·3), MAJ3∘OR2 (6 = 3·2), MAJ3∘MAJ3 (9 = 3·3), AND2∘XOR2 (4 = 2·2), and XOR2∘XOR2 (4 = 2·2); all are tight. |

## 3. Additional notes

- The conjecture statements (conj/refuted) have no standard answer because this is an open problem, so they are not numerically checked. The definition layer is supported by the pointwise comparisons in §1 (D recurrence values and Rc LP values agree with textbook examples) and the conceptual reconciliation in §2 of concept-ledger.
- “LP infeasible” for PARITY_4 is the correct signal: no depth ≤ 3 tree can reduce per-input error below 1/3, consistent with the classical argument that R(PARITY_4) = 4.
- The “Rubinstein n=4” row checks suggestion (b) in the task brief. Rubinstein's family gives a quadratic separation of block sensitivity from sensitivity (bs vs. s; Hamoudi 2025 survey, p. 9, research note dig2 item 3). It gives no separation in the D-vs-R direction (D and R have the same order). Quadratic separation of D from R comes from the pointer-function family of Ambainis–Balodis–Belovs–Lee–Santha–Smotrovs 2016/2017 (survey Proposition 9 states D(f) = Ω̃(R(f)²) [ABB+17]). See deviation 5 in concept-ledger.
