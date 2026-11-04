#!/usr/bin/env python3
"""Numerical verification behind the FEI task's definition layer and its
three checkpoint special cases (fourier-entropy-influence).

Everything is computed from first principles, mirroring the Lean definitions
in environment/app/Task/Basic.lean one by one:

  cube point  x in {±1}^n          (Lean: Cube n := Fin n → Bool, pmOne)
  character   chi_S(x) = prod x_i  (Lean: charFn)
  coefficient f^(S) = 2^-n sum_x f(x) chi_S(x)   (Lean: fourierCoeff)
  entropy     H = sum_S f^(S)^2 * ln(1 / f^(S)^2) (Lean: fourierEntropy)
  influence   Inf_i = Pr_x[f(x) != f(x^i)]        (Lean: influence_eq_card)
  total       I(f) = sum_i Inf_i                  (Lean: totalInfluence)

Checks (mirrors tests/checkpoints.json):
  c1 dictator family   n in 1..4, every i:  H = 0, I = 1
  c2 parity family     n in 1..4:           H = 0, I = n
  c3 andTwo (low I)    n = 2:               H = 2 ln 2, I = 1
  context maj3 (symmetric, nontrivial H):   H = 2 ln 2, I = 3/2
  Parseval:            sum_S f^(S)^2 = 1 for every function above
  minterm family       f = 1 except at one point: ratio H/I grows towards
                     4 ln 2 ≈ 2.7726 as n grows — so c3's "C >= 2 ln 2" is
                     valid but not optimal; sup H/I over all f is >= 4 ln 2
                     (reported as context, not asserted beyond the trend)
  exhaustive scan n = 3 and n = 4: H(f) <= 3 * I(f) for every non-constant
                     f (a numerical consistency check of the conjecture
                     itself at these dimensions; observed max ratios
                     2.049 at n=3 and 2.358 at n=4, both attained by the
                     minterm family).

Pure stdlib; runs in a couple of seconds. Usage: python3 verify_small.py
Exit code 0 iff every check passes.
"""

import math
from itertools import product

LN2 = math.log(2.0)


def cube(n):
    """All ±1 points of the n-cube, lexicographic with +1 first."""
    return list(product([1.0, -1.0], repeat=n))


def char_fn(S, x):
    """chi_S(x) = product of x_i over i in S."""
    v = 1.0
    for i in S:
        v *= x[i]
    return v


def fourier_coeffs(f, n):
    """f^(S) = 2^-n sum_x f(x) chi_S(x) for every S subset of [n]."""
    pts = cube(n)
    coeffs = []
    for mask in range(1 << n):
        S = [i for i in range(n) if mask >> i & 1]
        coeffs.append(sum(fx * char_fn(S, x) for fx, x in zip(f, pts)) / len(pts))
    return coeffs


def entropy(coeffs):
    """H = sum p ln(1/p) over p = f^(S)^2 (zero terms skipped)."""
    h = 0.0
    for c in coeffs:
        p = c * c
        if p > 0:
            h += p * math.log(1.0 / p)
    return h


def influences(f, n):
    """Inf_i = Pr_x[f(x) != f(x^i)], the paper's probability form."""
    pts = cube(n)
    out = []
    for i in range(n):
        bad = 0
        for fx, x in zip(f, pts):
            y = list(x)
            y[i] = -y[i]
            j = pts.index(tuple(y))
            if fx != f[j]:
                bad += 1
        out.append(bad / len(pts))
    return out


def analyze(name, f, n, expect_H, expect_I):
    coeffs = fourier_coeffs(f, n)
    parseval = sum(c * c for c in coeffs)
    H = entropy(coeffs)
    I = sum(influences(f, n))
    ok_parseval = abs(parseval - 1.0) < 1e-9
    ok_H = abs(H - expect_H) < 1e-9
    ok_I = abs(I - expect_I) < 1e-9
    status = "ok" if (ok_parseval and ok_H and ok_I) else "FAIL"
    print(f"[{status}] {name:28s} n={n}  H={H:.10f} (expect {expect_H:.10f})  "
          f"I={I:.10f} (expect {expect_I:.10f})  Parseval sum f^2 ={parseval:.12f}")
    return ok_parseval and ok_H and ok_I


def dictator(n, i):
    return [x[i] for x in cube(n)]


def parity(n):
    return [math.prod(x) for x in cube(n)]


def and_two():
    return [1.0 if (x[0] > 0 and x[1] > 0) else -1.0 for x in cube(2)]


def maj3():
    return [1.0 if sum(x) > 0 else -1.0 for x in cube(3)]


def all_functions(n):
    """Every {±1}-valued function on the n-cube, as tuples over cube(n)."""
    return product([1.0, -1.0], repeat=2 ** n)


def minterm(n):
    """f = 1 everywhere except at the all-(-1) point (an AND-like minterm)."""
    return [-1.0 if all(v < 0 for v in x) else 1.0 for x in cube(n)]


def main():
    ok = True

    print("== c1: dictator family (H = 0, I = 1) ==")
    for n in range(1, 5):
        for i in range(n):
            ok &= analyze(f"dictator i={i}", dictator(n, i), n, 0.0, 1.0)

    print("== c2: parity family (H = 0, I = n) ==")
    for n in range(1, 5):
        ok &= analyze(f"parity n={n}", parity(n), n, 0.0, float(n))

    print("== c3: AND_2, low influence (H = 2 ln 2, I = 1) ==")
    ok &= analyze("andTwo", and_two(), 2, 2 * LN2, 1.0)

    print("== context: majority of 3 (symmetric, nontrivial H) ==")
    ok &= analyze("maj3", maj3(), 3, 2 * LN2, 1.5)

    print("== context: minterm family ratio H/I -> 4 ln 2 ==")
    for n in (2, 3, 4, 6, 8, 10):
        f = minterm(n)
        H = entropy(fourier_coeffs(f, n))
        I = sum(influences(f, n))
        print(f"[  ] minterm n={n:2d}: H={H:.8f}  I={I:.8f}  H/I={H / I:.8f}  "
              f"(4 ln 2 = {4 * LN2:.8f})")

    print("== exhaustive scan: H <= 3 I on small cubes (conjecture check) ==")
    for n in (3, 4):
        worst = 0.0
        worst_f = None
        for f in all_functions(n):
            I = sum(influences(list(f), n))
            if I == 0:  # constant functions: H = I = 0, no constraint on C
                continue
            H = entropy(fourier_coeffs(list(f), n))
            if H / I > worst:
                worst = H / I
                worst_f = f
        bound_ok = worst <= 3.0
        print(f"[{'ok' if bound_ok else 'FAIL'}] n={n}: max H/I = {worst:.10f} "
              f"<= 3 (minterm-like worst, values {worst_f})")
        ok &= bound_ok

    print("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
