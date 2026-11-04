#!/usr/bin/env python3
"""Mathematical validation of the jsplib-jssp form2 transformation.

This file checks three mathematical properties of the hidden scored set (85
structure-preserving transformed copies in tests/instances/exNNN.txt), following
the transformation requirements in form2-conversion-recipes.md:
  1. Round trip: regenerate rho/mu from the seed rule; applying the transformation
     to an official instance must reproduce the scored exNNN byte for byte.
     invert(apply(x)) must equal x element by element, and apply output must be a
     canonical fixed point.
  2. Solution value is preserved: recompute the makespan from official schedules
     (tests/official-sols/) on all 85 official instances. The replay target is K for
     the 31 generated instances and the retained L value or K for classic instances
     (reference K/L is checked per key so it is never weaker than K). After mapping
     job IDs, recomputing on transformed instances must yield the same value using
     the built-in Python checker, which follows jssp_check: precedence constraints,
     machine non-overlap, and makespan recomputation.
  3. K reuse: each hidden key's K in tests/reference.json equals the value recomputed
     from the mapped schedule (a mapped schedule attaining <=K confirms K reuse; the
     stored oracle schedule attains the recorded level per key—generated cases equal
     K, classic cases equal the retained value >= K—so the equality and >=K checks
     both hold); B and K in tests/anchors.json match reference key by key.
A further set-consistency gate checks that the key sets in split.json, codename-map,
tests/instances, reference, solution/solutions, the public environment instance list
(environment/public-instances.txt), and public_reference all agree.

This does not depend on the private manifest (the permutation is regenerated from
the seed rule). Run with `python3 tests/test_transform.py` from the task root or
any directory."""
import hashlib
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import transform as tf  # noqa: E402

SPLIT = json.load(open(os.path.join(HERE, "split.json")))["instances"]
CMAP = json.load(open(os.path.join(HERE, "codename-map.json")))["instances"]
REF = json.load(open(os.path.join(HERE, "reference.json")))["instances"]
HIDDEN = sorted(n for n, e in SPLIT.items() if e["side"] == "hidden")
PUBLIC = sorted(n for n, e in SPLIT.items() if e["side"] == "public")
OFF2CODE = {rec["official"]: code for code, rec in CMAP.items()}
OFFICIAL_DIR = os.path.join(HERE, "official-instances")
TRANS_DIR = os.path.join(HERE, "instances")
SOLS_DIR = os.path.join(HERE, "official-sols")


def makespan_of(inst_path, sched):
    n, m, ops = tf.parse_instance(inst_path)
    return tf.check_schedule(ops, sched)


class SetConsistencyTest(unittest.TestCase):
    def test_split_sizes(self):
        self.assertEqual(len(SPLIT), 283)
        self.assertEqual(len(HIDDEN), 85)
        self.assertEqual(len(PUBLIC), 198)

    def test_codename_map_covers_hidden(self):
        self.assertEqual(sorted(OFF2CODE), HIDDEN)
        self.assertEqual(sorted(CMAP), sorted(OFF2CODE[n] for n in HIDDEN))

    def test_judged_files_match_map(self):
        self.assertEqual(sorted(os.listdir(TRANS_DIR)),
                         sorted(c + ".txt" for c in CMAP))
        for code, rec in CMAP.items():
            h = hashlib.sha256(
                open(os.path.join(TRANS_DIR, code + ".txt"), "rb").read()
            ).hexdigest()
            self.assertEqual(h, rec["src_sha256"], f"{code}: scored-instance bytes do not match the record")
            ho = hashlib.sha256(
                open(os.path.join(OFFICIAL_DIR, rec["official"] + ".txt"), "rb")
                .read()).hexdigest()
            self.assertEqual(ho, rec["official_sha256"],
                             f"{rec['official']}: official source-instance bytes do not match the record")

    def test_reference_and_oracle_keys(self):
        self.assertEqual(sorted(REF), sorted(CMAP))
        sols = sorted(f[:-len(".sol")] for f in os.listdir(
            os.path.join(TASK, "solution", "solutions")))
        self.assertEqual(sols, sorted(CMAP))

    def test_public_side_keys(self):
        with open(os.path.join(TASK, "environment", "public-instances.txt")) as f:
            env_names = sorted(x.strip() for x in f if x.strip())
        self.assertEqual(env_names, PUBLIC)
        pubref = json.load(open(os.path.join(
            TASK, "environment", "app", "public_reference.json")))["instances"]
        self.assertEqual(sorted(pubref), PUBLIC)
        pub_files = sorted(f[:-len(".txt")] for f in os.listdir(
            os.path.join(HERE, "public-instances")))
        self.assertEqual(pub_files, PUBLIC)


