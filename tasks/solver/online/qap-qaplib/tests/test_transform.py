#!/usr/bin/env python3
"""Mathematical validation of the qap-qaplib form2 transformation.

This file checks three mathematical properties of the hidden scored set (41
structure-preserving transformed copies in tests/instances/exNNN.dat), following
the transformation requirements in form2-conversion-recipes.md:
  1. Round trip: regenerate π/σ from the seed rule; applying the transformation to
     an official instance must reproduce the scored exNNN byte for byte.
     invert(apply(x)) must equal x element by element, and apply output must be a
     canonical fixed point (apply(invert(apply(x))) == apply(x) byte for byte).
  2. Solution value is preserved: recompute K from each official registered
     permutation p on all 41 hidden instances. After mapping by p'(π(i)) = σ(p(i)),
     recomputing on the transformed instance must give the same K, using the actual
     check_qap in tests/scoring.py, also used in scoring.
  3. K reuse: each hidden key's K in tests/reference.json equals the value recomputed
     from the mapped permutation; B and K in tests/anchors.json (metric-engine
     anchors) match reference key by key.
A further set-consistency gate checks that the key sets in split.json, codename-map,
tests/instances, reference, oracle manifest, public environment instances, and
public_reference all agree.

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

SPLIT = json.load(open(os.path.join(HERE, "split.json")))
CMAP = json.load(open(os.path.join(HERE, "codename-map.json")))["instances"]
REF = json.load(open(os.path.join(HERE, "reference.json")))["instances"]
HIDDEN = sorted(n for n, s in SPLIT.items() if s == "hidden")
PUBLIC = sorted(n for n, s in SPLIT.items() if s == "public")
NEITHER = sorted(n for n, s in SPLIT.items() if s == "neither")
OFF2CODE = {rec["official"]: code for code, rec in CMAP.items()}
OFFICIAL_DIR = os.path.join(HERE, "official-instances")
TRANS_DIR = os.path.join(HERE, "instances")
PERMS_DIR = os.path.join(HERE, "official-perms")


def cost_of_perm(inst_path, perm):
    with tempfile.NamedTemporaryFile("w", suffix=".perm", delete=False) as f:
        f.write(" ".join(str(x) for x in perm) + "\n")
        tmp = f.name
    try:
        cost, err = scoring.check_qap(inst_path, tmp)
    finally:
        os.unlink(tmp)
    if err is not None:
        raise AssertionError(f"{inst_path}: invalid permutation {err}")
    return cost


class SetConsistencyTest(unittest.TestCase):
    def test_split_sizes(self):
        self.assertEqual(len(SPLIT), 136)
        self.assertEqual(len(HIDDEN), 41)
        self.assertEqual(len(PUBLIC), 75)
        self.assertEqual(len(NEITHER), 20)
        # dilution bucket: excluded from environment, scoring reference, and public reference
        env_names = set(os.listdir(os.path.join(
            TASK, "environment", "app", "instances")))
        self.assertFalse(env_names & set(NEITHER))
        pubref = json.load(open(os.path.join(
            TASK, "environment", "app", "public_reference.json")))["instances"]
        self.assertFalse(set(pubref) & set(NEITHER))
        self.assertFalse(set(REF) & set(NEITHER))
        self.assertFalse(set(CMAP) & set(NEITHER))

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
        env_names = sorted(
            os.listdir(os.path.join(TASK, "environment", "app", "instances")))
        self.assertEqual(env_names, PUBLIC)
        pubref = json.load(open(os.path.join(
            TASK, "environment", "app", "public_reference.json")))["instances"]
        self.assertEqual(sorted(pubref), PUBLIC)


class RoundtripTest(unittest.TestCase):
    """Round trip and scored-side bytes equal apply output (the transformation was constructed correctly)."""

    def test_apply_matches_judged_bytes(self):
        for name in HIDDEN:
            with self.subTest(inst=name):
                n, F, D = tf.parse_dat(os.path.join(OFFICIAL_DIR, name))
                Fp, Dp, pi, sigma = tf.transform_instance(name, n, F, D)
                applied = tf.serialize(n, Fp, Dp)
                with open(os.path.join(TRANS_DIR, OFF2CODE[name]), "rb") as f:
                    self.assertEqual(applied, f.read(),
                                     f"{name}: locally applied output differs from scored-side bytes")
                # permutation-parameter hash matches codename-map record
                self.assertEqual(tf.params_hash(pi, sigma),
                                 CMAP[OFF2CODE[name]]["transform_params_sha256"])

    def test_invert_roundtrip(self):
        for name in HIDDEN:
            with self.subTest(inst=name):
                n, F, D = tf.parse_dat(os.path.join(OFFICIAL_DIR, name))
                Fp, Dp, _, _ = tf.transform_instance(name, n, F, D)
                F2, D2, _, _ = tf.invert_instance(name, n, Fp, Dp)
                self.assertEqual((F, D), (F2, D2),
                                 f"{name}: invert(apply(x)) != x")
                # Canonical fixed point: apply(invert(apply(x))) == apply(x) byte for byte
                Fp2, Dp2, _, _ = tf.transform_instance(name, n, F2, D2)
                self.assertEqual(tf.serialize(n, Fp, Dp),
                                 tf.serialize(n, Fp2, Dp2))

    def test_element_multiset_and_bytes_differ(self):
        for name in HIDDEN:
            with self.subTest(inst=name):
                n, F, D = tf.parse_dat(os.path.join(OFFICIAL_DIR, name))
                _, Ft, Dt = tf.parse_dat(os.path.join(TRANS_DIR, OFF2CODE[name]))
                self.assertEqual(sorted(v for r in F for v in r),
                                 sorted(v for r in Ft for v in r))
                self.assertEqual(sorted(v for r in D for v in r),
                                 sorted(v for r in Dt for v in r))
                with open(os.path.join(OFFICIAL_DIR, name), "rb") as f:
                    ob = f.read()
                with open(os.path.join(TRANS_DIR, OFF2CODE[name]), "rb") as f:
                    self.assertNotEqual(ob, f.read())


class ValueAndAnchorTest(unittest.TestCase):
    """Solution value is preserved and K reused (recompute all 41 keys with the actual check_qap)."""

    def test_solution_value_invariant_and_k_carried(self):
        for name in HIDDEN:
            with self.subTest(inst=name):
                code = OFF2CODE[name]
                n, F, D = tf.parse_dat(os.path.join(OFFICIAL_DIR, name))
                _, _, pi, sigma = tf.transform_instance(name, n, F, D)
                with open(os.path.join(
                        PERMS_DIR, name[:-len(".dat")] + ".perm")) as f:
                    perm = [int(x) for x in f.read().split()]
                k_ref = REF[code]["K"]
                cost_off = cost_of_perm(os.path.join(OFFICIAL_DIR, name), perm)
                self.assertEqual(cost_off, k_ref,
                                 f"{name}: recomputed official permutation {cost_off} != K {k_ref}")
                mapped = tf.rewrite_perm(perm, pi, sigma)
                cost_tr = cost_of_perm(os.path.join(TRANS_DIR, code), mapped)
                self.assertEqual(cost_tr, k_ref,
                                 f"{code} ({name}): recomputed mapped permutation {cost_tr} != K {k_ref}")

    def test_oracle_perms_recompute_to_k(self):
        oracle = os.path.join(TASK, "solution", "precomputed")
        man = json.load(open(os.path.join(oracle, "manifest.json")))
        for h, e in man.items():
            with self.subTest(inst=e["codename"]):
                with open(os.path.join(oracle, e["perm"])) as f:
                    perm = [int(x) for x in f.read().split()]
                cost = cost_of_perm(os.path.join(TRANS_DIR, e["codename"]), perm)
                self.assertEqual(cost, REF[e["codename"]]["K"],
                                 f"{e['codename']}: oracle recomputation {cost} != K")

    def test_anchors_match_reference(self):
        anchors = json.load(open(os.path.join(HERE, "anchors.json")))
        for code in REF:
            self.assertEqual(anchors["K"][code], REF[code]["K"], f"{code}: K anchor drift")
            self.assertEqual(anchors["B"][code], REF[code]["B"], f"{code}: B anchor drift")


if __name__ == "__main__":
    unittest.main(verbosity=2)
