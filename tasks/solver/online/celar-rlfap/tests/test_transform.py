#!/usr/bin/env python3
"""Mathematical validation of the celar-rlfap form2 structure-preserving transformation (the three checks in form2-conversion-recipes.md).

  1. Round trip and deterministic replay: for the 8 hidden instances in split.json,
     applying the transformation into a temporary directory must reproduce the
     delivered bytes in tests/instances/. Inverting via the manifest must recover
     the token stream equal to the official source bytes in tests/instances-library/.
  2. Solution value is preserved: for each hidden instance, use its stored solution
     (solution/precomputed/<official-name>.sol, the witness solution used by the
     oracle stub). Recompute the objective on the original instance using
     check_solution from tests/scoring.py, then transform both the instance and
     solution and recompute. The values must match exactly; this is validation only
     and runs no solver.
  3. Spot-check K reuse: for each hidden key, K in tests/reference.json equals the
     corresponding official-set value in tests/reference-library.json under the
     manifest mapping, confirming reuse by isomorphism. B is currently a placeholder
     based on the source instance before transformation; it is replaced during batch
     remeasurement in the same scoring environment (see
     tests/calibration/measure-manifest.json). This assertion only requires B to be
     numeric and scored keys to retain the B>K relation.

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
        self.assertEqual(len(self.manifest), 8)

    def test_apply_is_deterministic_and_roundtrips(self):
        tmp = tempfile.mkdtemp(prefix="celar-transform-")
        try:
            out_dir = os.path.join(tmp, "instances")
            args = type("A", (), {
                "instances_dir": os.path.join(TESTS, "instances-library"),
                "out_dir": out_dir,
                "manifest": os.path.join(tmp, "manifest.json")})()
            transform.cmd_apply(args)
            for new_name, rec in sorted(self.manifest.items()):
                stem = rec["official"]
                with open(os.path.join(out_dir, new_name + ".dzn"), "rb") as f:
                    regenerated = f.read()
                with open(os.path.join(TESTS, "instances",
                                       new_name + ".dzn"), "rb") as f:
                    delivered = f.read()
                self.assertEqual(regenerated, delivered,
                                 f"{new_name}: apply is nondeterministic or delivered bytes have drifted")
                d_t = transform.load_dzn(os.path.join(
                    TESTS, "instances", new_name + ".dzn"))
                restored = transform.invert_instance(
                    d_t, [None] + rec["var_permutation_new_from_old"],
                    rec["hard_order_new_from_old"],
                    rec["soft_order_new_from_old"])
                with open(os.path.join(TESTS, "instances-library",
                                       stem + ".dzn"), "rb") as f:
                    orig = f.read()
                self.assertEqual(transform.serialize(restored).split(),
                                 orig.split(),
                                 f"{new_name} ({stem}): round-trip mismatch")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_solution_value_invariant(self):
        sol_dir = os.path.join(TASK, "solution", "precomputed")
        tmp = tempfile.mkdtemp(prefix="celar-transform-sol-")
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
                                         stem + ".dzn")
                orig_sol = os.path.join(sol_dir, stem + ".sol")
                self.assertTrue(os.path.isfile(orig_sol),
                                f"{stem}: stored solution missing")
                obj_orig, err = scoring.check_solution(orig_inst, orig_sol)
                self.assertIsNone(err, f"{stem}: original solution is invalid: {err}")
                trans_inst = os.path.join(TESTS, "instances",
                                          new_name + ".dzn")
                trans_sol = os.path.join(tmp, new_name + ".sol")
                obj_trans, err = scoring.check_solution(trans_inst, trans_sol)
                self.assertIsNone(err,
                                  f"{new_name} ({stem}): transformed solution is invalid: {err}")
                self.assertEqual(obj_orig, obj_trans,
                                 f"{new_name} ({stem}): solution value changed "
                                 f"{obj_orig} != {obj_trans}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_k_inherited_by_isomorphism(self):
        with open(os.path.join(TESTS, "reference.json")) as f:
            hidden_ref = json.load(f)["instances"]
        with open(os.path.join(TESTS, "reference-library.json")) as f:
            lib_ref = json.load(f)["instances"]
        self.assertEqual(sorted(hidden_ref),
                         sorted(n + ".dzn" for n in self.manifest))
        for new_name, rec in sorted(self.manifest.items()):
            stem = rec["official"]
            ent = hidden_ref[new_name + ".dzn"]
            lib_ent = lib_ref[stem + ".dzn"]
            self.assertEqual(ent["K"], lib_ent["K"],
                             f"{new_name} ({stem}): K was not reused by isomorphism")
            self.assertIsInstance(ent["B"], int,
                                  f"{new_name} ({stem}): B placeholder is not numeric")
            if lib_ent["B"] > lib_ent["K"]:
                self.assertGreater(ent["B"], ent["K"],
                                   f"{new_name} ({stem}): scored instance should retain B>K")


if __name__ == "__main__":
    unittest.main(verbosity=2)
