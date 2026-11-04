# Concept ledger — binary-code-a24-10-lean-open

This document provides a crosswalk from each Lean identifier in the definition layer to the literature definition, with a record of formalization choices.

## Literature concepts ↔ Lean identifiers

each row maps a literature definition to its Lean representation and explains the formalization.

| Literature definition | Lean identifier | Crosswalk notes |
|---|---|---|
| Binary word w ∈ {0,1}²⁴ | `Fin 24 → Fin 2` | 24 coordinates, each 0 or 1; standard representation (same as covering-code-k12-lean-open, with code length changed from 12 to 24). |
| Hamming distance d(x,y) (number of differing coordinates) | `hammingDist x y` | Built into mathlib (`Mathlib/InformationTheory/Hamming.lean`: `#{i \| x i ≠ y i}`; computable). The fixed layer reuses it directly rather than reimplementing it. |
| Minimum distance ≥ 10 (every pair of distinct codewords is at distance ≥ 10) | `MinDist10 S` := `∀ x ∈ S, ∀ y ∈ S, x ≠ y → 10 ≤ hammingDist x y` | Exactly the literature definition of minimum distance ≥ 10. It also agrees item by item with the Solver version checker (`tests/checker.py`: compare all pairs using `bin(a^b).count("1") >= 10`). `@[reducible]` only lets `native_decide` synthesize `Decidable` instances for concrete codes; it does not change the semantics. |
| Certificate that A(24,10) ≥ m | `submission_construction : ∃ S : Finset (Fin 24 → Fin 2), MinDist10 S ∧ m ≤ S.card` | A valid code of size at least m exists iff A(24,10) ≥ m (for a maximization problem, a construction gives a lower bound). |
| Certificate that A(24,10) ≤ k | `submission_upper : ∀ S : Finset (Fin 24 → Fin 2), MinDist10 S → S.card ≤ k` | Every valid code has at most k codewords iff A(24,10) ≤ k (the universal statement gives the upper bound; since a valid code exists, the two directions together pin down the value). |

## Predicate alignment with the Solver sibling version (binary-code-a24-10; Solver repository path `construction-conjecture-solver/tasks/binary-code-a24-10/`)

each row compares the Solver checker semantics with this task's Lean statement.

| Solver checker semantics | Lean semantics in this task | Alignment |
|---|---|---|
| A codeword is a 24-bit 0/1 string (`len(w) == 24`, characters in {0,1}) | A codeword is `Fin 24 → Fin 2` | Two representations of the same object: the i-th bit of the 24-bit string corresponds to the function value at coordinate i. |
| Duplicate codewords are rejected | `Finset` excludes duplicates automatically | Same set semantics; the Solver version checks lists for duplicates, while this task excludes them by type. |
| Distance: every pair of codewords i<j has popcount(a XOR b) ≥ 10 (compare all pairs) | `MinDist10 S`: `∀ x ∈ S, ∀ y ∈ S, x ≠ y → 10 ≤ hammingDist x y` | Same predicate: XOR popcount is the number of differing coordinates. The Solver version uses unordered pairs; this task uses ordered pairs with x ≠ y, which is equivalent. The Solver version accepts the empty and one-word codes (`min_distance=null`); the predicate here is vacuously true for codes with at most one word, so the behavior agrees. |
| Format cap of 400 words | None | This is a Solver-format guard to limit scoring time (above the proven upper bound 268, so it blocks no valid submission), not a mathematical predicate. The claim parameter here is capped at 2²⁴ = 16777216, the size of the full cube. |
| Score uses k = \|C\| in `((k − 2) / 134)³` | Construction direction uses the same formula with parsed m | Anchors 2 / 136 / 268 match in both versions (see below); the 136-word code scores 1.0 in both (Solver side `milestone=record_tied`; this task `record_matched`). |

## Record anchors (same source as the Solver version binary-code-a24-10; see its `PROVENANCE.md`)

- Lower-bound record (construction): 136 (Laaksonen–Östergård 2016, arXiv:1604.06022, with an explicit code in the preprint appendix) → `record_m = 136`; `record_broken` when m ≥ 137.
- Upper bound: 268 (Gijswijt–Mittelmann–Schrijver 2012, IEEE Trans. Inf. Theory 58(5):2697–2705, a strengthened Delsarte linear-programming bound) → in the construction direction, m > 268 is marked `above_proven_upper_bound` and requires manual review; in the upper-bound direction, `record_k = 268` and `record_broken` when k ≤ 267.
- Trivial baseline in the construction direction: 2 (the repetition code `{0²⁴, 1²⁴}`, whose two words are at distance 24 ≥ 10) = score 0.
- Trivial baseline in the upper-bound direction: **1295 (sphere-packing / Hamming bound) = score 0**. Derivation: minimum distance 10 implies that Hamming balls of radius t = ⌊(10−1)/2⌋ = 4 around codewords are pairwise disjoint. Each ball contains Σ_{i=0}^{4} C(24,i) = 1 + 24 + 276 + 2024 + 10626 = 12951 words. All balls lie in the 2²⁴ = 16777216-word cube, so |S| ≤ ⌊16777216 / 12951⌋ = ⌊1295.43…⌋ = 1295. This is the textbook trivial upper bound (the Singleton bound 2^15 = 32768 is weaker; the Plotkin bound does not apply when d < n/2).
- Upper-bound direction anomaly: k < 136 contradicts the Laaksonen–Östergård construction → marked `below_proven_lower_bound` (requires manual review).
- Tracking source: Brouwer's online table of A(n,d) (n=24, d=10 column: 136–268; consistent in reconnaissance and a source-text check; see `conjecture-bounds.md`). The table's latest recorded improvement is from 2019.

