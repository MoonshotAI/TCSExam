# small-examples — lean-quantum-crypto-algorithmica (executable small examples)

This page reports 15 small-example checks (E1–E15) that reimplement the task's definition layer in pure Python and test the behavior of the statement predicates and all threshold arithmetic.

The script is `small_examples.py`.

## Results by check

each row states the checked claim and its outcome.

| ID | Check | Result |
|---|---|---|
| E1 | Bias from Definition 8: bias = trnc(√(ε2ⁿ)f̂(x)), |bias| ≤ 1, and E[g(x)\|f] = bias (enumerate all x for random f at n=1,2,3) | Passed |
| E2 | First branch of c2: `forrExp = 2^{−N}∑_f C(f, bias_f)` (n=1,2; random multilinear C; exhaustive comparison; error < 1e-9) | Passed |
| E3 | Second branch of c2: `unifExp = C(0⃗)` (exhaustive over random C at n=1,2) | Passed |
| E4 | c1: `|C(z)−C(z′)| ≤ 2N·‖z−z′‖_∞` (random points in the cube, n=1,2) | Passed |
| E5 | Values ±1 at vertices imply `|C| ≤ 1` inside the cube (predicate behavior of `abs_mlEval_le_one`, including strict interior points) | Passed |
| E6 | Restriction identity for c3: under the explicit product distribution (freeze +1 with probability (1−δ_i+v_i)/2, freeze −1 with probability (1−δ_i−v_i)/2, retain with probability δ_i), check `f(v+δ⊙z)−f(v) = E_ρ[f_ρ(z)−f_ρ(0⃗)]` pointwise for random v/δ/z, including z outside the cube and boundary cases `\|v_i\|=1` | Passed |
| E7 | Polarization for c4: under both driving distributions (uniform on [−1,1] and ±1/2), simulated `E[B_m²] > 1−3e^{−mp/16}` (m=60, 4000 trials) | Passed |
| E8 | Bad-probability arithmetic in Claim 11: `2N e^{−1/(2ε)} + 2N e^{−1/(8ε²)} + 2N e^{−1/(8ε)} ≤ 1/N^{10}` holds for n=1..29 (so the n ≥ 1 assumption in c5 is nonvacuous and sufficient) | Passed |
| E9 | Threshold in Claim 12: `3e^{−mε/32} ≤ N⁻⁶` iff n ≥ 7 (ratio ≈ 1.09 at n=6, confirming the c6 assumption cannot be removed); packaged truncated second moment `≤ 1/N⁵⁰ ≤ ε/2` for n=1..24 | Passed |
| E10 | Constants in Claim 13: `m ≤ N⁸` iff n ≥ 2 (the c7 assumption); variance/covariance conditions for δ = ε/√N hold for n ≥ 1; assembled `Pr[¬ℰ] ≤ m/N^{10} + 1/N² + 2m/N² ≤ 1/N` holds starting at **n = 24** | Passed |
| E11 | Simulate the walk with the full Gaussian steps XLe/YLe: frequency of the Claim 11 event (`Y = √εHX` and `Y ∈ [−1/2,1/2]^N`) and polarization event—n=1: 120/120 and 120/120 (m=13863); n=2: 120/120 and 120/120 (m=55452), each at least the claimed rate | Passed |
| E12 | `∑_g forrWt = 1` (the component of the trivial c8 bound `|LHS| ≤ 2`) | Passed |
| E13 | Numerical integration of the two `gaussianTailProp` inequalities (`v ∈ {0.01,0.1,1,3}` × `t ∈ {0,0.5,1,2.5}`): both the tail bound and truncated second-moment bound are valid upper bounds | Passed |
| E14 | `√ε·(Hf)(x) = √(ε2ⁿ)·f̂(x)` (identification identity for c8, n=1,2,3) | Passed |
| E15 | `m·ε ∈ [200 ln N, 200 ln N + ε]` (ceiling-shaped step count; assembled telescoping constant `mε = 200 ln N + O(ε)`) | Passed |

## How the checks informed the design

- E9 confirms the `7 ≤ n` assumption for c6 cannot be removed (`3e^{−mε/32} > N⁻⁶` at n=6); E10 confirms the `2 ≤ n` assumption for c7 cannot be removed (`m > N^8` at n=1). Both assumptions were added to the statements to match the range where the proofs work.
- E10 gives the assembly threshold n₀ = 24. The main theorem's ∃K argument only needs to absorb the finitely many cases n < 24 (for each, `ln N/√N` has a positive lower bound).
- The boundary case in E6 confirms that the c3 identity remains valid when using the closed interval, as required in the application of Claim 13.
- No statement errors were found.
