# Component crosswalk: `lean-negations-small-depth` (first route in SOP step 6)

- Contents: item-by-item comparison of each checkpoint statement with arXiv 2512.19515v1, including assumptions, quantifiers, boundary cases, constants, and a complete list of deviations with reasons
Each item can be located in the source; line numbers refer to `pdftotext` output for the archived `cbfmsy25.txt`.

## Comparison conventions

- The paper uses circuits represented as DAGs; this task uses tree formulas (file-header deviation 1; precedent in the related `lean-monotone-matching` task). Statements about “circuits” in the paper are stated here for “formulas”; this restricts lower bounds to formulas, while upper bounds are unchanged.
- All asymptotic notation is made explicit: `O(e(G)²·n)` becomes `35·(e(G)+1)²·n`; `2^{Ω(n)}` becomes `∃ c > 0, ∃ N₀, ∀ n ≥ N₀, 2^{c·n} ≤ …`.

## c1 `graphPoly_support` (opening of Corollary 2.8 proof, lines 1026–1057)

| Item | Source | Task statement | Check |
|---|---|---|---|
| Coefficient | In `P_G`, the coefficient of monomial `∏ᵢ x_{i,aᵢ}` is `(Σ_{uv∈E} a_u a_v − 1)²` (from equation (1), lines 528–533; the HTML version confirms the sum is inside the square) | `(graphPoly G).coeff (expVec a) = ((edgeCount G (suppOf a)) − 1)²` | Equivalent: `Σ_{uv∈E} a_u a_v = e(G[supp a])`, since `a_u a_v = 1` iff both endpoints are in the support. |
| Support characterization | `A(P_G) = {supp(a) : e(G[supp a]) ≠ 1} = supp(fG⁻¹(1))` | `expVec a ∈ (graphPoly G).support ↔ fG G a = true` | Equivalent pointwise form, avoiding a set equality involving an image. |
| Assumptions | None | None (`G` arbitrary) | Match. |
| Boundary | For `e = 0`, coefficient is `(0−1)² = 1` | Same | Checked in small examples 1/2/6. |

## c2 `graphPoly_shallow_upper` (Corollary 2.2, line 776; Lemma 2.1, line 566)

| Item | Source | Task statement | Check |
|---|---|---|---|
| Conclusion | `P_G` has a ΣΠΣ **formula** of size `O(e(G)²·n)` | There exists a formula with `toPoly = graphPoly G` and `size ≤ 35·(e+1)²·n` | The constant is explicit; the paper already states a formula, matching the tree model. |
| Constant derivation | `O(e²k2^{n/k})` (Lemma 2.1; setting k=n gives `O(e²n)`) | There are at most e² `Q₂` terms, each of size ≤ 4n+8; at most e `Q₁` terms, each ≤ 4n+5; `Q₀` has size 4n+1. Folding costs +1 per term. The total is ≤ (4n+9)e² + (4n+6)e + 4n+8 ≤ 35(e+1)²n for n ≥ 1: `13e²n + 10en + 12n ≤ 35(e+1)²n`, termwise using `4n+9 ≤ 13n`, `4n+6 ≤ 10n`, `4n+8 ≤ 12n`, `e ≤ e²`, and `n ≤ e²n` for e ≥ 1; for e=0, `4n+7 ≤ 35n`. | Constant 35 is sufficient. |
| Assumptions | None | `1 ≤ n` | For n=0, `P_G = 1` and `const 1` has size 1 > 35·(e+1)²·0 = 0, making the literal statement false. The assumption was added. |
| ΣΠΣ shape | Depth-3 formula (top-level addition, with one subtraction) | Does not define an abstract ΣΠΣ class; gives the explicit construction directly (file-header deviation 8) | Shape is noted in the docstring. |

## c3 `balanced_pair_decomp` (Lemma 2.3, lines 818–833)

| Item | Source | Task statement | Check |
|---|---|---|---|
| Conclusion | `P = Σᵢ gᵢhᵢ`, `i ∈ [s]` (s is circuit size); each pair is balanced and monotone, and each product contains only monomials of `P` | `∃ ps : Finset (BalancedPair n)`, `ps.card ≤ C.size`, `P = ∑ p ∈ ps, p.g * p.h`, and `∀ p, (p.g * p.h).support ⊆ P.support` | Equivalent. The paper’s indexed family `[s]` may repeat elements; a Finset removes duplicates, hence `≤`. |
| Balance definition | For partition `{Y,Z}` of the variables, part count is in `[1/3, 2/3)·n` | `BalancedPair`: `n ≤ 3·Y.card ∧ 3·Y.card < 2·n`, with the same inequalities explicitly for Z; variable membership is recorded by `gVars/hVars` | Equivalent; exact integer form of `[1/3, 2/3)`. Both sides must be stated: a one-sided condition admits a falsely balanced pair with `3|Y| = n` and `|Z| = 2n/3` (caught in the initial draft by SOP 6.5 item 6). |
| Monotone factors | `g ∈ R[Y]`, `h ∈ R[Z]` are monotone | All coefficients are nonnegative (`gMono/hMono`) plus variable-side constraints | Equivalent. |
| Assumptions | P is set-multilinear monotone and computed by a monotone circuit | Same, for formulas, plus `4 ≤ n` | For n ∈ {1,3}, balanced partitions do not exist (small example 5), making the literal claim false. The paper works asymptotically; adding this assumption preserves the intended theorem. |
| Note | The paper says the proof is essentially the same as [RY11] | This task states the result by induction on formulas | Deviation 1. |

