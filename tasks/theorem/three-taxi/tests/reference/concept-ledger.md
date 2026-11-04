# Component Crosswalk — lean-three-taxi (Coester–Poon 3-Taxi)

- What this document contains: A crosswalk of the eight checkpoints and definition layer in lean-three-taxi with the source, a deviation list, key calculations, and the SOP 6.5 self-check.
- Intended readers: Task authors and reviewers.
- Version checked: arXiv 2510.25861v1 (2025-10-29); full text is in `paper.txt`.

## 1. Checkpoint crosswalk

Each row pairs a checkpoint with its paper reference and the corresponding Lean object in this task.

| Checkpoint | Lean theorem | Paper reference | Paper content |
|---|---|---|---|
| c1 | tripod_edge_perturbation | Lemma 2.1 | The change in a corresponding edge length is at most w₁w₂ (the three edges u, v, w). |
| c2 | interval_invariant | Claim 3.1 | The interval order x₂→q₂→q₃→x₃ is preserved iff ℓ₂+ℓ₃ ≤ x₂x₃ (movement phase + reorganization, lines 17–18). |
| c3 | min_matching_characterization | Lemma 3.2 | Pairing x₂ with ŷ and x₃ with y is no worse iff x₂ĝ ≤ x₂g. |
| c4 | offline_phase_potential | Lemma 3.3 | In the offline movement phase, ∆Φ ≤ α·OPT_t. |
| c5 | rate_lemma | Lemma 3.5 | The rates of change of x₂g, x₃g, yg are (±p±q±r)/2 of the rates of change of the three distances. |
| c6 | online_movement_nonpositive | Corollary 3.6 + Claim 3.4 | When the offline move serves a passive taxi, the online movement phase satisfies COST + ∆Φ ≤ 0. |
| c7 | reorg_phase_potential | Lemmas 3.7, 3.8, 3.11 | Reorganization gives ∆Σ ≤ 0 and ∆M ≤ ψ·OPT_t; reset gives ∆Φ ≤ 0. |
| c8 | tripod_tracker_competitive | Theorem 3.12 (= Theorem 1.1) | TripodTracker is κ-competitive. |

Paper content not included: Background and related work in Section 1 (no propositions); intuition paragraph in §3.2 (no numbered proposition); Claims 3.9/3.10 (proof details for c7); Figures 2/3/4 (examples); discussion for k > 3 in Section 4 (open problem, no proved proposition); Appendix A (examples). The three edges in Lemma 2.1 correspond to the paper’s “any two corresponding edges (sharing the same endpoint u or v, and likewise the edges w₁h₁ and w₂h₂).”

## 2. Definition-layer crosswalk

