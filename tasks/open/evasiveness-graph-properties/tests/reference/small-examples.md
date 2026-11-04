# Executable Small Examples — Enumeration and Probe Assertions for Evasiveness-Conjecture Checkpoints

Pure-Python enumeration and Lean-kernel `decide` checks independently confirm numerical facts behind the task's three checkpoints; actual outputs are recorded here.

- Script: `tests/reference/enumerate_small.py` (Python standard library only; run locally). Lean probe: `tests/reference/Probe.lean` (run with `lake env lean` in an independent validation environment; exit code 0).

## 1. Python enumeration: decision-tree complexity of graph properties on small numbers of vertices

A property is a 0/1 assignment to graph isomorphism classes; D is the minimum decision-tree depth for deciding it (memoized recursive exhaustive search over all variable orders); evasive means D equals the number of candidate edges, C(v,2).

### A. v = 3 (four isomorphism classes, indexed by 0…3 edges)

All 14 nontrivial properties have D = 3 = C(3,2) and are evasive. Exactly three are monotone (increasing): {at least 1 edge} (having an edge, the property in c1), {at least 2 edges}, and {3 edges} (complete graph); all are evasive. This matches the v=3 case of c1's general proof for all v.

### B. v = 4 (11 isomorphism classes)

There are 2,046 nontrivial properties and all 2,046 are evasive; among them, 22 nontrivial properties are monotone and all 22 are evasive. **There are 0 nonmonotone, nonevasive properties.**

### C. v = 5 (m = 10, targeted candidates)

All ten natural candidates have D = 10 and are evasive: exactly one edge; contains an isolated edge; star K1,4; is C5; has an isolated vertex; edge count ∈ [3,6]; degree sequence (2,2,2,3,3); triangle plus an isolated vertex; has a dominating vertex (monotone); scorpion (nonmonotone; an asymptotic O(v) example of Best–van Emde Boas–Lenstra 1974—at v = 5, 3v = 15 > 10 = C(5,2), and its nonevasiveness appears only for v ≥ 8, outside the kernel-decidable range).

### Design conclusion

No graph property on these small vertex sets is “nonmonotone but nonevasive” (full enumeration in B and targeted candidates in C both find none). This suggests that a “nonmonotone-property contrast” would not make a kernel-decidable checkpoint. c2 therefore uses a contrast with the equally documented necessary premise “nontriviality” (Miller 2011 / Wikipedia: trivial properties are decided with no queries at all).

## 2. Lean probe assertions (all kernel `decide` checks in Probe.lean passed)

| ID | Assertion | Result |
|---|---|---|
| E1 | `hasEdgeProp 2 ⊥ = false` | Pass |
| E2 | `hasEdgeProp 2 ⊤ = true` | Pass |
| E3 | `hasEdgeProp 3 ⊥ = false`, `⊤ = true`, and `⊤` has 3 edges | Pass |
| E4 | `singleEdge 0 1` on v=3 has `edgeFinset.card = 1` | Pass |
| E5 | c2 witness tree (leaf `true`) evaluates to `true` on ⊥/⊤ for v=3 and has depth 0 | Pass |
| E6 | At v=2, a single leaf and `hasEdgeProp` have opposite values on ⊥ (or ⊤): the leaf cannot decide whether an edge exists (shadow case of c1 at v=2) | Pass |
| E7 | The example tree's all-negative path queries the set {s(0,1), s(0,2)} and returns `false` | Pass |

## Correspondence with the Lean statements

- c1 (`hasEdge_evasive`): general inductive proof, independent of enumeration. Part A (the three monotone properties on v=3 are all evasive) and E6 (the leaf fails at v=2) provide checks of special cases.
- c2 (`trivial_property_not_evasive`): E5 evaluates the witness tree and checks its depth; this is the existential witness in the statement.
- c3 (`hasEdge_is_property`): E1–E3 check the two witness values for nontriviality (⊥ is false, ⊤ is true).
