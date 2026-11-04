# Executable Small Examples — Behavioral Checks for the Ryser-Conjecture Definition Layer

Small hand-computable hypergraphs exercise Lean definitions (numerical values of τ/ν and edge-set behavior); independent pure-Python enumeration checks numerical facts behind the three checkpoints. Actual outputs are recorded here.

- Materials: Lean probes `Probe*.lean` (compiled in a task-app copy with `lake env lean`, image `tcs-lean-base:5b3f719`, toolchain leanprover/lean4:v4.33.0-rc1); Python script `tests/reference/enumerate_small.py` (standard library only, runs in seconds), raw output `enumerate_small.out`.

## Design notes

Definitions of τ/ν (powerset filters plus `Finset.min'`/`max'`) use only computable operations and decidable instances on `Finset`, so they are **computable**: for small instances kernel `decide` evaluates them directly (`native_decide` is prohibited by lexical scanning of task statements and is never used; proof terms from kernel `decide` introduce no extra axioms, as confirmed by `#print axioms`; the probes measured all three instances as `[propext, Classical.choice, Quot.sound]`). Hand-computed expectations come from §1 of concept-ledger and the independent Python enumeration in §1 below.

## 1. Python enumeration checks (`tests/reference/enumerate_small.py`,)

Enumeration method: encode an r-partite r-uniform hypergraph as an edge set on bitmask-encoded vertices. Compute τ and ν exactly by recursive search with global memoization: for τ, choose an edge that must be covered by one of its vertices and recurse over the branches; for ν, branch on including or excluding an edge. Evaluate every hypergraph in the powerset of the edge set.

| Check | Result |
|---|---|
| `konigWitness` (r=2, edges a₀b₀ a₀b₁ a₁b₁ a₁b₂) | τ = 2, ν = 2; equality in τ = (r−1)ν ✓ |
| `paschConfig` (r=3, {(x,y,x+y) : x,y ∈ F₂}) | τ = 2, ν = 1, pairwise intersecting ✓ |
| `truncatedPG3` (r=4, {(x,y,x+y,x+2y) : x,y ∈ F₃}) | τ = 3, ν = 1, pairwise intersecting; maximum vertex degree 3 ✓ |
| r=3, part sizes (2,2,2): all 256 hypergraphs | No violations of τ ≤ 2ν; 18 attain equality; maximum τ/ν = 2 |
| r=3, part sizes (2,2,3): all 4,096 hypergraphs | No violations of τ ≤ 2ν; 78 attain equality; maximum τ/ν = 2 |
| r=4, part sizes (2,2,2,2): all 65,536 hypergraphs | No violations of τ ≤ 3ν; none attain equality (part size 2 gives τ ≤ 2, so it cannot reach 3); maximum τ/ν = 2 |

Hand-check cross-validation:

- `paschConfig` is pairwise intersecting: check the four edges (0,0,0), (0,1,1), (1,0,1), (1,1,0) pairwise (for nonzero difference vector (Δx,Δy), exactly one of Δx, Δy, Δx+Δy is zero). Each vertex lies in only two edges, so one vertex cannot cover all four; {a₀,a₁} covers them all, hence τ = 2.
- `truncatedPG3` is pairwise intersecting: for any two distinct parameter pairs with difference (Δx,Δy) ≠ 0, the four linear forms Δx, Δy, Δx+Δy, Δx+2Δy are pairwise linearly independent over F₃. The four lines through the origin contain 4 × 2 = 8 nonzero vectors, exactly |F₃²∖{0}|, so exactly one coordinate agrees and ν = 1. Every vertex lies in 3 edges, so two vertices cover at most 6 < 9 edges; thus τ ≥ 3. Any full part (3 vertices) covers all edges, so τ = 3.
- The absence of an equality case in the enumeration at r=4 and part sizes (2,2,2,2) agrees with the theory: any full part is a cover, giving τ ≤ 2 < 3 = (r−1)·1. A tight example requires at least 3 vertices in each part (as in `truncatedPG3`).

## 2. Lean probe results (kernel `decide` and API-lemma routes)

“Decision route” means the proof method used for the checkpoint. Times are whole-file `lake env lean` measurements in the container (including about 5–8 seconds to load `Task.Basic`).

| ID | Check | Hand-computed expectation | Decision route and measured result |
|---|---|---|---|
| E1 | τ and ν of `konigWitness` | τ = 2, ν = 2 | Bare `decide` passes (default `maxRecDepth` 512 suffices; single check about 0.7 seconds) |
| E2 | τ and ν of `paschConfig` | τ = 2, ν = 1 | Bare `decide` passes (about 1 second) |
| E3 | Intersections among edges of `truncatedPG3` (81 edge pairs) | Every pair of edges shares a vertex | Expand 81 cases with `fin_cases` and use `decide` per case (plan-B proof, about 9.5 seconds overall). Note: one bare `decide` on the whole statement requires `maxRecDepth` ≥ 131072 (131072 passed, 65536 was insufficient). |
| E4 | ν of `truncatedPG3` | 1 | Two routes measured: bare `decide` passes with `maxRecDepth` 1,000,000 and `maxHeartbeats` 8,000,000 (about 45 seconds); plan-B (singleton matching + contradiction from intersection) takes about 10 seconds |
| E5 | τ of `truncatedPG3` | 3 | Plan-B passes (explicit cover {(0,0),(0,1),(0,2)} for the upper bound; union bound using degree ≤ 3 gives 9 ≤ 3·|C| for the lower bound), about 10 seconds; axiom list `[propext, Classical.choice, Quot.sound]` |
| E6 | Axiom cleanliness of the three instances | Standard axioms only | `#print axioms` confirms konig/pasch (`decide`) and pg3 (plan-B) each use `[propext, Classical.choice, Quot.sound]` |

## 3. Issues found

- **Different resource needs for bare `decide`:** c1/c2 search spaces (powerset of 2⁶ vertices × 4 edges) are decidable at the default `maxRecDepth` 512. c3's τ (2¹² = 4,096 cover candidates), ν (2⁹ = 512 matching candidates), and an entire ∀∀ edge-intersection statement need `maxRecDepth` around 131,072–1,000,000 and several million heartbeats. The pinned option remains in the fixed zone (shipped unchanged to the grading variant; deleting or changing the fixed zone earns 0).
- **Grading time budget:** With a plan-B proof for c3, a single variant compiles and evaluates in about 10–15 seconds. With bare `decide`, ν alone takes about 45 seconds and the full τ statement takes longer. The grader allows 900 seconds per job and 1,800 seconds total for the verifier, so plan-B has ample headroom. The delivered checkpoint validation (`partial-c3`) uses plan-B.
- **Axiom cleanliness of kernel `decide`:** E1/E2/E4/E5 were checked in the grading chain using the `#print axioms` whitelist, confirming kernel evaluation introduces no extra axioms such as `Lean.ofReduceBool`.
