# Independent Retranslation: Is the Matrix-Multiplication Exponent 2?

This record independently derives a formalization draft from the standard literature statements without consulting the shipped Lean file, then compares the two component by component. It is the third fidelity record (independent retranslation).

- Sources: the survey by Alman and Vassilevska Williams (SODA 2021) and the standard definitions in Chapter 15 of Bürgisser–Clausen–Shokrollahi, *Algebraic Complexity Theory*.
- Method: refine the statements in natural language, draft the types, then compare with the shipped version.

## Step 1: Source statement

Let F be a field. Denote the structure tensor of the bilinear map “multiply an m×n matrix by an n×p matrix” by ⟨m,n,p⟩. In the bases (e_{ij}), (f_{jk}), and (g_{ki}), it is ⟨m,n,p⟩ = Σ_{i,j,k} e_{ij} ⊗ f_{jk} ⊗ g_{ki}. The rank R(T) of a tensor T is the minimum number of rank-1 tensors whose sum is T. The matrix-multiplication exponent is ω = inf { τ ∈ ℝ | R(⟨n,n,n⟩) = O(n^τ) }. It is known that ω ≥ 2 (the trivial lower bound); the question is whether ω = 2.

## Step 2: Natural-language refinement (resolving ambiguities)

- **Base field:** the literature does not fix one; choose ℚ, an arithmetic model of characteristic 0.
- **Tensor representation:** represent an element of F^I⊗F^J⊗F^K as a function from the product of finite index sets I,J,K to F.
- **Rank-1 tensor:** there are functions u : I → F, v : J → F, w : K → F such that the tensor takes value u i · v j · w k at (i,j,k).
- **Rank:** R(T) = min { r ∈ ℕ | T is a sum of r rank-1 tensors }. Finiteness follows from the standard-basis expansion: each nonzero component contributes one term, so a minimum exists.
- **⟨m,n,p⟩:** the structure tensor of the trilinear form (A,B,C) ↦ Tr(ABC) = Σ A_{ij} B_{jk} C_{ki}. Its three legs are indexed by the matrix-index pairs of A, B, and C; the C leg uses (k,i), according to the trace convention.
- **Exponent set:** { τ | ∃ C, ∀ n, R(⟨n,n,n⟩) ≤ C·n^τ }, with the constant quantified before n as in the standard Big-O definition.
- **ω:** the infimum of this set. The set is nonempty (τ = 3 by the naive algorithm) and bounded below by 0 (rank is always ≥ 1 when n ≥ 1).
- **Conjecture:** ω = 2; given the trivial lower bound ω ≥ 2, this is equivalent to ω ≤ 2. The negation is ω > 2 (a superquadratic lower bound).

## Step 3: Independently drafted types

```
Tensor3 F I J K := (I × J × K) → F
simple u v w := fun (i,j,k) => u i * v j * w k
IsSimple T := ∃ u v w, T = simple u v w
rank T := sInf { r | ∃ s : Fin r → Tensor3, (∀ i, IsSimple (s i)) ∧ T = ∑ i, s i }
MM F m n p : ((Fin m × Fin n) × (Fin n × Fin p) × (Fin p × Fin m)) → F
           := fun ((i,j),(j',k),(k',i')) => if j=j' ∧ k=k' ∧ i=i' then 1 else 0
expSet F := { τ : ℝ | ∃ C, ∀ n : ℕ, (rank (MM F n n n) : ℝ) ≤ C * n^τ }
omega F := sInf (expSet F)
conj := omega ℚ ≤ 2
refuted := ¬ conj
```

## Step 4: Component-by-component comparison with the shipped version

| Component | Draft | Shipped version | Finding |
|---|---|---|---|
| Tensor | (I × J × K) → F | `Tensor3 F ι₁ ι₂ ι₃`, same form as an abbreviation | Match |
| Rank-1 tensor | Pointwise product u·v·w | `simpleTensor` / `IsSimpleTensor`, same form | Match |
| Rank | `sInf` of the set of decomposition lengths | `tensorRank := sInf (decompSet T)`, same form | Match (nonemptiness is proved by `tensorRank_decomp_card`) |
| Multiplication tensor | Same if-expression, with third leg (k,i) | `matMulTensor`, identical form | Match; there is also a sanity lemma `matMulTensor_contract` fixing its correspondence with `Matrix.mul`. |
| Exponent set | ∃ C ∀ n, R ≤ C·n^τ | `omegaSet`, same form | Match |
| ω | `sInf` | `matMulOmega := sInf (omegaSet F)` | Match (`omegaSet_nonempty` and `omegaSet_bddBelow` prove the set is nonempty and bounded below) |
| Conjecture | ω ≤ 2 / negation | `conj` / `refuted`, same form | Match |

There are no disagreements. Two fixed-layer items added in the shipped version but absent from the draft—sanity lemma `matMulTensor_contract` and the API packaging of `matMulOmega_le_of_mem` / `le_matMulOmega_of_forall_le`—do not change the meaning of the conjecture.

## Notes

- The quantifier order in “O(n^τ)” is ∃C∀n (a constant for each τ), matching the standard Big-O definition and the literature. The draft and shipped version agree.
- The range of n includes 0: R(⟨0,0,0⟩) = 0 for the zero tensor on empty index sets, so this does not affect set membership. The paper's “for all n” has the same convention.
- The trivial lower bound ω ≥ 2 from flattening is immediate in the literature but is not formalized in this task (deviation 5 in `concept-ledger`). This does not affect the literature meaning of `conj` or `refuted`.
