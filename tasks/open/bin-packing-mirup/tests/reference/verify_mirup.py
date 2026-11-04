#!/usr/bin/env python3
"""Executable verification behind the bin-packing MIRUP special cases.

For a bin packing instance (item sizes s_1..s_n in (0,1], bin capacity 1):
  - patterns: subsets of items with total size <= 1
  - configuration LP: min sum x_p, x_p >= 0, covering every item >= once
  - OPT: exact minimum number of bins (DFS)

Everything is computed exactly with Fraction arithmetic (dual simplex with
Bland's rule; the primal certificate is read off the shadow prices of the
optimal dual tableau and then verified). No third-party libraries; runs in
about half a minute.

Checks (the numbers go into tests/reference/small-examples.md):
  1. uniform sizes: OPT = ceil(n/m), LP = n/m with m = floor(1/c)
     (special case (a), `mirup_uniform`)
  2. the three small instances of special case (b), `mirup_small`
  3. MIRUP on 3000 random instances with n <= 6 items (no violation, and no
     IRUP failure either), plus 2000 random instances with n in 7..9 (all
     IRUP, consistent with Kartak et al. 2015)
  4. the tightness instance of special case (c), `mirup_tight`: the
     Kartak-Kurz-Ripatti-Scheithauer instance (4,6,6,9,16,29,32,37,40,62)/81
     has LP = 3, OPT = 4; prints the exact primal/dual certificates used in
     the Lean proofs
"""

from fractions import Fraction
import random

# ---------------------------------------------------------------- patterns

def all_patterns(sizes):
    n = len(sizes)
    out = []
    for mask in range(1, 1 << n):
        tot = sum(sizes[i] for i in range(n) if mask >> i & 1)
        if tot <= 1:
            out.append(tuple(i for i in range(n) if mask >> i & 1))
    return out

def maximal_patterns(sizes):
    pats = [set(p) for p in all_patterns(sizes)]
    out = []
    for i, p in enumerate(pats):
        if not any(j != i and p < q for j, q in enumerate(pats)):
            out.append(tuple(sorted(p)))
    return out

# ---------------------------------------------------------------- exact LP

def simplex_max(c, A, b):
    """max c.w s.t. A w <= b, w >= 0 (b >= 0), exact via Bland's rule.

    Returns (optimum, w, shadow): shadow is the optimal solution of the dual
    problem (min b.y, A^T y >= c, y >= 0), read off the bottom row under the
    slack columns."""
    m, n = len(A), len(c)
    T = [[Fraction(A[i][j]) for j in range(n)]
         + [Fraction(1) if k == i else Fraction(0) for k in range(m)]
         + [Fraction(b[i])] for i in range(m)]
    obj = [Fraction(-x) for x in c] + [Fraction(0)] * m + [Fraction(0)]
    basis = [n + i for i in range(m)]
    while True:
        j = next((j for j in range(n + m) if obj[j] < 0), None)
        if j is None:
            break
        piv, piv_row = None, None
        for i in range(m):
            if T[i][j] > 0:
                r = T[i][-1] / T[i][j]
                if piv is None or r < piv or (r == piv and basis[i] < basis[piv_row]):
                    piv, piv_row = r, i
        if piv is None:
            raise ValueError("unbounded")
        i = piv_row
        pv = T[i][j]
        T[i] = [x / pv for x in T[i]]
        for i2 in range(m):
            if i2 != i and T[i2][j] != 0:
                f = T[i2][j]
                T[i2] = [a - f * bb for a, bb in zip(T[i2], T[i])]
        if obj[j] != 0:
            f = obj[j]
            obj = [a - f * bb for a, bb in zip(obj, T[i])]
        basis[i] = j
    w = [Fraction(0)] * n
    for i in range(m):
        if basis[i] < n:
            w[basis[i]] = T[i][-1]
    shadow = [obj[n + k] for k in range(m)]
    return obj[-1], w, shadow

def lp_exact(sizes):
    """Exact configuration-LP value plus verified primal/dual certificates.

    Returns (value, dual_w, primal_x): dual_w has w_i >= 0 and
    sum_{i in p} w_i <= 1 on every pattern; primal_x is a list of
    (pattern, x_p) with x_p > 0 covering every item at least once; and
    sum w_i == sum x_p == value (strong duality, checked)."""
    n = len(sizes)
    pats = maximal_patterns(sizes)
    A = [[Fraction(1) if i in p else Fraction(0) for i in range(n)] for p in pats]
    val, w, shadow = simplex_max([Fraction(1)] * n, A, [Fraction(1)] * len(pats))
    x = [(pats[k], v) for k, v in enumerate(shadow) if v > 0]
    for p in all_patterns(sizes):
        assert sum(w[i] for i in p) <= 1, ("dual infeasible", p)
    assert all(v >= 0 for v in w)
    for i in range(n):
        assert sum(v for p, v in x if i in p) >= 1, ("primal infeasible", i)
    assert sum(v for _, v in x) == val == sum(w), "duality gap"
    assert val >= sum(sizes), "LP below volume"
    return val, w, x

