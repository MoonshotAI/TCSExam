# Faithfulness Review: Is the Matrix Multiplication Exponent 2?

This note explains the task statement for readers comparing the mathematical definitions with the Lean source. The current scoring statements are `conj` and `refuted`; proving either earns full credit.

This review compares the standard literature statement ω=2 with the Lean statement used by this task and explains each modeling choice.

- Sources: Alman–Vassilevska Williams, “A Refined Laser Method and Faster Matrix Multiplication,” SODA 2021; definition-layer survey tensor-coding.md; tensor-rank layer ported from spectra-research/asymptotic-tensor-rank-semicontinuity (Apache-2.0); Bürgisser–Clausen–Shokrollahi, Algebraic Complexity Theory, Chapter 15 (tensor-rank definition of ω).
- Released statement: environment/app/Task/Basic.lean; its fixed region and slot statements match tests/reference/Basic.lean word for word. The reference file contains full proofs for the three checkpoints.

## 1. Literature statement and Lean correspondence

In the standard formulation, over a field F, the bilinear complexity of multiplying n-by-n matrices equals the tensor rank R(⟨n,n,n⟩) of the matrix multiplication tensor. The matrix multiplication exponent is ω = inf{τ ∈ ℝ | ∃ C, R(⟨n,n,n⟩) ≤ C·n^τ for all n}. The trivial lower bound is ω≥2: the output has n² coefficients and in general requires n² input data; formally, the flattening bound gives R(⟨n,n,n⟩)≥n². The question is whether ω=2, equivalently whether ω≤2 given the known ω≥2.

| Concept | Literature | Lean identifier in this task | Notes |
|---|---|---|---|
| Base field | Often left unspecified; classical formulations use ℂ or an arbitrary field. | Fixed to ℚ (Rat). | See deviation 1. |
| Third-order tensor | An element of Fᴵ ⊗ Fᴶ ⊗ Fᴷ. | Tensor3 F ι₁ ι₂ ι₃ := (ι₁ × ι₂ × ι₃) → F (functional encoding). | See deviation 2. |
| Rank-one tensor | u⊗v⊗w. | simpleTensor u v w; IsSimpleTensor is its existential form. | |
| Tensor rank R(T) | Minimum number of rank-one tensors whose sum is T. | tensorRank T := sInf (decompSet T), the infimum of the set of decomposition lengths. | The set is nonempty by the standard-basis expansion (tensorRank_decomp_card), so the infimum is attained. |
| Matrix multiplication tensor ⟨m,n,p⟩ | Structure constants of the trilinear form Tr(ABC). | matMulTensor F m n p; its legs are Fin m × Fin n, Fin n × Fin p, and Fin p × Fin m. | See deviation 3. |
| Tensor encodes matrix multiplication | By definition. | matMulTensor_contract: contracting the first two legs with A and B gives (A * B) i' k' (sanity lemma). | Proved in the fixed region. |
| Exponent set | {τ : R(⟨n,n,n⟩) = O(n^τ)}. | omegaSet F. | |
| ω | Infimum of that set. | matMulOmega F := sInf (omegaSet F). | Nonempty (omegaSet_nonempty, using the naive decomposition with τ=3) and bounded below by 0 (omegaSet_nonneg_of_mem / omegaSet_bddBelow) are proved; see deviation 4. |
| Conjecture | ω=2. | Main slot conj : matMulOmega ℚ ≤ 2; refuted is its literal negation. | See deviation 5. |
| Trivial lower bound ω≥2 | Flattening gives R(⟨n,n,n⟩)≥n². | Not formalized; it was the fourth checkpoint candidate cut under the three-checkpoint limit. | See deviation 5. |

## 2. Deviations and rationale

