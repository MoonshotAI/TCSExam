#!/usr/bin/env python3
"""Mathematical validation of the scp-orlib form2 transformation.

This file checks three mathematical properties of the hidden scored set (26
structure-preserving transformed copies in tests/instances/exNNN.txt), following
the transformation requirements in form2-conversion-recipes.md:
  1. Round trip: regenerate pi/rho from the seed rule (including tests/seed-overrides.json).
     Applying the transformation to an official instance must reproduce the scored
     exNNN byte for byte. invert(apply(x)) must equal x as a canonical set system
     (the source file's within-line ascending order is recovered token by token),
     and apply output must be a canonical fixed point.
  2. Solution value is preserved: for the 20 hidden instances with K witnesses in
     tests/official-sols/, recompute K on the official solutions on the official
     instances. After mapping column IDs by the permutation, recomputing on the
     transformed instances must give the same K using the actual check_scp in
     tests/scoring.py, also used in scoring; the oracle stub must also recompute K
     for all 20 keys. The six keys without witnesses (rail2536/scpcyc07/scpcyc10/
     scpe3/scpnrg3/scpnrh3, listed in tests/official-sols/WITNESS-MISSING.json)
     are covered by the isomorphism check in item 1.
  3. K reuse: each hidden key's K in tests/reference.json equals the mapped witness
     value when a witness exists; B and K in tests/anchors.json match reference
     key by key.
A further set-consistency gate checks that the key sets in split.json, codename-map,
tests/instances, reference, oracle manifest, the public environment instance list
(environment/public-instances.txt), and public_reference all agree.

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
SOLS_DIR = os.path.join(HERE, "official-sols")
OVERRIDES = json.load(open(os.path.join(HERE, "seed-overrides.json")))


def cost_of_cover(inst_path, cover):
    with tempfile.NamedTemporaryFile("w", suffix=".sol", delete=False) as f:
        f.write(" ".join(str(x) for x in cover) + "\n")
        tmp = f.name
    try:
        cost, err = scoring.check_scp(inst_path, tmp)
    finally:
        os.unlink(tmp)
    if err is not None:
        raise AssertionError(f"{inst_path}: invalid cover {err}")
    return cost


def stem(name):
    return name[:-len(".txt")]


class SetConsistencyTest(unittest.TestCase):
    def test_split_sizes(self):
        self.assertEqual(len(SPLIT), 87)
        self.assertEqual(len(HIDDEN), 26)
        self.assertEqual(len(PUBLIC), 48)
        self.assertEqual(len(NEITHER), 13)
        # dilution bucket: excluded from environment inventory, scoring reference, public reference, and environment covers
        with open(os.path.join(TASK, "environment",
                               "public-instances.txt")) as f:
            env_names = {x.strip() for x in f if x.strip()}
        self.assertFalse(env_names & set(NEITHER))
        pubref = json.load(open(os.path.join(
            TASK, "environment", "app", "public_reference.json")))["instances"]
        self.assertFalse(set(pubref) & set(NEITHER))
        self.assertFalse(set(REF) & set(NEITHER))
        self.assertFalse(set(CMAP) & set(NEITHER))
        sols = os.listdir(os.path.join(TASK, "environment", "app", "solutions"))
        self.assertFalse({s[:-len(".sol")] + ".txt" for s in sols} & set(NEITHER))

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
                         sorted(c for c in CMAP
                                if stem(CMAP[c]["official"])
                                in {stem2 for stem2 in
                                    (e["instance"] for e in man.values())}))
        for h, e in man.items():
            with open(os.path.join(TRANS_DIR, e["codename"]), "rb") as f:
                self.assertEqual(tf.oracle_hash(f.read()), h,
                                 f"{e['codename']}: oracle key does not match instance bytes")
        missing = json.load(open(os.path.join(SOLS_DIR, "WITNESS-MISSING.json")))
        self.assertEqual(sorted(missing["witness_missing"]),
                         sorted(set(HIDDEN) -
                                {e["instance"] + ".txt" for e in man.values()}))

    def test_public_side_keys(self):
        with open(os.path.join(TASK, "environment", "public-instances.txt")) as f:
            env_names = sorted(x.strip() for x in f if x.strip())
        self.assertEqual(env_names, PUBLIC)
        pubref = json.load(open(os.path.join(
            TASK, "environment", "app", "public_reference.json")))["instances"]
        self.assertEqual(sorted(pubref), PUBLIC)
        # only public-side solutions remain in environment solutions/
        sols = sorted(os.listdir(os.path.join(TASK, "environment", "app",
                                              "solutions")))
        for s in sols:
            self.assertIn(s[:-len(".sol")] + ".txt", PUBLIC,
                          f"{s}: covers for hidden source instances must not remain in the environment")


class RoundtripTest(unittest.TestCase):
    """Round trip and scored-side bytes equal apply output (the transformation was constructed correctly)."""

    def test_apply_matches_judged_bytes(self):
        for name in HIDDEN:
            with self.subTest(inst=name):
                st = stem(name)
                m, n, costs, rows = tf.load_instance(
                    os.path.join(OFFICIAL_DIR, name))
                nc, nr, cp, rp = tf.transform_instance(
                    st, m, n, costs, rows, suffix=OVERRIDES.get(st, ""))
                applied = tf.serialize(m, n, nc, nr)
                with open(os.path.join(TRANS_DIR, OFF2CODE[name]), "rb") as f:
                    self.assertEqual(applied, f.read(),
                                     f"{name}: locally applied output differs from scored-side bytes")
                self.assertEqual(tf.params_hash(cp, rp),
                                 CMAP[OFF2CODE[name]]["transform_params_sha256"])

    def test_invert_roundtrip(self):
        for name in HIDDEN:
            with self.subTest(inst=name):
                st = stem(name)
                m, n, costs, rows = tf.load_instance(
                    os.path.join(OFFICIAL_DIR, name))
                nc, nr, _, _ = tf.transform_instance(
                    st, m, n, costs, rows, suffix=OVERRIDES.get(st, ""))
                rc, rr, _, _ = tf.invert_instance(
                    st, m, n, nc, nr, suffix=OVERRIDES.get(st, ""))
                self.assertEqual(tf.canonical(m, n, costs, rows),
                                 tf.canonical(m, n, rc, rr),
                                 f"{name}: invert(apply(x)) canonical != x")
                # token-by-token inversion must match for official files with ascending values on each line
                if all(r == sorted(r) for r in rows):
                    with open(os.path.join(OFFICIAL_DIR, name), "rb") as f:
                        orig = f.read().split()
                    self.assertEqual(
                        tf.serialize(m, n, rc, rr).split(), orig,
                        f"{name}: token-by-token inversion failed for official file with ascending values")
                # Canonical fixed point
                nc2, nr2, _, _ = tf.transform_instance(
                    st, m, n, rc, rr, suffix=OVERRIDES.get(st, ""))
                self.assertEqual(tf.serialize(m, n, nc, nr),
                                 tf.serialize(m, n, nc2, nr2))


class ValueAndAnchorTest(unittest.TestCase):
    """Solution value is preserved and K reused (recompute the 20 keys with covers using the actual check_scp)."""

    def _official_cover(self, name):
        with open(os.path.join(SOLS_DIR, stem(name) + ".sol")) as f:
            return [int(x) for x in f.read().split()]

    def test_solution_value_invariant_and_k_carried(self):
        covered = [n for n in HIDDEN
                   if os.path.isfile(os.path.join(SOLS_DIR, stem(n) + ".sol"))]
        self.assertEqual(len(covered), 20)
        for name in covered:
            with self.subTest(inst=name):
                code = OFF2CODE[name]
                st = stem(name)
                m, n, costs, rows = tf.load_instance(
                    os.path.join(OFFICIAL_DIR, name))
                _, _, cp, _ = tf.transform_instance(
                    st, m, n, costs, rows, suffix=OVERRIDES.get(st, ""))
                cover = self._official_cover(name)
                k_ref = REF[code]["K"]
                cost_off = cost_of_cover(os.path.join(OFFICIAL_DIR, name), cover)
                self.assertEqual(cost_off, k_ref,
                                 f"{name}: recomputed official cover {cost_off} != K {k_ref}")
                mapped = tf.rewrite_cover(cover, cp)
                cost_tr = cost_of_cover(os.path.join(TRANS_DIR, code), mapped)
                self.assertEqual(cost_tr, k_ref,
                                 f"{code} ({name}): recomputed mapped cover {cost_tr} != K {k_ref}")

    def test_oracle_covers_recompute_to_k(self):
        oracle = os.path.join(TASK, "solution", "precomputed")
        man = json.load(open(os.path.join(oracle, "manifest.json")))
        self.assertEqual(len(man), 20)
        for h, e in man.items():
            with self.subTest(inst=e["codename"]):
                with open(os.path.join(oracle, e["sol"])) as f:
                    cover = [int(x) for x in f.read().split()]
                cost = cost_of_cover(os.path.join(TRANS_DIR, e["codename"]), cover)
                self.assertEqual(cost, REF[e["codename"]]["K"],
                                 f"{e['codename']}: oracle recomputation {cost} != K")

    def test_anchors_match_reference(self):
        anchors = json.load(open(os.path.join(HERE, "anchors.json")))
        for code in REF:
            self.assertEqual(anchors["K"][code], REF[code]["K"], f"{code}: K anchor drift")
            self.assertEqual(anchors["B"][code], REF[code]["B"], f"{code}: B anchor drift")


if __name__ == "__main__":
    unittest.main(verbosity=2)
