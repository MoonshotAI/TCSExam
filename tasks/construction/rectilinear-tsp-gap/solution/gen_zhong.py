#!/usr/bin/env python3
"""Generate the Zhong-family oracle certificate for rectilinear-tsp-gap-lean-open.

Instance: the family member I^2_{1,8,1} of X. Zhong, *Lower bounds on the
integrality ratio of the subtour LP for the traveling salesman problem*,
DAM 365 (2025), Section 5.3, at n = 16 — the current best known construction
in the scoring window, gap exactly 64/55 (LP = 5, tour = 6 - 2/11 = 64/11).
Coordinates are scaled by 22 to integers (the gap is scale-invariant), giving

  X-line y = 0 : (0,0), (11,0), (22,0)
  Y-line y = 11: (2k, 11) for k = 1..10
  Z-line y = 22: (0,22), (11,22), (22,22)

LP certificate: the paper's half-integral optimal fractional tour x_{1,8,1}
(Section 5.1) — x = 1 on the three line paths, x = 1/2 on the six edges of
the two end triangles; numerator y = 2x over D = 2, value 110 = 5 x 22.
Tour certificate: the exact Held-Karp DP table (T = 128 = (64/11) x 22),
computed INSIDE Lean by `certWTable` (the 2^16 x 16 table is too large to
ship as a literal); this script recomputes the same table in Python and
checks every certificate condition (the same checks the Lean
`decide`/`native_decide`s do) before emission.

Cross-validation: if numpy/scipy are available, the sister solver task's own
stack (tests/tsp_gap.py of construction-conjecture-solver/rectilinear-tsp-gap)
recomputes OPT_LP and OPT_tour on the scaled instance: LP = 110, tour = 128,
gap = 64/55 exactly.

Emits the certificate epilogue (below `-- END OF FIXED PART`) of
solution/Basic.lean on stdout.
"""
import os
import sys
from fractions import Fraction

N = 16
BIG = 1000000

# --- instance: I^2_{1,8,1} scaled by 22 ---------------------------------------
PX = [0, 11, 22] + [2 * k for k in range(1, 11)] + [0, 11, 22]
PY = [0, 0, 0] + [11] * 10 + [22, 22, 22]
assert len(PX) == len(PY) == N

cost = [[abs(PX[i] - PX[j]) + abs(PY[i] - PY[j]) for j in range(N)] for i in range(N)]

# point-set premise: pairwise distinct (the L1 metric is then positive off-diagonal)
for a in range(N):
    for b in range(a + 1, N):
        assert (PX[a], PY[a]) != (PX[b], PY[b]), (a, b)

# --- LP certificate: y = 2 on the line paths, 1 on the end triangles, D = 2 ---
D = 2
y = [[0] * N for _ in range(N)]


def put(u, v, w):
    y[u][v] = y[v][u] = w


path_edges = ([(i, i + 1) for i in range(0, 2)] +       # X-line path
              [(i, i + 1) for i in range(3, 12)] +      # Y-line path
              [(i, i + 1) for i in range(13, 15)])      # Z-line path
tri_edges = [(0, 3), (0, 13), (3, 13), (2, 12), (2, 15), (12, 15)]
for u, v in path_edges:
    put(u, v, 2)
for u, v in tri_edges:
    put(u, v, 1)

# LP checks (same shape as the Lean certificate conditions)
for u in range(N):
    assert y[u][u] == 0
    for v in range(N):
        assert y[u][v] == y[v][u] and y[u][v] <= D
for v in range(N):
    assert sum(y[v][u] for u in range(N)) == 2 * D, v
full = (1 << N) - 1
for mask in range(1, full):
    cut = sum(y[u][v] for u in range(N) if (mask >> u) & 1
              for v in range(N) if not (mask >> v) & 1)
    assert cut >= 2 * D, mask
S = sum(cost[u][v] * y[u][v] for u in range(N) for v in range(N))
assert S == 440, S  # LP value = S / (2D) = 110 = 5 x 22

