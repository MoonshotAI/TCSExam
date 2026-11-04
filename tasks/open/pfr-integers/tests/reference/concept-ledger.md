# Faithfulness Review: The Integer Polynomial Freiman–Ruzsa Conjecture

This note explains the task statement for readers comparing the mathematical definitions with the Lean source. The current scoring statements are `conj` and `refuted`; proving either earns full credit.

This document compares the integer PFR statement in the literature with the Lean statement used by this task, and records all modeling choices.

- **Sources:** Lovett–Regev, “A Counterexample to a Strong Variant of the PFR Conjecture in Euclidean Space,” Discrete Analysis 2017:8, arXiv:1612.03332v2 (Conjecture 1.2 and footnote 1 checked sentence by sentence); Manners, arXiv:1709.09738 (abstract checked: the ellipsoid form and convex-progression form are equivalent); definition-layer survey addcomb-patterns.md.
- **Released statement:** environment/app/Task/Basic.lean; its fixed region and slot headers match tests/reference/Basic.lean word for word.

## 1. Literature statement and Lean correspondence

Lovett–Regev Conjecture 1.2 states: there is an absolute constant c>0 such that if A⊆ℝⁿ satisfies |A+A|≤K|A|, then for some d≤c·log K there are (1) a d-dimensional lattice L⊆ℝᵈ (footnote 1 says WLOG L=ℤᵈ), (2) a symmetric convex body B⊆ℝᵈ, (3) a linear map φ:ℝᵈ→ℝⁿ, and (4) a set X⊆ℝⁿ with |X|≤K^c, such that |L∩B|≤|A| and A⊆φ(L∩B)+X. The same paper disproves the strengthening that replaces φ(L∩B) with a generalized arithmetic progression (GAP), Conjecture 1.3, which was posed by Green in 2007. This task uses the special case n=1 and A⊆ℤ (the integer version, also called Marton’s conjecture), with the size bound relaxed to |P|≤K^O(1)|A| following Tao’s lecture-note convention; see deviation 1.

| Concept | Literature | Lean identifier in this task | Notes |
|---|---|---|---|
| Set A | Finite, nonempty A⊆ℤ. | A : Finset ℤ, A.Nonempty. | Finite by Finset; see deviation 4 for empty sets. |
| Sumset | A+A={a+b}. | A+A, pointwise Finset addition (open scoped Pointwise). | Elementwise membership is Finset.mem_add. |
| Doubling bound | |A+A|≤K·|A|, K≥1. | (A+A).card≤K*A.card, with K:ℕ. | See deviation 2. |
| Dimension | d≤c·log K. | P.dim≤C₁*Nat.log 2 (K+1). | See deviation 3. |
| Structured set | φ(L∩B), L=ℤᵈ, B symmetric convex, φ linear. | ConvexProgression ℤ: body : Set (Fin dim→ℝ) with convex_body, symm_body, bounded_body; map : (Fin dim→ℤ)→+G; base; toSet is the translated image of lattice points in the body. | See deviations 5 and 6. |
| Size of structured set | |L∩B|≤|A| (Lovett–Regev) or ≤K^O(1)|A| (Tao convention). | P.latticeFinset.card≤(K+1)^C₂*A.card (strengthened). | See deviations 1 and 8. |
| Covering | A⊆φ(L∩B)+X with |X|≤K^c. | ∃X:Finset ℤ, X.card≤(K+1)^C₂ ∧ A⊆X+P.toFinset. | X+P is the union of |X| translates of P, using pointwise addition. |
| Conjecture | There exists an absolute constant c. | ∃C₁ C₂:ℕ, ∀A K, …. | See deviation 1. |
| Negation | — | refuted is the literal negation of conj. | |
| Example | In one dimension, B=[−1,1], φ is multiplication by 2. | prog024: body {x:Fin 1→ℝ | |x 0|≤1}, map l=2·l 0, base=2, point set {0,2,4}. | Checkpoint c3. |

## 2. Deviations and rationale

1. **Use Tao/instruction size bounds, with two constants and |P|≤(K+1)^C₂|A|, rather than Lovett–Regev’s single bound |P|≤|A|.** The Lovett–Regev form implies this weaker form by choosing C₂ so K^c≤(K+1)^C₂ and |A|≤(K+1)^C₂|A|; both forms remain open, and proving the literature form proves this one. The task instructions explicitly require |P|≤K^O(1)|A| and K^O(1) translates, so this task follows that convention. Combining the exponents for |X| and |P| into one C₂ is standard absorption of O(1) constants.

