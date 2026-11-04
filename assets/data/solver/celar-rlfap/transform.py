"""Original CALMA input conversion and frozen variable/constraint relabeling."""

import sys, os

def read_var(path):
    """Returns {var_index: category}. CALMA variable indices are arbitrary
    labels (not 1..n contiguous); see convert() for the renumbering."""
    dom = {}
    with open(path) as f:
        for line in f:
            t = line.split()
            if len(t) >= 2:
                dom[int(t[0])] = int(t[1])
    return dom

def read_dom(path):
    cats = {}
    with open(path) as f:
        for line in f:
            t = line.split()
            if len(t) >= 3:
                c = int(t[0]); cnt = int(t[1])
                vals = [int(x) for x in t[2:2 + cnt]]
                assert len(vals) == cnt, f"DOM cat {c}: {len(vals)} != {cnt}"
                cats[c] = vals
    return [cats[i] for i in range(len(cats))]

def read_ctr(path):
    hard, soft = [], []
    with open(path) as f:
        for line in f:
            t = line.split()
            if len(t) < 6:
                continue
            x, y, ty, op, k = int(t[0]), int(t[1]), t[2], t[3], int(t[4])
            w = int(t[5])
            if ty == "D":
                assert op == "=", f"D with op {op}"
                hard.append((x, y, k))
            else:
                assert op == ">", f"soft with op {op}"
                soft.append((x, y, k, w))
    return hard, soft

DEFAULT_COSTS = [1000, 100, 10, 1]

def read_cst(path):
    costs = {}
    with open(path, errors="replace") as f:
        for line in f:
            t = line.split()
            if len(t) == 3 and t[0].startswith("a") and t[1] == "=":
                costs[int(t[0][1:])] = int(t[2])
    if not costs:
        return list(DEFAULT_COSTS)
    assert sorted(costs) == [1, 2, 3, 4], f"cost table incomplete: {costs}"
    return [costs[1], costs[2], costs[3], costs[4]]

def convert(srcdir, outpath):
    for fn in ("VAR.TXT", "var.txt"):
        p = os.path.join(srcdir, fn)
        if os.path.exists(p):
            vardom = read_var(p)
            break
    else:
        raise FileNotFoundError(f"no var file in {srcdir}")
    for fn in ("DOM.TXT", "dom.txt"):
        p = os.path.join(srcdir, fn)
        if os.path.exists(p):
            cats = read_dom(p)
            break
    else:
        raise FileNotFoundError(f"no dom file in {srcdir}")
    for fn in ("CTR.TXT", "ctr.txt"):
        p = os.path.join(srcdir, fn)
        if os.path.exists(p):
            hard, soft = read_ctr(p)
            break
    else:
        raise FileNotFoundError(f"no ctr file in {srcdir}")
    costs = read_cst(os.path.join(srcdir, "cst.txt"))
    # Renumber variables to 1..n by ascending original index (matches how
    # minizinc-benchmarks packaged the CALMA instances; verified against
    # scen06/scen07 dzn by verify_conversion.py).
    order = sorted(vardom)
    remap = {old: i + 1 for i, old in enumerate(order)}
    domains = [vardom[o] for o in order]
    hard = [(remap[x], remap[y], k) for x, y, k in hard]
    soft = [(remap[x], remap[y], k, ty) for x, y, k, ty in soft]
    lo = min(v for c in cats for v in c)
    hi = max(v for c in cats for v in c)
    w = [f"{{{','.join(map(str, c))}}}" for c in cats]
    lines = [
        f"costs= [{','.join(map(str, costs))}];",
        f"num_categories= {len(cats)};",
        f"categories= [{','.join(w)}];",
        f"min_freq= {lo};",
        f"max_freq= {hi};",
        f"num_variables= {len(domains)};",
        f"domains= [{','.join(str(d + 1) for d in domains)}];",
        f"num_hardconstraints= {len(hard)};",
        f"hardctrx= [{','.join(str(h[0]) for h in hard)}];",
        f"hardctry= [{','.join(str(h[1]) for h in hard)}];",
        f"hardctrk= [{','.join(str(h[2]) for h in hard)}];",
        f"num_softconstraints= {len(soft)};",
        f"softctrx= [{','.join(str(s[0]) for s in soft)}];",
        f"softctry= [{','.join(str(s[1]) for s in soft)}];",
        f"softctrk= [{','.join(str(s[2]) for s in soft)}];",
        f"softctrw= [{','.join(str(s[3]) for s in soft)}];",
    ]
    with open(outpath, "w") as f:
        f.write("\n".join(lines) + "\n")

import argparse

import hashlib

import json

import os

import random

import re

import sys

TRANSFORM_ID = "celar-var-relabel-form2-v1"

SEED_PREFIX = "tcshard-form2-celar-260920:"

FIELDS = ["costs", "num_categories", "categories", "min_freq", "max_freq",
          "num_variables", "domains", "num_hardconstraints",
          "hardctrx", "hardctry", "hardctrk", "num_softconstraints",
          "softctrx", "softctry", "softctrk", "softctrw"]

def derive_seed(stem):
    h = hashlib.sha256((SEED_PREFIX + stem).encode()).digest()
    return int.from_bytes(h[:8], "big")

