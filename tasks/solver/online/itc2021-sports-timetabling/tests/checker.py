#!/usr/bin/env python3
"""Judge-side checker: build /app solver, run on hidden instances, score."""
import json
import os
import sys

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
# Judge-side copy of the shared scoring module: import from /tests so the
# agent cannot tamper with it (the agent environment carries no scoring
# code at all — only /opt/itc2021/public_runner.py, a reference-free
# convenience runner).
sys.path.insert(0, "/tests")
import scoring

INSTANCES_DIR = os.environ.get("INSTANCES_DIR",
                               os.path.join(TESTS_DIR, "instances"))
REWARD_PATH = os.environ.get("REWARD_PATH", "/logs/verifier/reward.json")

out = scoring.main(["checker.py", "/app", INSTANCES_DIR,
                    os.path.join(TESTS_DIR, "reference.json")])
os.makedirs(os.path.dirname(REWARD_PATH), exist_ok=True)
with open(REWARD_PATH, "w") as f:
    json.dump(out, f, indent=1, sort_keys=True)
# The platform judge reads the plain-number reward file; keep the rich
# JSON alongside it.
with open("/logs/verifier/reward.txt", "w") as f:
    f.write(str(out["reward"]))
print(json.dumps(out, indent=1, sort_keys=True))
