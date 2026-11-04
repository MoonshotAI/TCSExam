#!/usr/bin/env python3
"""Mathematical validation of the cvrp-cvrplib form2 transformation.

This file checks three mathematical properties of the hidden scored set (34
structure-preserving transformed copies in tests/instances/exNNN.vrp), following
the transformation requirements in form2-conversion-recipes.md:
  1. Round trip: regenerate pi from the seed rule; applying the transformation
     to an official instance must reproduce the scored exNNN byte for byte.
     invert(apply(x)) must equal x field by field in semantic content
     (n/capacity/depot/coords/demands; source COMMENT fingerprints are intentionally
     unrecoverable), and apply output must be a canonical fixed point.
  2. Solution value is preserved: recompute K from the official best solutions in
     tests/official-routes/ for all 34 hidden instances. After relabeling nodes by
     the node permutation, the value recomputed on the transformed instance must
     equal the same K using the actual check_cvrp in tests/scoring.py, also used in
     scoring, including enforcement of the fleet-size limit.
  3. K reuse: each hidden key's K in tests/reference.json equals the value recomputed
     from the relabeled solution; B and K in tests/anchors.json match reference key
     by key.
A further set-consistency gate checks that the key sets in split.json, codename-map,
tests/instances, reference, the oracle manifest, public environment instances
(/app/instances), the background library (/app/library), and public_reference all
agree. The background library must not overlap the full 114-instance scored set.

This does not depend on the private manifest (the permutation is regenerated from
the seed rule). Run with `python3 tests/test_transform.py` from the task root or
any directory."""
import hashlib
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import scoring  # noqa: E402
import transform as tf  # noqa: E402

SPLIT = json.load(open(os.path.join(HERE, "split.json")))["instances"]
CMAP = json.load(open(os.path.join(HERE, "codename-map.json")))["instances"]
REF = json.load(open(os.path.join(HERE, "reference.json")))["instances"]
HIDDEN = sorted(n for n, e in SPLIT.items() if e["side"] == "hidden")
PUBLIC = sorted(n for n, e in SPLIT.items() if e["side"] == "public")
OFF2CODE = {rec["official"]: code for code, rec in CMAP.items()}
OFFICIAL_DIR = os.path.join(HERE, "official-instances")
TRANS_DIR = os.path.join(HERE, "instances")
ROUTES_DIR = os.path.join(HERE, "official-routes")
JUDGED114 = set(HIDDEN) | set(PUBLIC)


def cost_of_routes(inst_path, routes):
    with tempfile.NamedTemporaryFile("w", suffix=".routes", delete=False) as f:
        f.write(tf.serialize_routes(routes))
        tmp = f.name
    try:
        cost, err = scoring.check_cvrp(inst_path, tmp)
    finally:
        os.unlink(tmp)
    if err is not None:
        raise AssertionError(f"{inst_path}: invalid route {err}")
    return cost


def read_routes(path):
    with open(path) as f:
        return tf.parse_routes_tokens(f.read().split())


def semantic(inst):
    return (inst["n"], inst["header"]["CAPACITY"], inst["depot"],
            {k: (float(x), float(y)) for k, (x, y) in inst["coords"].items()},
            {k: int(v) for k, v in inst["demand"].items()})


class SetConsistencyTest(unittest.TestCase):
    def test_split_sizes(self):
        self.assertEqual(len(SPLIT), 114)
        self.assertEqual(len(HIDDEN), 34)
        self.assertEqual(len(PUBLIC), 80)

    def test_codename_map_covers_hidden(self):
        self.assertEqual(sorted(OFF2CODE), HIDDEN)
        self.assertEqual(sorted(CMAP), sorted(OFF2CODE[n] for n in HIDDEN))

    def test_judged_files_match_map(self):
        self.assertEqual(sorted(os.listdir(TRANS_DIR)), sorted(CMAP))
        for code, rec in CMAP.items():
            h = hashlib.sha256(
                open(os.path.join(TRANS_DIR, code), "rb").read()).hexdigest()
            self.assertEqual(h, rec["src_sha256"], f"{code}: scored-instance bytes do not match the record")
            ho = hashlib.sha256(
                open(os.path.join(OFFICIAL_DIR, rec["official"]), "rb").read()
            ).hexdigest()
            self.assertEqual(ho, rec["official_sha256"],
                             f"{rec['official']}: official source-instance bytes do not match the record")

    def test_reference_and_oracle_keys(self):
        self.assertEqual(sorted(REF), sorted(CMAP))
        man = json.load(open(os.path.join(TASK, "solution", "precomputed",
                                          "manifest.json")))
        self.assertEqual(sorted(e["codename"] for e in man.values()),
                         sorted(CMAP))
        for h, e in man.items():
            with open(os.path.join(TRANS_DIR, e["codename"]), "rb") as f:
                self.assertEqual(tf.oracle_hash(f.read()), h,
                                 f"{e['codename']}: oracle key does not match instance bytes")

    def test_public_side_keys(self):
        env_dir = os.path.join(TASK, "environment", "app", "instances")
        self.assertEqual(sorted(os.listdir(env_dir)), PUBLIC)
        lib_dir = os.path.join(TASK, "environment", "app", "library")
        lib = set(os.listdir(lib_dir))
        self.assertEqual(len(lib), 190 - 114)
        self.assertFalse(lib & JUDGED114,
                         "the background library must not contain any official instance from the full 114-instance scored set")
        pubref = json.load(open(os.path.join(
            TASK, "environment", "app", "public_reference.json")))["instances"]
        self.assertEqual(sorted(pubref), PUBLIC)
        sols = sorted(os.listdir(os.path.join(TASK, "environment", "app",
                                              "solutions")))
        for s in sols:
            self.assertNotIn(s[:-len(".routes")] + ".vrp", HIDDEN,
                             f"{s}: solutions for hidden source instances must not remain in the environment")


