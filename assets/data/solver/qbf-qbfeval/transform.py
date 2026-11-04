"""Original QDIMACS input transformation; no proof or answer processing."""

import argparse

import hashlib

import json

import os

import random

import subprocess

import sys

MASTER_SEED_TAG = 'tcshard-transform-20260831'

TRANSFORM_ID = 'qbf-block-relabel-v1'

SEED_RULE = "seed = int.from_bytes(sha256('tcshard-transform-20260831:' + name)[:8], 'big'); rng = random.Random(seed); consumption order: per-block variable-list shuffles (prefix order), literal shuffles (original clause order), clause-order shuffle"

def derive_seed(name):
    h = hashlib.sha256(f'{MASTER_SEED_TAG}:{name}'.encode())
    return int.from_bytes(h.digest()[:8], 'big')

def read_qdimacs(path):
    """-> (plain, nvars, prefix, clauses). prefix = [(q, [vars])]."""
    if path.endswith('.xz'):
        plain = subprocess.run(['xz', '-dc', path], capture_output=True, check=True).stdout
    else:
        with open(path, 'rb') as f:
            plain = f.read()
    nvars = None
    prefix = []
    clauses = []
    cur = []
    for line in plain.split(b'\n'):
        line = line.strip()
        if not line or line.startswith(b'c'):
            continue
        if line.startswith(b'p'):
            parts = line.split()
            if len(parts) >= 4 and parts[1] == b'cnf':
                nvars = int(parts[2])
            continue
        if line[:2] in (b'a ', b'e ') or line in (b'a', b'e'):
            parts = line.split()
            prefix.append((parts[0].decode(), [int(t) for t in parts[1:] if t != b'0']))
            continue
        if line.startswith(b'%'):
            break
        for tok in line.split():
            lit = int(tok)
            if lit == 0:
                if cur:
                    clauses.append(cur)
                    cur = []
            else:
                cur.append(lit)
    if cur:
        clauses.append(cur)
    if nvars is None:
        nvars = max((abs(l) for c in clauses for l in c), default=0)
    return (plain, nvars, prefix, clauses)

def make_block_perms(prefix, seed):
    """-> (var->new-label map, per-block permutations for the manifest).

    RNG consumption: one shuffle per block, in prefix order, over the
    variable list as written in the instance."""
    rng = random.Random(seed)
    vmap = {}
    blocks = []
    for (q, vars_) in prefix:
        shuffled = list(vars_)
        rng.shuffle(shuffled)
        for (old, new) in zip(vars_, shuffled):
            if old in vmap:
                raise ValueError(f'variable {old} quantified twice')
            vmap[old] = new
        blocks.append({'quant': q, 'perm_new_from_old': shuffled, 'vars_orig_order': vars_})
    return (vmap, blocks, rng)

def transform_instance(nvars, prefix, clauses, seed):
    (vmap, blocks, rng) = make_block_perms(prefix, seed)
    new_clauses = []
    for clause in clauses:
        renamed = []
        for lit in clause:
            v = abs(lit)
            if v not in vmap:
                raise ValueError(f'matrix literal {lit} not quantified')
            renamed.append((1 if lit > 0 else -1) * vmap[v])
        rng.shuffle(renamed)
        new_clauses.append(renamed)
    rng.shuffle(new_clauses)
    return (new_clauses, vmap, blocks)

def serialize(nvars, prefix, clauses):
    out = [f'p cnf {nvars} {len(clauses)}\n']
    for (q, vars_) in prefix:
        out.append(q + ' ' + ' '.join(map(str, vars_)) + ' 0\n')
    for clause in clauses:
        out.append(' '.join(map(str, clause)) + ' 0\n')
    return ''.join(out).encode()
