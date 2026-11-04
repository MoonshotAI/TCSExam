# Executable Small Examples: Checking the Frege Definition Layer

Small hand-checkable formulas and proofs exercise the Lean definitions of evaluation, symbol count, axiom verification, substitution, and step-by-step proof checking. Actual output from each run is recorded below.

- Probe: `Probe.lean`, compiled in the task app copy using `lake build Task` followed by `lake env lean Probe.lean`; a Lean validation image, Lean 4.33.0.

## Design notes

`Formula` / `eval` / `size` / `subst` are computable structural-recursive definitions. `Tautology` for a concrete small formula can be checked by Boolean evaluation at every assignment (split by cases on assignments). Concrete `IsAxiom` examples follow directly from constructors. `IsProof` for an explicit five-line list can be checked line by line. `decide` is used only for closed equalities (natural numbers and formula syntax, evaluated by the kernel); `native_decide` is not used. Expected values come from Section 1 of `concept-ledger.md`.

## Small-example results (; all passed; PROBE_EXIT=0)

| ID | Check | Hand-computed result | Actual output |
|---|---|---|---|
| E1 | `proofSize` of the five-line Hilbert derivation of φ→φ | 41 (7+17+9+5+3) | `decide` passed ✓ |
| E2 | φ → φ (atom 0) is a tautology | ¬φ∨φ is true under both assignments | Proof passed ✓ |
| E3 | ⊥ is not a tautology | False under the all-false assignment | Proof passed ✓ |
| E4 | Symbol counts: binary `imp` = 3; `or(falsum, and)` = 5 | 3; 5 (1+1+3) | `decide` passed ✓ (two assertions) |
| E5 | Axiom instances: instance k and Peirce instance | Directly provided by constructors | Proof passed ✓ (two assertions) |
| E6 | Atom 0 is not an axiom | None of the ten axiom schemas matches | All branches closed by `cases h` ✓ |
| E7 | Substitution on `imp`: replace each atom, distribute through connectives | `imp falsum falsum` | `rfl` passed ✓ |
| E8 | Excluded-middle instance φ ∨ ¬φ (¬φ is represented by φ→⊥) is a tautology | True under both assignments | Proof passed ✓ |
| E9 | Line 3 of the five-line proof is the MP step from lines 1 and 2 | i=0, j=1 satisfy the MP conditions | Proof passed ✓ |

## Run record

- First pass: Lean could not infer the type parameter for `Formula.falsum` inside an anonymous function (`don't know how to synthesize implicit argument α`). Adding the annotation `(Formula.falsum : Formula ℕ)` fixed it.
- Second pass: all 12 examples passed, with no compiler errors or warnings; PROBE_EXIT=0.
- The `proofSize` value 41 was also checked by a positive judging control: `proofSize π ≤ 41` in the `id_short_proof` slot passed using `decide` (gate 4 in `logs/scoring-matrix.log`).

## Issues found

- **Type annotation for `Formula.falsum`:** falsum has no parameters, so α cannot be inferred when it appears where the expected type is unknown (such as an anonymous function's return type). When writing a bare falsum in a probe or proof, specify the formula type. The same advice applies to agents solving the task; this is standard Lean behavior and is not included in the instruction.
- **Axiom cleanliness of kernel `decide`:** E1/E4 and the checkpoint c2 proof by `decide` were checked against the judging-chain `#print axioms` whitelist (all three examples at gate 4 passed), confirming that kernel evaluation introduces no extra axioms such as `Lean.ofReduceBool`.