def load_dzn(path):
    """Parse a celar .dzn into a dict of fields (ints / int lists /
    list-of-int-sets). Field order fixed; one physical line per field."""
    with open(path, errors="replace") as f:
        text = f.read()
    found = re.findall(r"^([a-z_0-9]+)\s*=", text, re.M)
    if found != FIELDS:
        raise ValueError(f"unexpected field layout in {path}: {found}")

    def arr(name):
        m = re.search(name + r"\s*=\s*\[(.*?)\]\s*;", text, re.S)
        if not m:
            raise ValueError(f"could not parse {name} in {path}")
        return [int(x) for x in re.findall(r"-?\d+", m.group(1))]

    def scal(name):
        m = re.search(name + r"\s*=\s*(-?\d+)\s*;", text)
        if not m:
            raise ValueError(f"could not parse {name} in {path}")
        return int(m.group(1))

    cats_m = re.search(r"categories\s*=\s*\[(.*?)\]\s*;", text, re.S)
    categories = [[int(x) for x in re.findall(r"-?\d+", s)]
                  for s in re.findall(r"\{(.*?)\}", cats_m.group(1), re.S)]
    d = {
        "costs": arr("costs"),
        "num_categories": scal("num_categories"),
        "categories": categories,
        "min_freq": scal("min_freq"),
        "max_freq": scal("max_freq"),
        "num_variables": scal("num_variables"),
        "domains": arr("domains"),
        "num_hardconstraints": scal("num_hardconstraints"),
        "hardctrx": arr("hardctrx"),
        "hardctry": arr("hardctry"),
        "hardctrk": arr("hardctrk"),
        "num_softconstraints": scal("num_softconstraints"),
        "softctrx": arr("softctrx"),
        "softctry": arr("softctry"),
        "softctrk": arr("softctrk"),
        "softctrw": arr("softctrw"),
    }
    n = d["num_variables"]
    if len(d["domains"]) != n:
        raise ValueError(f"{path}: domains has {len(d['domains'])} != {n}")
    nh = d["num_hardconstraints"]
    ns = d["num_softconstraints"]
    for key in ("hardctrx", "hardctry", "hardctrk"):
        if len(d[key]) != nh:
            raise ValueError(f"{path}: {key} length != {nh}")
    for key in ("softctrx", "softctry", "softctrk", "softctrw"):
        if len(d[key]) != ns:
            raise ValueError(f"{path}: {key} length != {ns}")
    for v in d["hardctrx"] + d["hardctry"] + d["softctrx"] + d["softctry"]:
        if v < 1 or v > n:
            raise ValueError(f"{path}: variable index {v} out of 1..{n}")
    return d

def serialize(d):
    """One physical line per field, original field order and style."""
    def flat(vals):
        return "[" + ",".join(str(v) for v in vals) + "]"
    lines = [
        "costs= " + flat(d["costs"]) + ";",
        f"num_categories= {d['num_categories']};",
        "categories= [" + ",".join(
            "{" + ",".join(str(v) for v in s) + "}"
            for s in d["categories"]) + "];",
        f"min_freq= {d['min_freq']};",
        f"max_freq= {d['max_freq']};",
        f"num_variables= {d['num_variables']};",
        "domains= " + flat(d["domains"]) + ";",
        f"num_hardconstraints= {d['num_hardconstraints']};",
        "hardctrx= " + flat(d["hardctrx"]) + ";",
        "hardctry= " + flat(d["hardctry"]) + ";",
        "hardctrk= " + flat(d["hardctrk"]) + ";",
        f"num_softconstraints= {d['num_softconstraints']};",
        "softctrx= " + flat(d["softctrx"]) + ";",
        "softctry= " + flat(d["softctry"]) + ";",
        "softctrk= " + flat(d["softctrk"]) + ";",
        "softctrw= " + flat(d["softctrw"]) + ";",
    ]
    return ("\n".join(lines) + "\n").encode()

def transform_instance(stem, d):
    """Return (new_d, var_perm, hard_order, soft_order).
    var_perm[old] = new (1-based); hard_order[new_pos] = old_idx (0-based);
    soft_order likewise."""
    n = d["num_variables"]
    rng = random.Random(derive_seed(stem))
    perm = list(range(1, n + 1))
    rng.shuffle(perm)
    var_perm = [None] + perm
    nh = d["num_hardconstraints"]
    ns = d["num_softconstraints"]
    hard_order = list(range(nh))
    rng.shuffle(hard_order)
    soft_order = list(range(ns))
    rng.shuffle(soft_order)

    new = dict(d)
    new_domains = [None] * n
    for old in range(1, n + 1):
        new_domains[var_perm[old] - 1] = d["domains"][old - 1]
    new["domains"] = new_domains
    for a, b in (("hardctrx", "hardctry"), ("softctrx", "softctry")):
        new[a] = [var_perm[v] for v in d[a]]
        new[b] = [var_perm[v] for v in d[b]]
    for keys, order in ((("hardctrx", "hardctry", "hardctrk"), hard_order),
                        (("softctrx", "softctry", "softctrk", "softctrw"),
                         soft_order)):
        for key in keys:
            vals = new[key]
            new[key] = [vals[old_idx] for old_idx in order]
    return new, var_perm, hard_order, soft_order
