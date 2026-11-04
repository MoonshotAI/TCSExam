#!/usr/bin/env python3
"""Deterministic constructions for kissing-d13.

  cross polytope (26 points): the coordinate unit vectors and their
  negations, {+-e_i}. Squared norms are 1; distinct points sit at squared
  distance 2 (+-e_i vs +-e_j, i != j) or 4 (e_i vs -e_i), so
  max ||x||^2 = 1 <= 2 = min ||x-y||^2. This is the trivial construction.

  D13 root system (312 points): all +-e_i +- e_j with i < j, i.e. the
  minimal vectors of the D13 lattice: 4 * C(13,2) = 312 vectors of
  squared norm 2. Distinct roots have inner product in {-2, -1, 0, 1},
  hence squared distance 4 - 2<x,y> >= 2: the kissing condition holds
  with equality.

Usage: python3 gen_examples.py [cross|d13]   (default: print both sizes)
Writes the chosen configuration to stdout as a submission JSON; with no
argument it just reports the sizes. The two shipped example files were
produced by:
  python3 gen_examples.py cross > example_cross26.json
  python3 gen_examples.py d13   > example_d13_roots312.json
"""
import json
import sys

DIM = 13


def cross_polytope():
    pts = []
    for i in range(DIM):
        for s in (1, -1):
            p = [0] * DIM
            p[i] = s
            pts.append(p)
    return pts


def d13_roots():
    pts = []
    for i in range(DIM):
        for j in range(i + 1, DIM):
            for si in (1, -1):
                for sj in (1, -1):
                    p = [0] * DIM
                    p[i] = si
                    p[j] = sj
                    pts.append(p)
    return pts


def emit(points, comment):
    print(json.dumps({"points": points, "comment": comment}))


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else ""
    if which == "cross":
        emit(cross_polytope(),
             "cross polytope {+-e_i} (26 points): the trivial construction")
    elif which == "d13":
        emit(d13_roots(),
             "D13 root system {+-e_i +- e_j} (312 points)")
    else:
        print(f"cross polytope: {len(cross_polytope())} points", file=sys.stderr)
        print(f"D13 root system: {len(d13_roots())} points", file=sys.stderr)


if __name__ == "__main__":
    main()
