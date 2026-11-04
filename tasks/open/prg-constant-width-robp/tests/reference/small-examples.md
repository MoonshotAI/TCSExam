# Executable Small Examples — Behavioral Checks for the Constant-Width ROBP PRG Definition Layer

Small, hand-checkable programs, generators, and Turing machines exercise Lean definitions (acceptance probability, fooling value, exhaustive optimal error, TM execution) and record each run's actual output. These examples serve as unit tests for the definition layer.

- Test artifacts: probes `Probe.lean`/`Probe3.lean`/`Probe5.lean`/`Probe6.lean` (compiled inside a copy of the task app with `lake env lean`, using a Lean validation image, toolchain v4.33.0, and mathlib pinned at 5b3f719); exhaustive-search script `bruteforce_c3.py` (pure Python, run locally).

## Design notes

- Probability-value layer: `acceptProb`/`fooledProb` are exact rational values in ℚ (counts divided by powers of 2). **The kernel cannot evaluate ℚ** (`Rat.normalize` uses well-founded recursion through `Nat.gcd`; even `decide` on the literal rational equation `(8:ℚ)/16 = 1/2` stalls; observed in Probe4a). Therefore numerical claims use two steps: the kernel decides the natural-number counts (`acceptCount`/`fooledCount`), then `norm_num` closes rational equalities (checkpoint c2). For the fooling relation `Fools`, a proved cross-multiplication bridge `fools_iff` in the pinned zone converts it to one integer inequality, which the kernel can decide (checkpoint c3; integer comparisons are kernel-decidable, and Probe5 passed).
- Enumeration layer: inputs and seeds are enumerated as flat `List`s through bit encoding `inputOf` (bit i of j); width-2, length-3 transition functions are enumerated through the 12-bit index `tableOf`. Directly enumerating a three-level nested function type (`Fin 3 → Fin 2 → Bool → Fin 2`) via `Finset.univ` stalls in kernel quotient lifting through `Multiset.Pi` (observed in the initial Probe6). `Fin 4 → Bool` (16 elements, one level) works—the scale/nesting boundary lies between these forms, so all enumeration was switched to bit encoding.
- Recursion depth: the pinned zone sets `set_option maxRecDepth 8192` (kernel evaluation for c2/c3 passes at this depth, confirmed). Kernel expansion cost for universal enumeration grows with the number of programs (512 programs take seconds; 4096 programs were killed after 20+ minutes); this determined the scale choice (see run log).

## Small-example table (; all entries use kernel `decide` unless otherwise stated)

| ID | Check | Hand-computed expectation | Actual result |
|---|---|---|---|
| E1 | `parityROBP.run` on two concrete inputs | Even/odd parity ends in states 0/1, respectively | `decide` passes ✓ (Probe3 D1) |
| E2 | `parityROBP.acceptCount` | 8 (8 of 16 inputs have odd Hamming weight) | `decide` = 8 ✓ (Probe3 D2); `#eval` gives the same value |
| E3 | Directly written filter version of the same count | 8 | `decide` passes ✓ (Probe3 D3, earlier Finset version) |
| E4 | Integer cross-multiplication form for `parity3` (length-3 parity program) | (4·(3·8−4·4) ≤ 32)∧(4·(4·4−3·8) ≤ 32), which holds | `decide` passes ✓ (Probe5 I5) |
| E5 | Output table of `andGen` | 00↦000,01↦001,10↦100,11↦111 | `decide` passes ✓ (Probe P4) |
| E6 | Full c3: `∀ k < 64, ∀ start : Fin 2, ∀ acc < 4, Fools quarter (⟨tableOfPerm k, start, fun s => acc.testBit s.val⟩) andGen` | True (maximum over permutation ROBPs is exactly 1/4; see Python record below) | `decide` passes ✓; default heartbeats + pinned maxRecDepth 8192; whole file 12.9 seconds (Probe15a/15b/15c) |
| E7 | TM pipeline: `readY0` machine on (n=4, seed [t,f,t,f], i=0) | Reads true (passes four unary 1s and a blank, then stops at the first seed bit) | `decide` passes ✓ (Probe P7); with seed [f,..], reads false ✓ |
| E8 | TM pipeline: `readY2` machine (fixed-length index) on two seeds | Reads both true and false values of y_2 | `decide` passes ✓ (Probe P8) |
| E9 | Proposition form `TM.ComputesBit` (with probe-side Decidable instance) | Same as E7 | `decide` passes ✓ (Probe3 D8) |
| E10 | Exhaustion: give `readY2` only 3 steps of fuel | `run` returns `none` (machine has not halted) | `decide` passes ✓ (Probe P8) |
| E11 | `fooledProb_id` is `rfl` | The identity generator's fooling probability is definitionally equal to the uniform acceptance probability | `rfl` passes ✓ (Probe P1) |
| E12 | c1 form: `∀ B, B.Fools 0 id` | One-line `simp` using `fooledProb_id` | Pass ✓ (Probe P2 / Probe6 R1) |
| E13 | c2 form: `parityROBP.acceptProb = 1/2` | `decide` the count (= 8), then close with `norm_num` | Pass ✓ (Probe6 R2) |

## Python exhaustive-search record

Full class (reference data; c3 does not use this class size):

- There are 2^12×2×4 = 32768 standard-order ROBPs of width 2 and length 3, but they realize only **88 distinct acceptance masks** among the 256 subsets of {0,1}³.
- For all multisets of 4 seed generators (330 total), the maximum distinguishing-gap distribution is: 1/4 for 24, 3/8 for 24, 1/2 for 178, 5/8 for 48, 3/4 for 48, and 7/8 for 8 (constant generators are worst).
- **The optimal error over the full class with 2-bit seeds is exactly 1/4.** `andGen (a,b) = (a, a∧b, b)` (outputs 000/001/100/111) is one of the 24 optimal generators with a closed-form expression.

Permutation subclass (used for c3):

- There are 2^6×2×4 = 512 width-2, length-3 permutation ROBPs (each bit's transition at each layer is either identity or swap).
- **The maximum gap of `andGen` over this class is exactly 1/4** (`bruteforce_c3_perm.py`); 128 programs attain 1/4. The length-3 parity program (each bit is either swapped or kept, start state 0, accept set {1}) is among them: true value 1/2 and fooling value 3/4.

## Issues found

- **The kernel cannot evaluate ℚ:** see design notes. Resolution: use the ℤ bridge and the two-step count/rational procedure. The grading variant inherits the same pinned zone and behaves consistently.
- **Kernel stalls when enumerating nested function types via `Finset.univ`:** three nesting levels (2^12 elements) do not reduce. Resolution: enumerate by bit encoding (`inputOf`/`tableOf`); the bijection argument is recorded in concept-ledger.
- **Exhaustive-search depth grows with scale:** default depth 8192 is insufficient for the full c3 enumeration. Resolution: pin the depth in the common zone and ship it with the task file (value above); the grading variant inherits it from the same source.
