"""Original MSE new-to-classic input conversion with its original comments and order."""
def convert(inp, outp):
    hard = []
    soft = []
    comments = []
    n = 0
    with open(inp, 'rb') as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            if line[:1] == b'c':
                comments.append(line.decode('ascii', 'replace'))
                continue
            if line[:1] == b'p':
                continue
            toks = line.split()
            if toks[0] == b'h':
                lits = [int(t) for t in toks[1:] if int(t) != 0]
                hard.append(lits)
            else:
                w = int(toks[0])
                lits = [int(t) for t in toks[1:] if int(t) != 0]
                soft.append((w, lits))
            for l in hard[-1] if toks[0] == b'h' else soft[-1][1]:
                v = abs(l)
                if v > n:
                    n = v
    sumw = sum((w for (w, _) in soft))
    if sumw + 1 >= 1 << 63:
        raise ValueError(f'sum of soft weights {sumw} too large for int64 top')
    top = sumw + 1
    m = len(hard) + len(soft)
    with open(outp, 'w') as f:
        f.write(f'c converted from MSE new format (h-lines, no p-line)\n')
        for c in comments:
            f.write(c + '\n')
        f.write(f'p wcnf {n} {m} {top}\n')
        for lits in hard:
            f.write(f"{top} {' '.join(map(str, lits))} 0\n")
        for (w, lits) in soft:
            f.write(f"{w} {' '.join(map(str, lits))} 0\n")
