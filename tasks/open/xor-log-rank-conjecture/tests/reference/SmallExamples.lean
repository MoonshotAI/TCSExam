/-
Kernel-decidable probe for the XOR log-rank task definition layer.

Every assertion is closed by `decide` (kernel computation only;
`native_decide` is never used). Run inside the task app:

    lake env lean tests/reference/SmallExamples.lean

The expected values are recorded in `tests/reference/small-examples.md`.
-/

import Task.Basic

open XorLogRank

-- The ±1 form of fpar2 is −χ_{0,1}: integer numerators of its Fourier
-- coefficients are 0 on ∅, {0}, {1} and −4 on {0,1} (the coefficients
-- themselves are the numerators over 2² = 4, i.e. −1 on {0,1} and 0 else).
example : fourierNum (boolSignZ fpar2) (∅ : Finset (Fin 2)) = 0 := by decide
example : fourierNum (boolSignZ fpar2) ({0} : Finset (Fin 2)) = 0 := by decide
example : fourierNum (boolSignZ fpar2) ({1} : Finset (Fin 2)) = 0 := by decide
example : fourierNum (boolSignZ fpar2) ({0, 1} : Finset (Fin 2)) = -4 := by decide

-- Hence the kernel-computable sparsity of fpar2 is 1 (this is the ℤ-layer
-- count; `sparsity_eq_filter_num` bridges it to `sparsity fpar2`).
example : (Finset.univ.filter fun S : Finset (Fin 2) =>
    fourierNum (boolSignZ fpar2) S ≠ 0).card = 1 := by decide

-- The constant-true function on Fin 2 has a single nonzero coefficient:
-- the empty character, with numerator 4 (coefficient 1).
example : fourierNum (boolSignZ fun (_ : Fin 2 → Bool) => true) (∅ : Finset (Fin 2)) = 4 := by
  decide
example : (Finset.univ.filter fun S : Finset (Fin 2) =>
    fourierNum (boolSignZ fun (_ : Fin 2 → Bool) => true) S ≠ 0).card = 1 := by decide

-- Parity query truth table on Fin 2 (answer = "χ_{0,1}(x) = +1").
example : parityQuery ({0, 1} : Finset (Fin 2)) ![true, true] = true := by decide
example : parityQuery ({0, 1} : Finset (Fin 2)) ![true, false] = false := by decide
example : parityQuery ({0, 1} : Finset (Fin 2)) ![false, true] = false := by decide
example : parityQuery ({0, 1} : Finset (Fin 2)) ![false, false] = true := by decide

-- The depth-1 tree querying {0,1} computes fpar2 (hi on even parity).
example : (ParityTree.node ({0, 1} : Finset (Fin 2)) (.leaf true) (.leaf false)).Computes
    fpar2 := by
  unfold ParityTree.Computes
  decide
example : (ParityTree.node ({0, 1} : Finset (Fin 2)) (.leaf true) (.leaf false)).depth = 1 := by
  decide

-- A bare leaf computes the constant function in depth 0.
example : (ParityTree.leaf true : ParityTree 2).Computes (fun _ => true) := by
  unfold ParityTree.Computes
  decide
example : (ParityTree.leaf true : ParityTree 2).depth = 0 := by decide
