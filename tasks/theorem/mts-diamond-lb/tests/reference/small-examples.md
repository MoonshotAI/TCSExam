# Small examples — lean-mts-diamond-lb

This record gives a Python implementation of the construction in section 3 of BCR23 and its numerical checks (one of the three L2 fidelity checks).

- Script: `small_examples.py` (pure Python + exact `Fraction` arithmetic). E1–E9 below are the matching checks in the script.

## Scope of the implementation

The script mirrors the Lean definition layer: the point set in the diamond family (represented by `Fin (6·m_w) × {x ≠ t}`), the `cdist` distance formula, the reversing involution `swapW`, the copy embedding (`rightEmb = copyEmb ∘ swapW`), the three-stage difficult random request sequence (including `{t}` padding to `T_{w+1} = 4·m_w·T_w`), the optimal offline cost by position-based dynamic programming, and a concrete online algorithm (greedy). For the graph-side comparison, it computes all-pairs shortest paths with Floyd–Warshall on the graph formed by the construction's gluing.

## Checklist and results

each row gives a check and the instance sizes covered.

| Check | Claim | Coverage and result |
|---|---|---|
| E1 | `cdist` formula equals the shortest-path metric of the glued graph | For m-sequences {1,1,1}/{2,1,1}/{1,2,1} and w ∈ {1,2}, exhaustive agreement for every pair of vertices. |
| E2 | Diameter recurrence `DD(w+1) = 3·m_w·DD(w)` and antipodal property (`diam = d(s,t)`) | Same parameter families as above, w ∈ {1,2}; maximum distance over all pairs is exactly DD. |
| E3 | Point-count recurrence `card = 6m_w·(card−1)` and geodesic property `d(x,s)+d(x,t) ≤ DD` | All points checked for w ≤ 3 (up to 180 points in M₃). |
| E4 | Copy embedding `copyEmb` is isometric | w = 1; all pairs among copy 0/1/L−1. |
| E5 | Structure of the difficult sequence: length = T_w, first request is {s}, last is {t}, and every request set is nonempty | All samples at w ∈ {1,2} (|Ω₁| = 2, |Ω₂| = 32). |
| E6 | `c_opt(ρ_w(ω)) = DD_w` for every realization | All samples as above; the optimum is computed exactly by positional DP. |
| E7 | Sanity check for the direction of the stage lower bound: measured stage expected cost of greedy ≥ the lower bound | w = 1: E[stage 1] = 1 ≥ m₀C₀D₀ = 1; E[stage 2] = 0.5 ≥ 0.5; E[stage 3] = 3.5 ≥ 1.75; total 5 ≥ C₁·DD₁ = 3.25. |
| E8 | Closed form for binomial deviation, `E\|S_m − m/2\| = m·C(m−1,⌊(m−1)/2⌋)/2^m`, and it is ≥ √m/4 | Checked exactly for each m = 1..60. |
| E9 | Recurrence values: `C_w` lies in `[w²/2592, (1+w/24)²]`; `log₂\|M_w\| ≤ 2w·log₂w` for w ≥ 48 | All w ≤ 200 passed (`C_200 = 82.3`, `log₂\|M_200\| = 1370.3 ≤ 3057.5`). |

## Development notes: issues caught by the small examples

1. **Wrong orientation of the right path in the first version**: the initial `rightEmb` did not apply the reversing `swapW`. The first request in E5 was not {s}, and E6 computed an optimum of 15 > DD = 9 on one w=2 sample. The orientation was reversed, so preserving the surviving path required the copy to fold back. This confirms that the paper's (S,S′,i,j) notation implicitly orients the right-path copy's own s toward the global s, and fixes the correct form `rightEmb = copyEmb ∘ swapW`. The endpoint swap, involution, and isometry properties of `swapW` were also checked numerically with no violations.
2. The first E7 version used the wrong layer length when slicing the stages (confusing T_w with T_{w−1}). After correction, measurements match the lower-bound accounting exactly; stage 2 attains the lower bound 0.5, so greedy is tight at that scale.

## Conclusion

The definition-layer distance formula, construction, request sequence, characterization of the optimum, and recurrence constants agree numerically on hundreds of small instances. The predicate behavior in the test points (E5/E6/E7 directly execute the object-level semantics of c2/c3/c4/c6) also matches the claims in the paper.
