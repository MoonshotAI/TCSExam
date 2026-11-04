# Faithfulness Review: Deterministic versus Randomized Decision Trees on Total Functions

This note explains the task statement for readers comparing the mathematical definitions with the Lean source. The current scoring statements are `conj` and `refuted`; proving either earns full credit.

This document aligns the definition layer and five proposition slots in d-vs-r-total-functions with the cited literature.

- **Sources:** Nisan 1991, “CREW PRAMs and decision trees,” SICOMP 20(6) (D(f)=O(R(f)³) and R(f)≥bs(f)/3); Buhrman–de Wolf 2002 survey of complexity measures (CWI version, definitions of D and R and record of the open problem); Ambainis–Balodis–Belovs–Lee–Santha–Smotrovs 2017, JACM 64(5) (quadratic separation by pointer functions); Hamoudi 2025 survey of quantum query complexity, arXiv:2508.08852v1 (model in Definition 1, status in Proposition 9, and R≥bs/3 in Lemma 4.2).

## 1. Proposition-slot correspondence

| Slot | Literature correspondence | Role |
|---|---|---|
| conj | Open question in §6 of Buhrman–de Wolf 2002, “is the optimal exponent 2 or 3?”; Hamoudi 2025 Proposition 9 records D=O(R³) as the best known relation. | Main conjecture: is there a constant C with D(f)≤C·R(f)² for every total Boolean function? |
| refuted | Same sources. | Literal negation of the conjecture; proving either direction earns full credit in the former scoring design. |
| c1 symmetric_evasive | Classical adversary argument; also follows from the more general Rivest–Vuillemin 1976 theorem: every nonconstant symmetric Boolean function is evasive. | Deterministic side of special case (a): D=n for symmetric functions. The paired randomized fact R=Θ(n) (Nisan lower bound and Turán 1984, s≥(n+1)/2) gives exponent 1 in this class; randomized complexity is not itself a checkpoint. |
| c2 maj3_gap | Textbook small example of randomized advantage for three-variable majority; exact R(MAJ₃)=8/9 computed by the LP enumeration in small-examples.md. | Special case (b): strict separation on the smallest nontrivial instance, D=3>8/3≥Rc. |
| c3 compose_D_le | Classical decision-tree replacement construction (for example, property in §2 of Buhrman–de Wolf 2002). | Special case (c): composition upper bound D(f∘g)≤D(f)·D(g), a basic lemma for iterative separation constructions. |

## 2. Definition-layer correspondence

| Lean definition | Literature object | Correspondence |
|---|---|---|
| DTree n (inductive leaf/node type) | Decision tree (Hamoudi 2025, Definition 1: rooted ordered binary tree, internal nodes labeled by variables, leaves by outputs). | Matches. Repeated variable queries along a path are allowed in the literature too; an optimal tree does not need them, so D/Rc is unchanged. |
| DTree.eval | Follow the input’s value, taking the false/true branch, and output the reached leaf. | Exact match. |
| DTree.cost | Number of queries on input x (path depth). | Exact match. |
| DTree.Computes | The tree computes f correctly on every input. | Exact match. |
| D f (sInf of feasible depths) | D(f), minimum worst-case depth of a tree computing f. | Matches. sInf of an empty set would be 0, but the set is always nonempty: a full-query tree gives depth n (see small-examples and the positive-control construction dvrBuildFull), so it is a true minimum. |
| RTree n (finite type ι, family of trees, weights summing to 1) | Randomized decision tree, i.e. a probability distribution over deterministic trees (Hamoudi 2025, Definition 1, second paragraph). | Matches. Uses finite-support distributions; the literature permits arbitrary distributions, but finite support suffices because the optimum is attained on finite support and the conjecture is existential. |
| RTree.expCost | Expected number of queries on input x. | Exact match. |
| RTree.errProb | Error probability on input x. | Exact match. |
| Rc f (sInf of feasible costs) | R(f): minimum worst-case expected cost among distributions whose error is at most 1/3 on every input. | Definition convention in deviation 1; error 1/3 in deviation 2. |
| weight / Symmetric / Nonconstant | Hamming weight / depends only on weight / nonconstant function. | Exact match. |
| majFn n | Strict majority (weight > n/2). | Used only for n=3, where strictness does not change the result. |
| comp f g (indexed via finProdFinEquiv) | Composition f∘g on m blocks of n input bits. | Matches; indexing uses the canonical equivalence Fin m × Fin n ≃ Fin(m·n). |

## 3. Recorded deviations

1. **Define Rc by expected cost.** The literature uses two equivalent common conventions for R(f): (i) every tree in the distribution’s support has depth at most T (Hamoudi 2025, Definition 1), or (ii) the worst input’s expected cost is at most T (Buhrman–de Wolf 2002). They differ by at most a constant factor, using Markov’s inequality and error reduction to convert one convention to the other. This conjecture allows a free constant C in a polynomial relation, so that factor does not affect truth.

