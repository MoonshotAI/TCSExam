# Concept ledger — ramsey-r3-10-lean

This document provides a crosswalk from each Lean identifier in the definition layer to the literature definition, an item-by-item alignment with the Solver sibling predicate, and a record of formalization choices.

## Literature concepts ↔ Lean identifiers

each row maps a literature definition to its Lean representation and explains any modeling choice.

| Literature definition | Lean identifier (`namespace R310`) | Crosswalk notes |
|---|---|---|
| Vertex set of the complete graph K_N | `Fin N` (parameter of `Coloring`) | N vertices indexed 0..N-1, the standard representation. |
| Red/blue 2-coloring of edges (edges are unordered pairs of vertices) | `Coloring N`: `color : Fin N → Fin N → Fin 2` plus field `symm : ∀ i j, color i j = color j i` | 0/1 in `Fin 2` mean red/blue; the `symm` field encodes unordered pairs in the type. **Choice**: no constraint on diagonal `color i i` (K_N has no loops, so the diagonal has no mathematical content; `MonoFree` only considers pairs with `i ≠ j`, so this does not affect truth of any statement). |
| Red K3 (3 vertices, all 3 edges red) | `∀ i ∈ s, ∀ j ∈ s, i ≠ j → c.color i j = 0`, where `s : Finset (Fin N)` and `s.card = 3` | Expressing a “triple” as a 3-element subset (Finset with card = 3) is equivalent to the literature's “any 3 vertices”; `i ≠ j` excludes loops, and the 3 edges are all unordered pairs (symmetry makes the ordered quantification redundant). |
| Blue K10 (10 vertices, all 45 edges blue) | Same form, with `s.card = 10` and `c.color i j = 1` | The 45 edges are all unordered pairs, C(10,2). |
| A coloring with no red K3 and no blue K10 (certificate that R(3,10) > N) | `MonoFree c` := `∀ s : Finset (Fin N), (s.card = 3 → not all red) ∧ (s.card = 10 → not all blue)` | That is, “every triple is not all red and every 10-tuple is not all blue” (one ∀ carrying two clauses is logically equivalent to the conjunction of two separate ∀ statements). `@[reducible]` only lets `decide` / `native_decide` synthesize `Decidable` instances directly for small N; it does not change the semantics. |
| Lower-bound claim R(3,10) ≥ N+1 | `submission_lower : ∃ c : Coloring N, MonoFree c` | A valid coloring exists iff R(3,10) > N. |
| Upper-bound claim R(3,10) ≤ N | `submission_upper : ∀ c : Coloring N, ¬ MonoFree c` | Every coloring contains a red K3 or a blue K10 iff R(3,10) ≤ N. When N < R(3,10), this statement is false and cannot be proved validly, so there is no way to gain credit by exploiting that case. |

## Formalization choices

