#!/usr/bin/env python3
"""Generate the Petersen-graph sanity certificate for tsp-gap-lean.

Instance: the Petersen graph on 10 vertices (unit edges), metric closure
(non-edges have distance 2). OPT_LP = 10 (x = 2/3 on every graph edge),
OPT_tour = 11 (Petersen is non-Hamiltonian), gap exactly 11/10.

Emits the certificate epilogue (below `-- END OF FIXED PART`) of
solution/Basic.lean on stdout; every certificate condition is verified in
Python before emission (these are the same checks the Lean `decide`s do).
"""
import sys

N = 10
BIG = 1000000

# Petersen graph: outer 5-cycle, inner 5-point star, matching spokes.
edges = ([(i, (i + 1) % 5) for i in range(5)] +
         [(5 + i, 5 + (i + 2) % 5) for i in range(5)] +
         [(i, 5 + i) for i in range(5)])
assert len(edges) == 15

# metric closure (diameter 2): cost 1 on edges, 2 on non-edges, 0 diagonal.
adj = [[False] * N for _ in range(N)]
for u, v in edges:
    adj[u][v] = adj[v][u] = True
cost = [[0 if i == j else (1 if adj[i][j] else 2) for j in range(N)] for i in range(N)]

# metric premise
for i in range(N):
    assert cost[i][i] == 0
    for j in range(N):
        assert cost[i][j] == cost[j][i]
        assert i == j or cost[i][j] > 0
        for k in range(N):
            assert cost[i][k] <= cost[i][j] + cost[j][k]

# LP certificate: y = 2 on every graph edge, D = 3 (x = 2/3).
D = 3
y = [[2 if adj[i][j] else 0 for j in range(N)] for i in range(N)]
for v in range(N):
    assert sum(y[v][u] for u in range(N)) == 2 * D, v
    assert y[v][v] == 0
    for u in range(N):
        assert y[u][v] == y[v][u] and y[u][v] <= D
full = (1 << N) - 1
for mask in range(1, full):
    cut = sum(y[u][v] for u in range(N) if (mask >> u) & 1
              for v in range(N) if not (mask >> v) & 1)
    assert cut >= 2 * D, mask
S = sum(cost[u][v] * y[u][v] for u in range(N) for v in range(N))
assert S == 60, S  # LP value = S / (2D) = 10

# Held-Karp DP potential table (exact values; BIG at unused states).
size = 1 << N
W = [[BIG] * N for _ in range(size)]
W[1][0] = 0
for mask in range(1, size):
    if not mask & 1:
        continue
    for j in range(1, N):
        if not (mask >> j) & 1:
            continue
        pm = mask ^ (1 << j)
        W[mask][j] = min(W[pm][i] + cost[i][j] for i in range(N) if (pm >> i) & 1)
T = min(W[full][j] + cost[j][0] for j in range(1, N))
assert T == 11, T

# potential inequalities (the Lean `pot_step` check, quantifier by quantifier)
for mask in range(size):
    if not mask & 1:
        continue
    for j in range(1, N):
        if not (mask >> j) & 1:
            continue
        for i in range(N):
            if i != j and (mask >> i) & 1:
                assert W[mask][j] <= W[mask ^ (1 << j)][i] + cost[i][j], (mask, j, i)
for j in range(1, N):
    assert T <= W[full][j] + cost[j][0], j
assert W[1][0] == 0

# gap arithmetic: alpha = 11/10, p * S <= q * (2 * (T * D))
assert 11 * S <= 10 * (2 * (T * D)) == 660 == 11 * S


def rows(M):
    return ",\n   ".join("[" + ", ".join(map(str, r)) + "]" for r in M)


print(f"""/-! ## Sanity certificate: the Petersen graph (n = 10, gap exactly 11/10)

Instance: the Petersen graph (outer 5-cycle, inner 5-point star, matching
spokes), metric closure: graph edges cost 1, non-edges cost 2. The LP point
`x = 2/3` on every graph edge is subtour-feasible (the Petersen graph is
3-edge-connected) with value 10; the exact Held-Karp potential table
certifies that every tour costs at least 11 (the Petersen graph is not
Hamiltonian). Hence `OPT_tour / OPT_LP >= 11/10`. -/

/-- Number of vertices: the Petersen graph. -/
def certN : ℕ := 10

instance : NeZero certN := ⟨by decide⟩

/-- Metric closure of the Petersen graph: 1 on edges, 2 on non-edges. -/
def certCostM : List (List ℕ) :=
  [{rows(cost)}]

/-- The cost function. -/
def certCost : Fin certN → Fin certN → ℕ := fun u v => matGet certCostM u.val v.val

/-- LP numerator: `2` on every Petersen edge (both directions). -/
def certYM : List (List ℕ) :=
  [{rows(y)}]

/-- The LP numerator as a function. -/
def certY : Fin certN → Fin certN → ℕ := fun u v => matGet certYM u.val v.val

/-- The LP denominator: `x = certY / 3 = 2/3` on the graph edges. -/
def certD : ℕ := 3

/-- Exact Held-Karp DP table (`1000000` = sentinel at unused states). -/
def certWM : List (List ℕ) :=
  [{rows(W)}]

/-- The potential table as a function. -/
def certW : ℕ → Fin certN → ℕ := fun mask j => matGet certWM mask j.val

/-- Certified tour lower bound (the Petersen graph is non-Hamiltonian). -/
def certT : ℕ := 11

/-- Claimed gap lower bound. -/
def claimedAlpha : ℚ := 11 / 10

/-- LP degree check: every row of `certY` sums to `2 * certD = 6`. -/
theorem lp_deg : ∀ v : Fin certN, ∑ u : Fin certN, certY v u = 2 * certD := by
  decide

/-- LP subtour-cut check: every proper nonempty cut carries at least
`2 * certD = 6` (the Petersen graph is 3-edge-connected). -/
theorem lp_subtour : ∀ mask : ℕ, mask < 2 ^ certN → mask ≠ 0 → mask ≠ 2 ^ certN - 1 →
    2 * certD ≤ ∑ u : Fin certN, ∑ v : Fin certN,
      if mask.testBit u.val ∧ ¬ mask.testBit v.val then certY u v else 0 := by
  decide

/-- The Held-Karp potential inequalities for `certW`. -/
theorem pot_step : ∀ mask : ℕ, mask < 2 ^ certN → mask.testBit 0 = true →
    ∀ j i : Fin certN, j ≠ 0 → i ≠ j → mask.testBit j.val = true →
      mask.testBit i.val = true →
      certW mask j ≤ certW (mask ^^^ (2 ^ j.val)) i + certCost i j := by
  decide

/-- Main theorem: the Petersen metric-closure instance has subtour-LP
integrality gap at least `11/10` (in fact exactly `11/10`). -/
theorem main : GapBound certN certCost claimedAlpha := by
  refine ⟨by decide, by decide, ⟨by decide, by decide, by decide, by decide⟩, ?_⟩
  exact gapLB_of_cert (by decide) certCost certW certY certD certT (by decide)
    claimedAlpha 11 10 (by decide) (by norm_num [claimedAlpha])
    (by decide) pot_step (by decide)
    (by decide) (by decide) (by decide) lp_deg lp_subtour (by decide)

end TSPGap""")
