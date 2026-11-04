#!/usr/bin/env python3
"""Structure-preserving transformation for the maxcut-mqlib form2 hidden set (vertex relabeling; exact isomorphism).

Transformation mathematics (the graph entry in form2-conversion-recipes.md):
  Apply a random vertex permutation π, relabel vertices by π, and rewrite the edge
  list. The MaxCut objective depends only on the weighted adjacency structure, so
  every cut value is exactly invariant under π. Reuse K by isomorphism; remeasure B
  on transformed instances because the baseline tabu-search trajectory depends on
  vertex IDs.

Byte-level handling (fingerprint removal, following the same rule as the 2026-08-31
transformation batch):
  * Drop every `#` comment line (the original header contains instance names and
    random seeds, which can act as memorized fingerprints).
  * Relabel vertices with the per-instance seeded permutation.
  * Rewrite each edge as "a b w", with a < b, preserving the weight token exactly
    (no reformatting: 60 instances have fractional weights and 47 have negative
    weights, so objective values must match bit for bit).
  * Sort the edge list, removing traces of the original layout. The 150 scored
    instances were scanned: there are no repeated endpoint pairs and the m in each
    header matches the number of data rows; sorting does not change semantics.

Seed rule (same as the 2026-08-31 batch and the 260913 async restoration batch):
    seed = int.from_bytes(sha256("tcshard-transform-20260831:" + official_name)[:8])
    perm = Random(seed).shuffle([1..n]); perm[v-1] = new label of old vertex v.
The complete permutation table is recorded in transform_manifest.json here, under
tests/ only, together with the mapping from official names to transformed names
txNNN. Validation and oracle rewriting do not depend on replaying the RNG.

Naming: hidden scored instances use new names txNNN.txt.xz to avoid collisions with
public instances (txNNN numbers follow sorted official names).

Usage:
    transform.py --apply OFFICIAL_XZ_DIR OUT_DIR MANIFEST_JSON [official_name ...]
        Transform <official>.txt.xz from OFFICIAL_XZ_DIR into txNNN.txt.xz under
        OUT_DIR and write or merge the manifest.
    transform.py --invert TX_XZ MANIFEST_JSON OUT_TXT
        Use the manifest permutation to invert the transformed instance to its
        original labels (header plus sorted edge list; comment lines cannot be
        recovered, but the result is semantically equivalent; see the round-trip
        assertion in test_transform.py).
"""
import hashlib
import json
import lzma
import os
import random
import sys

MASTER_SEED_TAG = "tcshard-transform-20260831"
TRANSFORM_ID = "vertex-relabeling-v1"


def derive_seed(official_name):
    """Per-instance seed: hash the master seed 20260831 together with the official instance name."""
    h = hashlib.sha256(f"{MASTER_SEED_TAG}:{official_name}".encode())
    return int.from_bytes(h.digest()[:8], "big")


def load_mqlib_text(text):
    """Parse decompressed MQLib instance text and return (n, edges), where edges are
    a list of (u, v, w_token) tuples (1-based; preserve weight tokens verbatim to avoid floating-point drift)."""
    n = m = None
    edges = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if n is None:
            n, m = int(parts[0]), int(parts[1])
            continue
        if len(parts) != 3:
            raise ValueError(f"bad data line: {line!r}")
        u, v = int(parts[0]), int(parts[1])
        if u == v:
            raise ValueError(f"self-loop: {line!r}")
        edges.append((u, v, parts[2]))
    if n is None:
        raise ValueError("empty instance")
    if len(edges) != m:
        raise ValueError(f"edge count mismatch: header {m} vs {len(edges)}")
    return n, edges


def canonical_bytes(n, edges):
    """Canonical byte stream with header and sorted edge list (a<b; preserve weight tokens verbatim)."""
    norm = []
    for u, v, w in edges:
        a, b = (u, v) if u < v else (v, u)
        norm.append((a, b, w))
    norm.sort(key=lambda e: (e[0], e[1]))
    out = [f"{n} {len(norm)}\n"]
    out += [f"{a} {b} {w}\n" for a, b, w in norm]
    return "".join(out).encode("utf-8")


def transform_bytes(data, official_name):
    """Transform one decompressed instance byte stream. Return (new_bytes, perm, seed)."""
    text = data.decode("utf-8", errors="replace")
    n, edges = load_mqlib_text(text)
    seed = derive_seed(official_name)
    perm = list(range(1, n + 1))
    random.Random(seed).shuffle(perm)  # perm[v-1] = new label of old vertex v
    new_edges = [(perm[u - 1], perm[v - 1], w) for u, v, w in edges]
    return canonical_bytes(n, new_edges), perm, seed


