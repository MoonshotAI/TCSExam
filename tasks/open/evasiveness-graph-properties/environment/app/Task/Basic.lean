/-
Statement layer for the **evasiveness conjecture** (Karp's conjecture): every
nontrivial monotone graph property P on v vertices is evasive — every
deterministic decision tree deciding P has depth at least C(v,2), i.e. in the
worst case it must query all C(v,2) candidate edges.

Sources: conjectured by R. Karp in the early 1970s, strengthening the weaker
Ω(v²) form of Aanderaa–Rosenberg (A. L. Rosenberg, *On the time required to
recognize properties of graphs: a problem*, SIGACT News 5(4), 1973, pp. 15–16).
Survey: C. A. Miller, *Evasiveness of Graph Properties and Topological
Fixed-Point Theorems*, Foundations and Trends in Theoretical Computer Science
7(4), 2011, pp. 337–415 (arXiv:1306.0110). The conjecture is open: no proof
and no counterexample is known (Miller, Introduction: "To date, this
conjecture is unproven and no counterexamples are known"). It is proved for v
a prime power (Kahn–Saks–Sturtevant, *A topological approach to evasiveness*,
Combinatorica 4(4), 1984, pp. 297–306); the best general deterministic lower
bound is (1/3 − o(1))·v² (Scheidweiler–Triesch, SIAM J. Discrete Math. 27(1),
2013, pp. 257–265).

This file is the task's definition zone plus slot zone:
- The definition zone defines boolean graph properties (`GraphProp`) together
  with the three hypotheses of the conjecture (isomorphism invariance
  `IsGraphProperty`, monotonicity `IsMonotone`, nontriviality `IsNontrivial`),
  deterministic decision trees (`DTree`, `depth`, evaluation `eval` on a
  graph, correctness predicate `DTree.Decides`), and the running example
  `hasEdgeProp` (having at least one edge).
- The slot zone states the conjecture (`conj`) and its negation (`refuted`).
  Both proof bodies are left blank; proving either one scores full marks.

Fidelity notes (see `tests/reference/concept-ledger.md` of the packaged task):
1. A graph property is a *boolean* function on graphs (Miller 2011, §0:
   "a graph property is simply a function [from the graphs on V] to {0,1}");
   the isomorphism-invariance clause is stated separately, exactly as in the
   literature.
2. Monotonicity is taken in the increasing direction ("preserved by the
   addition of edges"). The decreasing variant is equivalent by boolean
   complementation, which does not change decision-tree depth.
3. The conjectured statement "D(P) = C(v,2)" is phrased as the lower bound
   `v.choose 2 ≤ t.depth` for *every* deciding tree: the matching upper bound
   is witnessed by the naive tree querying all C(v,2) edges in any order, so
   the two forms are equivalent.
4. Queries may range over all of `Sym2 (Fin v)`, including diagonal pairs
   `s(a,a)`; a diagonal pair is never an edge, so such a query is always
   answered "no" and is useless. Allowing them does not change the minimal
   depth of a deciding tree.
5. v ≤ 1 is harmless: no nontrivial property exists there, so both mains are
   vacuously true over the empty hypothesis class — the "nontrivial" premise
   of the literature statement excludes these v automatically.
-/

import Mathlib

namespace Evasiveness

/-- A boolean graph property on `v` vertices: a boolean-valued function on the
simple graphs with vertex set `Fin v`. Following Miller 2011, §0, a graph
property is simply a function from the graphs on `V` to `{0,1}`; the
isomorphism-invariance requirement is stated separately (`IsGraphProperty`).
The adjacency-decidability instance argument lets concrete properties compute
over the edge finset; a property's value never actually depends on the choice
of instance. -/
abbrev GraphProp (v : ℕ) :=
  ∀ (G : SimpleGraph (Fin v)) [DecidableRel G.Adj], Bool

/-! ### Decision trees -/

/-- A deterministic decision tree over the candidate edges of a graph on
`Fin v`: a `leaf` outputs a boolean verdict; a node `query e t f` asks whether
the unordered pair `e` is an edge of the input graph and continues in `t` on
"yes" and in `f` on "no". -/
inductive DTree (v : ℕ) : Type
  | leaf : Bool → DTree v
  | query : Sym2 (Fin v) → DTree v → DTree v → DTree v

namespace DTree

/-- The depth of a decision tree: the worst-case number of queries along a
root-to-leaf path. -/
def depth : DTree v → ℕ
  | leaf _ => 0
  | query _ t f => max (depth t) (depth f) + 1

/-- Evaluate a decision tree on a concrete graph: follow the root-to-leaf path
whose queries are answered by the adjacency of `G`, and output the leaf bit. -/
def eval (G : SimpleGraph (Fin v)) [DecidableRel G.Adj] : DTree v → Bool
  | leaf b => b
  | query e t f => if e ∈ G.edgeFinset then eval G t else eval G f

/-- `t` decides the property `P` if on every input graph the leaf bit equals
the property value. The decision-tree complexity D(P) of a property is the
minimal depth of a tree deciding it. -/
def Decides {v : ℕ} (t : DTree v) (P : GraphProp v) : Prop :=
  ∀ (G : SimpleGraph (Fin v)) [DecidableRel G.Adj], t.eval G = P G

@[simp] theorem depth_leaf (b : Bool) : (leaf b : DTree v).depth = 0 := rfl

@[simp] theorem depth_query (e : Sym2 (Fin v)) (t f : DTree v) :
    (query e t f).depth = max t.depth f.depth + 1 := rfl

@[simp] theorem eval_leaf (G : SimpleGraph (Fin v)) [DecidableRel G.Adj] (b : Bool) :
    (leaf b).eval G = b := rfl

@[simp] theorem eval_query (G : SimpleGraph (Fin v)) [DecidableRel G.Adj]
    (e : Sym2 (Fin v)) (t f : DTree v) :
    (query e t f).eval G = (if e ∈ G.edgeFinset then t.eval G else f.eval G) := rfl

end DTree

/-! ### The three hypotheses of the conjecture -/

variable {v : ℕ}

/-- Isomorphism invariance: isomorphic graphs receive the same value. This is
the requirement that makes a bare boolean function a *graph property*
(Miller 2011, §0: "whenever two graphs G and H are isomorphic, P(G) = P(H)"). -/
def IsGraphProperty (P : GraphProp v) : Prop :=
  ∀ (G H : SimpleGraph (Fin v)) [DecidableRel G.Adj] [DecidableRel H.Adj],
    G ≃g H → P G = P H

/-- Monotonicity (increasing): the property is preserved by the addition of
edges (`G ≤ H` is the spanning-subgraph relation, i.e. inclusion of edge
sets). -/
def IsMonotone (P : GraphProp v) : Prop :=
  ∀ (G H : SimpleGraph (Fin v)) [DecidableRel G.Adj] [DecidableRel H.Adj],
    G ≤ H → P G = true → P H = true

/-- Nontriviality: some graph has the property and some graph does not
(Miller 2011; without this condition the conjecture fails — see the
checkpoints). -/
def IsNontrivial (P : GraphProp v) : Prop :=
  (∃ (G : SimpleGraph (Fin v)) (i : DecidableRel G.Adj), @P G i = true) ∧
    ∃ (H : SimpleGraph (Fin v)) (i : DecidableRel H.Adj), @P H i = false

/-! ### The running example: having at least one edge -/

/-- The property of having at least one edge ("non-emptiness"): the canonical
first example of an evasive property. -/
def hasEdgeProp (v : ℕ) : GraphProp v :=
  fun G => 0 < G.edgeFinset.card

-- END OF FIXED PART — auxiliary definitions and lemmas may be added below,
-- outside the CHECKPOINT slots.

/-! ## Slot zone: the conjecture and its negation

Prove **either** `conj` (the conjecture) **or** `refuted` (its negation) for
full credit.  There is no partial credit: auxiliary results are welcome but
do not affect the score. -/

-- @[slot main]
/-- **The evasiveness conjecture** (Karp, early 1970s): every nontrivial
monotone graph property on `v` vertices is evasive — every decision tree
deciding it has depth at least C(v,2), i.e. in the worst case it queries all
candidate edges. -/
theorem conj :
    ∀ {v : ℕ} (P : GraphProp v),
      IsGraphProperty P → IsMonotone P → IsNontrivial P →
        ∀ t : DTree v, t.Decides P → v.choose 2 ≤ t.depth := by
  -- CHECKPOINT conj BEGIN
  sorry
  -- CHECKPOINT conj END

-- @[slot main]
/-- The negation of the evasiveness conjecture: some nontrivial monotone graph
property on some vertex number `v` can be decided by a decision tree of depth
strictly less than C(v,2). -/
theorem refuted :
    ¬∀ {v : ℕ} (P : GraphProp v),
        IsGraphProperty P → IsMonotone P → IsNontrivial P →
          ∀ t : DTree v, t.Decides P → v.choose 2 ≤ t.depth := by
  -- CHECKPOINT refuted BEGIN
  sorry
  -- CHECKPOINT refuted END

end Evasiveness