| Paper object | Lean object | Comparison |
|---|---|---|
| Metric space (S,d) | `dist` plus three axioms in class `TaxiMetric` | Only distance axioms are used (a pseudometric; d=0 does not imply equality of points). Since paper statements concern only distances, this loses no content. |
| Bridge B(x,y) (isometric to an interval) | `TaxiMetric.bridge`: ∀ 0 ≤ t ≤ d(x,y), ∃ p, d(x,p)=t ∧ d(p,y)=d(x,y)−t | Direct translation of the WLOG reduction in Section 2 (add virtual points); an isometric interval implies intermediate points, which is the direction used. The converse (intermediate points imply an isometric interval) is unnecessary. |
| Tripod B(x,y,z) and center e | `TaxiMetric.tripod`: ∃ e, with three arm lengths given by Equation (1) | Equation (1) is `tripodC`; identities such as xe+ye=xy follow from `tripodC_edge_sum`/`tripodC_path` (algebraic identities). |
| Arm-length formula (1) | `tripodC dxy dxz dyz = (dxy+dxz−dyz)/2` | Direct match. |
| Active/passive taxi, x₁/x₂/x₃, y₁/y₂/y₃ | Fields of `FState` | Direct match; reindexing is implemented by `reorgPhase`/`reorgApply`. |
| Interval lengths ℓ₂, ℓ₃ (qᵢ defined by ℓᵢ = xᵢqᵢ) | `OState.ℓ2 ℓ3` | qᵢ is not represented separately. Every location using qᵢ (q₂q₃ in Σ, and the integral breakpoints ℓᵢ) is rewritten using ℓᵢ and distances. |
| Integral ∫_{Pᵢ} fᵢ dz | `distContrib dd dxy djy ℓi = dxy − ψ·(min ℓi (tripodC dd dxy djy) + tripodC dxy djy dd)` | f takes only 1 and 1−ψ, so the integral is full length minus ψ times the discounted segment length. The discounted part is [xᵢ,min(ℓᵢ,xᵢg)] when ℓᵢ < xᵢg, plus the full y-arm. If min(ℓᵢ,xᵢg) ≥ xᵢg, the whole path is discounted, giving (1−ψ)dxy; the unified expression agrees because min = xᵢg and xᵢg + yg = dxy. |
| M = x₁y₁ + ∫f₂ + ∫f₃ (minimum matching) | `Mpot = x1y1 + min (matchSum pairing 2-2, 3-3) (matchSum pairing 2-3, 3-2)` | The active pair is forced (paper: “The active online taxi x₁ will always be matched to the active offline taxi”). The passive pair takes the minimum of two matchings. |
| Σ = max(0, min(ℓ₂,ℓ₃) − q₂q₃) | `SigmaPot dd ℓ2 ℓ3 = max 0 (min ℓ2 ℓ3 − (dd − ℓ2 − ℓ3))` | q₂q₃ = dd − ℓ₂ − ℓ₃ under the order x₂→q₂→q₃→x₃; c2 ensures the invariant makes this nonnegative. |
| Φ = αM + βΣ | `Phi` | Direct match. |
| Constants a ≪ b ≪ ψ ≪ 1 ≪ αa ≪ β ≪ αb (Equation (3)) | `cA=10⁻⁴, cB=10⁻², cPsi=10⁻¹, cBeta=10², cAlpha=10⁵` | Instance ε=1/10 of the family in footnote 2: a=ε⁴, b=ε², ψ=ε, β=ε⁻², α=ε⁻⁵. Equation (3) and Equation (6), αa≪β≪αb≪αψ≪α, hold numerically: 10<100<10³<10⁴<10⁵. |
| Algorithm 1 lines 6–14 (movement phase) | `movePhase` (explicit piecewise function) | Branch-by-branch translation is in Deviation 4 and the calculations in Section 4. |
| Algorithm 1 lines 15–20 (reorganization) | `reorgPhase` | Direct match: server=2 (x₃ moves to r) is the printed branch; server=1 is the stated symmetric branch. |
| Line 21 (serve/reset) | `serveOnly` (x₁,y₁ → s) | Free in the hard-instance version. ✓ |
| Cost COST = Σ d(C_{t−1}, Ĉ_t) | `runTrj` accumulating `s1+s2+s3` (third output of `onlineMove`) | See Deviation 6. |
| OPT | `runTrj` accumulating `dist (yjOf st j) r` (offline movement distance for each request) | See Deviation 7. |
| ρ-competitive (COST ≤ ρ·OPT + c) | c8: ∃ κ>0, COST ≤ κ·OPT (c=0) | See Deviation 8. |

## 3. Deviation list