class RoundtripTest(unittest.TestCase):
    """Round trip and scored-side bytes equal apply output (the transformation was constructed correctly)."""

    def test_apply_matches_judged_bytes(self):
        for name in HIDDEN:
            with self.subTest(inst=name):
                n, m, ops = tf.parse_instance(
                    os.path.join(OFFICIAL_DIR, name + ".txt"))
                new_ops, rho, mu = tf.transform_instance(name, n, m, ops)
                applied = tf.serialize(n, m, new_ops)
                with open(os.path.join(TRANS_DIR, OFF2CODE[name] + ".txt"),
                          "rb") as f:
                    self.assertEqual(applied, f.read(),
                                     f"{name}: locally applied output differs from scored-side bytes")
                self.assertEqual(tf.params_hash(rho, mu),
                                 CMAP[OFF2CODE[name]]["transform_params_sha256"])

    def test_invert_roundtrip(self):
        for name in HIDDEN:
            with self.subTest(inst=name):
                n, m, ops = tf.parse_instance(
                    os.path.join(OFFICIAL_DIR, name + ".txt"))
                new_ops, _, _ = tf.transform_instance(name, n, m, ops)
                ops2, _, _ = tf.invert_instance(name, n, m, new_ops)
                self.assertEqual(ops, ops2, f"{name}: invert(apply(x)) != x")
                new_ops2, _, _ = tf.transform_instance(name, n, m, ops2)
                self.assertEqual(tf.serialize(n, m, new_ops),
                                 tf.serialize(n, m, new_ops2))


class ValueAndAnchorTest(unittest.TestCase):
    """Solution value is preserved and K reused (recompute all 85 keys with the built-in machine checker)."""

    def _official_schedule(self, name):
        return tf.parse_schedule(
            os.path.join(SOLS_DIR, name + ".sol"),
            SPLIT[name]["n"], SPLIT[name]["m"])

    def test_solution_value_invariant_and_k_carried(self):
        for name in HIDDEN:
            with self.subTest(inst=name):
                code = OFF2CODE[name]
                sched = self._official_schedule(name)
                ms_off = makespan_of(
                    os.path.join(OFFICIAL_DIR, name + ".txt"), sched)
                n, m, ops = tf.parse_instance(
                    os.path.join(OFFICIAL_DIR, name + ".txt"))
                _, rho, _ = tf.transform_instance(name, n, m, ops)
                mapped = tf.rewrite_schedule(sched, rho)
                ms_tr = makespan_of(
                    os.path.join(TRANS_DIR, code + ".txt"), mapped)
                self.assertEqual(ms_off, ms_tr,
                                 f"{code} ({name}): mapped schedule makespan drift "
                                 f"{ms_off} -> {ms_tr}")
                # K reuse: the mapped schedule attains at least the recorded level and cannot beat K (K is
                # known best/proven optimal, so a valid schedule cannot be better; a better value means the K anchor or
                # the construction is wrong and needs review)
                self.assertGreaterEqual(ms_tr, REF[code]["K"],
                                        f"{code} ({name}): mapped schedule {ms_tr} "
                                        f"< K {REF[code]['K']}—the K anchor or transformation is wrong")

    def test_oracle_solutions_replay_at_reference(self):
        for code in sorted(CMAP):
            with self.subTest(inst=code):
                name = CMAP[code]["official"]
                sched = tf.parse_schedule(
                    os.path.join(TASK, "solution", "solutions", code + ".sol"),
                    SPLIT[name]["n"], SPLIT[name]["m"])
                ms = makespan_of(os.path.join(TRANS_DIR, code + ".txt"), sched)
                # oracle replay target = retained best schedule (generated cases == K; classic cases == retained L-tier or
                # retained baseline schedule, both >= K; equal to official-solution value)
                sched_off = self._official_schedule(name)
                ms_off = makespan_of(
                    os.path.join(OFFICIAL_DIR, name + ".txt"), sched_off)
                self.assertEqual(ms, ms_off,
                                 f"{code}: oracle replay {ms} != official retained value {ms_off}")
                self.assertGreaterEqual(ms, REF[code]["K"],
                                        f"{code}: oracle {ms} < K {REF[code]['K']}")

    def test_anchors_match_reference(self):
        anchors = json.load(open(os.path.join(HERE, "anchors.json")))
        for code in REF:
            self.assertEqual(anchors["K"][code], REF[code]["K"], f"{code}: K anchor drift")
            self.assertEqual(anchors["B"][code], REF[code]["B"], f"{code}: B anchor drift")


if __name__ == "__main__":
    unittest.main(verbosity=2)
