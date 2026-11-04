#!/usr/bin/env python3
"""Structure-preserving transformation for the gp-dimacs10 form2 hidden set (vertex relabeling; exact isomorphism).

Transformation mathematics (the gp entry in form2-conversion-recipes.md):
  Apply a random vertex permutation π, relabel vertices by π, and rewrite the
  adjacency lists. The minimum balanced 4-cut depends only on adjacency
  structure, so its optimum is exactly invariant under π. Reuse K by isomorphism;
  remeasure B on the transformed instances (kaffpa's internal order depends on
  vertex IDs). **The task-level parameters k=4 blocks and 3% balance tolerance
  are not carried in files and are not changed by the permutation.**

Byte-level handling (fingerprint removal, following the same rule as the
2026-08-31 transformation batch):
  * Drop every `%` comment line.
  * Relabel vertices using the per-instance seeded permutation.
  * Re-emit each adjacency row with relabeled neighbors in ascending order, so
    the byte stream carries no trace of the original layout. Preserve each
    vertex's neighbor multiset exactly; the total remains 2m tokens.
  * Rewrite the header as "n m" (all scored instances in this task use fmt=0,
    with no edge weights).

Loading semantics (match scoring.py's load_instance line by line):
  Skip all `%` lines. After the header, every non-`%` line, including a blank
  line, is an adjacency row for one vertex (including isolated vertices).
  The total number of adjacency tokens must equal 2m.

Seed rule (same as the 2026-08-31 transformation batch):
    seed = int.from_bytes(sha256("tcshard-transform-20260831:" + official_name)[:8])
    perm = Random(seed).shuffle([1..n]); perm[v-1] = new label of old vertex v.
The complete permutation table is recorded in transform_manifest.json here,
under tests/ only, together with the mapping from official names to transformed
names txNNN. Validation and oracle rewriting do not depend on replaying the RNG.

Naming: hidden scored instances use new names txNNN.graph.bz2 (reference key
 txNNN.graph; txNNN numbers follow sorted official names).

Usage:
    transform.py --apply OFFICIAL_BZ2_DIR OUT_DIR MANIFEST_JSON [official_name.graph ...]
        Transform <official>.graph.bz2 from OFFICIAL_BZ2_DIR into
        txNNN.graph.bz2 under OUT_DIR and write or merge the manifest.
    transform.py --invert TX_BZ2 MANIFEST_JSON OUT_GRAPH
        Use the manifest permutation to invert the transformed instance to its
        original labels (header plus adjacency lists in original label order;
        comment lines cannot be recovered, but the result is semantically
        equivalent; see the round-trip assertion in test_transform.py).
"""
import bz2
import hashlib
import json
import os
import random
import sys

MASTER_SEED_TAG = "tcshard-transform-20260831"
TRANSFORM_ID = "vertex-relabeling-v1"


def derive_seed(official_name):
    """Per-instance seed: hash the master seed 20260831 together with the official instance name."""
    h = hashlib.sha256(f"{MASTER_SEED_TAG}:{official_name}".encode())
    return int.from_bytes(h.digest()[:8], "big")


def load_metis(text):
    """Parse decompressed METIS/DIMACS10 instance text and return (n, m, adj), where adj[v] is
    1-based neighbor list (in input order). Match scoring's loading semantics: skip `%` lines; after the header,
    each non-`%` line, including a blank line, is one vertex adjacency row."""
    lines = text.splitlines()
    n = m = None
    adj = []
    for line in lines:
        s = line.strip()
        if not s or s.startswith("%"):
            if n is not None and s.startswith("%"):
                continue
            if n is None:
                continue
        if n is None:
            parts = s.split()
            if len(parts) < 2:
                raise ValueError("malformed header line")
            n, m = int(parts[0]), int(parts[1])
            fmt = parts[2] if len(parts) > 2 else "0"
            if fmt != "0":
                raise ValueError(f"weighted graphs unsupported (fmt={fmt})")
            continue
        adj.append([int(t) for t in s.split()])
        if len(adj) == n:
            break
    if n is None:
        raise ValueError("empty instance")
    if len(adj) != n:
        raise ValueError(f"expected {n} adjacency lines, found {len(adj)}")
    if sum(len(a) for a in adj) != 2 * m:
        raise ValueError(f"expected {2*m} adjacency tokens, found "
                         f"{sum(len(a) for a in adj)}")
    return n, m, adj


