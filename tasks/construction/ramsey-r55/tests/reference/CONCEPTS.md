# Concept ledger — ramsey-r55-lean

This document provides a crosswalk from each Lean identifier in the definition layer to the literature definition, with a record of formalization choices.

## Literature concepts ↔ Lean identifiers

each row maps a literature definition to its Lean representation and explains any modeling choice.

| Literature definition | Lean identifier (`namespace R55`) | Crosswalk notes |
|---|---|---|
| Vertex set of the complete graph K_N | `Fin N` (parameter of `Coloring`) | N vertices indexed 0..N-1, the standard representation. |
| Red/blue 2-coloring of edges (edges are unordered pairs of vertices) | `Coloring N`: `color : Fin N → Fin N → Fin 2` plus field `symm : ∀ i j, color i j = color j i` | 0/1 in `Fin 2` mean red/blue; the `symm` field encodes unordered pairs in the type. **Choice**: no constraint on diagonal `color i i` (K_N has no loops, so the diagonal has no mathematical content; `MonoFree` only considers pairs with `i ≠ j`, so this does not affect truth of any statement). |
| Monochromatic K5 (5 vertices, all 10 edges the same color) | `∃ col : Fin 2, ∀ i ∈ s, ∀ j ∈ s, i ≠ j → c.color i j = col`, where `s : Finset (Fin N)` and `s.card = 5` | Expressing a “5-tuple” as a 5-element subset (Finset with card = 5) is equivalent to the literature's “any 5 vertices”; `i ≠ j` excludes loops, and the 10 edges are all unordered pairs (symmetry makes the ordered quantification redundant). |
| A coloring with no monochromatic K5 (certificate that R(5,5) > N) | `MonoFree c` := the above statement fails for **every** 5-element subset | That is, “no 5-tuple is monochromatic.” `@[reducible]` only lets `decide` synthesize `Decidable` instances directly for small N; it does not change the semantics. |
| Lower-bound claim R(5,5) ≥ N+1 | `submission_lower : ∃ c : Coloring N, MonoFree c` | A valid coloring exists iff R(5,5) > N. |
| Upper-bound claim R(5,5) ≤ N | `submission_upper : ∀ c : Coloring N, ¬ MonoFree c` | Every coloring contains a monochromatic K5 iff R(5,5) ≤ N. When N < R(5,5), this statement is false and cannot be proved validly, so there is no way to gain credit by exploiting that case. |

## Record anchors (same source as the Solver version ramsey-r55-lb; see `../ramsey-r55-lb/PROVENANCE.md`)

- Lower-bound record: valid coloring of K₄₂ (Exoo 1989, J. Graph Theory 13(1):97–98) → lower-bound record N=42.
- Upper-bound record: R(5,5) ≤ 46 (Angeltveit–McKay, J. Graph Theory 2026, arXiv:2409.15709) → upper-bound record N=46.
- Trivial anchors: construction direction N=30 (found by local search in minutes; same baseline as the Solver version); upper-bound direction N=70 = C(8,4), the Erdős–Szekeres recursion bound (a textbook result requiring no computation).
- Dynamic survey: Radziszowski, *Small Ramsey Numbers*, EJC DS1 rev #18; the prevailing conjecture is R(5,5) = 43.

## Scoring conventions (two modes; default is `alpha_milestone`)

- `alpha_milestone` (default in `judge.json`): any non-vacuous proof passing all gates receives the α-milestone score 1.0; `record_matched` (42 / 46) = 1.0; `record_broken` (lower bound ≥43 / upper bound ≤45) continues above 1 using the same cubic curve as the Solver version, without a cap.
- `solver_cubic`: exactly the same curve as the Solver version (N≤30 → 0; `((N−30)/12)³`; upper-bound mirror `((70−N)/24)³`). In this mode, sanity cases N≤30 score 0.
- **Open check**: the request said that “sanity proofs (N≤30) should receive full credit,” which conflicts with the Solver version's curve (N=30 → 0). The default implements “full credit for sanity”; the Solver curve remains available as a one-switch option (`judge.json` `score_mode`). If the project later decides to use the Solver curve, one configuration line can be changed.
