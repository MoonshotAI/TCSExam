#!/usr/bin/env python3
"""Generate the theta(7,7,7) oracle certificate for graph-tsp-gap-lean-open.

Instance: the theta graph Theta(7,7,7) — endpoints 0, 1 joined by three
internally-disjoint paths of length 7 (n = 20), the Desjardins 2017
Figure 5.3.1 family member at n = 20 (n = 2 mod 3 case). This is exactly the
best instance of the solver sibling's oracle (solution/gen_submission.py),
whose checker recomputes OPT_LP = 21, OPT_tour = 26, gap = 26/21.

Certificate:
  * adjacency matrix (21 edges), shortest-path closure, BFS walk witnesses;
  * LP point x = y/2 (half-integral, exact value 21): y = 2 on 17 graph
    edges, y = 1 on the graph edges (0,2),(0,8),(1,7),(1,19) and on the two
    cross-path closure edges (2,8) and (7,19) (cost 2). Solved with scipy
    (float), rationalized to halves, then re-verified exactly below
    (degree, every cut via exact Stoer-Wagner min-cut, symmetry, box);
  * tour bound T = 26 via the exact Held-Karp DP (verified below);
  * alpha = 26/21 with 26 * (c.y) = 26 * 84 = 2184 = 21 * (2 * (26 * 2)).

The Lean potential table is NOT listed literally (2^20 x 20 entries would be
~10^8 tokens); the certificate builds it by a deterministic in-Lean loop and
checks the potential inequalities by native_decide. Every certificate
condition that the Lean native_decides check is verified in Python here
before emission.
"""
import sys
from fractions import Fraction

import numpy as np
from scipy.optimize import linprog

N, K = 20, 7
BIG = 1000000

# ---- graph (same numbering as the solver sibling's gen_submission.py) ----
edges = []
nxt = 2
for _ in range(3):
    verts = [0] + [nxt + j for j in range(K - 1)] + [1]
    nxt += K - 1
    edges += [(u, v) for u, v in zip(verts[:-1], verts[1:])]
assert nxt == N and len(edges) == 3 * K

adj = [[0] * N for _ in range(N)]
for u, v in edges:
    adj[u][v] = adj[v][u] = 1

# ---- exact integer metric closure (Floyd-Warshall) ----
INF = float("inf")
D = [[INF] * N for _ in range(N)]
for i in range(N):
    D[i][i] = 0
for u, v in edges:
    D[u][v] = D[v][u] = 1
for kk in range(N):
    for i in range(N):
        dik = D[i][kk]
        if dik == INF:
            continue
        for j in range(N):
            alt = dik + D[kk][j]
            if alt < D[i][j]:
                D[i][j] = alt
for i in range(N):
    assert D[i][i] == 0
    for j in range(N):
        assert D[i][j] != INF and D[i][j] == D[j][i]
        assert i == j or D[i][j] > 0
        for kk in range(N):
            assert D[i][kk] <= D[i][j] + D[j][kk]

# ---- LP point: float solve, rationalize to halves, verify exactly ----
pairs = [(i, j) for i in range(N) for j in range(i + 1, N)]
c = np.array([D[i][j] for i, j in pairs], dtype=float)
A_eq = np.zeros((N, len(pairs)))
for e, (i, j) in enumerate(pairs):
    A_eq[i, e] = 1.0
    A_eq[j, e] = 1.0
res = linprog(c, A_eq=A_eq, b_eq=np.full(N, 2.0), bounds=(0.0, 1.0), method="highs")
assert res.status == 0
xr = [Fraction(v).limit_denominator(2) for v in res.x]
y = [[0] * N for _ in range(N)]
for f, (i, j) in zip(xr, pairs):
    y[i][j] = y[j][i] = int(2 * f)
assert abs(res.fun - 21.0) < 1e-9
S = sum(D[i][j] * y[i][j] for i in range(N) for j in range(N))
assert S == 84, S  # LP value = S / (2 * 2) = 21
for v in range(N):
    assert sum(y[v][u] for u in range(N)) == 4, v          # degree = 2 * D_den
    assert y[v][v] == 0
    for u in range(N):
        assert y[u][v] == y[v][u] and 0 <= y[u][v] <= 2
