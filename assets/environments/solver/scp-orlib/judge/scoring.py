"""Shared scoring logic for the scp-orlib task.

Judge-side scoring module (form 2, 2026-09-20): lives in tests/ only — the
judging chain (/tests/checker.py, both channels) imports it; the agent
environment no longer carries any scoring code (the agent-side convenience
runner /app/run_public.py is a self-contained per-instance runner with no
aggregation).

Pipeline: run `bash /app/build.sh` (must produce /app/solver) -> for each
instance, run `solver < instance` with the REMAINING time pool in env
SCP_TIME_POOL (hard-killed when the pool is exhausted; no per-instance
limit) -> validate the printed cover and recompute its cost with
check_scp() below -> A = cost of the (valid) cover -> per-instance gap ratio r = (B - A) / (B - K), unclipped -> arithmetic mean. Instances with
B == K carry no signal and are excluded.

Instance format (canonical OR-Library row-major layout, all integers,
whitespace arbitrary): m n ; n column costs ; then for each row i a block
k_i followed by the k_i column indices (1-based) covering row i.

Solution format: the selected column indices (1-based), whitespace
separated, each at most once. A cover is valid iff every token is an
integer in 1..n, no column repeats, and every row is covered by at least
one selected column. The objective A = sum of the costs of the selected
columns, recomputed from scratch. That is all check_scp() does — the same
code runs on both sides, and nothing the solver prints beyond the column
list is trusted.

Time budget: ONE TOTAL TIME POOL covers all instances of the channel being
judged — there is no per-instance limit. The pool size is
    TOTAL_POOL = PER_INSTANCE_SECONDS * number_of_instances
(PER_INSTANCE_SECONDS = 30 s; the hidden final judging runs 26 instances =
780 s, the public self-test channel 61 = 1830 s). The solver itself decides
how to distribute
the pool across instances (it can read the remaining pool from env
SCP_TIME_POOL on every run); when the pool is used up, every instance
without a verified result scores 0. Validity checking does not consume
the pool.

The raw unclipped values are reported per instance; raw > 1 means the
submission beat the task's K value for that instance (a proven optimum,
or the best literature value where noted) and is surfaced for
investigation, never silently dropped;
under the finalized formula it counts unclipped (r > 1).

Formula finalized 2026-09-20: the judged score is the pure gap ratio r —
A=B -> 0, A=K -> 1, beating K -> r > 1, worse than B -> r < 0, with no
[0, 1] clip — averaged over the participating instances by the unified
metric engine (tests/metric/engine.py) from the per-instance raw values
and anchors this file reports. This file's local `score` field still
clips r to [0, 1] and `reward` stays that clipped mean; both are kept
for the retired local-judging pipeline only and are not the judged score.
"""

import json
import os
import signal
import subprocess
import sys
import time

BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
CHECK_TIMEOUT = 60
# Per-instance reference seconds; total pool = this value x instance count.
# The judge enforces the pool globally, NOT per instance.
PER_INSTANCE_SECONDS = float(os.environ.get("PER_INSTANCE_SECONDS", "30"))


def load_instance(path):
    """Canonical layout: m, n, then n costs, then m row blocks."""
    with open(path) as f:
        vals = f.read().split()
    if len(vals) < 2:
        raise ValueError("instance file has fewer than 2 tokens")
    m = int(vals[0])
    n = int(vals[1])
    if len(vals) < 2 + n + m:
        raise ValueError(
            f"instance file too short: {len(vals)} tokens for m={m}, n={n}")
    costs = [int(v) for v in vals[2:2 + n]]
    pos = 2 + n
    rows = []
    for _ in range(m):
        k = int(vals[pos])
        pos += 1
        rows.append([int(v) for v in vals[pos:pos + k]])
        pos += k
    if pos != len(vals):
        raise ValueError(f"trailing tokens: consumed {pos}, found {len(vals)}")
    return m, n, costs, rows


def check_scp(instance_path, out_path):
    """Return (cost, None) iff the output is a valid cover; the cost is
    recomputed from scratch. Otherwise (None, reason)."""
    try:
        m, n, costs, rows = load_instance(instance_path)
    except (ValueError, OSError, IndexError) as e:
        return None, f"could not load instance: {e}"
    try:
        with open(out_path, errors="replace") as f:
            tokens = f.read().split()
    except OSError as e:
        return None, f"could not read solver output: {e}"
    if not tokens:
        return None, "empty output"
    try:
        sel = [int(t) for t in tokens]
    except ValueError:
        return None, "output contains a non-integer token"
    if len(sel) != len(set(sel)):
        return None, "a column index appears more than once"
    for j in sel:
        if j < 1 or j > n:
            return None, f"column index {j} out of range 1..{n}"
    selset = set(sel)
    for i, cols in enumerate(rows, start=1):
        if not any(j in selset for j in cols):
            return None, f"row {i} is not covered"
    return sum(costs[j - 1] for j in sel), None


