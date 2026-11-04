#!/usr/bin/env python3
"""Structure-preserving form2 transformation for celar-rlfap (tests-side utility for the 30% hidden scored instances).

For each instance marked hidden in split.json, apply an exact isomorphism by
permuting variables (sites), pi: old 1..n → new 1..n. Reorder the domains array
and relabel variable indices in hard and soft constraints. Also shuffle the hard
constraint rows and soft constraint rows. **Do not change the frequency domains**:
RLFAP includes value-metric constraints such as |f_i - f_j| = k and
|f_i - f_j| <= k, so a domain-value permutation is not an isomorphism. Preserve
costs/categories/min_freq/max_freq/k/w exactly. Every solution objective therefore
stays exactly the same, so reuse K by isomorphism.

Write transformed instances to new names h01.dzn, etc., numbered by sorted
official name. Store the original-to-transformed name mapping only in
tests/transform_manifest.json (under tests/, outside the environment and the
model-readable /tests layer of the scoring image).

Deterministic per-instance seed:
    seed = int.from_bytes(sha256("tcshard-form2-celar-260920:" + stem)
           .digest()[:8], "big")
    rng = random.Random(seed)
stem is the official filename without extension (for example, "scen06"). Consume
the RNG by shuffling, in order: variable permutation, hard-constraint row order,
soft-constraint row order. The same seed reproduces identical transformed bytes.

Subcommands:
  apply              Batch-transform hidden instances from split.json: read the
                     official source bytes in tests/instances-library/ and write
                     tests/instances/hNN.dzn plus tests/transform_manifest.json.
  invert             Independently invert each transformed instance using the
                     manifest permutation and compare tokens with the official
                     source (round-trip consistency).
  rewrite-solutions  Rewrite stored solutions (*.sol f = [...] blocks) using the
                     manifest variable permutation for the oracle stub, then
                     rebuild the lookup manifest for transformed instances.

Standard library only."""
import argparse
import hashlib
import json
import os
import random
import re
import sys

TRANSFORM_ID = "celar-var-relabel-form2-v1"
SEED_PREFIX = "tcshard-form2-celar-260920:"
SEED_RULE = (
    'seed = int.from_bytes(sha256("tcshard-form2-celar-260920:" + stem)'
    '.digest()[:8], "big"); rng = random.Random(seed); consumption order:'
    " variable-permutation shuffle, hard-constraint row shuffle,"
    " soft-constraint row shuffle; transformed file name hNN assigned in"
    " sorted official-name order"
)

FIELDS = ["costs", "num_categories", "categories", "min_freq", "max_freq",
          "num_variables", "domains", "num_hardconstraints",
          "hardctrx", "hardctry", "hardctrk", "num_softconstraints",
          "softctrx", "softctry", "softctrk", "softctrw"]

TESTS = os.path.dirname(os.path.abspath(__file__))


def derive_seed(stem):
    h = hashlib.sha256((SEED_PREFIX + stem).encode()).digest()
    return int.from_bytes(h[:8], "big")


def oracle_hash(plain_bytes):
    """Lookup key for the oracle stub: SHA-256 of the whitespace-normalized token stream."""
    return hashlib.sha256(b" ".join(plain_bytes.split())).hexdigest()


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


def invert_instance(d_t, var_perm, hard_order, soft_order):
    """Inverse transform: use the manifest permutation to restore the transformed instance to the official semantic bytes."""
    n = d_t["num_variables"]
    inv = [None] * (n + 1)
    for old in range(1, n + 1):
        inv[var_perm[old]] = old
    r = dict(d_t)
    r_domains = [None] * n
    for newidx in range(1, n + 1):
        r_domains[inv[newidx] - 1] = d_t["domains"][newidx - 1]
    r["domains"] = r_domains
    for a, b in (("hardctrx", "hardctry"), ("softctrx", "softctry")):
        r[a] = [inv[v] for v in d_t[a]]
        r[b] = [inv[v] for v in d_t[b]]
    for keys, order in ((("hardctrx", "hardctry", "hardctrk"), hard_order),
                        (("softctrx", "softctry", "softctrk", "softctrw"),
                         soft_order)):
        for key in keys:
            vals = r[key]
            restored = [None] * len(vals)
            for new_pos, old_idx in enumerate(order):
                restored[old_idx] = vals[new_pos]
            r[key] = restored
    return r


