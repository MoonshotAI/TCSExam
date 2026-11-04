#!/usr/bin/env python3
"""Small-instance numerical checks for total-coloring-conjecture, independent of the Lean definition layer.

Use brute-force enumeration to compute the total chromatic number χ'' for three test graphs (K3, the star K_{1,3}, and the complete bipartite graph K_{2,2}). Enumerate all assignments of colors to vertices and edges and check the three total-coloring conditions:
  (i)   adjacent vertices have different colors
  (ii)  adjacent edges (distinct edges sharing an endpoint) have different colors
  (iii) each edge has a different color from both of its endpoints
Also check Δ (maximum degree) and the relation between χ'' and Δ+1/Δ+2.

Literature reference: χ''(K_n) = n for odd n and n+1 for even n; χ''(K_{n,n}) = n+2
(Behzad–Chartrand–Cooper 1967). Expected values: 3 for K3, 4 for K_{2,2}, and 4 for the star K_{1,3}.
"""

from itertools import product


def total_colorings_ok(n, edges, vc, ec):
    """Check whether vertex coloring vc (an n-tuple) and edge coloring ec (a tuple aligned with edges) form a valid total coloring."""
    # (i) Adjacent vertices have different colors
    for a, b in edges:
        if vc[a] == vc[b]:
            return False
    # (ii) Adjacent edges have different colors
    for i in range(len(edges)):
        for j in range(i + 1, len(edges)):
            if set(edges[i]) & set(edges[j]) and ec[i] == ec[j]:
                return False
    # (iii) Each edge has a different color from its endpoints
    for (a, b), col in zip(edges, ec):
        if vc[a] == col or vc[b] == col:
            return False
    return True


def total_chromatic_number(n, edges, kmax):
    """Return the least k for which a valid total coloring exists; kmax is the search limit (the number of vertices plus edges always suffices)."""
    for k in range(0, kmax + 1):
        for vc in product(range(k), repeat=n):
            for ec in product(range(k), repeat=len(edges)):
                if total_colorings_ok(n, edges, vc, ec):
                    return k
    return None


def max_degree(n, edges):
    deg = [0] * n
    for a, b in edges:
        deg[a] += 1
        deg[b] += 1
    return max(deg) if n else 0


CASES = [
    ("K3 (complete graph)", 3, [(0, 1), (0, 2), (1, 2)], 3),
    ("Star K_{1,3} (tree)", 4, [(0, 1), (0, 2), (0, 3)], 4),
    ("K_{2,2} (complete bipartite graph, i.e. C4)", 4, [(0, 2), (0, 3), (1, 2), (1, 3)], 4),
]

failures = 0
for name, n, edges, expect in CASES:
    chi = total_chromatic_number(n, edges, n + len(edges))
    delta = max_degree(n, edges)
    ok = chi == expect
    failures += 0 if ok else 1
    print(f"{name}: χ'' = {chi} (expected {expect}), Δ = {delta}, "
          f"Δ+1 = {delta + 1}, Δ+2 = {delta + 2}, "
          f"χ'' ≤ Δ+2 holds: {chi <= delta + 2}; check {'PASS' if ok else 'FAIL'}")

print("All checks passed" if failures == 0 else f"{failures} case(s) failed")
raise SystemExit(1 if failures else 0)
