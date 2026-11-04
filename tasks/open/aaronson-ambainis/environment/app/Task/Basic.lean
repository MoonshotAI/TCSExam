/-
Statement layer for the Aaronson–Ambainis conjecture (open problem):
Conjecture 1.7 of Aaronson–Ambainis, "The Need for Structure in Quantum
Speedups", Theory of Computing 10(6):133–166, 2014 (arXiv:0911.0996).

Every bounded low-degree polynomial on the Boolean cube has an influential
variable: there is a universal exponent `C` such that for every real
polynomial `p` of degree `≤ d` with `0 ≤ p ≤ 1` on the cube and variance
`≥ ε`, some coordinate `i` has influence `Inf_i[p] ≥ (ε/d)^C`.

Status: open. The random-restriction analogue was proved
by Bhattacharya (ITCS 2025, arXiv:2402.13952); the original conjecture
stands. Dinur–Friedgut–Kindler–O'Donnell 2006 give an influence lower bound
decaying exponentially in `d`; the conjecture asks for polynomial decay.

The fixed part (everything above the end-of-fixed-part marker line) is the
definition layer the statements need. Influences are the paper's
L2-influences `Inf_i[p] = E[(p(X) − p(X^i))²]` — expected *squared*
difference under flipping bit `i` (the §1.2 display; the paper's §1.3 notes
the L2 form is provably equivalent to the L1 form of earlier versions).
Fidelity notes live in `tests/reference/`.
-/

import Mathlib

namespace AaronsonAmbainis

/-! ## Cube points and the ±1 embedding -/

/-- The ±1 embedding of a Boolean: `true ↦ 1`, `false ↦ −1`. -/
def pmOne (b : Bool) : ℝ := if b then 1 else -1

/-- Pointwise ±1 embedding of a cube point into `Fin n → ℝ`. -/
def cubeEmbed {n : ℕ} (x : Fin n → Bool) : Fin n → ℝ := fun i => pmOne (x i)

/-- Flip the `i`-th bit of a cube point (the paper's `X ↦ X^i`). -/
def flipAt {n : ℕ} (x : Fin n → Bool) (i : Fin n) : Fin n → Bool :=
  Function.update x i (!(x i))

/-! ## Uniform expectation, variance, influence -/

/-- Uniform expectation of a real function over the cube `{±1}ⁿ`. -/
noncomputable def cubeAvg {n : ℕ} (f : (Fin n → Bool) → ℝ) : ℝ :=
  (∑ x : Fin n → Bool, f x) / 2 ^ n

/-- Expectation `E[p]` of a polynomial over the uniform cube. -/
noncomputable def cubeExpect {n : ℕ} (p : MvPolynomial (Fin n) ℝ) : ℝ :=
  cubeAvg fun x => MvPolynomial.eval (cubeEmbed x) p

/-- Variance `Var[p] = E[(p(X) − E[p])²]` over the uniform cube. -/
noncomputable def cubeVariance {n : ℕ} (p : MvPolynomial (Fin n) ℝ) : ℝ :=
  cubeAvg fun x => (MvPolynomial.eval (cubeEmbed x) p - cubeExpect p) ^ 2

/-- Influence of coordinate `i`: `Inf_i[p] = E[(p(X) − p(X^i))²]`, the
expected squared difference when bit `i` is flipped (Aaronson–Ambainis §1.2;
their `X^i` is `flipAt x i`). -/
noncomputable def cubeInfluence {n : ℕ} (p : MvPolynomial (Fin n) ℝ) (i : Fin n) : ℝ :=
  cubeAvg fun x =>
    (MvPolynomial.eval (cubeEmbed x) p - MvPolynomial.eval (cubeEmbed (flipAt x i)) p) ^ 2

/-- `p` is bounded: `0 ≤ p(X) ≤ 1` at every cube point. -/
def BoundedOnCube {n : ℕ} (p : MvPolynomial (Fin n) ℝ) : Prop :=
  ∀ x : Fin n → Bool,
    0 ≤ MvPolynomial.eval (cubeEmbed x) p ∧ MvPolynomial.eval (cubeEmbed x) p ≤ 1

/-- `p` is symmetric on the cube: its value depends only on the Hamming
weight (number of `true` bits). -/
def IsSymmetricOnCube {n : ℕ} (p : MvPolynomial (Fin n) ℝ) : Prop :=
  ∀ x y : Fin n → Bool,
    (Finset.univ.filter fun i => x i = true).card =
      (Finset.univ.filter fun i => y i = true).card →
    MvPolynomial.eval (cubeEmbed x) p = MvPolynomial.eval (cubeEmbed y) p

/-- The 0/1-valued dictator on coordinate 0, `(1 + X₀)/2`, as a polynomial. -/
noncomputable def dictatorPoly {n : ℕ} (hn : 0 < n) : MvPolynomial (Fin n) ℝ :=
  MvPolynomial.C (1 / 2 : ℝ) * (1 + MvPolynomial.X ⟨0, hn⟩)

/-- The Aaronson–Ambainis conjecture (Conjecture 1.7 of [AA14]): there is a
universal exponent `C` such that every bounded polynomial of degree `≤ d`
with variance `≥ ε` has a coordinate of influence `≥ (ε/d)^C`. -/
def Conjecture : Prop :=
  ∃ C : ℕ,
    0 < C ∧
      ∀ {n : ℕ} (p : MvPolynomial (Fin n) ℝ) (d : ℕ) (ε : ℝ),
        0 < d →
          0 < ε →
            p.totalDegree ≤ d →
              BoundedOnCube p →
                ε ≤ cubeVariance p →
                  ∃ i : Fin n, (ε / (d : ℝ)) ^ C ≤ cubeInfluence p i

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- but the fixed part above and the theorem statements must not be modified.

/-- Prove the conjecture (full score). -/
theorem conj : Conjecture := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

/-- Or refute it (full score). -/
theorem refuted : ¬ Conjecture := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

end AaronsonAmbainis
