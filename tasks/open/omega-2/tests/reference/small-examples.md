# Executable Small Examples — Behavioral Checks for the Matrix-Multiplication Exponent Definition Layer

Kernel-executable checks (pointwise evaluation, numerical bounds from a naive construction, and axiom audits) exercise Lean definitions and record the actual output; they serve as unit tests for the definition layer.

- Test file: `tasks/omega-2/workbench/probe/Probe.lean`, compiled with `lake env lean` inside the positive-control candidate at `workbench/build-ref/`, using a Lean validation image, mathlib pinned at 5b3f719, and toolchain leanprover/lean4:v4.33.0-rc1.

## Design notes

Tensor values are conditional expressions (`if j = j' ∧ k = k' ∧ i = i' then 1 else 0`). The condition uses only equality on `Fin` values, which the kernel reduces, so **pointwise evaluation can use `rfl`** (the `if` simplifies without rational arithmetic). The sandbox toolchain's kernel does not reduce ℚ, so `decide` cannot prove rational identities (a known environment issue from the task brief); `rfl`/`if_pos` evaluation does not perform ℚ arithmetic and is unaffected. The 64-point Strassen identity in the checkpoint proof is handled by `fin_cases` + `simp` (with fallback `norm_num`); every result is a kernel-checkable proof term, so the `#print axioms` whitelist is unaffected.

## Small-example table (; all passed)

| ID | Check | Hand-computed expectation | Actual result |
|---|---|---|---|
| P1 | Value of MM(1,1,1) at its only point ((0,0),(0,0),(0,0)) | 1 (all contraction conditions hold) | `by rfl` passes ✓ |
| P2 | MM(2,2,2) at a non-contraction point ((0,1),(0,0),(0,0)) (j=1 ≠ 0=j′) | 0 | `by rfl` passes ✓ |
| P3 | MM(2,2,2) at a contraction point ((0,0),(0,1),(1,0)) (j=j′, k=k′, i=i′) | 1 | `by rfl` passes ✓ |
| P4 | Naive upper bound for n=2 (compare with Strassen ≤ 7) | R ≤ 8 | Passes using `tensorRank_matMulTensor_le` from the pinned zone + `omega` ✓ |
| P5 | Axiom audit of the three checkpoint proofs and key pinned-zone lemmas | Only propext / Classical.choice / Quot.sound | All seven `#print axioms` checks contain exactly those three axioms ✓ (`mm_tensorRank_le_cube`, `mm111_tensorRank`, `strassen_tensorRank_le`, `strassen_identity`, `matMulOmega_le_three`, `tensorRank_matMulTensor_le`, `omegaSet_bddBelow`) |

## Issues found

- **Omitted term on the third leg of w₂** (see above): collect each M's coefficient term by term from the four product expressions: C₁₁ = M₁+M₄−M₅+M₇, C₁₂ = M₃+M₅, C₂₁ = M₂+M₄, C₂₂ = M₁−M₂+M₃+M₆. Do not write coefficients by intuition about “which C term contains M.”
- **Effect of the environment's inability to use `decide` over ℚ:** c3's pointwise verification cannot rely on `decide`; the reference proof uses `simp`/`norm_num` throughout (reflective, kernel-checkable). The environment section of `instruction.md` tells the solving model this explicitly to prevent wasting effort on `decide`.
