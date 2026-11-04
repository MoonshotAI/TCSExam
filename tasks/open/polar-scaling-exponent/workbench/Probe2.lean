import Mathlib

#check @Finset.univ_product_univ
#check @Finset.sum_product'
#check @Finset.sum_product_univ

open Finset in
example {A : Type*} [Fintype A] (F : (A × A) × Fin 2 → ℝ) :
    (∑ y : (A × A) × Fin 2, F y) = ∑ u₁ : Fin 2, ∑ y₁ : A, ∑ y₂ : A, F ((y₁, y₂), u₁) := by
  rw [Finset.univ_product_univ, Finset.sum_product, Finset.sum_comm]
  refine Finset.sum_congr rfl fun u₁ _ => ?_
  rw [Finset.univ_product_univ, Finset.sum_product]

open Finset in
example {A : Type*} [Fintype A] (F : (A × A) → ℝ) :
    (∑ y : A × A, F y) = ∑ y₁ : A, ∑ y₂ : A, F (y₁, y₂) := by
  rw [Finset.univ_product_univ, Finset.sum_product]

-- key-style manipulation
example {A : Type*} [Fintype A] (g : A → ℝ) (h : ∑ y, g y = 1) (u₁ u : Fin 2) :
    ∑ y₁ : A, ∑ y₂ : A, (1 / 2) * g y₁ * g y₂ = 1 / 2 := by
  simp_rw [← Finset.mul_sum, h, mul_one]

-- conv ext under a sum
example {A : Type*} [Fintype A] (g : A → ℝ) :
    (∑ y₁ : A, (1/2) * g y₁) = (1/2) * ∑ y₁ : A, g y₁ := by
  conv_lhs => ext y₁; rw [← Finset.mul_sum]
