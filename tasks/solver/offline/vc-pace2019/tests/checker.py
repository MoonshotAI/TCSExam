#!/usr/bin/env python3
"""Judge-side checker: build /app solver via build.sh, run on hidden instances, score.

Sharding (env ``INSTANCE_SHARD=i/N``, injected by tcsexam for sharded judge
sessions): only slice i of the sorted instance list is judged — modulo
slicing (keys[i::N]) so every instance family is spread across shards. This
task's reward is the solve-count formula (solved - B) / (N - B) with B the
baseline's solved count, so the sliced reference also rewrites top-level B
to the slice's own baseline-solved count (from the per-instance "B" flags in
reference.json) — the shard reward stays well-defined, and its denominator
(judged minus baseline-solved) lands in the reward JSON as "participating",
the merge weight. Sharded mode also rewrites each per_instance record's
anchors to the solve-type shape (A/B/K in {0,1}: solved flag, baseline-solved
flag, K=1); the unsharded evaluation runner path is untouched — reference passed
through as-is, no record rewriting.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, "/opt/vc")
import scoring

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCES_DIR = os.environ.get("INSTANCES_DIR",
                               os.path.join(TESTS_DIR, "instances"))
REWARD_PATH = os.environ.get("REWARD_PATH", "/logs/verifier/reward.json")
INSTANCE_SHARD = os.environ.get("INSTANCE_SHARD", "").strip()  # "i/N" or ""


def _sharded_reference(ref_path):
    """Return ``(path, slice_instances)``: a reference restricted to this
    shard's slice, top-level B rewritten to the slice's baseline-solved
    count. Unsharded: ``(ref_path, None)`` — the reference is used as-is."""
    if not INSTANCE_SHARD:
        return ref_path, None
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
    inst = {k: data["instances"][k] for k in keep}
    data["instances"] = inst
    data["B"] = sum(1 for k in keep if inst[k].get("B"))
    fd, tmp_path = tempfile.mkstemp(prefix="reference-shard-", suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f)
    print(f"INSTANCE_SHARD={INSTANCE_SHARD}: judging {len(keep)} of {len(keys)} "
          f"instances (baseline-solved in slice: {data['B']}): {keep}")
    return tmp_path, inst


def _normalize_shard_output(out, inst):
    """Rewrite the shard's reward JSON: per-instance anchors to the
    solve-type shape (A = solved flag, B = baseline-solved flag, K = 1) and
    "participating" = judged minus baseline-solved (the reward formula's
    denominator). A fully baseline-solved slice has no headroom — the
    formula is undefined there, so the shard reports reward 0.0."""
    per = out.get("per_instance") or {}
    for name, rec in per.items():
        if not isinstance(rec, dict):
            continue
        rec["B"] = int(bool(inst[name].get("B")))
        rec["K"] = 1
        rec["A"] = 1 if rec.get("solved") else 0
    out["participating"] = sum(1 for k in inst if not inst[k].get("B"))
    if out.get("reward") is None and "build_error" not in out:
        out["reward"] = 0.0
        out["note"] = ("slice fully baseline-solved: no headroom "
                       f"(B == N == {len(inst)}); shard reward defined as 0.0")


ref, slice_inst = _sharded_reference(os.path.join(TESTS_DIR, "reference.json"))
out = scoring.main(["checker.py", "/app", INSTANCES_DIR, ref])
if slice_inst is not None:
    _normalize_shard_output(out, slice_inst)
elif out.get("reward") is None and "build_error" not in out:
    raise SystemExit("reference.json top-level B is null — the baseline "
                     "solved count has not been measured/filled in yet; "
                     "refusing to emit a reward (see SAMPLING.md)")
os.makedirs(os.path.dirname(REWARD_PATH), exist_ok=True)
with open(REWARD_PATH, "w") as f:
    json.dump(out, f, indent=1, sort_keys=True)
# The platform judge reads the plain-number reward file; keep the rich
# JSON alongside it.
with open("/logs/verifier/reward.txt", "w") as f:
    f.write(str(out["reward"]))
print(json.dumps(out, indent=1, sort_keys=True))
