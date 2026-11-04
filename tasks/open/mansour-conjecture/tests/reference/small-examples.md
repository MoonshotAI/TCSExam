# Executable Small Examples: Numerical Checks for the Mansour Definition Layer

Hand-computable DNF terms, formulas, and decision trees exercise the Lean definitions (integer numerator tables, Fourier-tail mass, and Parseval totals). Actual output from each run is recorded here.

- Lean probe: `Probe.lean`, compiled in the task app copy with `lake build Task` and then `lake env lean Probe.lean`; image `tcs-lean-base:5b3f719`, toolchain `leanprover/lean4:v4.33.0-rc1`.
- Independent recomputation: `tests/reference/fourier_small_examples.py` (output at `python-check.log`; `FAILURES: none`).

## Design notes

The denominator of f̂(S) is 2^n, so the integer numerator `fourierNum f S = Σ_x f(x)χ_S(x) = 2^n·f̂(S)` is an integer (for n = 3, the coefficient is numerator/8). Kernel `decide` does not reduce rational arithmetic (the first probe showed that even `(1:ℚ) + 1 = 2` does not reduce; `native_decide` is lexically banned by the task). Therefore, **kernel `decide` covers all numerical checks at the ℤ layer** (numerator tables, integer-form Parseval, complement identities, `lowDegree` membership, and pointwise function values), while **actual ℚ values are recorded with `#eval`** (native evaluation, not part of proofs). The theorem over ℚ is covered by the hand proof in checkpoint c2 (positive judging gate passed). Expected values come from Section 1 of `concept-ledger.md` and an independent Python recomputation.

## Small-example results (; all passed; PROBE_EXIT=0)

Integer-numerator table (E1–E5 are `decide` assertions quantified over every S; each passed):

| ID | Check | Hand-computed value (numerator = 2³ × coefficient) | Actual output |
|---|---|---|---|
| E1 | Numerator table for dictator term [x₀] | {0} ↦ 8 (coefficient 1); all others 0 | `decide` passed ✓ |
| E2 | Numerator table for negative literal [¬x₁] | {1} ↦ −8 (coefficient −1); all others 0 | `decide` passed ✓ |
| E3 | Numerator table for width-2 term [x₀x₁] | ∅ ↦ −4; {0}, {1}, {0,1} ↦ 4 (coefficients ∓1/2); all others 0 | `decide` passed ✓ |
| E4 | Sign for mixed term [x₀¬x₁] | ∅ ↦ −4; {0} ↦ 4; {1} ↦ −4; {0,1} ↦ −4 (sign = (−1)^{|S∩neg|}) | `decide` passed ✓ (four assertions) |
| E5 | Numerator table for selector (x₀x₁ ∨ ¬x₀x₂), first conjunct of c2 | {1}, {2}, {0,1} ↦ 4; {0,2} ↦ −4; all others 0 | `decide` passed ✓ |

Spectral properties and auxiliary facts:

| ID | Check | Hand-computed value | Actual output |
|---|---|---|---|
| E6 | Integer-form Parseval: sum of squared numerators (selector and one term) | 64 = 2^{2·3} (total mass of a ±1-valued function is 1) | `decide` passed ✓ (two assertions) |
| E7 | Pointwise characterization of the selector | “x₀ ? x₁ : x₂” (`dnfFunZ = if x 0 then pmOneZ (x 1) else pmOneZ (x 2)`) | `decide` passed ✓ |
| E8 | Spectrum of the depth-1 decision tree `node(0; leaf false, leaf true)` | Same as dictator; numerator 8 only at {0} | `decide` passed ✓ |
| E9 | `lowDegree` membership | {0,1} ∈ `lowDegree 2`; {0,1} ∉ `lowDegree 1`; ∅ ∈ `lowDegree 0` | `decide` passed ✓ (three assertions) |
| E10 | Complement identities used in c2 | `selectorSupportᶜ` = {∅, {0}, {1,2}, {0,1,2}}; complement of {{1},{2},{0,1}} = {∅, {0}, {0,2}, {1,2}, {0,1,2}} | `decide` passed ✓ (two assertions) |
| E11 | Pointwise test that a term is satisfied | ⟨{0,1}, ∅⟩ is satisfied when i ≠ 2 and not satisfied at the all-false input | `decide` passed ✓ (two assertions) |

Actual ℚ values recorded by `#eval` (native evaluation; each agrees with Python):

| Check | Expected | `#eval` output |
|---|---|---|
| f̂_selector({0,2}) | −1/2 | `-1 / 2` ✓ |
| f̂_selector({1}) | 1/2 | `1 / 2` ✓ |
| f̂_selector({0}), f̂_selector(∅) | 0, 0 | `0`, `0` ✓ |
| f̂_[x₀x₁](∅) | −1/2 | `-1 / 2` ✓ |
| Σ_S f̂_selector(S)² (total mass) | 1 | `1` ✓ |
| Tail mass outside `selectorSupport` (0-concentrated) | 0 | `0` ✓ |
| Tail mass outside {{1},{2},{0,1}} (1/4-concentrated) | 1/4 | `1 / 4` ✓ |

## Run record

- First pass established the boundary that rational arithmetic is not kernel-reduced: `∑ x : Fin 3 → Bool, (1:ℚ) = 8` and `∑ x ∈ {∅}, (1:ℚ) = 1` do not reduce (the same expressions over ℤ/ℕ do). The Pi-type universe (`Fin 3 → Bool`) is not the obstacle. Resolution: add an integer computation layer and cast bridge, and express numerical assertions using integer numerators.
- Second pass: all 16 `decide` theorems passed; the whole probe compiled in 6.9 seconds (including `import Task.Basic`). Log: `probe.log` (`PROBE_EXIT=0`). `#print axioms` for probeE1/E5/E6a/E10a listed only `[propext, Classical.choice, Quot.sound]`, confirming that kernel evaluation introduces no extra axioms such as `sorryAx` or `Lean.ofReduceBool`.
- Judging-chain check (partial-c2): the first conjunct was proved by direct `decide`; the two concentration conjuncts used “decide a complement identity + bridge + norm_num.” The actual `score.py` judged it PASS; log: `partial-c2.log`.
- Independent Python recomputation (`tests/reference/fourier_small_examples.py`): complete numerator tables for four terms, the selector table plus two concentration facts, and the full table for a depth-1 decision tree all passed (log `logs/python-check.log`, exit 0).

## Issues found

- **Kernel evaluation does not reduce `Rat` arithmetic:** see Design notes. This is the largest engineering difference from the Tuza task (where all numerical checks are propositions over ℕ/Finset and `decide` works directly). Resolution: add the ℤ layer and bridge lemma to the fixed prefix, and state c2's coefficient table as integer numerators.
- **`rw [if_pos h]` changes only the first match:** during development, the rewrite metavariable was fixed by the first match, so a second `if` with the same condition was not rewritten. Resolve it by rewriting each `if` separately; all proof scripts now use this form.
- **The concentrated part of c2 does not rely on c2's table:** its two concentration conjuncts need only “every coefficient in the complement is 0 or ±1/2” (obtained from the integer table via the bridge lemma and a cast); `norm_num` completes the sum of squares. No undecidable rational evaluation is involved.
