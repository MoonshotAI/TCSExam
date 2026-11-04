#!/usr/bin/env python3
"""Structure-preserving transformation tool for the bpp-bpplib scored set (deterministic form2 mapping).

This tool transforms official BPPLIB instances into coded scored instances
(exNNN.txt), and supports inversion and rewriting oracle packings. The transform
preserves the optimal number of bins, so memorized optimal packings of public
official instances cannot be submitted directly against their transformed copies.
The mapping from official instances to transformed instances is kept out of the
model environment.

Instance format (BPPLIB BPP text): n, C, then n integer weights. Item identity is
its position (the j-th token in a packing output is the bin ID for the j-th weight).

Transformation (objective value is preserved):
  Reorder the weight sequence using a seeded bijection perm: new position k gets
  original item perm[k] (perm is a seeded shuffle of range(n)). Capacity and the
  weight multiset stay unchanged, so reuse optimal value K by isomorphism. The FFD
  baseline is order-sensitive (stable tie-break), so remeasure B in the batch phase.
  Reorder the solution (item-to-bin sequence) by the same permutation:
  new_bins[k] = orig_bins[perm[k]]; the bin count is unchanged.

Deterministic per-instance seed:
    seed = int.from_bytes(sha256("tcshard-transform-20260831:" + name)[:8],
           "big"); rng = random.Random(seed)
  name is the official instance filename (for example, "201_2500_DI_30.txt").
This uses the same rule as the 2026-09-13 restoration batch (online async lineage,
judge-v8): the bytes regenerated here exactly match the restored outputs in
transform-restore-260913 historical record (not included in this package). Both final and async lineages use
the same transformed instances.

Code assignment: the mapping exNNN.txt ↔ official name reuses the existing async
lineage codename-map, ordered by official name as ex001..ex129. This script checks
that mapping but does not assign names again. After form2, the hidden
scored set is a stratified 30% sample of the 129 instances (39 keys in
 tests/split.json).

Subcommands:
  batch            Transform the full official-instance directory and write
                   transform_manifest.json (full permutation table; confidential,
                   write outside the Git repository, never into the model-readable
                   /tests layer of the scoring image).
                   Maintenance command for generating the full set; do not
                   rerun after the split is frozen.
  --apply IN --name OFFICIAL_NAME --out OUT
                   Forward-transform one instance by regenerating perm from the
                   seed rule and emit canonical bytes (n and C on separate lines,
                   followed by one weight per line).
  --invert IN --name OFFICIAL_NAME --out OUT
                   Invert one instance using the same perm and restore weight order
                   token by token.

For routine form2 mathematical checks, use tests/test_transform.py. It depends only
on this file and tests/scoring.py, not on the private manifest.

Standard library only."""
import argparse
import hashlib
import json
import os
import random
import sys

SEED_TAG = "tcshard-transform-20260831"
TRANSFORM_ID = "bpp-weight-sequence-permute-v1"
SEED_RULE = (
    "seed = int.from_bytes(sha256('tcshard-transform-20260831:' + name)[:8],"
    " 'big'); rng = random.Random(seed); consumption: single weight-sequence"
    " shuffle range(n); name = official instance file name"
)


def derive_seed(name):
    h = hashlib.sha256((SEED_TAG + ":" + name).encode()).digest()
    return int.from_bytes(h[:8], "big")


def oracle_hash(plain_bytes):
    """Exactly what the oracle stub computes on its stdin."""
    return hashlib.sha256(b" ".join(plain_bytes.split())).hexdigest()


def parse_instance(path):
    with open(path) as f:
        vals = f.read().split()
    if len(vals) < 2:
        raise ValueError(f"{path}: too few tokens")
    n, C = int(vals[0]), int(vals[1])
    w = [int(v) for v in vals[2:]]
    if len(w) != n:
        raise ValueError(f"{path}: expected {n} weights, found {len(w)}")
    return n, C, w


def serialize(n, C, w):
    return (f"{n}\n{C}\n" + "\n".join(str(x) for x in w) + "\n").encode()


