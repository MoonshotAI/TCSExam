#!/usr/bin/env python3
"""make_split.py — one-time, frozen form2 public/hidden split generator for maxcut-mqlib.

Rule (general rules in form2-conversion-recipes.md): 70% public practice / 30% hidden judging,
using stratified sampling by family × size instead of pure random sampling. Once merged, the split is frozen and is not adjusted based on experimental results.

Reuse the four size buckets from this task’s 2026-08 authoring (tests/SAMPLING.md), based on edge count m:
  S1: m < 20,000；S2: 20,000 <= m < 100,000；
  S3: 100,000 <= m < 1,000,000；S4: m >= 1,000,000。
Hidden quota per bucket = round(0.3 × bucket size); fix the full hidden count at 45 (105 public):
Allocate bucket quotas by largest remainder (start with floor(0.3 × bucket), then fill buckets with larger remainders first; break ties by bucket ID
in lexicographic order); within each bucket, allocate hidden quotas to family × size cells by largest remainder (ties by family name
lexicographically), then select each cell's quota using a fixed-seed shuffle. A singleton family cell may have no
hidden representative if its remainder is too small; this is a 30% sample, so not every family must appear.

Determinism: all randomness comes from per-cell seeds derived from MASTER_SEED_TAG (sha256), so rerunning the script
at any time produces the same split.json.

Usage: python3 make_split.py (run from tests/; writes split.json and prints
stratification table, which is copied unchanged into PROVENANCE.md)
"""
import hashlib
import json
import os
import random
from collections import Counter, defaultdict

MASTER_SEED_TAG = "tcshard-form2-split-260920:maxcut-mqlib"
N_HIDDEN_TOTAL = 45
HERE = os.path.dirname(os.path.abspath(__file__))


def bucket_of(m):
    if m < 20000:
        return "S1"
    if m < 100000:
        return "S2"
    if m < 1000000:
        return "S3"
    return "S4"


def cell_seed(*parts):
    h = hashlib.sha256(":".join([MASTER_SEED_TAG, *parts]).encode())
    return int.from_bytes(h.digest()[:8], "big")


def largest_remainder(quota, cells):
    """cells: {key: size}; return {key: hidden quota}, with the sum equal to quota.
    Start with floor(0.3*size); allocate remaining items to larger remainders first, breaking ties by key in lexicographic order."""
    exact = {k: 0.3 * v for k, v in cells.items()}
    alloc = {k: int(x) for k, x in exact.items()}
    remaining = quota - sum(alloc.values())
    assert 0 <= remaining <= len(cells), (quota, cells)
    order = sorted(cells, key=lambda k: (-(exact[k] - alloc[k]), k))
    for k in order[:remaining]:
        alloc[k] += 1
    assert sum(alloc.values()) == quota
    return alloc


def main():
    with open(os.path.join(HERE, "reference.json")) as f:
        ref = json.load(f)["instances"]
    by_bucket = defaultdict(dict)
    for name, e in ref.items():
        by_bucket[bucket_of(e["m"])][name] = e

    # Allocate the 45 hidden slots across buckets: floor(0.3*bucket) plus largest remainders, ties by bucket ID lexicographically.
    bucket_sizes = {b: len(names) for b, names in sorted(by_bucket.items())}
    bucket_quota = largest_remainder(N_HIDDEN_TOTAL, bucket_sizes)

    split = {}
    table_rows = []
    for b in sorted(by_bucket):
        names = by_bucket[b]
        fam_cells = defaultdict(list)
        for name, e in names.items():
            fam_cells[e["family"]].append(name)
        cell_quota = largest_remainder(
            bucket_quota[b], {f: len(v) for f, v in sorted(fam_cells.items())})
        for fam in sorted(fam_cells):
            cell = sorted(fam_cells[fam])
            q = cell_quota[fam]
            rng = random.Random(cell_seed(b, fam))
            shuffled = cell[:]
            rng.shuffle(shuffled)
            hidden = sorted(shuffled[:q])
            public = sorted(shuffled[q:])
            for n in hidden:
                split[n] = "hidden"
            for n in public:
                split[n] = "public"
            table_rows.append((b, fam, len(cell), len(public), len(hidden)))

    assert len(split) == len(ref) == 150
    n_hidden = sum(1 for v in split.values() if v == "hidden")
    n_public = sum(1 for v in split.values() if v == "public")
    assert (n_public, n_hidden) == (105, 45), (n_public, n_hidden)

    out = {
        "master_seed_tag": MASTER_SEED_TAG,
        "rule": ("70/30 stratified by family x size bucket (S1: m<2e4, "
                 "S2: 2e4<=m<1e5, S3: 1e5<=m<1e6, S4: m>=1e6); per-bucket "
                 "hidden quota by largest remainder (bucket id breaks ties), "
                 "per family x bucket cell quota by largest remainder (family "
                 "name breaks ties), in-cell seeded shuffle; generator "
                 "tests/make_split.py"),
        "counts": {"public": n_public, "hidden": n_hidden},
        "instances": dict(sorted(split.items())),
    }
    with open(os.path.join(HERE, "split.json"), "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)
        f.write("\n")

    print("| Size bucket | Family | Cell size | Public | Hidden |")
    print("|---|---|---|---|---|")
    for b, fam, size, npub, nhid in table_rows:
        print(f"| {b} | {fam} | {size} | {npub} | {nhid} |")
    tot = Counter()
    for b, fam, size, npub, nhid in table_rows:
        tot[b] += nhid
    print("bucket hidden:", dict(tot), "total:", sum(tot.values()))


if __name__ == "__main__":
    main()
