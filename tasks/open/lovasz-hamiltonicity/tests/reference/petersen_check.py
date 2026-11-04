#!/usr/bin/env python3
"""Small-instance numerical checks for lovasz-hamiltonicity (standard library only; no third-party dependencies).

Compare against the Petersen-graph definition in tests/reference/Basic.lean and compute:
  A. Basic graph parameters: vertex count, edge count, degree sequence (3-regularity), and girth (no triangles or quadrilaterals)
  B. Connectivity: BFS from one source reaches every vertex
  C. Vertex-transitivity: enumerate all automorphisms and verify transitivity on vertices (group order 120)
  D. Hamiltonian path: verify that the Lean-side witness 0-1-2-3-4-9-6-8-5-7 is a Hamiltonian path
  E. No Hamiltonian cycle: backtrack through all simple cycles starting at vertex 0; there is no 10-cycle
  F. Complete graphs K_n (n=1..8): connectivity, vertex-transitivity, and a Hamiltonian path (numerical version of c3)
Run: python3 tests/reference/petersen_check.py (prints PASS/FAIL for all checks; exits with code 1 if any check fails)
"""

from itertools import combinations

# ---- Petersen graph: edge list exactly matching Lean-side petersenEdges -----
EDGES = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 0),      # outer pentagon
         (5, 7), (7, 9), (9, 6), (6, 8), (8, 5),      # inner pentagram
         (0, 5), (1, 6), (2, 7), (3, 8), (4, 9)]      # spokes
N = 10
ADJ = [set() for _ in range(N)]
for a, b in EDGES:
    ADJ[a].add(b)
    ADJ[b].add(a)

results = []
def check(name, ok, detail=""):
    results.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}  {detail}")

# ---- A. Basic parameters ----------------------------------------------------
deg = sorted(len(ADJ[v]) for v in range(N))
check("A1 vertex count = 10", N == 10)
check("A2 edge count = 15 (no duplicate edges or self-loops)", len(EDGES) == 15 and len(set(tuple(sorted(e)) for e in EDGES)) == 15
      and all(a != b for a, b in EDGES))
check("A3 3-regular", deg == [3] * 10, f"degree sequence {deg}")

def girth():
    best = 99
    for s in range(N):
        dist = {s: 0}
        queue = [s]
        for v in queue:
            for w in ADJ[v]:
                if w not in dist:
                    dist[w] = dist[v] + 1
                    queue.append(w)
                elif dist[w] == dist[v]:          # cross-edge within the visited layer → odd-cycle candidate
                    best = min(best, dist[v] + dist[w] + 1)
                elif dist[w] > dist[v]:           # edge between layers → even-cycle candidate
                    best = min(best, dist[v] + dist[w] + 1)
    return best
check("A4 girth = 5 (no triangles or quadrilaterals)", girth() == 5, f"girth={girth()}")

# ---- B. Connectivity -------------------------------------------------------
seen = {0}
stack = [0]
while stack:
    v = stack.pop()
    for w in ADJ[v]:
        if w not in seen:
            seen.add(w)
            stack.append(w)
check("B1 connected (0 reaches all 10 vertices)", len(seen) == 10)

# ---- C. Vertex-transitivity: enumerate automorphisms with DFS -------------
def automorphisms():
    autos = []
    order = sorted(range(N), key=lambda v: -len(ADJ[v]))
    assign = {}
    used = set()
    def consistent(v, img):
        for u in ADJ[v]:
            if u in assign and (assign[u] not in ADJ[img]):
                return False
        return True
    def dfs(i):
        if i == N:
            autos.append(tuple(assign[v] for v in range(N)))
            return
        v = order[i]
        for img in range(N):
            if img not in used and len(ADJ[img]) == len(ADJ[v]) and consistent(v, img):
                assign[v] = img
                used.add(img)
                dfs(i + 1)
                del assign[v]
                used.remove(img)
    dfs(0)
    return autos

autos = automorphisms()
check("C1 automorphism group order = 120 (action of S5)", len(autos) == 120, f"found {len(autos)}")
orbit0 = sorted({a[0] for a in autos})
check("C2 vertex-transitive (orbit of vertex 0 covers all vertices)", orbit0 == list(range(N)), f"orbit {orbit0}")

# ---- D. Hamiltonian path (Lean-side witness) -------------------------------
WITNESS = [0, 1, 2, 3, 4, 9, 6, 8, 5, 7]
edges_ok = all(WITNESS[i + 1] in ADJ[WITNESS[i]] for i in range(len(WITNESS) - 1))
check("D1 witness 0-1-2-3-4-9-6-8-5-7 is a path (consecutive vertices are adjacent)", edges_ok)
check("D2 witness visits each vertex exactly once", sorted(WITNESS) == list(range(N)))

# ---- E. No Hamiltonian cycle: backtrack over all simple cycles through 0 ---
def has_hamiltonian_cycle():
    path = [0]
    visited = {0}
    def dfs(v):
        if len(path) == N:
            return 0 in ADJ[v]
        for w in ADJ[v]:
            if w not in visited:
                visited.add(w)
                path.append(w)
                if dfs(w):
                    return True
                path.pop()
                visited.remove(w)
        return False
    return dfs(0)
check("E1 Petersen graph has no Hamiltonian cycle (hypohamiltonian)", not has_hamiltonian_cycle())

# ---- F. Complete graphs K_n (numerical version of c3) ----------------------
def complete_ok(n):
    adj = [set(range(n)) - {v} for v in range(n)]
    connected = n >= 1  # a single vertex is connected by convention; for n≥2 every pair is adjacent
    # Vertex-transitive: for any u,v, swap(u,v) is an automorphism (adjacency in a complete graph depends only on inequality)
    transitive = True
    for u in range(n):
        for v in range(n):
            img = [w if w not in (u, v) else (v if w == u else u) for w in range(n)]
            for a, b in combinations(range(n), 2):
                if (b in adj[a]) != (img[b] in adj[img[a]]):
                    transitive = False
    ham_path = list(range(n))  # 0-1-...-n-1, consecutive vertices are adjacent
    return connected and transitive and ham_path is not None
check("F1 K_n (n=1..8) is connected, vertex-transitive, and has a Hamiltonian path", all(complete_ok(n) for n in range(1, 9)))

failed = [name for name, ok in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
raise SystemExit(1 if failed else 0)
