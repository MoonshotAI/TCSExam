#!/usr/bin/env python3
"""Small-instance numerical checks for explicit-rigid-matrix.
Covers:
  S1  All 2x2 minors of H₃ (the 3x3 Hilbert matrix over Q; special case b assumes all are nonzero),
      and the exact value of R_{H₃}(1) over Q (enumerate supports and solve exactly using the rank-one form u vᵀ).
  S2  Constructive numerical examples for identity-matrix rigidity R_{I_n}(r) = n - r, for several n and ε.
  S3  Sampling for special case c: use a fixed seed to sample uniform {0,1} 4x4 matrices
      until all 3x3 minors are nonzero; record the matrix, number of attempts, and overall frequency.
  S4  Exact samples of rigidity for random matrices over GF(2): for n=4/5, enumerate all matrices B of rank <= r,
      compute R_M(r) = min_B dist(M, B) exactly for random M, and report the distribution.
"""
import itertools
import random
from fractions import Fraction as F

# ---------- Small utilities ----------

def det_frac(M):
    """Exact determinant using Gaussian elimination over Fractions."""
    n = len(M)
    A = [row[:] for row in M]
    d = F(1)
    for col in range(n):
        p = next((r for r in range(col, n) if A[r][col] != 0), None)
        if p is None:
            return F(0)
        if p != col:
            A[col], A[p] = A[p], A[col]
            d = -d
        d *= A[col][col]
        inv = 1 / A[col][col]
        for r in range(col + 1, n):
            factor = A[r][col] * inv
            A[r] = [a - factor * b for a, b in zip(A[r], A[col])]
    return d


def minors(M, k):
    """List of all k x k minors as ((rows, cols), det) entries."""
    n = len(M)
    out = []
    for rows in itertools.combinations(range(n), k):
        for cols in itertools.combinations(range(n), k):
            sub = [[M[i][j] for j in cols] for i in rows]
            out.append((rows, cols, det_frac(sub)))
    return out


def rank_leq_1_witness(H, S):
    """Check whether there is a matrix B of rank <= 1 matching H entrywise outside S; S is a set of (i,j) pairs.
    Return (feasible?, u, v), where B = u v^T. Every rank-1 matrix has this form; rank 0 is included as a special case."""
    n = len(H)
    S = set(S)
    # Constraint graph: for each position (i,j) outside S, u_i * v_j = H[i][j]
    # K_{n,n} remains connected after removing at most 2 edges when n>=3; propagate from u_0 = 1
    u = [None] * n
    v = [None] * n
    u[0] = F(1)
    changed = True
    while changed:
        changed = False
        for i in range(n):
            for j in range(n):
                if (i, j) in S or H[i][j] == 0:
                    continue
                if u[i] is not None and v[j] is None:
                    v[j] = H[i][j] / u[i]
                    changed = True
                elif v[j] is not None and u[i] is None:
                    u[i] = H[i][j] / v[j]
                    changed = True
    for i in range(n):
        for j in range(n):
            if (i, j) in S:
                continue
            if u[i] is None or v[j] is None or u[i] * v[j] != H[i][j]:
                return (False, None, None)
    return (True, u, v)


def rigidity_rank1(H):
    """Exact value of R_H(1): the minimum |S| for which some B of rank <= 1 agrees with H outside S."""
    n = len(H)
    pos = [(i, j) for i in range(n) for j in range(n)]
    for s in range(0, n * n + 1):
        for S in itertools.combinations(pos, s):
            ok, u, v = rank_leq_1_witness(H, S)
            if ok:
                return s, S, u, v
    return None


# ---------- S1: H3 ----------
print("=" * 70)
print("S1: 3x3 Hilbert matrix (over Q)")
H3 = [[F(1) / (i + j + 1) for j in range(3)] for i in range(3)]
for row in H3:
    print("  ", [str(x) for x in row])
print("det(H3) =", det_frac(H3))
m2 = minors(H3, 2)
print("All %d 2x2 minors:" % len(m2))
for rows, cols, d in m2:
    print(f"  rows{rows} cols{cols}: det = {d}")
print("Number of nonzero minors:", sum(1 for _, _, d in m2 if d != 0), "/", len(m2))

