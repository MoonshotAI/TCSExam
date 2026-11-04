#!/usr/bin/env python3
"""One-time, frozen form2 split generator for qap-qaplib (70% public practice / 30% hidden judging, 2026-09-20).

Deterministically split all 136 official-library instances into public and hidden
sets, grouped by family × size, and write tests/split.json. Once merged, the split
is frozen and is not adjusted based on experimental results.

Rules (fully deterministic, no random source):
  1. Family is the letter prefix of the instance name (bur/chr/els/esc/had/kra/lipa/
     nug/rou/scr/sko/ste/tai/tho/wil, the QAPLIB naming groups); size is n in the
     first line of the instance file.
  2. Sort each family by (n, name); target hidden count is round(136 × 0.3) = 41.
  3. Allocate hidden quotas across families with Hamilton's largest-remainder method:
     begin with floor(0.3 × family size), then allocate the remaining slots in order
     of descending fractional remainder (ties: larger family first, then family name
     lexicographically).
  4. Within each family, choose hidden instances at evenly spaced positions in the
     sorted list: floor((i + 0.5) × size / quota), i = 0..quota-1. This spreads the
     sample evenly along the size axis rather than favoring either end.
  5. Put all remaining instances in the public set. The scored form of each hidden
     instance is its structure-preserving transformed copy (tests/transform.py,
     using the existing codename-map assignments).
  6. (Added after the 260920 dilution batch.) From the public set, move about 15%
     into a neither set with tests/make_neither.py (not included in the environment
     and not scored); record the list only in split.json.

Run with `python3 tests/make_split.py` from the task root or any directory. Read the
136 official instances under environment/app/instances and their first-line n,
write tests/split.json, and print the stratification table."""
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(HERE)
ENV_INSTANCES = os.path.join(TASK, "environment", "app", "instances")
OUT = os.path.join(HERE, "split.json")

TOTAL = 136
HIDDEN_TARGET = round(TOTAL * 0.3)  # 41


def family_of(name):
    m = re.match(r"^([a-z]+)", name)
    if not m:
        raise ValueError(f"cannot parse family: {name}")
    return m.group(1)


def read_n(path):
    with open(path) as f:
        return int(f.read().split()[0])


def main():
    names = sorted(f for f in os.listdir(ENV_INSTANCES) if f.endswith(".dat"))
    if len(names) != TOTAL:
        sys.exit(f"[make_split] environment instance count {len(names)} != {TOTAL}; this script is only for use"
                 "before splitting (when the environment contains the full official library); do not rerun after the split is frozen")
    fams = {}
    for name in names:
        fams.setdefault(family_of(name), []).append(name)
    sizes = {fam: sorted(((read_n(os.path.join(ENV_INSTANCES, nm)), nm)
                          for nm in members))
             for fam, members in fams.items()}
    # Hamilton largest-remainder method
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
        if len(picks) != q:  # evenly spaced positions collided (when quota is close to size); fill by shifting positions to the right in order
            for nm in ordered:
                if len(picks) == q:
                    break
                picks.add(nm)
        rows.append((fam, len(ordered), q, sorted(picks)))
        for nm in ordered:
            split[nm] = {"side": "hidden" if nm in picks else "public",
                         "family": fam,
                         "n": dict((nm_, nn) for nn, nm_ in sizes[fam])[nm]}
    n_hidden = sum(1 for e in split.values() if e["side"] == "hidden")
    assert n_hidden == HIDDEN_TARGET, (n_hidden, HIDDEN_TARGET)
    # split.json format: flat mapping {instance_name: "public"/"hidden"/"neither"} (one supported schema
    # form; this script writes only two buckets, and tests/make_neither.py adds neither later)
    with open(OUT, "w") as f:
        json.dump({nm: split[nm]["side"] for nm in sorted(split)}, f,
                  indent=1, sort_keys=False)
        f.write("\n")
    print(f"{'family':8s} {'size':>4s} {'hidden':>6s}  picks")
    for fam, size, q, picks in rows:
        print(f"{fam:8s} {size:4d} {q:6d}  {', '.join(picks) if picks else '-'}")
    print(f"total {TOTAL} -> public {TOTAL - n_hidden} / hidden {n_hidden}")
    print(f"written: {OUT}")


if __name__ == "__main__":
    main()
