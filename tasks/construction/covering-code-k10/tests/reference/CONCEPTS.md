# Concept ledger — covering-code-k10-lean-open

This document provides a crosswalk from each Lean identifier in the definition layer to the literature definition, with a record of formalization choices.

## Literature concepts ↔ Lean identifiers

each row maps a literature definition to its Lean representation and explains the formalization.

| Literature definition | Lean identifier | Crosswalk notes |
|---|---|---|
| Binary word w ∈ {0,1}¹⁰ | `Fin 10 → Fin 2` | 10 coordinates, each 0 or 1; standard representation (same point type as capset-d7-lean-open). |
| Hamming distance d(x,y) (number of differing coordinates) | `hammingDist x y` | Built into mathlib (`Mathlib/InformationTheory/Hamming.lean`: `#{i \| x i ≠ y i}`; computable). The fixed layer reuses it directly rather than reimplementing it. |
| Radius-1 covering (every word lies in the radius-1 ball around some codeword) | `Covers S` := `∀ w, ∃ c ∈ S, hammingDist w c ≤ 1` | The union of radius-1 balls around codewords is the full cube, equivalent to covering radius ≤ 1 in the literature. `@[reducible]` only lets `native_decide` synthesize `Decidable` instances for concrete codes; it does not change the semantics. |
| Certificate for K(10,1) ≤ N | `covering_code_k10_main : ∃ S : Finset (Fin 10 → Fin 2), Covers S ∧ S.card ≤ N` | A covering code of size ≤N exists iff K(10,1) ≤ N. |

## Record anchors (same source as the Solver version of covering-code-k10; see `../covering-code-k10/PROVENANCE.md`)

- Upper-bound record: 120 (Östergård 1991, IEEE Trans. Inf. Theory 37(1):179–180; the Kéri table also cites Wille 1990/1996) → `record_k = 120`; `record_broken` when k ≤ 119.
- Lower bound: 107 (Bertolo–Östergård–Weakley 2004, J. Combin. Designs 12:157–176) → k < 107 is marked `below_proven_lower_bound` (requires manual review).
- Trivial baseline: 512 (even-weight code) = score 0.
- Tracking sources: Kéri's online table (last updated 2011-11-21); Gijswijt–Polak (arXiv:2504.01932) and DeVivo–Hladký (arXiv:2409.14621) did not improve the n=10 endpoint ().

## Scoring convention

- Exactly the same curve as the Solver version: k ≥ 512 → 0; k < 512 → `((512 − k) / 392)³`; k = 120 → 1.0 (`record_matched`); k ≤ 119 → `record_broken`, with no cap.
- Unlike the `alpha_milestone` mode of ramsey-r55-lean-open, this task is purely constructive (it covers only the existence of a small covering code; proving the lower-bound direction is a different scale of research and outside this task). Milestones are defined directly in terms of k, with no “sanity receives full credit” rule. The sanity construction (the even-weight code of size 512) is expected to be accepted but scores 0, matching the Solver baseline.
- `native_decide` is allowed (`allowed_axioms` includes `Lean.ofReduceBool`; the `._native.native_decide.ax_*` trusted axiom is automatically exempted). Checking coverage of 512 words is finite computation, so `native_decide` is the practical route; kernel `decide` is infeasible at this scale.

## Formalization choices

- Use `Fin 10 → Fin 2` for words rather than `BitVec 10`: this matches the capset version, has the required `Fintype`/`DecidableEq` instances (`Fintype.decidablePiFintype`), and can be evaluated directly by `native_decide`.
- Represent the code `S` as a `Finset`: its cardinality is direct to read, and duplicates are excluded automatically.
- The fixed layer contains no construction or sequence of helper lemmas. The agent area begins after END OF FIXED PART; the theorem name is fixed as `covering_code_k10_main`, and only the number k may change.