1. **Distance-level formalization:** path integrals become explicit min expressions (row 7 of the crosswalk); rates become endpoint increments (c6/c7); Lemma 3.5 becomes affine-substitution equalities (c5). These are equivalent reformulations (the integrand is binary-valued, endpoint rates are piecewise constant, and Lemma 3.5 itself says “follows from (1)”).
2. **Axiomatized metric layer:** `TaxiMetric` = distance axioms + bridge assumption + tripod assumption, directly translating the two WLOG reductions in Section 2. The “remove virtual points” reduction (the paragraph on deferring movement) is not formalized. The main theorem is stated directly for spaces satisfying both assumptions, one reduction step weaker than Theorem 1.1 in the paper, which concerns arbitrary metric spaces; that reduction is argued in two prose paragraphs in the paper, not in the lemma chain.
3. **Instantiate constants at ε=1/10:** the paper allows any constants satisfying the hierarchy; κ remains existential (the paper says “sufficiently large κ”). The sufficient scale tracked for κ in this task: the coarse-bound branch needs κ ≥ (1+α+β)(a+2+2b)/a ≈ 2×10⁹; the main branch needs κ ≥ α + αψ. Thus κ = (1+α+β)(a+2+2b)/a + α(1+ψ) suffices (the c8 proof sketch uses the same expression).
4. **Movement phase made an explicit piecewise function:** `movePhase` compiles the continuous process in Algorithm 1 into at most four affine segments. Event-chain derivation: in case B (both passive taxis unobstructed), each passive taxi evolves independently (`passiveB`). If ℓᵢ < xᵢe, there is first a constant-speed segment (xᵢ and qᵢ both move at speed 1, ℓ is unchanged) until qᵢ reaches e, after time xᵢe−ℓᵢ; it then moves fast (speed 1+b), qᵢ stays at e, and ℓᵢ falls to 0 from xᵢe at the same rate. If ℓᵢ ≥ xᵢe, it moves fast immediately (if qᵢ is already past e it returns at speed 1, with ℓ rate −(2+b); if xᵢ reaches e first, the remaining ℓ is L₀−(2+b)·U, otherwise qᵢ returns and then ℓ=xᵢe). U, the time to e, is xᵢe/(1+b) when ℓ ≥ xᵢe, and (xᵢe−ℓ)+ℓ/(1+b) otherwise. Case B ends at min(d1/a, U2, U3); if Uᵢ is the minimum, enter case A (that taxi continues toward r at speed 1, q returns at relative rate 2, and ℓ decreases at rate −2, clipped at 0; the other taxi is frozen). Case A ends at min(d1′/a, er). The first taxi to reach r is the server. The example trajectory in Appendix A agrees segment by segment with this definition (checked in small example E3).
5. **Corollary 3.6 is not a separate checkpoint:** the source statement concerns “the matching contribution of x_j.” The matching is chosen by a minimum, and it switches while crossing the critical point xⱼg = xⱼe (the equality case in Lemma 3.2), so the object whose “contribution” is measured changes during the segment. Numerical analysis by the task authors (small example E10, exact fractions): take dd = 15.005, xᵢe = 10, xⱼe = 5.005, xⱼg = 5 (critical case xᵢe ≤ xᵢg, matching premise holds), ℓⱼ = 6, gy = 1, τ = 0.5, ci = 1, cⱼ = 1+b. The segment is valid throughout (fast condition ℓⱼ ≥ u remains true); the increment rate of a fixed-pairing contribution is exactly 0.910, strictly above the paper’s bound cⱼ(1−ψ) = 0.909 (after ℓⱼ falls below xⱼg, the term −ψ∆min becomes positive). **Therefore, the endpoint statement for a fixed pairing is false literally.** The paper’s instantaneous-rate argument (“positive in the undiscounted region ⟹ xⱼqⱼ < xⱼg ≤ xⱼe ⟹ constant speed ⟹ ℓ unchanged”) uses the current minimum matching. Its rate bound holds at every instant, and after integrating across switching points, it agrees with the composition used in Claim 3.4 (E10d: after switching, the contribution paired with r falls, so the min-form does not increase). Thus this corollary is proof content for c6; c6 states only the endpoint form of Claim 3.4.
6. **Online cost:** Section 2 defines cost as Σ d(C_{t−1}, Ĉ_t) (the minimum matching distance), while the analysis (proof of Claim 3.4) uses COST′ = sum of taxi speeds. The trajectory semantics use the latter (Σ sᵢ ≥ matching distance), which is stronger and matches the analysis.
7. **Offline-side model:** WLOG, exactly one taxi moves to r per request (the paper’s §3.4.1: “delaying any other movements to a later request does not increase its overall cost”). The main theorem bounds every offline choice sequence, hence also the optimal offline algorithm. The offline active taxi is at r in the trajectory (an invariant maintained by the serving step in `serveRequest`).
8. **Additive constant c = 0:** the online and offline configurations initially coincide and ℓ = 0, so Φ₀ = 0 (`phi_init`, proved in the definition layer).
9. **Generalized c4 statement:** `offline_phase_potential` is stated for any replacement y_j ↦ y′ (the paper uses only moving to r), with conclusion ∆Φ ≤ α·d(y_j,y′). Proof content is unchanged; the stronger statement covers the use site.
10. **Fix k = 3:** degenerate cases such as two taxis at the same point (dd = 0) are handled naturally by the definition’s branches (when u₂=u₃=0, it uses moveA2), matching the paper’s “regard one of them as unobstructed, chosen arbitrarily.”

