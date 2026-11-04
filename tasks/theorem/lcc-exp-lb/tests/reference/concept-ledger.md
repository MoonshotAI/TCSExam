# Component Crosswalk — Lean Statements for the Linear 3-Query LCC Exponent Lower Bound

- What this document contains: A line-by-line crosswalk between the lemmas and definitions in the paper (arXiv 2311.00558v1) and the Lean identifiers in this task, including every deviation and its rationale.
- Intended readers: Task authors and reviewers; one of the three L2 fidelity records (component crosswalk).
- Source: PDF of arXiv 2311.00558v1 ( and read in full; key formula pages inspected individually: Theorem 1 (p. 2), Definition 2.3 and Facts 2.4/2.5 (p. 4), Lemma 2.9 and its proof (pp. 5–6), Definitions 5.1/5.5/5.6 and Lemma 5.7 (pp. 24–25), Definition 6.1, Observation 6.2, Lemma 6.3, Algorithm 6.4, Definition 6.5, and Lemma 6.6 (pp. 26–28), Lemma 7.1 (p. 30), Definition 7.2 and Lemma 7.3 (pp. 31–32), Lemma 7.4 (p. 33), §§7.5–7.6 (pp. 34–36), and Lemmas 8.1/8.3/8.4 and Claim 8.5 (pp. 37–41)).
- Packaged statements: `environment/app/Task/Basic.lean` (namespace `LCCExpLB`).

## 1. Checkpoint numbering crosswalk

Each row documents one checkpoint. “Paper reference” uses the numbering in arXiv v1, the version used for every check in this document.

| Checkpoint | Lean identifier | Paper reference | Informal content |
|---|---|---|---|
| c1 | `chain_xor_value` | Lemma 5.7 (+ Observation 5.2) | The codeword satisfies the chain XOR formula, with val(Φ_b) = k·(3d₀)^{r+1}. |
| c2 | `exists_contiguously_regular_partition` | Lemma 6.3 (Algorithm 6.4) | For every d ≥ 1, there exists a d-contiguous regular partition (the d ≥ 1 boundary assumption is described in Section 5). |
| c3 | `cauchy_schwarz_trick` | Lemma 7.1 | E_b[val(Ψ^{(t)})] ≤ √(k(|P_t|(3d₀)^{r−t}d^t)² + |P_t|·2k·E_M E_b[val(f_M^{(t)})]). |
| c4 | `kikuchi_quadratic_form` | Lemma 7.3 | For 1 ≤ ℓ ≤ n−1, x'ᵀAx' = D·f_M(x), where D = 2^{2r+2−2t}·C(n−2,ℓ−1)^{2r+2−t}; val(f_M) ≤ ‖A‖_{∞→1}/D (the lower-bound assumption on ℓ is in Section 5, and the upper-bound assumption is in Section 6). |
| c5 | `row_pruning` | Lemma 7.4 (= Lemma 8.1) | Under five parameter conditions, the number of bad rows satisfies |ℬ| ≤ 2ℓ^{−Γr}N. |
| c6 | `linear_3lcc_exp_lower_bound` | Theorem 1 (F₂, standard form) | ∃ C > 0: every standard-form code satisfies k ≤ C·(log₂ n)⁸/δ². |

Dependency structure: c1 and c2 are independent; c3 is parameterized by a partition (whose existence follows from c2); c4 is parameterized by a partition and a maximum directed matching; c5 is parameterized by a partition, a matching, and two concentration assumptions; c6 assembles c1–c5 with Fact 2.5 (the §7.6 route). This agrees with the dependency graph in the paper, §§5→6→7→8→Theorem 1.

## 2. Definitions crosswalk (paper ↔ this task)

