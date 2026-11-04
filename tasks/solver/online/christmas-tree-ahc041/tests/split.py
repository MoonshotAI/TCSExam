#!/usr/bin/env python3
"""One-time, frozen form2 70/30 split generator for christmas-tree-ahc041.

General rule (form2-conversion-recipes.md): stratified sampling by family × size,
with 70% public practice and 30% hidden judging. This task's implementation:
  - Pool: 150 instances = 100 official public inputs (environment/app/instances,
    0000–0099.txt) plus 50 generated instances (h00–h49.txt under tests/; the
    official generator seed is unpublished).
  - Family handling: all 45 hidden instances come from the generated family. The K
    anchors (ratcheted from self-run simulated annealing measurements) cover only
    those 50 generated instances; official-family instances would have no K to reuse
    by isomorphism. Keep all 100 official instances public to maximize the practice
    set; select 45 generated instances as hidden and keep the other 5 public, for
    105 public total.
  - Size: all instances have the same N=1000, with only small changes in M, so
    stratify by sum(A), total vertex weight. Sort into five equal tiers of 10, then
    select 9 hidden instances per tier.
  - Use a fixed seed to sample within each tier:
      seed = int.from_bytes(sha256("tcshard-form2-split-christmas-tree-ahc041-260920")
             .digest()[:8], "big")
    A single random.Random(seed) samples each tier in order of increasing sum(A).

Output: tests/split.json maps instance names to "public"/"hidden". Once merged, the
split is frozen and is not adjusted based on experimental results. Rerunning this
script must reproduce split.json byte for byte (determinism check)."""
import hashlib
import json
import os
import random
import sys

SEED_PREFIX = "tcshard-form2-split-christmas-tree-ahc041-260920"
TESTS = os.path.dirname(os.path.abspath(__file__))
ENV_INST = os.path.join(TESTS, "..", "environment", "app", "instances")
SELFGEN_DIR = os.path.join(TESTS, "instances-library")
N_HIDDEN = 45


def sum_a(path):
    with open(path) as f:
        vals = f.read().split()
    n = int(vals[0])
    return sum(int(v) for v in vals[3:3 + n])


def main():
    officials = sorted(f for f in os.listdir(ENV_INST) if f.endswith(".txt"))
    selfgen = sorted(f for f in os.listdir(SELFGEN_DIR) if f.endswith(".txt"))
    if len(officials) != 100 or len(selfgen) != 50:
        raise SystemExit(f"pool mismatch: official {len(officials)}, "
                         f"selfgen {len(selfgen)}")
    members = sorted((sum_a(os.path.join(SELFGEN_DIR, fn)), fn)
                     for fn in selfgen)
    tiers = [members[i * 10:(i + 1) * 10] for i in range(5)]
    seed = int.from_bytes(hashlib.sha256(SEED_PREFIX.encode()).digest()[:8],
                          "big")
    rng = random.Random(seed)
    split = {fn: "public" for fn in officials}
    table = []
    for ti, tier in enumerate(tiers):
        picked = set(rng.sample([fn for _, fn in tier], 9))
        for _, fn in tier:
            split[fn] = "hidden" if fn in picked else "public"
        table.append((ti, sorted(picked)))
    out = {fn: split[fn] for fn in sorted(split)}
    path = os.path.join(TESTS, "split.json")
    if os.path.isfile(path):
        with open(path) as f:
            if json.load(f) == out:
                print(f"split.json already matches this deterministic draw "
                      f"(seed {seed}); unchanged")
                return
        raise SystemExit("split.json exists and differs — the split is "
                         "frozen; refusing to overwrite")
    with open(path, "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)
        f.write("\n")
    os.chmod(path, 0o644)
    n_h = sum(1 for v in out.values() if v == "hidden")
    n_p = sum(1 for v in out.values() if v == "public")
    print(f"seed={seed}  public={n_p} (official 100 + selfgen "
          f"{n_p - 100}) hidden={n_h}")
    for ti, picked in table:
        print(f"  stratum sumA-tier{ti} hidden=9: {picked}")


if __name__ == "__main__":
    sys.exit(main())
