#!/usr/bin/env python3
"""Structure-preserving form2 transformation for itc2021-sports-timetabling (tests-side utility for the 30% hidden scored instances).

For each instance marked hidden in split.json, apply an exact isomorphism by
permuting team IDs pi: old 0..n-1 → new 0..n-1. Rewrite <team id name>, remap
each item in the semicolon-separated teams/teams1/teams2 lists, and remap both
members of every comma-separated GA1 meetings pair. Replace <InstanceName> with a
neutral token (the original name is a public fingerprint). **Leave rounds, dates,
slots, league, penalty, and all other bytes unchanged.** The constraint set is the
same under team relabeling, so every schedule has exactly the same soft penalty;
reuse K by isomorphism.

Write transformed instances to new names h01.xml, etc., numbered by sorted
official name. Store the original-to-transformed mapping and permutation table only
in tests/transform_manifest.json (under tests/, outside the environment and the
model-readable /tests layer of the scoring image).

Deterministic per-instance seed:
    seed = int.from_bytes(sha256("tcshard-form2-itc2021-260920:" + stem)
           .digest()[:8], "big")
    rng = random.Random(seed)
stem is the official filename without extension (for example,
"ITC2021_Middle_5"). The same seed reproduces identical transformed bytes.

Subcommands:
  apply              Batch-transform hidden instances from split.json: read the
                     official source bytes in tests/instances-library/ and write
                     tests/instances/hNN.xml plus tests/transform_manifest.json.
  invert             Independently invert each transformed instance using the
                     manifest (restoring InstanceName) and compare bytes with the
                     official source.
  rewrite-solutions  Rewrite stored schedules (home/away in ScheduledMatch under
                     <Solution>) using the manifest team permutation for the oracle
                     stub, then rebuild the lookup manifest for transformed
                     instances.

Standard library only."""
import argparse
import hashlib
import json
import os
import random
import re
import sys

TRANSFORM_ID = "itc2021-team-relabel-form2-v1"
SEED_PREFIX = "tcshard-form2-itc2021-260920:"
SEED_RULE = (
    'seed = int.from_bytes(sha256("tcshard-form2-itc2021-260920:" + stem)'
    '.digest()[:8], "big"); rng = random.Random(seed); one shuffle of the'
    " team-id list 0..n-1; transformed file name hNN assigned in sorted"
    " official-name order"
)

TEAM_RE = re.compile(r"<team\b[^>]*/>")
TEAMREF_RE = re.compile(r'\b(teams|teams1|teams2)="([^"]*)"')
MEETINGS_RE = re.compile(r'\bmeetings="([^"]*)"')
INAME_RE = re.compile(r"<InstanceName>[^<]*</InstanceName>")
ATTR_RE = re.compile(r'(\w+)="([^"]*)"')
HOME_RE = re.compile(r'\bhome="(\d+)"')
AWAY_RE = re.compile(r'\baway="(\d+)"')
TEAMID_RE = re.compile(r'<team\b[^>]*\bid="(\d+)"')

TESTS = os.path.dirname(os.path.abspath(__file__))


def derive_seed(stem):
    h = hashlib.sha256((SEED_PREFIX + stem).encode()).digest()
    return int.from_bytes(h[:8], "big")


