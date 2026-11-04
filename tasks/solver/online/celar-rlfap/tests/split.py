#!/usr/bin/env python3
"""One-time, frozen form2 70/30 split generator for celar-rlfap, with the 260920 dilution.

Usage:
  python3 tests/split.py          # Initial 70/30 split (frozen; reruns only check
                                  # deterministic reproduction)
  python3 tests/split.py dilute   # Move selected public instances into neither
                                  # (frozen; reruns only check deterministic reproduction)

The deterministic split assigns 70% public practice
and 30% hidden judging by family × size. This task's implementation:
  - Families: scen (11) / graph (14), the two instance families in the ZIB CALMA archive.
  - Size: num_variables, split into two tiers at the median within each family
    (scen 5/6, graph 7/7).
  - Hidden quota: allocate 8 slots by the largest-remainder method proportional to
    family size: scen 11/25×8=3.52→4, graph 14/25×8=4.48→4. Then allocate within
    tiers by tier size using the same method (scen 2/2, graph 2/2).
  - Use a fixed seed to sample within each of four tiers:
      seed = int.from_bytes(sha256("tcshard-form2-split-celar-rlfap-260920")
             .digest()[:8], "big")
    A single random.Random(seed) samples scen small/large, then graph small/large;
    sort each tier by (num_variables, instance name).

Unscored-instance rule: the scored set is close to the public archive (all 25 ZIB CALMA instances),
so hidden identities can be identified exactly by "official full set minus public
environment set." Move 4 additional public instances into neither (not included in
the environment or scored), the upper end of 10–15% of 25. Reuse family × size
tiers; allocate family quotas by the largest-remainder method (scen 4×7/17→2,
graph 4×10/17→2), then choose one from each of scen small/large and graph small/
large. Leave the hidden bucket unchanged. Seed:
      seed = int.from_bytes(sha256("tcshard-form2-neither-celar-rlfap-260920")
             .digest()[:8], "big")
    A single random.Random(seed) samples the four tiers in the original order.

Output: tests/split.json maps instance names to "public"/"hidden"/"neither". Once
merged, the split is frozen and is not adjusted based on experimental results."""
import hashlib
import json
import os
import random
import re
import sys

SEED_PREFIX = "tcshard-form2-split-celar-rlfap-260920"
NEITHER_SEED_PREFIX = "tcshard-form2-neither-celar-rlfap-260920"

TESTS = os.path.dirname(os.path.abspath(__file__))
LIBRARY = os.path.join(TESTS, "instances-library")
N_HIDDEN = 8
N_NEITHER = 4


def num_variables(path):
    with open(path, errors="replace") as f:
        text = f.read()
    m = re.search(r"num_variables\s*=\s*(-?\d+)\s*;", text)
    if not m:
        raise ValueError(f"num_variables not found in {path}")
    return int(m.group(1))


def largest_remainder(quota_map, total):
    """quota_map: stratum -> float quota; use the largest-remainder method to round quotas so their sum equals total."""
    floors = {k: int(v) for k, v in quota_map.items()}
    rest = total - sum(floors.values())
    by_rem = sorted(quota_map, key=lambda k: (quota_map[k] - floors[k], k),
                    reverse=True)
    for k in by_rem[:rest]:
        floors[k] += 1
    return floors


def strata():
    """The original family × size tiers (25 instances total; sort each tier by (num_variables, instance name)
    within the tier). Return [(label, [instance names...]), ...] in RNG consumption order."""
    names = sorted(f for f in os.listdir(LIBRARY) if f.endswith(".dzn"))
    if len(names) != 25:
        raise SystemExit(f"expected the 25 CALMA-library instances, "
                         f"got {len(names)}")
    fams = {"scen": [], "graph": []}
    for fn in names:
        fams["scen" if fn.startswith("scen") else "graph"].append(
            (num_variables(os.path.join(LIBRARY, fn)), fn))
    out = []
    for fam in ("scen", "graph"):
        members = sorted(fams[fam])
        half = len(members) // 2
        out.append((f"{fam}-small", [fn for _, fn in members[:half]]))
        out.append((f"{fam}-large", [fn for _, fn in members[half:]]))
    return out


