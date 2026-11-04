# Statement Ledger: The KRW Composition Conjecture

This note explains the task statement for readers comparing the mathematical definitions with the Lean source. The current scoring statements are `conj` and `refuted`; proving either earns full credit.

This ledger compares the literature statement of the KRW composition conjecture with the Lean statement in this proof-conjecture task, and records every deviation and its rationale. It is intended for task authors and reviewers as one of the three fidelity records (the component-by-component ledger).

Sources: survey `communication-information-complexity.md`, item 3 (short name `krw-composition-conjecture`; includes sources, evidence that it is open, and known bounds); original source Karchmer–Raz–Wigderson 1995 (*Computational Complexity* 5:191–204, DOI 10.1007/BF01206317; volume, issue, pages, and authors checked against the Springer page).

Shipped statement: `environment/app/Task/Basic.lean` (the scoring copy in `tests/reference/Basic.lean` differs only in the proof bodies for the three checkpoint slots, which are proved as positive controls; the fixed region and slot headers are identical).

## 1. Published statement and Lean correspondence

A standard formula-depth formulation (used in the introductions of GMWW 2017 and STACS 2025) is equivalent, via the Karchmer–Wigderson correspondence, to the communication formulation in KRW 1995. There is a global constant c such that, for every **nonconstant** Boolean functions f: {0,1}^m → {0,1} and g: {0,1}^n → {0,1}, the formula depth of their block composition (f⋄g)(x₁,…,xₘ) = f(g(x₁),…,g(xₘ))—where each input bit of f is replaced by a copy of g on its own independent block of new variables—satisfies

  D(f⋄g) ≥ D(f) + D(g) − c.

Here D(f) is the minimum depth of a formula computing f over the De Morgan basis (binary AND/OR, with literals at the leaves); leaves have depth 0, and NOT gates do not count toward depth. The trivial upper bound D(f⋄g) ≤ D(f) + D(g) always holds; the conjecture asserts the lower bound. If it holds for a growing family of functions, it can be iterated to obtain superlogarithmic depth lower bounds and hence NC¹ ≠ P.

| Concept | Literature | Lean identifier in this task | Notes |
|---|---|---|---|
| Boolean function | f: {0,1}ⁿ → {0,1} | `f : (ι → Bool) → Bool` (ι finite) | Variables are indexed by an arbitrary finite type; see deviation 6. |
| Formula | De Morgan formula (binary AND/OR; leaves are variables or their negations) | `KRW.BFormula ι` (inductive type `const` / `lit i b` / `and` / `or`) | See deviations 2 and 3. |
| Formula depth | Number of edges in a longest root-to-leaf path; a leaf has depth 0 | `BFormula.depth` (leaf 0; AND/OR take max+1) | Matches the literature. |
| Computation | A formula agrees with f on every assignment | `BFormula.Computes φ f := ∀ x, φ.eval x = f x` | Decidable on a `Fintype`. |
| D(f) | Minimum depth of a formula computing f | `KRW.depthOf f` (the `sInf` of a set of natural numbers; attainability is proved) | See deviation 3. |
| Block composition | (f⋄g)(x₁,…,xₘ) = f(g(x₁),…,g(xₘ)) | `KRW.blockComp f g : (Fin m × Fin n → Bool) → Bool` | Each of the m inner copies of g receives its own block of new variables. |
| Nonconstant | f takes both values 0 and 1 | `KRW.NonConst f := ∃ x y, f x ≠ f y` | Needed; without it the claim is false, since if g is constant then f⋄g is constant while D(f) can be arbitrary. |
| Conjecture | ∃c, for all nonconstant f,g, D(f⋄g) ≥ D(f)+D(g)−c | Main slot `conj` (`refuted` is its negation); −c uses truncated subtraction on naturals | See deviation 4. |
| Upper-bound direction | D(f⋄g) ≤ D(f)+D(g), trivially | Checkpoint c2 (assembled with the `compFormula` API) | Explains why the conjecture asserts only a lower bound. |
| XOR as inner function | Inner function in the STACS 2025 progress result | Checkpoint c1: D(xor₂) = 2 | Calibration point for the smallest nonconstant example. |

## 2. Deviations and rationale

1. **Use the formula-depth form, rather than the communication form in KRW 1995.** The original paper states a communication-complexity bound, CC(KW_{f⋄g}) ≥ CC(KW_f) + CC(KW_g) − O(1), where KW_f is the Karchmer–Wigderson relation. By the Karchmer–Wigderson correspondence, the deterministic communication complexity of KW_f is exactly formula depth, so the formulations are equivalent. Later work (including GMWW 2017 and STACS 2025) commonly states the formula-depth form directly. We use it because formalizing communication protocols (trees with a rectangle partition at each node) is substantially more involved than an inductive formula type, and the formula form better fits the task's exact-depth small examples. Of the two routes (a)/(b) in the design guidance, this task follows (a).

