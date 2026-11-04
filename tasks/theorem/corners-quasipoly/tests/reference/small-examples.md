# small-examples — lean-corners-quasipoly (JLLOS25)

This record describes one of the three fidelity checks (executable small examples): reimplement key predicates from the task's definition layer in Python and check their behavior on small instances.

Script: `small_examples.py` (standard library only, no third-party dependencies). All **20/20 checks passed**. The Python mirror corresponds line by line to the Lean definitions (`expect` / `grid_norm` / `comb_spread` / `asym_spread` / `container` / `corner_free` / `corner_count`).

## Examples, item by item

- **E1 (grid-norm semantics)**: (a) the G(2,2) norm power of the constant function α is α⁴; (b) the norm power of the rectangle indicator `1_{X₀×Y₀}` is `(|X₀|/|Ω₁|)^k(|Y₀|/|Ω₂|)^ℓ` (supports the product structure in Definition 2.1); (c) the (1,1) norm is the expectation. All three match hand calculations.
- **E2 (combinatorial-spread semantics, Definition 3.1)**: the full set is (1,0)-spread ✓; a row strip (density 2/3) has density 1 in its own rectangle, so it is not (2/3,0)-spread but is (2/3,2/9)-spread (enumeration confirms the maximum violation is 2/9); the diagonal (density 1/3) is not (1/3,0)-spread but is (1/3,2/27)-spread. These examples pin down the direction of “spread = no excess density on large rectangles” and the additive remainder `τ·Ef·Eg + γ`.
- **E3 (counting lemma c1)**: k=2, ℓ=1, bipartite graph; set the indicator of T to a specified edge and enumerate assignments on a 2-point set to verify `E[T·f] ≤ τ·E[f] + γ`.
- **E4 (asymmetric spread, Definition 5.14)**: the constants 1 and 1/2 attain equality at ε=0 (fixing the placement of the factor (1+ε)); a dense rectangle (density 1/2) violates the condition for s=t=1 (take g₁=g₂ to be the corresponding side indicator), confirming the `2^{-s}` form of the “not too small rectangle” assumption.
- **E5 (containers and corners, F₂²)**: check container membership and size. The largest corner-free subset of F₂²×F₂² has size 8 (brute force; structure `{x₁=y₁}`); the number of corners in a corner-free set is exactly |A| (only the degenerate corner with d=0). This is the key identity in the derivation from c7 to c8.
- **E6 (general group, Z/3)**: the largest corner-free subset of Z/3×Z/3 has size 6 (structure x≠y); the corner count is also checked to equal |A|.

## Findings during development

Three assertions in the test script itself were wrong and have been corrected; these did not concern the task statements: the hand calculation for E1c was wrong; intuition about the spread parameter in E2b was wrong (the strip has density 1 in its own rectangle); and the maximum corner-free-set sizes in E5c/E6c were wrong (4→8 and 2→6). **One substantive finding**: the number of corners in a corner-free set is |A|, not |A|·|G| (the initial test-point card and c8 docstring had the wrong value). This has been corrected; the c8 derivation was rebuilt as “corner-free ⟹ α ≥ |G|·2^{−C·L^600} ⟹ contradiction with the assumption L^600 ≤ c·log|G| (choose c sufficiently small); failure of the assumption gives the claimed bound.” See section 4 of `concept-ledger.md`.

## Conclusion

The definition-layer predicates (expectation, grid norm, two levels of spread, containers, corner predicate, and corner count) all pass on enumerable small examples. The counting identity in the c7→c8 step was also checked on two small groups. No dimensional or scale-related risk remains.
