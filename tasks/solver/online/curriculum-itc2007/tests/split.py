#!/usr/bin/env python3
"""One-time, frozen form2 70/30 split generator for curriculum-itc2007, with the 260920 dilution.

Usage:
  python3 tests/split.py          # Initial 70/30 split (frozen; reruns only check
                                  # deterministic reproduction)
  python3 tests/split.py dilute   # Move selected public instances into neither
                                  # (frozen; reruns only check deterministic reproduction)

The deterministic split assigns 70% public practice
and 30% hidden judging by family × size. This task's implementation:
  - Family: all 21 instances belong to one ITC 2007 Track 3 family (comp01–comp21),
    so only size is available for stratification.
  - Size: number of courses (Courses header field), split into three sorted tiers of
    7 instances each.
  - Hidden quota: 2 per tier, 6 total (21×0.3=6.3→6; 15 public).
  - Use a fixed seed to sample within each tier:
      seed = int.from_bytes(sha256("tcshard-form2-split-curriculum-itc2007-260920")
             .digest()[:8], "big")
    A single random.Random(seed) samples each of the three tiers (small/medium/large),
    sorted within tier by (Courses, instance name).

Unscored-instance rule: the scored set is close to the publicly registered set (all 21 official
ITC 2007 Track 3 instances), so the hidden identities can be identified exactly by
"official full set minus public environment set." Move 3 more instances from the
public bucket into neither (not included in the environment or scored); this is the
upper end of 10–15% of 21. Reuse the three original tiers and select 1 from each;
leave the hidden bucket unchanged. Seed:
      seed = int.from_bytes(sha256("tcshard-form2-neither-curriculum-itc2007-260920")
             .digest()[:8], "big")
    A single random.Random(seed) samples each tier in the original order.

Output: tests/split.json maps instance names to "public"/"hidden"/"neither". Once
merged, the split is frozen and is not adjusted based on experimental results."""
import hashlib
import json
import os
import random
import sys

SEED_PREFIX = "tcshard-form2-split-curriculum-itc2007-260920"
NEITHER_SEED_PREFIX = "tcshard-form2-neither-curriculum-itc2007-260920"

TESTS = os.path.dirname(os.path.abspath(__file__))
LIBRARY = os.path.join(TESTS, "instances-library")
N_HIDDEN = 6
N_NEITHER = 3


def course_count(path):
    with open(path, errors="replace") as f:
        for line in f:
            if line.startswith("Courses:"):
                return int(line.split(":")[1].strip())
    raise ValueError(f"Courses header not found in {path}")


def tiers():
    """The three size tiers in the original split (21 total; sort each tier by (Courses, instance name))."""
    names = sorted(f for f in os.listdir(LIBRARY) if f.endswith(".ctt"))
    if len(names) != 21:
        raise SystemExit(f"expected the 21 official instances, got {len(names)}")
    members = sorted((course_count(os.path.join(LIBRARY, fn)), fn)
                     for fn in names)
    return [("small", [fn for _, fn in members[0:7]]),
            ("medium", [fn for _, fn in members[7:14]]),
            ("large", [fn for _, fn in members[14:21]])]


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
    for label, ms in tiers():
        picked = set(rng.sample(ms, 2))
        for fn in ms:
            split[fn] = "hidden" if fn in picked else "public"
        table.append((label, len(ms), sorted(picked)))
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
    print(f"seed={seed}  public={21 - n_h} hidden={n_h}")
    for label, size, picked in table:
        print(f"  stratum {label:7s} size={size} hidden=2: {picked}")


def cmd_dilute():
    path = os.path.join(TESTS, "split.json")
    with open(path) as f:
        split = json.load(f)
    seed = int.from_bytes(hashlib.sha256(NEITHER_SEED_PREFIX.encode())
                          .digest()[:8], "big")
    rng = random.Random(seed)
    picked_all = {}
    table = []
    for label, ms in tiers():
        public_ms = [fn for fn in ms if split[fn] == "public"]
        picked = set(rng.sample(public_ms, 1))
        for fn in picked:
            picked_all[fn] = "neither"
        table.append((label, len(public_ms), sorted(picked)))
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
    for label, size, picked in table:
        print(f"  stratum {label:7s} public={size} neither=1: {picked}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "dilute":
        cmd_dilute()
    else:
        cmd_split()
