#!/usr/bin/env python3
"""Mathematical validation of the bpp-bpplib form2 transformation.

This file checks three mathematical properties of the hidden scored set (39
structure-preserving transformed copies in tests/instances/exNNN.txt), following
the transformation requirements in form2-conversion-recipes.md:
  1. Round trip: regenerate perm from the seed rule; applying the transformation
     to an official instance must reproduce the scored exNNN byte for byte.
     invert(apply(x)) must equal x token by token, and apply output must be a
     canonical fixed point.
  2. Solution value is preserved: recompute K for all 39 official optimum packings
     in tests/official-packs/. After reordering item IDs according to the item
     permutation, recompute the value on the transformed instance; it must equal
     the same K, using the actual check_bpp in tests/scoring.py, also used in scoring.
  3. K reuse: each hidden key's K in tests/reference.json equals the value recomputed
     from the reordered packing; B and K in tests/anchors.json match reference key by key.
A further set-consistency gate checks that the key sets in split.json, codename-map,
tests/instances, reference, the oracle manifest, public environment instances
(/app/instances), the background library (/app/library), and public_reference all
agree. The background library must not overlap the full 129-instance scored set.

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
PACKS_DIR = os.path.join(HERE, "official-packs")
JUDGED129 = set(HIDDEN) | set(PUBLIC)


def bins_of_pack(inst_path, bins, B):
    with tempfile.NamedTemporaryFile("w", suffix=".pack", delete=False) as f:
        f.write(f"{B}\n" + " ".join(str(x) for x in bins) + "\n")
        tmp = f.name
    try:
        got, err = scoring.check_bpp(inst_path, tmp)
    finally:
        os.unlink(tmp)
    if err is not None:
        raise AssertionError(f"{inst_path}: invalid packing {err}")
    return got


def read_pack(path):
    with open(path) as f:
        vals = f.read().split()
    return int(vals[0]), [int(x) for x in vals[1:]]


class SetConsistencyTest(unittest.TestCase):
    def test_split_sizes(self):
        self.assertEqual(len(SPLIT), 129)
        self.assertEqual(len(HIDDEN), 39)
        self.assertEqual(len(PUBLIC), 90)

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
        self.assertEqual(len(lib), 6345 - 129)
        self.assertFalse(lib & JUDGED129,
                         "the background library must not contain any official instance from the full 129-instance scored set")
        pubref = json.load(open(os.path.join(
            TASK, "environment", "app", "public_reference.json")))["instances"]
        self.assertEqual(sorted(pubref), PUBLIC)
        sols = sorted(os.listdir(os.path.join(TASK, "environment", "app",
                                              "solutions")))
        for s in sols:
            self.assertNotIn(s[:-len(".pack")] + ".txt", HIDDEN,
                             f"{s}: packings for hidden source instances must not remain in the environment")


class RoundtripTest(unittest.TestCase):
    """Round trip and scored-side bytes equal apply output (the transformation was constructed correctly)."""

    def test_apply_matches_judged_bytes(self):
        for name in HIDDEN:
            with self.subTest(inst=name):
                n, C, w = tf.parse_instance(os.path.join(OFFICIAL_DIR, name))
                nw, perm = tf.transform_instance(name, n, w)
                applied = tf.serialize(n, C, nw)
                with open(os.path.join(TRANS_DIR, OFF2CODE[name]), "rb") as f:
                    self.assertEqual(applied, f.read(),
                                     f"{name}: locally applied output differs from scored-side bytes")
                self.assertEqual(tf.params_hash(perm),
                                 CMAP[OFF2CODE[name]]["transform_params_sha256"])

    def test_invert_roundtrip(self):
        for name in HIDDEN:
            with self.subTest(inst=name):
                n, C, w = tf.parse_instance(os.path.join(OFFICIAL_DIR, name))
                nw, _ = tf.transform_instance(name, n, w)
                w2, _ = tf.invert_instance(name, n, nw)
                self.assertEqual(w, w2, f"{name}: invert(apply(x)) != x")
                nw2, _ = tf.transform_instance(name, n, w2)
                self.assertEqual(tf.serialize(n, C, nw),
                                 tf.serialize(n, C, nw2))
                # multiset unchanged and bytes changed
                self.assertEqual(sorted(w), sorted(nw))
                with open(os.path.join(OFFICIAL_DIR, name), "rb") as f:
                    ob = f.read()
                with open(os.path.join(TRANS_DIR, OFF2CODE[name]), "rb") as f:
                    self.assertNotEqual(ob, f.read())


class ValueAndAnchorTest(unittest.TestCase):
    """Solution value is preserved and K reused (recompute all 39 keys with the actual check_bpp)."""

    def test_solution_value_invariant_and_k_carried(self):
        for name in HIDDEN:
            with self.subTest(inst=name):
                code = OFF2CODE[name]
                n, C, w = tf.parse_instance(os.path.join(OFFICIAL_DIR, name))
                _, perm = tf.transform_instance(name, n, w)
                B, bins = read_pack(os.path.join(
                    PACKS_DIR, name[:-len(".txt")] + ".pack"))
                k_ref = REF[code]["K"]
                got_off = bins_of_pack(os.path.join(OFFICIAL_DIR, name), bins, B)
                self.assertEqual(got_off, k_ref,
                                 f"{name}: recomputed official packing {got_off} != K {k_ref}")
                mapped = tf.rewrite_packing(bins, perm)
                got_tr = bins_of_pack(os.path.join(TRANS_DIR, code), mapped, B)
                self.assertEqual(got_tr, k_ref,
                                 f"{code} ({name}): recomputed reordered packing {got_tr} != K {k_ref}")

    def test_oracle_packs_recompute_to_k(self):
        oracle = os.path.join(TASK, "solution", "precomputed")
        man = json.load(open(os.path.join(oracle, "manifest.json")))
        self.assertEqual(len(man), 39)
        for h, e in man.items():
            with self.subTest(inst=e["codename"]):
                B, bins = read_pack(os.path.join(oracle, e["pack"]))
                got = bins_of_pack(os.path.join(TRANS_DIR, e["codename"]), bins, B)
                self.assertEqual(got, REF[e["codename"]]["K"],
                                 f"{e['codename']}: oracle recomputation {got} != K")

    def test_anchors_match_reference(self):
        anchors = json.load(open(os.path.join(HERE, "anchors.json")))
        for code in REF:
            self.assertEqual(anchors["K"][code], REF[code]["K"], f"{code}: K anchor drift")
            self.assertEqual(anchors["B"][code], REF[code]["B"], f"{code}: B anchor drift")


if __name__ == "__main__":
    unittest.main(verbosity=2)
