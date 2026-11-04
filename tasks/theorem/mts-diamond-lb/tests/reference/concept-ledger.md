# Component Crosswalk — lean-mts-diamond-lb (Core Construction from Section 3 of BCR23)

- What this document contains: The core fidelity record for the three-tier lean-mts-diamond-lb task: a point-by-point comparison of checkpoint statements with the paper, a definition crosswalk, all deviations, and a main-theorem assembly check.
- Intended readers: Task authors and reviewers.
- Version checked: arXiv 2211.05753v2 (2023-07-06); full text `bcr23.txt` (line references below refer to this file).

## 1. Numbering crosswalk (checkpoints ↔ paper locations)

| Checkpoint | Name | Paper location | Content |
|---|---|---|---|
| c1 | diamond_construction | §3.1 (lines 425–440) | Recursive construction (M₀ is a unit edge; M_{w+1} consists of 6m_w copies of M_w arranged in a cycle), antipodal choice of s/t (lines 430, 435–436), and point-count bound (line 545: |M_{w+1}| ≤ 6m_w|M_w|; this task uses the exact form 6m_w(|M_w|−1)). |
| c2 | hard_sequence_opt | §3.2 (lines 446–454) | “ρ_w[1] = {s}, ρ_w[T_w] = {t}, and it can be served along a shortest s–t path ⟹ c_opt = d_w(s,t)” (lines 450–452). |
| c3 | stage_one_cost | §3.3, Stage 1 (lines 502–504) | “by induction, the expected cost is simply lower bounded by m_w C_w”. |
| c4 | stage_two_cost | §3.3, Stage 2 (lines 505–519) + §3.5 (lines 561–587) | “the expected cost in this stage is lower bounded by (m_w/2)·C_w”, assuming m_w ≥ C_w; its conditional-expectation gap is repaired by the escape-price argument in §3.5. |
| c5 | binomial_mean_dev | Probability input for Stage 3 in §3.3 (lines 520–523) | The paper cites Berry–Esseen; this task uses the elementary mean absolute deviation form E|S−m/2| ≥ √m/4. |
| c6 | stage_three_cost | §3.3, Stage 3 (lines 520–527) | “expected cost of this stage is (3m_w/2 + Ω(√m_w))·C_w”. |
| c7 | escape_step | Entire §3.5 (lines 561–587) | Inductive lift of the escape-price relaxation: p_w = 2·diam(M_w)·C_w, with accounting inequality (2+3.5m_w)C_w ≤ 6m_w C_{w+1} (lines 583–585). |
| c8 | mss_loglog_lower (main theorem) | §3.4 (lines 531–555) | Recurrence C_{w+1} ≥ (1+Ω(1/√m_w))C_w; choosing m_w = Θ(C_w) gives C_w ≥ Ω(w²); |M_w| ≤ 6^w∏m_{w'} can be inverted to w = Θ(log n/log log n); then “extend M_w arbitrarily to contain exactly n′ points”. |

The reduction between problems in Section 2 (Proposition 8: an MSS lower bound ⟹ MTS/kSRV lower bound) and Yao’s minimax theorem (Theorem 3) are not part of the task. Section 3.6 (the variant with request sets of size ≤ w and LGT’s Ω(w²)) is not included; neither are Sections 4–5.

## 2. Definition-layer crosswalk (definition-layer object ↔ paper object)

| Definition-layer object | Paper object | Comparison |
|---|---|---|
| `DM w`, `ds w`, `dt w` | M_w = (M_w, d_w), special points s,t | M₀ = Bool, a unit edge (d=1); points of M_{w+1} are `Fin (6·m_w) × {x : DM w // x ≠ dt w}`; t in copy i is glued to s in copy i+1, represented by (i+1,s). |
| `cdist`/`legCw`/`legCcw` | Shortest-path metric d_w | Piecewise formula for distances between copies around the cycle (including the direct path within a copy); proof of metric axioms in fixed layer `copiesMetric`; small example E1 checks the formula against graph shortest paths for every pair with w ≤ 2. |
| `swapW` | Left-right reversal symmetry, unnamed in the paper | The other case in Stage 3, “the other case is dealt with by symmetry” (§3, line 484), relies on this symmetry. It is constructed explicitly as a fixed-layer object, and its properties are in c1(v). |
| `copyEmb`/`leftEmb`/`rightEmb` | Notation (S, S′, i, j) (lines 438–440) | rightEmb includes swapW: the local s of the right-path copy points toward the global s. Small examples E5/E6 pin down orientation fidelity: reversing it makes c_opt > d(s,t). |
| `Om w`, `hardSeq` | Distribution of random request sequence ρ_w | Ω₀ is a singleton; Ω_{w+1} = (Ω_w)^{m_w} × (Ω_w)^{m_w} × (Ω_w)^{2m_w} × {0,1}^{m_w}; expectation is a uniform average; ε_i are Bernoulli(1/2). The paper’s §3.2 omits this parameter, which is supplied from the introduction and §3.3’s “with probability 1/2”; an independent retranslation reached the same reading. |
| `stage1Seq`/`stage2Seq`/`stage3Seq` | Three stage formulas (lines 457–458, 462–479, 484–489) | Checked formula by formula: Stage 1 uses the same ρ_{w,i} on both sides (lines 457–458); Stage 2 uses left(i)/right(i) and the ε_i branches (lines 462–463, 479); Stage 3 uses (∅, S, 1, right(m_w)+i) (line 486). |
| Padding segment | “we can always pad a sequence with some dummy sets to attain a fixed length” (lines 447–449) | Set T_{w+1} = 4·m_w·T_w and pad with {t}; padding follows the final request {t}, so it changes neither the optimum nor any lower bound. Independent retranslation reached the same choice. |
| `DetAlg`/`costAux`/`endPos` | “response function alg maps every request sequence to an action” (lines 199–202) | Online behavior is guaranteed by the type (a response sees only the history); feasibility (response belongs to the request set) is a structure field. |
| `optCost` | c_opt(ρ) = min_alg c_alg(ρ) (line 206) | Dynamic-programming recursion by position; auxiliary lemmas such as `optCost_ge_dist` support the decomposition of the trajectory minimum. |
| `EscAlg`/`escCost`/`EscLB` | Escape-price relaxation (lines 237–244) and p_w = 2·diam(M_w)·C_w (line 574) | Stopping incurs cost on that step and all later steps for free (directly matches lines 241–244); escape price is available at any time (throughout this construction’s sequence, as in the paper). |
| `DistLB` | Finite-witness form of Definition 2 (lines 217–222) | See Deviations 4 and 5. |
| `ExtSpace`/`extMetric` | “extend M_w arbitrarily to contain exactly n′ points (the extra points will be ignored in the request sequence)” (lines 552–554) | Every new point is at distance D_w from M_w and 2D_w from other new points. Feasibility keeps the algorithm within request sets (subsets of M_w), so the lower bound transfers directly. |
| `Cseq`/`mseq`/`gamma0` | Parameter choices and constants in §3.4 (lines 537–541) | γ₀ = 1/4 (from the elementary c5 bound); C₀ = 1; m_w = ⌈C_w⌉₊; C_{w+1} = C_w·(1 + γ₀/(3·√m_w)). |

## 3. Deviation list (all intentional differences from the paper)

1. **No scaling:** Starting in §3.3, the paper scales each copy of M_w in M_{w+1} to diameter 1 (lines 495–496). This task does not scale; it carries D_w throughout (`DD w`). Lower bounds in c3/c4/c6 are multiplied by DD w. Cross-check: the scaled form (3m_w + Ω(√m_w))·C_w becomes (3m_w + Ω(√m_w))·C_w·D_w without scaling, consistently at each stage: Stage 1 m_w·C_w → m_w·C_w·D_w; Stage 2 (m_w/2)·C_w → ·D_w; Stage 3 (3m_w/2+Ω(√m_w))·C_w → ·D_w.
2. **Asymptotic notation is made explicit:** Berry–Esseen is replaced by the elementary c5 proposition (constant 1/4, with the closed form and bound numerically checked for m = 1..60 in small example E8); Ω(w²) becomes an explicit ∃a > 0 ∀w ≥ 1 form (the c8 proof uses a = (γ₀/(12√2))² = 1/2592; small example E9 checks values for 1 ≤ w ≤ 200 and the point-count inversion); the main theorem’s Ω((log n/log log n)²) becomes ∃c > 0 ∃n₀ ∀n ≥ n₀.
3. **Fixed-length padding:** The paper says to ignore the random sequence length “for simplicity”; this task pads with {t} to T_{w+1} = 4·m_w·T_w. The Stage 3 block count is at most 2m_w (min(l,r) ≥ m_w because r = 2m_w − s ≥ m_w iff s ≤ m_w), so total length is always at most 4m_wT_w.
4. **Distributional form of the main theorem:** The main theorem takes the witness form “there exists a hard distribution” (for every deterministic algorithm, E[c_alg] ≥ C·E[c_opt]); this is the form actually delivered by the paper’s proof, on the input side of Yao’s minimax theorem. Definitions 1/2 and Theorem 3 are not formalized.
5. **The κ bookkeeping is retained:** Definition 2 universally quantifies an additive constant κ, and Section 3 gives no argument to eliminate it (independent retranslation reached the same result); the distributional form of this task has no κ.
6. **swapW is explicit:** The paper dispatches the Stage 3 case with “by symmetry.” This task defines the symmetry as the fixed-layer map `swapW` (an involution reversing direction), with endpoint exchange, involution, and isometry properties in c1(v).
7. **Orientation of the right path:** rightEmb = copy embedding ∘ swapW (the local s of the copy faces the global s). Small examples confirm that reversing the orientation makes c_opt strictly greater than d(s,t) (initial version failed at E6); the paper’s (S,S′,i,j) notation presupposes this orientation.
8. **c_opt uses an equality form:** The paper says “c_opt(ρ_w) is simply the length of this path.” c2 states equality for each realization (ω: optCost = DD w); the lower bound follows from the triangle inequality, and the upper bound from clearing the surviving path (an inductive construction that knows ε offline).

## 4. Main-theorem assembly check (step-by-step accounting for c8 from c1–c7)

1. Base case EscLB 0 1: DM 0 is a unit edge, ρ₀ = [{s},{t}]. A non-stopping algorithm pays d(s,t) = 1 = 1·DD 0; stopping costs p₀ = 2·1·1 = 2 ≥ 1. ✓
2. Induction: c7 (`EscLB w (Cseq w) ⟹ EscLB (w+1) (Cseq (w+1))`); its premise m_w ≥ C_w follows from the definition-layer equation mseq = ⌈Cseq⌉₊ (`Nat.le_ceil`). ✓ Hence ∀w, EscLB w (Cseq w).
3. Solve the recurrence: m_w ≤ C_w + 1 ≤ 2C_w (C_w ≥ 1, definition-layer lemma Cseq_ge_one) ⟹ C_{w+1} ≥ C_w + (γ₀/(3√2))·√C_w ⟹ by induction C_w ≥ a·w², where a ≤ (γ₀/(3√2)/3)² = 1/2592 (base C₁ = 1 + γ₀/3 ≥ a). Also √(C_{w+1}) − √C_w ≤ γ₀/6 ⟹ √C_w ≤ 1 + γ₀w/6, used for the point-count bound.
4. Point count: |M₀| = 2, |M_{w+1}| = 6m_w(|M_w|−1) (c1(iii)) ⟹ |M_w| ≤ 2·6^w·∏_{w′<w}m_{w′} ≤ 2·12^w·(1+w/24)²ʷ-ish ⟹ log₂|M_w| ≤ 2w·log₂w for w ≥ 48 (numerical window checked in small example E9).
5. Invert: for given n ≥ n₀, take w = max{w : |M_w| ≤ n} (exists because |M_w| strictly increases and is unbounded). Since |M_{w+1}| > n, log₂ n < 2(w+1)log₂(w+1) ⟹ w ≥ c′·log₂ n/log₂log₂ n (with an explicit c′ available).
6. Extend: ExtSpace (r = n − |M_w|) + extMetric (hD = DD_pos, hDiam from c1(i)); map each set in the request sequence into the extension using Sum.inl. Feasibility implies every algorithm position stays in M_w, so its cost agrees with projection; optCost agrees in both directions, so DistLB transfers. The constant C_w ≥ a·w² ≥ a·(c′ log₂n/log₂log₂n)²; take c = a·c′²/2-ish.
7. The two DistLB side conditions: each request set is nonempty (c2(i)) and E[opt] > 0 (c2(iv): E[opt] = DD w ≥ DD 0 = 1 > 0). ✓

## 5. Premise-by-premise check for each checkpoint

- The EscLB w (Cseq w) premises of c3/c4/c6 match the conclusion of c7, EscLB (w+1) (Cseq (w+1)), and match the c8 induction instance C = Cseq w. In `EscLB`, the escape price 2·C·DD w agrees with the paper’s p_w = 2·diam·C_w (diam = DD w by c1(i)+(ii)).
- The implicit premise m_w ≥ C_w for c4 is built into the definition layer (mseq = ⌈Cseq⌉₊), and is stated in the checkpoint card and guided docstring. The escape comparison (2m_w+1)·D_w ≥ 2·C_w·D_w follows from m_w ≥ C_w.
- c5’s premise 1 ≤ m holds at its call site, where m = m_w ≥ 1 (`mseq_pos`). ✓
- c6’s γ₀·√m_w follows from c5’s γ₀ = 1/4 and the block-count identity for the expected value 3m_w/2 + E|S − m_w/2|. ✓ (closed form in small example E8).
- c8’s dependencies: c1(i)+(iii), c2, c7, c5 (through c6 and c7) are all in the chain; no cycle.

## 6. SOP 6.5 error-pattern self-check (itemized answers)

1. **Are existential outputs constrained?** c8’s output is a four-tuple (metric space, start point, sample space, request-sequence distribution), tied to the inputs by the body of `DistLB`: each request set is nonempty, E[c_opt] > 0, and every deterministic algorithm has E[c_alg] ≥ C·E[c_opt]. Degenerate examples checked: a singleton space (excluded by n ≥ n₀ ≥ 2); the all-empty sequence (excluded by E[c_opt] > 0—without it, any C would “work,” a degenerate case like hdx-pcp); c = 0 (excluded by 0 < c). Constraints are all present.
2. **Degenerate parameters:** c1–c2 were checked individually at w = 0 (M₀ is a unit edge: antipodality 1 ≤ 1, recurrence DD 1 = 3·1·1, cardinality 6·(2−1)=6, and ρ₀=[{s},{t}] has the correct endpoints, nonempty requests, and optCost = 1, all directly). c3/c4/c6 have EscLB 0 1 as a true premise (base case). c5 includes 1 ≤ m, and at the call site m = m_w ≥ 1. c8’s n ≥ n₀ avoids the singularity in log₂log₂n (n₀ can be chosen large, e.g. on the order of 2^16, as the proof requires).
3. **Are the main-theorem premises at least as strong as the premises required at each checkpoint call?** c7 invokes c3/c4/c6 with premises EscLB w (Cseq w), exactly matching c7’s premise; c8 invokes c7 with the same form. c6 invokes c5 at m := mseq w, satisfying 1 ≤ m by the definition-layer lemma mseq_pos. c8 invokes c1(i) for hDiam, c1(iii) for cardinality, and c2 for DistLB side conditions; c1/c2 have no premises. No checkpoint premise is omitted by the main theorem.
4. **Are substitution and evaluation points consistent?** The Stage 2 request index ε_i·j + (1−ε_i)·T_w (1-indexed) translates to reqAt’s j.val and Tseq w − 1 (0-indexed), matching line 479 point for point; small examples E5/E6 pin it down numerically (first/last entries and c_opt are exact on all small samples). No statement comes from an unproved upstream draft.
5. **Are base cases present?** c5 includes 1 ≤ m; c7’s induction base EscLB 0 1 is a proof obligation and is stated in the guided docstring; c1’s base w = 0 is direct.
6. **Were both directions and off-by-one boundaries checked?** The (m_w/2) factor in c4 is cross-checked against the §3.5 accounting “m_w C_w/2 for stage 2”; c6’s 3m_w/2 + γ₀√m_w matches the block-count identity 3m_w/2 + |S − m_w/2| numerically (E8). The Stage 3 copy range right(m_w)+1 .. 3m_w (paper line 486) maps to the 0-indexed expression rt + (i.val+1), for i < 3m − rt. ✓
7. **Weakening and vacuous truth:** c8’s explicit-constant form is stronger than the paper’s Ω form (∃c > 0 is what Ω states); there is no result weaker than the paper’s. EscLB w C is inhabited at C = Cseq w (base case and c7 induction), so its premise is not impossible; DistLB’s combined premises are satisfied by c2.

## 7. Follow-ups and risks

- The non-rigorous step acknowledged by the paper in §3.3 (Stage 2 conditional expectation) is repaired in this task by the escape-price induction hypothesis. The Stage 1 comparison between the two sides (actual cost ≥ induced cost) has also been supplied in the authoring analysis (pointwise triangle inequality on both sides of the same implementation) and recorded in the guided docstring.
- The expansion |M_{w+1}| ≤ 6^w∏_{w′=1}^{w}m_{w′} in §3.4 of the paper is looser than the exact recurrence by a factor at most 6m₀. This task’s c1(iii) uses the exact form (tighter and equal to the true count in the construction).
- A formal equivalence between the κ-form in Definition 2 and the witness form used here (requires an LP/minimax argument) has not been formalized; it belongs to the reduction layer in Section 2, outside scope.

## Statement requirements

- Root cause: `DetAlg.next_mem` was originally `∀ hist S, next hist S ∈ S`, requiring the response to belong to even an empty request set. The empty set has no elements, so `DetAlg` was uninhabited and the universal quantifiers “∀ A : DetAlg” in `DistLB` and all three stage_cost checkpoints were vacuously true. Two independent reviews confirmed this: an old full-credit submission proved the main theorem in one line with `detAlg_absurd` (take `A.next_mem [] ∅` to get `next [] ∅ ∈ ∅`, and simp derives False), making that full score invalid.
- Fix: make the same one-line change in all three tiers: `next_mem : ∀ hist S, S.Nonempty → next hist S ∈ S`. Require a response to belong to the request set only when it is nonempty, matching the paper’s online-algorithm definition and the convention `∀ S ∈ ρ ω, S.Nonempty` in `DistLB`. `EscAlg.next_mem` in the same file (`∀ hist S x, next hist S = some x → x ∈ S`) was already correct and was not changed. There are no other uses of `next_mem` in the definition layer or checkpoint statements, so no follow-up edits were needed. No byte in the statement region changed apart from this line; app and tests/reference were synchronized verbatim.
- Compilation evidence (independent validation environment, Lean 4.33.0 image, pinned mathlib 5b3f719 full build): `lake build Task` passed under the new definition layer in all three tiers (BUILD_RAW_EXIT=0 for each; “Build completed successfully (8691 jobs)”).
- Inhabitation proof: probes `stage-{guided,ladder,bare}/Probe.lean` construct `next := fun _ S => if h : S.Nonempty then Classical.choose h else start`. `next_mem` follows from `dif_pos` and `Classical.choose_spec`; they also prove `Nonempty (DetAlg M start)` and the singleton-request behavior (the response is exactly the requested point, so the feasibility field is genuinely used). All three PROBE_RAW_EXIT=0: `DetAlg` is inhabited, so “∀ A : DetAlg” is no longer vacuous.