def build_solver(app_dir, timeout=BUILD_TIMEOUT):
    """Run the agent-visible build script; require /app/solver afterwards."""
    script = os.path.join(app_dir, "build.sh")
    if not os.path.exists(script):
        return None, "no /app/build.sh found"
    try:
        p = subprocess.run(
            ["bash", script], cwd=app_dir, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None, f"build.sh timed out after {timeout}s"
    solver = os.path.join(app_dir, "solver")
    if not (os.path.exists(solver) and os.access(solver, os.X_OK)):
        tail = ((p.stdout or "") + (p.stderr or ""))[-3000:]
        return None, (f"build.sh finished (exit {p.returncode}) but did not "
                      f"produce an executable /app/solver\n{tail}")
    return solver, None


def run_solver(solver, instance_path, out_path, remaining_pool):
    """Run solver < instance > out_path with hard timeout = remaining pool.

    The solver learns the remaining pool via env SCP_TIME_POOL and is free
    to use as much of it as it wants on this instance. Returns
    (seconds, None) on success, (seconds, reason) otherwise.
    """
    env = dict(os.environ)
    env["SCP_TIME_POOL"] = f"{remaining_pool:.3f}"
    t0 = time.time()
    with open(instance_path) as fin, open(out_path, "w") as fout:
        p = subprocess.Popen(
            [solver], stdin=fin, stdout=fout, env=env,
            stderr=subprocess.DEVNULL, start_new_session=True,
        )
        try:
            p.wait(timeout=remaining_pool)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
            return time.time() - t0, "time pool exhausted during this instance"
    seconds = time.time() - t0
    if p.returncode != 0:
        return seconds, f"solver exited with code {p.returncode}"
    return seconds, None


def evaluate(solver, instances_dir, reference, work_dir, pool_seconds):
    """Run + check every instance in the reference under one shared pool."""
    results = {}
    spent = 0.0
    for name in sorted(reference):
        inst_path = os.path.join(instances_dir, name)
        out_path = os.path.join(work_dir, name + ".out")
        B, K = reference[name]["B"], reference[name]["K"]
        rec = {"B": B, "K": K, "A": None, "raw": None, "score": 0.0,
               "status": "ok", "seconds": 0.0}
        if not os.path.exists(inst_path):
            rec["status"] = "instance file missing on judge side"
            results[name] = rec
            continue
        remaining = pool_seconds - spent
        if remaining <= 0:
            rec["status"] = "time pool exhausted before this instance"
            results[name] = rec
            continue
        seconds, err = run_solver(solver, inst_path, out_path, remaining)
        spent += seconds
        rec["seconds"] = round(seconds, 2)
        if err is None:
            cost, cerr = check_scp(inst_path, out_path)
            if cerr is None:
                rec["A"] = cost
            else:
                rec["status"] = f"invalid solution ({cerr})"
        else:
            rec["status"] = err
        if rec["A"] is not None and B > K:
            rec["raw"] = (B - rec["A"]) / (B - K)
            rec["score"] = min(1.0, max(0.0, rec["raw"]))
        results[name] = rec
    return results, spent


def summarize(results, reference, pool_seconds, spent):
    """Mean of the legacy clipped local `score` over participating (B > K)
    instances — not the judged score (the judged score is the unclipped
    gap-ratio mean computed by the metric engine; see module docstring)."""
    part = [n for n in results if reference[n]["B"] > reference[n]["K"]]
    total = sum(results[n]["score"] for n in part) / len(part) if part else 0.0
    raws = [results[n]["raw"] for n in part if results[n]["raw"] is not None]
    return {
        "reward": total,
        "participating": len(part),
        "excluded_B_equals_K": sorted(n for n in results if n not in part),
        "mean_raw_unclipped": (sum(raws) / len(raws)) if raws else None,
        "pool_seconds": pool_seconds,
        "pool_seconds_spent": round(spent, 2),
        "beat_known_best": sorted(
            n for n in part
            if results[n]["A"] is not None and results[n]["A"] < reference[n]["K"]
        ),
    }


def load_reference(path):
    with open(path) as f:
        data = json.load(f)
    return data["instances"]


def main(argv):
    if len(argv) != 4:
        print(f"usage: {argv[0]} APP_DIR INSTANCES_DIR REFERENCE_JSON",
              file=sys.stderr)
        return 2
    app_dir, instances_dir, ref_path = argv[1], argv[2], argv[3]
    reference = load_reference(ref_path)
    work_dir = os.path.join("/tmp", f"scp-score-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)
    pool_seconds = float(os.environ.get(
        "TOTAL_TIME_POOL", str(PER_INSTANCE_SECONDS * len(reference))))

    solver, err = build_solver(app_dir)
    if err:
        return {"reward": 0.0, "build_error": err, "per_instance": {}}
    results, spent = evaluate(solver, instances_dir, reference, work_dir,
                              pool_seconds)
    out = summarize(results, reference, pool_seconds, spent)
    out["per_instance"] = results
    return out


if __name__ == "__main__":
    print(json.dumps(main(sys.argv), indent=1, sort_keys=True))