2. **Use the De Morgan basis, with signed literals at the leaves and free NOT.** The literature uses {∧,∨,¬} and counts only ∧/∨ layers toward depth. De Morgan's laws push negations to leaves without changing the ∧/∨ structure or depth; the reverse inclusion is immediate. Thus D(f) is the same under either convention. The dual operator `BFormula.dual` (with proved lemmas `eval_dual` and `depth_dual`) implements this negation-pushing process.

3. **Allow constant leaves.** The literature usually does not discuss constant leaves explicitly. Allowing `const` does not change D(f) for nonconstant functions: constants can be eliminated using x∧0=0, x∧1=x, x∨0=x, and x∨1=1 without increasing depth. It also makes `depthOf` well-defined for zero-variable types and constant functions. A DNF exists for every finite ι (`exists_computes`), so the `sInf` is attained. The conjecture excludes constant functions, so the two readings agree on its domain.

4. **Conjecture form: reciprocal-fraction form for k ≥ 2, expressed multiplicatively.** The current form follows GMWW (ECCC TR13-190 rev.11, 2017), Conjecture 1.3 and footnote 3(ii):
   `conj : ∃ k : ℕ, 2 ≤ k ∧ ∀ m n f g, NonConst f → NonConst g → k·depthOf f + depthOf g ≤ k·depthOf (blockComp f g)`.
   This uses natural-number multiplication, with neither division nor truncated subtraction. Equivalently, D(g) contributes ⌈D(g)/k⌉ to the integer-valued lower bound; `ε = 1/k` is equivalent to `∃k ≥ 2`.

5. **The `refuted` slot is the classical negation of `conj`:**
   `∀ k : ℕ, 2 ≤ k → ∃ m n f g, NonConst f ∧ NonConst g ∧ k·depthOf (blockComp f g) < k·depthOf f + depthOf g`.
   The counterexample may depend on k. The task's proved lemma `refuted_iff_not_conj` establishes equivalence with `¬conj`.

6. **Use an arbitrary finite type ι for the variable index set.** The natural variable index for block composition is a pair (i,j) : Fin m × Fin n. If formulas were fixed to Fin k, the statement would need an equivalence Fin(m·n) ≃ Fin m × Fin n, and every lemma would need to carry that conversion. A polymorphic ι removes this conversion layer; the literature writes at the set level and has no such distinction.

7. **Decidability of small examples is implemented by enumerating `BFormula.upTo`.** `upTo d` enumerates all formulas of depth at most d (constants/literals and pairings built level by level); `mem_upTo` characterizes membership as depth ≤ d. Together with `depthOf_le` (an explicit formula gives an upper bound) and `le_depthOf` (exhaustive rejection of smaller formulas gives a lower bound), statements of the form `depthOf f = k` for small examples can be verified directly by kernel `decide`. `native_decide` is prohibited by the task's lexical scan; kernel `decide` is unaffected.

## 3. Distinguishing related problems

- The same repository's `log-rank-conjecture` is also in communication complexity (the relation between the log-rank of a Boolean matrix and deterministic complexity), but it is a different conjecture.
- `mansour-conjecture` and `fourier-entropy-influence` in the same repository belong to Boolean Fourier analysis and do not overlap with this statement.
- This is a **decision problem about a structural statement** whose truth is open: either proving it for all nonconstant f,g or refuting it with a family of counterexamples indexed by c would resolve it.

## 4. Current bounds and source checks

Checked for task authoring.

- The best known general lower bound on De Morgan formula depth remains Håstad 1998's (3−o(1))·log n, as stated in the introductions of both STACS 2025 and Wu 2024.
- The monotone-formula version is proved in the original KRW 1995 paper, as a direct-sum theorem for the monotone KW game.
- Constrained versions: composition with the universal relation is proved (Gavinsky–Meir–Weinstein–Wigderson 2017, SICOMP 46(1):114–131; ECCC TR13-190); a KRW-style theorem for strong composition is proved (Mihajlin–Smal, arXiv:2306.00615); and for strong composition KW_XOR ⊛ KW_f, with f a random Boolean function, n^{3−o(1)} leaves are required with probability 1−o(1) (Chukhin–Kulikov–Mihajlin, STACS 2025, arXiv:2410.10189; the arXiv page's comments confirm acceptance at STACS 2025).
- A depth lower bound close to 4·log n is known in the restriction-on-top restricted model (Wu 2024, arXiv:2404.15613).
-, searches through the arXiv API (three queries: “Karchmer-Raz-Wigderson,” “KRW conjecture,” and “Karchmer-Wigderson AND composition,” sorted by submission date) and the full ECCC 2025/2026 yearly catalogs found no work resolving or claiming to resolve the general conjecture. The STACS 2025 paper still describes it as an open approach. The conjecture remains open.