def canonical_text(n, m, adj_new_order):
    """Canonical text consisting of the header and adjacency rows (neighbors already sorted)."""
    out = [f"{n} {m}\n"]
    out += [(" ".join(str(u) for u in line)) + "\n" for line in adj_new_order]
    return "".join(out)


def transform_text(text, official_name):
    """Transform one decompressed instance text. Return (new_text, perm, seed, n, m)."""
    n, m, adj = load_metis(text)
    seed = derive_seed(official_name)
    perm = list(range(1, n + 1))
    random.Random(seed).shuffle(perm)  # perm[v-1] = new label of old vertex v
    new_adj = [None] * n
    for v in range(n):
        new_adj[perm[v] - 1] = sorted(perm[u - 1] for u in adj[v])
    return canonical_text(n, m, new_adj), perm, seed, n, m


def invert_text(text, perm):
    """Invert the transformed text using the permutation table and emit canonical text with original labels."""
    n, m, adj = load_metis(text)
    if sorted(perm) != list(range(1, n + 1)):
        raise ValueError("perm is not a bijection of 1..n")
    inv = [0] * (n + 1)  # inv[new-1] = old
    for old, new in enumerate(perm, start=1):
        inv[new - 1] = old
    # adj[j] is the neighbor list for new vertex j+1 (members are also new labels); after inversion, original vertex v has
    # neighbors {inv[u-1] : u in adj[inv_new_pos-1]}, where the new position is perm[v-1]
    orig_adj = [None] * n
    for v in range(n):
        new_pos = perm[v]  # row number (1-based) of original vertex v+1 in the new file
        orig_adj[v] = sorted(inv[u - 1] for u in adj[new_pos - 1])
    return canonical_text(n, m, orig_adj)


def permute_partition_tokens(tokens, perm):
    """Synchronized solution transformation: move block labels with vertices, new_part[perm[v]-1] =
    old_part[v-1]. tokens contains one block ID per vertex."""
    if len(tokens) != len(perm):
        raise ValueError(f"partition has {len(tokens)} tokens, perm {len(perm)}")
    out = [None] * len(tokens)
    for v in range(len(tokens)):
        out[perm[v] - 1] = tokens[v]
    return out


def token_sha256_text(text):
    """Oracle-stub key: SHA-256 of the normalized token stream (decompressed text)."""
    return hashlib.sha256(" ".join(text.split()).encode()).hexdigest()


def cmd_apply(argv):
    if len(argv) < 4:
        print(f"usage: {argv[0]} --apply OFFICIAL_BZ2_DIR OUT_DIR MANIFEST_JSON "
              "[official_name.graph ...]", file=sys.stderr)
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
        "hash_note": "sha256 values are over the decompressed token stream",
        "params_note": ("k=4 blocks / 3% balance tolerance are task-level "
                        "constants, not carried by instance files; the "
                        "transform does not touch them"),
        "instances": {},
    }
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            manifest = json.load(f)
        manifest.setdefault("instances", {})
    officials = sorted(names)
    for i, official in enumerate(officials, start=1):
        tx = f"tx{i:03d}.graph"
        with bz2.open(os.path.join(in_dir, official + ".bz2"), "rt") as f:
            text = f.read()
        new_text, perm, seed, n, m = transform_text(text, official)
        with bz2.open(os.path.join(out_dir, tx + ".bz2"), "wt") as f:
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
        print(f"usage: {argv[0]} --invert TX_BZ2 MANIFEST_JSON OUT_GRAPH",
              file=sys.stderr)
        return 2
    tx_bz2, manifest_path, out_graph = argv[2:5]
    with open(manifest_path) as f:
        manifest = json.load(f)
    tx = os.path.basename(tx_bz2)
    if tx.endswith(".bz2"):
        tx = tx[:-4]
    ent = manifest["instances"].get(tx)
    if ent is None:
        print(f"{argv[0]}: {tx} not in manifest", file=sys.stderr)
        return 1
    with bz2.open(tx_bz2, "rt") as f:
        text = f.read()
    with open(out_graph, "w") as f:
        f.write(invert_text(text, ent["perm"]))
    print(f"inverted {tx} (official {ent['official']}) -> {out_graph}")
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