def load_split():
    with open(os.path.join(TESTS, "split.json")) as f:
        return json.load(f)


def hidden_stems_sorted():
    split = load_split()
    return sorted(fn[:-len(".dzn")] for fn, side in split.items()
                  if side == "hidden")


def cmd_apply(args):
    os.makedirs(args.out_dir, exist_ok=True)
    stems = hidden_stems_sorted()
    manifest = {
        "transform": TRANSFORM_ID,
        "operations": ["permute-variables", "shuffle-hard-constraints",
                       "shuffle-soft-constraints"],
        "frequency_domain": "untouched (value-metric constraints make any "
                            "domain relabeling non-isomorphic)",
        "seed_rule": SEED_RULE,
        "instances": {},
    }
    for i, stem in enumerate(stems, 1):
        new_name = f"h{i:02d}"
        src = os.path.join(args.instances_dir, stem + ".dzn")
        with open(src, "rb") as f:
            plain = f.read()
        d = load_dzn(src)
        new, var_perm, hard_order, soft_order = transform_instance(stem, d)
        out_plain = serialize(new)
        dst = os.path.join(args.out_dir, new_name + ".dzn")
        with open(dst, "wb") as f:
            f.write(out_plain)
        os.chmod(dst, 0o644)
        manifest["instances"][new_name] = {
            "official": stem,
            "seed": derive_seed(stem),
            "num_variables": new["num_variables"],
            "var_permutation_new_from_old": var_perm[1:],
            "hard_order_new_from_old": hard_order,
            "soft_order_new_from_old": soft_order,
            "src_sha256_plain": hashlib.sha256(plain).hexdigest(),
            "out_sha256_plain": hashlib.sha256(out_plain).hexdigest(),
            "oracle_key": oracle_hash(out_plain),
        }
        print(f"[apply] {stem} -> {new_name}.dzn "
              f"({new['num_variables']} vars)", flush=True)
    with open(args.manifest, "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
        f.write("\n")
    os.chmod(args.manifest, 0o644)
    print(f"[apply] manifest: {args.manifest} "
          f"({len(manifest['instances'])} instances)")


def cmd_invert(args):
    with open(args.manifest) as f:
        manifest = json.load(f)
    n_ok = n_bad = 0
    for new_name, rec in sorted(manifest["instances"].items()):
        stem = rec["official"]
        problems = []
        try:
            d_o = load_dzn(os.path.join(args.orig_dir, stem + ".dzn"))
            d_t = load_dzn(os.path.join(args.trans_dir, new_name + ".dzn"))
        except ValueError as e:
            print(f"[invert] {new_name} ({stem}): FAIL parse: {e}")
            n_bad += 1
            continue
        n = rec["num_variables"]
        var_perm = [None] + rec["var_permutation_new_from_old"]
        hard_order = rec["hard_order_new_from_old"]
        soft_order = rec["soft_order_new_from_old"]
        if d_o["num_variables"] != n or d_t["num_variables"] != n:
            problems.append("num_variables mismatch")
        if sorted(var_perm[1:]) != list(range(1, n + 1)):
            problems.append("variable permutation is not a bijection")
        if sorted(hard_order) != list(range(d_o["num_hardconstraints"])):
            problems.append("hard order is not a permutation")
        if sorted(soft_order) != list(range(d_o["num_softconstraints"])):
            problems.append("soft order is not a permutation")
        if not problems:
            r = invert_instance(d_t, var_perm, hard_order, soft_order)
            with open(os.path.join(args.orig_dir, stem + ".dzn"), "rb") as f:
                orig = f.read()
            if serialize(r).split() != orig.split():
                problems.append("restored token stream != original")
        if problems:
            n_bad += 1
            print(f"[invert] {new_name} ({stem}): FAIL {'; '.join(problems)}")
        else:
            n_ok += 1
            print(f"[invert] {new_name} ({stem}): ok")
    print(f"[invert] ok={n_ok} bad={n_bad}")
    return 1 if n_bad else 0


def cmd_rewrite_solutions(args):
    """Rewrite prerecorded f-vectors with the manifest's variable
    permutation; rebuild the oracle lookup manifest against the transformed
    instances."""
    with open(args.manifest) as f:
        manifest = json.load(f)["instances"]
    os.makedirs(args.out_dir, exist_ok=True)
    out_manifest = {}
    n_sol = 0
    for new_name, rec in sorted(manifest.items()):
        stem = rec["official"]
        src_sol = os.path.join(args.sol_dir, stem + ".sol")
        if not os.path.exists(src_sol):
            print(f"[rewrite-solutions] {stem}: no prerecorded solution, "
                  f"skipped")
            continue
        with open(src_sol) as f:
            text = f.read()
        blocks = list(re.finditer(r"f\s*=\s*\[(.*?)\]\s*;", text, re.S))
        if not blocks:
            sys.exit(f"[rewrite-solutions] {stem}: no f block found")
        n = rec["num_variables"]
        var_perm = [None] + rec["var_permutation_new_from_old"]
        # a solver transcript may carry several f blocks (improving
        # solutions); the judge scores the last complete one — rewrite
        # every block with the same permutation
        out_text, last_end = [], 0
        for b in blocks:
            out_text.append(text[last_end:b.start()])
            fv = [int(x) for x in re.findall(r"-?\d+", b.group(1))]
            if len(fv) != n:
                sys.exit(f"[rewrite-solutions] {stem}: f has {len(fv)} != {n}")
            new_fv = [None] * n
            for old in range(1, n + 1):
                new_fv[var_perm[old] - 1] = fv[old - 1]
            out_text.append("f = [" + ",".join(str(v) for v in new_fv)
                            + "];")
            last_end = b.end()
        out_text.append(text[last_end:])
        with open(os.path.join(args.out_dir, new_name + ".sol"), "w") as f:
            f.write("".join(out_text))
        with open(os.path.join(args.instances_dir, new_name + ".dzn"),
                  "rb") as f:
            key = oracle_hash(f.read())
        if key != rec["oracle_key"]:
            sys.exit(f"[rewrite-solutions] {new_name}: instance key mismatch "
                     f"with manifest ({key} != {rec['oracle_key']})")
        out_manifest[key] = {"sol": new_name + ".sol", "instance": new_name}
        n_sol += 1
    with open(os.path.join(args.out_dir, "manifest-hidden.json"), "w") as f:
        json.dump(out_manifest, f, indent=0, sort_keys=True)
        f.write("\n")
    print(f"[rewrite-solutions] {n_sol} solutions rewritten -> {args.out_dir}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("apply")
    p.add_argument("--instances-dir", default=os.path.join(
        TESTS, "instances-library"))
    p.add_argument("--out-dir", default=os.path.join(TESTS, "instances"))
    p.add_argument("--manifest", default=os.path.join(
        TESTS, "transform_manifest.json"))
    p.set_defaults(fn=cmd_apply)
    p = sub.add_parser("invert")
    p.add_argument("--orig-dir", default=os.path.join(TESTS,
                                                      "instances-library"))
    p.add_argument("--trans-dir", default=os.path.join(TESTS, "instances"))
    p.add_argument("--manifest", default=os.path.join(
        TESTS, "transform_manifest.json"))
    p.set_defaults(fn=cmd_invert)
    p = sub.add_parser("rewrite-solutions")
    p.add_argument("--instances-dir", default=os.path.join(TESTS, "instances"),
                   help="directory with the TRANSFORMED instances")
    p.add_argument("--sol-dir", required=True,
                   help="directory with the original prerecorded solutions")
    p.add_argument("--manifest", default=os.path.join(
        TESTS, "transform_manifest.json"))
    p.add_argument("--out-dir", required=True)
    p.set_defaults(fn=cmd_rewrite_solutions)
    args = ap.parse_args()
    sys.exit(args.fn(args) or 0)


if __name__ == "__main__":
    main()
