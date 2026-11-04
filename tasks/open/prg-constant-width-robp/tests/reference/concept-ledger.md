# Faithfulness Review: A Width-4 PRG for Constant-Width ROBPs

This note explains the task statement for readers comparing the mathematical definitions with the Lean source. The current scoring statements are `conj` and `refuted`; proving either earns full credit.

This document compares the literature statement with the Lean statement used by this task, records every deviation and its rationale, and points to the supporting sources.

- **Primary literature:** Nisan 1992 (*Combinatorica* 12(4):449–461); Braverman–Rao–Raz–Yehudayoff (FOCS 2010 / SICOMP 43(3):973–986, 2014); Forbes–Kelley (FOCS 2018, arXiv:1808.06265); Bogdanov–Dvir–Verbin–Yehudayoff (*Theory Comput.* 9:283–293, 2013); Meka–Reingold–Tal (STOC 2019, arXiv:1806.04256); Doron–Hoza (APPROX/RANDOM 2025, LIPIcs 353:28); Lee–Viola (CCC 2025, LIPIcs 339:9).
- **Released statement:** `environment/app/Task/Basic.lean`; its fixed region matches the fixed region in the scoring model `tests/reference/Basic.lean` word for word.

## 1. Literature statement and Lean correspondence

The survey gives the standard literature statement: for constant width (w ≥ 4), construct an explicit pseudorandom generator (PRG) that fools every standard ordered read-once branching program (ROBP) of width (w) and length (n), with error (1/n) and seed length (o(log^2 n)). Following the task design, the width is fixed to (w=4), the first fully open width. We do not use the weakened statement “there exists some (w ≥ 4),” which would allow the freedom to choose (w) to dilute the problem.

| Concept | Literature | Lean identifier in this task | Notes |
|---|---|---|---|
| Standard ordered ROBP | A directed graph with (n+1) layers, at most (w) nodes per layer; each node in layer (i) has two outgoing edges labeled 0 and 1 to layer (i+1); layer (i) reads input bit (x_i); layer 0 has one start node; the last layer is partitioned into accepting and rejecting nodes. | `structure ROBP n w`: `step : Fin n → Fin w → Bool → Fin w`, `start : Fin w`, `accept : Fin w → Bool` | See deviations 1 (normalizing to exactly (w) states) and 2 (accepting-state convention). |
| Computation | On input (x), follow the edge labeled (x_i) from the start node; acceptance is determined by the state reached in the last layer. | `B.run x` (a `List.foldl` over `List.finRange n`) | |
| Acceptance probability | Probability of acceptance for uniform input (x ≤ftarrow {0,1}^n). | `B.acceptProb : ℚ` (= `acceptCount / 2ⁿ`, an exact finite counting ratio) | See deviation 6 ((ℚ), not (ℝ)). |
| PRG | (G : {0,1}^s → {0,1}^n). | `G : (Fin s → Bool) → (Fin n → Bool)` | |
| (ε)-fooling | (|Pr[B(G(U_s))=1] - Pr[B(U_n)=1]| ≤ ε). | `B.Fools ε G := |B.fooledProb G - B.acceptProb| ≤ ε` | |
| Explicitness | “Explicit” means computable by an algorithm in `poly(n)` time, where (n) is the output length and is given in unary. | `Explicit s G`: there are a single-tape Turing machine (M) and constants (c,k) such that for every (n ≥ 1), seed (y), and bit index (i), (M) halts within (k n^c) steps on `encodeInput` (the unary-tape encoding of (n,y,i)) and the head reads the value (G,n,y,i). | See deviation 3 (explicitness must be part of the statement). |
| Seed length (o(log^2 n)) | (s(n)=o(log^2 n)). | `Filter.Tendsto (fun n => (s n : ℝ) / (Real.log n)^2) Filter.atTop (nhds 0)` | See deviation 4. |
| Error (1/n) | (ε=1/n) for all sufficiently large (n). | `∀ n ≥ 1, ∀ B : ROBP n 4, B.Fools (1/(n:ℚ)) (G n)` | See deviation 5 (all (n) versus all sufficiently large (n)). |
| Conjecture | There is an explicit generator family of width 4 satisfying the three conditions above. | `theorem conj`; `theorem refuted` is its literal negation. | |

## 2. Deviations and rationale

1. **Exactly (w) states per layer (the literature allows at most (w)).** Any program with at most (w) states can be extended to exactly (w) states by adding unreachable dummy states. Their transitions are arbitrary, the start state cannot reach them, and the computation is unchanged. Thus both models compute the same functions and define the same fooling problem. The normalization gives one uniform `Fin w` type throughout the definitions, without a family of per-layer finite sets.

2. **Accepting states are represented as a subset of the last layer** (`accept : Fin w → Bool`). The two common literature conventions—“a set of accepting states in the last layer” and “an accepting sink”—are equivalent for finite layered programs: a sink is the special case with one accepting state in the last layer. This task uses the first convention, which includes the second.

