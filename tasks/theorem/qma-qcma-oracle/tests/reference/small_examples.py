#!/usr/bin/env python3
"""Executable small examples for lean-qma-qcma-oracle (fidelity check 2/3).

Re-implements the task's definition-layer objects in numpy and checks the
checkpoint statements' predicate behavior on small instances. Every check
prints one EXAMPLE line; any mismatch aborts.
"""
import numpy as np
from itertools import product

FAIL = []

def check(name, cond, detail=""):
    print(f"EXAMPLE {name}: {'ok' if cond else 'FAIL'} {detail}")
    if not cond:
        FAIL.append(name)

def bits(n):
    return [np.array(list(v), dtype=int) for v in product([0, 1], repeat=n)]

def dot2(x, y):
    return int(np.dot(x, y) % 2)

def sign(x, y):
    return (-1.0) ** dot2(x, y)

def hadamard(n):
    N = 2 ** n
    H = np.zeros((N, N))
    B = bits(n)
    for i, x in enumerate(B):
        for j, y in enumerate(B):
            H[i, j] = sign(x, y) / np.sqrt(N)
    return H

def proj(f):
    """f: indicator array of length 2^n."""
    return np.diag(f.astype(float))

# ---- E1: gamma_y(S) on a concrete example (eq. 28) ---------------------------
# n = 2, S = [00, 01] (as a list), y = 10.
n = 2
B = bits(n)
S = [B[0], B[1]]  # 00, 01
y = np.array([1, 0])
ell = 2
gamma_y = (sum(sign(y, s) for s in S)) ** 2 / ell
# direct: sign(10,00)=1, sign(10,01)=1 -> (2)^2/2 = 2
check("E1-gamma", abs(gamma_y - 2.0) < 1e-12, f"gamma={gamma_y}")
# y = 01: sign(01,00)=1, sign(01,01)=-1 -> 0
y2 = np.array([0, 1])
gamma_y2 = (sum(sign(y2, s) for s in S)) ** 2 / ell
check("E1-gamma-zero", abs(gamma_y2 - 0.0) < 1e-12, f"gamma={gamma_y2}")
# gamma_0 = ell always (y = 00)
g0 = (sum(sign(np.zeros(n, dtype=int), s) for s in S)) ** 2 / ell
check("E1-gamma0", abs(g0 - ell) < 1e-12, f"gamma0={g0}")

# ---- E2: sfVal on n=1, S=U={0} ----------------------------------------------
n = 2
H1 = hadamard(1)
P0 = proj(np.array([1, 0]))
M = P0 @ H1 @ P0  # Pi_U H Pi_S with S=U={0}
sfn = np.linalg.norm(M, 2) ** 2
# M = [[1/sqrt(2),0],[0,0]] -> op norm^2 = 1/2
check("E2-sfVal-half", abs(sfn - 0.5) < 1e-12, f"sfVal={sfn}")

# ---- E3: empty oracle -> 0 ----------------------------------------------------
f_empty = np.zeros(4)
check("E3-sfVal-empty", np.linalg.norm(proj(np.ones(4)) @ hadamard(2) @ proj(f_empty), 2) ** 2 == 0.0)

# ---- E4: sfVal in [0,1] on random small pairs ---------------------------------
rng = np.random.default_rng(7)
ok = True
for _ in range(200):
    f = (rng.random(4) < 0.5)
    g = (rng.random(4) < 0.5)
    v = np.linalg.norm(proj(g.astype(float)) @ hadamard(2) @ proj(f.astype(float)), 2) ** 2
    ok = ok and (-1e-12 <= v <= 1 + 1e-12)
check("E4-sfVal-range", ok)

# ---- E5: Rayleigh form ||Pi_U H Pi_S psi||^2 = <psi, M psi> --------------------
n = 2
H = hadamard(n)
f = np.array([1, 0, 1, 0], dtype=float)
g = np.array([0, 1, 1, 0], dtype=float)
Fr = proj(g) @ H @ proj(f)
Msf = proj(f) @ H @ proj(g) @ H @ proj(f)
psi = rng.normal(size=4)
psi = psi / np.linalg.norm(psi)
lhs = np.linalg.norm(Fr @ psi) ** 2
rhs = psi @ Msf @ psi
check("E5-rayleigh", abs(lhs - rhs) < 1e-10, f"{lhs} vs {rhs}")
# and the max over the unit sphere equals the top eigenvalue of Msf (PSD)
ev = np.linalg.eigvalsh(Msf)
check("E5-max-eig", abs(ev[-1] - np.linalg.norm(Fr, 2) ** 2) < 1e-10)

# ---- E6: uWeight normalizes to 1 over U ---------------------------------------
def gamma_vec(S_list, y):
    return (sum(sign(y, s) for s in S_list)) ** 2 / len(S_list)

