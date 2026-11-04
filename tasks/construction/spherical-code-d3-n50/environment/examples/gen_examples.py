#!/usr/bin/env python3
"""Deterministic constructions for spherical-code-d3-n50.

Both constructions produce 50 points on (strictly inside) the unit sphere
in R^3 and are fully deterministic: fixed formula, fixed iteration count,
no randomness, stdlib only.

  (Fibonacci spiral): the classic
  Fibonacci sphere point set. Point i (0 <= i < 50) has
      z = 1 - 2*(i + 0.5)/50,  r = sqrt(1 - z^2),  phi = i * pi * (3 - sqrt(5))
      (x, y) = r * (cos(phi), sin(phi)).
  Coordinates are truncated toward zero to 12 decimal places, so every
  point lands strictly inside the ball (||v||^2 < 1: truncation toward
  zero only shrinks each |coordinate|, and the pre-truncation squared
  norm exceeds 1 by at most float64 noise ~3e-16, while truncation
  removes ~1e-13 or more). The exact maximum normalized inner product of
  this set is 0.9045852811944625 749 ... (witness pair (0, 3)).

  relaxed: deterministic Coulomb
  relaxation of the Fibonacci seed -- the classic Thomson-problem
  iteration. 12000 steps; at step t the step size is
  0.03 * 0.5**(t/2000); each pair repels with force (pa - pb)/|pa-pb|^3,
  the total force on each point is projected onto the tangent plane of
  the unit sphere, the point is moved and renormalized to the sphere.
  Final coordinates truncated toward zero to 12 decimals (same ||v||<1
  argument). Exact maximum normalized inner product
  0.8770506049328...

Usage: python3 gen_examples.py [fib|relaxed]   (default: report both)
Writes the chosen configuration to stdout as a submission JSON. The two
shipped example files were produced by:
  python3 gen_examples.py fib > example_fib50.json
  python3 gen_examples.py relaxed  > example_relaxed50.json
"""
import json
import math
import sys
from fractions import Fraction

N = 50
GOLDEN_ANGLE = math.pi * (3.0 - math.sqrt(5.0))
ND = 12                    # decimal places kept after truncation
RELAX_STEPS = 12000
RELAX_ETA0 = 0.03
RELAX_HALF = 2000.0


def trunc_tz(v, nd=ND):
    """Truncate toward zero to nd decimal places; exact Fraction result.

    The float64 input is converted to an exact Fraction first, so the
    truncation is exact decimal arithmetic, not float multiplication.
    """
    q = 10 ** nd
    a = Fraction(v)
    t = math.trunc(abs(a) * q)
    f = Fraction(t, q)
    return f if a >= 0 else -f


def dec_str(f, nd=ND):
    """Exact decimal string of a Fraction produced by trunc_tz."""
    neg = f < 0
    f = abs(f)
    q = 10 ** nd
    num = f.numerator * q // f.denominator  # exact: denominator divides q
    int_part, frac_part = divmod(num, q)
    s = f"{int_part}.{str(frac_part).zfill(nd)}"
    return ("-" + s) if neg else s


def fibonacci_seed():
    """The Fibonacci sphere seed, float64 unit vectors."""
    pts = []
    for i in range(N):
        z = 1.0 - 2.0 * (i + 0.5) / N
        r = math.sqrt(max(0.0, 1.0 - z * z))
        phi = i * GOLDEN_ANGLE
        pts.append([r * math.cos(phi), r * math.sin(phi), z])
    return pts


def fib_points():
    return [tuple(trunc_tz(v) for v in p) for p in fibonacci_seed()]


def relaxed_points():
    """Coulomb relaxation of the Fibonacci seed; fixed schedule, no RNG."""
    pts = fibonacci_seed()
    for t in range(RELAX_STEPS):
        eta = RELAX_ETA0 * (0.5 ** (t / RELAX_HALF))
        forces = [[0.0, 0.0, 0.0] for _ in range(N)]
        for a in range(N):
            pa = pts[a]
            fa = forces[a]
            for b in range(a + 1, N):
                pb = pts[b]
                dx = pa[0] - pb[0]
                dy = pa[1] - pb[1]
                dz = pa[2] - pb[2]
                d2 = dx * dx + dy * dy + dz * dz
                inv = 1.0 / (d2 * math.sqrt(d2))
                fa[0] += dx * inv
                fa[1] += dy * inv
                fa[2] += dz * inv
                fb = forces[b]
                fb[0] -= dx * inv
                fb[1] -= dy * inv
                fb[2] -= dz * inv
        for a in range(N):
            pa = pts[a]
            fa = forces[a]
            dot = fa[0] * pa[0] + fa[1] * pa[1] + fa[2] * pa[2]
            nx = pa[0] + eta * (fa[0] - dot * pa[0])
            ny = pa[1] + eta * (fa[1] - dot * pa[1])
            nz = pa[2] + eta * (fa[2] - dot * pa[2])
            nn = math.sqrt(nx * nx + ny * ny + nz * nz)
            pts[a] = [nx / nn, ny / nn, nz / nn]
    return [tuple(trunc_tz(v) for v in p) for p in pts]


def emit(points, comment):
    pts = [[dec_str(c) for c in p] for p in points]
    print(json.dumps({"n": N, "points": pts, "comment": comment}))


def max_cos_float(points):
    """Float64 summary for the stderr report (the checker is exact)."""
    best, wit = None, None
    norms = [sum(c * c for c in p) for p in points]
    for i in range(N):
        for j in range(i + 1, N):
            num = sum(a * b for a, b in zip(points[i], points[j]))
            c = float(num) / math.sqrt(float(norms[i] * norms[j]))
            if best is None or c > best:
                best, wit = c, (i, j)
    return best, wit


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else ""
    if which == "fib":
        emit(fib_points(),
             "Fibonacci sphere, 50 points, coords truncated toward zero to "
             "12 decimals")
    elif which == "relaxed":
        emit(relaxed_points(),
             "deterministic Coulomb relaxation (12000 steps) of the "
             "Fibonacci seed, coords truncated toward zero to 12 decimals")
    else:
        for name, fn in (("fib", fib_points),
                         ("relaxed", relaxed_points)):
            pts = fn()
            mxn = max(sum(c * c for c in p) for p in pts)
            c, wit = max_cos_float(pts)
            print(f"{name}: {N} points, max ||v||^2 = {float(mxn):.15f} "
                  f"(< 1: {mxn < 1}), max inner product ~= {c:.15f} "
                  f"witness {wit}", file=sys.stderr)


if __name__ == "__main__":
    main()
