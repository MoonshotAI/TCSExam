# Concept ledger — binary-code-a22-10-lean-open

This document provides a crosswalk from each Lean identifier in the definition layer to the literature definition, with a record of formalization choices.

## Literature concepts ↔ Lean identifiers

each row maps a literature definition to its Lean representation and explains the formalization.

| Literature definition | Lean identifier | Crosswalk notes |
|---|---|---|
| Binary word w ∈ {0,1}²² | `Fin 22 → Fin 2` | 22 coordinates, each 0 or 1; same representation as the pilot tasks (covering-code-k10-lean-open / k11), with only the code length changed. |
| Hamming distance d(x,y) (number of differing coordinates) | `hammingDist x y` | Built into mathlib (`Mathlib/InformationTheory/Hamming.lean`: `#{i \| x i ≠ y i}`; computable) and reused in the fixed layer. The Solver sibling checker implements it as `popcount(x XOR y)`; both count differing bits coordinate by coordinate and have the same semantics. |
| Minimum distance 10 (every pair of distinct codewords is at distance ≥ 10) | `isMinDist10Code S : Bool` := nonempty && for every pair of positions `i ≠ j`, require `hammingDist x y ≥ 10`; `MinDist10Code S := isMinDist10Code S = true` | Aligned item by item with the Solver sibling checker for binary-code-a22-10: it checks every pair of codewords and rejects if distance < 10. This predicate checks every pair by position (`List.zipIdx`) and excludes the diagonal with `i == j ||`, which is the contrapositive form. The checker explicitly rejects duplicate codewords; this predicate needs no separate clause because repeated words have distance 0 < 10 and are rejected by clause 2. The checker requires a nonempty codeword list, matching clause 1. All clauses are packaged in one `Bool` function, so `native_decide` evaluates a concrete code directly without synthesizing a `Decidable` instance for each clause. `@[reducible]` does not change the semantics. |
| Certificate that A(22,10) ≥ k | `submission_lower : ∃ S : List (Fin 22 → Fin 2), MinDist10Code S ∧ k ≤ S.length` | A valid code of size at least k exists iff A(22,10) ≥ k (for a maximization problem, a construction gives a lower bound). |
| Certificate that A(22,10) ≤ m | `submission_upper : ∀ S : List (Fin 22 → Fin 2), MinDist10Code S → S.length ≤ m` | Every valid code has at most m words iff A(22,10) ≤ m (the ∀ direction gives an upper bound). A valid list has pairwise distinct entries because the pairwise clause rejects duplicates, so its length is the cardinality of the underlying word set; quantifying over lists is equivalent to quantifying over sets. |

## Record anchors (same sources as the Solver version binary-code-a22-10; see `../binary-code-a22-10/` and `conjecture-bounds.md`)

- Lower-bound record: 64 (Östergård 2005, *Two new four-error-correcting binary codes*, Des. Codes Cryptogr. 37:283–288) → `record_m = 64`; `record_broken` when k ≥ 65.
- Upper bound: 84 (Gijswijt–Mittelmann–Schrijver 2012, *Semidefinite code bounds based on quadruple distances*, IEEE Trans. Inf. Theory 58(5):2697–2705) → `record_k = 84`; `record_broken` when m ≤ 83.
- Trivial baseline for construction: 2 (repetition code `{0²², 1²²}`) = score 0; trivial baseline for upper bound: 460 (Hamming sphere-packing bound, derived below) = score 0.
- Tracking source: Brouwer's online *Table of A(n,d)*.

## Derivation of the trivial upper-bound baseline (sphere-packing bound, content-reviewed)

Minimum distance 10 implies that Hamming balls of radius e = ⌊(10−1)/2⌋ = 4 are pairwise disjoint. The volume of a radius-4 ball is

`V(22,4) = Σ_{i=0}^{4} C(22,i) = 1 + 22 + 231 + 1540 + 7315 = 9109`,

so `A(22,10) ≤ ⌊2²² / 9109⌋ = ⌊4194304 / 9109⌋ = ⌊460.457…⌋ = **460**`.
(9109 × 460 = 4190140 ≤ 4194304 < 9109 × 461 = 4199249.)
This is the textbook sphere-packing / Hamming bound and needs no machine assistance. By comparison, the Singleton bound gives only 2¹³ = 8192, which is weaker, so 460 is used as the baseline.

