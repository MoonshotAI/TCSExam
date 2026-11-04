import Mathlib

open Finset in
#check @Finset.mul_sum
#check @Finset.sum_mul
#check @Finset.sum_product
#check @Finset.sum_product'
#check @Finset.sum_comm
#check @Fintype.sum_option
#check @Finset.sum_insertNone
#check @Fin.sum_univ_two
#check @Finset.univ_option
#check @Filter.liminf
#check @Filter.limsup
#check @Matrix.kronecker
#check @Matrix.kronecker_apply
#check @Matrix.submatrix
#check @Equiv.swap_involutive
#check @Equiv.optionCongr
#check @finProdFinEquiv
#check @pow_succ'
#check @pow_succ
#check @Equiv.cast
#check @Real.sqrt_mul_self
#check @Real.sqrt_sq
#check @Real.sqrt_mul
#check @Real.sq_sqrt
#check @Real.sqrt_nonneg
#check @Real.logb
#check @List.ofFn
#check @Finset.sum_mul_sq_le_sq_mul_sq
#check @Equiv.prodCongr
#check @Equiv.prodComm
#check @Equiv.refl
#check @Equiv.trans
#check @Function.Involutive
#check @Equiv.Perm
#check @Fin.sum_univ_two
example : (∑ i : Fin 2, (1:ℝ)) = 2 := by norm_num [Fin.sum_univ_two]
example (f : Option (Fin 2) → ℝ) : ∑ o, f o = f none + f (some 0) + f (some 1) := by
  rw [Fintype.sum_option, Fin.sum_univ_two]; ring