def oracle_hash(path):
    """Lookup key for the oracle stub: SHA-256 of the original instance-file bytes."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def remap_idlist(value, pi):
    if not value:
        return value
    return ";".join(str(pi[int(t)]) for t in value.split(";") if t != "") \
        + (";" if value.endswith(";") else "")


def remap_meetings(value, pi):
    out = []
    for pair in value.split(";"):
        if not pair:
            continue
        a, b = pair.split(",")
        out.append(f"{pi[int(a)]},{pi[int(b)]};")
    return "".join(out)


def transform_text(text, pi, neutral_name):
    def fix_team(m):
        attrs = dict(ATTR_RE.findall(m.group(0)))
        old = int(attrs["id"])
        attrs["id"] = str(pi[old])
        if "name" in attrs:
            attrs["name"] = f"Team {pi[old]}"
        return "<team " + " ".join(f'{k}="{v}"' for k, v in attrs.items()) \
            + "/>"

    out = TEAM_RE.sub(fix_team, text)
    out = TEAMREF_RE.sub(
        lambda m: f'{m.group(1)}="{remap_idlist(m.group(2), pi)}"', out)
    out = MEETINGS_RE.sub(
        lambda m: f'meetings="{remap_meetings(m.group(1), pi)}"', out)
    out = INAME_RE.sub(f"<InstanceName>{neutral_name}</InstanceName>", out,
                       count=1)
    return out


def invert_text(text, pi, orig_iname):
    inv = {new: old for old, new in enumerate(pi)}
    return transform_text(text, inv, orig_iname)


def hidden_stems_sorted():
    with open(os.path.join(TESTS, "split.json")) as f:
        split = json.load(f)
    return sorted(fn[:-len(".xml")] for fn, side in split.items()
                  if side == "hidden")


def cmd_apply(args):
    os.makedirs(args.out_dir, exist_ok=True)
    stems = hidden_stems_sorted()
    manifest = {
        "transform": TRANSFORM_ID,
        "operations": ["permute-team-ids", "neutralize-InstanceName"],
        "rounds_dates": "untouched (calendar semantics)",
        "seed_rule": SEED_RULE,
        "instances": {},
    }
    for i, stem in enumerate(stems, 1):
        new_name = f"h{i:02d}"
        src = os.path.join(args.instances_dir, stem + ".xml")
        with open(src) as f:
            text = f.read()
        ids = sorted(int(m) for m in TEAMID_RE.findall(text))
        n = len(ids)
        if ids != list(range(n)):
            sys.exit(f"{stem}: team ids not 0..n-1")
        rng = random.Random(derive_seed(stem))
        perm = list(range(n))
        rng.shuffle(perm)
        iname_m = INAME_RE.search(text)
        orig_iname = iname_m.group(0)[len("<InstanceName>"):-len("</InstanceName>")] \
            if iname_m else stem
        neutral = f"Instance-{derive_seed(stem):016x}"[:18]
        new_text = transform_text(text, perm, neutral)
        dst = os.path.join(args.out_dir, new_name + ".xml")
        with open(dst, "w") as f:
            f.write(new_text)
        os.chmod(dst, 0o644)
        manifest["instances"][new_name] = {
            "official": stem,
            "orig_instance_name": orig_iname,
            "neutral_instance_name": neutral,
            "n_teams": n,
            "seed": derive_seed(stem),
            "perm": perm,
            "src_sha256": oracle_hash(src),
            "out_sha256": oracle_hash(dst),
        }
        print(f"[apply] {stem} -> {new_name}.xml ({n} teams)", flush=True)
    with open(args.manifest, "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
        f.write("\n")
    os.chmod(args.manifest, 0o644)
    print(f"[apply] manifest: {args.manifest} "
          f"({len(manifest['instances'])} instances)")


def cmd_invert(args):
    with open(args.manifest) as f:
        manifest = json.load(f)
    n_ok = n_bad = 0
    for new_name, rec in sorted(manifest["instances"].items()):
        stem = rec["official"]
        with open(os.path.join(args.trans_dir, new_name + ".xml")) as f:
            text_t = f.read()
        restored = invert_text(text_t, rec["perm"],
                               rec["orig_instance_name"])
        with open(os.path.join(args.orig_dir, stem + ".xml")) as f:
            orig = f.read()
        if restored == orig:
            n_ok += 1
            print(f"[invert] {new_name} ({stem}): ok")
        else:
            n_bad += 1
            print(f"[invert] {new_name} ({stem}): FAIL restored != original")
    print(f"[invert] ok={n_ok} bad={n_bad}")
    return 1 if n_bad else 0


def cmd_rewrite_solutions(args):
    """Rewrite prerecorded schedules (<Solution> XML) with the manifest's
    team permutation; rebuild the oracle lookup manifest against the
    transformed instances."""
    with open(args.manifest) as f:
        manifest = json.load(f)["instances"]
    os.makedirs(args.out_dir, exist_ok=True)
    out_manifest = {}
    n_sol = 0
    for new_name, rec in sorted(manifest.items()):
        stem = rec["official"]
        src_sol = os.path.join(args.sol_dir, stem + ".xml")
        if not os.path.exists(src_sol):
            print(f"[rewrite-solutions] {stem}: no prerecorded solution, "
                  f"skipped")
            continue
        with open(src_sol) as f:
            text = f.read()
        pi = rec["perm"]
        text = HOME_RE.sub(lambda m: f'home="{pi[int(m.group(1))]}"', text)
        text = AWAY_RE.sub(lambda m: f'away="{pi[int(m.group(1))]}"', text)
        text = INAME_RE.sub(
            f"<InstanceName>{rec['neutral_instance_name']}</InstanceName>",
            text, count=1)
        dst = os.path.join(args.out_dir, new_name + ".xml")
        with open(dst, "w") as f:
            f.write(text)
        key = oracle_hash(os.path.join(args.instances_dir,
                                       new_name + ".xml"))
        if key != rec["out_sha256"]:
            sys.exit(f"[rewrite-solutions] {new_name}: instance key mismatch "
                     f"with manifest ({key} != {rec['out_sha256']})")
        out_manifest[key] = {"file": new_name + ".xml", "instance": new_name}
        n_sol += 1
    with open(os.path.join(args.out_dir, "manifest-hidden.json"), "w") as f:
        json.dump(out_manifest, f, indent=0, sort_keys=True)
        f.write("\n")
    print(f"[rewrite-solutions] {n_sol} solutions rewritten -> {args.out_dir}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("apply")
    p.add_argument("--instances-dir", default=os.path.join(
        TESTS, "instances-library"))
    p.add_argument("--out-dir", default=os.path.join(TESTS, "instances"))
    p.add_argument("--manifest", default=os.path.join(
        TESTS, "transform_manifest.json"))
    p.set_defaults(fn=cmd_apply)
    p = sub.add_parser("invert")
    p.add_argument("--orig-dir", default=os.path.join(TESTS,
                                                      "instances-library"))
    p.add_argument("--trans-dir", default=os.path.join(TESTS, "instances"))
    p.add_argument("--manifest", default=os.path.join(
        TESTS, "transform_manifest.json"))
    p.set_defaults(fn=cmd_invert)
    p = sub.add_parser("rewrite-solutions")
    p.add_argument("--instances-dir", default=os.path.join(TESTS, "instances"),
                   help="directory with the TRANSFORMED instances")
    p.add_argument("--sol-dir", required=True,
                   help="directory with the original prerecorded solutions")
    p.add_argument("--manifest", default=os.path.join(
        TESTS, "transform_manifest.json"))
    p.add_argument("--out-dir", required=True)
    p.set_defaults(fn=cmd_rewrite_solutions)
    args = ap.parse_args()
    sys.exit(args.fn(args) or 0)


if __name__ == "__main__":
    main()
