#!/usr/bin/env python3
"""Small-example numeric checks for the log-rank-conjecture task package.

Pure Python (exact rational arithmetic, no dependencies). Verifies the
numbers the three special-case checkpoints assert:

  (a) EQ on Fin 4: communication matrix = identity, rank 4, D <= 3,
      3 <= (log2 4)^2.
  (b) ip2 (two-bit inner product): rank of the 4x4 0/1 matrix is 3,
      D <= 3 <= (log2 3)^3.
  (c) rank-1 conjunctions u && v: D <= 2 while log2(rank) = 0 when the
      rank is exactly 1 -- the reason the conjecture needs 2 <= rank.

Also tabulates EQ_n / IP_n ranks for small n as a sanity sweep.
"""

from fractions import Fraction
from math import log2, ceil


def rank(rows):
    """Exact rank of a matrix over Q (list of lists of ints/Fractions)."""
    m = [[Fraction(x) for x in row] for row in rows]
    nr, nc = len(m), len(m[0])
    r = 0
    for c in range(nc):
        piv = next((i for i in range(r, nr) if m[i][c] != 0), None)
        if piv is None:
            continue
        m[r], m[piv] = m[piv], m[r]
        for i in range(nr):
            if i != r and m[i][c] != 0:
                f = m[i][c] / m[r][c]
                m[i] = [a - f * b for a, b in zip(m[i], m[r])]
        r += 1
    return r


def mat(f, xs, ys):
    return [[1 if f(x, y) else 0 for y in ys] for x in xs]


def eq(x, y):
    return x == y


def ip(x, y):
    return sum(a * b for a, b in zip(x, y)) % 2 == 1


def strings(n):
    return [tuple((k >> i) & 1 for i in range(n)) for k in range(2 ** n)]


def report(name, f, xs, ys, d_upper):
    A = mat(f, xs, ys)
    r = rank(A)
    lr = log2(r) if r > 0 else 0.0
    line = f"{name}: size {len(xs)}x{len(ys)}, rank {r}, D <= {d_upper}"
    if r >= 2:
        # least real c with d_upper <= (1 + log2 r)^c
        if d_upper <= 1 + lr:
            c_min = 1.0
        else:
            import math
            c_min = math.log(d_upper) / math.log(1 + lr)
        line += f", log2 rank {lr:.4f}, min c for (1+log2 r)^c {c_min:.4f}"
    print(line)
    return r


print("== EQ_n (identity matrices) ==")
for n in range(1, 5):
    xs = list(range(2 ** n))
    r = report(f"EQ_{n}", eq, xs, xs, n + 1)
    assert r == 2 ** n, f"EQ_{n} rank {r} != {2**n}"

print("\n== IP_n (inner product mod 2) ==")
for n in range(1, 4):
    xs = strings(n)
    r = report(f"IP_{n}", ip, xs, xs, n + 1)
    assert r == 2 ** n - 1, f"IP_{n} rank {r} != {2**n - 1}"

print("\n== checkpoint (a): EQ on Fin 4 ==")
xs = list(range(4))
r = rank(mat(eq, xs, xs))
assert r == 4
assert 3 <= log2(4) ** 2, "3 <= (log2 4)^2 fails"
print(f"rank = {r}, D <= 3, (log2 4)^2 = {log2(4)**2:.4f}: 3 <= {log2(4)**2:.4f} OK")

print("\n== checkpoint (b): ip2 on (Fin 2 -> Fin 2) ==")
xs = strings(2)
A = mat(ip, xs, xs)
for row in A:
    print("  ", row)
r = rank(A)
assert r == 3, f"ip2 rank {r} != 3"
assert 3 <= log2(3) ** 3, "3 <= (log2 3)^3 fails"
print(f"rank = {r}, D <= 3, (log2 3)^3 = {log2(3)**3:.4f}: 3 <= {log2(3)**3:.4f} OK")

print("\n== checkpoint (c) and the rank-1 degeneracy ==")
# f(x,y) = u(x) && v(y) with u, v nonconstant: rank exactly 1, D = 2,
# log2 rank = 0 -> no pure power of log2 rank can bound D here.
u = [1, 1, 0, 0]
v = [0, 1, 0, 1]
A = [[u[x] * v[y] for y in range(4)] for x in range(4)]
for row in A:
    print("  ", row)
r = rank(A)
assert r == 1
print(f"rank = {r}, log2 rank = 0, D = 2 (both bits are needed): "
      "2 <= 0^c is false for every c -- hence the 2 <= rank hypothesis")

print("\n== why the statement uses 1 + log2 rank (EQ on one bit) ==")
# EQ_1: communication matrix I_2, rank 2, D = 2.
# Pure power form: 2 <= (log2 2)^c = 1 is false for EVERY c.
# The shipped statement: 2 <= (1 + log2 2)^c = 2^c, which holds for c >= 1.
xs = list(range(2))
r = rank(mat(eq, xs, xs))
assert r == 2
assert all(2 > log2(2) ** c for c in (0.5, 1, 2, 10)), "pure-power check"
assert 2 <= (1 + log2(2)) ** 1, "(1+log2 r)^c with c=1"
print(f"EQ_1: rank = {r}, D = 2; (log2 2)^c = 1 < 2 for all c (pure power "
      "impossible); 2 <= (1 + log2 2)^c = 2^c holds for c >= 1 -- "
      "the shipped statement absorbs this with 1 + log2 rank")

print("\nAll small-example checks passed.")