def u_weight(kappa, S_list, U_bits, n):
    w = 1.0
    for i, y in enumerate(bits(n)):
        if np.all(y == 0):
            w *= 0.0 if U_bits[i] else 1.0
        else:
            p = 1 - np.exp(-kappa * gamma_vec(S_list, y)) / 2
            w *= p if U_bits[i] else (1 - p)
    return w

n = 2
S_list = [bits(2)[0], bits(2)[3]]  # 00, 11
tot = sum(u_weight(0.1, S_list, np.array(u), 2) for u in product([0, 1], repeat=4))
check("E6-uWeight-norm", abs(tot - 1.0) < 1e-12, f"total={tot}")

# ---- E7/E8: good-list predicate on concrete lists ------------------------------
def trivial_eq(idxs):
    from collections import Counter
    c = Counter(idxs)
    return all(v % 2 == 0 for v in c.values())

def is_good(S_list, n):
    # 2-term: no i != j with S_i = S_j
    for i in range(len(S_list)):
        for j in range(len(S_list)):
            if i != j and np.all((np.array(S_list[i]) + np.array(S_list[j])) % 2 == 0):
                return False
    # 4-term and 6-term
    from itertools import product as iproduct
    for k in (4, 6):
        for idxs in iproduct(range(len(S_list)), repeat=k):
            x = np.zeros(n, dtype=int)
            for t in idxs:
                x = (x + np.array(S_list[t])) % 2
            if np.all(x == 0) and not trivial_eq(idxs):
                return False
    return True

S_good = [bits(3)[0], bits(3)[1], bits(3)[2]]  # 000,001,010
S_bad = [bits(3)[0], bits(3)[0]]              # repeated point: bad (2-term nontrivial)
check("E7-good-yes", is_good(S_good, 3))
check("E7-good-no-repeat", not is_good(S_bad, 3))
S_bad4 = [bits(3)[1], bits(3)[2], bits(3)[3], bits(3)[0]]
# 001 xor 010 xor 011 = 000 -> 3-term... need 4-term: 001^010^011^000 = 000? 001^010=011, 011^011=000 -> xor of first three is 000 then xor 000 = 000; indices all distinct -> nontrivial 4-term equation
x = np.zeros(3, dtype=int)
for s in S_bad4:
    x = (x + np.array(s)) % 2
check("E8-nontrivial-4term", np.all(x == 0) and not trivial_eq([0, 1, 2, 3]))
check("E8-good-no-4term", not is_good(S_bad4, 3))

# ---- E9/E10/E11: the sandwich on a small good list ------------------------------
n = 3
N = 2 ** n
H = hadamard(n)
kappa = 1.0
S_list = [bits(3)[0], bits(3)[1], bits(3)[2], bits(3)[4]]  # 000,001,010,100 good
ell = len(S_list)
assert is_good(S_list, 3) and 3 <= kappa * ell
gam = np.array([gamma_vec(S_list, y) for y in bits(n)])
diagB = 0.5 + kappa * gam / 2
diagA = 0.5 + kappa * gam / 2 - kappa ** 2 * gam ** 2 / 4
p = np.array([0.0 if np.all(y == 0) else 1 - np.exp(-kappa * g) / 2 for y, g in zip(bits(n), gam)])
Amat = H @ np.diag(diagA) @ H
Bmat = H @ np.diag(diagB) @ H
Mmat = H @ np.diag(p) @ H
ev1 = np.linalg.eigvalsh(Mmat - Amat)
ev2 = np.linalg.eigvalsh(Bmat - Mmat)
check("E9-sandwich-A", ev1[0] > -1e-10, f"min eig {ev1[0]}")
check("E9-sandwich-B", ev2[0] > -1e-10, f"min eig {ev2[0]}")
# y=0 diagonal check: 1/2 + k*l/2 - k^2 l^2/4 <= 0 requires k*l >= 1+sqrt(3)
d0 = 0.5 + kappa * ell / 2 - kappa ** 2 * ell ** 2 / 4
check("E9-y0-lower-sign", d0 <= 0, f"d0={d0}, k*l={kappa*ell} >= 1+sqrt(3)={1+3**0.5:.3f}")

# E10: B Rayleigh upper bound on Delta-supported vectors
supp = sorted({tuple(s) for s in S_list})
supp_idx = [i for i, y in enumerate(bits(n)) if tuple(y) in supp]
for Delta in [supp_idx[:2], supp_idx]:
    ok = True
    for _ in range(300):
        psi = rng.normal(size=N)
        mask = np.zeros(N); mask[Delta] = 1.0
        psi = psi * mask
        if np.linalg.norm(psi) < 1e-9:
            continue
        psi = psi / np.linalg.norm(psi)
        val = psi @ Bmat @ psi
        ok = ok and val <= (1 + kappa) / 2 + kappa * len(Delta) / ell + 1e-9
    check(f"E10-B-bound-|D|={len(Delta)}", ok)

# E11: A's |S>-Rayleigh lower bound (eq. 44c)
unif = np.zeros(N)
for idx in supp_idx:
    unif[idx] = 1.0 / np.sqrt(ell)
