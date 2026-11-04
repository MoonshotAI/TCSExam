#!/usr/bin/env python3
"""curriculum-itc2007 oracle-stub self-check (codified after the 260920 key-name incident; replaying the stub is not solver execution).

Two gates prevent incidents where the stub and manifest use different key names
(observed in cross-task checks on 260920: this task's stub read ent["pack"] while
the manifest used key "sol", as in the ahc058/christmas batch incidents):

1. Static gate: extract the embedded stub solver from solution/solve.sh (the INNER
   heredoc, preserving its original bytes). Every ent["..."] key access in the
   stub must exist in every entry in solution/precomputed/manifest.json. This locks
   key-name consistency without executing the stub.
2. Dynamic gate (stub replay): place the stub and precomputed/ files in a temporary
   directory, then feed each hidden instance from tests/instances/ on stdin as in
   scoring. Set CTT_TIME_LIMIT=240 to match tests/scoring.py. Assert for every
   instance: (a) exit code is 0, (b) output is nonempty, and (c) check_ctt from
   tests/scoring.py accepts the solution and the official validator recomputes
   Total Cost == reference K (tests/reference.json). This test compiles the official
   validator (environment/app/validator.cc), the same binary used in scoring. The
   validator checks solutions; it is not a solver.

Run with `python3 tests/test_oracle_stub.py` (unittest; requires local g++)."""
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

VALIDATOR_BIN = os.path.join(tempfile.gettempdir(),
                             "ctt-oracle-stub-test-validator")
if not os.path.exists(VALIDATOR_BIN):
    subprocess.run(["g++", "-O2", "-o", VALIDATOR_BIN,
                    os.path.join(TASK, "environment", "app", "validator.cc")],
                   check=True)
os.environ["CTT_VALIDATOR"] = VALIDATOR_BIN

sys.path.insert(0, TESTS)
import scoring  # noqa: E402  (imported after CTT_VALIDATOR is available)

ENV = {"CTT_TIME_LIMIT": "240"}


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
        with open(os.path.join(TESTS, "reference.json")) as f:
            cls.hidden_ref = json.load(f)["instances"]

    def test_static_key_consistency(self):
        keys = set(re.findall(r'ent\["([^"]+)"\]', self.stub))
        self.assertTrue(keys, "no ent[...] key access found in stub code")
        for h, ent in self.manifest.items():
            for k in keys:
                self.assertIn(k, ent,
                              f"manifest entry lacks stub key access {k!r}: {ent!r}")
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
                cost, err = scoring.check_ctt(inst, out_path)
                self.assertIsNone(err, f"{name}: checker rejected solution: {err}")
                self.assertEqual(cost, self.hidden_ref[name]["K"],
                                 f"{name}: recomputed cost {cost} != K "
                                 f"{self.hidden_ref[name]['K']}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
