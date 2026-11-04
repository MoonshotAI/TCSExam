# Independent Retranslation: Mansour's Conjecture

This record derives a formalization draft from the literature without consulting the shipped Lean file, then compares the two component by component. It is the third fidelity record (independent retranslation).

- Source: the original statement in the “Mansour's Conjecture” section of the Simons Open Problems collection, checked character by character against the PDF. The paraphrase in `learning-theory-boolean-testing.md` matches it.

## Step 1: Source statement (Simons Open Problems, “Mansour's Conjecture”)

> “Let f : {−1, 1}ⁿ → {−1, 1} be computable by a DNF of size s > 1 and let ε ∈ (0, 1/2]. Then f's Fourier spectrum is ε-concentrated on a collection ℱ with |ℱ| ≤ s^{O(log(1/ε))}.”

The source cites [Man94]. Its note says a weaker form is s^{O_ε(1)}, and the weaker form s^{O(1/ε)} follows from FEI. Random DNFs were already handled by Klivans–Lee–Wan. Mansour [Man95] proved the upper bound (s/ε)^{O(log log(s/ε)·log(1/ε)).

## Step 2: Natural-language refinement (resolving ambiguities)

- **DNF:** a disjunction (OR) of terms, where each term is a conjunction (AND) of literals and a literal is a variable x_i or its negation ¬x_i. The size s is the number of terms, and s > 1.
- **“f is computed by this DNF”:** for every input X, f(X) = +1 iff some term is satisfied (the ±1 output convention is explained in the deviation notes).
- **Fourier coefficient:** f̂(S) = E_X[f(X)·χ_S(X)], where χ_S(X) = ∏_{i∈S} X_i, X is uniform on {±1}ⁿ, and S ⊆ [n].
- **ε-concentrated on ℱ:** Σ_{S∉ℱ} f̂(S)² ≤ ε (the mean-square tail mass; Parseval gives total mass E[f²] = 1).
- **Big-O:** there is a constant independent of n, s, and ε such that |ℱ| is bounded by s^{O(log(1/ε))}.

## Step 3: Independently drafted types

```
Cube point: x : Fin n → Bool (embed ±1 via pmOne)
chi S x := ∏ i ∈ S, pmOne (x i)
fHat f S := 2^{-n} · Σ_x f x · chi S x
concentrated f ε ℱ := Σ_{S ∉ ℱ} (fHat f S)² ≤ ε
Term := (pos, neg : Finset (Fin n)); sat T x := (∀ i ∈ pos, x i) ∧ (∀ j ∈ neg, ¬ x j)
DNF := List Term; size = length
dnfFun D x := if some term is satisfied then 1 else -1
Conjecture := ∃ C, ∀ (D : DNF), length D > 1 → ∀ ε ∈ (0, 1/2],
          ∃ ℱ, concentrated (dnfFun D) ε ℱ ∧ |ℱ| ≤ (length D)^{C·log(1/ε)}
```

## Step 4: Component-by-component comparison with the shipped version

| Component | Draft | Shipped version | Finding |
|---|---|---|---|
| Cube and characters | Fin n → Bool, with products of `pmOne` | Same (`chi`) | Match |
| Fourier coefficient | 2⁻ⁿ Σ f·χ_S | `fourierCoeff f S := cubeAvg (fun x => f x * chi S x)` (`cubeAvg` = Σ/2ⁿ) | Match |
| Concentration | Σ_{S∉ℱ} f̂² ≤ ε | `SpectralConcQ` (ℚ) / `SpectralConc` (ℝ, cast) | Match (the conjecture uses the ℝ version because ε is real). |
| Term / satisfaction | Separate positive- and negative-literal sets | Same (`Term` / `Term.Sat`) | Match |
| DNF / size / function | List, length, if-then-else | Same (`dnfFun`, `pmOne (decide (DNFSat D x))`) | Match |
| Conjecture quantifiers | ∃ C, ∀ D(s>1), ∀ ε∈(0,1/2], ∃ ℱ | Same (`Conjecture`, with ε : ℝ and 0 < ε → ε ≤ 1/2) | Match |
| Upper bound | s^{C·log(1/ε)} | (D.length : ℝ)^((C:ℝ)·Real.log (1/ε)) | Match (log-base changes are absorbed by the Big-O constant; see deviation 2 in `concept-ledger`). |

There are no disagreements. Packaging choices (quantifying directly over DNF syntax, the ±1 output convention, and the ℤ computation layer) preserve meaning; see deviations 1/3/5 of `concept-ledger.md`.

## Notes

- The source's `(s/ε)^{O(log log(s/ε) log(1/ε))}` is Mansour's proved upper bound in the notes, not the conjecture itself. The shipped `Conjecture` contains only the conjectured s^{O(log(1/ε))} form; the proved upper bound is omitted from the statement layer because it does not affect truth, only the perceived difficulty.
- The conjecture has one existential constant C and no hidden second constant (the multiplicative constant is absorbed since s > 1; see deviation 2 of `concept-ledger`). `refuted` is its literal negation.
