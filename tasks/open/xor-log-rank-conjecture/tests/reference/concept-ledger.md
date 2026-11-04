# Statement Ledger: The XOR Log-Rank Conjecture

This note explains the task statement for readers comparing the mathematical definitions with the Lean source. The current scoring statements are `conj` and `refuted`; proving either earns full credit.

This ledger compares the published statement of the XOR log-rank conjecture with the Lean statement used in this proof-conjecture task, and records every deviation and its rationale. It is intended for task authors and reviewers as one of the three fidelity records (the component-by-component ledger).

Sources: background survey `communication-information-complexity.md` (short name `xor-log-rank-conjecture`); Montanaro–Osborne 2009 (arXiv:0909.3392); and Tsang–Wong–Xie–Zhang, FOCS 2013 (arXiv:1304.1245; the abstract and author information were checked directly on arXiv).

Shipped statement: `environment/app/Task/Basic.lean` (identical, character for character, to the scoring copy in `tests/reference/Basic.lean`, apart from the checkpoint proofs).

## 1. Published statement and Lean correspondence

A standard formulation of the literature statement (TWXZ 2013 abstract; the communication-complexity form appears in Montanaro–Osborne 2009) is that there is a constant c such that every Boolean function f : {±1}ⁿ → {±1} has parity decision tree complexity PDT(f) = O(log^c sp(f)). A parity decision tree may query the parity of any subset of coordinates at each step. Here sp(f) is the number of nonzero Fourier coefficients of f. TWXZ also prove that the rank of the communication matrix M_f is exactly sp(f), so this statement is equivalent to the log-rank conjecture for XOR communication problems. The PDT version is stronger (PDT is at least the communication complexity, up to a factor of 2); both formulations remain open.

| Concept | Literature | Lean identifier in this task | Notes |
|---|---|---|---|
| Boolean function | f : {±1}ⁿ → {±1} | `f : (Fin n → Bool) → Bool`, with the ±1 form `boolSign f = pmOne ∘ f` (`true ↦ +1`, `false ↦ −1`) | Bool-valued and ±1-valued forms correspond bijectively via `pmOne`; this is the same encoding used by the related `mansour-conjecture` task. |
| Cube | {±1}ⁿ | `Fin n → Bool` | Finite, equality is decidable, and it has a complete `Fintype` instance. |
| Character | χ_S(x) = ∏_{i∈S} x_i (in the ±1 encoding) | `chi S x = ∏ i ∈ S, pmOne (x i)` (rational-valued) | Orthogonality, inversion, and Parseval have all been proved on the fixed cube. |
| Fourier coefficient | f̂(S) = E[f·χ_S] | `fourierCoeff (boolSign f) S` (rational-valued, with uniform average `cubeAvg`) | There is also an integer layer, `fourierNum`, for kernel-computable values; the bridge is `fourierCoeff_boolSign_eq_num`. |
| Sparsity | sp(f) = #{S : f̂(S) ≠ 0} | `sparsity f` (the cardinality after filtering the full set) | Always at least 1 (`sparsity_pos` is proved); the computable form is `sparsity_eq_filter_num`. |
| Parity query | Query the parity of any coordinate subset S | `parityQuery S x`: true when the number of −1 coordinates in S is even (equivalently, χ_S(x) = +1) | See deviation 1. |
| Parity decision tree | An internal node queries one parity and has two branches; leaves return answers | Inductive type `ParityTree n` (`leaf` / `node S lo hi`), with `eval`, `depth`, and `Computes` | |
| PDT(f) ≤ B | A parity decision tree of depth at most B computes f | `∃ d ≤ B, ComputesInDepth f d`, where `ComputesInDepth f d := ∃ t, t.depth ≤ d ∧ t.Computes f` | See deviation 3. |
| Conjecture | ∃ c, PDT(f) = O(log^c sp(f)) | `Conjecture`: `∃ c : ℕ, ∀ {n} (f), ∃ d, ComputesInDepth f d ∧ (d : ℝ) ≤ (1 + Real.logb 2 (sparsity f))^c` | See deviation 2 (the `1 +` safeguard, natural-number exponent, and logarithm base). |
| Refutation | Negation of the conjecture | `refuted : ¬Conjecture` | In classical logic this is equivalent to saying that for every c there is an f exceeding the bound. |

## 2. Deviations and rationale