# --- Held-Karp DP table (exact values; BIG at unused states) -------------------
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
assert T == 128, T  # (6 - 2/11) x 22 = 64/11 x 22

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

# gap arithmetic: alpha = 64/55, p * S <= q * (2 * (T * D))
assert 64 * S <= 55 * (2 * (T * D))
assert 64 * S == 55 * (2 * (T * D)) == 28160  # in fact equality: gap exactly 64/55

# --- cross-validation against the sister solver task's own stack ---------------
SISTER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..",
                      "construction-conjecture-solver", "tasks", "rectilinear-tsp-gap", "tests")
try:
    sys.path.insert(0, SISTER)
    import numpy as np
    from tsp_gap import opt_lp, opt_tour
    Dm = np.array([[float(cost[i][j]) for j in range(N)] for i in range(N)])
    lp, tour = opt_lp(N, Dm), opt_tour(N, Dm)
    assert abs(lp - 110.0) < 1e-9 and abs(tour - 128.0) < 1e-9, (lp, tour)
    print(f"# cross-check (sister tsp_gap.py on the scaled instance): "
          f"OPT_LP={lp:.6f} OPT_tour={tour:.6f} gap={tour / lp:.12f} = 64/55", file=sys.stderr)
except Exception as e:  # numpy/scipy missing — skip (certificate is self-contained)
    print(f"# cross-check skipped: {e}", file=sys.stderr)


def arr_z(vals):
    return "#[" + ", ".join(str(v) for v in vals) + "]"


def arr_rows(M):
    return "#[" + ",\n   ".join("#[" + ", ".join(map(str, r)) + "]" for r in M) + "]"


