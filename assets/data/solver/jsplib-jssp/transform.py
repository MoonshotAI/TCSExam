"""Frozen job/machine permutation and original project input generator."""

import argparse

import hashlib

import json

import os

import random

import sys

SEED_TAG = "tcshard-transform-20260831"

TRANSFORM_ID = "jssp-job-machine-relabel-v1"

def derive_seed(name):
    h = hashlib.sha256((SEED_TAG + ":" + name).encode()).digest()
    return int.from_bytes(h[:8], "big")

def parse_instance(path):
    with open(path) as f:
        vals = f.read().split()
    n, m = int(vals[0]), int(vals[1])
    need = 2 + 2 * n * m
    if len(vals) != need:
        raise ValueError(f"{path}: expected {need} tokens, found {len(vals)}")
    ops = []
    i = 2
    for j in range(n):
        row = []
        for k in range(m):
            row.append((int(vals[i]), int(vals[i + 1])))
            i += 2
        ops.append(row)
    for j in range(n):
        for k in range(m):
            if not (0 <= ops[j][k][0] < m):
                raise ValueError(f"{path}: machine id out of range")
    return n, m, ops

def serialize(n, m, ops):
    out = [f"{n} {m}\n"]
    for row in ops:
        out.append(" ".join(f"{a} {b}" for a, b in row) + "\n")
    return "".join(out).encode()

def transform_instance(name, n, m, ops):
    """Return (new_ops, rho, mu); rho[old_job]=new_row, mu[old_mach]=new_id,
    all 0-based."""
    rng = random.Random(derive_seed(name))
    rho = list(range(n))
    rng.shuffle(rho)
    mu = list(range(m))
    rng.shuffle(mu)
    new_ops = [None] * n
    for j in range(n):
        new_ops[rho[j]] = [(mu[mach], dur) for mach, dur in ops[j]]
    return new_ops, rho, mu

def params_hash(rho, mu):
    """置换参数哈希：codename-map 里登记的是它，完整置换表只活在
    transform_manifest.json（仓外保密）。"""
    blob = json.dumps({"perm_jobs_new_from_old": rho,
                       "perm_machines_new_from_old": mu},
                      separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()

def generate_instance(argv):
    fam, n, m, seed, out = argv[1], int(argv[2]), int(argv[3]), int(argv[4]), argv[5]
    if fam == "ta":
        lo, hi = 1, 99
    elif fam == "dmu":
        lo, hi = 1, 200
    else:
        raise SystemExit(f"unknown family {fam}")
    rng = random.Random(seed)
    routes = []
    for _ in range(n):
        r = list(range(m))
        rng.shuffle(r)
        routes.append(r)
    durs = [[rng.randint(lo, hi) for _ in range(m)] for _ in range(n)]
    with open(out, "w") as f:
        f.write(f"{n} {m}\n")
        for j in range(n):
            f.write(" ".join(f"{routes[j][k]} {durs[j][k]}"
                             for k in range(m)) + "\n")
