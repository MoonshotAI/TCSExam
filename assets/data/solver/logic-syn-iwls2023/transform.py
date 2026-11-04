"""Original truth-table input/output relabeling, with saved permutations."""

_FULL = {}

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

def full_mask(n):
    if n not in _FULL:
        _FULL[n] = (1 << (1 << n)) - 1
    return _FULL[n]

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
