# Statement Ledger: Mansour's Conjecture

This note explains the task statement for readers comparing the mathematical definitions with the Lean source. The current scoring statements are `conj` and `refuted`; proving either earns full credit.

This ledger compares the literature statement of Mansour's conjecture (Fourier concentration for DNF formulas) with the Lean statement in this proof-conjecture task, and records every deviation and its rationale. It is intended for task authors and reviewers as one of the three fidelity records (the component-by-component ledger).

Sources: survey `learning-theory-boolean-testing.md` (short name `mansour-conjecture`; includes source, evidence that the conjecture is open, known bounds, and overlap checks with FC); Mansour, COLT 1992 / JCSS 1995; the complete statement is taken from the Simons Institute collection *Real Analysis in Computer Science: A Collection of Open Problems* and O'Donnell, *Analysis of Boolean Functions*, §4.4. The original Simons PDF was opened and checked word for word on 2026-09-05: “Let f : {−1,1}ⁿ → {−1,1} be computable by a DNF of size s > 1 and let ε ∈ (0, 1/2]. Then f's Fourier spectrum is ε-concentrated on a collection ℱ with |ℱ| ≤ s^{O(log(1/ε))}.”

Shipped statement: `environment/app/Task/Basic.lean` (identical, character for character, to the scoring copy in `tests/reference/Basic.lean`).

## 1. Published statement and Lean correspondence

