#!/usr/bin/env python3
"""One-time, frozen form2 70/30 split generator for itc2021-sports-timetabling, including unscored instances.

Usage:
  python3 tests/split.py          # Initial 70/30 split (frozen; reruns only check
                                  # deterministic reproduction)
  python3 tests/split.py dilute   # Move selected public instances into neither
                                  # (frozen; reruns only check deterministic reproduction)

The deterministic split assigns 70% public practice
and 30% hidden judging by family × size. This task's implementation:
  - Families: Early (15) / Middle (15) / Late (15) / Test (8), the four official
    ITC2021 groups.
  - Size: number of teams (count of <team> elements), divided at the median within
    each family.
  - Hidden quota: allocate 16 slots by the largest-remainder method proportional to
    family size (floor first, then descending fractional remainder, ties by family
    name descending): Early 15/53×16=4.53→4, Middle 5, Late 5, Test 2. Then allocate
    within each size tier by the same method.
  - Use a fixed seed to sample within each of eight tiers:
      seed = int.from_bytes(sha256("tcshard-form2-split-itc2021-sports-timetabling-260920")
             .digest()[:8], "big")
    A single random.Random(seed) samples Early small/large, Middle small/large, Late
    small/large, then Test small/large; sort each tier by (teams, instance name).

Unscored-instance rule: the scored set is close to the publicly registered set (all 53 official
ITC2021 instances), so hidden identities can be identified exactly by "official full
set minus public environment set." Move 8 additional public instances into neither
(not included in the environment or scored), the upper end of 10–15% of 53. Allocate
family quotas by the largest-remainder method based on public members: Early
8×11/37=2.38→3, Middle 8×10/37=2.16→2, Late 2, Test 8×6/37=1.30→1. Within each
family, allocate by public tier size the same way (Early small 1 / Early large 2;
other families 1/1; Test large 1). Leave the hidden bucket unchanged. Seed:
      seed = int.from_bytes(sha256("tcshard-form2-neither-itc2021-sports-timetabling-260920")
             .digest()[:8], "big")
    A single random.Random(seed) samples the eight tiers in the original order.

Output: tests/split.json maps instance names to "public"/"hidden"/"neither". Once
merged, the split is frozen and is not adjusted based on experimental results."""
import hashlib
import json
import os
import random
import re
import sys

SEED_PREFIX = "tcshard-form2-split-itc2021-sports-timetabling-260920"
NEITHER_SEED_PREFIX = "tcshard-form2-neither-itc2021-sports-timetabling-260920"

TESTS = os.path.dirname(os.path.abspath(__file__))
LIBRARY = os.path.join(TESTS, "instances-library")
N_HIDDEN = 16
N_NEITHER = 8
FAMILIES = ("Early", "Middle", "Late", "Test")


def n_teams(path):
    with open(path, errors="replace") as f:
        return len(re.findall(r"<team\b", f.read()))


def family_of(fn):
    for fam in ("Early", "Middle", "Late"):
        if fn.startswith(f"ITC2021_{fam}_"):
            return fam
    return "Test"


def largest_remainder(quota_map, total):
    floors = {k: int(v) for k, v in quota_map.items()}
    rest = total - sum(floors.values())
    by_rem = sorted(quota_map, key=lambda k: (quota_map[k] - floors[k], k),
                    reverse=True)
    for k in by_rem[:rest]:
        floors[k] += 1
    return floors


def tiers_of(fam):
    """The two size tiers within each family (sort each tier by (teams, instance name))."""
    names = sorted(f for f in os.listdir(LIBRARY)
                   if f.endswith(".xml") and family_of(f) == fam)
    members = sorted((n_teams(os.path.join(LIBRARY, fn)), fn)
                     for fn in names)
    half = len(members) // 2
    return [(f"{fam}-small", [fn for _, fn in members[:half]]),
            (f"{fam}-large", [fn for _, fn in members[half:]])]


def write_split(out):
    path = os.path.join(TESTS, "split.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)
        f.write("\n")
    os.chmod(path, 0o644)


def cmd_split():
    names = sorted(f for f in os.listdir(LIBRARY) if f.endswith(".xml"))
    if len(names) != 53:
        raise SystemExit(f"expected the 53 official instances, got {len(names)}")
    fam_quota = {fam: sum(1 for fn in names if family_of(fn) == fam)
                 / len(names) * N_HIDDEN for fam in FAMILIES}
    fam_hidden = largest_remainder(fam_quota, N_HIDDEN)
    seed = int.from_bytes(hashlib.sha256(SEED_PREFIX.encode()).digest()[:8],
                          "big")
    rng = random.Random(seed)
    split = {}
    table = []
    for fam in FAMILIES:
        fam_tiers = tiers_of(fam)
        members = [fn for _, ms in fam_tiers for fn in ms]
        tier_quota = {ti: fam_hidden[fam] * len(fam_tiers[ti][1]) / len(members)
                      for ti in range(2)}
        tier_hidden = largest_remainder(tier_quota, fam_hidden[fam])
        for ti, (label, ms) in enumerate(fam_tiers):
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
    print(f"seed={seed}  public={53 - n_h} hidden={n_h}")
    for label, size, k, picked in table:
        print(f"  stratum {label:14s} size={size} hidden={k}: {picked}")


def cmd_dilute():
    path = os.path.join(TESTS, "split.json")
    with open(path) as f:
        split = json.load(f)
    seed = int.from_bytes(hashlib.sha256(NEITHER_SEED_PREFIX.encode())
                          .digest()[:8], "big")
    rng = random.Random(seed)
    n_pub = {fam: sum(1 for fn, v in split.items()
                      if v == "public" and family_of(fn) == fam)
             for fam in FAMILIES}
    fam_neither = largest_remainder(
        {fam: N_NEITHER * n / sum(n_pub.values())
         for fam, n in n_pub.items()}, N_NEITHER)
    picked_all = {}
    table = []
    for fam in FAMILIES:
        fam_tiers = tiers_of(fam)
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
        print(f"  stratum {label:14s} public={size} neither={k}: {picked}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "dilute":
        cmd_dilute()
    else:
        cmd_split()
