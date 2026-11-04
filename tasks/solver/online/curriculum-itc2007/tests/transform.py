#!/usr/bin/env python3
"""Structure-preserving form2 transformation for curriculum-itc2007 (tests-side utility for the 30% hidden scored instances).

For every instance marked hidden in split.json, permute identifiers independently
within the four classes: courses, rooms, teachers, and curricula (reassign the same
multiset of strings within each class). Relabel all references in CURRICULA member
lists and UNAVAILABILITY_CONSTRAINTS course fields. **Leave days and periods
unchanged**, because availability and cycle structure have calendar meaning. The
official cost (RoomCapacity + 5×MinWorkingDays + 2×CurriculumCompactness +
RoomStability) and four hard constraints depend only on course attributes,
course-to-curriculum membership, shared teachers, and room capacity—not identifier
strings. Every timetable therefore keeps exactly the same objective value, so reuse
K by isomorphism.

To remove memorized fingerprints, replace the Name header with a neutral constant,
reorder rows in each section by the new identifiers, and emit canonical layout.
Write transformed instances to new names h01.ctt, etc., numbered by sorted official
name. Store the original-to-transformed mapping and four permutation tables only in
tests/transform_manifest.json (under tests/, outside the environment and the
model-readable /tests layer of the scoring image).

Deterministic per-instance seed:
    seed = int.from_bytes(sha256("tcshard-form2-curriculum-260920:" + stem)
           .digest()[:8], "big")
    rng = random.Random(seed)
stem is the official filename without extension (for example, "comp05"). Consume
the RNG by shuffling each ordered identifier list once, in this order: courses,
rooms, teachers, curricula. The same seed reproduces identical transformed bytes.

Subcommands:
  apply              Batch-transform hidden instances from split.json: read the
                     official bytes in tests/instances-library/ and write
                     tests/instances/hNN.ctt plus tests/transform_manifest.json.
  invert             Independently invert each transformed instance using the
                     manifest permutations, restore identifier labels and Name
                     header, then compare canonical bytes with the original.
  rewrite-solutions  Rewrite stored schedules (*.sol rows of
                     "<CourseID> <RoomID> <Day> <Period>") using the manifest course
                     and room permutations for the oracle stub, then rebuild the
                     lookup manifest for transformed instances.

Standard library only."""
import argparse
import hashlib
import json
import os
import random
import sys

TRANSFORM_ID = "ctt-relabeling-form2-v1"
SEED_PREFIX = "tcshard-form2-curriculum-260920:"
SEED_RULE = (
    'seed = int.from_bytes(sha256("tcshard-form2-curriculum-260920:" + stem)'
    '.digest()[:8], "big"); rng = random.Random(seed); consumption order:'
    " sorted-label shuffles of courses, rooms, teachers, curricula"
    " (labels permuted within class); transformed file name hNN assigned in"
    " sorted official-name order"
)
NEUTRAL_NAME = "instance"
HEADER_KEYS = ("Name", "Courses", "Rooms", "Days", "Periods_per_day",
               "Curricula", "Constraints")
TESTS = os.path.dirname(os.path.abspath(__file__))


def derive_seed(stem):
    h = hashlib.sha256((SEED_PREFIX + stem).encode()).digest()
    return int.from_bytes(h[:8], "big")


def oracle_hash(plain_bytes):
    """Lookup key for the oracle stub: SHA-256 of the whitespace-normalized token stream."""
    return hashlib.sha256(b" ".join(plain_bytes.split())).hexdigest()


def load_ctt(path):
    """Parse a .ctt instance. Returns a dict with header + sections."""
    inst = {"header": {}, "courses": [], "rooms": [], "curricula": [],
            "unavail": []}
    section = None
    with open(path, errors="replace") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            if line == "COURSES:":
                section = "courses"
                continue
            if line == "ROOMS:":
                section = "rooms"
                continue
            if line == "CURRICULA:":
                section = "curricula"
                continue
            if line == "UNAVAILABILITY_CONSTRAINTS:":
                section = "unavail"
                continue
            if line == "END.":
                break
            if section is None:
                k, _, v = line.partition(":")
                if k.strip() in HEADER_KEYS:
                    inst["header"][k.strip()] = v.strip()
                continue
            parts = line.split()
            if section == "courses":
                if len(parts) != 5:
                    raise ValueError(f"{path}: bad COURSES line: {line!r}")
                inst["courses"].append(parts)
            elif section == "rooms":
                if len(parts) != 2:
                    raise ValueError(f"{path}: bad ROOMS line: {line!r}")
                inst["rooms"].append(parts)
            elif section == "curricula":
                if len(parts) < 2 or int(parts[1]) != len(parts) - 2:
                    raise ValueError(f"{path}: bad CURRICULA line: {line!r}")
                inst["curricula"].append(parts)
            else:
                if len(parts) != 3:
                    raise ValueError(f"{path}: bad UNAVAILABILITY line: "
                                     f"{line!r}")
                inst["unavail"].append(parts)
    h = inst["header"]
    for k, sec in {"Courses": "courses", "Rooms": "rooms",
                   "Curricula": "curricula", "Constraints": "unavail"}.items():
        if k in h and int(h[k]) != len(inst[sec]):
            raise ValueError(f"{path}: header {k}={h[k]} but "
                             f"{len(inst[sec])} lines")
    return inst


