#!/usr/bin/env python3
"""Two-step machine checker for SyGuS synthesis answers.

Used by BOTH sides of the sygus-comp task so the validity definition cannot
diverge:
  - agent side:  /app/score_public.py (via /app/scoring.py)
  - judge side:  /tests/checker.py    (via /opt/sygus/scoring.py, same file)

Step 1 — grammar (syntax template) check: when a synth-fun comes with a
grammar, the synthesized body must be derivable from the grammar's start
non-terminal. Supports the SyGuS-IF v2 grammar features that occur in the
comp/ benchmark pool: (Constant S), (Variable S), (InputVariable S),
(LocalVariable S), let-bound productions, indexed operator heads
(e.g. ((_ extract 7 0) Start)), and define-fun macros used as operators.
Synth-funs without a grammar skip this step (well-formedness is then
enforced by step 2, which fails to parse/ill-sorts → invalid).

Step 2 — semantic check: the benchmark's define-fun macros are copied
verbatim, the submitted define-fun(s) are added, every declare-var /
declare-primed-var becomes a fresh constant, and the negation of the
conjunction of all constraints is asserted. A pristine cvc5 binary (NOT
the agent's build) must prove the query unsat. For inv-constraint
benchmarks the three invariant implications (initiation, consecution,
safety) are checked separately, each must be unsat. sat / unknown /
timeout / solver error → invalid.

The solver's own claims are never trusted: a printed solution only counts
when both steps pass.
"""

import os
import re
import subprocess
import sys
import tempfile

# Legit solver output can nest deeply (cvc5 let-chains nest one level per
# binding); the parsers below are recursive. Give them headroom while
# staying well inside a typical 8 MiB main-thread stack — anything deeper
# raises RecursionError, which callers treat as a rejection (run in a
# thread? give the thread a real stack, e.g. threading.stack_size(32<<20)).
sys.setrecursionlimit(10000)