r, S, u, v = rigidity_rank1(H3)
print(f"R_{{H3}}(1) = {r}  (witness support S = {S})")
print("  u =", [str(x) for x in u])
print("  v =", [str(x) for x in v])
B = [[u[i] * v[j] for j in range(3)] for i in range(3)]
diff = [(i, j) for i in range(3) for j in range(3) if B[i][j] != H3[i][j]]
print("  Positions where B = u v^T differs from H3:", diff, " count:", len(diff))
rk1minors = [d for _, _, d in minors(B, 2)]
print("  Are all 2x2 minors of B zero:", all(d == 0 for d in rk1minors))

# ---------- S2: Identity matrix ----------
print("=" * 70)
print("S2: Rigidity R(r) = n - r for identity matrix I_n (constructive demonstration)")
for n, eps_num, eps_den in [(8, 1, 2), (16, 1, 4)]:
    eps = F(eps_num, eps_den)
    r = int(eps * n)  # floor
    changed = n - r
    print(f"  n={n}: set {changed} diagonal entries to 0; rank becomes {r} = floor(eps*n), eps={eps}")

# ---------- S3: Sample 4x4 {0,1} matrices (over Q) ----------
print("=" * 70)
print("S3: Sampling for special case c (seed 20260904)")
rng = random.Random(20260904)


def all_kminors_nonzero(M, k):
    return all(d != 0 for _, _, d in minors(M, k))


trials = 0
found = None
while True:
    trials += 1
    M = [[F(rng.randrange(2)) for _ in range(4)] for _ in range(4)]
    if all_kminors_nonzero(M, 3):
        found = M
        break
print(f"Found a sample on attempt {trials} (all 3x3 minors nonzero):")
for row in found:
    print("  ", [int(x) for x in row])
N = 10000
rng2 = random.Random(1)
hits = 0
for _ in range(N):
    M = [[F(rng2.randrange(2)) for _ in range(4)] for _ in range(4)]
    if all_kminors_nonzero(M, 3):
        hits += 1
print(f"Estimated frequency: among {N} random {{0,1}} 4x4 matrices, {hits} have all 3x3 minors nonzero"
      f" ({hits / N:.4f})")

# ---------- S4: Exact rigidity samples over GF(2) ----------
print("=" * 70)
print("S4: Exact rigidity values for random matrices over GF(2) (enumerate all B of rank <= r)")


def gf2_rank(x, n):
    rows = [(x >> (i * n)) & ((1 << n) - 1) for i in range(n)]
    rk = 0
    for col in range(n):
        p = next((i for i in range(rk, n) if (rows[i] >> col) & 1), None)
        if p is None:
            continue
        rows[rk], rows[p] = rows[p], rows[rk]
        for i in range(n):
            if i != rk and ((rows[i] >> col) & 1):
                rows[i] ^= rows[rk]
        rk += 1
    return rk


def low_rank_matrices(n, r):
    """All n x n GF(2) matrices of rank <= r (represented as n*n-bit integers)."""
    if n == 4:
        return [x for x in range(1 << 16) if gf2_rank(x, n) <= r]
    # n == 5: enumerate u v^T plus the general structure (rank<=2 from a column-space basis and coefficients)
    # General method: enumerate (A, B) with A: n x r and B: r x n; M = A·B
    seen = set()
    cols = list(range(1 << n))
    for Abits in itertools.product(cols, repeat=r):
        for Bbits in itertools.product(cols, repeat=r):
            x = 0
            for i in range(n):
                row = 0
                for j in range(n):
                    acc = 0
                    for k in range(r):
                        acc ^= ((Abits[k] >> i) & 1) & ((Bbits[k] >> j) & 1)
                    row |= acc << j
                x |= row << (i * n)
            seen.add(x)
    return list(seen)


def rigidity_exact(M, n, r, lowrank):
    return min(bin(M ^ B).count("1") for B in lowrank)


for n, r, nsamp in [(4, 1, 300), (4, 2, 300), (5, 2, 40)]:
    low = low_rank_matrices(n, r)
    rng3 = random.Random(7)
    dist = {}
    for _ in range(nsamp):
        M = rng3.randrange(1 << (n * n))
        val = rigidity_exact(M, n, r, low)
        dist[val] = dist.get(val, 0) + 1
    print(f"  n={n}, r={r}: there are {len(low)} matrices of rank <=r;"
          f" distribution of R_M(r) for {nsamp} random M: {dict(sorted(dist.items()))}")