def emit(inst):
    """Re-emit canonical layout: rows in each section are sorted; put one blank line between sections and a blank line before END.
    (The official CPSolver parser uses blank lines to delimit sections; blank lines carry semantics and must not be dropped)."""
    h = inst["header"]
    out = []
    for k in HEADER_KEYS:
        out.append(f"{k}: {h[k]}")
    out.append("")
    out.append("COURSES:")
    out += [" ".join(c) for c in inst["courses"]]
    out.append("")
    out.append("ROOMS:")
    out += [" ".join(r) for r in inst["rooms"]]
    out.append("")
    out.append("CURRICULA:")
    out += [" ".join(q) for q in inst["curricula"]]
    out.append("")
    out.append("UNAVAILABILITY_CONSTRAINTS:")
    out += [" ".join(u) for u in inst["unavail"]]
    out.append("")
    out.append("END.")
    return ("\n".join(out) + "\n").encode()


def _perm_map(labels, rng):
    """Return {old_label: new_label} permuting the label multiset."""
    labs = sorted(labels)
    shuffled = labs[:]
    rng.shuffle(shuffled)
    return dict(zip(labs, shuffled))


def transform_instance(stem, inst):
    """Return (new_inst, maps). maps contains four old-to-new identifier maps: course/room/teacher/curriculum.
    Days and periods remain unchanged."""
    seed = derive_seed(stem)
    rng = random.Random(seed)
    cmap = _perm_map([c[0] for c in inst["courses"]], rng)
    rmap = _perm_map([r[0] for r in inst["rooms"]], rng)
    tmap = _perm_map(sorted({c[1] for c in inst["courses"]}), rng)
    qmap = _perm_map([q[0] for q in inst["curricula"]], rng)

    new = {"header": dict(inst["header"]), "courses": [], "rooms": [],
           "curricula": [], "unavail": []}
    new["header"]["Name"] = NEUTRAL_NAME
    new["courses"] = sorted([cmap[c[0]], tmap[c[1]], c[2], c[3], c[4]]
                            for c in inst["courses"])
    new["rooms"] = sorted([rmap[r[0]], r[1]] for r in inst["rooms"])
    new["curricula"] = sorted([qmap[q[0]], q[1]]
                              + sorted(cmap[c] for c in q[2:])
                              for q in inst["curricula"])
    new["unavail"] = sorted(([cmap[u[0]], u[1], u[2]]
                             for u in inst["unavail"]),
                            key=lambda u: (u[0], int(u[1]), int(u[2])))
    maps = {"course_map": cmap, "room_map": rmap, "teacher_map": tmap,
            "curriculum_map": qmap}
    return new, maps


def invert_instance(inst_t, maps, orig_name):
    """Inverse transform: restore identifiers and the Name header using the four maps; reorder rows by original identifiers
    (consistent with emit normalization)."""
    inv = {k: {new: old for old, new in m.items()} for k, m in maps.items()}
    cm, rm, tm, qm = (inv["course_map"], inv["room_map"],
                      inv["teacher_map"], inv["curriculum_map"])
    r = {"header": dict(inst_t["header"]), "courses": [], "rooms": [],
         "curricula": [], "unavail": []}
    r["header"]["Name"] = orig_name
    r["courses"] = sorted([cm[c[0]], tm[c[1]], c[2], c[3], c[4]]
                          for c in inst_t["courses"])
    r["rooms"] = sorted([rm[rr[0]], rr[1]] for rr in inst_t["rooms"])
    r["curricula"] = sorted([qm[q[0]], q[1]]
                            + sorted(cm[c] for c in q[2:])
                            for q in inst_t["curricula"])
    r["unavail"] = sorted(([cm[u[0]], u[1], u[2]]
                           for u in inst_t["unavail"]),
                          key=lambda u: (u[0], int(u[1]), int(u[2])))
    return r


def hidden_stems_sorted():
    with open(os.path.join(TESTS, "split.json")) as f:
        split = json.load(f)
    return sorted(fn[:-len(".ctt")] for fn, side in split.items()
                  if side == "hidden")


