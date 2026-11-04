# Independent Retranslation: The Polar-Code Scaling-Exponent Conjecture

This record derives a formalization draft from the literature without consulting the shipped Lean file, then compares the two component by component. It is the third fidelity record (independent retranslation).

- Sources: the full texts of Mondelli–Hassani–Urbanke 2016 (arXiv:1501.02444v3) and Hassani–Alishahi–Urbanke 2014 (arXiv:1304.4778v4),.

> **Superseded-version notice:** This document treated “for every β < 1/μ, liminf P(Z_n ≤ 2^(−n^β)) ≥ I(W)” as the process-form working definition for HAU/MHU, and concluded that it agreed with the shipped version. Both the attribution and this form were disproved by an independent blind check: the supplied MHU text contains no such form, and the statement holds trivially for every BMS channel and every ν > 0 (proof in Section 6 of `concept-ledger.md`). The shipped definition was changed to the rate form (MHU equation (34)). The remaining content here—the channel, transform, BEC, and generator-matrix retranslation and hand checks—is unaffected.

## Step 1: Source statements

- MHU 2016 introduction: “In the scaling exponent approach, the channel W and the error probability P_e are fixed and it was proved that the gap to capacity I(W) − R scales as N^(−1/μ). Here, μ is called scaling exponent and this scaling exponent depends on the channel W. A heuristic computation for the binary erasure channel (BEC) gives μ = 3.627 and it was shown that, for any channel W, 3.579 ≤ μ ≤ 5.702.” The same paper gives a new upper bound of 4.714 (improved to 4.63 by WLVG 2022) and says, “It is conjectured that the lower bound on μ can be increased up to 3.627.”
- HAU 2014 abstract: to make the sum of the synthesized-channel Bhattacharyya parameters less than a given P_e, the required block length N satisfies α/(I(W) − R)^{3.579} ≤ N ≤ β/(I(W) − R)^6.
- Process-form working definition used in the HAU/MHU body: Bhattacharyya process Z_n (Z_0 = Z(W), with each step choosing W⁻/W⁺ with equal probability); speed criterion: for every β < 1/μ, liminf P(Z_n ≤ 2^(−n^β)) ≥ I(W). MHU Theorem 1's block-length form (for fixed P_e, N ≤ β₁(I(W) − R)^(−μ) suffices) follows from the process form.

## Step 2: Natural-language refinement (resolving ambiguities)

- **Channel:** binary input ({0,1}, addition in GF(2)), finite output alphabet, memoryless, output-symmetric: there is an involution π on the output alphabet such that W(y|1) = W(πy|0).
- Z(W) = ∑_y √(W(y|0)W(y|1)); I(W) is mutual information under uniform input (the symmetric capacity for a BMS channel).
- **One-step synthesized channels:** W⁻(y₁y₂|u₁) = ½∑_{u₂} W(y₁|u₁⊕u₂)W(y₂|u₂); W⁺(y₁y₂u₁|u₂) = ½W(y₁|u₁⊕u₂)W(y₂|u₂). The 2ⁿ synthesized channels at depth n are indexed by ± sequences.
- **P(Z_n ≤ t):** the fraction, by finite counting, of the 2ⁿ equally likely sequences whose Z value is at most t.
- **“Scaling exponent of W is at most ν”:** for every 0 < β < 1/ν, liminf_n P(Z_n ≤ 2^(−n^β)) ≥ I(W). This is the universal upper-bound form; the dual lower-bound formulation reverses the condition to β > 1/μ, which is not needed for this task's threshold formulation.
- **Conjecture (threshold form):** every BMS channel has scaling exponent ≤ 4. Its negation is that there exists a BMS channel with scaling exponent > 4.
- **BEC:** three-symbol output alphabet {0,1,?}, with W(v|v) = 1−ε and W(?|u) = ε.

## Step 3: Independently drafted types

```
Channel Y := { toFun : Fin 2 → Y → ℝ, nonnegative, each row sums to 1 }       (Y finite)
IsBMS W := ∃ σ : Perm Y, involution σ ∧ ∀ y, W 1 y = W 0 (σ y)
Z W := ∑ y, sqrt (W 0 y * W 1 y)
I W := (1/2) * ∑ x y, W x y * log2 (W x y / ((W 0 y + W 1 y)/2))   (with 0·log0 = 0)
minus W u (y₁,y₂) := (1/2) * ∑ u′, W (u+u′) y₁ * W u′ y₂
plus  W u ((y₁,y₂),u₁) := (1/2) * W (u₁+u) y₁ * W u y₂
synth W : List {−,+} → Channel  (alphabet recurses with the sequence: − squares, + squares and appends one bit)
frac W n t := fraction of the 2ⁿ length-n sequences for which Z (synth W s) ≤ t
ScLe W ν := ∀ β, 0 < β → β < 1/ν → I W ≤ liminf (fun n => frac W n (2^(−n^β)))
Conjecture := ∀ W, IsBMS W → ScLe W 4
```