| Concept | Paper | Identifier in this task | Notes |
|---|---|---|---|
| ±1 values | {−1,1}, x^S = ∏_{v∈S} x_v | `signOf : ZMod 2 → ℝ`, `xS x S` | 0 ↦ 1, 1 ↦ −1; addition in F₂ corresponds to multiplication of signs (`signOf_add`, proved). |
| val | max_{x∈{−1,1}ⁿ} f(x) (§2.2) | `val` (maximum over a finite set of real values, using max') | `valXY` is the two-variable version for (x,y), used by Ψ. |
| Standard-form LCC | Definition 2.3: three consistent matchings ℋ_u, |ℋ_u| ≥ δn, and x_u = Σ α_i x_{v_i} | `NormalFormCode` | All α_i are 1 over F₂; the size is exactly d₀ (see Deviation 2); systematic form is built in, as in the paper’s “without loss of generality” convention. |
| t-chain | Definition 5.1: (u, C_1, w_1, …, C_t, w_t), where C_h ∪ {w_h} ∈ H_{w_{h−1}} | `ChainData n t` + `IsChain` + `chainSet` | Chain data consists of a head and functions C and w; indices are 0-based (C_0.. correspond to the paper’s C_1..). |
| Chain containing Q | Definition 5.5: Q ∈ ([n]∪{★})^t × [n], with final entry Q_{t+1}, and each non-★ entry in C_h | `QVec`, `chainContains` | Same-length version; cond4 uses the suffix version (see Deviation 6). |
| Contiguous / size / ⊇ | Definition 5.5 | `contiguous`, `qsize`, `qle` | qsize includes the final entry, matching the paper’s definition of |Q|. |
| XOR formula Φ | Definition 5.6 | `phi` | Uses the paper’s first form (sum over (r+1)-chains; the paper states that it equals the split-chain form). |
| Contiguous regular partition | Five conditions in Definition 6.1 | `ContiguousPartition` (structure with eight fields: coverage, disjointness, containment, and cond1–cond5) | p is 0-based `Fin m` (the paper uses 1-based [m]; cond3 is interpreted correspondingly as p > 0). |
| Piece set P_t | Definition 6.1 (5) | `pieceIdx` | |
| Bipartite formula Ψ | Definition 6.5 | `psiPiece` (Ψ_{i,Q,p}), `psiT` (Ψ^{(t)}) | The y variables are indexed by all (Q,p); `qdiffSet` implements the convention C_h \ ★ := C_h. |
| Cross-term polynomial f_M | Lemma 7.1 | `fM` | |
| Maximum directed matching | Lemma 7.1 + footnotes 10–11 | `IsDirectedMatching`, `IsMaxDirectedMatching`, `maxMatchings`, `expectM` | Size ⌊k/2⌋ (perfect when k is even, with one vertex left over when k is odd); E_M is the uniform average. |
| Kikuchi matrix | Definition 7.2 (conditions 1–3) | `kikuchiEntry`, `kikuchiAijQp`, `kikuchiAij`, `kikuchiAM` | Rows are labeled by `SlotIdx`, a sum type with S/S'/R sections; see Deviation 5. The shared-chain clause in condition 3 is described in Deviation 11. |
| Kikuchi vector x' | Lemma 7.3 | `kikuchiVec` | |
| N, D | Lemma 7.3 | `kikuchiN`, `kikuchiD` | |
| ‖A‖_{∞→1} | §2.1 | `inftyToOne` | |
| Bad rows ℬ, Δ | Lemma 7.4 | `badRows`, `rowDeg`, `kikuchiDelta` | Only row degree is used; the column case is covered by all ordered pairs (i,j), using the same paper argument A_{j,i} = A_{i,j}ᵀ. |
| 2-LDC lower bound | Fact 2.5 (GKST06) | `twoLDCLowerBoundProp` | Packaged as a c6 assumption (see Deviation 3); F₂ form x_u + x_v = b_i. |
| Chernoff lower tail | Lower-tail form of Fact 2.6, used in Lemma 8.3 | `chernoffLowerProp` | Packaged as a c5 assumption; the statement is a weighted sum (see Deviation 4). |
| r-partite tail bound | Lemma 2.9, used in Lemma 8.4 | `partiteTailBoundProp` | Packaged as a c5 assumption; the expected partial derivative is expanded as a combinatorial sum (see Deviation 4). |

## 3. Statement-level deviations (itemized, with reasons)

1. **The main theorem uses the binary, standard-form version.** Theorem 1 in the paper gives n ≥ 2^{Ω((δ²k/(|F|−1)²)^{1/8})} for a linear (3,δ,ε)-LCC over any field. Its proof first handles the F₂ case, reducing a general (3,δ,ε)-LCC via Fact 2.4 (cited from Theorem 8.1 of Dvir’s notes) to a (3,δ') standard-form code, with δ' ≥ δ/6 and n' = 2n. Packaged c6 states the result directly for standard-form codes: k ≤ C·(log₂ n)⁸/δ², equivalently n ≥ 2^{(δ²k/C)^{1/8}}; the two forms differ only by constants, since C absorbs 6² from Fact 2.4 and the constant factor in log₂(2n). Fact 2.4 is an external result cited by the paper and is not packaged. The standard-form definition (Definition 2.3) is purely combinatorial, so the main theorem does not involve decoding algorithms or probability.
2. **The matching size is denoted d₀, and δ appears only in the conclusion.** The paper says that each matching has exactly δn edges and treats δn as an integer (in the chain count (3δn)^{r+1}, in (3δn)^{2r+1−t} in Δ, and in the parameter condition δℓ). In the packaged statement, the matching size is a natural number d₀, and δ : ℝ is related to the conclusion only through `d0 ≥ δ * n`. Replacing δn with d₀ point by point leaves every counting argument unchanged; the δ terms in conditions (2), (3), and (5) of Lemma 7.4 become d₀/n (which agrees with the paper when δn = d₀).
3. **Three proved facts are packaged as assumptions** (handled the same way as the corresponding results in companion tasks):
   - `chernoffLowerProp` (the lower-tail form of Fact 2.6): Pr[X < (1−δ)mp] ≤ exp(−δ²mp/2) for a binomial random variable. The proof of c5 (the coupling in Lemma 8.3) uses only this fact.
   - `partiteTailBoundProp` (Lemma 2.9): for an r-partite polynomial with nonnegative coefficients, Pr[P ≥ (1+β)^r μ] ≤ r(m+1)^r·exp(−½β²/(2γ+γβ/3)). The proof of c5 (Lemma 8.4) uses only this fact.
   - `twoLDCLowerBoundProp` (Fact 2.5, GKST06 Lemma 3.3/Claim 4.4): the linear 2-LDC lower bound δk ≤ 2 log₂ n. The c6 assembly in §7.6 uses only this fact. All three are established results in peer-reviewed literature (the proofs of Fact 2.6 and Lemma 2.9 appear in §2.4 of the paper; Fact 2.5 is cited from GKST06).
4. **Probability statements are written as weighted sums.** The two concentration assumptions avoid measure theory and are written as weighted sums over finite sets: subsets s ⊆ Fin m receive weight p^{|s|}(1−p)^{m−|s|} (Chernoff); x : Fin ρ → Fin m → Bool receives weight p^{|x|}(1−p)^{ρm−|x|} (r-partite tail bound). The expected partial derivative μ_Z in Lemma 2.9 is expanded as the combinatorial sum Σ_{T ⊇ Z} c_T·p^{|T|−|Z|}, which is the term-by-term calculation of the expected partial derivative of a multilinear polynomial.
5. **Kikuchi row labels align their indices with the components of Q.** Condition 3 of Definition 7.2 pairs C_{r−t+h} with Q_h (h = 1..t); in the original indexing Q = (Q_1,…,Q_r,Q_{r+1}), this component is Q_{r−t+h} (when |Q| = t+1 and Q is contiguous, it is exactly the h-th non-★ entry; the split product Π_{h=1}^{r−t} x_{C_h}·Π_{h=1}^t x_{C_{r−t+h}\Q_h} in Definition 6.5 can only be read this way). The package uses the original indexing: `kikuchiQR ht h = ⟨r − t + h, _⟩` (0-based). The row label is the sum type `SlotIdx = Fin (r+1−t) ⊕ (Fin (r+1−t) ⊕ Fin t)`, corresponding to (S_0..S_{r−t}, S'_0..S'_{r−t}, R_1..R_t), with 2r+2−t entries in total, as in the paper.
6. **In cond4, “contains Q'” is interpreted as suffix containment.** The tuple C⃗' ∈ ℋ^{(|Q'|−1)} in condition (4) of Definition 6.1 is a chain of length |Q'|−1, shorter than Q' (which has r+1 components); “contains Q” in Definition 5.5 is defined only for equal lengths. Following the use in the proof of Observation 6.2 (“first choose a suffix C⃗' ∈ ℋ^{(r)}_{|Q|−1}, then complete it”), the phrase “contains Q'” in cond4 must mean suffix containment: its tail is Q'_{r+1}, and every non-★ entry among the last |Q'|−1 chain positions of Q' lies in the corresponding C. The package defines `chainContainsSuffix` for this interpretation; same-length `chainContains` remains in use for cond1 and Definition 5.5.
7. **The constant in condition (1) of Lemma 7.4 is fixed at 2^16.** The paper says “γ ≤ 1/(cΓr³ log₂ n), for a sufficiently large absolute constant c” (Claim 8.5 has the same form; §8 determines the constant). The package sets c = 2^16 in `h1`; any sufficiently large choice works, and fixing a value makes the statement precise.
8. **The §7.6 route is used; no spectral norm appears.** The c6 assembly follows §7.6 (reduction to a 2-LDC), not §7.5 (spectral contradiction plus matrix Khintchine). Therefore the definition layer contains neither a spectral norm nor Fact 2.8. Three facts used internally in §7.6—“after zeroing bad rows, each row/column has at most Δ nonzero entries” (directly from rowDeg), “each row has at most (2ℓ)^{2r+2−t} nonzero entries” (directly from the row-label slots), and “a bipartite graph of maximum degree at most Δ has a matching of size at least |E|/Δ” (by a greedy argument)—belong to the proof of c6 and are not part of the statement.
9. **Φ uses the paper’s first form.** Definition 5.6 gives two equivalent forms (a sum over whole (r+1)-chains equals a sum obtained by splitting into a 1-chain and an r-chain); the package’s `phi` uses the first form, which the paper states is equal to the other. The arguments for Ψ and §7 use the split form, represented by `psiPiece`/`chainHeadPiece`. The proof of c1 needs this equality internally; it is part of the checkpoint’s proof obligations.
10. **Small boundary cases and defaults:**
    - If `maxMatchings k` is empty, `expectM` is defined as 0 by real division-by-zero convention (mathematically, this set is always nonempty for any k; this case has no practical effect and has no counterpart in the paper).
    - `badRows` quantifies over rows only (the paper says “rows/columns”); because A_{j,i} = A_{i,j}ᵀ (provable from the symmetry condition in `kikuchiEntry`), bad columns are covered by (j,i), so the two formulations are equivalent.
    - In `kikuchiD`, n − 2 and ℓ − 1 use truncated subtraction on natural numbers; `Nat.choose` is 0 when ℓ − 1 > n − 2, matching the convention for binomial coefficients.
    - In c6, the universal quantifier over codes is written by first choosing the code and then stating the range assumptions as antecedents (n ≥ 2, 0 < δ, and d₀ ≥ δn); n ≥ 3 follows automatically from a nonempty matching when d₀ ≥ 1.
11. **Condition 3 of the Kikuchi definition adds `u = v → qv ∉ U` (second repair; item 10 in the discrepancy list at the top of the file).** Condition 3 of Definition 7.2 in the paper (p. 31) requires only `u, v ∉ U`. When the two chains in a chain pair share their h-th chain link (`u = v`), this gives C(n−1, ℓ−1) choices for `U`, whereas the counting step in Lemma 7.3 (p. 32) uses C(n−2, ℓ−1) (“there are exactly C(n−2, ℓ−1) pairs … as this is the number of choices for U”); that count holds only when the two links differ (u ≠ v). The proof is written with u and v as distinct roles and does not handle the shared-link case. After `u ∉ U ∧ v ∉ U`, the package adds `∧ (u = v → qv ∉ U)`: when the links coincide, it also excludes the shared pivot qv from U, making the count C(n−2, ℓ−1) in both cases. This does not affect the monomial accounting in the identity (both sides have monomial 1 for shared-link entries). **This is the first actual deviation from the literal paper statement**; previous items are faithful interpretations, including making boundary cases explicit. Under the formal reading used here, the literal statement of the paper’s lemma is false: the review report `lcc-contradiction-10892038-review-260926.md` gives an instance with n = 4, k = 2, d0 = 1, r = t = 1, ℓ = 3, where the left side of the identity is 72 ≠ 24 = D·f_M; machine verification of the premises uses only the three standard axioms.

## 4. Items to verify

1. **Final confirmation of the suffix interpretation in cond4** (Deviation 6): fixed according to the use in the proof of Observation 6.2. If the original authors interpret it differently, only the cond4 field changes; the truth values of c2–c6 are unaffected.
2. **The bound |Ψ_{i,Q,p}| ≤ (3d₀)^{r−|Q|+1}d^{|Q|−1} in Lemma 7.1** depends on both forms in Observation 6.2 (|ℋ^{(r)}_{Q,p}| and |ℋ^{(r)}_{u,Q,p}|). Observation 6.2 is not packaged as a separate lemma (it is an internal step in the proof of c3); nothing is missing from the statement layer, but the proof obligations for c3 include it.
3. **The k′ = |L| ≥ (k−1)/2 bound in §7.6 and the use of 2N coordinates:** Fact 2.5 must be applied with n' = 2N (the row and column coordinate sets); the packaged `twoLDCLowerBoundProp` is stated for arbitrary n' ≥ 1 (the lower bound was made explicit; see Section 5), and c6 instantiates it internally.
4. **Appendix A (arbitrary fields)** has not been checked. The main theorem uses only the F₂ version, and Appendix A is outside the scope of this task.

## 5. Repair record: four boundary assumptions made explicit

### Defects and counterexamples

Source: the whole-repository adversarial falsification sweep (`group-6.md`, Section 1; counterexample scripts `lcc_check.py` and `lcc_hyp_check.py` are in the same directory and were). The four defects have the same form: a proposition lacks a positive lower bound for a natural-number parameter. At parameter value 0, all assumptions hold but the conclusion fails, making the proposition false as written and any checkpoint that assumes it vacuously true.

1. **`twoLDCLowerBoundProp` lacks `0 < n'` (reported defect L1):** Set k' = 1, n' = 0, δ' = 1, let ℒ' be the zero map, and G ≡ ∅. The three conditions about cycles/matchings/corrections hold vacuously; `0 < k'` holds; and `δ'·n' = 0 ≤ average matching size = 0`. The conclusion requires `1 ≤ 2·log₂ 0`. In mathlib, log 0 = 0, so the right side is 0 and the proposition is false. The c6 checkpoint and the bare main theorem assume this proposition, so the main theorem becomes vacuously true.
2. **`partiteTailBoundProp` lacks `1 ≤ ρ` (reported defect L2):** Set ρ = 0, m = 3, p = 1/2, c ≡ 1, μ = 1, γ = 1/2, and β = 1. The partial-assignment type `Fin 0 → Option (Fin 3)` contains only the empty assignment, and the Boolean array contains only the empty function; hZ reduces to the true statement `1 ≤ 1`. The left side of the conclusion has one term and its indicator condition holds (the term is 1), while the right side `ρ·(m+1)⁰·exp(…)` is 0. Thus `1 ≤ 0` is false and c5 is vacuously true.
3. **c2, `exists_contiguously_regular_partition`, lacks `1 ≤ d` (reported defect L3):** For d = 0, the cond4 bound for |Q'| ≥ 2 is `0^{|Q'|−1} = 0`, requiring that no suffix-chain extension containing Q' land in a piece. But coverage forces each chain into a piece, and cond1 forces that piece’s label Q to be contained in the chain. From the chain one can construct an all-non-★ Q' ⊇ Q that makes the chain a member of cond4Set, so `|cond4Set| ≥ 1 > 0`, a contradiction. On the counterexample code with n = 6, k = 2, d0 = 1 (`enc b = (b₀,b₁,b₀,b₁,b₀,b₁)`; the six 3-sets are `{2,3,5},{2,3,4},{0,3,5},{1,2,4},{0,1,3},{0,2,3}`; the fields were checked by script), all 18 one-chains and all three allowed labels per chain violate cond4. No valid partition exists when d = 0.
4. **c4, `kikuchi_quadratic_form`, lacks `1 ≤ ℓ` (reported defect L4):** When ℓ = 0, each row-index slot can only be ∅; condition 1 of `kikuchiEntry` requires `C_h = ∅ ∆ ∅ = ∅`, contradicting `|C_h| = 2`, so A ≡ 0. But ℓ − 1 in `kikuchiD` is truncated natural subtraction and equals 0, so C(n−2, 0) = 1 and D = 2^{2r+2−2t} > 0. On the same code as L3, take r = 1, t = 0, d = 3, a valid partition, M = {(0,1)}, and b = (0,0). The script computes fM(0) = 14 ≠ 0, violating both conjuncts: `0 = D·fM` and `val(fM) ≤ 0`.

### Support in the paper

All four boundary assumptions are implicit positivity conditions in the paper’s context (line numbers refer to `km24-lcc.txt`):

- Fact 2.5 (from line 344) comes from GKST06 and concerns codes of positive length; at n' = 0, “a matching on 0 vertices” degenerates, and log₂ n in the conclusion is undefined.
- The r-partite polynomial in Lemma 2.9 (from line 425) has r groups of variables (1 ≤ i ≤ r); when r = 0, it is a constant polynomial and the tail bound is meaningless.
- Lemma 6.3 (from line 1905) says “for every d ∈ N”, but the greedy step in Algorithm 6.4—“select exactly d^{|Q'|−1} chains”—requires selecting zero chains at d = 0, so the loop cannot terminate. The proof is meaningful only for d ≥ 1; the paper’s actual application takes d = 3δnℓγ/n ≥ 2.
- Lemma 7.3 (from line 2288) indexes rows by “sets of size exactly ℓ” and D contains C(n−2, ℓ−1); §7.6 takes ℓ = Θ(log⁴n/δ) ≥ 1, so ℓ = 0 is outside the paper’s scope.

### Repairs (synchronized across all three tiers)

- Add the premise `0 < n' →` to `twoLDCLowerBoundProp` (the guided, ladder, and bare tiers); add the bound assumption `(hρ : 1 ≤ ρ)` to `partiteTailBoundProp`; add `(hd : 1 ≤ d)` to c2; and add `(hℓ : 1 ≤ ℓ)` to c4. Apart from these four premises and their associated docstrings, the statements are unchanged.
- Compatibility at call sites: the 2-LDC assembled in c6 has n' = 2N ≥ 2 (N is the number of Kikuchi rows; §7.6); the number of parts when applying Lemma 2.9 in c5 is 2r+2−t ≥ 1; the partition in c6 uses d = 3d0ℓγ/n ≥ 2 (from h2 and h5 of c5); c6 takes ℓ = Θ(log⁴n/δ) ≥ 1.
- Guided and ladder checkpoint statements match token for token (compared using the same block-extraction logic as the grader); the bare main theorem matches the last guided checkpoint; `tests/reference/Basic.lean` matches the problem statement verbatim; the c2/c4 descriptions in `checkpoints.json` are synchronized with `weight_note`; `instruction.md` is synchronized; and item 9 was added to the deviation list in the guided file header.

## 6. Repair record: upper-bound assumption added to c4

### Defect and counterexample

When ℓ ≥ n, `C(n−2, ℓ−1) = 0`, so `D = 0`; at ℓ = n, every ℓ-subset is the full set, and `S ∆ T = ∅` cannot equal a two-element chain link, so the Kikuchi matrix is identically zero. In Lean, `x/0 = 0`, and the second conjunct reduces to `val(f_M) ≤ 0`. A legal instance with n = 6, k = 2, d0 = 1, r = t = 1, ℓ = 6 has `val(f_M) ≥ 1`, a contradiction (the axioms supporting the legal premises and failed conclusion are exactly propext / Classical.choice / Quot.sound).

### Support in the paper

- Lemma 7.3 in the paper (line 2288) states only the identity `x'ᵀAx' = D·f_M(x)`; the inequality `val(f_M) ≤ ‖A‖_{∞→1}/D` is a consequence used later (line 2543), and it implicitly requires D > 0. When that consequence was combined with the identity in one checkpoint statement, the range where D is positive was omitted. The identity still holds at ℓ = n (both sides are 0), so the counterexample refutes only the second conjunct.
- Machine-checked fact: `D > 0` iff `C(n−2, ℓ−1) > 0`, that is, ℓ ∈ [1, n−1] (together with the existing `1 ≤ ℓ`; `t ≤ r` ensures the exponent `2r+2−t > 0`).
- The paper’s assembly in §7.6 (line 2598) takes `ℓ = O(log⁴n/δ)`, well below n.

### Repair (synchronized across two tiers; c4 is absent from bare tier)

- Add the premise `(hℓn : ℓ ≤ n - 1)` to c4 (using the same explicit-boundary style as `(hℓ : 1 ≤ ℓ)` added; over ℕ this is equivalent to ℓ < n, and the ≤ form matches the existing premise). The quantified range is now [1, n−1], exactly the region where D > 0. Apart from the premise and its associated docstring, the statement is unchanged.
- Compatibility at the c6 call site: the assembly takes `ℓ = Θ(log⁴n/δ)`. When `ℓ ≤ n−1`, it uses the Kikuchi route; in the overflow case (`n ≤ ℓ ≤ log₂(n)⁴/δ + 1`), the main theorem’s conclusion absorbs the case directly through ∃C (machine lemma `c6_scheduling`, C = 2; this is the same path used for “c6 assembly compatibility”).
- Guided and ladder checkpoint statements match token for token; `tests/reference/Basic.lean` matches the problem statement verbatim; the c4 description in `checkpoints.json` is synchronized with `weight_note`; `instruction.md` is synchronized; item 9 in the guided header’s discrepancy list was updated to include five boundary assumptions.

### Same-pattern audit

c1–c3, c5, c6, and the three packaged assumptions were rechecked for quantifier domains and parameter ranges; no defect of the same kind was found. c5 does not constrain ℓ, but its degenerate cases are safe (at ℓ = 0, h4 is unsatisfiable; for ℓ > n, the row index is empty and the conclusion is true). The repair report’s same-pattern audit section contains the itemized arguments.

## 7. Repair record: shared-chain-link counting in c4 `kikuchiEntry`

### Defect and counterexample

The Section 6 repair (upper-bound assumption) blocked degeneration of the second conjunct when ℓ ≥ n. The first conjunct (the identity) was still false as written when the two chains in a chain pair share a link (u = v): condition 3 of `kikuchiEntry` gives C(n−1, ℓ−1) choices for `U` in that case, rather than C(n−2, ℓ−1), which is the count in `D`. A finite counterexample has n = 4, k = 2, d0 = 1, r = t = 1, ℓ = 3 (satisfying all premises, including equality in `hℓn`), with the identity’s left side equal to 72 ≠ 24 = D·f_M(0). The packaged `kikuchiEntry` matches Definition 7.2 of the paper verbatim, so the defect carries over from the literal paper statement (the counting proof of Lemma 7.3 assumes u ≠ v).

### Repair (synchronized across two tiers; bare tier has no c4)

- Add `∧ (u = v → qv ∉ U)` at the end of condition 3 of `kikuchiEntry` (a fixed-definition-layer repair following the same route as discrepancy r9/r10): when u = v, `U ⊆ [n] ∖ {u, qv}`, restoring the count C(n−2, ℓ−1); when u ≠ v, the condition is unchanged. The seven checkpoint statements and the Section 6 repair remain byte-for-byte unchanged, with no new premise. The three alternatives—changing D, omitting shared-chain pairs, or changing fM—were ruled out.
- Docstrings now explain the counting semantics (`kikuchiEntry` in both tiers and the counting paragraph in the guided c4 proof sketch); item 10 was added to the guided header’s discrepancy list; the corresponding rows in the Section 2 crosswalk and Section 3 item 11 were synchronized; item 4 of `instruction.md` and c4’s role and `weight_note` in `checkpoints.json` were synchronized.
- Scope of impact: the text of c5/c6 is unchanged, but the matrix’s meaning changes (the repaired matrix is a submatrix of the original—only entries with u = v ∧ qv ∈ U are removed). The upper bound on bad rows in c5 becomes weaker (machine lemma `badRows_card_new_le_old`); both types of entries used in c6’s decoding relation remain (the u ≠ v case is unchanged by definition; the u = v ∧ qv ∉ U case has a nonempty machine witness in the 10892038 instance).

### Same-pattern audit

The remaining fixed-region counting definitions were checked individually (symmetric-difference counts in S slots, cond4 batch counts, `kikuchiN`, the uniform expectation `maxMatchings`, chain-link counts, and others). No similar defect from assuming two objects are distinct was found: distinctness of the two elements in S slots follows from the `|C_h| = 2` field of `IsChain`; the other arguments are in the same-pattern audit section of the review report.
