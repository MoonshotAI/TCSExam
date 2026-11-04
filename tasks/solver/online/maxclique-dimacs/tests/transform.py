#!/usr/bin/env python3
"""Structure-preserving transformation for the maxclique-dimacs form2 hidden set (vertex relabeling; exact isomorphism).

Transformation mathematics (the graph entry in form2-conversion-recipes.md):
  Apply a random vertex permutation π, relabel vertices by π, and rewrite the
  edge list. The maximum clique size depends only on adjacency structure, so
  ω(G') == ω(G). Reuse K by isomorphism; remeasure B on transformed instances
  because MaxCliqueDyn's search order depends on vertex IDs.

Byte-level handling (fingerprint removal, following the same rule as the
2026-08-31 transformation batch):
  * Drop every `c` comment line (the original header comments include instance
    names and sources, which can act as memorized fingerprints); leave one
    uniform-format comment in the transformed file.
  * Relabel vertices using the per-instance seeded permutation.
  * Normalize each edge to (a<b), then deduplicate and sort (matching checker
    loading semantics: repeated and bidirectional rows collapse into an edge
    set, and self-loops are discarded). This removes original layout traces.
  * Rewrite the header as `p edge n <deduplicated edge count>` (the original m
    counts both directions separately; the task statement already calls m
    advisory).

Seed rule (same as the 2026-08-31 batch and the 260913 async restoration batch):
    seed = int.from_bytes(sha256("tcshard-transform-20260831:" + official_name)[:8])
    perm = Random(seed).shuffle([1..n]); perm[v-1] = new label of old vertex v.
The complete permutation table is recorded in transform_manifest.json here,
under tests/ only, together with the mapping from official names to transformed
names txNNN. Validation and oracle rewriting do not depend on replaying the RNG.

Naming: hidden scored instances use new names txNNN.clq to avoid collisions
with public instances (txNNN numbers follow sorted official names).

Usage:
    transform.py --apply OFFICIAL_COL_DIR OUT_DIR MANIFEST_JSON [official_name.clq ...]
        Transform <official>.clq from OFFICIAL_COL_DIR into txNNN.clq under
        OUT_DIR and write or merge the manifest.
    transform.py --invert TX_COL MANIFEST_JSON OUT_COL
        Use the manifest permutation to invert the transformed instance to its
        original labels (uniform comment header plus sorted edge list in
        original labels; original comment lines cannot be recovered, but the
        result is semantically equivalent; see test_transform.py's round-trip
        assertion).
"""
import hashlib
import json
import os
import random
import sys

MASTER_SEED_TAG = "tcshard-transform-20260831"
TRANSFORM_ID = "vertex-relabeling-v1"
HEADER_COMMENT = "c max clique instance (DIMACS ASCII)"


def derive_seed(official_name):
    """Per-instance seed: hash the master seed 20260831 together with the official instance name."""
    h = hashlib.sha256(f"{MASTER_SEED_TAG}:{official_name}".encode())
    return int.from_bytes(h.digest()[:8], "big")


def parse_dimacs_text(text):
    """Parse DIMACS ASCII graph text and return (n, edges), where edges is a set of (u,v) pairs
    (1-based, u<v; duplicate and bidirectional rows are collapsed, self-loops discarded, matching the scoring checker loading semantics
    ). If no p line exists, fall back to the largest vertex ID."""
    n = None
    vmax = 0
    edges = set()
    for line in text.splitlines():
        if not line or line[0] in "c\r\n":
            continue
        parts = line.split()
        if line[0] == "p":
            if len(parts) >= 4:
                n = int(parts[2])
        elif line[0] == "e":
            if len(parts) < 3:
                continue
            u, v = int(parts[1]), int(parts[2])
            if u == v or u < 1 or v < 1:
                continue
            if u > v:
                u, v = v, u
            edges.add((u, v))
            vmax = max(vmax, u, v)
    if n is None:
        n = vmax
    if n < vmax:
        n = vmax
    if n < 1:
        raise ValueError("no p line and no edges")
    return n, edges


def canonical_text(n, edges):
    """Canonical text with a uniform comment header, p line, and sorted edge list."""
    ordered = sorted((a, b) if a < b else (b, a) for a, b in edges)
    out = [HEADER_COMMENT + "\n", f"p edge {n} {len(ordered)}\n"]
    out += [f"e {a} {b}\n" for a, b in ordered]
    return "".join(out)