## c4 `monotone_size_rect_cover` (Lemma 2.4, lines 841–878)

| Item | Source | Task statement | Check |
|---|---|---|---|
| Conclusion | `S₊(P) ≥ mprn(f)` (lower bound on the minimum cover size) | Existential form: `∃ ι [Fintype ι] (rects : ι → BalancedRectangle n)`, `Fintype.card ι ≤ C.size`; all `suppOf a` with `f a = true` are covered, and each rectangle member is the support of some 1-input | `mprn` is not defined as an object (file-header deviation 6); this existential form connects directly to c6’s universal form. Both inclusion directions are needed for the source equality `supp(f⁻¹(1)) = ⋃ Rᵢ`. A formulation without this condition stated only coverage; the reverse inclusion was added (summary item 11). |
| Support condition | `supp(f⁻¹(1)) = A(P)` | `P.support = (univ.filter fun a => f a = true).image expVec` | Equivalent (`A(∏ᵢ x_{i,aᵢ}) = supp a`). |
| Rectangle definition | `R = {S ∪ T : S ∈ 𝒴, T ∈ 𝒵}`, with `𝒴 ⊆ P(Y)` etc.; balance as in c3 | Isomorphic `BalancedRectangle` structure (both balance conditions, `balY/balZ`) | Equivalent. |
| Assumptions | Same as c3 | Same as c3 (`4 ≤ n`) | Match. |

## c5 `corruption_disj` (Lemma 2.6, lines 903–919)

| Item | Source | Task statement | Check |
|---|---|---|---|
| Experiment | Each coordinate independently and uniformly samples from `{(0,0),(1,0),(0,1)}` | Uniform sample space `Fin ℓ → Fin 3` (counting measure / 3^ℓ); 1 ↦ (1,0), 2 ↦ (0,1), 0 ↦ (0,0) | Equivalent finite probability space. |
| Rectangle | A 1-rectangle for fixed partition `{{1..ℓ},{ℓ+1..2ℓ}}`, `R ⊆ supp(g⁻¹(1))` | `𝒴 ×ˢ 𝒵`, with `∀ L ∈ 𝒴, ∀ R ∈ 𝒵, (L ∩ R).card ≠ 1` | Equivalent (`g(b,c) = 1 ↔ |supp b ∩ supp c| ≠ 1`, lines 905–907). |
| Conclusion | `Pr[b ∈ R] < 2^{−ℓ/2}` | Same, with strict inequality | Match. |
| Assumption | `ℓ ∈ ℕ` | `1 ≤ ℓ` | Necessary: for ℓ=0 the only sample is `(∅,∅)`; if it is in R, its mass is 1 and not < 1, while if R=∅ the mass is 0 < 1. See small example 4 and SOP 6.5 item 2. The source has ℓ ∈ [n], which implicitly means positive. |

## c6 `multipartition_rect_lower` (Lemma 2.5, line 897)

| Item | Source | Task statement | Check |
|---|---|---|---|
| Conclusion | `mprn(fG) ≥ 2^{Ω(n)}` | `∀ d ≥ 2, ∃ c > 0, ∃ N₀, ∀ n ≥ N₀, ∀ G` (d-regular expander), and for every cover family, `(2)^{c·n} ≤ Fintype.card ι` | Universal form (deviation 6), with asymptotics explicit and constants depending on degree. |
| Assumption | G is an expander (d-regular and second-largest eigenvalue ≤ d^0.75) | Same (`IsExpander G d`, file-header deviation 5), plus `expanderMatchingProp` | The matching lemma (Lemma 2.7 = [Sri20] Lemma 9) is packaged as an assumption, as a previously proved literature result, just as in the paper. |
| Cover condition | `supp(fG⁻¹(1)) = ⋃ Rᵢ` (equality, lines 796–800; proof of Lemma 2.5 says “for every balanced rectangle R ⊆ fG⁻¹(1)”, lines 942–943) | Two assumptions: coverage `∀ a, fG G a = true → ∃ i, suppOf a ∈ (rects i).mem`; and reverse inclusion `∀ i, ∀ S ∈ (rects i).mem, ∃ a, fG G a = true ∧ suppOf a = S` | A formulation without this condition required coverage only, making the statement stronger than the lower bound for mprn and literally false. The reverse inclusion was added (summary item 11). |
| Threshold | None (absorbed by Ω) | Existential `N₀` | The proof needs conditions such as `⌈αn⌉ ≥ 1` and `γ⌈αn⌉ ≥ 1`; N₀ absorbs them, faithful to the meaning of Ω. |

