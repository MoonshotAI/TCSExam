# Sanity fixture — cage-girth-lean-open

This fixture is a small submission that the judge should accept but score 0 (the (3,5) cage, the Petersen graph), used to check the scoring path.

`Basic.lean` is a complete submission: the fixed layer plus a witness for the Petersen graph (Kneser graph K(5,2): vertices are the 2-element subsets of {0..4}, encoded by 5-bit masks; adjacent vertices are disjoint; n(3,5) = 10 is the only scoring cell with an exact known value). `submission_lower` proves the claim for the cell (3,5), N=10, using `native_decide`.

Expected result: reward = 0.0, valid = 1, `submission_lower` milestone = "sanity" (the (3,5) cell is closed and always scores 0). `#print axioms` contains only `propext` and the `native_decide` trusted axiom (`._native.native_decide.ax_*` form, allowed by the scoring template). A sandbox smoke run with the same stage1 toolchain compiled and checked it in seconds.
