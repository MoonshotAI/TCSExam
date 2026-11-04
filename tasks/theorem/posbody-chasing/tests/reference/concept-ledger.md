# Component crosswalk — Lean statements for linear positive-body chasing

- Contents: item-by-item comparison of the eight checkpoints and definition layer in `lean-posbody-chasing` against the source, with deviations, key calculations, and the §6.5 self-check

- Source version: arXiv 2304.01889v2 (2024-05-06); the complete text is stored at `paper.txt`

## 1. Checkpoint crosswalk

Each row gives one checkpoint and its correspondence to the paper and the Lean object in this task.

| Checkpoint | Lean theorem | Paper location | Paper result |
|---|---|---|---|
| c1 | `lp_weak_duality` | Section 3.2 (weak duality for (P)/(D), used implicitly in the proof) | Dual objective ≤ benchmark upward recourse |
| c2 | `movement_le_y` | Lemma 3.3 | Upward movement cost at a covering step ≤ (1+ε/4)·yᵗ |
| c3 | `dual_obj_nonneg` | Lemma 3.4 | (1+ε/4)·Σ_C yᵗ − (1+ε)·Σ_P zᵗ ≥ 0 |
| c4 | `recourse_le_dual` | Lemma 3.5 (specialized to α = 1/10) | Total upward recourse ≤ ((2+ε)(1+ε)/ε)·(Σ_C ỹ − Σ_P z) |
| c5 | `prefix_bound` | Lemma 3.9 | (1/w_i)(Σ_S c y − Σ_{P∩[s,t]} p z) ≤ log(1 + (4d·cmax_i(S)/ε)·xᵗ_i) |
| c6 | `tilde_y_exists` | Lemma 3.7 (constructed by Algorithm 1) | ∃ ỹ: segment sum ≤ w_i·log(1+40d²/ε²) (3.11) ∧ Σ_C ỹ ≥ (1−ε/10)Σ_C y (3.12) |
| c7 | `constructed_dual_feasible` | Lemma 3.8 | (ỹ/A, z/A, r̄) is feasible for (D) |
| c8 | `chasing_positive_bodies_competitive` | Theorem 3.6 (= Theorem 1.1) | Upward recourse ≤ K·benchmark upward recourse, where K = (2+ε)(1+ε)·log(1+40d²/ε²)/ε |

Paper material not included in the task: Theorem 3.1 and Lemma 3.2 (a warm-up route strictly subsumed by Theorem 3.6); all applications in Section 4 and Appendices B/C/D (rounding); Theorem 1.2 and Appendix E (lower bound); Appendix A (reduction from bodies to halfspaces, accepted as part of the problem definition); Appendix F (static box-constraint extension); and the background in Sections 1–2 (no numbered claims, except the two WLOG reductions listed as deviation 1).

## 2. Definition crosswalk

