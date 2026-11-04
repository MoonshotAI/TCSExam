# Independent Retranslation — `lean-three-taxi`

This note cross-checks a second, independent retranslation of the eight checkpoints and core definitions against the finalized (shipped) statements, recording disagreements and their adjudication. It is the third retranslation path under step 6 of the SOP.

Method and independence, stated candidly: the same subagent authored the task and performed the retranslation. After finalization, the statements were independently derived again from the paper (`paper.txt`, §§2–4) and compared with the final version. This is less independent than a retranslation by “another agent/person” and is recorded as a residual risk.

## Summary of retranslation results

Each row covers one object; the “Cross-check” column states how the retranslation relates to the finalized version.

| Object | Retranslated statement (in plain language) | Cross-check |
|---|---|---|
| Equation (1) / `tripodC` | Edge length from the center to one endpoint = half the sum of two sides minus the opposite side | Agree (verbatim) |
| Distorted contribution | For (xᵢ, y): d(xᵢ,y) − ψ·(min(ℓᵢ, xᵢg) + yg) | Agree (piecewise integral check: the discounted segment is the interval segment intersected with [xᵢ, g], plus the full y-edge segment) |
| M | x₁y₁ plus the minimum of the discounted matching costs for the two passive pairs | Agree (the forced pairing of the active pair matches the paper) |
| Σ | max(0, min(ℓ₂,ℓ₃) − (dd − ℓ₂ − ℓ₃)) | Agree (q₂q₃ follows from the order identity dd − ℓ₂ − ℓ₃) |
| c1 (Lemma 2.1) | Each of the three corresponding edges changes by at most d(w₁,w₂) | Agree (all three u/v/w edges are listed, matching the paper's “any two corresponding edges”) |
| c2 (Claim 3.1) | During movement and after recombination, ℓ₂′+ℓ₃′ ≤ d(x₂′,x₃′) | Agree (preserving order is equivalent to this inequality; nonnegativity is covered by a definition-layer support lemma, see D1) |
| c3 (Lemma 3.2) | matchSum(x₂ŷ,x₃y) ≤ matchSum(x₂y,x₃ŷ) ⟺ x₂ĝ ≤ x₂g | Agree (both matchings have equal cost at the equality threshold, so the iff still holds; confirmed by the E8 grid check) |
| c4 (Lemma 3.3) | Replace y_j with any point y′; then ∆Φ ≤ α·d(y_j, y′) | Stronger than the paper (which only uses “move to r”); see adjudication D2 |
| c5 (Lemma 3.5) | Three slope identities under affine substitution | Agree (the paper says “follows from (1),” i.e. linearity) |
| c6 (Corollary 3.6 + Claim 3.4) | While an offline algorithm moves a passive server, movement-phase cost + ∆Φ ≤ 0 (endpoint form) | Agree (endpoint form is equivalent to integrating the rate; Corollary 3.6 is not stated separately, see D3) |
| c7 (Lemmas 3.7/3.8/3.11) | Recombination: ∆Σ ≤ 0 ∧ ∆M ≤ ψ·OPT_t; reset: ∆Φ ≤ 0 | Agree (covers four cases; OPT_t = d(y_j, r) uses the position before movement) |
| c8 (Theorem 3.12) | ∃ κ > 0, trajectory COST ≤ κ·OPT | Agree (c = 0 follows from Φ₀ = 0; holds for any offline request sequence, stronger than only for OPT) |

## Disagreements and adjudications

- **D1 (nonnegativity part of c2).** Claim 3.1 in the paper states only the order (x₂→q₂→q₃→x₃, with equality allowed), and does not list ℓ ≥ 0 separately. Finalized c2 states only the upper bound (ℓ₂′+ℓ₃′ ≤ d(x₂′,x₃′)); ℓ ≥ 0 is proved by definition-layer lemmas (`movePhase_ℓ_nonneg` / `serveRequest_ℓ_nonneg`) and maintained along the trajectory. Adjudication: Lean's order statement is equivalent to the upper-bound inequality (q₂q₃ = dd − ℓ₂ − ℓ₃ ≥ 0). Placing nonnegativity in the definition layer is technically needed for totality of the trajectory function and loses no content (order plus the definition ℓ = xᵢqᵢ already implies ℓ ≥ 0).
- **D2 (generalization in c4).** Lemma 3.3 in the paper is used for the offline move “to r”; the finalized statement applies to arbitrary y′. Adjudication: the proof (contribution Lipschitz bound + variation of min) does not rely on y′ = r. The generalization is free and makes the checkpoint self-contained (without introducing an offline-phase function); keep it.
- **D3 (Corollary 3.6).** During retranslation, the source was initially read as stating “the matching contribution of xⱼ grows at rate at most cⱼ(1−ψ).” It was then found that fixing the matching endpoints fails literally at a critical switch (exact E10 counterexample: rate 0.910 > 0.909). The paper's instantaneous-rate argument still works when the current minimum-cost matching is used. Adjudication: Corollary 3.6 is incorporated into c6 as proof content; c6 states only Claim 3.4 in its min-form endpoint version. This agrees with deviation 5 in concept-ledger.
- **D4 (tie during the movement phase).** When movePhase has a tie T1 = U2, it chooses server = 0 (active arrives first). The paper does not specify tie-breaking. The retranslation confirms that both interpretations have the same movement distance and arrival state at that instant (both are “at that instant the two cars are simultaneously at r”); tie-breaking does not affect any checkpoint statement. No adjudication needed; recorded.
- **D5 (Σ in the single-unobstructed-car case).** The proof of Claim 3.4 establishes Σ′ ≤ 2 only for the case with two unobstructed cars. Check for the single-car case (case A): ℓ does not increase (it is frozen or has rate ≤ 0), q₂q₃ is unchanged, so Σ does not increase (Σ′ ≤ 0). The finalized c6's proof sketch uses this tighter bound; in that case no contribution from Σ is needed. No conflict with the paper.
- **D6 (shape of the `hx1r` premise in c7).** Case (d) in the paper uses “the new location of x1 can only be closer to r” (x₁x₃ = x₁r ≤ OPT_t). The finalized premise is d(x₁′, r) ≤ d(st.y₁, r) (distance from the moved x₁ to r is at most the distance from the pre-move y₁ to r). Adjudication: the two follow from each other using d(x₁′,r) = d1 − s1 ≤ d1 = d(x₁,r) = d(y₁,r) (`hxy`). This premise form is more direct for the call site in c8. They agree.

## Unadjudicated disagreements

None.