# exact min cut over the integer numerators must be >= 2 * D_den = 4
def mincut_int(n, cap):
    w = [row[:] for row in cap]
    alive = [True] * n
    best = None
    remaining = n
    while remaining > 1:
        added = [False] * n
        tight = [0] * n
        prev = -1
        cur = next(i for i in range(n) if alive[i])
        added[cur] = True
        for _ in range(remaining - 1):
            nxt2, nxt_w = -1, None
            for i in range(n):
                if alive[i] and not added[i]:
                    tight[i] += w[cur][i]
                    if nxt_w is None or tight[i] > nxt_w:
                        nxt_w, nxt2 = tight[i], i
            prev, cur = cur, nxt2
            added[cur] = True
        cutval = sum(w[cur][j] for j in range(n) if alive[j] and j != cur)
        if best is None or cutval < best:
            best = cutval
        if prev == -1:
            break
        for i in range(n):
            if alive[i] and i != cur and i != prev:
                w[prev][i] += w[cur][i]
                w[i][prev] = w[prev][i]
        alive[cur] = False
        remaining -= 1
    return best
assert mincut_int(N, y) == 4

# ---- exact Held-Karp DP table (checked, not emitted) ----
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
        W[mask][j] = min(W[pm][i] + D[i][j] for i in range(N) if (pm >> i) & 1)
T = min(W[size - 1][j] + D[j][0] for j in range(1, N))
assert T == 26, T
for mask in range(size):
    if not mask & 1:
        continue
    for j in range(1, N):
        if not (mask >> j) & 1:
            continue
        for i in range(N):
            if i != j and (mask >> i) & 1:
                assert W[mask][j] <= W[mask ^ (1 << j)][i] + D[i][j], (mask, j, i)
for j in range(1, N):
    assert T <= W[size - 1][j] + D[j][0], j
assert 26 * S <= 21 * (2 * (T * 2)) == 2184 == 26 * S

# ---- BFS walk witnesses (PathsOk data) ----
from collections import deque
paths = [[None] * N for _ in range(N)]
for s in range(N):
    par = {s: None}
    q = deque([s])
    while q:
        u = q.popleft()
        for v in range(N):
            if adj[u][v] == 1 and v not in par:
                par[v] = u
                q.append(v)
    assert len(par) == N  # connected
    for t in range(N):
        p = []
        cur = t
        while cur is not None:
            p.append(cur)
            cur = par[cur]
        p.reverse()
        paths[s][t] = p
        assert len(p) - 1 == D[s][t], (s, t)
        for a, b in zip(p[:-1], p[1:]):
            assert adj[a][b] == 1

# ---- emission ----
def flat_rows(M):
    return ", ".join(str(x) for r in M for x in r)

def path_rows():
    out = []
    for s in range(N):
        for t in range(N):
            out.append("[" + ", ".join(map(str, paths[s][t])) + "]")
    return ",\n   ".join(out)

nonzero_y = [(i, j, y[i][j], D[i][j]) for i in range(N) for j in range(i + 1, N) if y[i][j]]
y_comment = "; ".join(f"y={v} on ({i},{j}) cost={d}" for i, j, v, d in nonzero_y)

