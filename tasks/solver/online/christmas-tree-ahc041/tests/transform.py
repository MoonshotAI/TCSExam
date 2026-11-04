#!/usr/bin/env python3
"""Structure-preserving form2 transformation for christmas-tree-ahc041 (tests-side utility for the 30% hidden scored instances).

For each instance marked hidden in split.json, apply an exact isomorphism by
permuting vertex IDs pi: old 0..N-1 → new 0..N-1. Reorder A rows by pi, rewrite
each edge (u,v) as (pi(u),pi(v)), and reorder the N coordinate rows by pi
(**coordinate values stay unchanged**). Keep the N/M/H header and edge-row order
unchanged. The official scorer (scoring.check_ahc041, a behavior port of the
official AHC041 scorer: parent edges must belong to G, undirected cycles are
forbidden, depth must be ≤H, score = 1 + sum_v (depth(v)+1)·A[v]) is invariant
under vertex relabeling. Every valid parent-pointer array has exactly the same
score, so reuse K by isomorphism.

Write transformed instances to new names t01.txt, etc., numbered by sorted source
name. Store the original-to-transformed mapping and permutation table only in
tests/transform_manifest.json (under tests/, outside the environment and the
model-readable /tests layer of the scoring image).

Deterministic per-instance seed:
    seed = int.from_bytes(sha256("tcshard-form2-christmas-260920:" + stem)
           .digest()[:8], "big")
    rng = random.Random(seed)
stem is the source filename without extension (for example, "h06"). The same seed
reproduces identical transformed bytes.

Subcommands:
  apply              Batch-transform hidden instances from split.json: read the
                     generated originals in tests/instances-library/ and write
                     tests/instances/tNN.txt plus tests/transform_manifest.json.
  invert             Independently invert transformed instances using the manifest
                     and compare parsed content with the source (semantic equality).
  rewrite-solutions  Rewrite stored parent-pointer arrays (*.out: N tokens per
                     block, with the last block used; parent'[pi(v)] = pi(parent[v]),
                     roots remain -1) using the manifest vertex permutation for the
                     oracle stub, then rebuild the lookup manifest for transformed
                     instances.

Standard library only."""
import argparse
import hashlib
import json
import os
import random
import sys

TRANSFORM_ID = "christmas-vertex-relabel-form2-v1"
SEED_PREFIX = "tcshard-form2-christmas-260920:"
SEED_RULE = (
    'seed = int.from_bytes(sha256("tcshard-form2-christmas-260920:" + stem)'
    '.digest()[:8], "big"); rng = random.Random(seed); one shuffle of the'
    " vertex-id list 0..N-1; transformed file name tNN assigned in sorted"
    " source-name order"
)

TESTS = os.path.dirname(os.path.abspath(__file__))


def derive_seed(stem):
    h = hashlib.sha256((SEED_PREFIX + stem).encode()).digest()
    return int.from_bytes(h[:8], "big")


def oracle_hash(plain_bytes):
    """Lookup key for the oracle stub: SHA-256 of the whitespace-normalized token stream."""
    return hashlib.sha256(b" ".join(plain_bytes.split())).hexdigest()


def load_instance(path):
    """AHC041 format: N M H, then N weights A, then M edges (u v),
    then N points (x y)."""
    with open(path) as f:
        vals = f.read().split()
    pos = 0

    def nxt(what):
        nonlocal pos
        if pos >= len(vals):
            raise ValueError(f"unexpected end of instance file at {what}")
        v = int(vals[pos])
        pos += 1
        return v

    N, M, H = nxt("N"), nxt("M"), nxt("H")
    A = [nxt("A") for _ in range(N)]
    edges = [(nxt("u"), nxt("v")) for _ in range(M)]
    points = [(nxt("x"), nxt("y")) for _ in range(N)]
    if pos != len(vals):
        raise ValueError(f"{path}: trailing tokens ({len(vals) - pos} extra)")
    return {"N": N, "M": M, "H": H, "A": A, "edges": edges,
            "points": points}


def emit(inst):
    lines = [f"{inst['N']} {inst['M']} {inst['H']}",
             " ".join(str(v) for v in inst["A"])]
    lines += [f"{u} {v}" for u, v in inst["edges"]]
    lines += [f"{x} {y}" for x, y in inst["points"]]
    return ("\n".join(lines) + "\n").encode()


def transform_instance(inst, perm):
    """Return new_inst with vertex ids permuted by perm (new[pi[old]] =
    old ID; coordinate values do not change)."""
    N = inst["N"]
    new_A = [None] * N
    new_points = [None] * N
    for old in range(N):
        new_A[perm[old]] = inst["A"][old]
        new_points[perm[old]] = inst["points"][old]
    new_edges = [(perm[u], perm[v]) for u, v in inst["edges"]]
    return {"N": inst["N"], "M": inst["M"], "H": inst["H"], "A": new_A,
            "edges": new_edges, "points": new_points}