## c7 `negations_small_depth_separation` (Theorem 1.1, lines 118–120; = Corollaries 2.2 and 2.8)

| Item | Source | Task statement | Check |
|---|---|---|---|
| Quantification | “There exists an n-variable polynomial P = Pn” (constructed from an expander on n/2 vertices) | “For every d ≥ 2, there exist c,N₀; for every n ≥ N₀ and every n-vertex d-regular expander G, both bounds hold for P_G” | Per-graph, per-degree form implies the source form by taking a family of explicit constant-degree expanders (existence of that family is not included). The paper’s setting is also constant-degree expanders ([Sri20] fixes a sufficiently large constant d); Section 2 uses n-vertex graphs / 2n variables, while Theorem 1.1 uses n/2 vertices / n variables, just a variable-name change. |
| Upper bound | ΣΠΣ circuit of size `O(n³)` | Formula of size `35·(e+1)²·n` | For d-regular graphs, `e = dn/2`; constant degree gives `O(n³)`. A formula bound is stronger than a circuit bound. ✓ |
| Lower bound | Every monotone arithmetic circuit has size at least `2^{Ω(n)}` | Every monotone arithmetic formula has size at least `2^{c·n}` for n ≥ N₀ | Formula lower bound follows from the source circuit lower bound; the converse does not hold (deviation 1). |
| Assumption | None (all lemmas proved in the paper) | `expanderMatchingProp` | Lemma 2.7 is packaged as an assumption, following the related task’s treatment of proved external facts. |

## Additional definition checks

- `fG` (lines 888–889): `fG(a) = 1 ↔ e(G[supp a]) ≠ 1`; task uses `decide (edgeCount G (suppOf a) ≠ 1)`. ✓
- Set-multilinear (lines 807–809): each monomial contains exactly one variable from every part; task uses `m (i,false) + m (i,true) = 1`. ✓
- Expander (lines 894–895): d-regular and second-largest eigenvalue ≤ `d^{0.75}`; equivalent to `IsExpander G d`’s condition that at most one eigenvalue has absolute value > `d^{3/4}`. For a regular graph the largest eigenvalue is d > `d^{3/4}`; the absolute-value interpretation comes from footnote 5 in [Sri20], omitted when CBFMSY cites it. `2 ≤ d` excludes the empty graph and 1-regular graphs (perfect-matching families), which satisfy the literal spectral condition but not Lemma 2.7.
- Packaging Lemma 2.7 (lines 950–958): induced matching, size `⌈αn⌉`, and cross-edge tail bound `exp(−γm)`; `expanderMatchingProp` matches each item. α and γ depend on degree (`∀ d ≥ 2, ∃ α γ`), based on α ≤ 1/(100·d²) in [Sri20] Lemma 9 and its assumption that d is a sufficiently large constant. A uniform α does not exist (counterexample K_n; see summary item 10).

## Complete list of recorded deviations