## 4. Key calculations

### 4.1 Pairwise contribution Lipschitz bound in c4 (validity of the literal Lemma 3.3 bound)

The paper gives only one sentence: “since M is a weighted sum of distances of the minimal matching where the weights are all no greater than 1”. The weights change as g moves, so a rigorous version must track them. Let the contribution of a passive pair be C = A − ψ(min(ℓ,B) + D), where A = d(xᵢ,y), B = xᵢg = (dd+A−F)/2, D = yg = (A+F−dd)/2, and F = d(xⱼ,y). If y moves by δ, then |∆A| ≤ δ, |∆F| ≤ δ, ∆B = (∆A−∆F)/2, and ∆D = (∆A+∆F)/2. The min is 1-Lipschitz in B and ℓ is fixed: −ψ∆min ≤ ψ·(−∆B)⁺. Thus ∆C ≤ ∆A + ψ(−∆B)⁺ + ψ(−∆D)⁺. The identity (−∆B)⁺ + (−∆D)⁺ ≤ max((−∆A)⁺, |∆F|) is used as follows. If ∆A ≥ 0, refining the two positive-part terms gives ∆C ≤ ∆A + ψ(δ−∆A)⁺ ≤ max(δ,(1−ψ)δ+ψδ) = δ. If ∆A < 0, then ∆C ≤ 0 + ψ·2δ/2? More directly, (−∆B)⁺+(−∆D)⁺ ≤ (−∆A)⁺+|∆F| ≤ δ+δ, together with |∆A| ≤ δ gives ∆C ≤ ∆A + ψ((−∆A)⁺+δ) ≤ 2ψδ; since ψ < 1/2, this is ≤ δ. For the minimum matching, ∆M is at most the maximum increment over the two matching sums. Each matching contains only one contribution involving y_j, so its increment is at most δ when j≠0; when j=0, the active term is at most δ and the min term is unchanged. Therefore ∆M ≤ δ, matching the paper’s literal claim. ∆Σ = 0 by definition (Σ does not involve y).
(Derived by the task authors; small example E9 randomly scanned 10⁵ numerical cases and confirmed ∆C ≤ δ.)

### 4.2 Mixed cases in Lemma 3.2 (unconditionality of c3)

The difference matchA − matchB (A pairs x₂ with ŷ and x₃ with y; B uses the crossed pairing) has four cases based on ℓ₂ relative to x₂g and x₂ĝ. If both are fully discounted (ℓ₂ ≥ max), the x₂-side difference is (1−ψ)(x₂g−x₂ĝ + gy−ĝŷ). If both are undiscounted (ℓ₂ ≤ min), it is (x₂g−x₂ĝ) + (1−ψ)(gy−ĝŷ). The x₃-side is symmetric with opposite sign; the gy−ĝŷ terms cancel on the two sides; and x₃g = dd−x₂g, x₃ĝ = dd−x₂ĝ. Thus the total is 2(x₂g−x₂ĝ) in the fully undiscounted case and 2(1−ψ)(x₂g−x₂ĝ) in the fully discounted case, with sign sign(x₂g−x₂ĝ). In a mixed case, for example x₂ĝ ≤ ℓ₂ ≤ x₂g, the difference is 2(x₂g−x₂ĝ) − ψ(ℓ₂−x₂ĝ) + ψ(ℓ₃−x₃ĝ) ≥ (2−ψ)(x₂g−x₂ĝ), using ℓ₂−x₂ĝ ≤ x₂g−x₂ĝ and ℓ₃−x₃ĝ ≥ 0 (the latter follows by checking the symmetric condition x₃ĝ ≤ x₃g iff x₂g ≤ x₂ĝ). The task authors checked the signs in all four combinations; each agrees with x₂g−x₂ĝ (small example E8 scanned a grid of ℓ values). Thus the iff is unconditional, and c3 matches the paper (it adds only nonnegative tripod arm lengths as premises).

