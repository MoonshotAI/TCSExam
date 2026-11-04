#!/usr/bin/env python3
"""Mathematical validation of the ahc058-atcoder form2 structure-preserving transformation (the three checks in form2-conversion-recipes.md).

  1. Round trip and deterministic replay: for the 45 hidden instances in split.json,
     applying the transformation into a temporary directory must reproduce the
     delivered bytes in tests/instances/. Inverting via the manifest must recover
     parsed content equal to the generated originals in tests/instances-library/
     (semantic equality: files are whitespace-separated token streams, and emit
     normalizes their layout).
  2. Solution value is preserved: for each hidden instance, use its stored action
     sequence (solution/precomputed/<source-name>.out, a pilot44 replay at the
     measured K level). Recompute the final score on both original and transformed
     instances using simulate/check_ahc in tests/scoring.py (a pure checker
     implementation of the official AHC058 compute_score; no solver runs). Scores
     must match exactly.
  3. Spot-check K reuse: each hidden key's K in tests/reference-hidden.json equals
     the corresponding value in tests/reference.json (the 50 generated-instance
     references and async anchor source) under the manifest mapping, confirming
     reuse by isomorphism. B is currently a placeholder based on the source value
     before transformation; it is replaced during batch remeasurement in the same
     scoring environment (see tests/calibration/measure-manifest.json). This
     assertion only requires B to be numeric and retain the B<K relation.

Run with `python3 tests/test_transform.py` (unittest)."""
import json
import os
import shutil
import sys
import tempfile
import unittest

TESTS = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(TESTS)
sys.path.insert(0, TESTS)

import scoring  # noqa: E402
import transform  # noqa: E402


class TransformTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(TESTS, "transform_manifest.json")) as f:
            cls.manifest = json.load(f)["instances"]
        with open(os.path.join(TESTS, "split.json")) as f:
            cls.split = json.load(f)

    def test_manifest_covers_exactly_the_hidden_set(self):
        hidden = sorted(fn[:-4] for fn, side in self.split.items()
                        if side == "hidden")
        self.assertEqual(sorted(rec["official"] for rec in
                                self.manifest.values()), hidden)
        self.assertEqual(len(self.manifest), 45)

    def test_apply_is_deterministic_and_roundtrips(self):
        tmp = tempfile.mkdtemp(prefix="ahc058-transform-")
        try:
            out_dir = os.path.join(tmp, "instances")
            args = type("A", (), {
                "instances_dir": os.path.join(TESTS, "instances-library"),
                "out_dir": out_dir,
                "manifest": os.path.join(tmp, "manifest.json")})()
            transform.cmd_apply(args)
            for new_name, rec in sorted(self.manifest.items()):
                stem = rec["official"]
                with open(os.path.join(out_dir, new_name + ".txt"), "rb") as f:
                    regenerated = f.read()
                with open(os.path.join(TESTS, "instances",
                                       new_name + ".txt"), "rb") as f:
                    delivered = f.read()
                self.assertEqual(regenerated, delivered,
                                 f"{new_name}: apply is nondeterministic or delivered bytes have drifted")
                inst_t = transform.load_instance(os.path.join(
                    TESTS, "instances", new_name + ".txt"))
                inst_o = transform.load_instance(os.path.join(
                    TESTS, "instances-library", stem + ".txt"))
                restored = transform.invert_instance(inst_t, rec["perm"])
                self.assertEqual(restored, inst_o,
                                 f"{new_name} ({stem}): round-trip mismatch")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_solution_value_invariant(self):
        sol_dir = os.path.join(TASK, "solution", "precomputed")
        tmp = tempfile.mkdtemp(prefix="ahc058-transform-sol-")
        try:
            args = type("A", (), {
                "instances_dir": os.path.join(TESTS, "instances"),
                "sol_dir": sol_dir,
                "manifest": os.path.join(TESTS, "transform_manifest.json"),
                "out_dir": tmp})()
            transform.cmd_rewrite_solutions(args)
            for new_name, rec in sorted(self.manifest.items()):
                stem = rec["official"]
                orig_inst = os.path.join(TESTS, "instances-library",
                                         stem + ".txt")
                orig_sol = os.path.join(sol_dir, stem + ".out")
                self.assertTrue(os.path.isfile(orig_sol),
                                f"{stem}: stored action sequence missing")
                score_o, err = scoring.check_ahc(orig_inst, orig_sol)
                self.assertIsNone(err, f"{stem}: original action sequence is invalid: {err}")
                trans_inst = os.path.join(TESTS, "instances",
                                          new_name + ".txt")
                trans_sol = os.path.join(tmp, new_name + ".out")
                score_t, err = scoring.check_ahc(trans_inst, trans_sol)
                self.assertIsNone(err,
                                  f"{new_name} ({stem}): transformed action sequence is invalid: {err}")
                self.assertEqual(score_o, score_t,
                                 f"{new_name} ({stem}): solution value changed "
                                 f"{score_o} != {score_t}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_k_inherited_by_isomorphism(self):
        with open(os.path.join(TESTS, "reference-hidden.json")) as f:
            hidden_ref = json.load(f)["instances"]
        with open(os.path.join(TESTS, "reference.json")) as f:
            lib_ref = json.load(f)["instances"]
        self.assertEqual(sorted(hidden_ref),
                         sorted(n + ".txt" for n in self.manifest))
        for new_name, rec in sorted(self.manifest.items()):
            stem = rec["official"]
            ent = hidden_ref[new_name + ".txt"]
            lib_ent = lib_ref[stem + ".txt"]
            self.assertEqual(ent["K"], lib_ent["K"],
                             f"{new_name} ({stem}): K was not reused by isomorphism")
            self.assertIsInstance(ent["B"], int,
                                  f"{new_name} ({stem}): B placeholder is not numeric")
            self.assertLess(ent["B"], ent["K"],
                            f"{new_name} ({stem}): scored instance should retain B<K")


if __name__ == "__main__":
    unittest.main(verbosity=2)
