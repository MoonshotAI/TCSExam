# Executable Small Examples — Behavioral Checks for the Polar-Code Scaling-Exponent Definition Layer

Small hand-computable channel/matrix instances exercise Lean definitions (BEC transition probabilities, Z value, one-step polarization recursion, `bitRev`, and the generator matrix) and record the actual output; they serve as unit tests for the definition layer.

- Test file: `workbench/Probe3.lean` (in this repository; run with `lake env lean Probe3.lean` in the candidate directory containing the reference checkpoint proofs, using a Lean validation image and toolchain leanprover/lean4:v4.33.0-rc1).

## Design notes

Among the three checkpoints, c1/c2 are symbolic real-number proofs (finite-sum expansion + `Real.sqrt_mul_self` + `ring`) and c3 uses kernel `decide`. This probe instantiates the symbolic theorems at concrete values (ε = 1/4, 1/2) and compares with hand-computed expectations; small examples of `bitRev` and `polarGen` are evaluated directly by `decide`. Hand-computed expectations come from concept-ledger §1 and the manual cross-check in the current Lean statement.

## Small-example table (run in sandbox; all passed, PROBE_EXIT=0)

| ID | Check | Hand-computed expectation | Actual result |
|---|---|---|---|
| P1 | Permutation behavior of `bitRev 2` | [0↦0, 1↦2, 2↦1, 3↦3] (reverse two bits) | `decide` passes ✓ |
| P2 | `polarGen 1` (generator matrix for block length 2) | = `polarKernel` = [[1,0],[1,1]] (one-bit reversal is trivial) | `decide` passes ✓ |
| P3 | Three transition probabilities for BEC(1/4) | W(0\|0) = 3/4, W(0\|1) = 0, W(?\|1) = 1/4 | `simp+norm_num` passes ✓ (three assertions) |
| P4 | Z value for BEC(1/4) | = 1/4 (instance of Z(BEC(ε)) = ε) | Passes by instantiating theorem c1 ✓ |
| P5 | One-step polarization of BEC(1/4) | Z(W⁻) = 2·(1/4) − (1/4)² = 7/16; Z(W⁺) = (1/4)² = 1/16 | Passes by instantiating theorem c2 ✓ (two assertions) |
| P6 | Output symmetry of BEC | `IsBMS` is satisfied by definition (an involution swaps some 0 ↔ some 1 and leaves erasure fixed) | `isBMS_BEC` instantiation passes ✓ |
| P7 | Point value of a summand in W⁻ (none, some 0), ε = 1/4 | √(W⁻0·W⁻1) = (1/2)·(1/4)·(3/4) = 3/32 | Passes using helper lemma `BEC_minus_summand` ✓ |
| P8 | `polarGen 2` (generator matrix for block length 4) | = Arikan G₄ = [[1,0,0,0],[1,0,1,0],[1,1,0,0],[1,1,1,1]] | `decide` passes ✓ |

## Issues found

- **`simp only` does not reduce an `if` condition involving a `Fin 2` literal** (initial c1/c2 reference proofs failed): decidable conditions like `if (1:Fin 2) = ⟨0,⋯⟩ then … else …` remain in the goal. Resolution: checkpoint proofs use `simp (config := { decide := true }) only [...]` (invoke `decide` on closed decidable propositions) and add `ite_true`/`ite_false` to the simp set; all passed on the second round. This resembles the known toolchain issue that kernel evaluation does not reduce ℚ, and is included in the checkpoint hints in `instruction.md` (real-number calculations use the symbolic route).
- **Wrong condition object for the second factor in `polarPlus`** (caught during implementation, not by the probe): see the “definition layer” section of `PROVENANCE.md`—the incorrect expression contradicted the identity Z(W⁺) = Z(W)². After repair, c2's hand-computed value matches the literature's BEC recursion.