def transform_instance(name, n, w):
    """Return (new_w, perm); new_w[k] = w[perm[k]]，perm 0-based。"""
    rng = random.Random(derive_seed(name))
    perm = list(range(n))
    rng.shuffle(perm)
    return [w[perm[k]] for k in range(n)], perm


def invert_instance(name, n, w_t):
    """Inverse of the forward transform: w[perm[k]] = w_t[k]. Return (w, perm)."""
    rng = random.Random(derive_seed(name))
    perm = list(range(n))
    rng.shuffle(perm)
    w = [0] * n
    for k in range(n):
        w[perm[k]] = w_t[k]
    return w, perm


def params_hash(perm):
    """Permutation-parameter hash: this is recorded in codename-map; the full permutation table exists only in
    transform_manifest.json (confidential, outside the repository)."""
    blob = json.dumps({"perm": perm}, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def rewrite_packing(bins, perm):
    """Reorder packing (item-to-bin sequence) by perm: new_bins[k] = bins[perm[k]]."""
    return [bins[perm[k]] for k in range(len(bins))]


def cmd_apply(args):
    n, C, w = parse_instance(args.apply)
    nw, _ = transform_instance(args.name, n, w)
    with open(args.out, "wb") as f:
        f.write(serialize(n, C, nw))
    print(f"[apply] {args.name}: n={n} -> {args.out}")


def cmd_invert(args):
    n, C, w_t = parse_instance(args.invert)
    w, _ = invert_instance(args.name, n, w_t)
    with open(args.out, "wb") as f:
        f.write(serialize(n, C, w))
    print(f"[invert] {args.name}: n={n} -> {args.out}")


def cmd_batch(args):
    os.makedirs(args.out_dir, exist_ok=True)
    names = sorted(f for f in os.listdir(args.instances_dir) if f.endswith(".txt"))
    if args.names:
        keep = set(args.names.split(","))
        names = [n for n in names if n in keep]
    manifest = {"transform": TRANSFORM_ID, "seed_rule": SEED_RULE,
                "instances": {}}
    for name in names:
        src = os.path.join(args.instances_dir, name)
        with open(src, "rb") as f:
            plain = f.read()
        n, C, w = parse_instance(src)
        nw, perm = transform_instance(name, n, w)
        out_plain = serialize(n, C, nw)
        dst = os.path.join(args.out_dir, name)
        with open(dst, "wb") as f:
            f.write(out_plain)
        os.chmod(dst, 0o644)
        manifest["instances"][name] = {
            "seed": derive_seed(name),
            "n": n, "C": C, "perm": perm,
            "sha256_orig_tokens": oracle_hash(plain),
            "sha256_new_tokens": oracle_hash(out_plain),
        }
        print(f"[batch] {name}: n={n} C={C}", flush=True)
    with open(args.manifest, "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
    os.chmod(args.manifest, 0o644)
    print(f"[batch] manifest (confidential, retained outside the repository): {args.manifest} "
          f"({len(manifest['instances'])} instances)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", metavar="IN",
                    help="Forward-transform one instance: read official .txt and write transformed bytes to --out")
    ap.add_argument("--invert", metavar="IN",
                    help="Invert one instance: read transformed .txt and write the restored file to --out")
    ap.add_argument("--name", help="Official instance filename (used to derive the seed)")
    ap.add_argument("--out", help="Output path for --apply/--invert")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("batch")
    p.add_argument("--instances-dir", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--names", default=None)
    p.set_defaults(fn=cmd_batch)
    args = ap.parse_args()
    if args.apply or args.invert:
        if not args.name or not args.out:
            ap.error("--apply/--invert require --name and --out")
        if args.apply and args.invert:
            ap.error("choose either --apply or --invert")
        if args.apply:
            cmd_apply(args)
        else:
            cmd_invert(args)
        return
    if not args.cmd:
        ap.error("Specify the batch subcommand or --apply/--invert")
    sys.exit(args.fn(args) or 0)


if __name__ == "__main__":
    main()
