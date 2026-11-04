#!/usr/bin/env python3
"""Exhaustive enumeration behind the Alon–Jaeger–Tarsi special cases.

For a prime p and dimension n this script enumerates every n x n matrix over
F_p, keeps the nonsingular ones (det != 0 mod p), and checks the
Alon–Jaeger–Tarsi property: there exists a vector x with every component of
x and of A*x nonzero.

Cases (mirrors tests/checkpoints.json):
  (a) p = 3, n = 1 and n = 2  -> n = 1 holds for all; n = 2 has counterexamples
  (b) p = 5, n = 2            -> holds for all
  context: p = 2, n = 2       -> counterexamples (the q >= 4 threshold)

Pure stdlib; runs in seconds. Usage: python3 enumerate_small.py
"""

from itertools import product


def det(A, p):
    """Determinant of an n x n matrix (tuple of tuples) mod p, Laplace expansion."""
    n = len(A)
    if n == 1:
        return A[0][0] % p
    if n == 2:
        return (A[0][0] * A[1][1] - A[0][1] * A[1][0]) % p
    s = 0
    for j in range(n):
        minor = tuple(row[:j] + row[j + 1:] for row in A[1:])
        s += ((-1) ** j) * A[0][j] * det(minor, p)
    return s % p


def mat_vec(A, x, p):
    n = len(A)
    return tuple(sum(A[i][j] * x[j] for j in range(n)) % p for i in range(n))


def all_matrices(n, p):
    for entries in product(range(p), repeat=n * n):
        yield tuple(tuple(entries[i * n + j] for j in range(n)) for i in range(n))


def find_ajt_vector(A, p):
    """Return a nowhere-zero x with A*x nowhere-zero, or None."""
    n = len(A)
    for x in product(range(1, p), repeat=n):  # nowhere-zero x: all components in 1..p-1
        if all(c != 0 for c in mat_vec(A, x, p)):
            return x
    return None


def survey_case(p, n):
    total = nonsing = ok = 0
    counterexample = None
    example_witness = None
    for A in all_matrices(n, p):
        total += 1
        if det(A, p) == 0:
            continue
        nonsing += 1
        x = find_ajt_vector(A, p)
        if x is not None:
            ok += 1
            if example_witness is None:
                example_witness = (A, x)
        elif counterexample is None:
            counterexample = A
    return {
        "p": p, "n": n, "total": total, "nonsingular": nonsing,
        "with_ajt_vector": ok, "without_ajt_vector": nonsing - ok,
        "counterexample": counterexample, "example_witness": example_witness,
    }


def fmt_mat(A):
    return "[" + "; ".join(str(list(row)) for row in A) + "]"


def main():
    for p, n in [(2, 2), (3, 1), (3, 2), (5, 2)]:
        r = survey_case(p, n)
        verdict = "ALL nonsingular matrices have an AJT vector" if r["without_ajt_vector"] == 0 \
            else f"COUNTEREXAMPLES EXIST ({r['without_ajt_vector']} of {r['nonsingular']})"
        print(f"p = {r['p']}, n = {r['n']}: "
              f"{r['total']} matrices, {r['nonsingular']} nonsingular, "
              f"{r['with_ajt_vector']} with AJT vector -> {verdict}")
        if r["counterexample"] is not None:
            print(f"   first counterexample: A = {fmt_mat(r['counterexample'])}")
        if r["example_witness"] is not None:
            A, x = r["example_witness"]
            print(f"   example witness: A = {fmt_mat(A)}, x = {list(x)}, "
                  f"A*x = {list(mat_vec(A, x, p))}")


if __name__ == "__main__":
    main()