# ---------------------------------------------------------------- exact OPT

def opt_exact(sizes):
    order = sorted(range(len(sizes)), key=lambda i: -sizes[i])
    s = [sizes[i] for i in order]
    best = [len(sizes) + 1]
    best_asg = [None]
    loads = []

    def dfs(i, asg):
        if len(loads) >= best[0]:
            return
        if i == len(s):
            best[0] = len(loads)
            best_asg[0] = list(asg)
            return
        seen = set()
        for b in range(len(loads)):
            if loads[b] + s[i] <= 1 and loads[b] not in seen:
                seen.add(loads[b])
                loads[b] += s[i]
                dfs(i + 1, asg + [b])
                loads[b] -= s[i]
        loads.append(s[i])
        dfs(i + 1, asg + [len(loads) - 1])
        loads.pop()

    dfs(0, [])
    bins = [[] for _ in range(best[0])]
    for pos, b in enumerate(best_asg[0]):
        bins[b].append(order[pos])
    return best[0], bins

def ceil_frac(q):
    return -((-q.numerator) // q.denominator)

# ---------------------------------------------------------------- reporting

def analyze(name, sizes, show_certs=True):
    lp, w, x = lp_exact(sizes)
    opt, bins = opt_exact(sizes)
    vol = sum(sizes)
    irup = opt <= ceil_frac(lp)
    mirup = opt <= ceil_frac(lp) + 1
    print(f"[{name}] n={len(sizes)} vol={vol}={float(vol):.4f} "
          f"LP={lp}={float(lp):.4f} ceil(LP)={ceil_frac(lp)} OPT={opt} "
          f"IRUP={'YES' if irup else 'NO'} MIRUP={'YES' if mirup else 'NO'} "
          f"patterns={len(all_patterns(sizes))} maximal={len(maximal_patterns(sizes))}")
    if show_certs:
        print(f"  packing ({opt} bins): "
              + "; ".join("{" + ",".join(str(i) for i in sorted(b)) + "}" for b in bins))
        print(f"  dual w = {[str(v) for v in w]}  (sum {sum(w)})")
        for p, v in x:
            print(f"  primal {v} * {list(p)}")
    return lp, opt

def main():
    random.seed(20260905)

    print("=== 1. uniform sizes (special case a) ===")
    for c, n in [(Fraction(1, 3), 7), (Fraction(2, 5), 9), (Fraction(17, 50), 5),
                 (Fraction(1, 2), 6), (Fraction(3, 4), 5)]:
        m = 1
        while (m + 1) * c <= 1:
            m += 1
        lp, opt = analyze(f"uniform c={c} n={n}", [c] * n, show_certs=False)
        assert opt == ceil_frac(Fraction(n, m)) and lp == Fraction(n, m)
        print(f"  OK: OPT = ceil(n/m) = {opt}, LP = n/m = {lp} (m={m})")

    print("\n=== 2. small instances (special case b) ===")
    analyze("I1 (1/2,1/3,1/3,1/4,1/4)",
            [Fraction(1, 2), Fraction(1, 3), Fraction(1, 3), Fraction(1, 4), Fraction(1, 4)])
    analyze("I2 (7/12 x4)", [Fraction(7, 12)] * 4)
    analyze("I3 (1/2,1/2,1/3,1/3,1/3)",
            [Fraction(1, 2), Fraction(1, 2), Fraction(1, 3), Fraction(1, 3), Fraction(1, 3)])

    print("\n=== 3. MIRUP on random instances ===")
    bad = nonirup = 0
    for _ in range(3000):
        n = random.randint(2, 6)
        sizes = [Fraction(random.randint(1, 12), 12) for _ in range(n)]
        lp, _, _ = lp_exact(sizes)
        opt, _ = opt_exact(sizes)
        if opt > ceil_frac(lp) + 1:
            bad += 1
            print("  MIRUP VIOLATION:", sizes, lp, opt)
        if opt > ceil_frac(lp):
            nonirup += 1
    print(f"  n<=6, 3000 random instances (sizes k/12): "
          f"MIRUP violations = {bad}, IRUP failures = {nonirup}")
    nonirup = 0
    for _ in range(2000):
        n = random.randint(7, 9)
        sizes = [Fraction(random.randint(2, 17), 18) for _ in range(n)]
        lp, _, _ = lp_exact(sizes)
        opt, _ = opt_exact(sizes)
        assert opt <= ceil_frac(lp) + 1, ("MIRUP VIOLATION", sizes)
        if opt > ceil_frac(lp):
            nonirup += 1
    print(f"  n in 7..9, 2000 random instances (sizes k/18): IRUP failures = {nonirup} "
          "(consistent with Kartak et al. 2015: all instances with <= 9 items are IRUP)")

    print("\n=== 4. tightness instance (special case c) ===")
    analyze("instC (4,6,6,9,16,29,32,37,40,62)/81",
            [Fraction(v, 81) for v in [4, 6, 6, 9, 16, 29, 32, 37, 40, 62]])

if __name__ == "__main__":
    main()
