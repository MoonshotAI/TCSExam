#!/usr/bin/env python3
"""Judge-side checker: integrity-check the pristine engine, build the /app
solver, run on the hidden instances, machine-check solutions, score.

Sharding (env ``INSTANCE_SHARD=i/N``, injected by tcsexam for sharded judge
sessions): only slice i of the sorted instance list is judged — modulo
slicing (keys[i::N]) so every track is spread across shards instead of one
shard getting all the big ones. The slice's participating count lands in
the reward JSON ("participating", via scoring.summarize) and the service
merges shard scores weighted by it, reproducing the unsharded mean
exactly. Unset = judge everything (the evaluation runner task path, unchanged).
"""
import hashlib
import json
import os
import sys
import tempfile

sys.path.insert(0, "/opt/sygus")

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCES_DIR = os.environ.get("INSTANCES_DIR",
                               os.path.join(TESTS_DIR, "instances"))
REWARD_PATH = os.environ.get("REWARD_PATH", "/logs/verifier/reward.json")
INSTANCE_SHARD = os.environ.get("INSTANCE_SHARD", "").strip()  # "i/N" or ""


def _sharded_reference(ref_path):
    """Return a reference path restricted to this shard's slice (or the
    original path when unsharded)."""
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
    # Balanced slicing: participating (K > B) instances are dealt
    # first, then the no-signal (K <= B) ones, each modulo-sliced separately —
    # so no shard ends up with an empty participating set (an empty slice would
    # take the retired SOL fallback path and report 0.0 with merge weight 1,
    # dragging every score down by ~1/(part+N); mc-exact shard 7/8 hit exactly
    # that).
    inst = data["instances"]
    kb = [k for k in keys if inst[k].get("K", 0) > inst[k].get("B", 0)]
    rest = [k for k in keys if k not in set(kb)]
    keep = kb[shard_i::shard_n] + rest[shard_i::shard_n]
    data["instances"] = {k: inst[k] for k in keep}
    fd, tmp_path = tempfile.mkstemp(prefix="reference-shard-", suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f)
    print(f"INSTANCE_SHARD={INSTANCE_SHARD}: judging {len(keep)} of {len(keys)} instances: {keep}")
    return tmp_path


# The agent could in principle overwrite files inside the image during its
# session; the judge-side code (this file, /tests) is only mounted after
# the agent finishes, so the hashes pinned here cannot be forged from the
# agent side. Fail closed on any mismatch.
with open(os.path.join(TESTS_DIR, "integrity.json")) as f:
    INTEGRITY = json.load(f)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


tampered = [p for p, want in INTEGRITY.items()
            if not os.path.exists(p) or sha256(p) != want]
if tampered:
    out = {"reward": 0.0,
           "integrity_error": "pristine judge-side files were modified",
           "tampered": tampered, "per_instance": {}}
else:
    import scoring
    out = scoring.main(["checker.py", "/app", INSTANCES_DIR,
                        _sharded_reference(
                            os.path.join(TESTS_DIR, "reference.json"))])
os.makedirs(os.path.dirname(REWARD_PATH), exist_ok=True)
with open(REWARD_PATH, "w") as f:
    json.dump(out, f, indent=1, sort_keys=True)
# The platform judge reads the plain-number reward file; keep the rich
# JSON alongside it.
with open("/logs/verifier/reward.txt", "w") as f:
    f.write(str(out["reward"]))
print(json.dumps(out, indent=1, sort_keys=True))
