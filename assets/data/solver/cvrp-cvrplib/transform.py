"""Original capacitated routing vertex relabeling and serialization."""

import argparse

import hashlib

import json

import os

import random

import re

import sys

SEED_TAG = "tcshard-transform-20260831"

TRANSFORM_ID = "cvrp-node-relabel-v1"

NEUTRAL_COMMENT = "instance"

def derive_seed(name):
    h = hashlib.sha256((SEED_TAG + ":" + name).encode()).digest()
    return int.from_bytes(h[:8], "big")

def parse_vrp(path):
    """Parse a TSPLIB/CVRPLIB .vrp (EUC_2D only). Returns a dict with raw
    tokens preserved for coordinates/demands (exact round-trip)."""
    with open(path, errors="replace") as f:
        tokens = f.read().split()
    header = {}
    coords = {}
    demand = {}
    depot = None
    section = None
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t == "EOF":
            break
        if t in ("NODE_COORD_SECTION", "DEMAND_SECTION", "DEPOT_SECTION"):
            section = t
            i += 1
            continue
        if section == "NODE_COORD_SECTION":
            coords[int(tokens[i])] = (tokens[i + 1], tokens[i + 2])
            i += 3
            continue
        if section == "DEMAND_SECTION":
            demand[int(tokens[i])] = tokens[i + 1]
            i += 2
            continue
        if section == "DEPOT_SECTION":
            v = int(tokens[i])
            if v != -1:
                depot = v
            i += 1
            continue
        section = None
        key = t
        i += 1
        if i < len(tokens) and tokens[i] == ":":
            i += 1
        if key == "COMMENT":
            val = []
            while i < len(tokens) and tokens[i] not in (
                    "NAME", "COMMENT", "TYPE", "DIMENSION",
                    "EDGE_WEIGHT_TYPE", "CAPACITY", "NODE_COORD_SECTION",
                    "DEMAND_SECTION", "DEPOT_SECTION", "EOF"):
                val.append(tokens[i])
                i += 1
            header[key] = " ".join(val)
        else:
            if i < len(tokens):
                header[key] = tokens[i]
                i += 1
    n = int(header["DIMENSION"])
    if sorted(coords) != list(range(1, n + 1)):
        raise ValueError(f"{path}: coord ids are not 1..{n}")
    if sorted(demand) != list(range(1, n + 1)):
        raise ValueError(f"{path}: demand ids are not 1..{n}")
    if depot is None:
        raise ValueError(f"{path}: no depot")
    if header.get("EDGE_WEIGHT_TYPE") != "EUC_2D":
        raise ValueError(f"{path}: not EUC_2D")
    return {"header": header, "n": n, "coords": coords, "demand": demand,
            "depot": depot}

def transform_instance(name, inst):
    """Return (new_inst, perm) where perm[old] = new (1-based)."""
    rng = random.Random(derive_seed(name))
    vals = list(range(1, inst["n"] + 1))
    rng.shuffle(vals)
    perm = [None] + vals
    inv = [None] * (inst["n"] + 1)
    for old in range(1, inst["n"] + 1):
        inv[perm[old]] = old
    new_coords = {new: inst["coords"][inv[new]] for new in range(1, inst["n"] + 1)}
    new_demand = {new: inst["demand"][inv[new]] for new in range(1, inst["n"] + 1)}
    new = {"header": dict(inst["header"]), "n": inst["n"],
           "coords": new_coords, "demand": new_demand,
           "depot": perm[inst["depot"]]}
    return new, perm

def serialize(inst, comment=None):
    h = inst["header"]
    out = []
    out.append(f"NAME : {h['NAME']}\n")
    out.append(f"COMMENT : {comment if comment is not None else h.get('COMMENT', NEUTRAL_COMMENT)}\n")
    out.append(f"TYPE : {h.get('TYPE', 'CVRP')}\n")
    out.append(f"DIMENSION : {inst['n']}\n")
    out.append("EDGE_WEIGHT_TYPE : EUC_2D\n")
    out.append(f"CAPACITY : {h['CAPACITY']}\n")
    out.append("NODE_COORD_SECTION\n")
    for v in range(1, inst["n"] + 1):
        x, y = inst["coords"][v]
        out.append(f"{v} {x} {y}\n")
    out.append("DEMAND_SECTION\n")
    for v in range(1, inst["n"] + 1):
        out.append(f"{v} {inst['demand'][v]}\n")
    out.append("DEPOT_SECTION\n")
    out.append(f"{inst['depot']}\n-1\nEOF\n")
    return "".join(out).encode()

def params_hash(perm, depot_old, depot_new):
    """置换参数哈希：codename-map 里登记的是它，完整置换表只活在
    transform_manifest.json（仓外保密）。"""
    blob = json.dumps({"permutation_new_from_old": perm[1:],
                       "depot_old": depot_old, "depot_new": depot_new},
                      separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()
