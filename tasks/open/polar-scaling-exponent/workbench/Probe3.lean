import Task.Basic

namespace PolarScaling

-- P1: bitRev 2 is the permutation [0↦0, 1↦2, 2↦1, 3↦3]
example : bitRev 2 0 = 0 ∧ bitRev 2 1 = 2 ∧ bitRev 2 2 = 1 ∧ bitRev 2 3 = 3 := by decide

-- P2: the generator matrix at block length 2 is the Arikan kernel itself
example : polarGen 1 = polarKernel := by decide

-- P4: BEC(1/4) transition values
example : (BEC (1/4 : ℝ) (by norm_num) (by norm_num)).toFun 0 (some 0) = 3/4 := by
  simp only [BEC_apply_some]; norm_num
example : (BEC (1/4 : ℝ) (by norm_num) (by norm_num)).toFun 1 (some 0) = 0 := by
  simp only [BEC_apply_some]; norm_num
example : (BEC (1/4 : ℝ) (by norm_num) (by norm_num)).toFun 1 none = 1/4 := by
  simp only [BEC_apply_none]

-- P5: Z of BEC(1/4) via the checkpoint theorem
example : Z (BEC (1/4 : ℝ) (by norm_num) (by norm_num)) = 1/4 :=
  bec_bhattacharyya _ _ _

-- P6: one polarization step on BEC(1/4): 2·(1/4) − (1/4)² = 7/16 and (1/4)² = 1/16
example : Z (polarMinus (BEC (1/4 : ℝ) (by norm_num) (by norm_num))) = 7/16 := by
  rw [(bec_polar_step _ _ _).1]; norm_num
example : Z (polarPlus (BEC (1/4 : ℝ) (by norm_num) (by norm_num))) = 1/16 := by
  rw [(bec_polar_step _ _ _).2]; norm_num

-- P7: the BEC is output-symmetric (IsBMS is inhabited as intended)
example : IsBMS (BEC (1/2 : ℝ) (by norm_num) (by norm_num)) := isBMS_BEC _ _ _

-- P8: pointwise W⁻-summand at (none, some 0) for ε = 1/4 is (1/2)·(1/4)·(3/4) = 3/32
example : Real.sqrt ((polarMinus (BEC (1/4 : ℝ) (by norm_num) (by norm_num))).toFun 0 (none, some 0)
      * (polarMinus (BEC (1/4 : ℝ) (by norm_num) (by norm_num))).toFun 1 (none, some 0))
    = 3/32 := by
  rw [BEC_minus_summand]; norm_num

-- P9: G₄ again as a plain probe (same mechanism as checkpoint c3)
example : polarGen 2 = !![1, 0, 0, 0; 1, 0, 1, 0; 1, 1, 0, 0; 1, 1, 1, 1] := by decide

end PolarScaling
