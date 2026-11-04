#!/usr/bin/env python3
"""Judge-side checker: build /app solver, run on hidden instances, score.

Sharding (env ``INSTANCE_SHARD=i/N``, injected by tcsexam for sharded judge
sessions): only slice i of the sorted instance list is judged — modulo
slicing (keys[i::N]) so every instance family is spread across shards
instead of one shard getting all the big ones. The slice's participating
count lands in the reward JSON ("participating", via scoring.summarize) and
the service merges shard scores weighted by it, reproducing the unsharded
mean exactly. Unset = judge everything (the evaluation runner task path, unchanged).
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, "/opt/glasscut")
import scoring

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCES_DIR = os.environ.get("INSTANCES_DIR",
                               os.path.join(TESTS_DIR, "instances"))
REWARD_PATH = os.environ.get("REWARD_PATH", "/logs/verifier/reward.json")
INSTANCE_SHARD = os.environ.get("INSTANCE_SHARD", "").strip()  # "i/N" or ""


def _sharded_reference(ref_path):
    if not INSTANCE_SHARD:
        return ref_path
    try:
        shard_i, shard_n = (int(x) for x in INSTANCE_SHARD.split("/"))
    except ValueError:
        raise SystemExit(f"bad INSTANCE_SHARD {INSTANCE_SHARD!r}: expected i/N")
    if not (0 <= shard_i < shard_n):
        raise SystemExit(f"bad INSTANCE_SHARD {INSTANCE_SHARD!r}: need 0 <= i < N")
    with open(ref_path) as f:
        data = json.load(f)
    keys = sorted(data["instances"])
    keep = keys[shard_i::shard_n]
    data["instances"] = {k: data["instances"][k] for k in keep}
    fd, tmp_path = tempfile.mkstemp(prefix="reference-shard-", suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f)
    print(f"INSTANCE_SHARD={INSTANCE_SHARD}: judging {len(keep)} of {len(keys)} instances: {keep}")
    return tmp_path


out = scoring.main(["checker.py", "/app", INSTANCES_DIR,
                    _sharded_reference(os.path.join(TESTS_DIR, "reference.json"))])
os.makedirs(os.path.dirname(REWARD_PATH), exist_ok=True)
with open(REWARD_PATH, "w") as f:
    json.dump(out, f, indent=1, sort_keys=True)
# The platform judge reads the plain-number reward file; keep the rich
# JSON alongside it.
with open("/logs/verifier/reward.txt", "w") as f:
    f.write(str(out["reward"]))
print(json.dumps(out, indent=1, sort_keys=True))
