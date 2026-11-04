#!/usr/bin/env python3
"""Judge-side checker: build /app solver, run on hidden instances, score.

Sharding (env ``INSTANCE_SHARD=i/N``, injected by tcsexam for sharded judge
sessions): only slice i of the instance list is judged. Slices are dealt
size-balanced (judge-v12, 260923): stat every instance file, sort by size
descending (ties broken by name), then deal one instance per shard in
rotation — largest to shard 0, next to shard 1, ..., N-th to shard N-1,
(N+1)-th to shard 0 again. The previous plain modulo slice (keys[i::N] over
sorted names) put the two largest instances (ex152/ex202) on the same shard;
that shard was killed every judging round (rc=137, no output) and its
participating keys were lost from the merge. Dealing by size spreads the big
instances across different shards and balances per-shard total size. The
slices still partition the key set, so the service's
participating-count-weighted merge reproduces the unsharded mean exactly
(merge semantics unchanged). The deal is deterministic: same instance files
-> same sizes -> same slices. Unset = judge everything (the evaluation runner task
path, unchanged).
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, "/opt/maxsat")
import scoring

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCES_DIR = os.environ.get("INSTANCES_DIR",
                               os.path.join(TESTS_DIR, "instances"))
REWARD_PATH = os.environ.get("REWARD_PATH", "/logs/verifier/reward.json")
INSTANCE_SHARD = os.environ.get("INSTANCE_SHARD", "").strip()  # "i/N" or ""


def _shard_slice(keys, shard_i, shard_n):
    """Size-balanced round-robin deal over the instance files (see module
    docstring): order keys by file size descending (name tie-break, so the
    deal is deterministic), shard i takes positions i, i+N, i+2N, ....
    Returns (keep, slice_total_bytes)."""
    sizes = {}
    for k in keys:
        path = os.path.join(INSTANCES_DIR, k)
        try:
            sizes[k] = os.path.getsize(path)
        except OSError:
            raise SystemExit(
                f"INSTANCE_SHARD {INSTANCE_SHARD!r}: cannot stat instance "
                f"file {path} (needed for size-balanced slicing)")
    order = sorted(keys, key=lambda k: (-sizes[k], k))
    keep = sorted(order[pos] for pos in range(shard_i, len(order), shard_n))
    return keep, sum(sizes[k] for k in keep)


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
    keep, total = _shard_slice(keys, shard_i, shard_n)
    data["instances"] = {k: data["instances"][k] for k in keep}
    fd, tmp_path = tempfile.mkstemp(prefix="reference-shard-", suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f)
    print(f"INSTANCE_SHARD={INSTANCE_SHARD}: judging {len(keep)} of {len(keys)} instances "
          f"(slice file-size total {total} bytes): {keep}")
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
