"""Original input-only weighted-clause relabeling; historical seed label retained."""
import hashlib
import random
import subprocess
MASTER_SEED_TAG = 'tcshard-transform-20260831'

def derive_seed(name):
    h = hashlib.sha256(f'{MASTER_SEED_TAG}:{name}'.encode())
    return int.from_bytes(h.digest()[:8], 'big')

def read_wcnf(path):
    """-> (plain, n, top, clauses) with clauses = [(weight, [lits])]."""
    if path.endswith('.xz'):
        plain = subprocess.run(['xz', '-dc', path], capture_output=True, check=True).stdout
    else:
        with open(path, 'rb') as f:
            plain = f.read()
    n = None
    top = None
    clauses = []
    for line in plain.split(b'\n'):
        line = line.strip()
        if not line or line.startswith(b'c'):
            continue
        if line.startswith(b'p'):
            parts = line.split()
            if len(parts) >= 5 and parts[1] == b'wcnf':
                n = int(parts[2])
                top = int(parts[4])
            continue
        parts = line.split()
        try:
            w = int(parts[0])
        except (ValueError, IndexError):
            continue
        lits = []
        for tok in parts[1:]:
            lit = int(tok)
            if lit == 0:
                break
            lits.append(lit)
        clauses.append((w, lits))
    if n is None or top is None:
        raise ValueError(f'bad wcnf header in {path}')
    return (plain, n, top, clauses)

def transform_clauses(n, clauses, seed):
    rng = random.Random(seed)
    perm = list(range(1, n + 1))
    rng.shuffle(perm)
    perm = [None] + perm
    new_clauses = []
    for (w, lits) in clauses:
        renamed = [(1 if lit > 0 else -1) * perm[abs(lit)] for lit in lits]
        rng.shuffle(renamed)
        new_clauses.append((w, renamed))
    rng.shuffle(new_clauses)
    return (new_clauses, perm)

def serialize(n, top, clauses):
    out = [f'p wcnf {n} {len(clauses)} {top}\n']
    for (w, lits) in clauses:
        out.append(f'{w} ' + ' '.join(map(str, lits)) + ' 0\n')
    return ''.join(out).encode()