1. Circuit model changes from DAGs to tree formulas; lower bounds are only claimed for formulas.
2. Upper-bound constant made explicit as 35; `(e+1)²` absorbs the edgeless graph.
3. Lower-bound asymptotics made explicit using `∃ c,N₀`.
4. Matching lemma packaged as an assumption; its sampling algorithm is not formalized.
5. Expander spectral condition restated as “at most one eigenvalue exceeds the threshold in absolute value” (equivalent); nondegeneracy condition `2 ≤ d`.
6. `mprn` is not defined as an object; c4 uses an existential form, c6 a universal form.
7. c3/c4 require `4 ≤ n` (no balanced partition for n ∈ {1,3}); c5 requires `1 ≤ ℓ`; c2 requires `1 ≤ n`.
8. No abstract ΣΠΣ class is defined; an explicit construction is given.
9. Rectangle elements use ordered pairs of subtype `GraphEdge` rather than the `Sym2` API; mathematics is unchanged.
10. **Repair: matching-lemma constants now depend on degree and expander definition includes nondegeneracy.**
    - Defect: the old `IsExpander` allowed `1 ≤ d`, did not take absolute values in its spectral condition, and `expanderMatchingProp` required uniform α,γ independent of degree.
    - Counterexample (precheck run8-5163-batch5/7046827, bare tier, machine-checked by a model): the perfect matching on 4 vertices (edges 0↔1 and 2↔3) is 1-regular, its adjacency matrix squares to the identity, and all eigenvalues are ±1 ≤ 1 = 1^{3/4}; it was an `IsExpander` under the old definition. But every induced matching has zero crossing edges across the balanced cut `{0,1}|{2,3}`. The event “crossing edges ≤ γ⌈4α⌉” then has probability 1 > exp(−γ⌈4α⌉), so `expanderMatchingProp` was false as stated and the main theorem became vacuous (reward 1).
    - A second degeneration was found: complete graph K_n meets the spectral condition (d=n−1, other eigenvalues −1) but has no induced matching of size ≥ 2. Any uniform α fails for n with αn > 1; adding only `2 ≤ d` does not close this gap.
    - Source basis: footnote 5 in [Sri20], the original source of Lemma 9, specifies “second-largest eigenvalue (in absolute value)”; the main text fixes d as a sufficiently large constant; Lemma 9’s α depends on degree (α ≤ 1/(100·d²)).
    - Repair: `IsExpander` now has explicit degree, requires `2 ≤ d`, and uses absolute values for eigenvalues; `expanderMatchingProp` now states `∀ d ≥ 2, ∃ α γ`; c6 and c7 add the prefix `∀ d ≥ 2`. This matches the paper’s constant-degree expander setting.
    - Probes (real compilation inside the pinned image, `verify-context/probe/`): ProbeA proves the positive fact that pm4 remains regular and meets the spectral condition at d=1 when absolute values are used, while `¬ IsExpander pm4 1` is provable, so the repair excludes it exactly through nondegeneracy. ProbeB shows the old model proof `pm4_isExpander` fails to compile on the obligation `2 ≤ 1`. ProbeC shows the first step of the model’s refutation (destructing the assumption with `obtain`) no longer compiles under the new statement.
11. **Repair: c6 now requires rectangles to be contained in the 1-input support set, and c4 concludes the same property.**
    - Defect: `multipartition_rect_lower` required only that the family of balanced rectangles cover all 1-input supports. It omitted the other half of the mprn definition: their union **equals** the 1-input support set, i.e. every rectangle lies in `fG⁻¹(1)` (equality in `cbfmsy25.txt` lines 796–800; proof of Lemma 2.5 says “for every balanced rectangle R ⊆ fG⁻¹(1)”, lines 942–943). A lower bound for “every cover” is stronger than a bound on mprn and is false as stated.
    - Counterexample (second pass of the repository-wide adversarial falsification sweep, group-7 report): use one “full rectangle” for any balanced split Y⊔Z, with `memLeft = P(Y)` and `memRight = P(Z)`. It contains the support of every assignment, so one rectangle covers all 2ⁿ supports, including 0-inputs; c6 would imply `2^{c·n} ≤ 1`, false for every c > 0. The assumptions are satisfiable: for the Petersen graph (n=10,d=3), powers of the adjacency matrix `trace(A^k)` match the spectrum `{3¹,1⁵,(−2)⁴}`, satisfying `IsExpander G 3`; LPS Ramanujan graphs with d=18 also satisfy it for arbitrarily large n (`2√17 ≈ 8.246 ≤ 18^{3/4} ≈ 8.738`). Bare-tier main theorem c7 is unaffected (part (b) follows directly from Theorem 1.1).
    - Source basis: equality defining mprn at lines 796–800 and the rectangle-containment condition in the proof of Lemma 2.5 at lines 942–943. The c4 proof already establishes containment: members of a rectangle are supports of monomials of `g·h`, and `(g·h).support ⊆ P.support`, the 1-input support set. The paper compares `S₊(P) ≥ mprn(f)`, where mprn includes equality of the cover.
    - Repair: c6 adds `∀ i, ∀ S ∈ (rects i).mem, ∃ a, fG G a = true ∧ suppOf a = S`; c4 adds the same property to its conclusion. Guided and ladder tiers were changed together, with checkpoint statements matching token for token.
    - Probes (real compilation inside the pinned image, `verify-context/probe/`): a static guard checks that the containment text is present in guided/ladder c4 and c6. ProbeD proves the full rectangle on a 4-vertex graph with one edge meets the old coverage assumption but not the new containment condition, so the repair blocks the counterexample. ProbeE proves the full rectangle on the empty graph meets both assumptions, showing the new assumption is inhabited. ProbeF adapts the ProbeE proof to the one-edge graph and fails to compile at the “induced edge count = 0” obligation.
    - Related correction: the guided-tier c5 proof hint “Pr ≤ (3/4)^{ℓ/2} < 2^{−ℓ/2}” is numerically false (`(3/4)^{1/2} ≈ 0.866 > 0.707`). It was changed to “Pr ≤ (2/3)^ℓ < 2^{−ℓ/2}” (for ℓ = 1,2,3, exhaustive enumeration gives maximum mass `(2/3)^ℓ`). This changes only the explanatory hint, not the theorem.
