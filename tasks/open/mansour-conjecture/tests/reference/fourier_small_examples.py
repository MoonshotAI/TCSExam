#!/usr/bin/env python3
"""Numerical cross-checks for the Mansour-conjecture task package
(tcsexam-open/tasks/mansour-conjecture).

Independent recomputation of every concrete number appearing in the task's
Lean statements and reference docs, in exact integer/rational arithmetic:

  - single-term DNF spectra (the `single_term_spectrum` checkpoint);
  - the selector DNF's integer numerators (the `selector_spectrum`
    checkpoint, first conjunct) and its two concentration facts;
  - a depth-1 decision tree's spectrum (the `dtree_exact_concentration`
    checkpoint's small instance);
  - Parseval's identity in integer form (sum of squared numerators = 2^{2n}).

Conventions (must match the Lean definition layer):
  - cube point x : Fin n -> Bool; chi_S(x) = prod_{i in S} (+1 if x i else -1)
  - integer numerator num(S) = sum_x f(x) chi_S(x);  f_hat(S) = num(S) / 2^n
  - a term is (pos, neg): variables required true / required false
  - dnfFun D x = +1 if some term is satisfied else -1
"""
from fractions import Fraction as Fr
from itertools import combinations


def pm1(b):
    return 1 if b else -1


def chi(S, x):
    out = 1
    for i in S:
        out *= pm1(x[i])
    return out


def term_sat(term, x):
    pos, neg = term
    return all(x[i] for i in pos) and all(not x[i] for i in neg)


def dnf_fun(dnf, x):
    return pm1(any(term_sat(t, x) for t in dnf))


def numerators(f, n):
    pts = [tuple((k >> i) & 1 == 1 for i in range(n)) for k in range(2**n)]
    out = {}
    for r in range(n + 1):
        for S in combinations(range(n), r):
            out[S] = sum(f(x) * chi(S, x) for x in pts)
    return out


def tail_mass(nums, kept, n):
    """Mass outside `kept`, as an exact fraction (sum of f_hat^2)."""
    return sum(Fr(v * v, 2 ** (2 * n)) for S, v in nums.items() if S not in kept)


FAILURES = []


def check(label, got, want):
    ok = got == want
    if not ok:
        FAILURES.append(label)
    print(f"  [{'OK' if ok else 'FAIL'}] {label}: got {got}, want {want}")


def check_single_term(name, term, n):
    """Verify the single-term formula: num(S) = 2^{n+1-w} (-1)^{|S cap neg|}
    for nonempty S subset of vars, num(empty) = 2^{n+1-w} - 2^n, else 0."""
    pos, neg = term
    assert not (pos & neg), "term must be consistent"
    w = len(pos | neg)
    f = lambda x: dnf_fun([term], x)
    nums = numerators(f, n)
    print(f"== single term {name} (width w={w}, n={n}) ==")
    for S, v in sorted(nums.items(), key=lambda kv: (len(kv[0]), kv[0])):
        if len(S) == 0:
            want = 2 ** (n + 1 - w) - 2 ** n
        elif set(S) <= (pos | neg):
            want = (-1) ** len(set(S) & neg) * 2 ** (n + 1 - w)
        else:
            want = 0
        check(f"num{S}", v, want)
    check("sum num^2 = 2^(2n)", sum(v * v for v in nums.values()), 2 ** (2 * n))
    print()


n = 3
check_single_term("dictator [x0]", ({0}, set()), n)
check_single_term("negated literal [~x1]", (set(), {1}), n)
check_single_term("conjunction [x0 x1]", ({0, 1}, set()), n)
check_single_term("mixed conjunction [x0 ~x1]", ({0}, {1}), n)

print("== selector DNF: x0*x1 OR ~x0*x2 (n=3) ==")
selector = [({0, 1}, set()), ({2}, {0})]
f = lambda x: dnf_fun(selector, x)
nums = numerators(f, n)
expected_table = {(1,): 4, (2,): 4, (0, 1): 4, (0, 2): -4}
for S in sorted(nums, key=lambda s: (len(s), s)):
    check(f"num{S}", nums[S], expected_table.get(S, 0))
check("sum num^2 = 2^(2n)", sum(v * v for v in nums.values()), 64)
support = set(expected_table)
check("0-concentration on support", tail_mass(nums, support, n), Fr(0))
check("1/4-concentration on {(1,),(2,),(0,1)}",
      tail_mass(nums, {(1,), (2,), (0, 1)}, n), Fr(1, 4))
print()

print("== depth-1 decision tree node(x0; leaf false, leaf true) = dictator ==")
tree_eval = lambda x: x[0]
f = lambda x: pm1(tree_eval(x))
nums = numerators(f, n)
for S in sorted(nums, key=lambda s: (len(s), s)):
    check(f"num{S}", nums[S], 8 if S == (0,) else 0)
check("0-concentration on {S : |S| <= 1} (depth = 1)",
      tail_mass(nums, {S for S in nums if len(S) <= 1}, n), Fr(0))
print()

print("FAILURES:", FAILURES if FAILURES else "none")
raise SystemExit(1 if FAILURES else 0)
