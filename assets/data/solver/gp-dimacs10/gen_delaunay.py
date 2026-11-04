#!/usr/bin/env python3
"""Delaunay-triangulation instance generator (judge-side tooling, NOT shipped).

  gen_delaunay.py SEED N

Points ~ Uniform([0,1)^2) with numpy seed SEED, Delaunay triangulation
(scipy), edges = triangulation edges; largest connected component kept,
relabelled, written to stdout in METIS/DIMACS10 format.
"""
import sys

import numpy as np
from scipy.spatial import Delaunay


def main():
    seed, n = int(sys.argv[1]), int(sys.argv[2])
    rng = np.random.default_rng(seed)
    pts = rng.random((n, 2))
    tri = Delaunay(pts)
    adj = [set() for _ in range(n)]
    for simplex in tri.simplices:
        a, b, c = int(simplex[0]), int(simplex[1]), int(simplex[2])
        adj[a].update((b, c))
        adj[b].update((a, c))
        adj[c].update((a, b))
    # largest connected component
    comp = [-1] * n
    best_id, best_sz, ncomp = -1, -1, 0
    for s in range(n):
        if comp[s] != -1:
            continue
        stack, sz = [s], 0
        comp[s] = ncomp
        while stack:
            u = stack.pop()
            sz += 1
            for v in adj[u]:
                if comp[v] == -1:
                    comp[v] = ncomp
                    stack.append(v)
        if sz > best_sz:
            best_id, best_sz = ncomp, sz
        ncomp += 1
    relabel = {u: i for i, u in enumerate(u for u in range(n) if comp[u] == best_id)}
    out = [[] for _ in range(len(relabel))]
    for u in range(n):
        if comp[u] != best_id:
            continue
        for v in adj[u]:
            if comp[v] == best_id:
                out[relabel[u]].append(relabel[v])
    m = sum(len(l) for l in out) // 2
    print(len(out), m)
    for l in out:
        print(" ".join(str(v + 1) for v in sorted(l)))
    print(f"n={len(out)} m={m} (dropped {n - len(out)} outside LCC)",
          file=sys.stderr)


if __name__ == "__main__":
    main()
