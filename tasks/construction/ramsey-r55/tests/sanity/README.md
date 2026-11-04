# Sanity fixture — ramsey-r55-lean

This fixture is a small submission that the judge should accept for full credit (N=13 ≤ 30), used to check the scoring path.

`Basic.lean` is a complete submission: the fixed layer plus the Paley coloring of K₁₃ (edge {i,j} is red iff (j−i) mod 13 ∈ {1,3,4,9,10,12}; this set of nonzero quadratic residues is closed under negation, so the coloring is symmetric. The Paley graph of order 13 is self-complementary and has clique number 3, so neither color contains K5). `submission_lower` is proved with `by decide`; `submission_upper` is left with `sorry` to check that leaving one side incomplete does not affect the other.

Expected result (default `alpha_milestone` mode): reward = 1.0, `submission_lower` milestone = verified; `#print axioms` contains only [propext, Classical.choice, Quot.sound]. Local compilation and checking took about 80 seconds (within the verifier's 1800-second budget).