| Paper object | Lean object | Crosswalk notes |
|---|---|---|
| Weighted KL divergence KL_w(x‖y) = Σ w_i(x_i log(x_i/y_i) − x_i + y_i) | Per-coordinate term `x log(x/y) − x + y` (no separate definition) | The proof uses only nonnegativity term by term (`kl_term_nonneg`) and summation after substituting the KKT conditions; the aggregate form is never used. |
| “Poor man’s Pinsker”: a−b ≤ a·log(a/b) | `sub_le_mul_log` | An inline fact in the proof of Lemma 3.3, derived from 1+x ≤ eˣ; stated verbatim. |
| Positive-body chasing instance (sequence of halfspaces) | `ChaseData`: w, isCov, a, d, ε | Form after the WLOG reductions in Section 2: at each time, one covering constraint ⟨cᵗ,x⟩ ≥ 1 or packing constraint ⟨pᵗ,x⟩ ≤ 1+ε; constraints have nonnegative coefficients (`ha`). |
| Row sparsity dᵗ and d = max dᵗ | `ChaseData.supp/dCov` and `hsp` | dᵗ is used only at covering steps; `hd : 0 < d` (deviation 5). |
| Additive offset ε/(4·dᵗ·cᵗ_i), x̂ᵗ = xᵗ + offset | `ChaseData.off`, `xhat D x t u i = x u i + off t i` | Footnote 3 convention: both x̂ values at time t use the offset for time t; `xhat` makes the time parameters explicit (offset time t, point time u). |
| Algorithm (solutions to programs (I)/(II)) | Response bundle `ChaseRun` | The decisions are packaged; see deviation 2. |
| KKT (3.1)–(3.4) | `cov_tight/cov_kkt/pack_tight/pack_kkt` | (3.4) is required only where x^{t−1}_i > 0 (deviation 3). |
| Monotonicity (covering increases, packing decreases) and freezing outside the support | `cov_mono/pack_mono/cov_frozen/pack_frozen` | Direct consequences of the algorithm description (“If for some xᵗ_i the coefficients cᵗ_i = 0, then we set xᵗ_i = x^{t−1}_i”). |
| y⁰ = z⁰ = 0, x⁰ = 0, y,z ≥ 0 | `hy0/hz0/hx0/hynn/hznn` | The paper says “For convenience, we define y⁰ = z⁰ = 0”; x⁰ = 0 is in the problem definition in Section 1. |
| Auxiliary program (P) | `PrimalFeas` + `upwardRec` | The ℓ variables in (P) are absorbed by `min`: the optimum is ℓᵗ_i = (xᵗ_i − x^{t−1}_i)⁺, so opt(P) is minimum upward recourse. This task quantifies directly over every exactly feasible trajectory, a stronger pointwise statement than opt(P). |
| Dual (D) | `DualFeas` + `dualObj` | The constraints c y − rᵗ + r^{t+1} ≤ 0, −p z − rᵗ + r^{t+1} ≤ 0, 0 ≤ r ≤ w, and y,z ≥ 0 are stated verbatim. The boundary r^{T+1} = 0 is a convention outside the task, consistent with the direction of the recurrence and required for weak-duality Abel summation. |
| A = log(1 + 40d²/ε²) | `ChaseData.Aconst` (`Aconst_pos` is proved) | Stated verbatim. |
| ȳ = ỹ/A, z̄ = z/A | `ybar/zbar` | Stated verbatim. |
| r̄ˢ_i = (1/A)·max(0, max_{t≥s} segment sum), r̄^{T+1} = 0 | `rbar` (defined as 0 for s > T) | Stated verbatim; max_{t≥s} is a finite supremum over t ∈ [s,T] (`Finset.sup'`). |
| Segment sum Σ_{C∩[s,t]} c ỹ − Σ_{P∩[s,t]} p z | `segSum` | Stated verbatim. |
| cmax_i(S) = max_{τ∈S} cᵗ_i | `cmaxS` (0 when S is empty) | Stated verbatim; for S = ∅ both sides of Lemma 3.9 reduce to 0 ≤ 0 (deviation 8). |
| Upward recourse Σ w_i(xᵗ_i − x^{t−1}_i)⁺ | `upwardRec` | The cost measure after the WLOG reductions in Section 2 (deviation 1). |

## 3. Statement deviations

