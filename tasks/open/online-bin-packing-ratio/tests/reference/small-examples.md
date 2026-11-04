# Executable Small Examples — Behavioral Checks for the Online Bin-Packing Definition Layer

Small hand-computable instances exercise Lean definitions (First Fit assignments by bin, volume, optimal bin count, and the optimal value for all-ones instances) and record the actual output; they serve as unit tests for the definition layer.

- Test file: `tests/reference/logs/Probe-full.lean` (positive-control content plus probe examples, compiled in the task app's lake environment with `lake env lean`; image `tcs-lean-base:5b3f719`, toolchain leanprover/lean4:v4.33.0-rc1).

## Design notes

- Kernel `decide` cannot compute over ℚ/ℝ (`Rat.normalize` uses well-founded recursion through `Nat.gcd`, which the kernel does not reduce; same finding recorded for the mirup task). All computable content uses an **ℕ-scaled shadow**: integer-scaled instance instFFN for instFFR at scale 41, the ℕ version of First Fit `ffAssignN` (comparisons over ℕ are kernel-computable), and `packsInNat` (ℕ feasibility, kernel-decidable). Bridge lemmas (`ffAssign_bridge` / `packsIn_of_packsInNat` / `valid_scaled`) connect the ℝ and ℕ layers.
- First Fit / Next Fit themselves are `noncomputable` (real comparisons use Classical) and cannot be evaluated with `#eval`. Behavior on concrete instances is computed through the ℕ shadow plus bridge lemmas; this is the only computation path (the restriction is also given to the task-solving model in `instruction.md`).
- Hand-computed expectations come from the literature (the worst-case First Fit instance in JDUGG 1974) and concept-ledger.

## Small-example table (; all passed)

| ID | Check | Hand-computed expectation | Actual result |
|---|---|---|---|
| E1 | `ffAssignN 41 instFFN` (First Fit assignment by bin) | Six items of size 6/41 share one bin; the 14/41 items pair up, using 3 bins; each of the six 21/41 items uses one bin | `#eval` outputs `[0,0,0,0,0,0,1,1,2,2,3,3,4,5,6,7,8,9]` ✓ (matches the hand calculation item by item) |
| E2 | `costOf (ffAssignN 41 instFFN)` = 10 | First Fit uses exactly 10 bins | `decide` passes ✓ |
| E3 | `instFFN.sum` = 246 | 6×6+6×14+6×21 = 246 | `decide` passes ✓ |
| E4 | `ValidInstance instFFR` | Every size lies in (0,1] (6/41, 14/41, and 21/41 are all < 1) | Compiles ✓ |
| E5 | `packsInNat instFFN 41 6` | A packing into 6 bins exists: bin j holds items {j, 6+j, 12+j} (6/41+14/41+21/41 = 41/41 exactly) | `fin_cases b <;> decide` passes ✓ |
| E6 | `PacksIn instFFR 6` | The E5 packing is feasible for the ℝ-scaled instance (by bridge lemma) | Compiles ✓ |
| E7 | `instFFR.sum` = 6 | Total volume is 246/41 = 6 exactly (so OPT ≥ 6) | Compiles ✓ |
| E8 | `optNumber instFFR` = 6 | Volume = 6 implies OPT ≥ 6; E6 implies OPT ≤ 6 | Compiles ✓ (this is the second half of c1) |
| E9 | `optNumber (ones k)` = k (k = 1, 5, 41) | Unit-size items cannot share a bin, so OPT equals the number of items | Compiles ✓ (all three cases) |
| E10 | `optNumber instFFR ≤ algCost firstFit instFFR` | Any feasible online-algorithm run is a packing, so OPT ≤ algorithm's bin count (6 ≤ 10) | Compiles ✓ |

## Issues found

- **`upload_dir` sync removes `.lake/build` under the sandbox's `/work`:** If a probe depends on a built `Task.olean`, run `lake build Task` in the same `sbx` command (first attempt with `import Task.Basic` reported unknown module for this reason).
- **Kernel `decide` fails on a target with free variables:** The per-bin check `fun b => by decide` in `instFF_pack` failed with “Expected type must not contain free variables.” Replacing it with `by fin_cases b <;> decide` (proving the six bins one by one) passes.
- **Domain inference for a standalone function lambda:** When `List.map fun n => ((n : ℝ) / (cap : ℕ))` is used as a standalone function, n is inferred as ℝ (inconsistent with the ℕ shadow). It is now written as `fun n : ℕ => ((n : ℝ) / (cap : ℕ))`. Where the instance type constrains it (e.g. the definition of instFFR), this annotation is optional; the elaborated form is the same.
