# Faithfulness Review: Frege versus Extended Frege

This note explains the task statement for readers comparing the mathematical definitions with the Lean source. The current scoring statements are `conj` and `refuted`; proving either earns full credit.

This document compares the literature statement of whether Frege can polynomially simulate Extended Frege (EF) with the Lean statement used by this task, and explains all deviations.

- **Definition-layer survey:** proof-circuit.md.
- **Background sources:** Wikipedia’s “Frege system” entry (Extended Frege section) and “Propositional proof system” entry (p-simulation paragraph), fetched through the session proxy. Cook–Reckhow 1979 bibliography, the original extension-rule wording, and the direction of p-simulation were checked. The definition layer starts from the finished sibling task frege-not-pbounded; reused choices are identified below.
- **Released statement:** environment/app/Task/Basic.lean; it matches the fixed region of tests/reference/Basic.lean word for word, apart from checkpoint proof bodies and auxiliary definitions.

## 1. Literature statement and Lean correspondence

Cook–Reckhow 1979 introduced EF and simulation; Krajíček’s 2019 book lists this as a central problem. EF extends Frege system F by a rule that introduces p↔D (with ↔ expanded in F’s language), where atom p has not occurred in any earlier formula, including axioms, does not occur in D, and does not occur in the formula A being proved (the conclusion condition). The Wikipedia “Frege system” entry gives the first two conditions; the conclusion condition follows Cook–Reckhow and the standard textbook formulation—without it, the system can “prove” a bare atom, as noted for checkpoint c1.

The question is whether Frege p-simulates EF: does there exist a polynomial q such that every EF proof π of conclusion φ has a Frege proof π′ of the same conclusion with length at most q(|π|)? The standard conjecture is that it cannot.

| Concept | Literature | Lean identifier in this task | Notes |
|---|---|---|---|
| Propositional formula | Arbitrary nesting of proposition variables p₀,p₁,... with a functionally complete set of connectives. | Frege.Formula α: atom / falsum / and / or / imp; the main slot fixes α=ℕ. | Same convention as frege-not-pbounded deviation 1. |
| Formula length | Number of symbols. | Formula.size. | Same as frege-not-pbounded. |
| Variables of a formula | Proposition variables appearing in it. | Formula.vars : Formula α → List α (duplicates allowed; membership is what is needed). | Added so freshness conditions for extension can be expressed. |
| Frege system | Finite set of axiom schemas plus modus ponens; sound and (implicationally) complete. | Ten fixed axiom schemas IsAxiom plus MP, the same system as frege-not-pbounded. | Same as that task’s deviations 2/3. |
| Frege proof | Finite sequence of formulas, each an axiom instance or obtained by MP. | IsProof. | |
| Extension rule | Derive p↔D, where p occurs neither in D nor any previously derived formula (including axioms). | Third constructor of IsEFProof: line is and (imp (atom p) D) (imp D (atom p)), with p∉D.vars and ∀l<k, p∉(π.get l).vars. | ↔ expands in the language; “previously derived” is represented by previous sequence lines. See deviations 1 and 2. |
| Extension step | Same conditions, as a property of one line. | ExtStep π k p. | Same conditions as the third IsEFProof constructor; used by the conclusion condition. |
| EF proof of A | EF sequence ending in A, with the conclusion condition that no extension variable occurs in A. | EFProves π φ := IsEFProof π ∧ π.getLast?=some φ ∧ ∀k p, ExtStep π k p → p∉φ.vars. | See deviation 3. Without this condition the system can “prove” a bare atom; EFProves’ docstring explains this. The three components of EF soundness have been proved (IsAxiom.tautology, Tautology.mp, Formula.eval_agree); the assembled theorem is taken as a standard literature fact. |
| EF-provable | There exists an EF proof. | EFProvable φ := ∃π, EFProves π φ. | |
| Proof length | Number of symbols. | proofSize. | Same as frege-not-pbounded deviation 4. |
| Simulation by length | There is a polynomial q such that each EF proof π of φ has a Frege proof π′ of φ with |π′|≤q(|π|). | Expressed by the negation form used for conj below. | Length convention in deviation 5. |
| Conjecture | Frege does not p-simulate EF: for every polynomial q there is an EF proof π such that every same-conclusion Frege proof π′ has |π′|>q(|π|). | conj: ∀d, ∃φ ∃π, EFProves π φ ∧ ∀π′, IsProof π′ → π′.getLast?=some φ → (proofSize π+1)^d < proofSize π′. | Quantifiers are aligned in retranslation.md. “Every Frege proof is larger” is equivalent to “the shortest Frege proof is larger,” as in frege-not-pbounded deviation 5. |
| Negation of conjecture | Literal negation: EF can be simulated. | refuted : ¬(conj statement). | Same two-main-slot pattern as tuza. |
| Polynomial | Arbitrary polynomial q. | Explicit monomial family (proofSize π+1)^d, d:ℕ. | Same as frege-not-pbounded deviation 6. |