1. **The WLOG reductions are part of the problem definition.** (a) An instance is a sequence of single-constraint halfspaces (the body-to-halfspace reduction in Appendix A is not formalized); (b) both costs are upward recourse (equivalence to total ℓ₁ movement up to a factor of 2 is not formalized); (c) only violated constraints are received. The paper says, “We assume without loss of generality that we only get violated constraints.” This corresponds to the tightness assumptions (3.1)/(3.3) in the `ChaseRun` bundle. The analysis never uses violation at arrival directly: every use of x^τ_i ≤ 1/c^τ_i follows from tightness and nonnegativity, and has been checked individually.
2. **The algorithm is packaged as a response bundle.** Existence, uniqueness, and optimality of the KL projection are not formalized. Every checkpoint is stated for any (x,y,z) satisfying the KKT bundle, which is stronger than the paper’s statement about the specific algorithm; the analysis uses only these properties. Non-vacuity check: small example E5 numerically simulates the actual KL projection algorithm; all 60 random instances satisfy every response-bundle condition, so the bundle is instantiable and not vacuous.
3. **Positivity for the packing KKT condition (3.4).** The paper states (3.4) for every i, relying on convention (2.1). If x^{t−1}_i = 0 and pᵗ_i ≠ 0, monotonicity freezes the coordinate at 0, and the literal equality fails under Lean’s conventions 0/0 = 0 and log 0 = 0. Both uses in the proof remain valid: Lemma 3.4 uses the weighted form w_i xᵗ_i log(·) = −pᵗ_i zᵗ xᵗ_i, where both sides are 0; Lemma 3.9 uses the inequality −p^τ_i z^τ/w_i ≤ log(x^τ_i/x^{τ−1}_i), whose left side is ≤ 0 and right side is 0. Therefore this task requires (3.4) only where 0 < x^{t−1}_i, and small example E5 confirms that degenerate coordinates of the simulated algorithm are indeed 0.
4. **Lemma 3.5 is specialized to α = 1/10.** The paper states the result for general α ∈ [0,1/10], but uses it only in two places: the warm-up (α = 0, proving the weaker Theorem 3.1, not included here) and Section 3.4 (α = 1/10). The latter is used. The constants in (3.10) are specialized accordingly: (1+ε/4)(1+ε/5) ≤ 1+ε/2 (ε ≤ 1); checked numerically in small example E3.
5. **The assumption d ≥ 1.** d = 0 is equivalent to having no covering constraints; then upward recourse is always 0 (packing constraints only decrease the variables), and the main theorem is trivial. Excluding this case loses no content.
6. **The main theorem uses competitive recourse with an explicit constant.** Theorem 3.6 in the paper says “recourse ≤ O((1/ε)log(d/ε)) × opt(D)”, and opt(D) ≤ opt(P) = minimum upward recourse. This task combines the result with the explicit constant K = (2+ε)(1+ε)·log(1+40d²/ε²)/ε (= O((1/ε)log(d/ε)), since log(1+40d²/ε²) = O(log(d/ε))) and gives the bound pointwise for every exactly feasible benchmark trajectory, stronger than the statement through opt(D), with the constant fully explicit. c1 (weak duality) connects the two forms; the paper uses it once at the end of each proof of Theorems 3.1 and 3.6 (“the theorem follows from weak duality”).
7. **Time indices and boundaries.** Times are 1..T and x⁰ = 0. y and z are total functions, with value 0 outside their type and at time 0 (an extension of the paper’s y⁰ = z⁰ = 0 convention that simplifies sums).
8. **Alignment of Lean’s conventions with paper convention (2.1).** Lean uses 0/0 = 0 and log 0 = 0. The KL term’s nonnegativity is used only where y > 0 or x = y = 0 (`kl_term_nonneg` requires y > 0; the degenerate coordinate term is evaluated directly as 0). The case cmax_i(S) = 0 in Lemma 3.9, including S = ∅, is handled separately by a sign argument (left side ≤ 0 = log 1 = right side), without the offset telescoping argument.
9. **Finite form of the max_{t≥s} in r̄.** The paper writes max_{t≥s}; the actual range is [s,T] (constraints are defined only on [1,T], and the segment sum is constant for t > T). `rbar` is defined as 0 for s > T, giving exactly the boundary r̄^{T+1} = 0.
10. **Bundled assumptions for c7.** `constructed_dual_feasible` explicitly lists the five properties from the c6 conclusion as assumptions (0 ≤ ỹ ≤ y, zero outside the type, ỹ⁰ = 0, and (3.11)). The c7 proof does not actually need ỹ⁰ = 0 (segment sums start at s ≥ 1); it is retained to match the c6 conclusion verbatim.

## 4. Key calculations

### 4.1 c2 (Lemma 3.3): summing the offsets

