#!/usr/bin/env python3
"""Structure-preserving transformation tool for the qap-qaplib scored set (deterministic facility and location relabeling).

This tool transforms official QAPLIB instances into coded scored instances
(exNNN) and produces transformed replay packages for the oracle stub. It preserves
the optimum, so memorized optimal permutations of public official instances cannot
be submitted directly on their transformed copies. The permutation map is kept out
of the model environment.

Transformation (objective value is preserved):
  Relabel facilities with a seeded bijection pi and locations with an independent
  seeded bijection sigma; reorder flow matrix F and distance matrix D accordingly:
      F'[pi(i)][pi(j)] = F[i][j]      D'[sigma(a)][sigma(b)] = D[a][b]
  Map each solution as p'(pi(i)) = sigma(p(i)), i.e. p' = sigma ∘ p ∘ pi^{-1}.
  For every permutation, cost'(p') == cost(p), so the optimal value K is invariant
  under isomorphism. The .dat format has no comments; canonical rewriting also
  removes byte-layout fingerprints from the original file.

Deterministic per-instance seed:
    seed = int.from_bytes(
        sha256(b"tcshard-transform-20260831:" + name.encode())[:8], "big")
    rng = random.Random(seed)
  name is the official instance name (for example, "bur26a.dat"). RNG use order:
  first shuffle [1..n] for the facility permutation pi, then shuffle [1..n] for the
  location permutation sigma.

The 20260831 seed tag is retained because the 2026-09-13 restoration batch
(next-steps-260911.md §E2) generated 136 instances by the same rule and baked them
into scoring image solver-qap-qaplib-judge-v9 (used by the async lineage); records
are in historical measurement records (not included in this package). Keeping the same seed makes
bytes generated here exactly match the online scoring image (release assertion:
regenerated bur26a.dat equals the restored bytes). Final lineage (v11) and async
lineage (v10) share the same transformed instances, and both oracle packages work.

Code assignment: exNNN ↔ official-name mapping reuses the existing assignment in
 tests/codename-map.json, ordered by official name as ex001..ex136. This script only
checks the mapping and does not assign names again, avoiding drift from the async
package and online v9 image.

Subcommands:
  batch            Transform the full official-instance directory into exNNN.dat
                   and write transform_manifest.json (full permutation table;
                   confidential and written outside Git by default, never into the
                   model-readable /tests layer of the scoring image), plus
                   codename-map.json (code ↔ official name ↔ transformed-byte
                   SHA-256 ↔ official-byte SHA-256 ↔ permutation-parameter hash;
                   this file may live under tests/). Maintenance command to
                   generate all 136 instances before the form2 split; after the
                   split is frozen, tests/instances contains only 41 hidden keys,
                   so do not rerun it.
  verify           Independently invert transformed instances using manifest
                   permutations and compare each official matrix element and
                   element multiset; bytes must differ. Maintenance command.
  bake-oracle      Rewrite registered 1-based forward permutations using
                   p'(pi(i)) = sigma(p(i)); rekey the manifest by transformed-instance
                   token-stream SHA-256. Maintenance command.
  verify-oracle    Apply the actual check_qap from tests/scoring.py to each
                   transformed instance and rewritten permutation; objective value
                   must exactly equal reference K.
  --apply IN --name OFFICIAL_NAME --out OUT
                   Forward-transform one instance by regenerating π/σ from the seed
                   rule and emitting canonical bytes.
  --invert IN --name OFFICIAL_NAME --out OUT
                   Invert the matrix with the same π/σ (canonical form); invert(apply(x))
                   and x must be elementwise equal.

After form2, the hidden scored set is a stratified 30% sample of the
136 official instances (41 transformed keys in tests/split.json). Routine
mathematical checks use tests/test_transform.py; it depends only on this file and
tests/scoring.py, not on the private manifest.

Standard library only."""

import argparse
import hashlib
import json
import os
import random
import sys

