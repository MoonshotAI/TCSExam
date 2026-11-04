"""Frozen OR-Library row/column relabeling; original seed strings are retained."""

import argparse

import hashlib

import json

import os

import random

import sys

TRANSFORM_ID = "scp-rowcol-permute-v1"

SEED_PREFIX = "tcshard-transform-20260831:"

def derive_seed(name, suffix=""):
    h = hashlib.sha256((SEED_PREFIX + name + suffix).encode()).digest()
    return int.from_bytes(h[:8], "big")

def load_instance(path):
    """m, n, n costs, then m row blocks (canonical row-major layout)."""
    with open(path) as f:
        vals = f.read().split()
    m, n = int(vals[0]), int(vals[1])
    costs = [int(v) for v in vals[2:2 + n]]
    pos = 2 + n
    rows = []
    for _ in range(m):
        k = int(vals[pos])
        pos += 1
        rows.append([int(v) for v in vals[pos:pos + k]])
        pos += k
    if pos != len(vals):
        raise ValueError(f"trailing tokens in {path}: "
                         f"consumed {pos}, found {len(vals)}")
    for i, row in enumerate(rows):
        for j in row:
            if j < 1 or j > n:
                raise ValueError(f"column {j} out of range in {path} row {i}")
    return m, n, costs, rows

def serialize(m, n, costs, rows):
    """OR-Library style: ' m n ' line, then 12 tokens per physical line."""
    toks = [str(c) for c in costs]
    for row in rows:
        toks.append(str(len(row)))
        toks.extend(str(j) for j in row)
    out = [f" {m} {n} \n"]
    for i in range(0, len(toks), 12):
        out.append(" " + " ".join(toks[i:i + 12]) + " \n")
    return "".join(out).encode()

def transform_instance(name, m, n, costs, rows, suffix=""):
    """Return (new_costs, new_rows, col_perm, row_perm);
    col_perm[old] = new, row_perm[old] = new-position (both 1-based)."""
    rng = random.Random(derive_seed(name, suffix))
    col_perm = [None] + list(range(1, n + 1))
    vals = col_perm[1:]
    rng.shuffle(vals)
    col_perm = [None] + vals
    row_perm = [None] + list(range(1, m + 1))
    vals = row_perm[1:]
    rng.shuffle(vals)
    row_perm = [None] + vals
    new_costs = [None] * (n + 1)
    for old in range(1, n + 1):
        new_costs[col_perm[old]] = costs[old - 1]
    new_costs = new_costs[1:]
    new_rows = [None] * (m + 1)
    for old in range(1, m + 1):
        new_rows[row_perm[old]] = sorted(col_perm[j] for j in rows[old - 1])
    new_rows = new_rows[1:]
    return new_costs, new_rows, col_perm, row_perm

def params_hash(col_perm, row_perm):
    """置换参数哈希：codename-map 里登记的是它，完整置换表只活在
    transform_manifest.json（仓外保密）。"""
    blob = json.dumps({"col_permutation_new_from_old": col_perm[1:],
                       "row_permutation_new_from_old": row_perm[1:]},
                      separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()
