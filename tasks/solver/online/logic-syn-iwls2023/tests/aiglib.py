#!/usr/bin/env python3
"""AIGER (binary) parser + truth-table utilities for logic-syn-iwls2023.

Self-contained, zero third-party deps. Used by:
  - judge-side checker (validate submitted AIG vs truth table, count ANDs)
  - K-anchor verification (re-verify contest submissions)
  - NPN transformation tooling (hidden-set hardening)

Truth-table convention (.truth file): each non-empty line is one output;
line length = 2^n chars over {0,1}. PINNED EMPIRICALLY against ABC's
`read_truth -xf` (2026-08-28, tiny probes + full submission sweep):
  - char at position p from the LEFT = value at minterm (2^n - 1 - p),
    i.e. the string is MSB-first (first char = all-ones assignment);
  - within a minterm index t, input x_i is bit i (x0 = LSB).
Internally every truth mask has bit t = value at minterm t (LSB-first).
"""


# ---------------------------------------------------------------- AIGER ----
class AigerError(Exception):
    pass


class Aig:
    """Parsed binary AIGER: inputs are literals 2..2I+1; ands[i] = (lhs, r0, r1)."""

    def __init__(self):
        self.n_inputs = 0
        self.outputs = []      # list of literals
        self.ands = []         # list of (lhs_lit, rhs0_lit, rhs1_lit), lhs ascending
        self.maxvar = 0

    @property
    def n_ands(self):
        return len(self.ands)


def _read_uint(data, pos):
    """AIGER variable-length uint encoding: 7 bits per byte, LSB groups first."""
    x = 0
    shift = 0
    while True:
        if pos >= len(data):
            raise AigerError("unexpected end of file in delta encoding")
        b = data[pos]
        pos += 1
        x |= (b & 0x7F) << shift
        if not (b & 0x80):
            return x, pos
        shift += 7
        if shift > 63:
            raise AigerError("delta encoding too large")


def parse_aiger(data, max_and=2_000_000):
    """Parse+validate binary AIGER for a COMBINATIONAL circuit.

    Rejects: ASCII format, latches, bad/constraint/justice/fairness sections,
    out-of-range literals, non-topological fanin, wrong header arithmetic.
    Returns Aig. Raises AigerError on any violation.
    """
    if not data.startswith(b"aig "):
        raise AigerError("not binary AIGER (must start with 'aig ')")
    nl = data.find(b"\n")
    if nl < 0:
        raise AigerError("truncated header")
    try:
        fields = data[4:nl].decode("ascii").split()
        nums = [int(t) for t in fields]
    except (ValueError, UnicodeDecodeError):
        raise AigerError("malformed header")
    if len(nums) < 5:
        raise AigerError("header needs M I L O A")
    M, I, L, O, A = nums[:5]
    if len(nums) > 5 and any(v != 0 for v in nums[5:]):
        raise AigerError("B/C/J/F sections not allowed (sequential/property AIGER)")
    if L != 0:
        raise AigerError("latches not allowed (combinational circuits only)")
    if M != I + A:
        raise AigerError(f"header arithmetic wrong: M({M}) != I({I}) + A({A})")
    if not (0 <= I <= 64 and 0 <= O <= 10000):
        raise AigerError("unreasonable I/O counts")
    if not (0 <= A <= max_and):
        raise AigerError(f"AND-gate count {A} exceeds limit {max_and}")
    pos = nl + 1
    aig = Aig()
    aig.n_inputs = I
    aig.maxvar = M
    # O output lines (ASCII, one literal each); no latch lines since L == 0.
    for _ in range(O):
        eol = data.find(b"\n", pos)
        if eol < 0:
            raise AigerError("truncated output section")
        try:
            lit = int(data[pos:eol].decode("ascii").strip())
        except ValueError:
            raise AigerError("malformed output literal")
        if not (0 <= lit <= 2 * M + 1):
            raise AigerError(f"output literal {lit} out of range")
        aig.outputs.append(lit)
        pos = eol + 1
    # A AND gates, delta encoded: lhs = 2*(I+a), delta0 = lhs-rhs0, delta1 = rhs0-rhs1
    for a in range(1, A + 1):
        lhs = 2 * (I + a)
        d0, pos = _read_uint(data, pos)
        d1, pos = _read_uint(data, pos)
        rhs0 = lhs - d0
        rhs1 = rhs0 - d1
        if d0 < 1 or d1 < 0 or rhs1 < 0:
            raise AigerError(f"gate {a}: non-topological or negative fanin")
        if rhs0 > lhs - 1:
            raise AigerError(f"gate {a}: fanin not strictly smaller")
        aig.ands.append((lhs, rhs0, rhs1))
    # Remaining bytes: optional symbol table + comment section — syntax check
    # only, content ignored. Must be printable ASCII lines.
    rest = data[pos:]
    if rest:
        try:
            rest.decode("ascii")
        except UnicodeDecodeError:
            raise AigerError("garbage after AND section")
    return aig