def invert_bytes(data, perm):
    """Invert using the permutation table: take transformed bytes and output canonical bytes with original labels."""
    text = data.decode("utf-8", errors="replace")
    n, edges = load_mqlib_text(text)
    if sorted(perm) != list(range(1, n + 1)):
        raise ValueError("perm is not a bijection of 1..n")
    inv = [0] * n  # inv[new-1] = old
    for old, new in enumerate(perm, start=1):
        inv[new - 1] = old
    orig_edges = [(inv[a - 1], inv[b - 1], w) for a, b, w in edges]
    return canonical_bytes(n, orig_edges)


def permute_solution_tokens(tokens, perm):
    """Synchronized solution transform: move the cut's 0/1 labels with vertices, new_side[perm[v]-1] =
    old_side[v-1]. tokens contains one "0"/"1" value per vertex."""
    if len(tokens) != len(perm):
        raise ValueError(f"solution has {len(tokens)} tokens, perm {len(perm)}")
    out = [None] * len(tokens)
    for v in range(len(tokens)):
        out[perm[v] - 1] = tokens[v]
    return out


def cmd_apply(argv):
    if len(argv) < 4:
        print(f"usage: {argv[0]} --apply OFFICIAL_XZ_DIR OUT_DIR MANIFEST_JSON "
              "[official_name ...]", file=sys.stderr)
        return 2
    in_dir, out_dir, manifest_path = argv[2:5]
    names = argv[5:]
    if not names:
        print(f"{argv[0]}: no instance names given (hidden set is explicit)",
              file=sys.stderr)
        return 1
    os.makedirs(out_dir, exist_ok=True)
    manifest = {
        "transform": TRANSFORM_ID,
        "master_seed_tag": MASTER_SEED_TAG,
        "seed_derivation": ("int.from_bytes(sha256(tag + ':' + official_name)[:8]); "
                            "Random(seed).shuffle([1..n]); perm[v-1] = new label "
                            "of old vertex v"),
        "name_note": ("txNNN assigned in sorted(official) order; official -> txNNN "
                      "mapping lives ONLY in this tests-side manifest"),
        "hash_note": "sha256 values are over the RAW DECOMPRESSED byte stream",
        "instances": {},
    }
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            manifest = json.load(f)
        manifest.setdefault("instances", {})
    officials = sorted(names)
    for i, official in enumerate(officials, start=1):
        tx = f"tx{i:03d}.txt"
        src = os.path.join(in_dir, official + ".xz")
        with lzma.open(src, "rb") as f:
            data = f.read()
        new_data, perm, seed = transform_bytes(data, official)
        with lzma.open(os.path.join(out_dir, tx + ".xz"), "wb", preset=6) as f:
            f.write(new_data)
        n = len(perm)
        manifest["instances"][tx] = {
            "official": official,
            "seed_hex": f"{seed:016x}",
            "n": n,
            "m": len(new_data.decode().splitlines()) - 1,
            "perm": perm,
            "sha256_orig_bytes": hashlib.sha256(data).hexdigest(),
            "sha256_new_bytes": hashlib.sha256(new_data).hexdigest(),
        }
        print(f"  {official} -> {tx}: n={n} seed={seed:016x}", flush=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
    print(f"transformed {len(officials)} instance(s) -> {out_dir}")
    print(f"manifest -> {manifest_path}")
    return 0


def cmd_invert(argv):
    if len(argv) != 5:
        print(f"usage: {argv[0]} --invert TX_XZ MANIFEST_JSON OUT_TXT",
              file=sys.stderr)
        return 2
    tx_xz, manifest_path, out_txt = argv[2:5]
    with open(manifest_path) as f:
        manifest = json.load(f)
    tx = os.path.basename(tx_xz)
    if tx.endswith(".xz"):
        tx = tx[:-3]
    ent = manifest["instances"].get(tx)
    if ent is None:
        print(f"{argv[0]}: {tx} not in manifest", file=sys.stderr)
        return 1
    with lzma.open(tx_xz, "rb") as f:
        data = f.read()
    orig = invert_bytes(data, ent["perm"])
    with open(out_txt, "wb") as f:
        f.write(orig)
    print(f"inverted {tx} (official {ent['official']}) -> {out_txt}")
    return 0


def main(argv):
    if len(argv) < 2 or argv[1] not in ("--apply", "--invert"):
        print(__doc__)
        return 2
    if argv[1] == "--apply":
        return cmd_apply(argv)
    return cmd_invert(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