def write_split(out):
    path = os.path.join(TESTS, "split.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)
        f.write("\n")
    os.chmod(path, 0o644)


def cmd_split():
    seed = int.from_bytes(hashlib.sha256(SEED_PREFIX.encode()).digest()[:8],
                          "big")
    rng = random.Random(seed)
    split = {}
    table = []
    for fam in ("scen", "graph"):
        fams_members = [(label, ms) for label, ms in strata()
                        if label.startswith(fam)]
        members = [fn for _, ms in fams_members for fn in ms]
        # Family quotas: scen 11/25*8=3.52→4, graph 14/25*8=4.48→4 (largest-remainder method)
        fam_quota = {"scen": 11 / 25 * N_HIDDEN, "graph": 14 / 25 * N_HIDDEN}
        fam_hidden = largest_remainder(fam_quota, N_HIDDEN)[fam]
        tier_quota = {ti: fam_hidden * len(fams_members[ti][1]) / len(members)
                      for ti in range(2)}
        tier_hidden = largest_remainder(tier_quota, fam_hidden)
        for ti, (label, ms) in enumerate(fams_members):
            k = tier_hidden[ti]
            picked = set(rng.sample(ms, k))
            for fn in ms:
                split[fn] = "hidden" if fn in picked else "public"
            table.append((label, len(ms), k, sorted(picked)))
    out = {fn: split[fn] for fn in sorted(split)}
    path = os.path.join(TESTS, "split.json")
    if os.path.isfile(path):
        with open(path) as f:
            cur = json.load(f)
        if {k: v for k, v in cur.items() if v != "neither"} == out:
            print(f"split.json already matches this deterministic draw "
                  f"(seed {seed}); unchanged")
            return
        raise SystemExit("split.json exists and differs — the split is "
                         "frozen; refusing to overwrite")
    write_split(out)
    n_h = sum(1 for v in out.values() if v == "hidden")
    print(f"seed={seed}  public={25 - n_h} hidden={n_h}")
    for label, size, k, picked in table:
        print(f"  stratum {label:12s} size={size} hidden={k}: {picked}")


def cmd_dilute():
    path = os.path.join(TESTS, "split.json")
    with open(path) as f:
        split = json.load(f)
    seed = int.from_bytes(hashlib.sha256(NEITHER_SEED_PREFIX.encode())
                          .digest()[:8], "big")
    rng = random.Random(seed)
    tiers = strata()  # [scen-small, scen-large, graph-small, graph-large]
    # Family quotas: allocate 4 slots across the 17 public instances (scen 7 + graph 10) proportionally by largest remainder
    # （scen 4×7/17=1.65→2，graph 4×10/17=2.35→2）
    n_pub = {"scen": sum(1 for fn, v in split.items()
                         if v == "public" and fn.startswith("scen")),
             "graph": sum(1 for fn, v in split.items()
                          if v == "public" and fn.startswith("graph"))}
    fam_neither = largest_remainder(
        {fam: N_NEITHER * n / sum(n_pub.values())
         for fam, n in n_pub.items()}, N_NEITHER)
    picked_all = {}
    table = []
    for fam in ("scen", "graph"):
        fam_tiers = [t for t in tiers if t[0].startswith(fam)]
        pub_counts = [sum(1 for fn in ms if split[fn] == "public")
                      for _, ms in fam_tiers]
        quota = {ti: fam_neither[fam] * pub_counts[ti] / sum(pub_counts)
                 for ti in range(2)}
        tier_neither = largest_remainder(quota, fam_neither[fam])
        for ti, (label, ms) in enumerate(fam_tiers):
            public_ms = [fn for fn in ms if split[fn] == "public"]
            k = tier_neither[ti]
            picked = set(rng.sample(public_ms, k))
            for fn in picked:
                picked_all[fn] = "neither"
            table.append((label, len(public_ms), k, sorted(picked)))
    out = dict(split)
    out.update(picked_all)
    out = {fn: out[fn] for fn in sorted(out)}
    if split == out:
        print("dilution already applied identically; unchanged")
        return
    if any(v == "neither" for v in split.values()):
        raise SystemExit("split.json already has a different neither set — "
                         "the dilution is frozen; refusing to overwrite")
    write_split(out)
    n_p = sum(1 for v in out.values() if v == "public")
    n_h = sum(1 for v in out.values() if v == "hidden")
    n_n = sum(1 for v in out.values() if v == "neither")
    print(f"neither-seed={seed}  public={n_p} hidden={n_h} neither={n_n}")
    for label, size, k, picked in table:
        print(f"  stratum {label:12s} public={size} neither={k}: {picked}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "dilute":
        cmd_dilute()
    else:
        cmd_split()
