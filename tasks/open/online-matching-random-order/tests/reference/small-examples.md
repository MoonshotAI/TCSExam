# Executable small examples — kernel-measured values for random-order online bipartite matching

This note records kernel-measured values of the definition layer on small instances, used as the third fidelity check (executable small examples) and as the source values for the test points.
- Method: compile `tests/reference/logs/Probe*.lean` in the scoring base image with `lake env lean` (toolchain leanprover/lean4:v4.33.0-rc1, mathlib pinned at 5b3f719); unless noted, assertions are evaluated successfully by the kernel's `decide`
- **Important environment fact**: in the Lean build used by this scoring image (kernel-reduction branch), `instDecidableEqRat` does not reduce in the kernel, so `decide` always fails on ℚ (even the literal equation `(2:ℚ)+2=4`; see Probe3d). `decide` works normally for ℕ, Finset equality, and permutation enumeration. Therefore the c1 proof uses symbolic reasoning (per-graph analysis + API lemmas), leaving only ℕ/Finset subgoals for `decide`.

## E1. The two graphs at n = 1

- `matchingNumber (∅ : BipGraph 1) = 0` (`decide`)
- `matchingNumber ({(0,0)} : BipGraph 1) = 1` (`decide`)
- Greedy matching (match whenever a neighbor exists) achieves ν on each graph and the only arrival order: `E = ν`. This is test point c1 (`omro_n1_exact`). The proof is in `tests/reference/Basic.lean` and analyzes each graph by evaluating its `step` and simplifying the sum.

## E2. The two path graphs at n = 2 (witness graphs for c3)

Notation: edges are written as (offline vertex, online vertex). `pathG1 = {(0,0),(1,0),(0,1)}` (online vertex 0 sees both offline vertices; online vertex 1 sees only offline vertex 0); `pathG2 = {(0,0),(1,0),(1,1)}` (online vertex 1 sees only offline vertex 1).

- `matchingNumber pathG1 = 2` (`decide`)
- `matchingNumber pathG2 = 2` (`decide`)
- `nbrs pathG1 ⟨0,_⟩ = {0,1}`, `nbrs pathG1 ⟨1,_⟩ = {0}`, `nbrs pathG2 ⟨1,_⟩ = {1}` (`decide`)
- `nbrs pathG1 ⟨0,_⟩ = nbrs pathG2 ⟨0,_⟩ = {0,1}` (`decide`): the two graphs give identical observations when online vertex 0 arrives first. This is the core of the indistinguishability argument for c3.

## E3. Enumerating permutations of Fin 2

- `(univ : Finset (Equiv.Perm (Fin 2))) = {1, Equiv.swap 0 1}` (`decide`)
- `Fintype.card (Equiv.Perm (Fin 2)) = 2` (`decide`, via `univ.card`)
- The function-based enumeration also reduces: `(univ.filter fun f : Fin 2 → Fin 2 => Function.Bijective f).card = 2` (`decide`; checked as an alternative design, not adopted).

## E4. Greedy's value on each permutation for pathG1 (measured by the kernel)

- `execCard greedyAlg pathG1 (1 : Perm (Fin 2)) = 1` (`decide`): for arrival order [online 0, online 1], greedy matches online 0 to the lowest-index offline vertex, 0; the only neighbor of online 1 is already taken, so there is 1 edge.
- `execCard greedyAlg pathG1 (Equiv.swap 0 1) = 2` (`decide`): for arrival order [online 1, online 0], each vertex gets a match, so there are 2 edges.
- Therefore greedy's expected size on pathG1 is (1+2)/2 = 3/2 = (3/4)·ν. The c3 upper bound 3/4 is attained by greedy, consistent with the exact minimax value 3/4 at n=2. The sum identity `∑ π, execCard greedyAlg pathG1 π = 3` is proved by `decide` over ℕ (Probe3b).

## E5. Negative-case checks (to catch a wrong direction in the definition layer)

- The already-proved fixed-layer lemma `expectedCard_le_matchingNumber` guarantees E ≤ ν for every A,G. The witness construction in c3 gives E ≤ (3/4)ν, so the two bounds are compatible (3/4 < 1).
- The conjecture at n = 2 requires `(∃ A, ∀ G, 4E ≥ 3ν)`, while c3 states `(∀ A, ∃ G, 4E ≤ 3ν)`. They meet at 3/4: E4 shows that greedy satisfies 4E ≥ 3ν on each small example, while every A has a graph on which it fails. Both claims hold at once exactly when the minimax value at n = 2 is 3/4.