The literature statement (Simons Institute collection, consistent with O'Donnell §4.4) is: let f : {±1}ⁿ → {±1} be computable by a DNF of size s > 1, and let ε ∈ (0, 1/2]. Then f's Fourier spectrum is ε-concentrated on a set of coefficients ℱ with |ℱ| ≤ s^{O(log(1/ε))}. Here f's Fourier coefficient is f̂(S) = E[f(X)·χ_S(X)], where χ_S(X) = ∏_{i∈S} X_i and X is uniform on {±1}ⁿ. “ε-concentrated on ℱ” means Σ_{S∉ℱ} f̂(S)² ≤ ε. The size of a DNF is its number of terms; each term is a conjunction of literals, and a DNF is a disjunction of terms.

| Concept | Literature | Lean identifier in this task | Notes |
|---|---|---|---|
| Cube point | X ∈ {±1}ⁿ (or {0,1}ⁿ) | `x : Fin n → Bool` | Bool and ±1 values are interconverted by `pmOne`; the spectrum is invariant under the isomorphism. |
| ±1 embedding | +1 / −1 | `pmOne : Bool → ℚ` (theory layer), `pmOneZ : Bool → ℤ` (computation layer) | See deviation 3. |
| Character | χ_S(X) = ∏_{i∈S} X_i | `chi S x := ∏ i ∈ S, pmOne (x i)` (over ℚ), `chiZ` (over ℤ) | |
| Fourier coefficient | f̂(S) = E[f·χ_S] = 2⁻ⁿ Σ f(X)χ_S(X) | `fourierCoeff f S := cubeAvg fun x => f x * chi S x` (over ℚ) | Expectation under the uniform distribution. |
| Spectral concentration | Σ_{S∉ℱ} f̂(S)² ≤ ε | `SpectralConcQ` (ε : ℚ, used by checkpoints), `SpectralConc` (ε : ℝ, used by the conjecture, via coercion) | See deviation 3. |
| DNF | Disjunction of terms; each term is a conjunction of literals; size is the number of terms | `D : List (Term n)`; `Term n = {pos, neg : Finset (Fin n)}` (positive/negative literal sets); size `D.length`; computed function `dnfFun D` (±1-valued) | See deviation 1. |
| Conjecture | ∃ universal C; for every DNF with s > 1 and every ε ∈ (0, 1/2], there is ℱ with concentration and |ℱ| ≤ s^{C·log(1/ε)} | `Conjecture`: `∃ C : ℕ, ∀ D, 1 < D.length → ∀ ε : ℝ, 0 < ε → ε ≤ 1/2 → ∃ ℱ, SpectralConc (dnfFun D) ε ℱ ∧ (ℱ.card : ℝ) ≤ (D.length : ℝ)^((C:ℝ)·Real.log (1/ε))` | See deviation 2. |
| Spectrum of a single term | Fourier expansion of a conjunction (textbook lemma) | Checkpoint c1 `single_term_spectrum` and fixed definitions `Term.ind_eq_sum`/`Term.ind_coeff`/`dnfFun_single_expansion` | For a term of width w: f̂(∅) = 2^{1−w} − 1; f̂(S) = (−1)^{|S∩neg|}·2^{1−w} when ∅ ≠ S ⊆ vars; all other coefficients are 0. |
| Spectrum of a decision tree | Fourier degree is at most the decision-tree depth | Checkpoint c3 `dtree_exact_concentration` and fixed definitions `DTree`/`lowDegree` | The spectrum is 0-concentrated on {S : |S| ≤ d}. |

## 2. Deviations and rationale

1. **The conjecture quantifies directly over DNF syntax rather than over functions with a size-s representation.** The literature quantifies over every f computed by a DNF of size s. These formulations are equivalent: each DNF D computes `dnfFun D`; conversely, saying “f is computed by D” means f = dnfFun D, and equal functions have the same spectrum. Quantifying over syntax avoids an existential wrapper and is standard in formalization. Terms are represented by `List (Term n)` (so repeated terms are allowed), rather than a Finset, matching the usual definition of size as the number of terms. The condition s > 1 is written `1 < D.length`. Positive and negative literals are each represented by a Finset. Inconsistent terms (containing both signs of one variable) are allowed and are unsatisfiable; when needed, such as for the single-term expansion lemma, the task explicitly assumes `T.Consistent`.

2. **The big-O bound is made explicit.** The bound `s^{O(log(1/ε))}` is written as “there is a universal natural number C such that |ℱ| ≤ s^(C·log(1/ε)).” Two points justify this. (a) The hidden multiplicative constant C′ in the big-O can be absorbed into the exponent C: since s > 1, take C″ = C + log C′/log s (and s ≥ 2 ensures log s > 0). The literature's condition s > 1 is what makes this absorption valid. (b) The logarithm base (natural log `Real.log` versus base 2) is also absorbed into C and does not affect the truth of the conjecture.

3. **Use two coefficient layers (ℚ for theory and ℤ for computation).** Spectral theory (orthogonality, inversion, Parseval, linearity, and shift rules) is developed over ℚ, matching the literature. The conjecture's concentration and cardinality bound use ℝ via coercion, because ε is an arbitrary real. However, Lean's kernel does not reduce Rat arithmetic (as tested: `decide` does not reduce even `(1:ℚ) + 1 = 2`, while the ℤ version succeeds; `native_decide` is prohibited by the lexical scan for this task family). Therefore, numerical content that the kernel must decide, such as the checkpoint c2 coefficient table, is stated using the integer numerator `fourierNum f S = Σ_x f(x)·χ_S(x) = 2^n·f̂(S)`, with `fourierCoeff_dnfFun_eq_num` bridging back to ℚ. The spectral-concentration definition remains in its ℚ/ℝ form, without rescaling. The concentration part of c2 is proved using a complement-set equality (checked by `decide`), the bridge lemma, and `norm_num`.

4. **“ε-concentrated” uses the standard definition:** Σ_{S∉ℱ} f̂(S)² ≤ ε, the squared-mass tail. This matches O'Donnell's textbook definition exactly.

5. **The ±1 output convention:** A satisfied DNF outputs +1, and an unsatisfied DNF outputs −1. Reversing this convention only negates every coefficient, leaving all squared mass unchanged and thus not affecting spectral concentration.

6. **Checkpoint c2's concrete example** (`selector:x₀x₁ ∨ ¬x₀x₂`) is a task example, not one from the literature. It was chosen because its two terms are disjoint (mutually exclusive) and its spectrum has exactly four nonzero coefficients (each ±1/2), making it the smallest nontrivial DNF that demonstrates a spectrum spread across multiple coefficients. The values were independently recomputed in Python (`tests/reference/fourier_small_examples.py`; all checks passed) and checked again by kernel `decide`.

## 3. Distinguishing related problems

- **FEI (Fourier Entropy–Influence conjecture):** FEI implies a weaker form of Mansour's conjecture, s^{O(1/ε)} (as noted in the Simons Institute collection; FEI is a separate task in this repository). The two conjectures are distinct.
- **Linial–Mansour–Nisan low-degree concentration:** LMN gives concentration of DNF Fourier coefficients on low degrees (degree O(log(s/ε)·log(1/ε))) and yields a quasipolynomial learning algorithm. Mansour's conjecture does not require the concentrated set to be low-degree and bounds its cardinality more tightly. The definition `lowDegree` is used only by the decision-tree checkpoint and is not the LMN statement.
- This is a **decision problem about a structural statement** whose truth is open: either prove it for all DNFs or refute it with a counterexample sequence that can be checked mechanically.

## 4. Current bounds and source checks

Checked against the survey and arXiv abstracts.

- Best known general DNF bound: ε-concentration on (s/ε)^{O(log log(s/ε)·log(1/ε))} coefficients (Mansour 1992/1995). Lecomte–Tan 2021 (arXiv:2109.04525; abstract checked) replaces log log s by log log k, where k is the read count, and reaches the optimal poly(s) bound when k ≲ log log s. Its conclusion still says, “the obvious open problem is to prove Mansour's conjecture.”
- The conjecture is proved for random DNF (Klivans–Lee–Wan, COLT 2010) and monotone DNF (O'Donnell–Servedio 2003).
- A lower-bound scale: for the tribes function (a read-once DNF with disjoint terms and w = log s), a constant ε requires s^{Ω(1)} coefficients (reproducible in Python). Thus poly(s) is the right logarithmic scale; the conjecture cannot be strengthened to polylog(s) coefficients.
- New work on FEI in 2025 (arXiv:2511.07739) still uses random DNF as a special-case reference; no result resolving Mansour's conjecture was found.
