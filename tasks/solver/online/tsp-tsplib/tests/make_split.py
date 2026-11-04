#!/usr/bin/env python3
"""make_split.py — one-time, frozen form2 public/hidden split generator for tsp-tsplib.

Rule (general rules in form2-conversion-recipes.md): 70% public practice / 30% hidden judging,
using stratified sampling by family × size instead of pure random sampling. Once merged, the split is frozen and is not adjusted based on experimental results.

Family definition (the task has no existing family field; set during the 260920 conversion): group by instance-name prefix. A prefix
(the initial letter string of the name) that occurs at least 3 times in the full set is its own family (kroA/kroB/kroC/kroD/kroE
are separate families); prefixes occurring fewer than 3 times are merged into misc. Split size buckets by city count n:
  S: n < 1,000；M: 1,000 <= n < 3,000；L: n >= 3,000。
The total hidden count is fixed at 33 (78 public). Starting from floor(0.3 × bucket size), allocate bucket quotas by the largest-remainder method,
adding remaining items by descending remainder (ties broken by bucket ID in lexicographic order). Within each bucket, allocate quotas to family × size cells by the largest-remainder method
(ties broken by family name in lexicographic order), then use a fixed-seed shuffle within each cell to choose the quota. A singleton family cell
may have no hidden representative if its remainder is too small. The hidden set is a 30% sample; every family does not need to appear.

Determinism: all randomness comes from per-cell seeds derived from MASTER_SEED_TAG (sha256), so rerunning the script
at any time produces the same split.json.

Usage: python3 make_split.py (run from tests/; writes split.json and prints
stratification table, which is copied unchanged into PROVENANCE.md)
"""
import hashlib
import json
import os
import random
import re
from collections import Counter, defaultdict

MASTER_SEED_TAG = "tcshard-form2-split-260920:tsp-tsplib"
N_HIDDEN_TOTAL = 33
HERE = os.path.dirname(os.path.abspath(__file__))


def bucket_of(n):
    if n < 1000:
        return "S"
    if n < 3000:
        return "M"
    return "L"


def prefix_of(name):
    m = re.match(r"([a-zA-Z]+)", name)
    return m.group(1) if m else name


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
    # Family merge: prefixes occurring fewer than 3 times in the full set are merged into misc.
    prefix_counts = Counter(prefix_of(n) for n in ref)
    def family_of(name):
        p = prefix_of(name)
        return p if prefix_counts[p] >= 3 else "misc"

    by_bucket = defaultdict(dict)
    for name, e in ref.items():
        by_bucket[bucket_of(e["n"])][name] = e

    bucket_sizes = {b: len(names) for b, names in sorted(by_bucket.items())}
    bucket_quota = largest_remainder(N_HIDDEN_TOTAL, bucket_sizes)

    split = {}
    table_rows = []
    for b in sorted(by_bucket):
        names = by_bucket[b]
        fam_cells = defaultdict(list)
        for name in names:
            fam_cells[family_of(name)].append(name)
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

    assert len(split) == len(ref) == 111
    n_hidden = sum(1 for v in split.values() if v == "hidden")
    n_public = sum(1 for v in split.values() if v == "public")
    assert (n_public, n_hidden) == (78, 33), (n_public, n_hidden)

    out = {
        "master_seed_tag": MASTER_SEED_TAG,
        "rule": ("70/30 stratified by family x size bucket (family = name-prefix "
                 "group, prefixes with <3 members merged into misc; S: n<1000, "
                 "M: 1000<=n<3000, L: n>=3000); per-bucket hidden quota by "
                 "largest remainder (bucket id breaks ties), per family x bucket "
                 "cell quota by largest remainder (family name breaks ties), "
                 "in-cell seeded shuffle; generator tests/make_split.py"),
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
