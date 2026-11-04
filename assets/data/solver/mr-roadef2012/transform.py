"""Original machine-reassignment input-only relabeling, with saved permutations."""

import hashlib

import json

import os

import random

import sys

def derive_orders(name, nM, nR, nS, nP, nB, nNei, nLoc):
    """Fixed consumption order — reproduces every permutation from the seed."""
    h = hashlib.sha256(f'tcshard-transform-20260831:{name}'.encode()).digest()
    rng = random.Random(int.from_bytes(h[:8], 'big'))

    def sh(n):
        v = list(range(n))
        rng.shuffle(v)
        return v
    orders = {'mOrder': sh(nM), 'rOrder': sh(nR), 'sOrder': sh(nS), 'pOrder': sh(nP), 'balOrder': sh(nB), 'neiPerm': sh(nNei), 'locPerm': sh(nLoc)}
    return (orders, h.hex()[:16])

def invert(order):
    inv = [0] * len(order)
    for (new, old) in enumerate(order):
        inv[old] = new
    return inv

def parse_model(path):
    with open(path) as f:
        toks = f.read().split()
    pos = [0]

    def nxt():
        v = int(toks[pos[0]])
        pos[0] += 1
        return v
    nR = nxt()
    resources = [(nxt(), nxt()) for _ in range(nR)]
    nM = nxt()
    machines = []
    for _ in range(nM):
        (nei, loc) = (nxt(), nxt())
        cap = [nxt() for _ in range(nR)]
        saf = [nxt() for _ in range(nR)]
        mc = [nxt() for _ in range(nM)]
        machines.append((nei, loc, cap, saf, mc))
    nS = nxt()
    services = []
    for _ in range(nS):
        (sm, nd) = (nxt(), nxt())
        services.append((sm, [nxt() for _ in range(nd)]))
    nP = nxt()
    procs = []
    for _ in range(nP):
        s = nxt()
        req = [nxt() for _ in range(nR)]
        procs.append((s, req, nxt()))
    nB = nxt()
    bals = [(nxt(), nxt(), nxt(), nxt()) for _ in range(nB)]
    weights = (nxt(), nxt(), nxt())
    assert pos[0] == len(toks), f'{path}: trailing tokens'
    return {'nR': nR, 'resources': resources, 'nM': nM, 'machines': machines, 'nS': nS, 'services': services, 'nP': nP, 'procs': procs, 'nB': nB, 'bals': bals, 'weights': weights}

def load_assignment(path):
    with open(path) as f:
        return [int(t) for t in f.read().split()]

def file_sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda : f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

def transform_instance(name, source_directory, saved_orders):
    model0 = parse_model(os.path.join(source_directory, f'model_{name}.txt'))
    assign0 = load_assignment(os.path.join(source_directory, f'assignment_{name}.txt'))
    (nM, nR, nS, nP, nB) = (model0['nM'], model0['nR'], model0['nS'], model0['nP'], model0['nB'])
    assert len(assign0) == nP
    nNei = max((m[0] for m in model0['machines'])) + 1
    nLoc = max((m[1] for m in model0['machines'])) + 1
    (orders, seed_hex) = derive_orders(name, nM, nR, nS, nP, nB, nNei, nLoc)
    (mO, rO, sO, pO, bO) = (orders['mOrder'], orders['rOrder'], orders['sOrder'], orders['pOrder'], orders['balOrder'])
    (neiP, locP) = (orders['neiPerm'], orders['locPerm'])
    (mInv, sInv, rInv) = (invert(mO), invert(sO), invert(rO))
    L = []
    L.append(str(nR))
    for k in range(nR):
        (t, w) = model0['resources'][rO[k]]
        L.append(f'{t} {w}')
    L.append(str(nM))
    for k in range(nM):
        (nei, loc, cap, saf, mc) = model0['machines'][mO[k]]
        row = [neiP[nei], locP[loc]] + [cap[rO[j]] for j in range(nR)] + [saf[rO[j]] for j in range(nR)] + [mc[mO[j]] for j in range(nM)]
        L.append(' '.join(map(str, row)))
    L.append(str(nS))
    for k in range(nS):
        (sm, deps) = model0['services'][sO[k]]
        L.append(' '.join(map(str, [sm, len(deps)] + [sInv[d] for d in deps])))
    L.append(str(nP))
    for k in range(nP):
        (s, req, c) = model0['procs'][pO[k]]
        L.append(' '.join(map(str, [sInv[s]] + [req[rO[j]] for j in range(nR)] + [c])))
    L.append(str(nB))
    for k in range(nB):
        (a, b, t, w) = model0['bals'][bO[k]]
        L.append(f'{rInv[a]} {rInv[b]} {t} {w}')
    L.append(' '.join(map(str, model0['weights'])))
    model1 = '\n'.join(L) + '\n'
    assign1 = ' '.join((str(mInv[assign0[pO[k]]]) for k in range(nP))) + '\n'
    return (model1, assign1, orders, seed_hex)