def write_aiger(aig):
    """Serialize Aig to binary AIGER (canonical: rhs0 >= rhs1)."""
    I, O, A = aig.n_inputs, len(aig.outputs), len(aig.ands)
    M = I + A
    out = bytearray(f"aig {M} {I} 0 {O} {A}\n".encode())
    for lit in aig.outputs:
        if not (0 <= lit <= 2 * M + 1):
            raise AigerError("output literal out of range on write")
        out += f"{lit}\n".encode()
    for idx, (lhs, r0, r1) in enumerate(aig.ands, start=1):
        want = 2 * (I + idx)
        if lhs != want:
            raise AigerError("non-canonical lhs ordering")
        if r0 < r1:
            r0, r1 = r1, r0
        if not (0 <= r1 <= r0 < lhs):
            raise AigerError("fanin out of range on write")
        for d in (lhs - r0, r0 - r1):
            while True:
                b = d & 0x7F
                d >>= 7
                if d:
                    out.append(b | 0x80)
                else:
                    out.append(b)
                    break
    return bytes(out)


# ---------------------------------------------------------------- truth ----
def parse_truth(text):
    """Parse .truth file -> (n_inputs, [output bitmask per line]).

    Bit t of each mask = value of the output at minterm t, where minterm t
    has input i as bit i (t = sum x_i 2^i, x0 = LSB). File chars are
    MSB-first: the first character of a line is the value at the all-ones
    assignment (minterm 2^n - 1); the last character is minterm 0.
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        raise ValueError("empty truth file")
    widths = {len(l) for l in lines}
    if len(widths) != 1:
        raise ValueError(f"ragged truth file: line lengths {sorted(widths)}")
    L = widths.pop()
    if L < 2 or L & (L - 1):
        raise ValueError(f"line length {L} is not a power of two >= 2")
    n = L.bit_length() - 1
    if n > 20:
        raise ValueError(f"too many inputs ({n})")
    masks = []
    for l in lines:
        if set(l) - {"0", "1"}:
            raise ValueError("non-binary character in truth file")
        m = 0
        # char at position p from the left = value at minterm (L-1-p).
        for p, ch in enumerate(l):
            if ch == "1":
                m |= 1 << (L - 1 - p)
        masks.append(m)
    return n, masks


def input_pattern(i, n):
    """Bitmask over 2^n minterms with bit t = (t >> i) & 1."""
    # Build via repeated block: 2^i zeros then 2^i ones, repeated.
    block = ((1 << (1 << i)) - 1) << (1 << i)
    period = 1 << (i + 1)
    total = 1 << n
    pat = 0
    reps = total // period
    for r in range(reps):
        pat |= block << (r * period)
    return pat


_FULL = {}


def full_mask(n):
    if n not in _FULL:
        _FULL[n] = (1 << (1 << n)) - 1
    return _FULL[n]


def simulate(aig, n):
    """Simulate combinational Aig on all 2^n input patterns.

    Returns list of output bitmasks (bit t = output value at minterm t).
    Memory: fanout-refcount freeing keeps only live node values.
    """
    size = 1 << n
    if size > (1 << 20):
        raise ValueError("simulation limited to <=20 inputs")
    full = full_mask(n)
    n_nodes = 1 + aig.maxvar
    # fanout counts
    fanout = [0] * n_nodes

    def var(lit):
        return lit >> 1

    for lit in aig.outputs:
        fanout[var(lit)] += 1
    for _, r0, r1 in aig.ands:
        fanout[var(r0)] += 1
        fanout[var(r1)] += 1
    values = {}

    def value(lit):
        v = var(lit)
        if v == 0:
            base = 0
        elif v <= aig.n_inputs:
            base = input_pattern(v - 1, n)
        else:
            base = values[v]
        return (~base & full) if (lit & 1) else base

    def release(lit):
        v = var(lit)
        if v > aig.n_inputs:
            fanout[v] -= 1
            if fanout[v] == 0:
                values.pop(v, None)

    for lhs, r0, r1 in aig.ands:
        v0 = value(r0)
        v1 = value(r1)
        values[lhs >> 1] = v0 & v1
        release(r0)
        release(r1)
    return [value(lit) for lit in aig.outputs]


def check_circuit(aig, n, masks):
    """None iff AIG computes exactly the given truth masks; else error string."""
    if aig.n_inputs != n:
        return f"input count mismatch: circuit {aig.n_inputs}, truth {n}"
    if len(aig.outputs) != len(masks):
        return f"output count mismatch: circuit {len(aig.outputs)}, truth {len(masks)}"
    got = simulate(aig, n)
    for j, (g, w) in enumerate(zip(got, masks)):
        if g != w:
            return f"output {j}: functionally different"
    return None


# ------------------------------------------------------------------ NPN ----
def write_truth(n, masks):
    """Serialize masks back to .truth text (MSB-first, one line per output)."""
    L = 1 << n
    out = []
    for m in masks:
        out.append("".join("1" if (m >> (L - 1 - p)) & 1 else "0"
                           for p in range(L)))
    return "\n".join(out) + "\n"


def npn_transform_truth(n, masks, in_perm, in_neg, out_perm, out_neg):
    """Apply an NPN transformation to a truth table.

    in_perm[i] = new input index that feeds old input i;
    in_neg[i]  = 1 if old input i is fed negated;
    out_perm[j] = old output index that becomes new output j;
    out_neg[j]  = 1 if that output is negated.
    Returns new mask list (same length).
    """
    assert sorted(in_perm) == list(range(n))
    assert len(in_neg) == n
    assert sorted(out_perm) == list(range(len(masks)))
    assert len(out_neg) == len(masks)
    size = 1 << n
    full = full_mask(n)
    # For each new minterm t, compute the old minterm u.
    old_of_t = [0] * size
    for t in range(size):
        u = 0
        for i in range(n):
            bit = ((t >> in_perm[i]) & 1) ^ in_neg[i]
            u |= bit << i
        old_of_t[t] = u
    new_masks = []
    for j in range(len(masks)):
        src = masks[out_perm[j]]
        g = 0
        for t in range(size):
            g |= ((src >> old_of_t[t]) & 1) << t
        if out_neg[j]:
            g ^= full
        new_masks.append(g)
    return new_masks


def npn_transform_aig(aig, in_perm, in_neg, out_perm, out_neg):
    """Apply the same NPN transformation to an AIG (node count unchanged)."""
    n = aig.n_inputs
    assert sorted(in_perm) == list(range(n))

    def map_lit(lit):
        v, s = lit >> 1, lit & 1
        if v == 0:
            return lit  # constant
        if v <= n:  # input i = v-1
            i = v - 1
            return 2 * (in_perm[i] + 1) + (s ^ in_neg[i])
        return lit  # AND-gate literal: variable indices unchanged

    new = Aig()
    new.n_inputs = n
    new.maxvar = aig.maxvar
    new.ands = [(lhs, map_lit(r0), map_lit(r1)) for lhs, r0, r1 in aig.ands]
    new.outputs = [map_lit(aig.outputs[out_perm[j]]) ^ out_neg[j]
                   for j in range(len(aig.outputs))]
    return new
