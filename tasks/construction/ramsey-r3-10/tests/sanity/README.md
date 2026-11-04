# Sanity fixture — ramsey-r3-10-lean

This fixture is a small submission that the judge should accept (N=18 ≤ 35, below the scoring baseline), used to check the scoring path.

`Basic.lean` is a complete submission: the fixed layer plus a coloring of the cycle C₁₈ (edge {i,j} is red iff (i−j) mod 18 ∈ {1,17}; the red graph is exactly the 18-cycle, so its girth is 18 and it has no triangle. Its independence number is ⌊18/2⌋ = 9, so there is no all-blue set of 10 vertices). `submission_lower` is proved by `by native_decide`; `submission_upper` is left with `sorry` to check that leaving one side incomplete does not affect the other.

Expected result (default `solver_cubic` mode): reward = 0.0 (N=18 ≤ 35 is below baseline, milestone = baseline), valid = 1, `submission_lower` status = proven, and N=18 is parsed correctly. `#print axioms` is within the allowlist [propext, Classical.choice, Quot.sound, Lean.ofReduceBool, Lean.trustCompiler]. Since this task allows `native_decide`, this fixture also checks that the `native_decide` path works. The same construction, converted to a sibling JSON certificate, is also valid=1 and reward=0 under the Solver checker (same score in both versions; see `../reference/CONCEPTS.md`).