class RoundtripTest(unittest.TestCase):
    """Round trip and scored-side bytes equal apply output (the transformation was constructed correctly)."""

    def test_apply_matches_judged_bytes(self):
        for name in HIDDEN:
            with self.subTest(inst=name):
                inst = tf.parse_vrp(os.path.join(OFFICIAL_DIR, name))
                new, perm = tf.transform_instance(name, inst)
                code = OFF2CODE[name]
                import re as _re
                m = _re.search(r"-k(\d+)\.vrp$", name)
                new["header"]["NAME"] = code[:-len(".vrp")] + (
                    ("-k" + m.group(1)) if m else "")
                applied = tf.serialize(new, comment=tf.NEUTRAL_COMMENT)
                with open(os.path.join(TRANS_DIR, code), "rb") as f:
                    self.assertEqual(applied, f.read(),
                                     f"{name}: locally applied output differs from scored-side bytes")
                self.assertEqual(
                    tf.params_hash(perm, inst["depot"], new["depot"]),
                    CMAP[code]["transform_params_sha256"])

    def test_invert_roundtrip(self):
        for name in HIDDEN:
            with self.subTest(inst=name):
                inst = tf.parse_vrp(os.path.join(OFFICIAL_DIR, name))
                new, _ = tf.transform_instance(name, inst)
                inst2, _ = tf.invert_instance(name, new)
                self.assertEqual(semantic(inst), semantic(inst2),
                                 f"{name}: semantic content of invert(apply(x)) != x")
                new2, _ = tf.transform_instance(name, inst2)
                code = OFF2CODE[name]
                with open(os.path.join(TRANS_DIR, code), "rb") as f:
                    deployed = f.read()
                import re as _re
                m = _re.search(r"-k(\d+)\.vrp$", name)
                new2["header"]["NAME"] = code[:-len(".vrp")] + (
                    ("-k" + m.group(1)) if m else "")
                self.assertEqual(tf.serialize(new2, comment=tf.NEUTRAL_COMMENT),
                                 deployed, f"{name}: canonical fixed-point property does not hold")


class ValueAndAnchorTest(unittest.TestCase):
    """Solution value is preserved and K reused (recompute all 34 keys with the actual check_cvrp)."""

    def test_solution_value_invariant_and_k_carried(self):
        for name in HIDDEN:
            with self.subTest(inst=name):
                code = OFF2CODE[name]
                inst = tf.parse_vrp(os.path.join(OFFICIAL_DIR, name))
                _, perm = tf.transform_instance(name, inst)
                routes = read_routes(os.path.join(
                    ROUTES_DIR, name[:-len(".vrp")] + ".routes"))
                k_ref = REF[code]["K"]
                cost_off = cost_of_routes(os.path.join(OFFICIAL_DIR, name), routes)
                self.assertEqual(cost_off, k_ref,
                                 f"{name}: recomputed official solution {cost_off} != K {k_ref}")
                mapped = tf.rewrite_routes(routes, perm)
                cost_tr = cost_of_routes(os.path.join(TRANS_DIR, code), mapped)
                self.assertEqual(cost_tr, k_ref,
                                 f"{code} ({name}): recomputed relabeled solution {cost_tr} != K {k_ref}")

    def test_oracle_routes_recompute_to_k(self):
        oracle = os.path.join(TASK, "solution", "precomputed")
        man = json.load(open(os.path.join(oracle, "manifest.json")))
        self.assertEqual(len(man), 34)
        for h, e in man.items():
            with self.subTest(inst=e["codename"]):
                routes = read_routes(os.path.join(oracle, e["solution"]))
                cost = cost_of_routes(os.path.join(TRANS_DIR, e["codename"]), routes)
                self.assertEqual(cost, REF[e["codename"]]["K"],
                                 f"{e['codename']}: oracle recomputation {cost} != K")

    def test_anchors_match_reference(self):
        anchors = json.load(open(os.path.join(HERE, "anchors.json")))
        for code in REF:
            self.assertEqual(anchors["K"][code], REF[code]["K"], f"{code}: K anchor drift")
            self.assertEqual(anchors["B"][code], REF[code]["B"], f"{code}: B anchor drift")


if __name__ == "__main__":
    unittest.main(verbosity=2)
