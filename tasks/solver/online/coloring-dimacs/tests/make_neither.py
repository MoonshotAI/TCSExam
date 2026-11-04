#!/usr/bin/env python3
"""make_neither.py — one-time, frozen generator for the coloring-dimacs neither-set holdout list.

Rule (holdout section of form2-conversion-recipes.md): because the judged set is close to the full publicly registered set, take an additional sample from
From the public bucket in the original split, select a further 15% stratified proportionally by family × size (240 total →
36 neither); exclude these from the environment and scoring; **leave the hidden bucket unchanged**.
Effect: dilute the candidate set from "exactly 72" to "official full set − environment instances" (36 of the 108 are decoys).

Reuse the size buckets and family definition from tests/make_split.py (B1: m<2e3 / B2: 2e3<=m<2e4 /
B3: 2e4<=m<1e5 / B4: m>=1e5; family comes from the family field in reference). Start bucket quotas
at floor(0.15 × bucket size), then use the largest-remainder method to reach 36 (ties by bucket ID lexicographically); within each bucket,
allocate to family cells by the largest-remainder method (ties by family name in lexicographic order); within each cell, choose **only from public members**
with a fixed-seed shuffle. Store the list only in tests/split.json (a leak invalidates the holdout).

Determinism: all randomness comes from per-cell seeds derived from SEED_TAG (sha256), so rerunning the script at any time
produces the same list.

Usage: python3 make_neither.py (run from tests/; updates split.json in place
add the neither bucket and print a family-level stratification table, which is copied unchanged into PROVENANCE.md)
"""
import hashlib
import json
import os
import random
from collections import Counter, defaultdict

SEED_TAG = "tcshard-form2-neither-coloring-dimacs-260920"
N_NEITHER_TOTAL = 36
HERE = os.path.dirname(os.path.abspath(__file__))


def bucket_of(m):
    if m < 2000:
        return "B1"
    if m < 20000:
        return "B2"
    if m < 100000:
        return "B3"
    return "B4"


def cell_seed(*parts):
    h = hashlib.sha256(":".join([SEED_TAG, *parts]).encode())
    return int.from_bytes(h.digest()[:8], "big")


def largest_remainder(quota, cells, rate=0.15):
    """cells: {key: size}; return {key: quota}, with the sum equal to quota."""
    exact = {k: rate * v for k, v in cells.items()}
    alloc = {k: int(x) for k, x in exact.items()}
    remaining = quota - sum(alloc.values())
    assert 0 <= remaining <= len(cells), (quota, cells)
    order = sorted(cells, key=lambda k: (-(exact[k] - alloc[k]), k))
    for k in order[:remaining]:
        alloc[k] += 1
    assert sum(alloc.values()) == quota
    return alloc


def main():
    with open(os.path.join(HERE, "split.json")) as f:
        split_doc = json.load(f)
    split = split_doc["instances"]
    assert set(split.values()) <= {"public", "hidden"}, "neither bucket already exists; do not rerun after freezing"
    with open(os.path.join(HERE, "reference.json")) as f:
        ref = json.load(f)["instances"]
    # Size/family data for 168 public instances comes from the environment-side public_reference; the 72 hidden names in split
    # are official names, while reference has txNNN keys; load hidden metadata (including family/m) from transform_manifest.
    with open(os.path.join(HERE, "..", "environment", "app",
                           "public_reference.json")) as f:
        pub_ref = json.load(f)["instances"]
    with open(os.path.join(HERE, "transform_manifest.json")) as f:
        tman = json.load(f)["instances"]
    all_entries = dict(pub_ref)
    for tx, ent in tman.items():
        all_entries[ent["official"]] = {"family": ent["family"], "m": ent["m"],
                                        "n": ent["n"]}

    by_bucket = defaultdict(lambda: defaultdict(list))
    for name, side in split.items():
        e = all_entries[name]
        by_bucket[bucket_of(e["m"])][e["family"]].append((name, side))

    bucket_sizes = {b: sum(len(v) for v in cells.values())
                    for b, cells in by_bucket.items()}
    bucket_quota = largest_remainder(N_NEITHER_TOTAL, bucket_sizes)

    neither = []
    table_rows = []
    for b in sorted(by_bucket):
        cells = by_bucket[b]
        cell_quota = largest_remainder(
            bucket_quota[b], {f: len(v) for f, v in sorted(cells.items())})
        for fam in sorted(cells):
            members = sorted(cells[fam])
            public_members = sorted(n for n, s in members if s == "public")
            q = cell_quota[fam]
            assert q <= len(public_members), (b, fam, q, len(public_members))
            rng = random.Random(cell_seed(b, fam))
            shuffled = public_members[:]
            rng.shuffle(shuffled)
            picked = sorted(shuffled[:q])
            neither.extend(picked)
            table_rows.append((b, fam, len(members),
                               sum(1 for _, s in members if s == "hidden"),
                               len(public_members), q))

    assert len(neither) == N_NEITHER_TOTAL == 36
    assert not any(split[n] != "public" for n in neither), "a hidden-bucket item was changed"
    for n in neither:
        split[n] = "neither"

    counts = Counter(split.values())
    assert (counts["public"], counts["hidden"], counts["neither"]) == (132, 72, 36)
    split_doc["neither_seed_tag"] = SEED_TAG
    split_doc["rule"] = (split_doc["rule"] + " | neither: 15% stratified holdout "
                         "from the public bucket by the same family x size cells "
                         "(hidden bucket untouched), generator "
                         "tests/make_neither.py; names live ONLY in tests/split.json")
    split_doc["counts"] = {"public": counts["public"], "hidden": counts["hidden"],
                           "neither": counts["neither"]}
    with open(os.path.join(HERE, "split.json"), "w") as f:
        json.dump(split_doc, f, indent=1, sort_keys=True)
        f.write("\n")

    print("| Size bucket | Family | Cell size | Hidden (unchanged) | Public candidates | Neither |")
    print("|---|---|---|---|---|---|")
    for b, fam, size, nhid, npub, q in table_rows:
        print(f"| {b} | {fam} | {size} | {nhid} | {npub} | {q} |")
    tot = Counter()
    for b, fam, size, nhid, npub, q in table_rows:
        tot[b] += q
    print("bucket neither:", dict(tot), "total:", sum(tot.values()))


if __name__ == "__main__":
    main()