def transform_text(text, official_name):
    """Transform one instance. Return (new_text, perm, seed, n, m)."""
    n, edges = parse_dimacs_text(text)
    seed = derive_seed(official_name)
    perm = list(range(1, n + 1))
    random.Random(seed).shuffle(perm)  # perm[v-1] = new label of old vertex v
    new_edges = set()
    for u, v in edges:
        a, b = perm[u - 1], perm[v - 1]
        if a > b:
            a, b = b, a
        new_edges.add((a, b))
    return canonical_text(n, new_edges), perm, seed, n, len(new_edges)


def invert_text(text, perm):
    """Invert the transformed text using the permutation table and emit canonical text with original labels."""
    n, edges = parse_dimacs_text(text)
    if sorted(perm) != list(range(1, n + 1)):
        raise ValueError("perm is not a bijection of 1..n")
    inv = [0] * n  # inv[new-1] = old
    for old, new in enumerate(perm, start=1):
        inv[new - 1] = old
    orig_edges = set()
    for a, b in edges:
        orig_edges.add((inv[a - 1], inv[b - 1]))
    return canonical_text(n, orig_edges)


def permute_clique_tokens(tokens, perm):
    """Synchronized solution transformation: relabel clique vertices by π (new_label = perm[v-1]).
    tokens is the solution-file token list: the first token is the clique size k (kept unchanged), followed by
    k 1-based vertex IDs; replace each vertex ID v with perm[v-1]."""
    k, verts = tokens[0], tokens[1:]
    if int(k) != len(verts):
        raise ValueError(f"clique declares k={k} but has {len(verts)} vertices")
    n = len(perm)
    out = []
    for tok in verts:
        v = int(tok)
        if v < 1 or v > n:
            raise ValueError(f"clique vertex {v} out of range 1..{n}")
        out.append(str(perm[v - 1]))
    return [k] + out


def token_sha256_text(text):
    """Oracle-stub key: SHA-256 of the normalized token stream."""
    return hashlib.sha256(" ".join(text.split()).encode()).hexdigest()


def cmd_apply(argv):
    if len(argv) < 4:
        print(f"usage: {argv[0]} --apply OFFICIAL_COL_DIR OUT_DIR MANIFEST_JSON "
              "[official_name.clq ...]", file=sys.stderr)
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
        "hash_note": "sha256 values are over the normalized token stream",
        "instances": {},
    }
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            manifest = json.load(f)
        manifest.setdefault("instances", {})
    officials = sorted(names)
    for i, official in enumerate(officials, start=1):
        tx = f"tx{i:03d}.clq"
        with open(os.path.join(in_dir, official), errors="replace") as f:
            text = f.read()
        new_text, perm, seed, n, m = transform_text(text, official)
        with open(os.path.join(out_dir, tx), "w") as f:
            f.write(new_text)
        manifest["instances"][tx] = {
            "official": official,
            "seed_hex": f"{seed:016x}",
            "n": n,
            "m": m,
            "perm": perm,
            "sha256_orig_tokens": token_sha256_text(text),
            "sha256_new_tokens": token_sha256_text(new_text),
        }
        print(f"  {official} -> {tx}: n={n} m={m} seed={seed:016x}", flush=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
    print(f"transformed {len(officials)} instance(s) -> {out_dir}")
    print(f"manifest -> {manifest_path}")
    return 0


def cmd_invert(argv):
    if len(argv) != 5:
        print(f"usage: {argv[0]} --invert TX_COL MANIFEST_JSON OUT_COL",
              file=sys.stderr)
        return 2
    tx_col, manifest_path, out_col = argv[2:5]
    with open(manifest_path) as f:
        manifest = json.load(f)
    tx = os.path.basename(tx_col)
    ent = manifest["instances"].get(tx)
    if ent is None:
        print(f"{argv[0]}: {tx} not in manifest", file=sys.stderr)
        return 1
    with open(tx_col, errors="replace") as f:
        text = f.read()
    with open(out_col, "w") as f:
        f.write(invert_text(text, ent["perm"]))
    print(f"inverted {tx} (official {ent['official']}) -> {out_col}")
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