2. **Set the error parameter to 1/3.** This agrees with both cited sources; standard amplification makes any fixed error in (0,1/2) give the same conjecture.

3. **Use randomized trees with finite-support distributions.** See the RTree row above. This is the standard Lean alternative to measure-theoretic probability and follows the same pattern as the monotonicity family’s DetAlg mixture.

4. **Define D and Rc via sInf.** Constant functions have D=Rc=0 because a leaf computes them, so the conjecture is trivially satisfied in those cases and its open content is unchanged; n=0 is analogous.

5. **Do not use the Rubinstein family for special case (b).** The task brief suggested the “known quadratic separation Rubinstein family.” Checking the sources shows that Rubinstein 1995 gives a quadratic separation between block sensitivity bs and sensitivity s (quoted on page 9 of Hamoudi 2025 and in item 3 of dig2-boolean-fourier.md). Its R≥bs/3=Ω(n) and D are of the same order, so it does not separate D from R. For n=4, this task’s small-examples computation gives D=4, R=16/15, bs=s=2. The quadratic separation between D and R is instead the pointer-function family of Ambainis–Balodis–Belovs–Lee–Santha–Smotrovs (Hamoudi 2025 Proposition 9 records D(f)=Ω̃(R(f)²) [ABB+17]). Formally developing that family, including its construction and R upper bound, is a paper-scale task and unsuitable for a one-third checkpoint. Even exact small-n values exceed practical computation: the R LP requires enumeration over all decision trees on 16 or more variables. Therefore (b) is a strict separation on the smallest instance, D(MAJ₃)=3>8/3≥Rc; the asymptotic separation is described in the task background from the literature.

6. **Use the clean upper bound 8/3 witnessed by a zero-error mixture for c2.** The exact value Rc(MAJ₃)=8/9 comes from LP enumeration (small-examples.md), but its optimal mixture has an unwieldy support and is unsuitable for a handwritten Lean proof. A mixture of three rotations with zero error has expected cost 8/3 and can be checked arithmetically on all eight inputs. The statement Rc≤8/3 is true and captures the strict inequality R<D.

## 4. SOP 6.5 formulation checks

1. **Constraints on existential witnesses:** The conjecture’s witness is only a constant C, with no structural constraints. c3’s witness is a composition tree inside the proof; the proposition asserts only a numeric upper bound and has no degenerate empty-witness route. ✓
2. **Degenerate parameters:** At n=0 the input type is a singleton, and every f has D=Rc=0. The corresponding component of conj/refuted is respectively true/false as expected; it does not change the existential conjecture, and refuted depends on a nondegenerate component. Constant functions likewise have D=Rc=0. c1 has hypothesis 1≤n (for emphasis); at n=0, Nonconstant is impossible and the proposition is vacuously true. In c3, m=0 or n=0 gives 0≤0; both cases were checked separately. ✓
3. **Main-theorem hypotheses versus uses:** Not applicable; this task has an open conjecture and three independent special cases, with no lemma chain. ✓
4. **Substitution/evaluation points:** c2’s constants 3 and 8/3 were checked term by term (small-examples §2); c3 has no substitution point. ✓
5. **Base cases:** c1’s induction base n=1 is within the numerical checks; all cases n=1..5 were checked. ✓
6. **Two-sided conditions and boundaries:** conj and refuted are exact negations of the full existential statement, without truncation. c2 is a conjunction whose two sides are both true (D=3 and Rc≤8/3), independently checked. ✓
7. **Weakening and vacuity:** conj has the literature’s exact shape (∃C, for all n and f, D≤C·R²), with no weakening; refuted is its negation. There is no premise that rules out the counterexample direction. The special cases are established facts rather than vacuous ones (c2 has numeric evidence; c1/c3 have literature and numerical support). ✓

Two scoring-side lessons were also applied. The writable region between the fixed text and slots contains no notation/macro/syntax/elab declarations. The fixed-part marker string -- END OF FIXED PART appears only once: an initial header comment literally included the marker, causing the fixed-region check to stop inside the comment; a dry run caught and fixed this. The scoring description in instruction.md matches score.py line by line (blacklist, statement order, isolated slot scoring, axiom whitelist, exfalso scan, and partial-credit sum).

Known residual risk, recorded consistently with pilot packages: the scorer shares the “prove or refute v1” template with proof-conjecture-lean pilot packages (tuza-conjecture, alon-jaeger-tarsi, aaronson-ambainis). The template has no text blacklist for notation/macro/syntax/elab, so a custom notation or local instance in the writable region could theoretically change a slot’s meaning without editing the protected text. This semantic-layer hole is shared across the LEAN line and is recorded in SOP 6.5 as “not observed to be exploited”; it remains a line-wide convergence issue. The exfalso scan, as in aaronson-ambainis, was narrowed to an exact False conclusion: the adversary proofs of this task’s special cases naturally use helper lemmas ending in ¬, which the BCIKS20-family False|¬ scan would wrongly reject.
