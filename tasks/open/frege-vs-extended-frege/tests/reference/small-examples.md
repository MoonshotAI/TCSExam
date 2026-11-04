# Executable Small Examples — Behavioral Checks for the Frege vs. Extended Frege Definition Layer

Small hand-computable formulas and proofs exercise Lean definitions (evaluation, symbol count, atom set, validity of extension steps, and stepwise proof checking) and record the actual output; they serve as unit tests for the definition layer.

- Test file: probe `Probe.lean`, compiled with `lake env lean Probe.lean` after `lake build Task` in the positive-control candidate app, using a Lean validation image and Lean 4.33.0. The probe was discarded after use; results are listed below.

## Design notes

The definition-layer functions Formula/eval/size/subst/vars are computable structural recursions; `Tautology` on concrete small formulas can be checked by evaluating Boolean values for every assignment; `IsAxiom` holds for concrete instances by construction and is refuted for noninstances by `cases`; each step of `IsEFProof`/`ExtStep` is checked line by line on an explicit list. `decide` is used only for closed equalities and finite membership checks (natural numbers and formula literals, evaluated by the kernel; `native_decide` is not used). Hand-computed expectations come from §1 of concept-ledger. The probe runs against the positive-control candidate (`tests/reference/Basic.lean`) and uses its helper definitions (extProof, extD, extLine, idLine1–5, etc.).

## Small-example table (; all passed, PROBE_EXIT=0)

| ID | Check | Hand-computed expectation | Actual result |
|---|---|---|---|
| E1 | `proofSize` of the 12-line EF reference proof `extProof` | 100 (11+17+5+41+17+5+1+3) | `decide` passes ✓ |
| E2 | Line 0 of `extProof` is an `ExtStep` introducing atom 2 (shorthand `extD = atom 0 → atom 0`) | Form, p∉D.vars, and no prior line all satisfy the three conditions | Proof passes ✓ |
| E3 | atom 0 → atom 0 is a tautology | ¬φ∨φ is true under both assignments | Proof passes ✓ |
| E4 | `vars` behavior: `imp(atom 0, atom 0).vars = [0, 0]`; 2 ∉ [0, 0] | The list retains duplicates; freshness is decidable | `rfl` / `decide` passes ✓ |
| E5 | Conjunction-form extension line `extLine` is not an axiom | All ten axiom patterns are implications at the top level, so the forms do not match | All branches closed by `cases h` ✓ |
| E6 | `eval_agree`: if two assignments agree on atom 0, then they agree on the value of `imp(atom 0, atom 0)` | Concrete instance of the definition-layer lemma | Proof passes ✓ |
| E7 | Substitute atoms pointwise in an implication | `imp falsum (atom 1)` | `rfl` passes ✓ (`falsum` needs a type annotation; same handling as in the fnpb record) |
| E8 | The five-line Frege proof is also an EF proof (apply `frege_sub_ef`) | First two branches map directly | Proof passes ✓ |
| E9 | Last line (line 11) of `extProof` is the MP step using lines 10 and 9 | i=10, j=9 satisfy the MP conditions | Proof passes ✓ |
| E10 | Apply `ef_soundness` to the reference EF proof: `extD` is a tautology (via c1, same conclusion as E3) | If EF-provable, then valid | Proof passes ✓ |

## Issues found

- **Type annotation for `Formula.falsum`:** same as in the fnpb record. Since falsum has no parameters, inference fails when it occurs in a position with an unknown type (such as the codomain of an anonymous function); when writing bare falsum, specify the formula type (same handling in E7). This is a basic Lean issue and is not included in `instruction`.
- **Axiom cleanliness of kernel `decide`:** E1/E4 and checkpoint c2's `by decide` proofs were checked in the grading chain using the `#print axioms` whitelist (gate 4, all three checkpoints PASS), confirming kernel evaluation introduces no extra axiom such as `Lean.ofReduceBool`.
- **Extension-line branch in the c1 reference proof:** for assignment updates of the form `if a = p then … else …`, `simp only [Formula.eval]` simplifies the atom condition to `if True`, so a hand-written `if_pos` equality does not match. The final proof uses `rw [hD]` (an `eval_agree` instance, independent of the if-expression shape), then `cases hd : D.eval w <;> simp [hd]`. Recorded here as a reference for similar blocks; not included in `instruction`.