## Scoring conventions

- Construction direction uses exactly the Solver version's curve: k ≤ 2 → 0; k > 2 → `((k − 2) / 62)³`; k = 64 → 1.0 (`record_matched`); k ≥ 65 → `record_broken` with no cap; k > 84 is marked `above_proven_upper_bound` (manual review required).
- The upper-bound direction uses the same curve shape, newly defined for this task because there is no corresponding Solver version: m ≥ 460 → 0; m < 460 → `((460 − m) / 376)³`; m = 84 → 1.0 (`record_matched`); m ≤ 83 → `record_broken` with no cap; m < 64 is marked `below_proven_lower_bound` (contradicts the published lower bound and requires manual review).
- The two directions are scored independently; reward is the larger of the two. A direction left with `sorry` receives neither score nor penalty.
- `native_decide` is allowed (`allowed_axioms` includes `Lean.ofReduceBool` and `Lean.trustCompiler`; `._native.native_decide.ax_*` is automatically exempted, following the pilot convention). Pairwise-distance checks over tens or hundreds of codewords are finite computations, so `native_decide` is the practical route; kernel `decide` is infeasible at this scale.
- The upper-bound task statement says “there is currently no scalable proof route”: the ∀ direction quantifies over all subsets and has no finite certificate to check. The published route is the semidefinite-programming computation using quadruple distances by Gijswijt–Mittelmann–Schrijver, with no formal certificate scheme.

## Formalization choices

- Use `Fin 22 → Fin 2` for words rather than `BitVec 22`: this matches the pilot, has the needed `Fintype` instances and coordinatewise equality, and makes `hammingDist` directly computable.
- Represent the word list S as a `List` and compare positions (`zipIdx`, `i == j ||` to exclude the diagonal), rather than using `Finset` and element equality. Before 2026-09-15, the predicate was `MinDist10 (S : Finset (Fin 22 → Fin 2)) := ∀ x ∈ S, ∀ y ∈ S, x ≠ y → hammingDist x y ≥ 10`. The `x ≠ y` test requires a `DecidableEq` instance for functions `Fin 22 → Fin 2`; `native_decide` compilation for the oracle timed out twice in the sandbox, at 1200s and 1500s (exit 124). The covering-code-k11 control in the same environment scored normally because its predicate did not compare codewords for equality. Switching to the `List` + position-comparison + packaged-`Bool` pattern used by kissing-d9 removed all function-type equality tests. The semantics agree: a valid list has no duplicates (the pairwise clause rejects repeated words because their distance is 0 < 10), `S.length` is the cardinality of its underlying word set, and the nonempty clause matches the Solver checker.
- The first three `set_option` lines in the fixed layer (`maxRecDepth 100000` / `maxHeartbeats 0` / `synthInstance.maxSize 512`) follow ramsey-r3-10-lean-open and kissing-d9-lean-open: instance-synthesis trees grow with nested clauses, and the default `synthInstance.maxSize` (128) is insufficient.
- The fixed layer has no construction or sequence of helper lemmas. The agent area begins after END OF FIXED PART. The theorem names are fixed (`submission_lower` = construction/lower-bound direction; `submission_upper` = upper-bound direction), named by the direction of the bound relative to A(22,10). This matches the k11 semantics: for a minimization problem, `submission_upper` is an upper bound and uses an ∃ statement. Only the numeric values in the statements may change; claim bodies are between CLAIM BEGIN/END markers. The two-direction format follows covering-code-k11-lean-open; the fixed-layer organization follows the pilot.
- Oracle construction representation: store codewords as a table of 22-bit integers; `wordOfNat n i` converts bit i of n to `Fin 22 → Fin 2`, and `List.map wordOfNat` forms the list. The integer table is copied entry by entry from the Solver sibling's `example_hadamard48.json` using `int(0/1 string, 2)`. This is a bijection on the cube that preserves coordinatewise differences, so Hamming distance agrees with checker `popcount(x XOR y)`. This avoids 48 function literals and lets `native_decide` compute the minimum distance and list length in one pass.