SEED_TAG = "tcshard-transform-20260831"
TRANSFORM_ID = "qap-fac-loc-permute-v1"
SEED_RULE = (
    "seed = int.from_bytes(sha256('tcshard-transform-20260831:' + name)[:8],"
    " 'big'); rng = random.Random(seed); consumption order: facility"
    " permutation shuffle, then location permutation shuffle;"
    " name = official instance file name (e.g. bur26a.dat)"
)


def derive_seed(name):
    h = hashlib.sha256((SEED_TAG + ":" + name).encode()).digest()
    return int.from_bytes(h[:8], "big")


def oracle_hash(plain_bytes):
    """Exactly what the oracle stub computes on its stdin."""
    return hashlib.sha256(b" ".join(plain_bytes.split())).hexdigest()


def parse_dat(path):
    with open(path) as f:
        vals = f.read().split()
    n = int(vals[0])
    need = 1 + 2 * n * n
    if len(vals) != need:
        raise ValueError(f"{path}: expected {need} tokens, found {len(vals)}")
    nums = [int(v) for v in vals[1:]]
    F = [nums[i * n:(i + 1) * n] for i in range(n)]
    D = [nums[n * n + i * n:n * n + (i + 1) * n] for i in range(n)]
    return n, F, D


def transform_instance(name, n, F, D):
    """Return (Fp, Dp, pi, sigma); pi/sigma are 1-based old->new lists."""
    rng = random.Random(derive_seed(name))
    pi = list(range(1, n + 1))
    rng.shuffle(pi)          # facilities: pi[old-1] = new
    sigma = list(range(1, n + 1))
    rng.shuffle(sigma)       # locations: sigma[old-1] = new
    inv_pi = [0] * n
    inv_sigma = [0] * n
    for old in range(n):
        inv_pi[pi[old] - 1] = old
        inv_sigma[sigma[old] - 1] = old
    Fp = [[F[inv_pi[a]][inv_pi[b]] for b in range(n)] for a in range(n)]
    Dp = [[D[inv_sigma[a]][inv_sigma[b]] for b in range(n)] for a in range(n)]
    return Fp, Dp, pi, sigma


def serialize(n, F, D):
    out = [f"{n}\n"]
    for row in F:
        out.append(" " + " ".join(str(v) for v in row) + " \n")
    for row in D:
        out.append(" " + " ".join(str(v) for v in row) + " \n")
    return "".join(out).encode()