## 2. Deviations and rationale

1. **Expand ↔ as (p→D)∧(D→p).** The Wikipedia Extended Frege section says to “derive a formula p↔D, where ↔ abbreviates its definition in the language of the particular F.” This task uses connectives {⊥,∧,∨,→}, as does frege-not-pbounded deviation 1; the standard expansion is (p→D)∧(D→p). Both directions can be obtained using ∧ elimination, so the behavior matches the literature.

2. **Represent “p has not occurred in any earlier formula, including axioms” as “p does not occur in any earlier line.”** Every sequence line is a derived formula, and axiom instances are also lines, so this is exact. The pitfall identified in the survey (proof-circuit.md §4.1) is that freshness must use Formula.vars, forbid p in any prior formula, and include the formula being abbreviated. Both conditions are enforced: p∉D.vars and ∀l<k, p∉(π.get l).vars.

3. **Apply the conclusion condition to every line satisfying the shape-and-freshness test (ExtStep), slightly stronger than Cook–Reckhow’s original pathological case.** The original condition says that variables introduced by extension steps do not appear in A. Here every line of the form (p→D)∧(D→p) with fresh p is treated as an extension step. A pathological line might also be derivable by MP; the original could treat it as an MP line and permit p in the conclusion, while this definition forbids that. Variable renaming removes the difference: rename p to a fresh atom and the proof remains valid. This formulation is cleanest for an unannotated sequence, where one cannot separately mark which lines are extension steps. The conclusion condition cannot be omitted: without it, introduce p↔D for a provable D, extract D→p, and use MP to “prove” the bare atom p; checkpoint c1 targets this issue.

4. **Prove the three components of EF soundness, but do not include the assembled claim in this file.** The definition layer proves IsAxiom.tautology (each axiom is a tautology), Tautology.mp (MP preserves tautologies), and Formula.eval_agree (an assignment’s values outside a formula’s variables are irrelevant). None requires [DecidableEq α]. The assembled statement “every EF-provable formula is a tautology” is taken as a standard literature fact, since its proof must modify an assignment at an extension step using (fun a => if a=p then …), which needs decidable equality on atoms. The definitions IsEFProof/ExtStep do not need that instance; membership in vars is propositional.

5. **Do not formalize the polynomial-time translation function in p-simulation; use the length-simulation convention.** Cook–Reckhow p-simulation requires a polynomial-time computable translation function. This definition layer, like frege-not-pbounded, compares only existence of proofs with bounded length. Direction: conj (even length simulation does not exist) implies the literature conjecture (no p-simulation), so it is a sufficient form. refuted (length simulation exists) is weaker than existence of p-simulation. Both literature directions are open, and a kernel proof in either direction would be substantive progress. This convention difference is recorded explicitly.

6. **Require the EF proof in conj to satisfy the conclusion condition (EFProves), rather than merely IsEFProof.** Bare IsEFProof is unsound (see deviation 3). If conj allowed arbitrary IsEFProof sequences, it could choose a “proof” of a bare atom; no Frege proof exists, so “all Frege proofs are larger than the bound” would hold vacuously and make conj trivial. With EFProves, the formula is a tautology by EF soundness. The three components of soundness are proved; the assembled claim is taken as standard literature (see deviation 4), matching the literature’s notion of EF proof.

