"""Original input-only SyGuS1-to-2 conversion and parser; no answer checking."""
import re
import types

_TOKEN_RE = re.compile('\n    \\s*(?:\n    (?P<comment>;[^\\n]*)\n  | (?P<lp>\\()\n  | (?P<rp>\\))\n  | (?P<str>"(?:[^"\\\\]|\\\\.)*")\n  | (?P<bar>\\|[^|]*\\|)\n  | (?P<atom>[^\\s()";|]+)\n    )', re.VERBOSE)

def tokenize(text):
    (pos, n) = (0, len(text))
    while pos < n:
        if not text[pos:].strip():
            break
        m = _TOKEN_RE.match(text, pos)
        if not m:
            raise ValueError(f'tokenize error at offset {pos}')
        pos = m.end()
        if m.group('comment') is not None:
            continue
        for kind in ('lp', 'rp', 'str', 'bar', 'atom'):
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
    for (kind, v) in tokenize(text):
        if kind == 'lp':
            stack.append([])
        elif kind == 'rp':
            if not stack:
                raise ValueError("unbalanced ')'")
            done = stack.pop()
            if stack:
                stack[-1].append(done)
            else:
                top.append(done)
        elif stack:
            stack[-1].append(Sx(v))
        else:
            top.append(Sx(v))
    if stack:
        raise ValueError("unbalanced '('")
    return top

def render(x):
    if isinstance(x, list):
        return '(' + ' '.join((render(y) for y in x)) + ')'
    return str(x)

def is_atom(x):
    return isinstance(x, Sx)

class SynthFun:

    def __init__(self, name, params, ret_sort, grammar, is_inv):
        self.name = name
        self.params = params
        self.ret_sort = ret_sort
        self.grammar = grammar
        self.is_inv = is_inv

class Benchmark:

    def __init__(self):
        self.logic = None
        self.define_funs = []
        self.declare_funs = []
        self.declare_vars = []
        self.primed_vars = []
        self.synth_funs = []
        self.constraints = []
        self.inv_constraint = None
        self.set_options = []
        self.has_check_synth = False

def _param_list(sexpr):
    out = []
    for p in sexpr:
        if not (isinstance(p, list) and len(p) == 2):
            raise ValueError(f'bad parameter {render(p)}')
        out.append((str(p[0]), p[1]))
    return out

def _grammar(sexpr):
    """sexpr: ((NT Sort (prod ...)) ...). Returns [(nt, sort, [prods])]."""
    out = []
    for g in sexpr:
        if not (isinstance(g, list) and len(g) == 3 and isinstance(g[2], list)):
            raise ValueError(f'bad grammar entry {render(g)}')
        out.append((str(g[0]), g[1], list(g[2])))
    if not out:
        raise ValueError('grammar with no non-terminals')
    return out

def parse_benchmark(path):
    with open(path, errors='replace') as f:
        text = f.read()
    bm = Benchmark()
    for e in parse_sexprs(text):
        if not isinstance(e, list) or not e or (not is_atom(e[0])):
            raise ValueError(f'bad top-level command {render(e)[:80]}')
        head = str(e[0])
        if head == 'set-logic' and len(e) == 2:
            bm.logic = str(e[1])
        elif head == 'set-option':
            bm.set_options.append(e)
        elif head == 'set-info' or head == 'set-options':
            pass
        elif head == 'define-fun':
            bm.define_funs.append(e)
        elif head == 'declare-fun' or head == 'declare-sort' or head == 'define-sort':
            bm.declare_funs.append(e)
        elif head == 'declare-var' and len(e) == 3:
            bm.declare_vars.append((str(e[1]), e[2]))
        elif head == 'declare-primed-var' and len(e) == 3:
            bm.primed_vars.append((str(e[1]), e[2]))
        elif head in ('synth-fun', 'synth-inv'):
            is_inv = head == 'synth-inv'
            min_len = 3 if is_inv else 4
            if len(e) < min_len:
                raise ValueError(f'{head}: bad arity')
            ret = Sx('Bool') if is_inv else e[3]
            grammar = None
            for g in e[min_len:]:
                if not isinstance(g, list) or not g:
                    raise ValueError('bad grammar section')
                if all((isinstance(x, list) and len(x) == 2 for x in g)):
                    continue
                grammar = _grammar(g)
            bm.synth_funs.append(SynthFun(str(e[1]), _param_list(e[2]), ret, grammar, is_inv=is_inv))
        elif head == 'constraint' and len(e) == 2:
            bm.constraints.append(e[1])
        elif head == 'inv-constraint' and len(e) == 5:
            bm.inv_constraint = tuple((str(x) for x in e[1:5]))
        elif head == 'check-synth':
            bm.has_check_synth = True
        else:
            raise ValueError(f'unsupported command {head}')
    if not bm.has_check_synth:
        raise ValueError('no (check-synth)')
    if not bm.synth_funs:
        raise ValueError('no synth-fun')
    return bm

