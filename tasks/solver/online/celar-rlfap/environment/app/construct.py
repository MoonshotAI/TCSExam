#!/usr/bin/env python3
"""Deterministic constructor for the celar task: seeded min-conflicts.

Always prints a complete `f = [...];` block on stdout. The search is fully
deterministic (fixed seed sequence, fixed iteration counts, fixed scan
orders), so the produced solution — and its objective value — is a pinned
constant for each instance, independent of machine speed.

Structure of the search:
  1. hard phase: min-conflicts over the equality constraints
     |f[x]-f[y]| = k ONLY, with sideways moves, restarting from a fresh
     deterministic seed until the system is satisfied (CELAR equality
     systems are consistent; restarts make the phase robust);
  2. soft phase: weighted min-conflicts initialized at the hard-feasible
     point. A hard violation is weighted above the sum of ALL soft costs,
     so the search never trades a hard constraint for soft savings (and if
     a drift move does break one, the repair phase engages again).

Model recap: soft constraint (x, y, k, w) costs costs[w] when
|f[x]-f[y]| <= k; the objective is the total weighted violation.

Usage: construct.py INSTANCE_PATH [ITERS]
"""
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("/opt/celar", "/work", HERE):
    if os.path.exists(os.path.join(p, "public_runner.py")):
        sys.path.insert(0, p)
        break
import public_runner


def solve(inst, iters):
    costs = inst["costs"]
    cats = inst["categories"]
    doms = [sorted(cats[d - 1]) for d in inst["domains"]]
    n = len(doms)
    hard = inst["hard"]
    soft = inst["soft"]
    hard_w = sum(costs[c[3] - 1] for c in soft) + 1  # hard outweighs ALL soft
    nh = len(hard)
    inc = [[] for _ in range(n)]
    for ci, (x, y, k) in enumerate(hard):
        inc[x - 1].append(ci)
        inc[y - 1].append(ci)
    for ci, (x, y, k, w) in enumerate(soft):
        inc[x - 1].append(nh + ci)
        inc[y - 1].append(nh + ci)
    cx = [c[0] - 1 for c in hard] + [c[0] - 1 for c in soft]
    cy = [c[1] - 1 for c in hard] + [c[1] - 1 for c in soft]
    ck = [c[2] for c in hard] + [c[2] for c in soft]
    cw = [1] * nh + [costs[c[3] - 1] for c in soft]
    m = len(cx)

    def hard_bad(f, ci):
        return abs(f[cx[ci]] - f[cy[ci]]) != ck[ci]

    # ---------------- phase 1: satisfy the equality system ----------------
    f = None
    hard_iters = max(20000, iters // 3)
    for restart in range(4):
        rng = random.Random(42 + restart * 7919)
        g = [d[rng.randrange(len(d))] for d in doms]
        bad = set(ci for ci in range(nh) if hard_bad(g, ci))
        for _ in range(hard_iters):
            if not bad:
                break
            ci = rng.choice(tuple(bad))
            j = cx[ci] if rng.random() < 0.5 else cy[ci]
            bv, bc = None, None
            for v in doms[j]:
                g[j] = v
                c = 0
                for c2 in inc[j]:
                    if c2 < nh and hard_bad(g, c2):
                        c += 1
                if bv is None or c < bc or (c == bc and rng.random() < 0.5):
                    bv, bc = v, c
            g[j] = bv
            for c2 in inc[j]:
                if c2 < nh:
                    if hard_bad(g, c2):
                        bad.add(c2)
                    else:
                        bad.discard(c2)
        if not bad:
            f = g
            break
    if f is None:
        # could not satisfy the hard system (not expected on CELAR data):
        # emit the last state anyway; the checker will score it invalid
        print("f = [%s];" % ", ".join(map(str, g)))
        print("----------")
        return

    # ---------------- phase 2: minimize weighted violations ---------------
    def violated(g, ci):
        d = abs(g[cx[ci]] - g[cy[ci]])
        return d != ck[ci] if ci < nh else d <= ck[ci]

    rng = random.Random(424242)
    bad = set()
    for ci in range(m):
        if violated(f, ci):
            bad.add(ci)

    def weight(ci):
        return hard_w if ci < nh else cw[ci]

    def total(g):
        return sum(weight(ci) for ci in bad)

    best = (total(f), tuple(f))
    for _ in range(iters):
        if not bad:
            break
        ci = rng.choice(tuple(bad))
        j = cx[ci] if rng.random() < 0.5 else cy[ci]
        bv, bc = None, None
        for v in doms[j]:
            g2 = f[j]
            f[j] = v
            c = 0
            for c2 in inc[j]:
                if violated(f, c2):
                    c += weight(c2)
            f[j] = g2
            if bv is None or c < bc or (c == bc and rng.random() < 0.5):
                bv, bc = v, c
        f[j] = bv
        for c2 in inc[j]:
            if violated(f, c2):
                bad.add(c2)
            else:
                bad.discard(c2)
        cur = total(f)
        if cur < best[0]:
            best = (cur, tuple(f))

    f = list(best[1])
    print("f = [%s];" % ", ".join(map(str, f)))
    print("----------")


if __name__ == "__main__":
    inst = public_runner.load_instance(sys.argv[1])
    iters = int(sys.argv[2]) if len(sys.argv) > 2 else 60000
    solve(inst, iters)
