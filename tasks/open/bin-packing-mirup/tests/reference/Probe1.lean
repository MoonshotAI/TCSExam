import Task.Basic

namespace BinPackingMIRUP

-- probe 1: the big kernel enumeration behind mirup_tight's integer lower bound
example : ¬ PacksIn instC 3 := by decide

-- probe 2: the LP certificates for instC
example : IsFracCover instC (fun p =>
    if p = ({0, 4, 5, 6} : Finset (Fin 10)) then 1/3
    else if p = {1, 3, 5, 7} then 1/3
    else if p = {1, 2, 6, 7} then 1/3
    else if p = {1, 2, 5, 8} then 1/3
    else if p = {3, 6, 8} then 1/3
    else if p = {0, 7, 8} then 1/3
    else if p = {0, 2, 3, 9} then 1/3
    else if p = {4, 9} then 2/3
    else 0) := by decide

example : ∀ p ∈ patterns instC,
    ∑ i ∈ p, (![0, 0, 0, 0, 0, 1/2, 1/2, 1/2, 1/2, 1] : Fin 10 → ℚ) i ≤ 1 := by decide

example : (∑ p ∈ patterns instC, (fun p =>
    if p = ({0, 4, 5, 6} : Finset (Fin 10)) then 1/3
    else if p = {1, 3, 5, 7} then 1/3
    else if p = {1, 2, 6, 7} then 1/3
    else if p = {1, 2, 5, 8} then 1/3
    else if p = {3, 6, 8} then 1/3
    else if p = {0, 7, 8} then 1/3
    else if p = {0, 2, 3, 9} then 1/3
    else if p = {4, 9} then 2/3
    else 0) p) = 3 := by decide

-- probe 3: small-instance decides
example : ¬ PacksIn instB1 1 := by decide
example : PacksIn instB1 2 := by decide
example : PacksIn instC 4 := by decide

end BinPackingMIRUP