Σ_{i∈supp} cᵗ_i·x̂ᵗ_i = Σ cᵗ_i xᵗ_i + Σ cᵗ_i·ε/(4dᵗ cᵗ_i) = 1 + dᵗ·ε/(4dᵗ) = 1 + ε/4. The condition dᵗ ≥ 1 follows from ⟨cᵗ,xᵗ⟩ = 1 (if the support is empty, the left side is 0); cᵗ_i ≠ 0 ⟹ cᵗ_i > 0 (`ha`) justifies cancellation in the denominator. Small example E4 checks this by hand (n=2, y¹ = log 17).

### 4.2 c3 (Lemma 3.4): telescoping signs

For a covering step, −x̂ᵗ + x̂^{t−1} = x^{t−1} − xᵗ (the offsets for the same t cancel); for a packing step, −xᵗ + x^{t−1} = x^{t−1} − xᵗ. Summing gives Σ_{t=1}^T (x^{t−1} − xᵗ) = x⁰ − xᵀ = −xᵀ (`sum_Icc_one_sub` + `hx0`), and summing with w_i ≥ 0 gives ≤ 0. The paper writes “−w_i(xᵀ_i + x⁰_i)”; this agrees because x⁰ = 0.

### 4.3 c4 (specialized Lemma 3.5): constants

(1+ε/4)Σy ≤ (1+ε/4)(1+ε/5)Σỹ ≤ (1+ε/2)Σỹ. For the first step, Σy ≤ Σỹ/(1−ε/10) ≤ (1+ε/5)Σỹ, using 1/(1−u) ≤ 1+2u for u = ε/10 ≤ 1/10. For the second, (1+ε/4)(1+ε/5) = 1 + 9ε/20 + ε²/20 ≤ 1 + ε/2 when ε ≤ 1. Combining gives (1+ε/2)(1+(2+ε)/ε) = (2+ε)(1+ε)/ε. Small example E3 numerically checks all three identities for ε ∈ {0.01, 0.1, 0.5, 1}.

### 4.4 c5 (Lemma 3.9): comparing offsets and constants

The offset δ^τ = ε/(4d^τ c^τ_i) ≥ A := ε/(4d·cmax_i(S)) iff d^τ c^τ_i ≤ d·cmax_i(S). For τ ∈ S, c^τ_i ≤ cmax_i(S), and d^τ ≤ d by `hsp`. A larger positive constant makes a covering ratio ≥ 1 smaller (`ratio_add_le_ratio_add`); for a packing ratio ≤ 1, adding a positive constant makes it larger (`ratio_le_ratio_add`), including the degenerate case x^{τ−1} = 0 where both sides are 0. After telescoping, (xᵗ+A)/(x^{s−1}+A) ≤ (xᵗ+A)/A = 1 + xᵗ/A = 1 + (4d·cmax_i(S)/ε)·xᵗ. If cmax_i(S) > 0, then A > 0 (d ≥ 1 follows from S nonempty, `hsp`, and `hd`). Small example E6 checks the numerical form of (3.11) for all (i,s,t) prefixes across 60 simulated instances.

### 4.5 c7 (Lemma 3.8): splitting a prefix

The segment sum `segSum(i,s,u)` equals ±(aˢ_i·multiplierˢ) + `segSum(i,s+1,u)` for u ≥ s (Icc splitting). The max(0, sup_s) is at least max(first term, first term + sup_{s+1}) = first term + max(0, sup_{s+1}) for covering, since the first term cˢ_i ỹˢ ≥ 0. For packing, the first term is ≤ 0, so split according to whether max(0, sup_{s+1}) is 0. When s = T, the second prefix is 0 (`rbar` branch for s > T). The box bound r̄ ≤ w follows from (3.11) on each segment. Small example E6 numerically checks the dual constraints and box bound for every (i,s).

### 4.6 c8: assembling the constant

