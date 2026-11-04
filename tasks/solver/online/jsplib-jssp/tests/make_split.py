#!/usr/bin/env python3
"""One-time, frozen form2 split generator for jsplib-jssp (70% public practice / 30% hidden judging, 2026-09-20).

Deterministically split 283 instances (252 classic and 31 generated) into public
and hidden sets, grouped by family × size, and write tests/split.json. Once merged,
the split is frozen and is not adjusted based on experimental results.

Rules (fully deterministic, no random source):
  1. Families: ft/la/abz/orb/swv/yn/ta/dmu (classic, determined by name prefix),
     tai (tai_10_10_*), and gta/gdmu (generated for this task, Taillard-style /
     Demirkol-style).
  2. Size = (n, m) (number of jobs × number of machines, parsed from the "n x m"
     size field in tests/reference.json); sort each family by (n, m, name).
  3. Target hidden count is round(283 × 0.3) = 85. Allocate quotas across families
     with Hamilton's largest-remainder method (start with floor, then add slots by
     descending fractional remainder; ties: larger family first, then family name
     lexicographically).
  4. Within each family, choose hidden instances at evenly spaced positions in the
     sorted list: floor((i + 0.5) × size / quota), i = 0..quota-1. This spreads the
     sample evenly along the size axis.
  5. Put all remaining instances in the public set. The scored form of each hidden
     instance is its structure-preserving transformed copy (tests/transform.py,
     using the existing async-lineage codename-map assignments).

Run with `python3 tests/make_split.py` from the task root or any directory. Read the
283 keys in tests/reference.json before splitting, write tests/split.json, and print
the stratification table. Do not rerun after the split is frozen: reference will
have hidden keys removed and the script will stop on the key-count mismatch."""
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(HERE)
REFERENCE = os.path.join(HERE, "reference.json")
OUT = os.path.join(HERE, "split.json")

TOTAL = 283
HIDDEN_TARGET = round(TOTAL * 0.3)  # 85


def family_of(name):
    if name.startswith("tai_10_10"):
        return "tai"
    if name.startswith("gdmu"):
        return "gdmu"
    if name.startswith("gta"):
        return "gta"
    if name.startswith("dmu"):
        return "dmu"
    if name.startswith("ta"):
        return "ta"
    m = re.match(r"^[a-z]+", name)
    if not m:
        raise ValueError(f"cannot parse family: {name}")
    return m.group(0)


def parse_size(s):
    m = re.match(r"^(\d+)\s*x\s*(\d+)$", s)
    if not m:
        raise ValueError(f"cannot parse size: {s!r}")
    return int(m.group(1)), int(m.group(2))


def main():
    with open(REFERENCE) as f:
        ref = json.load(f)["instances"]
    if len(ref) != TOTAL:
        sys.exit(f"[make_split] reference key count {len(ref)} != {TOTAL}; this script is only for use"
                 "before splitting (with the full set); do not rerun after the split is frozen")
    fams = {}
    for name, ent in ref.items():
        fams.setdefault(family_of(name), []).append((parse_size(ent["size"]), name))
    sizes = {fam: sorted(mems) for fam, mems in fams.items()}
    quota = {fam: int(0.3 * len(m)) for fam, m in sizes.items()}
    remain = HIDDEN_TARGET - sum(quota.values())
    fracs = sorted(sizes,
                   key=lambda f: (-(0.3 * len(sizes[f]) % 1),
                                  -len(sizes[f]), f))
    for fam in fracs[:remain]:
        quota[fam] += 1
    split = {}
    rows = []
    for fam in sorted(sizes):
        ordered = [nm for _, nm in sizes[fam]]
        q = quota[fam]
        picks = {ordered[math.floor((i + 0.5) * len(ordered) / q)]
                 for i in range(q)} if q else set()
        if len(picks) != q:
            for nm in ordered:
                if len(picks) == q:
                    break
                picks.add(nm)
        rows.append((fam, len(ordered), q, sorted(picks)))
        for nm in ordered:
            n, m = parse_size(ref[nm]["size"])
            split[nm] = {"side": "hidden" if nm in picks else "public",
                         "family": fam, "n": n, "m": m}
    n_hidden = sum(1 for e in split.values() if e["side"] == "hidden")
    assert n_hidden == HIDDEN_TARGET, (n_hidden, HIDDEN_TARGET)
    doc = {
        "rule": {
            "frozen": "2026-09-20",
            "total": TOTAL,
            "hidden_target": HIDDEN_TARGET,
            "stratification": "family (name prefix; tai/gta/gdmu special-cased) x "
                              "size (jobs n x machines m); deterministic Hamilton "
                              "apportionment for per-family hidden quota; evenly "
                              "spaced picks by size within family",
            "generator": "tests/make_split.py",
        },
        "instances": {nm: split[nm] for nm in sorted(split)},
    }
    with open(OUT, "w") as f:
        json.dump(doc, f, indent=1, sort_keys=False)
        f.write("\n")
    print(f"{'family':8s} {'size':>4s} {'hidden':>6s}  picks")
    for fam, size, q, picks in rows:
        print(f"{fam:8s} {size:4d} {q:6d}  {', '.join(picks) if picks else '-'}")
    print(f"total {TOTAL} -> public {TOTAL - n_hidden} / hidden {n_hidden}")
    print(f"written: {OUT}")


if __name__ == "__main__":
    main()