3. **Explicitness is formalized with a single-tape Turing machine and a polynomial time bound.** This is the only component where the formal statement makes a substantive choice of convention, so the rationale is detailed here.
   - A pure existence statement that omits “explicit” is true by a counting argument, contradicting the intended open problem. There are at most (2^{16n+O(1)}) width-4 programs of length (n). Hoeffding’s inequality and a union bound show that a random (G) has positive probability of fooling all of them with seed length (O(log(n/ε^2))). For (ε=1/n), this gives (s=O(log n) ≪ o(log^2 n)). The abstract of Forbes–Kelley 2018 also explicitly notes the existential logarithmic-seed bound.
   - All nonuniform models (circuits and branching programs) and computability notions that permit superpolynomial search (including Computable and Primrec) are likewise too weak a restriction at seed length (s=O(log n)): any seed map at that scale has polynomial-size circuits, and a polynomial-space search can find the lexicographically first family that fools all programs.
   - The standard literature meaning of “explicit” is “constructible/computable in `poly(n)` time.” A single-tape Turing machine is the textbook model and is polynomially equivalent to other reasonable models, such as multitape machines and random-access machines charged per bit. Requiring bit-by-bit output is equivalent to requiring the entire output, since (n) bits times polynomial time is still polynomial.
   - **Uniformity completion.** The initial definition constrained computation of each output bit but did not constrain the seed-length schedule (s) itself.  The current `Explicit` definition is `UniformSeedLength s ∧ (output-bit computability)`: a fixed machine must compute (s:\mathbb N→\mathbb N) from unary (n) in polynomial time (Hatami–Hoza 2024, §1.4, Definition 1.4 and §1.4.1). This constrains only the computability of the length schedule; seed values remain random inputs averaged uniformly by `ROBP.Fools`.
   - mathlib 4.33 has no polynomial-time predicate (the full `Mathlib/Computability/` directory was checked), so the task defines a minimal machine model: alphabet `Option Bool` (blank is `none`), halting when the transition function returns `none`, directions including stay-put `S`, fuel-based step semantics `TM.run`, and output equal to the cell under the head at halt. This model is used only to state the problem; its operational behavior was checked by kernel-verified small-example probes (small-examples.md E7–E10).

4. **(o(log^2 n)) is expressed as ((s n)/(log n)^2 → 0) over (ℝ), using the natural logarithm.** This is the asymptotic definition of little-(o). Changing the logarithm base changes only a constant factor, so the condition is equivalent for every base. We do not use the alternative “there exists (d<2) such that (s≤(log n)^d)” formulation. The literature uses (o(log^2 n)), which is stronger: the power bound implies the ratio tends to zero, but the converse need not hold. We retain the literature’s original, stronger statement.

5. **The error bound is required for every (n≥1) (the literature often says “for sufficiently large (n)”).** The formulations are equivalent. If a generator family fools for (n≥ N_0), replace its finitely many smaller cases with the identity generator (seed length (n), error 0, and explicit—the machine branches on the hard-coded threshold, so remains polynomial-time). Finitely many exceptions do not change (s/log^2n→0). Requiring the bound for every (n≥1) avoids adding an existential quantifier to the proposition.

6. **Probabilities are exact rationals.** Probabilities over finite uniform sample spaces are rational. Using (ℚ) makes small-instance statements (checkpoints c2 and c3) decidable by the kernel (the problem statement’s lexical scan forbids `native_decide`; use kernel `decide`), and matches the literature’s counting-ratio convention exactly, without measure theory over (ℝ).

7. **The case (n=0) is excluded.** Neither (1/n) nor (log n) is defined at (n=0), so the statement starts at (n≥1). This finite starting point does not affect the asymptotic claim.

## 3. Distinction from nearby problems

- **BPL = L (polynomial width):** This is item 1 of the survey (logspace derandomization). Here (w=4) is the smallest open constant-width case, not an equivalent problem. Solving width 4 would not imply BPL = L; conversely, BPL = L would immediately imply this task’s statement.
- **Permutation, regular, and unordered ROBPs:** Braverman–Rao–Raz–Yehudayoff 2010 and Reingold–Steinke–Vadhan 2013 solve the regular/permutation subclasses, with seed length Õ(`log n`). Forbes–Kelley 2018 treats arbitrary read orders, with seed length Õ(`log² n`) for constant width. The main statement here concerns **standard ordered general ROBPs**. The finite example exhaustively checks the smallest finite permutation-subclass instance (width 2, length 3, 512 programs); it has no implication for the main statement.
- **Widths 2 and 3, which are already resolved in part:** Width 2 has an optimal small-bias-space solution (BDVY 2013, seed (O(log(n/ε)))). For width 3, Meka–Reingold–Tal 2019 gives seed length Õ(`log n · log(1/ε)`), which is Õ(`log² n`) when (ε=1/n); this does not resolve the problem at that error. Neither the background nor the checkpoints in this task claim that width 3 is solved for error (1/n).

## 4. Known frontier (; abstract-level)

- All widths: Nisan 1992 gives an explicit PRG with seed length (O(log^2 n)) (*Combinatorica* 12(4):449–461).
- Width 2: optimal seed length (O(log(n/ε))) (BDVY 2013 plus Naor–Naor small-bias spaces).
- Width 3: Õ(`log n · log(1/ε)`) (Meka–Reingold–Tal 2019), which is Õ(`log² n`) for (ε=1/n).
- Width at least 4: no explicit PRG/WPRG/HSG with (o(log^2 n)) seed length (Doron–Hoza 2025, APPROX/RANDOM, LIPIcs 353:28). The best bound for the permutation subclass is also on the order of `log n · log(1/ε)` (Lee–Viola, CCC 2025, LIPIcs 339:9).
