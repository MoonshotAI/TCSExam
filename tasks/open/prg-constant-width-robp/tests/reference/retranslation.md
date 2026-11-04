# Independent Retranslation: PRGs for Width-4 Constant-Width ROBPs

This record derives a formalization draft independently from the literature statement without consulting the shipped Lean file, then compares the two component by component. It is the third fidelity record (independent retranslation).

- Source statement: item 2 in `pseudorandomness-explicit-constructions.md`, consistent with standard formulations by Nisan (1992), BRRY (2010), and Forbes–Kelley (2018).
- Method: first refine the statement in natural language, then draft its types, and finally compare with the shipped version.

## Step 1: Source statement (from the survey)

For some constant width w ≥ 4, construct an explicit PRG that fools every standard ordered ROBP of width w and length n with error 1/n and seed length o(log² n). The ultimate goal is seed length O(log(n/ε)), which in the constant-width setting would imply BPL = L.

## Step 2: Natural-language refinement (resolving ambiguities)

- **Standard ordered ROBP (width w, length n):** a directed graph with n+1 layers numbered 0 through n; each layer has at most w nodes; layer 0 has a single start node; every node in layer i (0 ≤ i < n) has two outgoing edges labeled 0 and 1, each leading to a node in layer i+1; layer i reads input bit x_i; the final layer is partitioned into accepting and rejecting nodes. On input x ∈ {0,1}ⁿ, start at the initial node, follow the edge labeled x_i at layer i, then accept or reject according to the reached node in the final layer.
- **Acceptance probability:** the fraction (finite count) of uniform random x ∈ {0,1}ⁿ that are accepted.
- **PRG with seed length s:** a function G : {0,1}ˢ → {0,1}ⁿ. G ε-fools a program B if |Pr_y[B(G(y)) accepts] − Pr_x[B(x) accepts]| ≤ ε, where y is uniform in {0,1}ˢ.
- **Explicit:** there is an algorithm which, given (n, y, i) with n in unary, outputs bit i of G(y) in poly(n) time. “Explicit” cannot be omitted: without it, a counting argument makes the claim immediately true (a random G with seed length O(log(n/ε)) has positive probability of fooling every width-w program; at ε = 1/n the seed is O(log n), which is of course o(log²n)).
- **Seed length o(log²n):** s(n)/log²n → 0 as n → ∞.
- **Conjecture:** there is a generator family satisfying the three requirements above. Set w = 4, the first completely open width; width 2 is optimally solved by small-bias spaces, while the MRT seed for width 3 is still Õ(log²n) at ε = 1/n.

## Step 3: Independently drafted types

```
ROBP n w := structure { step : Fin n → Fin w → Bool → Fin w; start : Fin w; accept : Fin w → Bool }
  -- Normalize ≤ w to exactly w states (unreachable dummy states).
run B x := start at B.start, then iterate step i currentState (x i) for i = 0..n-1
acceptProb B : ℚ := #{x | accept (run B x)} / 2^n
fooledProb B G : ℚ := #{y | accept (run B (G y))} / 2^s
Fools B ε G := |fooledProb B G − acceptProb B| ≤ ε
Explicit layer: single-tape TM (alphabet includes blank), ComputesBit M input fuel b := M halts within fuel and the cell under its head contains b
encode(n, y, i) := 1^n ␣ y ␣ 1^i
Explicit s G := ∃ M, ∃ c k, ∀ n ≥ 1, ∀ y, ∀ i, ComputesBit M (encode(n,y,i)) (k·n^c) ((G n y) i)
Conjecture := ∃ s : ℕ → ℕ, ∃ G : ∀ n, (Fin (s n) → Bool) → (Fin n → Bool),
  Explicit s G ∧ (∀ n ≥ 1, ∀ B : ROBP n 4, Fools B (1/n) (G n)) ∧ (fun n => s n / (log n)²) → 0
```

## Step 4: Component-by-component comparison with the shipped version

| Component | Draft | Shipped version | Finding |
|---|---|---|---|
| ROBP | Isomorphic structure with exactly w states | `structure ROBP n w`, same form | Match |
| Path traversal | Iterated `step` | `B.run` (`List.foldl` over `List.finRange n`) | Match (same iteration order: layer 0 first) |
| Acceptance probability | Count divided by 2ⁿ, over ℚ | `B.acceptCount` / `B.acceptProb : ℚ` | Match |
| Fooling | Absolute difference ≤ ε | `B.Fools ε G`, same form | Match |
| Explicitness | Single-tape TM + unary encoding + k·n^c steps + output one bit | `TM` / `ComputesBit` / `encodeInput` / `Explicit`, isomorphic | Match |
| Seed asymptotics | s/(log n)² → 0 | `Filter.Tendsto ... Filter.atTop (nhds 0)` over ℝ | Match |
| Conjecture | Existence of a family plus three conjuncts, width 4 | `conj` (`refuted` is its negation) | Match |

There are no disagreements. The semantic justifications for normalization (exactly w states, exact rational probabilities, all n ≥ 1, and the single-tape TM model) are in deviations 1/2/3/5/6 of `concept-ledger.md`.

## Notes

- The single-tape TM is a minimal concrete interpretation of the literature's “explicit.” Switching to another model, such as a multitape machine, would not change the statement up to polynomial factors.