### 4.3 Constants in case (d) of c7 (final part of Lemma 3.8)

The online passive x₃ serves, while offline active y₁ serves: OPT_t = d(y₁,r). Compare the new pair (x₃new = old x₁, y₃new = old y₁) with the old pair (x₃, y₃): its distance increases by at most x₁x₃ (triangle inequality); the x₁ arm of the new tripod B(x₂,x₁,y₃) differs from the old x₃ arm by at most x₁x₃ (use of c1), so contribution increases by at most x₁x₃ (worst case, fully undiscounted) + ψ·x₁x₃ (line 18 reduces ℓ₃ and shortens the discounted part by at most x₁x₃), totaling (1+ψ)x₁x₃. The old pair (x₁,r) contributes x₁x₃ and is removed, so net ∆M ≤ ψ·x₁x₃ = ψ·x₁r ≤ ψ·d(y₁,r) = ψ·OPT_t (premise hx1r). ✓ Matches the paper.

### 4.4 c6 combined constant (three subcases in Claim 3.4)

Rate composition (COST′ ≤ a + 2(1+b), contribution from x₁ is +αa):
- Subcase 1 (xᵢqᵢ < xᵢe): M′ ≤ −1 + (1+b)(1−ψ) + a = −ψ + b − bψ + a; Φ′ ≤ α(−ψ+b+a) + 2β + (a+2+2b). Numerically αψ = 10⁴, αb = 10³, αa = 10, 2β = 200, cost ≤ 2.02+10⁻⁴: −10⁴+10³+10+200+2.03 < 0. ✓
- Subcase 2: M′ ≤ −(1+b)(1−ψ) + (1−ψ) + a = −b(1−ψ) + a; Φ′ ≤ α(−b+bψ+a) + 2β + cost: −10³+100+10+200+2.03 < 0. ✓
- Subcase 3: M′ ≤ −(1+b)(1−ψ) + (1+b)(1−ψ) + a = a; Σ′ = −(1+b); Φ′ ≤ αa − β(1+b) + cost = 10 − 101 + 2.03 < 0. ✓
- Single unobstructed taxi: M′ ≤ −c + a (c ≥ 1), so Φ′ ≤ −α(1−a) + 2β? Here Σ′ ≤ 0 (the paper does not state a Σ bound for this case—the paper says “In all movement cases with two unobstructed passive taxis, we have Σ′ ≤ 2”; here ℓ does not increase (case A rate ≤ 0 or frozen), so Σ does not increase and Σ′ ≤ 0). Thus Φ′ ≤ α(−1+a) + 0 + cost ≤ −10⁵+10+2.03 < 0. ✓
All four branch inequalities hold numerically (at linarith level). Endpoint conversion: there are finitely many segments (≤ 4); multiply each rate bound by segment length and sum to obtain the endpoint increment bound. ✓

### 4.5 SOP 6.5 item 3: premises at main-theorem call sites

Sources of the premises for each checkpoint used in the c8 proof: the three c6 invariants are (i) ℓ ≥ 0, maintained along the trajectory by definition-layer `serveRequest_ℓ_nonneg`; (ii) ℓ₂+ℓ₃ ≤ x₂x₃, maintained for every request by c2 (initially 0 ≤ dd); (iii) d(x₁,y₁) = 0, maintained by the serving step in `serveRequest` (after service, x₁ = y₁ = s; initially equal). ✓ The c7 premise hx1r follows from `onlineMove_x1_traveled` (d(x₁′,r) = d1 − s1 ≤ d1) and hxy. ✓ c4 has no such premise. ✓ c2 follows by induction. ✓