- **Predicate shape**: the first version of `MonoFree` was a conjunction of two independent ∀ statements (`(∀ s, card=3 → …) ∧ (∀ s, card=10 → …)`). Sandbox testing showed that synthesizing `Decidable` instances failed (the instance tree exceeded the default `synthInstance.maxSize` of 128: each ∀ introduced a `Fintype.decidableForallFintype` subtree; one passed, while two exceeded the limit. Splitting the conjunction and applying `native_decide` separately to each part passed.) After changing it to one ∀ with two clauses, the instance tree was halved; together with the option below, it passed.
- **Third option in the fixed layer**: `set_option synthInstance.maxSize 512` (after the pilot's `maxRecDepth 100000` and `maxHeartbeats 0`). This changes synthesis capacity only and has no semantic content. The instance tree depends on the type, not N, so 512 suffices for every N. With this option, `by native_decide` works directly on `MonoFree c` (confirmed on the N=18 oracle; compilation took about 7 seconds).
- **Actual form of `#print axioms` output**: on this toolchain (4.33.0), axioms for a `native_decide` proof are shown as `[propext, Classical.choice, Quot.sound, <declaration>._native.native_decide.ax_*]`. The scorer removes the internal axiom using its substring filter; `Lean.ofReduceBool` / `Lean.trustCompiler` in the allowlist cover versions or forms where those appear directly.

## Item-by-item alignment with the Solver sibling predicate (ramsey-r3-10)

The Solver version submits a red-edge list (graph G); the checker's two tests correspond to the two conjuncts of this version's `MonoFree` predicate:

each row pairs a Solver checker condition with the corresponding `MonoFree` clause and states the equivalence.

| Solver checker (`tests/checker.py`) | Corresponding `MonoFree` clause | Equivalence |
|---|---|---|
| `find_triangle(n, red)`: the red graph has no triangle (red K3) | First clause: for every 3-element subset s, not all pairs in s are red | Equivalent by definition: the red graph has a triangle iff some 3-element subset has all 3 edges red. |
| `find_k(n, blue, 10)`: the complement (blue graph) has no 10-clique = the red graph has no independent set of 10 vertices | Second clause: for every 10-element subset s, not all pairs in s are blue | Equivalent by definition: blue means absent from the red-edge list (blue is the complement of red); an independent set of 10 vertices iff all 45 edges of that 10-element subset are blue. |
| Format constraints (n ∈ [1,64], valid endpoints, no loops, no duplicate pairs) | Not needed: `Coloring` uses `Fin N` and `symm` to encode validity in the type | Format validity for a graph representation corresponds to type validity for the coloring representation; the unconstrained diagonal does not affect the semantics. |

Cross-checks: ① Recompute the sibling's bundled construction `example_n30.json` (N=30, 102 red edges) using a literal Python transcription of this version's predicate. There is no red K3 (brute force over C(30,3)) and no blue K10 (the Tomita search used by the sibling checker confirms there is no independent set of 10 vertices); both formulations agree. ② Convert this version's oracle construction C₁₈ to a sibling JSON certificate and run the sibling checker: valid=1, reward=0 (N=18 ≤ 35). Both versions give the same score for the same construction. The record construction at N=39 (Exoo) has not been checked end-to-end in Lean: the blue-side check would scan C(39,10) ≈ 6×10⁸ 10-element subsets, and exhaustive `native_decide` over all subsets (2³⁹) is not feasible; a structural proof is needed.

## Record anchors (same sources as the Solver sibling; see `../../construction-conjecture-solver/tasks/ramsey-r3-10/PROVENANCE.md`)

- Lower-bound record: valid coloring on 39 vertices (Exoo 1989, SIAM J. Discrete Math. 2:488–490) → lower-bound record N=39.
- Upper-bound record: R(3,10) ≤ 41 (Angeltveit 2025, EJC 32(4) #P4.30) → upper-bound record N=41.
- Trivial anchors: construction direction N=35 (R(3,9) = 36, Grinstead–Roberts 1982, so a valid coloring exists on 35 vertices; same baseline as the Solver version); upper-bound direction N=55 = C(11,2), the Erdős–Szekeres recursion bound (a textbook result requiring no computation).
- Dynamic survey: Radziszowski, *Small Ramsey Numbers*, EJC DS1 rev #18; the interval 40–41 has width 1, so any new result in either direction would settle the problem.

## Scoring conventions (two modes; default is `solver_cubic`)

- `solver_cubic` (default in `judge.json`): exactly the Solver version's curves (lower bound N≤35 → 0; `((N−35)/4)³`, 39 → 1.0, ≥40 marked `record_broken` with no cap; upper-bound mirror `((55−N)/14)³`, 41 → 1.0, and ≤40 marked `record_broken` with no cap). In this mode, sanity cases N≤35 score 0 (milestone baseline, valid=1).
- `alpha_milestone`: any non-vacuous proof passing all gates receives the α-milestone score 1.0; `record_matched` (39 / 41) = 1.0; `record_broken` (lower bound ≥40 / upper bound ≤40) continues above 1 using the same cubic curve, without a cap.
- One difference from pilot r55: that pilot request specified “sanity should receive full credit,” so its default was `alpha_milestone`. This task has no such request; following the instruction “share scoring anchors with the Solver sibling version,” it defaults to `solver_cubic`, while `alpha_milestone` remains available as a one-switch option (`judge.json` `score_mode`).
- **`native_decide` is allowed** (the key difference from the pilot, decided): axiom allowlist = propext / Classical.choice / Quot.sound / Lean.ofReduceBool / Lean.trustCompiler; the lexical gate bans only `axiom` / `sorryAx` (the pilot also bans `native_decide`). Reason: kernel `decide` is already slow for small N when the two colors are asymmetric, so `native_decide` is the only plausible path for checking candidates at record scale. The authors explicitly accept its reliability cost (`trustCompiler`).