sc = types.SimpleNamespace(**{name: globals()[name] for name in ['Benchmark', 'Sx', 'SynthFun', '_grammar', '_param_list', 'is_atom', 'parse_benchmark', 'parse_sexprs', 'render', 'tokenize']})


Sx = sc.Sx

_OP_RENAMES = {'int.to.str': 'str.from_int', 'str.to.int': 'str.to_int'}

def norm_sort(s):
    if isinstance(s, list):
        if len(s) == 2 and str(s[0]) == 'BitVec':
            return [Sx('_'), Sx('BitVec'), s[1]]
        return [norm_sort(x) for x in s]
    return s

def norm_term(e):
    """Rename draft operators and strip v1 sort annotations from let
    bindings ((v Sort term) -> (v term)) inside terms (constraints,
    define-fun bodies)."""
    if isinstance(e, list):
        if e and str(e[0]) == 'let' and (len(e) == 3) and isinstance(e[1], list):
            binds = []
            for b in e[1]:
                if isinstance(b, list) and len(b) >= 2:
                    binds.append([b[0], norm_term(b[-1])])
                else:
                    binds.append(b)
            return [Sx('let'), binds, norm_term(e[2])]
        return [norm_term(x) for x in e]
    return Sx(_OP_RENAMES.get(str(e), str(e)))

def norm_gterm(e):
    """Grammar production normalization: operator renames + let bindings
    lose their v1 sort annotation ((v Sort g) -> (v g))."""
    if isinstance(e, list):
        if e and str(e[0]) == 'let' and (len(e) == 3) and isinstance(e[1], list):
            binds = []
            for b in e[1]:
                if isinstance(b, list) and len(b) >= 2:
                    binds.append([b[0], norm_gterm(b[-1])])
                else:
                    binds.append(b)
            return [Sx('let'), binds, norm_gterm(e[2])]
        if len(e) == 2 and str(e[0]) in ('Constant', 'Variable', 'InputVariable', 'LocalVariable'):
            return [e[0], norm_sort(e[1])]
        return [norm_gterm(x) for x in e]
    return Sx(_OP_RENAMES.get(str(e), str(e)))

def norm_params(params):
    return [(n, norm_sort(s)) for (n, s) in params]

def convert(inp, outp):
    bm = sc.parse_benchmark(inp)
    lines = []
    lines.append(f'(set-logic {bm.logic})' if bm.logic else '')
    for e in bm.declare_funs:
        head = str(e[0])
        if head == 'declare-fun' and len(e) == 4:
            args = ' '.join((sc.render(norm_sort(a)) for a in e[2]))
            lines.append(f'(declare-fun {e[1]} ({args}) {sc.render(norm_sort(e[3]))})')
        else:
            lines.append(sc.render(e))
    for e in bm.define_funs:
        ps = ' '.join((f'({n} {sc.render(norm_sort(s))})' for (n, s) in sc._param_list(e[2])))
        lines.append(f'(define-fun {e[1]} ({ps}) {sc.render(norm_sort(e[3]))} {sc.render(norm_term(e[4]))})')
    for (name, sort) in bm.declare_vars:
        lines.append(f'(declare-var {name} {sc.render(norm_sort(sort))})')
    for s in bm.synth_funs:
        head = 'synth-inv' if s.is_inv else 'synth-fun'
        ps = ' '.join((f'({n} {sc.render(t)})' for (n, t) in norm_params(s.params)))
        sig = f'({head} {s.name} ({ps})'
        if not s.is_inv:
            sig += f' {sc.render(norm_sort(s.ret_sort))}'
        if s.grammar is None:
            lines.append(sig + ')')
        else:
            grammar = [(nt, norm_sort(t), [norm_gterm(p) for p in prods]) for (nt, t, prods) in s.grammar]
            decls = ' '.join((f'({nt} {sc.render(t)})' for (nt, t, _) in grammar))
            rules = []
            for (nt, t, prods) in grammar:
                rules.append(f"({nt} {sc.render(t)} ({' '.join((sc.render(p) for p in prods))}))")
            lines.append(sig + f" ({decls}) ({' '.join(rules)}))")
    for c in bm.constraints:
        lines.append(f'(constraint {sc.render(norm_term(c))})')
    if bm.inv_constraint is not None:
        lines.append('(inv-constraint ' + ' '.join(bm.inv_constraint) + ')')
    lines.append('(check-synth)')
    text = '\n'.join((l for l in lines if l)) + '\n'
    with open(outp, 'w') as f:
        f.write(text)
    bm2 = sc.parse_benchmark(outp)
    assert len(bm2.synth_funs) == len(bm.synth_funs)
    assert len(bm2.constraints) == len(bm.constraints)
    assert (bm2.inv_constraint is None) == (bm.inv_constraint is None)
    for (a, b) in zip(bm.synth_funs, bm2.synth_funs):
        assert a.name == b.name and len(a.params) == len(b.params)
        assert (a.grammar is None) == (b.grammar is None)
        if a.grammar is not None:
            assert [x[0] for x in a.grammar] == [x[0] for x in b.grammar]