2. **Quantify K over ℕ.** The literature takes real K≥1. The condition |A+A|≤K|A| implies |A+A|≤⌈K⌉|A|, and log₂(⌈K⌉+1)≤2·log₂(K+1) for K≥1; constants are absorbed. Thus integer and real K formulations are equivalent for an existential-constant conjecture. The natural-number version avoids real logarithms and powers in the statement and keeps all bounds in kernel-decidable arithmetic.

3. **Express O(log K) as C₁·Nat.log 2 (K+1).** Nat.log 2 computes ⌊log₂⌋ in the kernel. K+1 avoids log 1=0 forcing dimension 0 when K=1; the literature’s log(2+K) or O(log K) notation is equivalent up to constants. The logarithm base only changes the constant.

4. **Require A.Nonempty.** The literature context assumes a nonempty set (|A| appears in ratio bounds). Formally the empty set would also satisfy this statement by choosing an empty body P and X=∅, but it is excluded to match the literature; this also makes K=0 constraints vacuous in the expected way.

5. **Put boundedness of the body in the structure (bounded_body).** A “convex body” in the literature is compact and hence bounded; in Lean, boundedness must be explicit for P to have finitely many lattice points. Convexity and symmetry are fields. **Do not require properness/injectivity:** Manners (arXiv:1709.09738, footnote 1 and Remark 1.5) notes that properness does not distinguish the two conjecture forms; GAP and convex-progression sizes use the same convention and both permit improper progressions. What Lovett–Regev disprove is the extra condition that the structured set be aligned with the lattice basis (an axis-parallel box in lattice coordinates). The surviving convex-progression form allows arbitrary symmetric convex bodies.

6. **Fix the lattice to ℤᵈ and represent φ as the group homomorphism (Fin d→ℤ)→+ℤ.** Lovett–Regev footnote 1 says L=ℤᵈ WLOG. In the integer case, φ:ℝᵈ→ℝ acts on lattice points exactly as choosing d integer steps, i.e. an additive homomorphism from the free abelian group ℤᵈ to ℤ (mathlib’s (Fin dim→ℤ)→+G). The base absorbs translation (the literature’s translate X and the affine offset).

7. **Write coverage as Finset inclusion A⊆X+P.toFinset.** The paper writes A⊂φ(L∩B)+X. Pointwise Finset addition X+P.toFinset is exactly the union of {x+p}, i.e. |X| translates of P, so the meanings agree pointwise.

8. **Strengthen the counted size from the image set to the number of lattice preimages, starting 2026-09-17.** Before the change (09-04 to 09-17), Lean bounded P.toFinset.card, the number of distinct image values in ℤ. The paper (Manners footnote 1 and Lovett–Regev’s |L∩B|) counts lattice points in the body, on the preimage side. Image cardinality is at most the lattice-point count, so the old condition was weaker (the paper’s condition implies the old Lean condition). The change added latticeSet/finite_latticeSet/latticeFinset and the sorry-free lemma toFinset_card_le_latticeFinset_card (image≤preimage count); the conj/refuted size condition now uses P.latticeFinset.card. The strengthened conj has the same strength as the original conjecture; the final3-check/statement-pfr-integers-poststrengthen.md audit confirmed this. Experiments under the old convention (v5, full1, and one pass each of flagship 3-task claude/gpt) should be read under the weaker formulation. The scoring gates passed under the old form and were all re-run successfully after strengthening.

## 3. Distinction from nearby problems

- The F₂ version of PFR (Marton’s conjecture) was solved in 2023 by Gowers–Green–Manners–Tao and formalized in teorth/pfr. This is the **integer version**, the main remaining case in that line, with a different statement and methods from the F₂ result.
- Weak integer PFR was proved in teorth/pfr (weak_PFR_int): it uses a weaker “dimension” formulation (no progression and weaker parameters), unlike the full-strength covering statement here. This task does not weaken the conjecture.
- A preprint from 2025-12 claims to solve this conjecture; as of 2026-09-06 it has no retraction, journal acceptance, or community confirmation. The task was authored as an open problem and does not mention the claim in task text or instructions.

## 4. Known frontier

- The GAP form was **disproved** by Lovett–Regev, Discrete Analysis 2017:8; this task does not use GAP.
- The convex-progression form remains open. Best known bounds are quasipolynomial or near-polynomial, not polynomial (Sanders and later work). The F₂ version was solved in 2023 by GGMMT. Manners (arXiv:1709.09738) proved equivalence of the ellipsoid and convex-progression formulations.
- Minimum doubling in ℤ is |A+A|≥2|A|−1 for finite nonempty A⊆ℤ, with equality for arithmetic progressions. This supports checkpoints c1 and c2 (the smallest case of Freiman’s theorem; textbook-level, e.g. Tao–Vu, Additive Combinatorics, Proposition 5.8).
