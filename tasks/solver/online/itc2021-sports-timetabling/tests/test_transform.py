#!/usr/bin/env python3
"""Mathematical validation of the itc2021-sports-timetabling form2 structure-preserving transformation (the three checks in form2-conversion-recipes.md).

  1. Round trip and deterministic replay: for the 16 hidden instances in split.json,
     applying the transformation into a temporary directory must reproduce the
     delivered bytes in tests/instances/. Inverting via the manifest (restoring
     InstanceName) must reproduce the official originals byte for byte from
     tests/instances-library/.
  2. Solution value is preserved: for each hidden instance, use its stored schedule
     (solution/precomputed/<official-name>.xml, the best known schedule backed up by
     official RobinX). Validate the rewritten schedule on original and transformed
     instances with official RobinX Validator 2.0 (tests/validator-bin/RobinX, the
     same binary used in scoring). Both must have zero hard violations and exactly
     the same soft penalty. The validator checks solutions; it is not a solver, and
     this test runs no solver.
  3. Spot-check K reuse: for each hidden key, K in tests/reference.json equals the
     corresponding official-set value in tests/reference-library.json under the
     manifest mapping, confirming reuse by isomorphism. B is currently a placeholder
     based on the source instance before transformation; it is replaced during batch
     remeasurement in the same scoring environment and pool protocol (see
     tests/calibration/measure-manifest.json). This assertion only requires B to be
     numeric or null (recorded when the baseline did not solve the instance), and
     numeric keys to retain the B>K relation.

Run with `python3 tests/test_transform.py` (unittest)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

TESTS = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(TESTS)
sys.path.insert(0, TESTS)

import transform  # noqa: E402

VALIDATOR = os.path.join(TESTS, "validator-bin", "RobinX")


def validated_cost(instance_path, sol_path):
    """Official validator: returns (hard, soft)."""
    import re
    p = subprocess.run([VALIDATOR, "-i", instance_path, "-s", sol_path],
                       capture_output=True, text=True, timeout=300)
    m = re.search(r"Objective:\s+(\d+)\s+(\d+)", p.stdout)
    if not m:
        raise AssertionError(f"validator failed on {instance_path} "
                             f"{sol_path}: {(p.stdout or '')[-300:]}")
    return int(m.group(1)), int(m.group(2))


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
        self.assertEqual(len(self.manifest), 16)

    def test_apply_is_deterministic_and_roundtrips(self):
        tmp = tempfile.mkdtemp(prefix="itc2021-transform-")
        try:
            out_dir = os.path.join(tmp, "instances")
            args = type("A", (), {
                "instances_dir": os.path.join(TESTS, "instances-library"),
                "out_dir": out_dir,
                "manifest": os.path.join(tmp, "manifest.json")})()
            transform.cmd_apply(args)
            for new_name, rec in sorted(self.manifest.items()):
                stem = rec["official"]
                with open(os.path.join(out_dir, new_name + ".xml"), "rb") as f:
                    regenerated = f.read()
                with open(os.path.join(TESTS, "instances",
                                       new_name + ".xml"), "rb") as f:
                    delivered = f.read()
                self.assertEqual(regenerated, delivered,
                                 f"{new_name}: apply is nondeterministic or delivered bytes have drifted")
                with open(os.path.join(TESTS, "instances",
                                       new_name + ".xml")) as f:
                    text_t = f.read()
                restored = transform.invert_text(
                    text_t, rec["perm"], rec["orig_instance_name"])
                with open(os.path.join(TESTS, "instances-library",
                                       stem + ".xml")) as f:
                    orig = f.read()
                self.assertEqual(restored, orig,
                                 f"{new_name} ({stem}): round-trip mismatch")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_solution_value_invariant(self):
        sol_dir = os.path.join(TASK, "solution", "precomputed")
        tmp = tempfile.mkdtemp(prefix="itc2021-transform-sol-")
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
                                         stem + ".xml")
                orig_sol = os.path.join(sol_dir, stem + ".xml")
                self.assertTrue(os.path.isfile(orig_sol),
                                f"{stem}: stored schedule missing")
                hard_o, soft_o = validated_cost(orig_inst, orig_sol)
                self.assertEqual(hard_o, 0,
                                 f"{stem}: original schedule is invalid (hard={hard_o})")
                trans_inst = os.path.join(TESTS, "instances",
                                          new_name + ".xml")
                trans_sol = os.path.join(tmp, new_name + ".xml")
                hard_t, soft_t = validated_cost(trans_inst, trans_sol)
                self.assertEqual(hard_t, 0,
                                 f"{new_name} ({stem}): transformed schedule is invalid "
                                 f"(hard={hard_t})")
                self.assertEqual(soft_o, soft_t,
                                 f"{new_name} ({stem}): solution value changed "
                                 f"{soft_o} != {soft_t}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_k_inherited_by_isomorphism(self):
        with open(os.path.join(TESTS, "reference.json")) as f:
            hidden_ref = json.load(f)["instances"]
        with open(os.path.join(TESTS, "reference-library.json")) as f:
            lib_ref = json.load(f)["instances"]
        self.assertEqual(sorted(hidden_ref),
                         sorted(n + ".xml" for n in self.manifest))
        for new_name, rec in sorted(self.manifest.items()):
            stem = rec["official"]
            ent = hidden_ref[new_name + ".xml"]
            lib_ent = lib_ref[stem + ".xml"]
            self.assertEqual(ent["K"], lib_ent["K"],
                             f"{new_name} ({stem}): K was not reused by isomorphism")
            if ent["B"] is not None:
                self.assertIsInstance(ent["B"], int,
                                      f"{new_name} ({stem}): B placeholder is not numeric")
                if lib_ent["B"] is not None and lib_ent["B"] > lib_ent["K"]:
                    self.assertGreater(ent["B"], ent["K"],
                                       f"{new_name} ({stem}): scored instance should retain B>K")


if __name__ == "__main__":
    unittest.main(verbosity=2)