def invert_instance(inst_t, perm):
    inv = [None] * len(perm)
    for old, new in enumerate(perm):
        inv[new] = old
    return transform_instance(inst_t, inv)


def hidden_stems_sorted():
    with open(os.path.join(TESTS, "split.json")) as f:
        split = json.load(f)
    return sorted(fn[:-len(".txt")] for fn, side in split.items()
                  if side == "hidden")


def cmd_apply(args):
    os.makedirs(args.out_dir, exist_ok=True)
    stems = hidden_stems_sorted()
    manifest = {
        "transform": TRANSFORM_ID,
        "operations": ["permute-vertex-ids"],
        "coordinates": "values untouched (rows follow the vertex-id "
                       "permutation)",
        "seed_rule": SEED_RULE,
        "instances": {},
    }
    for i, stem in enumerate(stems, 1):
        new_name = f"t{i:02d}"
        src = os.path.join(args.instances_dir, stem + ".txt")
        with open(src, "rb") as f:
            plain = f.read()
        inst = load_instance(src)
        n = inst["N"]
        rng = random.Random(derive_seed(stem))
        perm = list(range(n))
        rng.shuffle(perm)
        new = transform_instance(inst, perm)
        out_plain = emit(new)
        dst = os.path.join(args.out_dir, new_name + ".txt")
        with open(dst, "wb") as f:
            f.write(out_plain)
        os.chmod(dst, 0o644)
        manifest["instances"][new_name] = {
            "official": stem,
            "seed": derive_seed(stem),
            "n_vertices": n,
            "perm": perm,
            "src_sha256_plain": hashlib.sha256(plain).hexdigest(),
            "out_sha256_plain": hashlib.sha256(out_plain).hexdigest(),
            "oracle_key": oracle_hash(out_plain),
        }
        print(f"[apply] {stem} -> {new_name}.txt ({n} vertices)", flush=True)
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
        inst_t = load_instance(os.path.join(args.trans_dir,
                                            new_name + ".txt"))
        restored = invert_instance(inst_t, rec["perm"])
        inst_o = load_instance(os.path.join(args.orig_dir, stem + ".txt"))
        if restored == inst_o:
            n_ok += 1
            print(f"[invert] {new_name} ({stem}): ok")
        else:
            n_bad += 1
            print(f"[invert] {new_name} ({stem}): FAIL restored != original")
    print(f"[invert] ok={n_ok} bad={n_bad}")
    return 1 if n_bad else 0


def cmd_rewrite_solutions(args):
    """Rewrite prerecorded parent arrays with the manifest's vertex
    permutation (parent'[pi(v)] = pi(parent[v]), root -1 untouched);
    rebuild the oracle lookup manifest against the transformed instances."""
    with open(args.manifest) as f:
        manifest = json.load(f)["instances"]
    os.makedirs(args.out_dir, exist_ok=True)
    out_manifest = {}
    n_sol = 0
    for new_name, rec in sorted(manifest.items()):
        stem = rec["official"]
        src_sol = os.path.join(args.sol_dir, stem + ".out")
        if not os.path.exists(src_sol):
            print(f"[rewrite-solutions] {stem}: no prerecorded solution, "
                  f"skipped")
            continue
        perm = rec["perm"]
        n = rec["n_vertices"]
        with open(src_sol) as f:
            toks = f.read().split()
        if len(toks) % n != 0:
            sys.exit(f"[rewrite-solutions] {stem}: {len(toks)} tokens not "
                     f"a multiple of N={n}")
        out_toks = []
        for base in range(0, len(toks), n):
            block = [int(t) for t in toks[base:base + n]]
            new_block = [None] * n
            for old in range(n):
                p = block[old]
                new_block[perm[old]] = -1 if p == -1 else perm[p]
            out_toks.extend(str(v) for v in new_block)
        dst = os.path.join(args.out_dir, new_name + ".out")
        with open(dst, "w") as f:
            f.write("\n".join(out_toks) + "\n")
        with open(os.path.join(args.instances_dir, new_name + ".txt"),
                  "rb") as f:
            key = oracle_hash(f.read())
        if key != rec["oracle_key"]:
            sys.exit(f"[rewrite-solutions] {new_name}: instance key mismatch "
                     f"with manifest ({key} != {rec['oracle_key']})")
        out_manifest[key] = {"sol": new_name + ".out", "instance": new_name}
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
