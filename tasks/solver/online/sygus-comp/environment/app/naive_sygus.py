#!/usr/bin/env python3
"""Naive SyGuS baseline: bottom-up grammar enumeration + machine check.

The simplest possible honest synthesizer: enumerate candidate bodies from
the synth-fun's grammar bottom-up (depth by depth), and for each one ask
the task's own two-step machine check (sygus_check.check_answer — grammar
derivability is free by construction, the semantic step is a pristine
cvc5 unsat query) whether it is a valid solution. First valid candidate
wins. No CEGIS, no counterexamples, no pruning beyond identical-term
dedup, no portfolios.

Synth-funs WITHOUT a grammar (the majority of this pool) get a tiny
generic grammar built from the return sort and the parameter sorts
(params, 0/1/true/false, +,-,not,and,or,=,<,<=,ite — one generic
arithmetic/logic skeleton), then the same bottom-up enumeration runs.
Multi-synth-fun benchmarks and those the generic grammar cannot cover are
given up on.

Budget discipline: the whole run is bounded by N_CANDIDATES semantic
checks (default 240, each with a short cvc5 timeout) — well inside the
3600 s per-instance judging budget. Anything not solved by the first 240
candidates is given up on (`fail`).
"""
import itertools
import os
import sys
import time

sys.path.insert(0, "/opt/sygus")
import sygus_check
from sygus_check import Sx, is_atom, parse_benchmark, render

VERIFY_MS = int(os.environ.get("NAIVE_SYGUS_VERIFY_MS", "5000"))
N_CANDIDATES = int(os.environ.get("NAIVE_SYGUS_CANDIDATES", "1500"))
MAX_DEPTH = int(os.environ.get("NAIVE_SYGUS_MAX_DEPTH", "6"))
MAX_PER_NT = int(os.environ.get("NAIVE_SYGUS_MAX_PER_NT", "1500"))


# --------------------------------------------------------------------------
# grammars: benchmark's own, or a generic one built from the sorts
# --------------------------------------------------------------------------

def _generic_grammar(sf):
    """Build (start_nt, {nt: [productions]}) for a grammar-less synth-fun,
    from its return sort and parameter sorts. Supports Int and Bool
    returns/params (the CLIA/Inv mainstream); anything else yields a
    near-trivial grammar of just parameters (PBE/bit-vector instances will
    mostly fail — the naive baseline is allowed to be weak)."""
    ret = render(sf.ret_sort)
    params = [(str(p[0]), render(p[1])) for p in sf.params]
    int_params = [Sx(n) for n, s in params if s == "Int"]
    bool_params = [Sx(n) for n, s in params if s == "Bool"]
    if ret == "Int":
        int_atoms = int_params + [Sx("0"), Sx("1")]
        bool_atoms = bool_params + [Sx("true"), Sx("false")]
        prods = {
            "I": int_atoms + [[Sx("+"), Sx("I"), Sx("I")],
                              [Sx("-"), Sx("I"), Sx("I")],
                              [Sx("ite"), Sx("B"), Sx("I"), Sx("I")]],
            "B": bool_atoms + [[Sx("not"), Sx("B")],
                               [Sx("and"), Sx("B"), Sx("B")],
                               [Sx("or"), Sx("B"), Sx("B")],
                               [Sx("="), Sx("I"), Sx("I")],
                               [Sx("<"), Sx("I"), Sx("I")],
                               [Sx("<="), Sx("I"), Sx("I")]],
        }
        if not int_params:
            # No Int parameter (e.g. zero-arg or Bool-only): still offer 0/1.
            prods["I"] = [Sx("0"), Sx("1")] + prods["I"][len(int_atoms):]
        return "I", prods
    if ret == "Bool":
        int_atoms = int_params + [Sx("0"), Sx("1")]
        bool_atoms = bool_params + [Sx("true"), Sx("false")]
        prods = {
            "B": bool_atoms + [[Sx("not"), Sx("B")],
                               [Sx("and"), Sx("B"), Sx("B")],
                               [Sx("or"), Sx("B"), Sx("B")],
                               [Sx("=>"), Sx("B"), Sx("B")],
                               [Sx("="), Sx("I"), Sx("I")],
                               [Sx("<"), Sx("I"), Sx("I")],
                               [Sx("<="), Sx("I"), Sx("I")]],
            "I": int_atoms + [[Sx("+"), Sx("I"), Sx("I")],
                              [Sx("-"), Sx("I"), Sx("I")]],
        }
        return "B", prods
    # exotic sort (bit-vectors, strings): parameters only
    return None, {}


def _grammar_nts(grammar):
    """Benchmark grammar [(nt, sort, [prods])] -> (start_nt, {nt: [prods]})."""
    if not grammar:
        return None, {}
    start = None
    table = {}
    for entry in grammar:
        if len(entry) < 3:
            continue
        nt = str(entry[0])
        if start is None:
            start = nt
        table[nt] = list(entry[2])
    return start, table


# --------------------------------------------------------------------------
# bottom-up enumeration
# --------------------------------------------------------------------------