def cmd_apply(args):
    os.makedirs(args.out_dir, exist_ok=True)
    stems = hidden_stems_sorted()
    manifest = {
        "transform": TRANSFORM_ID,
        "operations": ["relabel-courses", "relabel-rooms",
                       "relabel-teachers", "relabel-curricula"],
        "days_periods": "untouched (calendar semantics)",
        "seed_rule": SEED_RULE,
        "instances": {},
    }
    for i, stem in enumerate(stems, 1):
        new_name = f"h{i:02d}"
        src = os.path.join(args.instances_dir, stem + ".ctt")
        with open(src, "rb") as f:
            plain = f.read()
        inst = load_ctt(src)
        new, maps = transform_instance(stem, inst)
        out_plain = emit(new)
        dst = os.path.join(args.out_dir, new_name + ".ctt")
        with open(dst, "wb") as f:
            f.write(out_plain)
        os.chmod(dst, 0o644)
        entry = {
            "official": stem,
            "orig_name_header": inst["header"].get("Name", ""),
            "seed": derive_seed(stem),
            "n_courses": len(new["courses"]),
            "n_rooms": len(new["rooms"]),
            "src_sha256_plain": hashlib.sha256(plain).hexdigest(),
            "out_sha256_plain": hashlib.sha256(out_plain).hexdigest(),
            "oracle_key": oracle_hash(out_plain),
        }
        entry.update(maps)
        manifest["instances"][new_name] = entry
        print(f"[apply] {stem} -> {new_name}.ctt "
              f"(C={entry['n_courses']} R={entry['n_rooms']})", flush=True)
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
        problems = []
        try:
            inst_o = load_ctt(os.path.join(args.orig_dir, stem + ".ctt"))
            inst_t = load_ctt(os.path.join(args.trans_dir,
                                           new_name + ".ctt"))
        except ValueError as e:
            print(f"[invert] {new_name} ({stem}): FAIL parse: {e}")
            n_bad += 1
            continue
        maps = {k: rec[k] for k in ("course_map", "room_map",
                                    "teacher_map", "curriculum_map")}
        for label, m in maps.items():
            if len(set(m) ^ set(m.values())):
                problems.append(f"{label} not a bijection on its class")
        if not problems:
            r = invert_instance(inst_t, maps, rec["orig_name_header"])
            # Semantic equality (ignore formatting differences such as trailing spaces, row order within sections, and curriculum-member order
            # in the source): compare header fields individually and compare normalized sets for each section
            if r["header"] != inst_o["header"]:
                problems.append("header mismatch after restore")
            for sec in ("courses", "rooms", "unavail"):
                if {tuple(x) for x in r[sec]} != {tuple(x)
                                                  for x in inst_o[sec]}:
                    problems.append(f"section {sec} mismatch after restore")
            norm = lambda qs: {(q[0], q[1], frozenset(q[2:])) for q in qs}
            if norm(r["curricula"]) != norm(inst_o["curricula"]):
                problems.append("section curricula mismatch after restore")
        if problems:
            n_bad += 1
            print(f"[invert] {new_name} ({stem}): FAIL "
                  f"{'; '.join(problems)}")
        else:
            n_ok += 1
            print(f"[invert] {new_name} ({stem}): ok")
    print(f"[invert] ok={n_ok} bad={n_bad}")
    return 1 if n_bad else 0


def cmd_rewrite_solutions(args):
    """Rewrite prerecorded timetables with the manifest's course/room maps;
    rebuild the oracle lookup manifest against the transformed instances."""
    with open(args.manifest) as f:
        manifest = json.load(f)["instances"]
    os.makedirs(args.out_dir, exist_ok=True)
    out_manifest = {}
    n_sol = 0
    for new_name, rec in sorted(manifest.items()):
        stem = rec["official"]
        src_sol = os.path.join(args.sol_dir, stem + ".sol")
        if not os.path.exists(src_sol):
            print(f"[rewrite-solutions] {stem}: no prerecorded solution, "
                  f"skipped")
            continue
        cmap, rmap = rec["course_map"], rec["room_map"]
        out_lines = []
        with open(src_sol) as f:
            for raw in f:
                line = raw.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) != 4:
                    sys.exit(f"[rewrite-solutions] {stem}: bad line {line!r}")
                c, r, day, period = parts
                if c not in cmap or r not in rmap:
                    sys.exit(f"[rewrite-solutions] {stem}: line {line!r} "
                             f"references an identifier not in the maps")
                out_lines.append(" ".join([cmap[c], rmap[r], day, period]))
        with open(os.path.join(args.out_dir, new_name + ".sol"), "w") as f:
            f.write("\n".join(out_lines) + "\n")
        with open(os.path.join(args.instances_dir, new_name + ".ctt"),
                  "rb") as f:
            key = oracle_hash(f.read())
        if key != rec["oracle_key"]:
            sys.exit(f"[rewrite-solutions] {new_name}: instance key mismatch "
                     f"with manifest ({key} != {rec['oracle_key']})")
        out_manifest[key] = {"sol": new_name + ".sol", "instance": new_name}
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