## Step 4: Component-by-component comparison with the shipped version

| Component | Draft | Shipped version | Finding |
|---|---|---|---|
| Channel | Structure with real-valued transition probabilities | `Channel`, same form | Match |
| Symmetry | Involution σ, W 1 y = W 0 (σ y) | `IsBMS`, same form | Match |
| Z | ∑ √(p·q) | `Z`, same form | Match |
| I | Mutual information with uniform input | `I`, same form (`xlog2` handles the zero convention) | Match |
| W⁻ | ½∑_{u₂} W(y₁|u₁⊕u₂)W(y₂|u₂) | `polarMinus`, same form | Match |
| W⁺ | ½W(y₁|u₁⊕u₂)W(y₂|u₂) | `polarPlus`, same form; the second factor is conditioned on input u₂ | Match |
| Depth-n channel | Recursive ± sequences, with the alphabet changing along the sequence | `outAlpha` / `polarChannel` (false = −, true = +), same form | Match (sequence-order convention does not affect the count) |
| P(Z_n ≤ t) | Count of the 2ⁿ equally likely sequences | `fracGood` (count over `Fin n → Bool` via `List.ofFn`, divided by 2ⁿ) | Match |
| Scaling exponent ≤ ν | ∀ 0 < β < 1/ν, liminf ≥ I(W) | `ScalingExponentLe`, same form | Match |
| Conjecture | ∀ BMS, ScLe W 4 | `conj` (`refuted` is its negation) | Match |
| BEC | {0,1,?}, erasure probability ε | `BEC` (`Option (Fin 2)`, `none` = ?) | Match |

There are no disagreements. Two packaging differences—the channel is a real-valued structure rather than a PMF, and mutual information is defined directly instead of using PFR—preserve semantics; see deviations 1/4 in `concept-ledger.md`.

## Hand checks against the literature and expanded definitions

- **Second factor of W⁺:** In the literature's formula W⁺(y₁y₂u₁|u₂), the factors are conditioned on u₁⊕u₂ for the first output and u₂ for the second. Check with Z(W⁺) = Z(W)², which holds for every channel (Arıkan 2009, Proposition 5). Under the correct formula,
  Z(W⁺) = ½∑_{u₁}[∑_{y₁}√(W(u₁,y₁)W(u₁⊕1,y₁))]·[∑_{y₂}√(W(0,y₂)W(1,y₂))] = Z(W)² ✓.
  During implementation, this check caught an error where the second factor was mistakenly conditioned on u₁ (`W(y₂|u₁)`). That incorrect formula gives Z(W⁺) = Z(W), contradicting the identity.
- **One-step BEC recursion** (hand check of c2's expected value): On the W⁻ side, 5 of the 9 output pairs contribute: (none,none) contributes ε², and the four single-erasure outputs each contribute ½ε(1−ε), totaling ε² + 2ε(1−ε) = 2ε − ε² ✓. On the W⁺ side, among the 18 outputs, only the two outputs ((none,none),u₁) contribute, each by ½ε², for a total of ε² ✓. This matches the BEC recursion in KMTU/MHU (z⁻ = 2z − z², z⁺ = z²).
- **Hand check of G₄** (c3 expected value): Reindexing the Kronecker product G₂ G₂ by `finSplit` (high bit first) gives [[1,0,0,0],[1,1,0,0],[1,0,1,0],[1,1,1,1]]. Applying bitRev 2 = [0↦0, 1↦2, 2↦1, 3↦3] to rows swaps the middle two, giving [[1,0,0,0],[1,0,1,0],[1,1,0,0],[1,1,1,1]] = Arıkan 2009's G₄ ✓.
- **Threshold semantics:** Proving `conj` (every BMS channel polarizes at least at rate 1/4) would prove a universal scaling-exponent upper bound ≤ 4 < 4.63, improving WLVG 2022. Proving `refuted` (some BMS channel is slower than rate 1/4) would prove a universal lower bound > 4 > 3.579, improving HAU 2014. The BEC's μ = 3.627 < 4 is consistent with `conj` and is not a counterexample. There is no evidence that any known channel is consistent with `refuted`; both directions remain open ✓.