# --------------------------------------------------------------------------
# S-expression machinery
# --------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"""
    \s*(?:
    (?P<comment>;[^\n]*)
  | (?P<lp>\()
  | (?P<rp>\))
  | (?P<str>"(?:[^"\\]|\\.)*")
  | (?P<bar>\|[^|]*\|)
  | (?P<atom>[^\s()";|]+)
    )""", re.VERBOSE)


def tokenize(text):
    pos, n = 0, len(text)
    while pos < n:
        if not text[pos:].strip():
            break
        m = _TOKEN_RE.match(text, pos)
        if not m:
            raise ValueError(f"tokenize error at offset {pos}")
        pos = m.end()
        if m.group("comment") is not None:
            continue
        for kind in ("lp", "rp", "str", "bar", "atom"):
            v = m.group(kind)
            if v is not None:
                yield (kind, v)
                break


class Sx(str):
    """An atom (symbol / literal / string). Strings keep their quotes."""


def parse_sexprs(text):
    """Parse all top-level s-expressions. Returns list; atoms are Sx."""
    stack = []
    top = []
    for kind, v in tokenize(text):
        if kind == "lp":
            stack.append([])
        elif kind == "rp":
            if not stack:
                raise ValueError("unbalanced ')'")
            done = stack.pop()
            if stack:
                stack[-1].append(done)
            else:
                top.append(done)
        else:
            if stack:
                stack[-1].append(Sx(v))
            else:
                top.append(Sx(v))
    if stack:
        raise ValueError("unbalanced '('")
    return top


def render(x):
    if isinstance(x, list):
        return "(" + " ".join(render(y) for y in x) + ")"
    return str(x)


def is_atom(x):
    return isinstance(x, Sx)


# --------------------------------------------------------------------------
# Benchmark model
# --------------------------------------------------------------------------

class SynthFun:
    def __init__(self, name, params, ret_sort, grammar, is_inv):
        self.name = name                # str
        self.params = params            # [(name, sort-sexpr)]
        self.ret_sort = ret_sort        # sort sexpr
        self.grammar = grammar          # None or [(nt, sort, [productions])]
        self.is_inv = is_inv


class Benchmark:
    def __init__(self):
        self.logic = None
        self.define_funs = []           # raw sexprs, in order
        self.declare_funs = []          # raw sexprs, in order
        self.declare_vars = []          # [(name, sort)]
        self.primed_vars = []           # [(name, sort)]  (declare-primed-var)
        self.synth_funs = []            # [SynthFun], in order
        self.constraints = []           # [sexpr]
        self.inv_constraint = None      # (inv, pre, trans, post)
        self.set_options = []           # raw sexprs (informational)
        self.has_check_synth = False


def _param_list(sexpr):
    out = []
    for p in sexpr:
        if not (isinstance(p, list) and len(p) == 2):
            raise ValueError(f"bad parameter {render(p)}")
        out.append((str(p[0]), p[1]))
    return out


def _grammar(sexpr):
    """sexpr: ((NT Sort (prod ...)) ...). Returns [(nt, sort, [prods])]."""
    out = []
    for g in sexpr:
        if not (isinstance(g, list) and len(g) == 3 and isinstance(g[2], list)):
            raise ValueError(f"bad grammar entry {render(g)}")
        out.append((str(g[0]), g[1], list(g[2])))
    if not out:
        raise ValueError("grammar with no non-terminals")
    return out


def parse_benchmark(path):
    with open(path, errors="replace") as f:
        text = f.read()
    bm = Benchmark()
    for e in parse_sexprs(text):
        if not isinstance(e, list) or not e or not is_atom(e[0]):
            raise ValueError(f"bad top-level command {render(e)[:80]}")
        head = str(e[0])
        if head == "set-logic" and len(e) == 2:
            bm.logic = str(e[1])
        elif head == "set-option":
            bm.set_options.append(e)
        elif head == "set-info" or head == "set-options":
            pass
        elif head == "define-fun":
            bm.define_funs.append(e)
        elif head == "declare-fun" or head == "declare-sort" or head == "define-sort":
            bm.declare_funs.append(e)
        elif head == "declare-var" and len(e) == 3:
            bm.declare_vars.append((str(e[1]), e[2]))
        elif head == "declare-primed-var" and len(e) == 3:
            bm.primed_vars.append((str(e[1]), e[2]))
        elif head in ("synth-fun", "synth-inv"):
            is_inv = head == "synth-inv"
            min_len = 3 if is_inv else 4  # synth-inv has no return sort (Bool)
            if len(e) < min_len:
                raise ValueError(f"{head}: bad arity")
            ret = Sx("Bool") if is_inv else e[3]
            grammar = None
            # Accept both grammar spellings:
            #   v1 single list:  (... ((NT S (prods)) ...))
            #   v2 two lists:    (... ((NT S) ...) ((NT S (prods)) ...))
            # (the task ships the v2 form, which is what cvc5 1.3.x parses).
            for g in e[min_len:]:
                if not isinstance(g, list) or not g:
                    raise ValueError("bad grammar section")
                if all(isinstance(x, list) and len(x) == 2 for x in g):
                    continue  # v2 non-terminal declarations; informational
                grammar = _grammar(g)
            bm.synth_funs.append(SynthFun(
                str(e[1]), _param_list(e[2]), ret, grammar, is_inv=is_inv))
        elif head == "constraint" and len(e) == 2:
            bm.constraints.append(e[1])
        elif head == "inv-constraint" and len(e) == 5:
            bm.inv_constraint = tuple(str(x) for x in e[1:5])
        elif head == "check-synth":
            bm.has_check_synth = True
        else:
            raise ValueError(f"unsupported command {head}")
    if not bm.has_check_synth:
        raise ValueError("no (check-synth)")
    if not bm.synth_funs:
        raise ValueError("no synth-fun")
    return bm


# --------------------------------------------------------------------------
# Solution parsing
# --------------------------------------------------------------------------

def parse_solution(text):
    """Parse solver stdout into {fname: (params, ret_sort, body)} preserving
    define-fun order. Accepts the competition output forms:
      ((define-fun f (params) sort body) ...)   -- one wrapped list
      (define-fun f ...) (define-fun g ...)     -- bare sequence
    and, as a convenience for hand-written solvers on single-synth-fun
    benchmarks, a bare body term (handled by the caller).
    Returns (ordered_list_of_(name, params, sort, body), error)."""
    text = text.strip()
    if not text or text.lower() in ("fail", "unknown", "infeasible"):
        return None, "solver reported no solution"
    try:
        exprs = parse_sexprs(text)
    except ValueError as e:
        return None, f"could not parse solver output: {e}"
    if not exprs:
        return None, "empty solver output"
    # Unwrap the single outer list form.
    if len(exprs) == 1 and isinstance(exprs[0], list) and exprs[0] and \
            all(isinstance(x, list) for x in exprs[0]):
        exprs = exprs[0]
    out = []
    for e in exprs:
        if isinstance(e, list) and len(e) == 5 and is_atom(e[0]) and \
                str(e[0]) == "define-fun" and isinstance(e[2], list):
            try:
                params = _param_list(e[2])
            except ValueError as err:
                return None, str(err)
            out.append((str(e[1]), params, e[3], e[4]))
        else:
            return None, f"unexpected output form {render(e)[:80]}"
    return out, None


# --------------------------------------------------------------------------
# Step 1: grammar derivation check
# --------------------------------------------------------------------------

def _literal_sort(tok):
    """Best-effort sort of a literal token for (Constant S) matching."""
    if tok in ("true", "false"):
        return "Bool"
    if tok.startswith("#x"):
        return ("BitVec", 4 * (len(tok) - 2))
    if tok.startswith("#b"):
        return ("BitVec", len(tok) - 2)
    if tok.startswith('"'):
        return "String"
    if re.fullmatch(r"-?\d+", tok):
        return "Int"
    if re.fullmatch(r"-?\d+\.\d+", tok):
        return "Real"
    return None


def _norm_bv_sort(s):
    """('BitVec', width) tuple for both (_ BitVec 64) (v2) and (BitVec 64)
    (v1) spellings; None otherwise."""
    if isinstance(s, list):
        if len(s) == 3 and str(s[0]) == "_" and str(s[1]) == "BitVec":
            return ("BitVec", str(s[2]))
        if len(s) == 2 and str(s[0]) == "BitVec":
            return ("BitVec", str(s[1]))
    return None


def _sort_eq(a, b):
    for x, y in ((a, b), (b, a)):
        bx = _norm_bv_sort(x)
        if bx is not None:
            by = _norm_bv_sort(y)
            if by is not None:
                return bx == by
            return isinstance(y, tuple) and y[0] == "BitVec" and \
                str(y[1]) == bx[1]
    return a == b


def _bv_value(tok):
    """(width, value) of a #x/#b bit-vector literal; None otherwise."""
    if tok.startswith("#x") and len(tok) > 2:
        try:
            return (4 * (len(tok) - 2), int(tok[2:], 16))
        except ValueError:
            return None
    if tok.startswith("#b") and len(tok) > 2:
        try:
            return (len(tok) - 2, int(tok[2:], 2))
        except ValueError:
            return None
    return None


def _literal_eq(a, b):
    """Literal equality up to surface spelling: #x/#b bit-vectors compare
    by (width, value), numerals by integer value, decimals by float."""
    if a == b:
        return True
    va, vb = _bv_value(a), _bv_value(b)
    if va is not None or vb is not None:
        return va is not None and vb is not None and va == vb
    if re.fullmatch(r"-?\d+", a) and re.fullmatch(r"-?\d+", b):
        return int(a) == int(b)
    if re.fullmatch(r"-?\d+\.\d+", a) and re.fullmatch(r"-?\d+\.\d+", b):
        return float(a) == float(b)
    return False


def _neg_lit_atom(t):
    """'-3' for the term (- 3): cvc5 prints negative numeric literals as
    unary-minus applications even when the grammar spells them as atoms.
    Returns None for anything else."""
    if (isinstance(t, list) and len(t) == 2 and is_atom(t[0])
            and str(t[0]) == "-" and is_atom(t[1])
            and re.fullmatch(r"\d+(\.\d+)?", str(t[1]))):
        return "-" + str(t[1])
    return None


class GrammarChecker:
    def __init__(self, grammar, synth_params, sol_params):
        # grammar: [(nt, sort, [prods])]; start symbol is the first entry.
        self.prods = {nt: prods for nt, _, prods in grammar}
        self.start = grammar[0][0]
        # Map grammar-visible parameter names (from the synth-fun header) to
        # the solution's own parameter names, positionally.
        self.param_map = {sp: dp for (sp, _), (dp, _)
                          in zip(synth_params, sol_params)}
        self.param_sorts = {sp: s for sp, s in synth_params}
        self.memo = {}

    def check(self, body):
        """True iff body derives from the start non-terminal."""
        self.memo = {}
        return self._derive(self.start, body, frozenset())

    def _derive(self, nt, term, letvars):
        if nt not in self.prods:
            return False
        key = (nt, id(term), letvars)
        if key in self.memo:
            return self.memo[key]
        self.memo[key] = False  # cycle guard for NT chains (A -> B -> A)
        ok = any(self._match(p, term, letvars, frozenset())
                 for p in self.prods[nt])
        self.memo[key] = ok
        return ok

    def _match(self, p, t, letvars, chain):
        if is_atom(p):
            ps = str(p)
            if ps in self.prods:
                # Non-terminal reference; guard against left-recursive
                # chains that never consume structure.
                if ps in chain:
                    return False
                if not is_atom(t) and ps == self.start:
                    pass  # fine, t is a list; derive handles it
                return self._derive_chain(ps, t, letvars, chain)
            if ps in self.param_map:
                return is_atom(t) and str(t) == self.param_map[ps]
            if ps in letvars:
                return is_atom(t) and str(t) == ps
            # Literal or nullary symbol: equality up to literal spelling,
            # including cvc5's (- 3) spelling of negative literals.
            if is_atom(t):
                return _literal_eq(ps, str(t))
            neg = _neg_lit_atom(t)
            return neg is not None and _literal_eq(ps, neg)
        if not p:
            return False
        # The grammar itself spells a negative literal as (- 3): treat the
        # production as the atom -3 (only when the argument is a numeral;
        # a unary-minus production like (- ntInt) is left alone).
        neg_p = _neg_lit_atom(p)
        if neg_p is not None:
            if is_atom(t):
                return _literal_eq(neg_p, str(t))
            neg_t = _neg_lit_atom(t)
            return neg_t is not None and _literal_eq(neg_p, neg_t)
        head = str(p[0]) if is_atom(p[0]) else None
        if head == "Constant" and len(p) == 2:
            neg = None if is_atom(t) else _neg_lit_atom(t)
            tt = str(t) if is_atom(t) else neg
            if tt is None:
                return False
            ls = _literal_sort(tt)
            return ls is not None and _sort_eq(p[1], ls if isinstance(ls, tuple) else ls)
        if head == "Variable" and len(p) == 2:
            if not is_atom(t):
                return False
            ts = str(t)
            for sp, dp in self.param_map.items():
                if dp == ts and _sort_eq(p[1], self.param_sorts[sp]):
                    return True
            return ts in letvars
        if head == "InputVariable" and len(p) == 2:
            if not is_atom(t):
                return False
            ts = str(t)
            return any(dp == ts and _sort_eq(p[1], self.param_sorts[sp])
                       for sp, dp in self.param_map.items())
        if head == "LocalVariable" and len(p) == 2:
            return is_atom(t) and str(t) in letvars
        if head == "let" and len(p) == 3 and isinstance(p[1], list):
            # Production: (let ((v [Sort] gterm) ...) body)
            if not (isinstance(t, list) and len(t) == 3 and is_atom(t[0])
                    and str(t[0]) == "let" and isinstance(t[1], list)):
                return False
            gbinds, tbinds = p[1], t[1]
            if len(gbinds) != len(tbinds):
                return False
            newvars = set(letvars)
            for gb, tb in zip(gbinds, tbinds):
                # grammar binding: (v Sort gterm) or (v gterm)
                # term binding:   (v term) or (v Sort term)
                if not (isinstance(gb, list) and isinstance(tb, list)):
                    return False
                gv = str(gb[0]) if gb and is_atom(gb[0]) else None
                tv = str(tb[0]) if tb and is_atom(tb[0]) else None
                if gv is None or gv != tv:
                    return False
                g_expr = gb[-1]
                t_expr = tb[-1]
                if not self._match(g_expr, t_expr,
                                   frozenset(newvars), frozenset()):
                    return False
                newvars.add(gv)
            return self._match(p[2], t[2], frozenset(newvars), frozenset())
        # Ordinary application: heads must be literally equal (covers
        # indexed heads like (_ extract 7 0)), arities must match.
        if not isinstance(t, list) or len(t) != len(p) or not t:
            return False
        if render(t[0]) != render(p[0]):
            return False
        return all(self._match(pi, ti, letvars, frozenset())
                   for pi, ti in zip(p[1:], t[1:]))

    def _derive_chain(self, nt, term, letvars, chain):
        if nt in chain or nt not in self.prods:
            return False
        chain = chain | {nt}
        return any(self._match(p, term, letvars, chain)
                   for p in self.prods[nt])


def grammar_check(synth, sol_params, body):
    """(ok, reason). Validate the signature before any optional grammar.
    Parameter names may differ; their positional sorts and count must match.
    Synth-funs without a grammar accept any body (step 2 checks the body).
    Solutions may use let as surface compression
    (cvc5 prints such solutions even under a grammar); lets are expanded
    before the derivation check, with a node cap against exponential
    blow-up."""
    if len(sol_params) != len(synth.params):
        return False, (f"parameter count mismatch: solution has "
                       f"{len(sol_params)}, synth-fun has {len(synth.params)}")
    if len({name for name, _ in sol_params}) != len(sol_params):
        return False, "duplicate solution parameter name"
    for position, ((_, expected), (_, actual)) in enumerate(zip(synth.params, sol_params), 1):
        if not _sort_eq(expected, actual):
            return False, (f"parameter sort mismatch at position {position}: solution "
                           f"has {render(actual)}, synth-fun has {render(expected)}")
    if synth.grammar is None:
        return True, None
    try:
        body = _expand_lets(body)
    except ValueError as e:
        return False, f"could not normalize solution lets: {e}"
    gc = GrammarChecker(synth.grammar, synth.params, sol_params)
    if gc.check(body):
        return True, None
    return False, "solution body is not derivable from the grammar"


_LET_EXPAND_CAP = 200000


def _expand_lets(e):
    """Substitute all let bindings; raise ValueError past the node cap."""
    budget = [_LET_EXPAND_CAP]

    def walk(t, env):
        budget[0] -= 1
        if budget[0] < 0:
            raise ValueError("let expansion exceeds the node cap")
        if is_atom(t):
            return env.get(str(t), t)
        if t and str(t[0]) == "let" and len(t) == 3 and isinstance(t[1], list):
            new_env = dict(env)
            for b in t[1]:
                if not (isinstance(b, list) and len(b) == 2 and is_atom(b[0])):
                    raise ValueError("malformed let binding")
                new_env[str(b[0])] = walk(b[1], new_env)
            return walk(t[2], new_env)
        return [walk(x, env) for x in t]

    return walk(e, {})


# --------------------------------------------------------------------------
# Step 2: semantic check via a pristine cvc5
# --------------------------------------------------------------------------

CVC5_CHECK = os.environ.get("SYGUS_CHECK_CVC5", "/opt/sygus/cvc5")
VERIFY_TIMEOUT_MS = int(os.environ.get("SYGUS_VERIFY_TIMEOUT_MS", "90000"))

# SyGuS logic names -> the quantifier-free SMT-LIB logics used for the
# verification query (constraints are ground in the declared variables).
_LOGIC_MAP = {"LIA": "QF_LIA", "NIA": "QF_NIA", "BV": "QF_BV",
              "SLIA": "QF_SLIA", "LRA": "QF_LRA", "NRA": "QF_NRA",
              "ALIA": "QF_ALIA", "ANIA": "QF_ANIA"}


def _primed_vars(bm):
    """State variables of an invariant benchmark: from declare-primed-var
    (v1 dialect) and/or the synth-inv parameter list (v2 dialect, where the
    declare-primed-var lines are dropped — the primed copies only appear as
    trans-f parameters named x!)."""
    out = list(bm.primed_vars)
    for s in bm.synth_funs:
        if s.is_inv:
            for n, srt in s.params:
                if (n, srt) not in out:
                    out.append((n, srt))
    return out


def _check_script(bm, sol_defs):
    """Build the SMT-LIB v2 verification script. sol_defs is the ordered
    list of (name, params, sort, body) from the solver output."""
    lines = []
    logic = _LOGIC_MAP.get(bm.logic or "", "ALL")
    lines.append(f"(set-logic {logic})")
    for e in bm.declare_funs:
        lines.append(render(e))
    for e in bm.define_funs:
        lines.append(render(e))
    for name, params, sort, body in sol_defs:
        ps = " ".join(f"({n} {render(s)})" for n, s in params)
        lines.append(f"(define-fun {name} ({ps}) {render(sort)} {render(body)})")
    # Fresh constants for the universally quantified variables.
    primed = _primed_vars(bm)
    consts = {}
    for name, sort in bm.declare_vars:
        if name in consts:
            continue
        c = f"__v_{name}"
        consts[name] = c
        lines.append(f"(declare-const {c} {render(sort)})")
    for name, sort in primed:
        for nm in (name, name + "!"):
            if nm in consts:
                continue
            c = f"__v_{nm}"
            consts[nm] = c
            lines.append(f"(declare-const {c} {render(sort)})")

    def app(f, args):
        return f"({f} {' '.join(args)})" if args else f

    def subst(e):
        """Replace declared variables by their constants, recursively."""
        if is_atom(e):
            return Sx(consts.get(str(e), str(e)))
        return [subst(x) for x in e]

    checks = []
    if bm.inv_constraint is not None:
        inv, pre, trans, post = bm.inv_constraint
        vs = [consts[n] for n, _ in primed]
        ps = [consts[n + "!"] for n, _ in primed]
        inv_v = app(inv, vs)
        inv_p = app(inv, ps)
        checks.append(("initiation",
                       f"(not (=> {app(pre, vs)} {inv_v}))"))
        checks.append(("consecution",
                       f"(not (=> (and {inv_v} {app(trans, vs + ps)}) {inv_p}))"))
        checks.append(("safety",
                       f"(not (=> {inv_v} {app(post, vs)}))"))
    else:
        cons = [render(subst(c)) for c in bm.constraints]
        if not cons:
            # No constraints: any well-formed solution is correct.
            return "\n".join(lines), []
        body = cons[0] if len(cons) == 1 else "(and " + " ".join(cons) + ")"
        checks.append(("spec", f"(not {body})"))
    return "\n".join(lines), checks


def semantic_check(bm, sol_defs, cvc5=CVC5_CHECK,
                   timeout_ms=VERIFY_TIMEOUT_MS):
    """(ok, reason). Runs the pristine cvc5 on the negated spec."""
    script, checks = _check_script(bm, sol_defs)
    if not checks:
        # Nothing to verify (no constraints); parsing by cvc5 still
        # worthwhile to catch ill-sorted bodies.
        script += "\n(check-sat)\n"
        queries = [("well-formedness", None)]
    else:
        queries = checks
    with tempfile.TemporaryDirectory(prefix="sygus-verify-") as td:
        for label, negated in queries:
            q = script + (f"\n(assert {negated})\n(check-sat)\n"
                          if negated is not None else "")
            path = os.path.join(td, "q.smt2")
            with open(path, "w") as f:
                f.write(q)
            try:
                p = subprocess.run(
                    [cvc5, "--lang=smt2", f"--tlimit={timeout_ms}", path],
                    capture_output=True, text=True,
                    timeout=timeout_ms / 1000 + 15)
            except subprocess.TimeoutExpired:
                return False, f"verification timed out ({label})"
            ans = (p.stdout or "").strip().splitlines()
            ans = ans[0].strip() if ans else ""
            if negated is None:
                if p.returncode != 0:
                    tail = ((p.stdout or "") + (p.stderr or ""))[-300:]
                    return False, f"verification script rejected: {tail}"
                continue
            if p.returncode != 0:
                tail = ((p.stdout or "") + (p.stderr or ""))[-300:]
                return False, f"verifier error ({label}): {tail}"
            if ans == "unsat":
                continue
            if ans == "sat":
                return False, f"solution violates the spec ({label})"
            return False, f"verifier returned {ans!r} ({label})"
    return True, None


# --------------------------------------------------------------------------
# Top-level check
# --------------------------------------------------------------------------

def check_answer(benchmark_path, solver_output, cvc5=CVC5_CHECK,
                 timeout_ms=VERIFY_TIMEOUT_MS):
    """Full two-step check. Returns (True, None) or (False, reason)."""
    try:
        bm = parse_benchmark(benchmark_path)
    except (ValueError, OSError) as e:
        return False, f"benchmark parse error: {e}"
    defs, err = parse_solution(solver_output)
    if err is not None:
        # Single-synth-fun convenience: a bare body term.
        if len(bm.synth_funs) == 1 and solver_output.strip() and \
                solver_output.strip().lower() not in ("fail", "unknown",
                                                      "infeasible"):
            try:
                body = parse_sexprs(solver_output)
            except ValueError:
                body = None
            if body is not None and len(body) == 1:
                s = bm.synth_funs[0]
                defs = [(s.name, list(s.params), s.ret_sort, body[0])]
                err = None
    if err is not None:
        return False, err
    solmap = {}
    ordered = []
    for name, params, sort, body in defs:
        if name in solmap:
            return False, f"define-fun {name} given twice"
        solmap[name] = (params, sort, body)
        ordered.append((name, params, sort, body))
    bench_defs = {str(e[1]) for e in bm.define_funs}
    for s in bm.synth_funs:
        if s.name not in solmap:
            return False, f"no define-fun for synth-fun {s.name}"
        params, sort, body = solmap[s.name]
        if render(sort) != render(s.ret_sort):
            return False, f"return sort mismatch for {s.name}"
        ok, reason = grammar_check(s, params, body)
        if not ok:
            return False, f"grammar check failed for {s.name}: {reason}"
    for name in solmap:
        if name in bench_defs:
            return False, f"solution redefines benchmark macro {name}"
    return semantic_check(bm, ordered, cvc5=cvc5, timeout_ms=timeout_ms)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"usage: {sys.argv[0]} BENCHMARK.sl SOLUTION_FILE|-",
              file=sys.stderr)
        sys.exit(2)
    out = sys.stdin.read() if sys.argv[2] == "-" else open(sys.argv[2]).read()
    ok, reason = check_answer(sys.argv[1], out)
    print("VALID" if ok else f"INVALID: {reason}")
    sys.exit(0 if ok else 1)