1. **The Bool encoding of a parity query returns true when χ_S(x) = +1.** This means that the number of −1 coordinates in S is even. Both common encodings occur in the literature: with {0,1} inputs, the query returns the bit ⊕_{i∈S} x_i; with ±1 inputs, it returns the sign of ∏_{i∈S} y_i. The points in this task's cube use the `pmOne` encoding (`true ↦ +1`), so defining the query Bool as “the coordinate product is +1” makes the bridge lemma `pmOne_parityQuery : pmOne (parityQuery S x) = chi S x` hold exactly, without a sign. The two conventions give parity decision trees of the same complexity: complementing a query answer simply swaps the two subtrees. Thus statement fidelity is unaffected.

2. **The upper bound is written as `(1 + Real.logb 2 sp)^c`, with `c : ℕ`.** The literature writes `O(log^c sp)` or `log^{O(1)} sp`. The three differences do not change the truth of the statement. (a) The `1 +` protects the degenerate case sp = 1: then `log sp = 0`, while functions with sp = 1 are ±χ_S and have depth at most 1 (checkpoint c2). Mathlib's `logb` is 0 at 0 and 1; without the added 1, when c = 0 the right-hand side at sp = 1 is `0⁰ = 1`, while for c > 0 it is 0, making the meaning depend on the junk value. (b) The exponent is natural-valued: if a real exponent works, rounding it up to an integer also works, since the base is at least 1 and the expression is monotone in the exponent. (c) Changing the logarithm base changes the bound only by a constant factor, which is absorbed by the power. For sp ≥ 2, `(1+log₂ sp)^c ≤ (2 log₂ sp)^c = 2^c log₂^c sp`; that constant factor is absorbed as well.

3. **“PDT(f) ≤ B” is expressed existentially:** `∃ d ≤ B, ComputesInDepth f d`. The literature defines PDT as the minimum depth, but the tree type is infinite, so defining a minimum requires additional construction. The existential form is logically equivalent to “the minimum depth is at most B” (take d to be the depth of the tree) and is more convenient for a task model to satisfy by providing a tree.

4. **The spectrum and sparsity are defined over ℚ, while kernel computation uses an ℤ layer.** This is the same engineering choice as in the related `mansour-conjecture` task. The rational layer supports symbolic reasoning (orthogonality, inversion, and Parseval), but the kernel does not compute rational arithmetic. The integer numerator `fourierNum` (the numerator 2ⁿ·f̂(S)) together with bridge lemmas lets `decide` verify concrete sparsity claims for small examples.

5. **The definition layer does not include the equivalent statement “rank of the communication matrix = sparsity.”** That equivalence is TWXZ's starting point, but this task needs only the PDT form (both the survey and task statement use PDT). Adding it would substantially enlarge the definition layer. The instruction text explains the relationship in prose.

## 3. Distinguishing related problems

- The related `log-rank-conjecture` task concerns the general log-rank conjecture for the real rank of communication matrices. This task is its special case for XOR functions (`f⊕(x,y) = f(x⊕y)`, whose communication matrix has rank sp(f)); the statement, definition layer (Fourier spectrum versus matrix rank), and checkpoints are different.
- The related `mansour-conjecture` task shares the Fourier-definition pattern (`pmOne`/`chi`/`fourierCoeff` and the ℤ bridge), but its main conjecture concerns Fourier concentration of DNF formulas, not a polylogarithmic bound on PDT in terms of sparsity.

## 4. Current bounds and source checks

Checked for task authoring, using the survey and direct arXiv page checks.

- Upper bound: PDT(f) = O(√sp(f)) (Tsang–Wong–Xie–Zhang, FOCS 2013, arXiv:1304.1245). In the communication-complexity formulation, Sudakov–Tomon 2023 (arXiv:2311.18524) slightly improved Lovett's upper bound to D^CC = O(√rank). The gap to the conjectured polylogarithmic bound remains polynomial.
- Two additive-structure approaches were ruled out: Ostuni et al. 2023 (arXiv:2312.09400) disproved the Montanaro–Osborne spectral-structure conjecture and the Mande–Sanyal conjecture; the conjecture considered here remains open.
- Source check: Montanaro–Osborne, arXiv:0909.3392, “On the communication complexity of XOR functions,” explicitly states the conjecture. TWXZ, arXiv:1304.1245, “Fourier sparsity, spectral norm, and the Log-rank conjecture,” is by Hing Yin Tsang, Chung Hoi Wong, Ning Xie, and Shengyu Zhang (FOCS 2013). The survey had a typo in the TWXZ arXiv number, giving 1305.2454 (an astrophysics paper); this ledger corrects it to 1304.1245, whose title, authors, and abstract were checked directly on arXiv.
