# Component Crosswalk — Lean Statements for the BC26 Linear Kernel from Independent-Set Reconfiguration (Lemma 6, Lemma 7, Lemma 16, Construction 13/Proposition 14, Lemma 18, Lemma 4, Theorem 1)

- What this document contains: A line-by-line crosswalk between the paper and the Lean identifiers in this task, including every deviation and its rationale.
- Intended readers: Task authors and reviewers; one of the three L2 fidelity records (component crosswalk).
- Sources: The main source is the LIPIcs conference version (STACS 2026, volume 364, 19:1–19:18; posted 2026-02-13). The long arXiv version 2506.03319 (first posted June 2025) is used to cross-check the lemma from Section 2. Numbering is one lower in the long version: conference Lemma 16 = long-version Lemma 15; conference Lemma 18 = long-version Lemma 17; conference Proposition 14 = long-version Proposition 13; conference Construction 13 = long-version Construction 12. The two versions agree paragraph by paragraph in that section; the long version writes χ_up as χ. All lemma references below use the LIPIcs version.
- Packaged statements: `environment/app/Task/Basic.lean` (namespace `PlanarISReconfigKernel`).

## 1. Checkpoint numbering crosswalk

Each row documents one checkpoint. “Dependencies” lists other checkpoints expected to be used in its Lean proof; the grader injects them as axioms in isolation.

| Checkpoint | Lean name | Paper reference | Informal content | Dependencies |
|---|---|---|---|---|
| c1 | `c1_large_reconfigurable` | Lemma 6 | Given a proper q-coloring, if |C1| ≥ q·k then there is a k-element independent set Im ⊆ C1 such that a reconfiguration sequence from Is to It stays entirely in X ∪ Im. | None |
| c2 | `c3_card_le` | Lemma 7 | K_{3,r}-minor-free ⟹ |C3| ≤ (r−1)·N3. | None |
| c3 | `connected_few_class_nbrs` | Lemma 16 | For a {x,x'}-class C, a connected vertex set A disjoint from C ∪ {x,x'} is adjacent to at most r−1 vertices of C. | None |
| c4 | `kernel_construction` | Construction 13 + Proposition 14 | Existence and size bound for the kernel construction: if |C2| ≤ q(N2(3r−2)+k), do not trim (W = the whole graph); otherwise there is a pair (I,W) satisfying the trimming rules, with |W ∩ C2| ≤ q(N2(4r−1)+k) and k ≤ |I ∩ W|. | None |
| c5 | `unlock_reaches_helpful` | Lemma 18 | Under the trimming construction, if a big class can be unlocked from Is, then a helpful set (a k-element subset of I ∩ W) is reachable from Is inside W. | c3 |
| c6 | `both_unlock_yes` | Lemma 4 | If both sides can unlock a big class, the original instance and the trimmed instance are equivalent and both are yes-instances. | c5 |
| c7 | `isr_tj_linear_kernel` (main theorem) | Theorem 1 (explicit-constant form) | If 1 ≤ r, 1 ≤ k, G is K_{3,r}-minor-free, G has a proper coloring with max{r,6300}+3 colors, and N2+N3 ≤ 2^{5r+13}(r+3)^{2r+5}·k, then ∃W ⊇ X with |W| ≤ K(r)·k and (reachable in G iff reachable inside W). | c1, c2, c4, c5, c6 |

Main-theorem constant:
[
K(r) = 2 + q + (r−1)·B + q·(B·(4r−1)+1),
]
where q = max{r,6300}+3 (the max{r,6300}+3 coloring bound in Lemma 11), and B = 2^{5r+13}·(r+3)^{2r+5} (right side of the second inequality in Corollary 10). Assembly:
[
|W| ≤ |X|+|C1|+|C3|+|W∩C2| ≤ 2k+q·k+(r−1)·N3+q·(N2(4r−1)+k),
]
then N3 ≤ B·k and N2 ≤ B·k follow from hn23. In the no-trimming branch, |C2| ≤ q(N2(3r−2)+k) ≤ q(N2(4r−1)+k) (use 3r−2 ≤ 4r−1 for r ≥ 1). In the trivial-yes branch, |W| = |X ∪ Im| ≤ 3k ≤ K(r)·k.