print(f"""/-! ## Oracle certificate: the theta graph Θ(7,7,7) (n = 20, gap exactly 26/21)

Instance: endpoints 0 and 1 joined by three internally-disjoint paths of
length 7 — the Desjardins 2017 (Figure 5.3.1) family member at `n = 20`
(the `n = 2 mod 3` case), the same construction as the solver sibling's
oracle. OPT_LP = 21, OPT_tour = 26, gap exactly `26/21 ≈ 1.2381`: the
standing record anchor, so this certificate scores exactly 1.0 (ties the
record, does not beat it; `record_broken` stays false).

LP point (half-integral, exact value 21): `{y_comment}`; the numerator matrix
is `y = 2x`. All other entries are zero. The tour bound `T = 26` is certified
by the exact Held-Karp DP table. The table is not listed literally
(`2^20 × 20` entries would be hundreds of MB of source); it is built by the
deterministic in-Lean loop below and every potential inequality is checked by
`native_decide` (the table build and the checks take a few minutes inside the
verifier's 28-minute probe budget). -/

/-- Number of vertices: the theta graph Θ(7,7,7). -/
def certN : ℕ := 20

instance : NeZero certN := ⟨by decide⟩

/-- Adjacency matrix of Θ(7,7,7), flat row-major (`20 × 20`): paths
`0 — (2..7) — 1`, `0 — (8..13) — 1`, `0 — (14..19) — 1`. -/
def certAdjA : Array ℕ := #[{flat_rows(adj)}]

/-- The adjacency function (array lookup; `List`-matrix lookups would cost
one traversal per access, which is prohibitive at `n = 20`). -/
def certAdj : Fin certN → Fin certN → ℕ := fun u v => certAdjA.getD (u.val * certN + v.val) 0

/-- Shortest-path metric closure of Θ(7,7,7), flat row-major. -/
def certDistA : Array ℕ := #[{flat_rows(D)}]

/-- The distance function. -/
def certDist : Fin certN → Fin certN → ℕ := fun u v => certDistA.getD (u.val * certN + v.val) 0

/-- Walk witnesses for the closure: entry `u * certN + v` is a BFS shortest
path from `u` to `v` in the graph (length exactly `certDist u v`). -/
def certPathsM : List (List ℕ) :=
  [{path_rows()}]

/-- LP numerator `y = 2x`, flat row-major. -/
def certYA : Array ℕ := #[{flat_rows(y)}]

/-- The LP numerator as a function. -/
def certY : Fin certN → Fin certN → ℕ := fun u v => certYA.getD (u.val * certN + v.val) 0

/-- The LP denominator: `x = certY / 2`. -/
def certD : ℕ := 2

/-- Sentinel for unused potential-table states. -/
def potBIG : ℕ := 1000000

/-- The exact Held-Karp DP table, computed once into a flat array
(`2 ^ certN` masks × `certN` rows; entry `mask * certN + j`). States without
vertex `0`, or with `j` outside the mask, keep the sentinel. -/
def certTable : Array ℕ := Id.run do
  let n := certN
  let sz := 2 ^ n
  let mut t : Array ℕ := .replicate (sz * n) potBIG
  t := t.set! (1 * n + 0) 0
  for mask in [1:sz] do
    if mask &&& 1 == 1 then
      for hj in [1:n] do
        if (mask >>> hj) &&& 1 == 1 then
          let pm := mask ^^^ (1 <<< hj)
          let mut best := potBIG
          for hi in [0:n] do
            if (pm >>> hi) &&& 1 == 1 then
              let cand := t.getD (pm * n + hi) 0 + certDistA.getD (hi * n + hj) 0
              if cand < best then
                best := cand
          t := t.set! (mask * n + hj) best
  return t

/-- The potential table as a function. -/
def certW : ℕ → Fin certN → ℕ := fun mask j => certTable.getD (mask * certN + j.val) potBIG

/-- Certified tour lower bound (the exact optimum). -/
def certT : ℕ := 26

/-- Claimed gap lower bound: `26/21`, the family value at `n = 20`. -/
def claimedAlpha : ℚ := 26 / 21

/-- The Held-Karp potential inequalities for `certW`. -/
theorem pot_step : ∀ mask : ℕ, mask < 2 ^ certN → mask.testBit 0 = true →
    ∀ j i : Fin certN, j ≠ 0 → i ≠ j → mask.testBit j.val = true →
      mask.testBit i.val = true →
      certW mask j ≤ certW (mask ^^^ (2 ^ j.val)) i + certDist i j := by
  native_decide

/-- LP degree check: every row of `certY` sums to `2 * certD = 4`. -/
theorem lp_deg : ∀ v : Fin certN, ∑ u : Fin certN, certY v u = 2 * certD := by
  native_decide

/-- LP subtour-cut check: every proper nonempty cut carries at least
`2 * certD = 4`. -/
theorem lp_subtour : ∀ mask : ℕ, mask < 2 ^ certN → mask ≠ 0 → mask ≠ 2 ^ certN - 1 →
    2 * certD ≤ ∑ u : Fin certN, ∑ v : Fin certN,
      if mask.testBit u.val ∧ ¬ mask.testBit v.val then certY u v else 0 := by
  native_decide

/-- Main theorem: the theta graph Θ(7,7,7) with its shortest-path closure has
subtour-LP integrality gap at least `26/21` (in fact exactly `26/21`). -/
theorem main : GraphGapBound certN certAdj certDist claimedAlpha := by
  refine ⟨by decide, by decide, (by unfold SimpleAdj; native_decide),
    ⟨by native_decide, by native_decide, by native_decide, by native_decide⟩,
    (by unfold EdgeConsistent; native_decide),
    ⟨certPathsM, (by unfold PathsOk; native_decide)⟩, ?_⟩
  exact gapLB_of_cert (by decide) certDist certW certY certD certT (by decide)
    claimedAlpha 26 21 (by decide) (by norm_num [claimedAlpha])
    (by native_decide) pot_step (by native_decide)
    (by native_decide) (by native_decide) (by native_decide) lp_deg lp_subtour (by native_decide)

end GraphTSPGap""")
