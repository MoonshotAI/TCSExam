#!/usr/bin/env python3
"""Exhaustive enumeration behind the Ryser-conjecture special cases.

An r-partite r-uniform hypergraph with part sizes s_0..s_{r-1} is a set of
transversals (one vertex from each part).  This script computes tau (vertex
cover number) and nu (matching number) exactly by memoized brute force over
edge subsets, and checks:

  (1) the three named instances of the Lean checkpoints:
        konigWitness  (r = 2, parts 2+3 -> modelled on 3+3, 4 edges)
        paschConfig   (r = 3, parts 2+2+2, 4 edges: {(x,y,x+y mod 2)})
        truncatedPG3  (r = 4, parts 3+3+3+3, 9 edges: {(x,y,x+y,x+2y) over F3})
  (2) Ryser's bound tau <= (r-1)*nu on *all* hypergraphs with
        r = 3, part sizes (2,2,2)   [2^8  = 256 hypergraphs]
        r = 3, part sizes (2,2,3)   [2^12 = 4096 hypergraphs]
        r = 4, part sizes (2,2,2,2) [2^16 = 65536 hypergraphs]

Pure stdlib; runs in seconds.  Usage: python3 enumerate_small.py
"""

from functools import lru_cache
from itertools import product


def build_universe(part_sizes):
    """Return (edge_masks, hit_masks) for the complete r-partite hypergraph.

    Vertices are numbered 0..n-1 with part offsets; each of the prod(s_i)
    possible edges is a bitmask over vertices.  hit_masks[v] is the bitmask of
    the universe of edges containing vertex v.
    """
    offsets = [0]
    for s in part_sizes:
        offsets.append(offsets[-1] + s)
    edges = []
    for choice in product(*[range(s) for s in part_sizes]):
        mask = 0
        for i, v in enumerate(choice):
            mask |= 1 << (offsets[i] + v)
        edges.append(mask)
    hit = [0] * offsets[-1]
    for idx, em in enumerate(edges):
        for v in range(offsets[-1]):
            if em >> v & 1:
                hit[v] |= 1 << idx
    return edges, hit


def make_tau_nu(hit, n_edges, n_vertices):
    """Memoized exact tau(S) and nu(S) over edge subsets S (bitmasks)."""
    full = (1 << n_edges) - 1

    @lru_cache(maxsize=None)
    def tau(S):
        if S == 0:
            return 0
        # pick the lowest edge e of S; every cover contains a vertex of e
        low = S & -S
        e_idx = low.bit_length() - 1
        em = 0
        for idx in range(n_edges):
            if low >> idx & 1:
                em = EDGE_MASKS[idx]
                break
        best = n_vertices + 1
        m = em
        while m:
            v_bit = m & -m
            v = v_bit.bit_length() - 1
            best = min(best, 1 + tau(S & ~HIT[v]))
            m &= m - 1
        return best

    @lru_cache(maxsize=None)
    def nu(S):
        if S == 0:
            return 0
        low = S & -S
        e_idx = low.bit_length() - 1
        em = EDGE_MASKS[e_idx]
        # option 1: skip e; option 2: take e, drop all edges meeting e
        meet = 0
        mm = em
        while mm:
            v_bit = mm & -mm
            meet |= HIT[v_bit.bit_length() - 1]
            mm &= mm - 1
        return max(nu(S & ~low), 1 + nu(S & ~meet))

    return tau, nu


# module-level, patched per universe (keeps the lru_cache keys small ints)
EDGE_MASKS = []
HIT = []


def tau_nu_of(part_sizes, edge_index_subset):
    global EDGE_MASKS, HIT
    EDGE_MASKS, HIT = build_universe(part_sizes)
    tau, nu = make_tau_nu(HIT, len(EDGE_MASKS), sum(part_sizes))
    S = 0
    for i in edge_index_subset:
        S |= 1 << i
    return tau(S), nu(S)


def check_named():
    """The three Lean-checkpoint instances, with hand-computed expectations."""
    cases = [
        ("konigWitness (r=2, edges a0b0 a0b1 a1b1 a1b2)", [3, 3],
         [(0, 0), (0, 1), (1, 1), (1, 2)], 2, 2),
        ("paschConfig (r=3, truncated Fano)", [2, 2, 2],
         [(0, 0, 0), (0, 1, 1), (1, 0, 1), (1, 1, 0)], 2, 1),
        ("truncatedPG3 (r=4, truncated PG(2,3))", [3, 3, 3, 3],
         [(x, y, (x + y) % 3, (x + 2 * y) % 3) for x in range(3) for y in range(3)], 3, 1),
    ]
    for name, parts, tuples_, exp_tau, exp_nu in cases:
        edge_masks, _ = build_universe(parts)
        idx = [edge_masks.index(
            sum(1 << (sum(parts[:i]) + v) for i, v in enumerate(t)))
            for t in tuples_]
        tau, nu = tau_nu_of(parts, idx)
        r = len(parts)
        ok = (tau == exp_tau and nu == exp_nu)
        print(f"{name}: tau = {tau}, nu = {nu} "
              f"(expected {exp_tau}, {exp_nu}) -> {'OK' if ok else 'MISMATCH'}; "
              f"tau <= (r-1)*nu: {tau} <= {(r - 1) * nu} -> {tau <= (r - 1) * nu}")
        # extra structural facts used in the docs
        degs = [0] * sum(parts)
        for t in tuples_:
            for i, v in enumerate(t):
                degs[sum(parts[:i]) + v] += 1
        intersecting = all(
            any(t[i] == u[i] for i in range(r)) for a, t in enumerate(tuples_)
            for u in tuples_[a + 1:])
        print(f"   max vertex degree {max(degs)}, pairwise intersecting: {intersecting}")


def enumerate_all(part_sizes):
    """Check tau <= (r-1)*nu on every hypergraph with the given part sizes."""
    global EDGE_MASKS, HIT
    EDGE_MASKS, HIT = build_universe(part_sizes)
    n_edges = len(EDGE_MASKS)
    r = len(part_sizes)
    tau, nu = make_tau_nu(HIT, n_edges, sum(part_sizes))
    total = 1 << n_edges
    bad = 0
    tight = 0
    worst_ratio_num, worst_ratio_den = 0, 1
    for S in range(total):
        t, n = tau(S), nu(S)
        if t > (r - 1) * n:
            bad += 1
            if bad == 1:
                print(f"   FIRST COUNTEREXAMPLE: S={S:b} tau={t} nu={n}")
        if n > 0 and t == (r - 1) * n:
            tight += 1
        if n > 0 and t * worst_ratio_den > worst_ratio_num * n:
            worst_ratio_num, worst_ratio_den = t, n
    print(f"r = {r}, part sizes {part_sizes}: checked {total} hypergraphs, "
          f"violations of tau <= (r-1)*nu: {bad}; "
          f"tight (tau = (r-1)*nu, nu > 0): {tight}; "
          f"max tau/nu = {worst_ratio_num}/{worst_ratio_den}")


def main():
    print("== named instances (Lean checkpoints) ==")
    check_named()
    print("== exhaustive enumeration ==")
    enumerate_all([2, 2, 2])
    enumerate_all([2, 2, 3])
    enumerate_all([2, 2, 2, 2])


if __name__ == "__main__":
    main()
