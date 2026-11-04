#!/usr/bin/env python3
"""Small-example verification for the Caccetta–Häggkvist task package.

Checks, by brute force:
  A. For each (n, k) in the sc_circulant slot [(4,1),(5,2),(7,2),(7,3),(10,3)]:
     the circulant digraph on Z_n with jumps 1..k has out-degree exactly k at
     every vertex, and its directed girth is exactly ceil(n/k) (a cycle of
     that length exists, none shorter).  Mirrors the Lean statement.
  B. The k = 1 case on ALL loopless digraphs on n <= 4 vertices: minimum
     out-degree >= 1 implies a directed cycle of length <= n exists.
  C. The k = 2 case on ALL loopless digraphs on n <= 5 vertices: minimum
     out-degree >= 2 implies a directed cycle of length <= ceil(n/2) exists.

Pure Python, no dependencies.  Run: python3 verify_small_examples.py
"""

from itertools import combinations, permutations, product


def ceil_div(n, k):
    return (n + k - 1) // k


def circulant(n, k):
    """adj[i] = sorted list of out-neighbors of i in the circulant digraph."""
    return [[(i + d) % n for d in range(1, k + 1)] for i in range(n)]


def has_cycle_of_length_le(adj, m):
    """True iff the digraph (adjacency lists) has a directed cycle of length
    in [1, m].  A directed cycle is simple; length >= 2 since loopless."""
    n = len(adj)
    for length in range(2, min(m, n) + 1):
        for cyc in permutations(range(n), length):
            if all(cyc[(i + 1) % length] in adj[cyc[i]] for i in range(length)):
                return True
    return False


def girth_ge(adj, b):
    """True iff no directed cycle of length < b."""
    return not has_cycle_of_length_le(adj, b - 1)


def check_a():
    pairs = [(4, 1), (5, 2), (7, 2), (7, 3), (10, 3)]
    for n, k in pairs:
        adj = circulant(n, k)
        deg_ok = all(len(adj[i]) == k for i in range(n))
        bound = ceil_div(n, k)
        cyc = has_cycle_of_length_le(adj, bound)
        tight = girth_ge(adj, bound)
        status = "OK" if (deg_ok and cyc and tight) else "FAIL"
        print(f"A  (n,k)=({n},{k}): out-degree=={k} everywhere: {deg_ok}; "
              f"cycle of length <= {bound}: {cyc}; none shorter: {tight}  [{status}]")
        assert deg_ok and cyc and tight, f"A failed for {(n, k)}"


def all_digraphs(n):
    """Yield adjacency lists of every loopless digraph on vertices 0..n-1."""
    arcs = [(i, j) for i in range(n) for j in range(n) if i != j]
    for bits in product([False, True], repeat=len(arcs)):
        adj = [[] for _ in range(n)]
        for (i, j), b in zip(arcs, bits):
            if b:
                adj[i].append(j)
        yield adj


def check_bc():
    for label, k, max_n in [("B", 1, 4), ("C", 2, 5)]:
        tested = 0
        for n in range(2, max_n + 1):
            for adj in all_digraphs(n):
                if all(len(adj[i]) >= k for i in range(n)):
                    tested += 1
                    bound = ceil_div(n, k)
                    assert has_cycle_of_length_le(adj, bound), \
                        f"{label} counterexample: n={n}, k={k}, adj={adj}"
        print(f"{label}  k={k}: all loopless digraphs on n<= {max_n} with min "
              f"out-degree >= {k} have a cycle of length <= ceil(n/{k}); "
              f"{tested} digraphs tested  [OK]")


if __name__ == "__main__":
    check_a()
    check_bc()
    print("all checks passed")