## Scoring conventions

- Construction direction uses exactly the Solver version's curve, formula, and anchors: m ≤ 2 → 0; m > 2 → `((m − 2) / 134)³`; m = 136 → 1.0 (`record_matched`); m ≥ 137 → `record_broken` with no cap; m > 268 → `above_proven_upper_bound` (manual review required, while the score still follows the formula—scoring and contradiction status are separate questions).
- The upper-bound direction uses a curve defined for this task (same shape as the two-direction engine in the pilot covering-code-k12-lean-open: trivial anchor at 0, literature anchor at 1.0, cubic interpolation with no cap after breaking the record): k ≥ 1295 → 0; k < 1295 → `((1295 − k) / 1027)³`; k = 268 → 1.0 (`record_matched`); k ≤ 267 → `record_broken` with no cap; k < 136 → `below_proven_lower_bound` (manual review required). The 1295 anchor is derived above.
- Total score = maximum over the two directions with a proved claim (same two-direction engine as covering-code-k12 / ramsey-r55).
- `native_decide` is allowed (`allowed_axioms` includes `Lean.ofReduceBool` and `Lean.trustCompiler`; `._native.native_decide.ax_*` is automatically exempted, following the k10/k12 convention). Checking all pairwise distances for a 136-word code is finite computation, and `native_decide` is the practical route; kernel `decide` is infeasible at this scale.

## Formalization choices

- Use `Fin 24 → Fin 2` for words rather than `BitVec 24`: this matches the k10/k12/capset versions, has the required `Fintype`/`DecidableEq` instances, and can be evaluated directly by `native_decide`.
- Represent the code S as a `Finset`: its cardinality is direct to read, and duplicates are excluded automatically.
- The fixed layer contains no construction or sequence of helper lemmas. Both claim statements are shipped with the task package, following the k12/ramsey/vdw convention. The agent may change only the numeric parameter (construction direction defaults to 2, the trivial baseline; upper-bound direction defaults to 1295, the trivial sphere-packing bound). The claim body is fixed between the `-- CLAIM ... BEGIN/END` markers.
- Claim names `submission_construction` / `submission_upper`: the construction direction of a maximization problem gives a lower bound on A(24,10), but names follow the model's action (construct a code / prove an upper bound), matching the task's convention “∃ = construction direction, ∀ = upper-bound direction.” The sibling task binary-code-a22-10-lean-open uses `lower`/`upper`; the two repositories are maintained independently, and the semantics agree.
- The upper-bound task statement notes that there is currently no scalable proof route. GMS's value 268 comes from a semidefinite-programming computation and has no scalable proof method. Even k = 1295 requires writing a genuine counting proof in Lean (the disjoint-ball volume argument).
- The scorer uses the two gates from k12: a complete banned-token list (`notation/macro/syntax/elab/opaque/unsafe/extern/implemented_by/initialize/skipKernelTC` plus `axiom/sorryAx`) and per-claim consistency checks (restate the proposition using `_root_.MinDist10` with the parsed number and derive it from the agent theorem). `#print axioms` allowlist = propext / Classical.choice / Quot.sound / Lean.ofReduceBool / Lean.trustCompiler.
- **`native_decide` instance-synthesis trap (confirmed in the sandbox)**: applying `by native_decide` directly to the claim shape `∀ x ∈ S, ∀ y ∈ S, …` makes instance synthesis enumerate the entire type `Fin 24 → Fin 2` (2²⁴ = 16777216 functions). Both compilation and scoring for a 136-word code then time out (sandbox evidence from 2026-09-15: `lake build` timed out after 2400s, scoring Lean timed out after 1500s, process RSS about 15 GB). A workable route is to express the distance check as Boolean computation over a **list** of concrete codewords (`List.all` on concrete words; 136×136 concrete distance calculations finish in seconds), then connect it back to the finset statement. The oracle's `recordPairsOk` / `recordCode_minDist10` use this pattern, which is also described in the task statement's Notes. This finding may help sibling tasks with the same predicate shape (such as a22-10-lean-open).
- The oracle uses the literature's 136-word record code rather than the trivial baseline because the task request said to prefer the 136-word code if available. The preprint appendix data was obtained and its orbit expansion was independently checked; this also verifies the `record_matched` branch end to end. The Solver version chose a 2-word baseline because it avoids transcribing a construction for a sanity check. The two oracle tasks have different purposes: the Solver oracle checks the checker path, while this task checks whether the record construction can be formalized with `native_decide`.