## 5. SOP 6.5 systematic error-pattern self-check

1. **Are existential outputs constrained?** c8’s output κ is constrained by COST ≤ κ·OPT. ✓ No other existential output occurs (tripod center e, etc. is in the axioms and not in the conclusion).
2. **Degenerate parameters:** empty request list ⟹ COST = OPT = 0, so 0 ≤ κ·0. ✓ dd = 0 ⟹ u₂ = u₃ = 0 and moveA2 is used. ✓ d1 = 0 (x₁ = r) ⟹ T1 = 0, server = 0, cost 0. ✓ er = 0 ⟹ reaching e also reaches r. ✓ Initially all points coincide ⟹ Φ = 0 (`phi_init` covers it). ✓
3. **Main-theorem premises cover checkpoint premises:** see Section 4.5.
4. **Substitution consistent:** no series or translation is involved; the tripod formula matches Equation (1) point for point (the `tripodC` definition is checked against (xy+xz−yz)/2 in the source).
5. **Base case:** trajectory induction starts from the empty sequence (COST = OPT = 0). ✓ c5 is an affine substitution and has no induction.
6. **Both sides / boundaries:** the invariant is two-sided (0 ≤ ℓ by definition layer; ℓ₂+ℓ₃ ≤ dd by c2). ✓ Lemma 3.2 is an iff in both directions. ✓ Mixed case checked in Section 4.2.
7. **Weakening and vacuous truth:** c8 quantifies over all trajectories and `runTrj` is total (defined for every input), with `serveRequest_ℓ_nonneg` supporting legal point selection, so the statement is not vacuous. ✓ The conclusion is not weakened (the paper itself gives ∃κ); c6 premises are not too strong (all reachable states satisfy them).
8. **Grading side:** checkpoint statements contain no `:=` (guard in consistency.py); the problem statement’s grading rules match score.py exactly. The problem explicitly says “comment-stripped lexical scan” is not discussed—`instruction.md` says “rejected by a lexical scan,” and the grader actually strips comments first. The statement does not promise to scan raw text, so there is no conflict; this is the same wording as the template task.

## 6. Remaining risks (recorded explicitly)

- The branch-composition inequalities in c6/c7 are tracked in rate form by the task authors (Sections 4.3/4.4); connecting endpoint values by summing piecewise segments is part of the model’s proof obligation. If any branch constant failed, the model would get stuck at c6; each was checked numerically in 4.4, so risk is low.
- In case B of `movePhase`, a tie such as T1=U2 assigns server=0. The paper does not specify tie-breaking; it does not affect the analysis because both interpretations have the same cost at that instant. Appendix A’s example has no tie.
- The paper’s “without loss of generality” for the offline side (move only one taxi, move the offline taxi first) is accepted from its prose argument (Deviation 7); formalizing that argument is outside the checkpoints.

## Common-tripod constraint repair for online movement

- What this records: the repair of false statements in c8 and c6 by adding the common-tripod constraint to onlineMove.
- Cross-check: §3.1, §3.3, and line 10 of Algorithm 1 in arXiv 2510.25861v1 explicitly move passive taxis along the common tripod B(x₂,x₃,r); the paper has no defect. Our onlineMove used Classical.choose to select a point on an arbitrary bridge and had dropped the constraint (the ledger omitted this deviation, and the guided problem statement already said “along the tripod”; the code had fallen behind the statement).
- The current `onlineMove` chooses the same center `tripodCenter x2 x3 r` and constrains both passive taxis with `alongTripod` identities (dist x p = t ∧ dist p r = dist x r − t ∧ dist p e = |dist x e − t|), the distance-level description of “moving along the edge x→e→r of B(x₂,x₃,r) toward the pickup point.” The active taxi still uses an arbitrary bridge. Checkpoint statements are unchanged.