K = (2+ε)(1+ε)/ε · A. The chain is: c6 gives ỹ; (3.12) feeds c4 to obtain recourse ≤ ((2+ε)(1+ε)/ε)(Σ_C ỹ − Σ_P z); zero values outside the type give Σ_C ỹ − Σ_P z = Σ_{[1,T]}(ỹ − z) = A·dualObj(ȳ,z̄); c7 gives feasibility; c1 gives dualObj ≤ upwardRec(x'). A > 0 (`Aconst_pos`) preserves the inequality when multiplying.

## 5. Systematic error-pattern self-check

1. **Existential outputs are constrained.** The c6 witness ỹ is constrained in four ways: 0 ≤ ỹ ≤ y, zero outside the type, (3.11), and (3.12). The most degenerate choice ỹ ≡ 0 violates (3.12) on an instance with Σy > 0 (for example E4); choosing ỹ = y violates (3.11) on an instance with a large aspect ratio (the Δ barrier at the start of Section 3.4). Neither direction is trivial. ✓
2. **Degenerate parameter substitutions.** T = 0 (no constraints): all sums are empty, so c1–c8 hold (for c8, 0 ≤ K·0). n = 0: no coordinates, and the bundle’s tightness condition 0 = 1 is unsatisfiable, so there is no `ChaseRun`; the checkpoints quantify over (D,R) and are vacuously true but harmless (actual instances have n ≥ 1). ε = 1: constants checked in E3. S = ∅ (c5): handled by deviation 8. ✓
3. **Main-theorem assumptions cover invoked checkpoints.** c8 invokes c4 (requires (3.12), supplied by c6) and c1 (requires DualFeas + PrimalFeas, supplied by c7 and the task assumptions), as well as c6/c7 (their assumptions are exactly (D,R)). c4 does not depend on ỹ being nonnegative (nor does c8). The five assumptions of c7 match the c6 conclusion verbatim. ✓
4. **Substitution and evaluation points agree.** The offset ε/(4·dᵗ·cᵗ_i) and the two time arguments of x̂ were checked against footnote 3. The evaluation point xᵗ_i in c5 (the right endpoint) matches (3.14). The 40d²/ε² in `Aconst` matches (3.11) and the definition of A before Lemma 3.8 (the two appearances on the same page were cross-checked). ✓
5. **Base cases.** The c6 proof is induction (base ℓ = 0 is trivial); c5 telescoping requires s ≥ 1 (assumption `hs : 1 ≤ s`); `sum_Icc_one_sub` starts at t = 1. ✓
6. **Two-sided conditions and boundaries.** c5 includes all three conditions 1 ≤ s ≤ t ≤ T; c6’s (3.11) has the same three conditions. DualFeas includes both sides of the box bound 0 ≤ r ≤ w. ✓
7. **Weakening and vacuity.** The conclusion is not weaker than the paper’s (deviation 6 establishes the stronger form). The assumptions can hold simultaneously: E5 instantiates a response bundle; E6 instantiates DualFeas; a benchmark heuristic search instantiates (P)-feasibility. ✓

## 6. Judging-side and task-statement self-check

- No notation/macro/syntax/elab declarations occur between the fixed section and the checkpoint slots (none appear anywhere in the file, consistent with the repository-wide state).
- Every sentence about judging in the task statement matches `score.py` behavior, item by item (checkpoint isolation, injected axioms, full assembly credit, `main_direct` bypass, lexical blacklist, and `sorry` handling). `instruction.md` adapts wording from the three-taxi family template.

## Statement requirements

- Contents: repair record for a false main theorem; the `ChaseRun` response bundle gained a positivity-preservation field `pack_pos`.
- Cross-check: under the real-log semantics in KKT (3.4) of arXiv 2304.01889v2, xᵗ_i = 0 makes the left side −∞, which no finite multiplier can satisfy; the paper itself excludes moves to 0, so the issue was in our formalization (deviation 3 had checked only the degenerate frozen-coordinate case).
- Repair: after `pack_kkt`, `ChaseRun` gained `pack_pos : ∀ t ∈ Finset.Icc 1 D.T, D.isCov t = false → ∀ i, D.a t i ≠ 0 → 0 < x (t−1) i → 0 < x t i` (the multiplicative update in program (II), §3.1, preserves positivity; draft by astra, task 214775; the primary agent applied the change atomically to all three tiers).
