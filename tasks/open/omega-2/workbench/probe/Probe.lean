import Task.Basic

open MatMulOmega

-- P1: MM(1,1,1) at the unique point evaluates to 1 (kernel reduction of the
-- if-condition; no rational arithmetic needed)
example : matMulTensor ℚ 1 1 1 ((0, 0), (0, 0), (0, 0)) = 1 := by rfl

-- P2: an off-contraction point of MM(2,2,2) evaluates to 0 (j ≠ j')
example : matMulTensor ℚ 2 2 2 ((0, 1), (0, 0), (0, 0)) = 0 := by rfl

-- P3: a valid contraction point evaluates to 1 (j = j', k = k', i = i')
example : matMulTensor ℚ 2 2 2 ((0, 0), (0, 1), (1, 0)) = 1 := by rfl

-- P4: the naive bound at n = 2 gives ≤ 8 (Strassen improves to 7)
example : tensorRank (matMulTensor ℚ 2 2 2) ≤ 8 := by
  have h := tensorRank_matMulTensor_le (F := ℚ) 2 2 2
  omega

-- P5: axiom audit of the three reference checkpoint proofs and the
-- fixed-zone omega sanity lemma (all must be the three standard axioms)
#print axioms MatMulOmega.mm_tensorRank_le_cube
#print axioms MatMulOmega.mm111_tensorRank
#print axioms MatMulOmega.strassen_tensorRank_le
#print axioms MatMulOmega.strassen_identity
#print axioms MatMulOmega.matMulOmega_le_three
#print axioms MatMulOmega.tensorRank_matMulTensor_le
#print axioms MatMulOmega.omegaSet_bddBelow
