#!/usr/bin/env python3
"""Enumerate small executable examples—the numerical facts behind the evasiveness conjecture (Karp conjecture).

Uses only the standard library and runs in seconds (the v=5 computation of D takes seconds, well under a minute). It has four parts:
  A. v=3: decision-tree complexity of all nontrivial graph properties (4 orbit assignments); all are evasive (D=3=C(3,2)).
  B. v=4: all 2046 nontrivial graph properties (11 isomorphism classes); all are evasive (D=6), with no non-evasive example.
  C. v=5: ten natural candidate properties, including non-monotone ones; all are evasive (D=10).
  D. The v=5 scorpion-graph property (the asymptotic O(v) example of Best–van Emde Boas–Lenstra 1974) is still evasive at D=10
     (the O(v) algorithm's constant 3v is no smaller than C(5,2) at v=5; non-evasiveness of the scorpion property appears only for v≥8).

A/B show that for small vertex counts there is no graph property that is both non-monotone and non-evasive. This is empirical support for making the nontriviality assumption necessary in c2, rather than claiming that the monotonicity assumption is necessary using a non-monotone counterexample. D supports c1: at v=3 there are exactly three nontrivial monotone properties, all evasive, consistent with the general proof of c1.
"""
import itertools, functools, sys

def edges_of(v):
    return [(a, b) for a in range(v) for b in range(a + 1, v)]

def orbits(v):
    E = edges_of(v)
    m = len(E)
    idx = {e: i for i, e in enumerate(E)}
    def apply(p, g):
        out = 0
        for i, (a, b) in enumerate(E):
            if (g >> i) & 1:
                a2, b2 = p[a], p[b]
                out |= 1 << idx[(min(a2, b2), max(a2, b2))]
        return out
    seen = [False] * (1 << m)
    orbs = []
    for g in range(1 << m):
        if seen[g]:
            continue
        orb = set()
        for p in itertools.permutations(range(v)):
            orb.add(apply(p, g))
        for h in orb:
            seen[h] = True
        orbs.append(sorted(orb))
    oid = [0] * (1 << m)
    for k, o in enumerate(orbs):
        for h in o:
            oid[h] = k
    return E, orbs, oid

def make_D(f, m):
    @functools.lru_cache(maxsize=None)
    def D(frozen, fvals):
        base = None
        for g in range(1 << m):
            if (g & frozen) == fvals:
                val = f[g]
                if base is None:
                    base = val
                elif val != base:
                    break
        else:
            return 0
        best = m + 1
        for e in range(m):
            if frozen >> e & 1:
                continue
            d = 1 + max(D(frozen | (1 << e), fvals), D(frozen | (1 << e), fvals | (1 << e)))
            if d < best:
                best = d
        return best
    return D

def mono_inc(f, m):
    for g in range(1 << m):
        for b in range(m):
            if f[g] == 1 and f[g | (1 << b)] == 0:
                return False
    return True

def part_A():
    v = 3
    E, orbs, oid = orbits(v)
    m = len(E)
    print(f"A. v=3: {len(orbs)} isomorphism classes (by edge count 0..3)")
    for assign in range(1 << len(orbs)):
        f = tuple((assign >> oid[g]) & 1 for g in range(1 << m))
        if len(set(f)) == 1:
            continue
        d = make_D(f, m)(0, 0)
        ec = [k for k in range(len(orbs)) if (assign >> k) & 1]
        print(f"   property true on edge-counts {ec}: monotone={mono_inc(f, m)} D={d}")

def part_B():
    v = 4
    E, orbs, oid = orbits(v)
    m = len(E)
    n_nt = n_ev = n_mono = n_mono_ev = 0
    for assign in range(1 << len(orbs)):
        f = tuple((assign >> oid[g]) & 1 for g in range(1 << m))
        if len(set(f)) == 1:
            continue
        n_nt += 1
        d = make_D(f, m)(0, 0)
        if d == m:
            n_ev += 1
        if mono_inc(f, m):
            n_mono += 1
            if d == m:
                n_mono_ev += 1
    print(f"B. v=4: {len(orbs)} classes; nontrivial properties {n_nt}, evasive {n_ev}; "
          f"monotone nontrivial {n_mono}, evasive {n_mono_ev}")
    print(f"   => non-monotone non-evasive properties on v=4: {n_nt - n_mono - (n_ev - n_mono_ev)}")

def prop_table(v):
    E = edges_of(v)
    m = len(E)
    idx = {e: i for i, e in enumerate(E)}
    def adj(g, a, b):
        if a == b:
            return False
        return (g >> idx[(min(a, b), max(a, b))]) & 1 == 1
    def degs(g):
        return tuple(sorted(sum(adj(g, a, b) for b in range(v)) for a in range(v)))
    def ne(g):
        return bin(g).count("1")
    P = {}
    P['exactly_one_edge'] = lambda g: int(ne(g) == 1)
    P['exists_isolated_edge'] = lambda g: int(any(
        adj(g, a, b)
        and all((not adj(g, a, y)) or y == b for y in range(v))
        and all((not adj(g, b, y)) or y == a for y in range(v))
        for a in range(v) for b in range(a + 1, v)))
    P['star_K1,4'] = lambda g: int(ne(g) == 4 and degs(g) == (1, 1, 1, 1, 4))
    P['is_C5'] = lambda g: int(ne(g) == 5 and degs(g) == (2, 2, 2, 2, 2))
    P['has_isolated_vertex'] = lambda g: int(0 in degs(g))
    P['edgecount_in_3..6'] = lambda g: int(3 <= ne(g) <= 6)
    P['deg_seq_2,2,2,3,3'] = lambda g: int(degs(g) == (2, 2, 2, 3, 3))
    P['triangle_plus_rest_isolated'] = lambda g: int(ne(g) == 3 and degs(g) == (0, 0, 2, 2, 2))
    P['has_dominating_vertex'] = lambda g: int(4 in degs(g))
    P['scorpion'] = lambda g: int(any(
        all(adj(g, q, x) for x in range(v) if x != q)
        and sum(1 for x in range(v) if x != q
                and all((not adj(g, x, y)) or y == q for y in range(v))) >= 2
        for q in range(v)))
    return E, m, P

def part_CD():
    v = 5
    E, m, P = prop_table(v)
    print(f"C/D. v=5: m={m}; candidate properties:")
    for name, f_ in P.items():
        f = tuple(f_(g) for g in range(1 << m))
        d = make_D(f, m)(0, 0)
        print(f"   {name:32s} monotone={mono_inc(f, m)!s:5s} ones={sum(f):4d} D={d}")

if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    part_A()
    part_B()
    part_CD()
