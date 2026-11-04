#!/usr/bin/env python3
"""Mathematical validation of the curriculum-itc2007 form2 structure-preserving transformation (the three checks in form2-conversion-recipes.md).

  1. Round trip and deterministic replay: for the 6 hidden instances in split.json,
     applying the transformation into a temporary directory must reproduce the
     delivered bytes in tests/instances/. Inverting via the manifest must recover
     parsed content semantically equal to the official originals in
     tests/instances-library/ (header plus normalized sets per section; trailing
     spaces and line ordering in the source files are excluded from comparison).
  2. Solution value is preserved: for each hidden instance, use its stored timetable
     (solution/precomputed/<official-name>.sol, the best-known timetable from OptHub).
     Validate the rewritten timetable on both the original and transformed instances
     with the official ITC 2007 Track 3 validator (compile environment/app/validator.cc,
     the same binary used in scoring). Both must have zero hard-constraint violations
     and exactly the same Total Cost. The validator checks solutions; it is not a
     solver, and this test runs no solver.
  3. Spot-check K reuse: for each hidden key, K in tests/reference.json equals the
     corresponding official-set reference in tests/reference-library.json under the
     manifest mapping, confirming reuse by isomorphism. B is currently a placeholder
     based on the source instance before transformation; it is replaced during batch
     remeasurement in the same scoring environment (see
     tests/calibration/measure-manifest.json). This assertion only requires B to be
     numeric and each scored key to retain the B>K relation.

Run with `python3 tests/test_transform.py` (unittest; requires local g++)."""
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

VALIDATOR_BIN = os.path.join(tempfile.gettempdir(), "ctt-form2-test-validator")


def build_validator():
    if os.path.exists(VALIDATOR_BIN):
        return
    subprocess.run(
        ["g++", "-O2", "-o", VALIDATOR_BIN,
         os.path.join(TASK, "environment", "app", "validator.cc")],
        check=True)


def validated_cost(instance_path, sol_path):
    """Official validator: returns (hard_violations_total, total_cost)."""
    import re
    p = subprocess.run([VALIDATOR_BIN, instance_path, sol_path],
                       capture_output=True, text=True, timeout=120)
    out = p.stdout or ""
    hard = {m.group(1): int(m.group(2)) for m in re.finditer(
        r"Violations of (Lectures|Conflicts|Availability|RoomOccupation)"
        r" \(hard\) : (\d+)", out)}
    m = re.search(r"Total Cost = (\d+)", out)
    if p.returncode != 0 or len(hard) != 4 or not m:
        raise AssertionError(f"validator failed on {instance_path} "
                             f"{sol_path}: rc={p.returncode} {out[-300:]}")
    return sum(hard.values()), int(m.group(1))


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
        self.assertEqual(len(self.manifest), 6)

    def test_apply_is_deterministic_and_roundtrips(self):
        tmp = tempfile.mkdtemp(prefix="ctt-transform-")
        try:
            out_dir = os.path.join(tmp, "instances")
            args = type("A", (), {
                "instances_dir": os.path.join(TESTS, "instances-library"),
                "out_dir": out_dir,
                "manifest": os.path.join(tmp, "manifest.json")})()
            transform.cmd_apply(args)
            for new_name, rec in sorted(self.manifest.items()):
                stem = rec["official"]
                with open(os.path.join(out_dir, new_name + ".ctt"), "rb") as f:
                    regenerated = f.read()
                with open(os.path.join(TESTS, "instances",
                                       new_name + ".ctt"), "rb") as f:
                    delivered = f.read()
                self.assertEqual(regenerated, delivered,
                                 f"{new_name}: apply is nondeterministic or delivered bytes have drifted")
                inst_t = transform.load_ctt(os.path.join(
                    TESTS, "instances", new_name + ".ctt"))
                inst_o = transform.load_ctt(os.path.join(
                    TESTS, "instances-library", stem + ".ctt"))
                maps = {k: rec[k] for k in (
                    "course_map", "room_map", "teacher_map",
                    "curriculum_map")}
                r = transform.invert_instance(inst_t, maps,
                                              rec["orig_name_header"])
                self.assertEqual(r["header"], inst_o["header"],
                                 f"{new_name} ({stem}): header round trip mismatch")
                for sec in ("courses", "rooms", "unavail"):
                    self.assertEqual({tuple(x) for x in r[sec]},
                                     {tuple(x) for x in inst_o[sec]},
                                     f"{new_name} ({stem}): {sec} round-trip mismatch")
                norm = lambda qs: {(q[0], q[1], frozenset(q[2:])) for q in qs}
                self.assertEqual(norm(r["curricula"]),
                                 norm(inst_o["curricula"]),
                                 f"{new_name} ({stem}): curricula round trip mismatch")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_solution_value_invariant(self):
        build_validator()
        sol_dir = os.path.join(TASK, "solution", "precomputed")
        tmp = tempfile.mkdtemp(prefix="ctt-transform-sol-")
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
                                         stem + ".ctt")
                orig_sol = os.path.join(sol_dir, stem + ".sol")
                self.assertTrue(os.path.isfile(orig_sol),
                                f"{stem}: stored timetable missing")
                hard_o, cost_o = validated_cost(orig_inst, orig_sol)
                self.assertEqual(hard_o, 0,
                                 f"{stem}: original timetable is invalid (hard={hard_o})")
                trans_inst = os.path.join(TESTS, "instances",
                                          new_name + ".ctt")
                trans_sol = os.path.join(tmp, new_name + ".sol")
                hard_t, cost_t = validated_cost(trans_inst, trans_sol)
                self.assertEqual(hard_t, 0,
                                 f"{new_name} ({stem}): transformed timetable is invalid "
                                 f"(hard={hard_t})")
                self.assertEqual(cost_o, cost_t,
                                 f"{new_name} ({stem}): solution value changed "
                                 f"{cost_o} != {cost_t}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_k_inherited_by_isomorphism(self):
        with open(os.path.join(TESTS, "reference.json")) as f:
            hidden_ref = json.load(f)["instances"]
        with open(os.path.join(TESTS, "reference-library.json")) as f:
            lib_ref = json.load(f)["instances"]
        self.assertEqual(sorted(hidden_ref),
                         sorted(n + ".ctt" for n in self.manifest))
        for new_name, rec in sorted(self.manifest.items()):
            stem = rec["official"]
            ent = hidden_ref[new_name + ".ctt"]
            lib_ent = lib_ref[stem + ".ctt"]
            self.assertEqual(ent["K"], lib_ent["K"],
                             f"{new_name} ({stem}): K was not reused by isomorphism")
            self.assertIsInstance(ent["B"], int,
                                  f"{new_name} ({stem}): B placeholder is not numeric")
            if lib_ent["B"] > lib_ent["K"]:
                self.assertGreater(ent["B"], ent["K"],
                                   f"{new_name} ({stem}): scored instance should retain B>K")


if __name__ == "__main__":
    unittest.main(verbosity=2)
