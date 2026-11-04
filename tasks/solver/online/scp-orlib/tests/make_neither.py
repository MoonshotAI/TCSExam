#!/usr/bin/env python3
"""Deterministic generator for the scp-orlib form2 neither (“in neither set”) dilution.

Move about 15% of the public bucket, stratified by family × size, into the neither
set (not included in the environment and not scored) to increase the cost of
recognition and replay. Selection is deterministic with a fixed recorded seed. Leave
the hidden bucket unchanged.

Rules (dilution section of form2-conversion-recipes.md):
  1. Target neither count = round(87 × 0.149) = 13 (about 15%, at the upper end
     of the 10–15% range).
  2. Allocate neither quotas across families based on 15% of each public family's
     size, using Hamilton's largest-remainder method (ties: larger family first,
     then family name lexicographically).
  3. Within each family, sort members by (n, name), then sample with a seeded RNG:
     seed = int.from_bytes(
         sha256("tcshard-form2-neither-scp-orlib-260920")[:8], "big")
     Use one RNG stream and call rng.sample in lexicographic family order so the
     draw order is deterministic.
  4. split.json is a flat mapping {instance_name: "public"/"hidden"/"neither"}
     (one supported schema form). Store the neither list only in tests/split.json;
     leaking it invalidates the dilution. Do not put it in the environment, task
     statement, or instance-level list in PROVENANCE.

Run with `python3 tests/make_neither.py` from the task root or any directory. Read
tests/split.json (the original 61/26 split, in any supported form) and
 tests/reference.json (authoritative family=group and size=n fields), write the flat
mapping with the neither bucket added, and print the family-level stratification
table without instance names."""
import hashlib
import json
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(HERE)
SPLIT_PATH = os.path.join(HERE, "split.json")

TOTAL = 87
NEITHER_TARGET = 13
SEED_STR = "tcshard-form2-neither-scp-orlib-260920"


def load_split():
    with open(SPLIT_PATH) as f:
        doc = json.load(f)
    if "instances" in doc:
        return {n: e["side"] for n, e in doc["instances"].items()}
    if all(isinstance(v, list) for v in doc.values()):
        return {n: side for side, names in doc.items() for n in names}
    return doc


def load_reference_129():
    """Family/size metadata for all 87 official keys: after splitting, reference.json retains only 26 hidden keys,
    so read group/n for the 61 public keys from the pre-split reference in Git history (read-only; do not alter history)."""
    out = subprocess.run(
        ["git", "show", "HEAD:tasks/scp-orlib/tests/reference.json"],
        capture_output=True, text=True, cwd=TASK)
    if out.returncode != 0:
        sys.exit("[make_neither] the pre-split reference.json (129 keys) from Git history is required")
    ref = json.loads(out.stdout)["instances"]
    if len(ref) == TOTAL:
        return ref
    # The split is on disk: hidden keys are in repository reference.json; public keys are in environment public_reference.json
    full = dict(ref)
    with open(os.path.join(TASK, "environment", "app",
                           "public_reference.json")) as f:
        full.update(json.load(f)["instances"])
    return full


def main():
    side = load_split()
    if len(side) != TOTAL or any(v == "neither" for v in side.values()):
        sys.exit("[make_neither] split.json is not the pre-dilution two-bucket split with 87 keys; stop")
    public = sorted(n for n, s in side.items() if s == "public")
    hidden = sorted(n for n, s in side.items() if s == "hidden")
    assert (len(public), len(hidden)) == (61, 26)
    ref = load_reference_129()
    fams = {}
    for name in public:
        fams.setdefault(ref[name]["group"], []).append(name)
    quota = {fam: int(0.149 * len(m)) for fam, m in fams.items()}
    remain = NEITHER_TARGET - sum(quota.values())
    fracs = sorted(fams, key=lambda f: (-(0.149 * len(fams[f]) % 1),
                                        -len(fams[f]), f))
    for fam in fracs[:remain]:
        quota[fam] += 1
    rng = random.Random(int.from_bytes(
        hashlib.sha256(SEED_STR.encode()).digest()[:8], "big"))
    neither = set()
    rows = []
    for fam in sorted(fams):
        ordered = sorted(fams[fam], key=lambda nm: (ref[nm]["n"], nm))
        q = quota[fam]
        picks = set(rng.sample(ordered, q)) if q else set()
        neither |= picks
        rows.append((fam, len(ordered), q))
    assert len(neither) == NEITHER_TARGET
    for n in neither:
        side[n] = "neither"
    with open(SPLIT_PATH, "w") as f:
        json.dump({n: side[n] for n in sorted(side)}, f, indent=1,
                  sort_keys=False)
        f.write("\n")
    print(f"{'family':8s} {'public':>6s} {'neither':>7s}")
    for fam, size, q in rows:
        print(f"{fam:8s} {size:6d} {q:7d}")
    print(f"neither total {len(neither)} / public {len(public)} -> "
          f"{len(public) - len(neither)}; hidden {len(hidden)} untouched")
    print(f"seed: sha256({SEED_STR!r})[:8]; written: {SPLIT_PATH}")


if __name__ == "__main__":
    main()