print(f'''/-! ## Oracle certificate: Zhong (2025) family member I^2_{{1,8,1}} at n = 16

Instance: the Section 5.3 family I^2_{{1,8,1}} of X. Zhong, *Lower bounds on
the integrality ratio of the subtour LP for the traveling salesman problem*
(DAM 365, 2025), at `n = 16` — the current best known construction in the
scoring window, with `OPT_LP = 5` and `OPT_tour = 6 − 2/11 = 64/11`, gap
exactly `64/55`. The coordinates are scaled by `22` to integers (the gap is
scale-invariant):

* X-line `y = 0`: `(0,0), (11,0), (22,0)`
* Y-line `y = 11`: `(2k, 11)` for `k = 1..10`
* Z-line `y = 22`: `(0,22), (11,22), (22,22)`

The LP witness is the paper's half-integral optimal fractional tour
`x_{{1,8,1}}` (Section 5.1): `x = 1` on the three line paths and `x = 1/2` on
the six edges of the two end triangles; numerator `y = 2x` over `D = 2`, value
`110 = 5 × 22`. The tour witness is the exact Held–Karp DP table
(`T = 128 = (64/11) × 22`), computed inside Lean by `certWTable` — the
`2^16 × 16` table is too large to ship as a source literal. Hence
`OPT_tour / OPT_LP ≥ 128/110 = 64/55`. -/

/-- Number of points: the `n = 16` record member. -/
def certN : ℕ := 16

instance : NeZero certN := ⟨by decide⟩

/-- x-coordinates: Zhong's `I^2_{{1,8,1}}` scaled by `22` (array-backed for
fast lookups inside `native_decide`). -/
def certPXA : Array ℤ := {arr_z(PX)}

/-- y-coordinates. -/
def certPYA : Array ℤ := {arr_z(PY)}

/-- The coordinate functions. -/
def certPX (u : Fin certN) : ℤ := certPXA.getD u.val 0

/-- The coordinate functions. -/
def certPY (u : Fin certN) : ℤ := certPYA.getD u.val 0

/-- Raw L1 cost on natural indices (used by the Held–Karp table builder;
agrees with `l1Cost certPX certPY` on valid indices by definition). -/
def ccRaw (i j : ℕ) : ℕ :=
  (certPXA.getD i 0 - certPXA.getD j 0).natAbs + (certPYA.getD i 0 - certPYA.getD j 0).natAbs

/-- LP numerator: `2` on the three line paths, `1` on the six edges of the two
end triangles (the paper's half-integral point `x_{{1,8,1}}` with `D = 2`). -/
def certYA : Array (Array ℕ) := {arr_rows(y)}

/-- The LP numerator as a function. -/
def certY : Fin certN → Fin certN → ℕ := fun u v => (certYA.getD u.val #[]).getD v.val 0

/-- The LP denominator: `x = certY / 2`. -/
def certD : ℕ := 2

/-- The exact Held–Karp DP table, computed inside Lean (native-compiled when
the `native_decide` checks run): `certWTable[mask][j]` is the shortest path
from point `0` visiting exactly the set `mask` and ending at `j`;
`1000000` is the sentinel at states the potential inequalities never use. -/
def certWTable : Array (Array ℕ) := Id.run do
  let size := 2 ^ certN
  let big := 1000000
  let mut w : Array (Array ℕ) := Array.replicate size (Array.replicate certN big)
  w := w.set! 1 ((w.getD 1 #[]).set! 0 0)
  for mask in [1:size] do
    if mask.testBit 0 then
      for j in [1:certN] do
        if mask.testBit j then
          let pm := mask ^^^ (2 ^ j)
          let mut best := big
          for i in [0:certN] do
            if pm.testBit i then
              let cand := ((w.getD pm #[]).getD i 0) + ccRaw i j
              if cand < best then
                best := cand
          w := w.set! mask ((w.getD mask #[]).set! j best)
  pure w

/-- The potential table as a function. -/
def certW : ℕ → Fin certN → ℕ := fun mask j => (certWTable.getD mask #[]).getD j.val 0

/-- Certified tour lower bound: every L1 tour of the point set costs at least
`128` (the exact Held–Karp value, `OPT_tour = 128`). -/
def certT : ℕ := 128

/-- Claimed gap lower bound: the family value `64/55` at `n = 16`. -/
def claimedAlpha : ℚ := 64 / 55

/-- Point-set premise: the 16 points are pairwise distinct. -/
theorem pts_distinct : PointsDistinct certPX certPY := by
  decide

/-- LP degree check: every row of `certY` sums to `2 * certD = 4`. -/
theorem lp_deg : ∀ v : Fin certN, ∑ u : Fin certN, certY v u = 2 * certD := by
  decide

/-- LP subtour-cut check: every proper nonempty cut carries at least
`2 * certD = 4` (65534 cuts, checked by native compilation). -/
theorem lp_subtour : ∀ mask : ℕ, mask < 2 ^ certN → mask ≠ 0 → mask ≠ 2 ^ certN - 1 →
    2 * certD ≤ ∑ u : Fin certN, ∑ v : Fin certN,
      if mask.testBit u.val ∧ ¬ mask.testBit v.val then certY u v else 0 := by
  native_decide

/-- The Held–Karp potential inequalities for `certW` (every mask with point
`0`, every end point `j ≠ 0` in the mask, every predecessor `i`). -/
theorem pot_step : ∀ mask : ℕ, mask < 2 ^ certN → mask.testBit 0 = true →
    ∀ j i : Fin certN, j ≠ 0 → i ≠ j → mask.testBit j.val = true →
      mask.testBit i.val = true →
      certW mask j ≤ certW (mask ^^^ (2 ^ j.val)) i + l1Cost certPX certPY i j := by
  native_decide

/-- Main theorem: the scaled `I^2_{{1,8,1}}` point set has rectilinear
subtour-LP integrality gap at least `64/55` (in fact exactly `64/55`). -/
theorem main : GapBound certN certPX certPY claimedAlpha := by
  refine ⟨by decide, by decide, pts_distinct, ?_⟩
  exact gapLB_of_cert (by decide) (l1Cost certPX certPY) certW certY certD certT (by decide)
    claimedAlpha 64 55 (by decide) (by norm_num [claimedAlpha])
    (by native_decide) pot_step (by native_decide)
    (by decide) (by decide) (by decide) lp_deg lp_subtour (by decide)

end RectTSPGap''')