def params_hash(pi, sigma):
    """Permutation-parameter hash: this is recorded in codename-map; the full permutation table exists only in
    transform_manifest.json (confidential, outside the repository)."""
    blob = json.dumps({"pi": pi, "sigma": sigma}, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def load_codename_assignment(path):
    """Read the existing codename-map.json and return {official: exNNN} (ordered by official name;
    assert that ex numbers are contiguous to prevent drift from async packages/online images)."""
    with open(path) as f:
        data = json.load(f)
    inst = data["instances"]
    official2code = {rec["official"]: code for code, rec in inst.items()}
    codes = sorted(inst)
    assert codes == [f"ex{i:03d}.dat" for i in range(1, len(codes) + 1)], \
        f"codename numbers are not contiguous: {codes[:3]}...{codes[-3:]}"
    officials = sorted(official2code)
    assert [official2code[o] for o in officials] == codes, \
        "existing assignments are not ordered by official name (they differ from the 3580 batch); stop to prevent drift"
    return official2code


def rewrite_perm(perm1, pi, sigma):
    """p'(pi(i)) = sigma(p(i)); all 1-based, lists indexed from 0."""
    n = len(perm1)
    newp = [0] * n
    for old in range(n):
        newp[pi[old] - 1] = sigma[perm1[old] - 1]
    return newp


def cmd_batch(args):
    official2code = load_codename_assignment(args.codename_map)
    os.makedirs(args.out_dir, exist_ok=True)
    names = sorted(f for f in os.listdir(args.instances_dir)
                   if f.endswith(".dat"))
    if sorted(official2code) != names:
        sys.exit(f"[batch] official instance set does not match codename-map: "
                 f"map {len(official2code)} vs dir {len(names)}")
    manifest = {
        "transform": TRANSFORM_ID,
        "operations": ["permute-facilities(F lockstep)",
                       "permute-locations(D lockstep)",
                       "canonical-reserialize"],
        "seed_rule": SEED_RULE,
        "codename_rule": "existing codename-map assignment (alphabetical)",
        "instances": {},
    }
    newmap = {
        "transform": {
            "id": TRANSFORM_ID,
            "seed_rule": SEED_RULE,
            "note": ("scored instances are structure-preserving transformed copies of the official set (facility/location relabeling,"
                     "optimal value unchanged); the complete permutation table is in transform_manifest.json"
                     "(confidential outside the repository; see PROVENANCE.md, 2026-09-17 section); this file only"
                     "records the parameter hash. Generated by the same rule as the 2026-09-13 restoration batch and regenerated on 260917 by "
                     "tests/transform.py and checked byte for byte."),
        },
        "instances": {},
    }
    for name in names:
        code = official2code[name]
        src = os.path.join(args.instances_dir, name)
        with open(src, "rb") as f:
            plain = f.read()
        n, F, D = parse_dat(src)
        Fp, Dp, pi, sigma = transform_instance(name, n, F, D)
        out_plain = serialize(n, Fp, Dp)
        dst = os.path.join(args.out_dir, code)
        with open(dst, "wb") as f:
            f.write(out_plain)
        os.chmod(dst, 0o644)
        manifest["instances"][name] = {
            "codename": code,
            "seed": derive_seed(name),
            "n": n,
            "perm_facilities_new_from_old": pi,
            "perm_locations_new_from_old": sigma,
            "src_sha256_plain": hashlib.sha256(plain).hexdigest(),
            "out_sha256_plain": hashlib.sha256(out_plain).hexdigest(),
            "oracle_key": oracle_hash(out_plain),
        }
        newmap["instances"][code] = {
            "judged": True,
            "official": name,
            "src_sha256": hashlib.sha256(out_plain).hexdigest(),
            "official_sha256": hashlib.sha256(plain).hexdigest(),
            "transform_params_sha256": params_hash(pi, sigma),
        }
        print(f"[batch] {name} -> {code}: n={n}", flush=True)
    with open(args.manifest, "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
    os.chmod(args.manifest, 0o644)
    with open(args.map_out, "w") as f:
        json.dump(newmap, f, indent=1, sort_keys=True)
    os.chmod(args.map_out, 0o644)
    print(f"[batch] manifest (confidential, retained outside the repository): {args.manifest} "
          f"({len(manifest['instances'])} instances)")
    print(f"[batch] codename-map: {args.map_out}")


def cmd_verify(args):
    with open(args.manifest) as f:
        manifest = json.load(f)
    official2code = {rec["official"]: code
                     for code, rec in json.load(open(args.codename_map))["instances"].items()}
    n_ok = n_bad = 0
    for name, rec in sorted(manifest["instances"].items()):
        code = rec.get("codename") or official2code[name]
        n_o, F_o, D_o = parse_dat(os.path.join(args.orig_dir, name))
        n_t, F_t, D_t = parse_dat(os.path.join(args.trans_dir, code))
        pi = rec["perm_facilities_new_from_old"]
        sigma = rec["perm_locations_new_from_old"]
        problems = []
        n = rec["n"]
        if n_o != n or n_t != n:
            problems.append("dimension mismatch")
        if sorted(pi) != list(range(1, n + 1)):
            problems.append("facility permutation not a bijection")
        if sorted(sigma) != list(range(1, n + 1)):
            problems.append("location permutation not a bijection")
        if not problems:
            inv_pi = [0] * n
            inv_sigma = [0] * n
            for old in range(n):
                inv_pi[pi[old] - 1] = old
                inv_sigma[sigma[old] - 1] = old
            for a in range(n):
                for b in range(n):
                    if F_t[a][b] != F_o[inv_pi[a]][inv_pi[b]]:
                        problems.append(f"F[{a}][{b}] mismatch")
                        break
                    if D_t[a][b] != D_o[inv_sigma[a]][inv_sigma[b]]:
                        problems.append(f"D[{a}][{b}] mismatch")
                        break
                if problems:
                    break
            # Element multiset (synchronized row/column permutations preserve the matrix-wide multiset)
            if sorted(v for row in F_t for v in row) != \
               sorted(v for row in F_o for v in row):
                problems.append("F element multiset differs")
            if sorted(v for row in D_t for v in row) != \
               sorted(v for row in D_o for v in row):
                problems.append("D element multiset differs")
            with open(os.path.join(args.orig_dir, name), "rb") as f:
                orig_bytes = f.read()
            with open(os.path.join(args.trans_dir, code), "rb") as f:
                if f.read() == orig_bytes:
                    problems.append("bytes unchanged")
        if problems:
            n_bad += 1
            print(f"[verify] {name} ({code}): FAIL {'; '.join(problems)}")
        else:
            n_ok += 1
    print(f"[verify] ok={n_ok} bad={n_bad}")
    return 1 if n_bad else 0


def cmd_bake_oracle(args):
    with open(args.manifest) as f:
        manifest = json.load(f)
    with open(os.path.join(args.orig_oracle, "manifest.json")) as f:
        om = json.load(f)
    with open(args.reference) as f:
        ref = json.load(f)["instances"]
    os.makedirs(args.out_dir, exist_ok=True)
    new_manifest = {}
    for name, rec in sorted(manifest["instances"].items()):
        code = rec["codename"]
        ent = None
        for _, e in om.items():
            if e["instance"] == name:
                ent = e
                break
        if ent is None:
            sys.exit(f"[bake-oracle] no original oracle entry for {name}")
        with open(os.path.join(args.orig_oracle, ent["perm"])) as f:
            perm1 = [int(x) for x in f.read().split()]
        newp = rewrite_perm(perm1, rec["perm_facilities_new_from_old"],
                            rec["perm_locations_new_from_old"])
        with open(os.path.join(args.out_dir, ent["perm"]), "w") as f:
            f.write(" ".join(str(x) for x in newp) + "\n")
        with open(os.path.join(args.trans_dir, code), "rb") as f:
            key = oracle_hash(f.read())
        if key != rec["oracle_key"]:
            sys.exit(f"[bake-oracle] oracle_key mismatch for {name}")
        new_manifest[key] = {"instance": name,
                             "codename": code,
                             "perm": ent["perm"],
                             "K": ref[name]["K"],
                             "interpretation": "rewritten-by-transform"}
    with open(os.path.join(args.out_dir, "manifest.json"), "w") as f:
        json.dump(new_manifest, f, indent=1, sort_keys=True)
    os.chmod(os.path.join(args.out_dir, "manifest.json"), 0o644)
    print(f"[bake-oracle] {len(new_manifest)} rewritten packs -> {args.out_dir}")


def cmd_verify_oracle(args):
    sys.path.insert(0, args.scoring_dir)
    import scoring  # the task's own scoring module (check_qap)
    with open(args.manifest) as f:
        manifest = json.load(f)
    with open(args.reference) as f:
        ref = json.load(f)["instances"]
    n_ok = n_bad = 0
    for name, rec in sorted(manifest["instances"].items()):
        code = rec["codename"]
        base = name[:-len(".dat")]
        sol_path = os.path.join(args.oracle_dir, base + ".perm")
        inst_path = os.path.join(args.trans_dir, code)
        cost, err = scoring.check_qap(inst_path, sol_path)
        K = ref[name]["K"] if name in ref else None
        if err is not None:
            n_bad += 1
            print(f"[verify-oracle] {code} ({name}): INVALID {err}")
        elif K is not None and cost != K:
            n_bad += 1
            print(f"[verify-oracle] {code} ({name}): cost {cost} != K {K}")
        else:
            n_ok += 1
            print(f"[verify-oracle] {code} ({name}): ok cost={cost}")
    print(f"[verify-oracle] ok={n_ok} bad={n_bad}")
    return 1 if n_bad else 0


def invert_instance(name, n, Ft, Dt):
    """Inverse of forward transform: F[x][y] = Ft[pi(x)][pi(y)], and likewise D (derive pi/sigma from the seed rule
    using the official name, yielding the same pair as the forward transform). Return (F, D, pi, sigma)."""
    rng = random.Random(derive_seed(name))
    pi = list(range(1, n + 1))
    rng.shuffle(pi)
    sigma = list(range(1, n + 1))
    rng.shuffle(sigma)
    F = [[Ft[pi[a] - 1][pi[b] - 1] for b in range(n)] for a in range(n)]
    D = [[Dt[sigma[a] - 1][sigma[b] - 1] for b in range(n)] for a in range(n)]
    return F, D, pi, sigma


def cmd_apply(args):
    n, F, D = parse_dat(args.apply)
    Fp, Dp, _, _ = transform_instance(args.name, n, F, D)
    with open(args.out, "wb") as f:
        f.write(serialize(n, Fp, Dp))
    print(f"[apply] {args.name}: n={n} -> {args.out}")


def cmd_invert(args):
    n, Ft, Dt = parse_dat(args.invert)
    F, D, _, _ = invert_instance(args.name, n, Ft, Dt)
    with open(args.out, "wb") as f:
        f.write(serialize(n, F, D))
    print(f"[invert] {args.name}: n={n} -> {args.out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", metavar="IN",
                    help="Forward-transform one instance: read official .dat and write transformed bytes to --out")
    ap.add_argument("--invert", metavar="IN",
                    help="Invert one instance: read transformed .dat and write the restored matrix to --out")
    ap.add_argument("--name", help="Official instance name (used to derive the seed, e.g. bur26a.dat)")
    ap.add_argument("--out", help="Output path for --apply/--invert")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("batch")
    p.add_argument("--instances-dir", required=True,
                   help="Official instance directory (environment/app/instances)")
    p.add_argument("--out-dir", required=True,
                   help="Output directory for transformed exNNN.dat files (tests/instances)")
    p.add_argument("--manifest", required=True,
                   help="Output path for transform_manifest.json (confidential path outside the repository)")
    p.add_argument("--codename-map", required=True,
                   help="Existing codename-map.json (reuse its exNNN assignments)")
    p.add_argument("--map-out", required=True,
                   help="Output path for the new codename-map.json")
    p.set_defaults(fn=cmd_batch)
    p = sub.add_parser("verify")
    p.add_argument("--orig-dir", required=True)
    p.add_argument("--trans-dir", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--codename-map", required=True)
    p.set_defaults(fn=cmd_verify)
    p = sub.add_parser("bake-oracle")
    p.add_argument("--orig-oracle", required=True,
                   help="Source directory for official permutations (tests/official-perms, including manifest.json)")
    p.add_argument("--trans-dir", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--reference", required=True,
                   help="reference.json keyed by official name (read K)")
    p.add_argument("--out-dir", required=True)
    p.set_defaults(fn=cmd_bake_oracle)
    p = sub.add_parser("verify-oracle")
    p.add_argument("--oracle-dir", required=True)
    p.add_argument("--trans-dir", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--reference", required=True,
                   help="reference.json keyed by official name (read K)")
    p.add_argument("--scoring-dir", required=True)
    p.set_defaults(fn=cmd_verify_oracle)
    args = ap.parse_args()
    if args.apply or args.invert:
        if not args.name or not args.out:
            ap.error("--apply/--invert require --name and --out")
        if args.apply and args.invert:
            ap.error("choose either --apply or --invert")
        if args.apply:
            cmd_apply(args)
        else:
            cmd_invert(args)
        return
    if not args.cmd:
        ap.error("Specify a subcommand (batch/verify/bake-oracle/verify-oracle) or --apply/--invert")
    sys.exit(args.fn(args) or 0)


if __name__ == "__main__":
    main()