1. **Fix the base field to ℚ.** Literature statements of ω usually leave the field unspecified. All known upper-bound constructions (from Strassen and Coppersmith–Winograd through laser methods and the bound 2.371177) use integer-coefficient decompositions and work over every field. Known lower bounds (flattenings and substitution methods) also hold over every field. The task fixes ℚ as the standard characteristic-zero choice for arithmetic computation. It does not use ZMod 2: tensor rank can vary under field extension, and field-independence of matrix multiplication tensor rank has not been proved; fixing ZMod 2 would turn conj into a nonclassical variant and fail to preserve the statement. The trade-off is that the sandbox kernel does not normalize rational arithmetic, so decide cannot prove rational identities. Checkpoint proofs therefore use norm_num or explicit algebra (kernel-checkable reflection proofs; #print axioms is clean), as documented in instruction.md.

2. **Use a function encoding for tensors rather than mathlib’s quotient tensor-product types.** TensorProduct/PiTensorProduct are quotient types, making pointwise identities such as the 64 checks in Strassen’s identity cumbersome. With functions, funext and Finset sums suffice. This encoding was validated throughout the spectra repository (the definition-layer port source, under Apache-2.0; its file headers give provenance). Leg indices generalize to any Fintype (the source repository uses Fin (d i)). Matrix multiplication’s legs are product types such as Fin m × Fin n; arbitrary Fintypes avoid repeated conversion through finProdFinEquiv. Reindexing by Fintype.equivFin gives the standard-basis expansion, whose rank upper bound uses products of Fintype cardinalities, as in the general tensor-rank literature.

3. **Use Fin p × Fin m for the third matrix-multiplication leg, following the Tr(ABC) convention.** The trilinear form is T(A,B,C)=Tr(ABC)=Σ AᵢⱼBⱼₖCₖᵢ, so C’s index pair is (k,i). This is the standard symmetric convention for the three factors. The tensor value is 1 exactly when j=j' ∧ k=k' ∧ i=i', and 0 otherwise. The fixed-region sanity lemma matMulTensor_contract pins down the convention: contracting the first two legs against A and B yields the matrix-product formula (A * B) i' k'. A transposed or misaligned index convention would fail this lemma. The docstring and instruction.md state the convention explicitly.

4. **Define ω directly with sInf, and rule out empty-set/unboundedness traps in the definition layer.** In Lean, sInf ∅=0, and the infimum of an unbounded-below set is also 0. If omegaSet were empty, conj could become vacuously true—the critical failure mode. The fixed region proves omegaSet_nonempty (3 belongs, with C=1, by the naive-decomposition bound tensorRank_matMulTensor_le giving R(⟨n,n,n⟩)≤n³); omegaSet_nonneg_of_mem (any τ in the set has τ≥0); and omegaSet_bddBelow. For nonnegativity, if τ<0, choose k=⌈−1/τ⌉+1, M=max(1,⌈C⌉), and N=(M+1)^k. Then C·N^τ≤M/(M+1)<1≤R(⟨N,N,N⟩), a contradiction. The bound R≥1 follows from tensorRank_eq_zero and the tensor being nonzero. This uses elementary rpow facts, not a limit theory. The lemmas matMulOmega_le_of_mem (an algorithm gives an upper bound) and le_matMulOmega_of_forall_le (a pointwise lower bound gives a lower bound on ω) are also provided. The docstring warns that a strict pointwise lower bound does not imply a strict lower bound on sInf.

5. **State conj as ω≤2 and do not formalize the trivial ω≥2 flattening bound.** The literature asks whether ω=2; given the known ω≥2, that is equivalent to ω≤2. Thus conj is matMulOmega ℚ ≤ 2, and refuted is its literal negation. Either result would solve the corresponding open direction: the upper-bound direction gives ω=2, while its negation proves a superquadratic exponent. The flattening bound (each one-leg flattening has matrix rank n²; a rank-one tensor flattens to a matrix of rank at most 1, and rank is subadditive) was the fourth checkpoint candidate cut to fit the three-checkpoint limit. It requires Matrix.rank and a rank-of-sum API, increasing definition-layer complexity and iteration risk. Its only role was to support the remark “ω≤2 iff ω=2”; omitting it does not change the literature meaning of either main proposition, which are independently open. The omission is recorded explicitly.

6. **The constant in O(n^τ) has the correct quantifier order.** omegaSet means ∃ C ∀ n, R ≤ C·n^τ, matching the literature’s R(⟨n,n,n⟩)=O(n^τ): the constant is chosen before n, separately for each τ. n ranges over all naturals, including 0. At n=0, R(⟨0,0,0⟩)=0 (the empty index type gives the zero tensor, represented by the empty decomposition), and C·0^τ is 0 for τ>0, C for τ=0, and 0 for τ<0 under the rpow definition. Thus n=0 imposes no obstruction. At n=1, the inequality gives C≥1, used in the proof of omegaSet_nonneg_of_mem.

## 3. Distinction from nearby problems

- **Rectangular matrix multiplication exponents** such as ω(1,k,n) (Bürgisser–Clausen–Shokrollahi, Chapter 15): this task concerns only square matrices. Although matMulTensor F m n p is defined for general (m,n,p), omegaSet/matMulOmega use only the diagonal (n,n,n).
- **Border rank and asymptotic rank R̃:** Laser methods improve bounds on border rank/asymptotic sum inequalities. This task defines ω using ordinary tensor rank, the standard definition of the matrix multiplication exponent; the border-rank exponent ω̃ is a different object. Degeneration and border rank are not introduced in the definition layer.
- **Rank of the 3×3 matrix multiplication tensor:** Laderman’s algorithm gives R(⟨3,3,3⟩)≤23, while the exact value is open. This is material for practicing small tensor rank, but was not chosen as a checkpoint: verifying the 23-term identity pointwise is more than five times the size of Strassen’s, while the checkpoint target was easy-to-medium.

## 4. Known frontier

- Upper bound: ω<2.371177, Dupont et al., arXiv:2608.16884. The abstract says it “yields an upper bound of ω < 2.371177, improving the previous best bound of 2.371339.” The previous 2.371339 bound is Alman et al. 2025 (arXiv:2404.16349, SODA 2025); before that, 2.371552 was due to Vassilevska Williams–Xu–Xu–Zhou 2024 (arXiv:2307.07970).
- The arXiv listing API search for “matrix multiplication exponent,” sorted by submission date, identified 2608.16884 as the latest work; no later result appeared.
- Lower bound: for ω itself, only the trivial ω≥2 is known.
- Barrier: Alman–Vassilevska Williams, FOCS 2018, “Limits on All Known (and Some Unknown) Approaches to Matrix Multiplication”: current laser-method frameworks cannot prove ω=2.
- Strassen 1969 gives R(⟨2,2,2⟩)≤7 (checkpoint c3). The matching lower bound R(⟨2,2,2⟩)=7 is known (Hopcroft–Kerr 1971 / Winograd 1971) but not formalized; the checkpoint uses only the ≤ direction.
