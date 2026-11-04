# Executable Small Examples: Checking the KRW Composition Definition Layer

Small, hand-checkable Boolean functions are used to exercise the Lean definitions: numeric `depthOf`, formula evaluation, bounded-depth enumeration, and block-composition evaluation. The actual output of each run is recorded below.

- Probe: `Probe.lean`, compiled in the task app copy using `lake env lean Probe.lean`; a Lean validation image, Lean 4.33.0, mathlib pinned at 5b3f719.

## Design notes

`depthOf` itself (defined by `sInf`) is not computable. Exact depths on small instances are established by combining an explicit formula for the upper bound (`depthOf_le`) with bounded enumeration that rules out smaller formulas for the lower bound (`le_depthOf`). The lower-bound search uses kernel `decide` (`native_decide` is lexically banned by the task). Hand-computed expected values come from the first section of `concept-ledger.md`.

**Empirical lesson about exhaustive-search structure (basis for the fixed prefix):** Naively checking `∀ ψ ∈ upTo 1, ¬ Computes ψ (blockComp and2 and2)` on four variables (2×2 blocks) made `decide`'s elaboration normalize the 16-element function universe anew for each formula. It exhausted all three heartbeat budgets: 200k (default), 800k, and 3,200k (at 3.2 million, about six minutes, it still had not completed). The fix was to define `assignments4` as an explicit list of all 16 assignments and prove its completeness `mem_assignments4` once using `decide`, plus a bridge lemma `not_computes_of_exhaust` that checks all formulas against the shared list in one flat computation. The same assertion then completed in seconds within the default heartbeat budget (the whole probe took 38 seconds, including mathlib loading). Naive exhaustive search over two variables (40 formulas × 4 assignments) is already cheap, so it remains in that form. The fixed prefix uses `set_option maxRecDepth 8192` and `set_option maxHeartbeats 800000` as a safety margin; judging variants inherit these settings.

## Small-example results (; all passed, PROBE_EXIT=0)

| ID | Check | Hand-computed result | Actual output |
|---|---|---|---|
| E1 | Evaluation of literals/constants (3 cases) | `lit 0 true` reads x₀; `lit 1 false` reads ¬x₁; `const true` is always true | `decide` passed ✓ |
| E2 | Evaluation and depth of the dual (2 cases) | `dual (x₀ ∧ ¬x₁)` computes ¬(x₀∧¬x₁), with depth still 1 | `decide` passed ✓ |
| E3 | `depthOf` for a projection, a constant, and `or₂` (3 cases) | Projection = 0 (single literal); constant = 0 (constant leaf); `or₂` = 1 | Upper-bound API plus exhaustive lower bound passed ✓ |
| E4 | Checkpoint values (3 cases) | D(`xor₂`) = 2; D(`and₂`) = 1; D(`and₂⋄and₂`) = 2 | Proofs of the same form as c1/c3 passed ✓ (c3 lower bound uses the bridge lemma). |
| E5 | Assemble the trivial direction (same form as c2) | For any f,g: D(f⋄g) ≤ D(f)+D(g) | API assembly passed ✓ |
| E6 | Enumeration sizes | `upTo 0` (2 variables) has 6 formulas; `upTo 1` (2 variables) has 78 | `decide` passed ✓ |
| E7 | Decidability of nonconstancy (3 cases) | `NonConst xor₂` holds; it fails for a constant function and for a constant function on zero variables | `decide` passed ✓ (`NonConst` is an abbreviation, so the instance synthesizes). |
| E8 | Block-composition evaluation (2 cases) | `and₂⋄and₂` is four-variable conjunction; `xor₂⋄xor₂` is four-variable parity | `decide` passed ✓ (all 16 assignments). |

## Run record

- First pass: five rounds of fixes were needed to compile the definition layer (grouping the disjunction, grouping rcases patterns, making `Finset.toList` noncomputable, `!v =` precedence, and both true/false substitution patterns). The sixth pass reported “Build completed successfully (8691 jobs)” with exactly the 5 expected `sorry` warnings.
- Exhaustive-search heartbeat issue: see the empirical lesson above. The naive four-variable search exhausted 200k/800k/3,200k heartbeats in separate measured runs (logs in the corresponding run outputs under `krw-open-2026-09-05`). After adding the bridge, the probe passed (`probe.log`, PROBE_EXIT=0, 38 seconds for the full file).
- Judging chain: checkpoint proof bodies had the same form as the probe and passed all three positive controls through the actual `score.py` (3/3 PASS; `logs/positive.log`, 35 seconds).

## Issues found

- **Naive enumeration of function types does not scale under kernel evaluation:** the decidable instance for `∀ x : ι → Bool` rebuilds the function universe for every candidate formula; four variables already exceed any reasonable heartbeat budget. Resolution: add an explicit assignment list and bridge lemma to the fixed prefix, changing “enumerate the function type once per formula” into one flat computation over all formulas and a shared list. Task documents and `instruction.md` point to this API.
- **`Finset.all` is absent in the current mathlib:** the exhaustive-search premise was changed to the decidable form `∀ ψ ∈ upTo d, (L.all …) = false` (`List.all` is available).
- **A `def`-based `NonConst` does not synthesize a decidability instance** (instance search does not unfold the definition); changing it to an `abbrev` makes E7 pass.
- **Axiom cleanliness of kernel `decide`:** the lower-bound proofs in E3/E4 were checked against the judging-chain `#print axioms` whitelist using positive controls (all three checkpoints passed). Kernel evaluation introduces no additional axioms such as `Lean.ofReduceBool`.