## 2. Definition-layer crosswalk (paper ↔ this task)

| Concept | Paper | Identifier in this task | Notes |
|---|---|---|---|
| Graph | Simple undirected finite graph G | `G : SimpleGraph V`, `[Fintype V] [DecidableEq V] [DecidableRel G.Adj]` | Thin graph-theory layer from mathlib. |
| Independent set | A set of pairwise nonadjacent vertices (§1) | `G.IsIndepSet ↑s` (existing mathlib Set-level definition, with Finset coercion) | Direct match. |
| One token-jump step | §1: remove one token and place it on any vertex, keeping the intermediate state independent | `TJStep G I J`: J is independent ∧ ∃v∈I, w∉I, J = insert w (erase v I) | Cardinality is preserved automatically (v∈I, w∉I ⟹ unchanged card), so checkpoint statements need no k parameter. |
| Reconfiguration sequence | §1: a sequence of reconfiguration steps | `Reconf` = `Relation.ReflTransGen (TJStep G)`; `ReconfIn G W` is the version restricted to W | ISR-TJ(G′,·,·) is expressed with ReconfIn; no subgraph API is introduced. |
| K_{3,r} minor | §2 (standard definition implicit) | `HasK3rMinor`: 3+r pairwise disjoint, nonempty, connected branch sets, with an edge between every set on the 3-side and every set on the r-side; `K3rMinorFree` is its negation | Connectivity means all vertices in a walk’s support lie in the set; equivalent to the contraction definition (standard). All three uses in the paper (single-vertex branch sets in Lemma 7, {x},{x'},A in Lemma 16, and contraction of {a,b,x} in Lemma 18) are direct special cases of branch-set construction. |
| Proper coloring | χ_up(G) in §2.2 (a constructible upper-bound coloring) | `ProperColoring G c` (c : V → Fin q, adjacent vertices have different colors) | The paper uses only existence; efficient construction is not formalized (no complexity model). |
| Key vertices | X := Is ∪ It | `keySet Is It` | Direct match. |
| X-projection class | C_Y := {v ∉ X : N(v) ∩ X = Y} | `projClass G X Y` | Direct match (neighborFinset plus filtering). |
| C1 / C2 / C3 | §2.1: union of classes with |Y| ≤ 1 / = 2 / ≥ 3 | `C1`/`C2`/`C3` (filtered by the size of N(v) ∩ X) | Equivalent: every class belongs to exactly one part. |
| N2 / N3 | §2.1: number of nonempty 2-classes / ≥3-classes | `N2`/`N3` (powerset and filtered counting) | Direct match. |
| Big / small class | (3) of Construction 13: |C_Y| ≥ χ_up(2r−1)+1 means big | `bigClass G X Y q r` | Direct match (q = χ_up). |
| Trimming construction | (1)–(5) of Construction 13 | `TrimCon` predicate + existence statement in `kernel_construction` | The algorithmic construction is represented by a predicate: (1) becomes the left disjunct in c4; thresholds 3r−1 / 3r−2 in (5a)/(5b), retention of a 2r-independent set, and moving I out of poor classes all match. Helpful pool = I ∩ W (the paper’s “I after deletion”). |
| Unlock | §2.3: achieve |I′ ∩ N(C_Y)| ≤ 1 | Predicate `(J ∩ Y).card ≤ 1`, where Y is a pair of key vertices | **Deviation 5**, below. |
| Helpful independent set | §2.3: k-element subset of I after deletion | H ⊆ I ∩ W ∧ H.card = k | Direct match. |

## 3. Statement-level deviations (itemized, with reasons)

1. **Two cited results are packaged as assumptions of the main theorem.** The paper cites, but does not prove, (i) the coloring bound (Lemma 5, Kostochka–Prince 2010: if r ≥ 6300 then a K_{3,r}-minor-free graph is (r+2)-degenerate, hence χ ≤ r+3; for r < 6300 reduce to K_{3,6300}-minor-free, combining to max{r,6300}+3); and (ii) the neighborhood-complexity bound (Corollary 10, cited from Theorem 18 of [7], taking s=1, t=r+3, A=X). The package takes them as c7 premises (a supplied proper q-coloring, and N2+N3 ≤ nbrComplBound r · k), matching the practice of packaging Chernoff in the related lcc-exp-lb task. Both hold for every K_{3,r}-minor-free graph, so the assumptions are inhabited. c1/c4 state coloring using a more general q; c7 instantiates q = colorBound r.
2. **Kernel form: vertex subset + explicit constant + equivalence; no polynomial-time bound.** Theorem 1 in the paper says “admits a kernel of size linear in k”; the “Main General Theorem” in §2.1 says “either trivial yes, or equivalent to ISR-TJ(G′,·,·) with G′ a subgraph, |V(G′)| = O(k).” The package states ∃W ⊇ X, |W| ≤ K(r)·k, and (Reconf G Is It ↔ ReconfIn G W Is It): the constant is explicit (stronger than O(k), assembled from Lemmas 11+12); the trivial-yes branch is folded into the same conclusion (W := X ∪ Im, with Lemma 6’s sequence inside and |W| ≤ 3k); polynomial-time computability is not formalized (no complexity model in the definition layer, consistent with related tasks).
3. **c1 uses the witness-strengthened form.** Lemma 6 in the paper concludes that the instance is yes. The trivial-yes branch in the main theorem needs an explicit W. Therefore c1 states: there is a k-element independent set Im ⊆ C1 and a reconfiguration Is to It inside X ∪ Im. This is exactly what the paper proves (choose the largest color class by pigeonhole; both stages of movement stay in X ∪ Im; reverse the argument from It). The strengthening is needed by the downstream call.
4. **c3 uses the connected-subset strengthening.** Lemma 16 in the paper refers to “each connected component of G[V \ (C ∪ {x,x′})]”; its proof uses only connectedness (A serves as a one-sided branch set). The proof works word for word for any connected subset, and avoids a connected-component API (mathlib has no component object for vertex subsets). The paper’s statement follows as a special case, since a component is connected.
5. **Unlock is formalized over the pair of key vertices.** The paper’s definition says |I′ ∩ N(C_Y)| ≤ 1, followed on the same page by the explanation “at most one token on the two key vertices” (“both tokens have moved off the vertices of Y (moving the first of these tokens off is called unlocking C_Y)”; the proof of Lemma 18 says |N(C) ∩ X| = 1). Since every vertex in the class has X-neighborhood Y, N(C_Y) ∩ X = Y, so the two readings agree on X and differ only for tokens outside X. The package uses |J ∩ Y| ≤ 1 because (i) this is the reading used in both actual applications: the premise of Lemma 18 and the “cannot unlock ⟹ sequence does not enter a big class” step in the Main General Theorem (entering a class with a token ⟹ the resulting set is independent ⟹ neither key vertex has a token ⟹ unlocked); and (ii) with the full-neighborhood reading, this step fails (the token entering the class is not itself in N(C_Y), and nothing restricts other tokens adjacent to the class).
6. **Construction 13 becomes a predicate, and c4’s conclusion includes a classification disjunction.** Step (1) (if |C2| is small, do nothing) becomes the left disjunct in c4 (W = the entire graph; no I needed). Step (2)’s pigeonhole choice of I and steps (3)–(5)’s class rules become the seven conjuncts of `TrimCon`. c4 also states k ≤ |I ∩ W|, used in the proof of Lemma 18: “we deleted vertices of I only in step (5b) … at most N2(G)(3r−2)”, hence |I ∩ W| ≥ |I| − N2(3r−2) = k. This is a construction property, not an additional assumption.
7. **Boundary premises 1 ≤ r and 1 ≤ k are stated in the main theorem and c5/c6.** The paper’s Theorem 1 assumes “each positive integer r”; k=0 makes Is=It=∅ and carries no content. c1/c2/c3/c4 were checked case by case and need no boundary premises (when r=0, r−1 is 0 under truncated natural subtraction: c2’s K_{3,0}-minor-free condition means at most two vertices, so C3=∅; c3 is likewise vacuous; when q=0, existence of a coloring implies the graph is empty, so the premises are contradictory or the conclusion is trivial). c5/c6 need r ≥ 1 (arithmetic such as 2r ≤ 3r−1) and k ≥ 1 (use of a nonempty helpful set), consistent with the paper’s assumptions.
8. **Intermediate-state independence is carried by the one-step definition.** The paper requires every intermediate arrangement to remain an independent set of size k. `TJStep` requires the target to be independent, and cardinality preservation is automatic, so the reachability relation needs no explicit size parameter. Equivalence: starting at Is (independent, size k), every set in any sequence remains independent and has size k.

## 4. Step-by-step main-theorem assembly check (the c7 chain)

1. Let X = keySet Is It, q = colorBound r, B = nbrComplBound r. Then |X| ≤ |Is| + |It| = 2k.
2. If q·k ≤ |C1|, instantiate c1 with coloring c and hc. It gives an independent Im ⊆ C1 with |Im|=k and ReconfIn G (X ∪ Im) Is It. Take W := X ∪ Im: X ⊆ W; |W| ≤ 2k+k = 3k ≤ K(r)·k (K(r) ≥ 2+q ≥ 2+6303). For equivalence: ReconfIn ⟹ Reconf by dropping the restriction; conversely, Reconf G Is It holds and ReconfIn G W Is It also holds, so the two propositions are equivalent. ✓
3. Otherwise |C1| ≤ q·k (over naturals, ¬(a ≤ b) ⟹ b ≤ a). Apply c4 (hq: q ≥ 1 is immediate) to obtain (I,W) and the size bounds, in two cases:
4. **Left disjunct (no trimming, W is the full graph):** V is the disjoint union X ∪ C1 ∪ C2 ∪ C3 (each v ∉ X belongs to exactly one part, according to the size of its X-neighborhood). Thus
   [
   |V|=|X|+|C1|+|C2|+|C3|
   ≤ 2k+qk+q(N2(3r−2)+k)+(r−1)·N3
   ]
   by c2. By hn23, N2 ≤ B·k and N3 ≤ B·k; since 3r−2 ≤ 4r−1 for hr, |W| = |V| ≤ K(r)·k. ✓ For equivalence, when W is all of V, ReconfIn G W and Reconf G are the same definition (I,J ⊆ univ hold automatically). ✓
5. **Right disjunct (TrimCon):** size: W is the disjoint union (X ∪ C1 ∪ C3) ∪ (W ∩ C2), hence
   [
   |W| ≤ 2k+qk+(r−1)Bk+q(B(4r−1)k+k)=K(r)·k.
   ]
   Equivalence (← is immediate) has three cases:
   (a) If Is can unlock a big class and It can unlock a big class, c6 gives equivalence and the yes result directly. ✓
   (b) If Is cannot unlock any big class, every reconfiguration sequence from Is stays in W. Suppose a step enters a vertex v outside W. Then v ∉ X ∪ C1 ∪ C3, so v ∈ C2. Let C_Y be its class. If C_Y is small, the whole class is retained, so v ∈ W, contradiction; hence C_Y is big. The resulting independent set J contains v and is disjoint from N(v). Since Y = N(v) ∩ X ⊆ N(v), J ∩ Y = ∅, hence |J ∩ Y| = 0 ≤ 1. Thus J witnesses that the sequence from Is unlocks the big class C_Y (Y ⊆ X, |Y|=2, and the big condition all hold), contradicting the assumption. So every Reconf sequence from Is stays in W, and Reconf G Is It ⟹ ReconfIn G W Is It. ✓
   (c) If It cannot unlock, use symmetry of Reconf (each step is reversible: J = insert w (erase v I) iff I = insert v (erase w J), and independence holds at both ends) to reduce to (b). ✓
6. Check premises at all checkpoint call sites: c1 needs coloring hc and the qk ≤ |C1| branch (step 2); c2 needs hminor; c4 needs hq (q = max{r,6300}+3 ≥ 1) and hc; c5 needs hr, hk, hminor, hcon, hIk, hunlock (the right disjunct of c4 and the unlock witness in case (a)); c6 has the same premises. ✓ Every premise in the main theorem is covered where it is used.

## 5. Premise-by-premise check for each checkpoint (against the source)

- **c1:** The paper assumes “|C1| ≥ χ_up(G)k” and an efficiently constructible χ_up coloring. The package uses qk ≤ |C1| plus a supplied proper q-coloring, matching it. The paper concludes “yes-instance”; the package strengthens this to an explicit witness (Deviation 3). Independence and size k for Is, It are standing assumptions from §2, included in each checkpoint.
- **c2:** The paper assumes only K_{3,r}-minor-free and concludes |C3| ≤ (r−1)N3 point for point. The package matches.
- **c3:** The paper assumes x,x′∈X and C is their class; it concludes every component has at most r−1 neighbors. The package strengthens to connected subsets (Deviation 4); premises hx,hx′,hxx′ ensure {x,x′} is genuinely a two-element key set.
- **c4:** Thresholds match exactly: no-trimming branch q(N2(3r−2)+k) (step (1)); big threshold q(2r−1)+1 (step (3)); rich/poor cutoffs 3r−1 / 3r−2 (steps (5a)/(5b)); size bound q(N2(4r−1)+k) (Proposition 14). A poor class retains “any 2r-independent set” and I is moved out of that class (second sentence of step (5b)). The coloring premise supplies both pigeonhole steps (choosing I; and existence of a 2r-independent set in a big class: |C_Y| ≥ q(2r−1)+1 implies some color class has size ≥ 2r).
- **c5:** The paper assumes that a big class can be unlocked from Is and that G′ comes from Construction 13; it concludes that a helpful set is reachable inside G′. The package uses hcon (TrimCon), hIk (k ≤ |I ∩ W|), and hunlock (∃J, Reconf G Is J ∧ ∃ big-class key pair Y with |J ∩ Y| ≤ 1); conclusion H ⊆ I ∩ W, |H|=k, ReconfIn G W Is H. hr/hk are standing assumptions in the paper (positive integer r and nonempty instance).
- **c6:** Lemma 4 says that if both sides can unlock, the instances are equivalent and both yes. The package concludes (Reconf ↔ ReconfIn) ∧ Reconf, matching it.
- **c7:** Theorem 1 says that for every positive integer r, a K_{3,r}-minor-free graph has a kernel of size O(k). The package makes the constant explicit, packages two cited facts as premises, and uses a vertex-subset kernel (Deviations 1/2).

## 6. Small-example cross-check summary

Executable small examples (Python version of the definition layer, E1–E7 all passed; script `small_examples.py`,) cover: semantics of token-jump reachability (E1, including a comparison where restricting to ReconfIn changes the answer); class partition and counts (E2); boundary of Lemma 7 (E3: |C3|=(r−1)N3 exactly with no minor, one more vertex creates K_{3,3}); Lemma 6 case (E4); thresholds and counts in Construction 13 (E5: case 2 triggers, rich/poor rules, bounds on |W∩C2| and |I∩W|); minor predicate behavior (E6: K_{3,3} does/does not contain a K_{3,4} minor; K_{3,0}-minor-free iff at most two vertices); constant assembly inequality (E7). Itemized records are in `small-examples.md`.
