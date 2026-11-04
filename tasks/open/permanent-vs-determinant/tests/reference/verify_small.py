#!/usr/bin/env python3
"""Small-instance numerical checks for the permanent-vs-determinant task package (author-side; not part of scoring).

Check three facts:
  V1. Explicit 2x2 representation at n=2: det [[X00, X01], [-X10, X11]] = perm_2.
  V2. The independently derived Grenet construction is numerically correct for n=2,3,4:
      Indices are the nonempty subsets of [n]; M[S][S]=1 when S is not the full set;
      M[S∪{j}][S] = -X(|S|+1, j) (growth edge); M[{j}][[n]] = +X(1, j) (closing edge).
      Assert det M = perm_n (at n=4 the matrix is 15x15, confirming the 2^n-1 size-bound construction has the intended form).
  V3. Degree lower-bound sanity check: total degree of perm_n is n (random assignments plus a homogeneity check).

Represent polynomials by dicts: monomial (sorted, duplicate-free tuple of variable exponents; degree equals tuple length) -> integer coefficient.
Every variable has degree at most 1 in this construction, so frozenset is used as the key.
"""
from itertools import permutations


# ---- Small polynomial algebra (sparse multivariate polynomials with integer coefficients) ----
# Representation: {tuple(sorted(var...)): coeff} (multiset; length = degree); variables are pairs (i, j).

def pvar(v):
    return {(v,): 1}

def pconst(c):
    return {(): c} if c else {}

def padd(p, q):
    r = dict(p)
    for m, c in q.items():
        r[m] = r.get(m, 0) + c
        if r[m] == 0:
            del r[m]
    return r

def pmul(p, q):
    r = {}
    for m1, c1 in p.items():
        for m2, c2 in q.items():
            m = tuple(sorted(m1 + m2))
            r[m] = r.get(m, 0) + c1 * c2
            if r[m] == 0:
                del r[m]
    return r

def pneg(p):
    return {m: -c for m, c in p.items()}

def pdet(M):
    """Leibniz formula, including signs."""
    n = len(M)
    total = {}
    for perm in permutations(range(n)):
        # sign of permutation
        inv = sum(1 for i in range(n) for j in range(i + 1, n) if perm[i] > perm[j])
        term = pconst((-1) ** inv)
        for i in range(n):
            term = pmul(term, M[perm[i]][i])
        total = padd(total, term)
    return total

def perm_poly(n):
    """perm_n = sum_sigma prod_i X(i, sigma(i))，0-based。"""
    total = {}
    for sigma in permutations(range(n)):
        term = pconst(1)
        for i in range(n):
            term = pmul(term, pvar((i, sigma[i])))
        total = padd(total, term)
    return total


def pdet_numeric(M, assign):
    """Substitute integer values from assign into the matrix entries (small polynomials), then compute the determinant exactly using the Bareiss algorithm."""
    n = len(M)
    def ev(p):
        total = 0
        for mono, c in p.items():
            v = c
            for var in mono:
                v *= assign[var]
            total += v
        return total
    A = [[ev(M[i][j]) for j in range(n)] for i in range(n)]
    # Fraction-free Gaussian elimination (Bareiss)
    sign = 1
    prev = 1
    for k in range(n - 1):
        if A[k][k] == 0:
            sw = next((r for r in range(k + 1, n) if A[r][k] != 0), None)
            assert sw is not None, "Matrix is singular (this should not happen)"
            A[k], A[sw] = A[sw], A[k]
            sign = -sign
        for i in range(k + 1, n):
            for j in range(k + 1, n):
                A[i][j] = (A[i][j] * A[k][k] - A[i][k] * A[k][j]) // prev
        prev = A[k][k]
        for i in range(k + 1, n):
            A[i][k] = 0
    return sign * A[n - 1][n - 1]

def perm_numeric(n, assign):
    total = 0
    for sigma in permutations(range(n)):
        v = 1
        for i in range(n):
            v *= assign[(i, sigma[i])]
        total += v
    return total

def grenet_matrix(n):
    """Return (size, M), where M is a 2^n-1 square matrix whose entries are small polynomials (affine-linear forms)."""
    subsets = [s for k in range(1, n + 1)
               for s in __import__('itertools').combinations(range(n), k)]
    idx = {s: i for i, s in enumerate(subsets)}
    full = tuple(range(n))
    m = len(subsets)
    assert m == 2 ** n - 1
    Z = {}
    M = [[Z for _ in range(m)] for _ in range(m)]
    for s in subsets:
        S = set(s)
        i = idx[s]
        if s != full:
            M[i][i] = pconst(1)                       # self-loop
            for j in range(n):
                if j not in S:
                    t = tuple(sorted(S | {j}))
                    M[idx[t]][i] = pneg(pvar((len(s), j)))   # growth edge: -X(|S|+1, j) (1-based row index)
        else:
            for j in range(n):
                M[idx[(j,)]][i] = pvar((0, j))        # closing edge: +X(1, j)
    return m, M


def check_affine(M):
    for row in M:
        for e in row:
            deg = max((len(m) for m in e), default=0)
            assert deg <= 1, f"matrix-entry degree {deg} > 1"


def main():
    # V1: explicit representation showing dc(perm_2) <= 2
    A2 = [[pvar((0, 0)), pvar((0, 1))],
          [pneg(pvar((1, 0))), pvar((1, 1))]]
    d2 = pdet(A2)
    p2 = perm_poly(2)
    assert d2 == p2, f"V1 failed: det={d2} perm={p2}"
    print("V1 passed: det [[X00,X01],[-X10,X11]] = perm_2 = X00*X11 + X01*X10")

    # V2: Grenet construction: symbolic verification for n=2,3; numerical verification on random integer assignments for n=3,4
    import random
    rng = random.Random(20260905)
    for n in (2, 3):
        m, M = grenet_matrix(n)
        check_affine(M)
        d = pdet(M)
        p = perm_poly(n)
        assert d == p, (f"V2 failed at n={n}: det and perm disagree\n"
                        f"det-only={ {k: v for k, v in d.items() if k not in p} }\n"
                        f"perm-only={ {k: v for k, v in p.items() if k not in d} }")
        print(f"V2 passed (symbolic): n={n}, size 2^{n}-1 = {m}, det M = perm_{n} ({len(d)} monomials)")
    for n in (3, 4):
        m, M = grenet_matrix(n)
        check_affine(M)
        for trial in range(3):
            assign = {(i, j): rng.randint(-9, 9) for i in range(n) for j in range(n)}
            dv = pdet_numeric(M, assign)
            pv = perm_numeric(n, assign)
            assert dv == pv, f"V2 numerical check failed at n={n}, trial={trial}: det={dv} perm={pv}"
        print(f"V2 passed (numeric, 3 random assignments): n={n}, size 2^{n}-1 = {m}")

    # V3: total degree of perm_n is n (each monomial has degree n, all coefficients are +1, with no cancellation)
    for n in (2, 3, 4):
        p = perm_poly(n)
        assert all(len(m) == n and c == 1 for m, c in p.items())
        import math
        assert len(p) == math.factorial(n)
        print(f"V3 passed: perm_{n} is a sum of {len(p)} monomials, each of degree {n} (total degree = {n})")

    print("\nAll small-instance checks passed.")


if __name__ == "__main__":
    main()