7. **Write “polynomial” as the explicit monomial (proofSize π+1)^d.** As in frege-not-pbounded deviation 6, every polynomial is eventually bounded by (n+1)^d for some d, and (n+1)^d is itself a polynomial, so the conventions are equivalent. The bound acts directly on proof-symbol length; there is no need to introduce formula length as an intermediate quantity, since textbook p-simulation is measured by proof length.

8. **Fix the variable type to ℕ in the main slot and c2.** As in frege-not-pbounded deviation 7, this supplies infinitely many variables as assumed in the literature. Definitions IsEFProof/ExtStep/EFProves remain parameterized by arbitrary α.

9. **Fix one concrete Frege system for the separation question.** Extending deviation 2 of frege-not-pbounded: Reckhow 1979 proves all Frege systems p-equivalent. Their EF extensions are p-equivalent as well (translate rows by simulation and copy extension steps), so the separation does not depend on the chosen system. Krajíček’s book likewise fixes a system.

## 3. Direction check

The direction of p-simulation is the easiest place to reverse the claim, so it is checked explicitly.

- On the Wikipedia “Propositional proof system” page, P p-simulates Q is written P≤pQ or Q≤pP depending on convention. The semantic definition is unambiguous: given a Q-proof of x, one can find in polynomial time a P-proof of the same tautology. The simulator P receives the simulated system Q’s proof and produces a proof with the same conclusion.
- Here the simulated system is EF (stronger); the simulator is Frege. The conjecture says Frege cannot simulate EF.
- Lean form: conj says for every d there is an EF proof π such that every same-conclusion Frege proof π′ has length greater than (|π|+1)^d. This expands “no length simulation,” i.e. the negation of “there exists d such that every π has a π′ with |π′|≤(|π|+1)^d.” refuted=¬conj says such a d exists: Frege can simulate EF by length. The direction is not reversed: conj is separation, the standard conjecture; refuted says simulation is possible.
- Relation to frege-not-pbounded: that problem asks whether Frege is not polynomially bounded (some tautology family requires long proofs); this one asks for relative efficiency between Frege and EF. EF polynomial boundedness is equivalent to NP=coNP (Cook–Reckhow theorem plus EF’s position as the strongest natural system); the separation conjecture here is weaker than “EF is not polynomially bounded,” and neither it nor “Frege is not polynomially bounded” implies the other. If Frege simulated EF, the two conjectures would have the same truth value; the standard expectation is that both are true. This relationship is background in instruction.md and is not part of the Lean statement.

## 4. Distinction from nearby problems

- **Sibling task frege-not-pbounded:** asks whether Frege is not polynomially bounded (a family of hard tautologies). This task shares its definition layer—the fixed-region formula system is reused, adding Formula.vars, the EF section, and eval_agree. The tasks occupy different cells: an absolute lower bound versus relative efficiency between proof systems.
- **Adjacent systems:** substitution Frege, which adds substitution rules, lies between Frege and EF. Lower bounds for fixed-depth Frege (AC⁰-Frege) are known (Ajtai et al.), but those results require depth definitions and switching lemmas absent here and are not checkpoints. Finite sanity properties of the definition layer do not follow from the main statement.
- EF not polynomially bounded (equivalent to NP≠coNP) is a stronger conjecture and is not this problem.

## 5. Known frontier

- EF was introduced by Cook–Reckhow 1979, “The relative efficiency of propositional proof systems,” JSL 44(1):36–50 (bibliography checked against the Wikipedia references).
- EF permits treating proofs as Frege proofs that operate on circuits (wording from the Wikipedia EF section); under Cook’s correspondence EF is the nonuniform counterpart of Cook’s PV and Buss’s S¹₂.
- Frege versus EF is the first open cell in the proof-strength hierarchy; the “Proof strengths of different systems” chart marks strict separation of EF from Frege as unresolved.
- The best known lower bound on Frege proof-symbol length is quadratic (same anchor as frege-not-pbounded); no superpolynomial lower bound against EF is known.
