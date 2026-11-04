#!/usr/bin/env python3
"""Small-case numerical validation for explicit-ramsey-graph-log.

Computes, with exact algorithms (branch and bound with greedy-coloring
bound; exhaustive for the tiny cases):

  (a) clique number and independence number of the Paley graphs at the
      small primes q = 1 (mod 4), with floor(log2 q) as a numerical
      reference scale — the task asks for a universal polylogarithmic bound;
  (b) the 17-vertex witness for R(4,4) > 17 (Paley graph on 17 vertices:
      no 4-clique, no 4-independent set) — the small-N echo of the
      probabilistic existence (Erdos 1947) behind the conjecture;
      plus sampled G(N,1/2) clique/independence numbers at small N
      against 2*log2(N) (the Erdos magnitude);
  (c) boundary behavior: complete and edgeless graphs.

Deterministic (fixed seeds).  Stdlib only.
"""

import math
import random


def paley_adj(q):
    """Adjacency (as bitsets) of the Paley graph on ZMod q, q = 1 (mod 4) prime."""
    squares = {(r * r) % q for r in range(q)}
    adj = [0] * q
    for x in range(q):
        for y in range(q):
            if x != y and ((x - y) % q) in squares:
                adj[x] |= 1 << y
    return adj


def gnaph_adj(n, adj):
    return adj


def random_adj(n, rng):
    adj = [0] * n
    for i in range(n):
        for j in range(i + 1, n):
            if rng.random() < 0.5:
                adj[i] |= 1 << j
                adj[j] |= 1 << i
    return adj


def complement_adj(n, adj):
    full = (1 << n) - 1
    return [(full ^ (1 << i)) & ~adj[i] & full for i in range(n)]


def max_clique(n, adj):
    """Exact maximum clique size via Tomita-style branch and bound."""
    best = [0]

    def color_sort(cands):
        # greedy coloring; returns (ordered vertices, color bounds)
        order, bounds = [], []
        uncolored = cands
        color = 0
        while uncolored:
            color += 1
            avail = uncolored
            while avail:
                v = avail & (-avail)  # lowest set bit
                v = v.bit_length() - 1
                order.append(v)
                bounds.append(color)
                uncolored &= ~(1 << v)
                avail &= ~(1 << v)
                avail &= ~adj[v]
        return order, bounds

    def expand(cands, size):
        if not cands:
            best[0] = max(best[0], size)
            return
        order, bounds = color_sort(cands)
        for i in range(len(order) - 1, -1, -1):
            if size + bounds[i] <= best[0]:
                return
            v = order[i]
            # Candidates follow the greedy-color order, not vertex labels.
            # Vertices already processed above have been removed from cands.
            expand(cands & adj[v], size + 1)
            cands &= ~(1 << v)

    expand((1 << n) - 1, 0)
    return best[0]


def main():
    print("== (a) Paley graphs at small primes q = 1 (mod 4) ==")
    print(f"{'q':>4} {'omega':>6} {'alpha':>6} {'floor(log2 q)':>14} {'omega/log2':>11}")
    primes = [q for q in range(5, 60)
              if q % 4 == 1 and all(q % d for d in range(2, int(q ** 0.5) + 1))]
    for q in primes:
        adj = paley_adj(q)
        omega = max_clique(q, adj)
        alpha = max_clique(q, complement_adj(q, adj))
        l2 = int(math.log2(q))
        print(f"{q:>4} {omega:>6} {alpha:>6} {l2:>14} {omega / l2:>11.3f}")

    print()
    print("== (b1) R(4,4) > 17 witness: Paley graph on 17 vertices ==")
    adj = paley_adj(17)
    has_4clique = False
    import itertools
    for s in itertools.combinations(range(17), 4):
        if all(adj[x] >> y & 1 for x, y in itertools.combinations(s, 2)):
            has_4clique = True
    cadj = complement_adj(17, adj)
    has_4indep = False
    for s in itertools.combinations(range(17), 4):
        if all(cadj[x] >> y & 1 for x, y in itertools.combinations(s, 2)):
            has_4indep = True
    print(f"Paley(17) omega = {max_clique(17, adj)}, alpha = {max_clique(17, cadj)}, "
          f"4-clique: {has_4clique}, 4-independent-set: {has_4indep} "
          f"(both must be False for R(4,4) > 17)")

    print()
    print("== (b2) sampled G(N,1/2) clique/independence numbers vs 2*log2(N) ==")
    print(f"{'N':>4} {'sample':>7} {'omega':>6} {'alpha':>6} {'2*log2(N)':>10}")
    rng = random.Random(20260904)
    for n in (8, 16, 32, 64):
        for t in range(3):
            adj = random_adj(n, rng)
            omega = max_clique(n, adj)
            alpha = max_clique(n, complement_adj(n, adj))
            print(f"{n:>4} {t:>7} {omega:>6} {alpha:>6} {2 * math.log2(n):>10.2f}")

    print()
    print("== (c) boundary cases ==")
    n = 5
    complete = [((1 << n) - 1) ^ (1 << i) for i in range(n)]
    edgeless = [0] * n
    print(f"K5 omega = {max_clique(n, complete)} (expect 5), alpha = {max_clique(n, complement_adj(n, complete))} (expect 1)")
    print(f"edgeless-5 omega = {max_clique(n, edgeless)} (expect 1), alpha = {max_clique(n, complement_adj(n, edgeless))} (expect 5)")


if __name__ == "__main__":
    main()
