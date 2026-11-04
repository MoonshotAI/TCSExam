#!/usr/bin/env python3
"""ahc058-atcoder oracle-stub self-check (codified after the 260920 key-name incident; replaying the stub is not solver execution).

Two gates prevent incidents where the stub and manifest use different key names
(observed in the 260920 oracle batch: the stub read ent["out"] while the manifest
used key "sol", causing all 45 cases to be invalid):

1. Static gate: extract the embedded stub solver from solution/solve.sh (the INNER
   heredoc, preserving its original bytes). Every ent["..."] key access in the
   stub must exist in every entry in solution/precomputed/manifest.json. This locks
   key-name consistency without executing the stub.
2. Dynamic gate (stub replay): place the stub and precomputed/ files in a temporary
   directory, then feed each hidden instance from tests/instances/ on stdin as in
   scoring. Set AHC_INSTANCE_SECONDS / AHC_TIME_POOL to the same values as in
   tests/scoring.py. Assert for every instance: (a) exit code is 0, (b) output is
   nonempty, and (c) check_ahc from tests/scoring.py accepts the solution and its
   recomputed score equals reference K (tests/reference-hidden.json).

Run with `python3 tests/test_oracle_stub.py` (unittest)."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

TESTS = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(TESTS)
sys.path.insert(0, TESTS)

import scoring  # noqa: E402

ENV = {"AHC_INSTANCE_SECONDS": "2", "AHC_TIME_POOL": "2"}


def extract_stub():
    """Original bytes of the INNER heredoc in solution/solve.sh (the content of /app/solver during scoring)."""
    with open(os.path.join(TASK, "solution", "solve.sh")) as f:
        text = f.read()
    m = re.search(r"<<'INNER'\n(.*?)\nINNER\n", text, re.S)
    if not m:
        raise AssertionError("INNER heredoc stub solver not found in solve.sh")
    return m.group(1)


class OracleStubTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stub = extract_stub()
        with open(os.path.join(TASK, "solution", "precomputed",
                               "manifest.json")) as f:
            cls.manifest = json.load(f)
        with open(os.path.join(TESTS, "reference-hidden.json")) as f:
            cls.hidden_ref = json.load(f)["instances"]

    def test_static_key_consistency(self):
        keys = set(re.findall(r'ent\["([^"]+)"\]', self.stub))
        self.assertTrue(keys, "no ent[...] key access found in stub code")
        for h, ent in self.manifest.items():
            for k in keys:
                self.assertIn(k, ent,
                              f"manifest entry lacks stub key access {k!r}: {ent!r}")
        # There must be exactly one solution filename key, and every file must exist
        for h, ent in self.manifest.items():
            sol = ent.get("sol")
            self.assertIsNotNone(sol, f"manifest entry lacks sol key: {ent!r}")
            self.assertTrue(os.path.isfile(os.path.join(
                TASK, "solution", "precomputed", sol)),
                f"precomputed file missing {sol}")

    def test_replay_all_hidden(self):
        tmp = tempfile.mkdtemp(prefix="oracle-stub-")
        try:
            os.makedirs(os.path.join(tmp, "precomputed"))
            for fn in os.listdir(os.path.join(TASK, "solution", "precomputed")):
                shutil.copy(os.path.join(TASK, "solution", "precomputed", fn),
                            os.path.join(tmp, "precomputed", fn))
            stub_path = os.path.join(tmp, "solver")
            with open(stub_path, "w") as f:
                f.write(self.stub)
            env = dict(os.environ)
            env.update(ENV)
            for name in sorted(self.hidden_ref):
                inst = os.path.join(TESTS, "instances", name)
                with open(inst) as f:
                    data = f.read()
                p = subprocess.run(
                    [sys.executable, stub_path], input=data, env=env,
                    capture_output=True, text=True, timeout=60)
                self.assertEqual(p.returncode, 0,
                                 f"{name}: stub exit code {p.returncode} "
                                 f"(stderr: {p.stderr[-300:]})")
                out_path = os.path.join(tmp, name + ".out")
                with open(out_path, "w") as f:
                    f.write(p.stdout)
                self.assertGreater(os.path.getsize(out_path), 0,
                                   f"{name}: stub output is empty")
                score, err = scoring.check_ahc(inst, out_path)
                self.assertIsNone(err, f"{name}: checker rejected solution: {err}")
                self.assertEqual(score, self.hidden_ref[name]["K"],
                                 f"{name}: recomputed score {score} != K "
                                 f"{self.hidden_ref[name]['K']}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