def _diag_product(pools, cap=512):
    """Cartesian product in index-sum (diagonal) order: combinations with
    small component indices first, so (* 1 x) appears long before the
    iterator exhausts the (* 0 x) family (itertools.product's dictionary
    order buries useful combos behind the first pool's whole prefix)."""
    if len(pools) == 1:
        for i, x in enumerate(pools[0]):
            yield (x,)
            if i >= cap:
                return
        return
    if len(pools) > 3:
        pools = [p[:8] for p in pools]  # wide productions: truncate hard
    emitted = 0
    max_sum = sum(len(p) for p in pools) - len(pools)
    for s in range(max_sum + 1):
        def _rec(k, rem, acc):
            nonlocal emitted
            if emitted >= cap:
                return
            if k == len(pools) - 1:
                if rem < len(pools[k]):
                    emitted += 1
                    yield tuple(acc + [pools[k][rem]])
                return
            for i in range(min(rem, len(pools[k]) - 1) + 1):
                yield from _rec(k + 1, rem - i, acc + [pools[k][i]])
        yield from _rec(0, s, [])
        if emitted >= cap:
            return


def enumerate_terms(start, table, max_depth, max_per_nt):
    """Yield terms of the start non-terminal in nondecreasing depth.
    (Constant S) / (Variable S) productions expand to a small literal and
    parameter set; composite productions combine shallower terms."""
    terms = {nt: [] for nt in table}
    seen = {nt: set() for nt in table}

    def atoms(nt):
        for prod in table[nt]:
            if is_atom(prod):
                yield prod
            elif isinstance(prod, list) and prod:
                head = str(prod[0])
                if head in ("Constant", "Variable", "InputVariable",
                            "LocalVariable"):
                    for lit in ("0", "1", "true", "false"):
                        yield Sx(lit)
                    # parameters were folded into the prod list by the
                    # caller for generic grammars; for benchmark grammars
                    # the Variable production just means "some variable",
                    # offer nothing (we cannot know sorts reliably).

    for depth in range(1, max_depth + 1):
        grew = False
        for nt in table:
            def _add(t, _nt=nt):
                r = render(t) if isinstance(t, list) else str(t)
                if r not in seen[_nt] and len(terms[_nt]) < max_per_nt:
                    seen[_nt].add(r)
                    terms[_nt].append(t)
                    return True
                return False

            if depth == 1:
                for t in atoms(nt):
                    if _add(t):
                        grew = True
                # plain-atom productions that are already terms (generic
                # grammars put parameters and literals directly)
                for prod in table[nt]:
                    if is_atom(prod) and str(prod) not in ("0", "1", "true", "false"):
                        if _add(prod):
                            grew = True
            else:
                for prod in table[nt]:
                    if not isinstance(prod, list) or not prod:
                        continue
                    head = prod[0]
                    if str(head) in ("Constant", "Variable", "InputVariable",
                                     "LocalVariable"):
                        continue
                    sub_nts = [str(a) for a in prod[1:]]
                    if any(s not in table for s in sub_nts):
                        continue
                    pools = [terms[s][:24] for s in sub_nts]
                    if any(not p for p in pools):
                        continue
                    for combo in _diag_product(pools):
                        # identity-element skip (pure syntactic redundancy,
                        # the standard symmetry pruning of bottom-up
                        # enumeration): (* 0 _) and (+ 0 _) / (+ _ 0) add
                        # nothing the shallower terms don't already say.
                        if str(head) == "*" and any(str(c) == "0" for c in combo):
                            continue
                        if str(head) == "+" and any(str(c) == "0" for c in combo):
                            continue
                        if _add([head] + list(combo)):
                            grew = True
                        if len(terms[nt]) >= max_per_nt:
                            break
        if not grew and depth > 1:
            break
    return terms.get(start, [])


# --------------------------------------------------------------------------
# main: enumerate + check
# --------------------------------------------------------------------------

def solve_one(bm_path, budget_s):
    bm = parse_benchmark(bm_path)
    if len(bm.synth_funs) != 1:
        return None  # the naive baseline only attempts single-synth-fun
    sf = bm.synth_funs[0]
    start, table = _grammar_nts(sf.grammar)
    if not start or not table:
        start, table = _generic_grammar(sf)
    if not start or not table:
        return None
    cands = enumerate_terms(start, table, MAX_DEPTH, MAX_PER_NT)
    t0 = time.time()
    checked = 0
    params_txt = " ".join("(" + str(p[0]) + " " + render(p[1]) + ")"
                          for p in sf.params)
    for body in cands:
        if checked >= N_CANDIDATES:
            break
        if time.time() - t0 > budget_s - 30:
            break
        text = (f"(\n(define-fun {sf.name} ({params_txt}) "
                f"{render(sf.ret_sort)} {render(body)})\n)")
        checked += 1
        try:
            ok, _reason = sygus_check.check_answer(bm_path, text,
                                                   timeout_ms=VERIFY_MS)
        except Exception:
            ok = False
        if ok:
            return text
    return None


def main():
    if len(sys.argv) != 2:
        print("usage: naive_sygus.py INSTANCE.sl", file=sys.stderr)
        return 2
    budget = float(os.environ.get("SYGUS_INSTANCE_SECONDS", "3600"))
    try:
        sol = solve_one(sys.argv[1], budget)
    except Exception as e:  # noqa: BLE001 - a crash counts as not solved
        print("fail", flush=True)
        print(f"naive baseline error: {type(e).__name__}: {e}", file=sys.stderr)
        return 0
    if sol is None:
        print("fail", flush=True)
    else:
        print(sol, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