valA = unif @ Amat @ unif
rhs = 0.5 + 3 * kappa / 2 - 15 * kappa ** 2 / 4 - 5 * kappa / ell
# explicit form from eqs. (43): id coeff + rank-1 coeff
idc = 0.5 + kappa * (0.5 - 1 / ell) + kappa ** 2 * (-3 / 4 + 7 / (2 * ell) - 4 / ell ** 2)
r1 = kappa - 3 * kappa ** 2 + 4 * kappa ** 2 / ell
valA_form = idc + r1
check("E11-A-rayleigh-form", abs(valA - valA_form) < 1e-9, f"{valA} vs {valA_form}")
check("E11-A-rayleigh-44c", valA >= rhs - 1e-12 and abs(valA - (0.5 + 3 * kappa / 2 - kappa / ell - 15 * kappa ** 2 / 4 + 15 * kappa ** 2 / (2 * ell) - 4 * kappa ** 2 / ell ** 2)) < 1e-9,
      f"{valA} >= {rhs}")

# ---- E12: Taylor bounds 1/2+kx/2-k^2x^2/4 <= 1-e^{-kx}/2 <= 1/2+kx/2 -----------
xs = np.linspace(0, 50, 5001)
mid = 1 - np.exp(-kappa * xs) / 2
lo = 0.5 + kappa * xs / 2 - kappa ** 2 * xs ** 2 / 4
hi = 0.5 + kappa * xs / 2
check("E12-taylor", np.all(lo <= mid + 1e-12) and np.all(mid <= hi + 1e-12))

# ---- E13: the c8 asymptotic comparison (log2 scale) ------------------------------
def log2_lower(n, a):
    # log2 of (1 - 2 l^6 2^-n) * 2^-q * (36 t^2)^(-1000 q), l = 2^(n//10), t = q = a n^a
    q = float(a * n ** a)
    t = q
    exponent = 1 + 6 * (n // 10) - n  # log2 of 2 l^6 2^-n
    if exponent >= 0:
        return None
    good_log2 = np.log2(1 - 2.0 ** exponent)
    return good_log2 - q - 1000 * q * np.log2(36 * t ** 2)

def log2_upper(n, a, c=1.0):
    # log2 of the Theorem 9.1 bound with l = 2^(n//10), v = 1000 q, T = max(v t, n);
    # computed in the log domain
    log2l = float(n // 10)
    q = float(a * n ** a)
    t = q
    v = 1000.0 * q
    T = max(v * t, float(n))
    # eq. (54): 2*(4v(T^30 + v T^20) sqrt(l) / 2^(n/4))^v + ((T^4/l^(1/32))^v + e^(-5T))^2
    base1_log2 = (np.log2(4 * v)
                  + 30 * np.log2(T)
                  + np.log1p(2.0 ** (np.log2(v) - 10 * np.log2(T))) / np.log(2)
                  + 0.5 * log2l - n / 4)
    lt1 = 1 + v * base1_log2  # leading factor 2
    lt2 = 2 * v * (4 * np.log2(T) - log2l / 32)
    lt3 = -10 * T / np.log(2)
    m = max(lt2, lt3)
    second = m + np.log2(2 ** (lt2 - m) + 2 ** (lt3 - m))
    big = max(lt1, second)
    return big + np.log2(2 ** (lt1 - big) + 2 ** (second - big))

for a in (1, 2):
    found = None
    for n in range(40, 300001, 40):
        ll, uu = log2_lower(n, a), log2_upper(n, a)
        if ll is not None and ll > uu:
            found = n
            break
    check(f"E13-asymptotic-a={a}", found is not None, f"first n with lower>upper: {found}")

# ---- E14: threshold window 57/100 <-> 59/100 with kappa = 1/10 -------------------
kappa = 0.1
ok = True
for l in (500, 1000, 10000):
    for v_over_l in (0.01, 0.005):
        v = v_over_l * l
        for rho in (0.0, 0.005):
            t1 = (1 + kappa) / 2 + v / l + rho
            t2 = (1 + 3 * kappa) / 2 - 15 * kappa ** 2 / 4 - 5 * kappa / l - rho
            ok = ok and (t1 <= 0.57 + 1e-12) and (t2 >= 0.59 - 1e-12) and (t1 < t2)
check("E14-threshold-window", ok)

# ---- E15: hybrid constant bookkeeping ---------------------------------------------
# 1/3 <= 2 sum_j ||Gamma psi_j|| <= 2 sqrt(t sum ||Gamma psi_j||^2)
# => (1/t) sum >= 1/(36 t^2)
t = 7
gap = 1 / 3
avg = (gap / 2) ** 2 / t
check("E15-hybrid-constant", abs(avg - 1 / (36 * t)) < 1e-15 and abs((1/t) * (1/(36*t)) - 1/(36*t**2)) < 1e-15)

print()
if FAIL:
    print("EXAMPLES FAILED:", FAIL)
    raise SystemExit(1)
print("EXAMPLES ALL: ok")
