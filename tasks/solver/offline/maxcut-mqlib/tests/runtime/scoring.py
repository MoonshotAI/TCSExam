"""Shared scoring logic for the maxcut-mqlib task (judge side only).

Lives in tests/ — no scoring
code ships in the agent environment. Used by the judging chain:
  - judge side:  /tests/checker.py      (hidden instances, hidden reference)
The agent-side local convenience runner (/app/run_public.py via
/opt/maxcut/public_runner.py) re-implements only the build/run/validate
machinery and deliberately shares no anchors or formula.

Pipeline: run `bash /app/build.sh` (must produce /app/solver) -> run the
solver once per instance -> validate the printed cut with mc_check (exactly
n tokens of 0/1; objective recomputed by summing the weights of all crossing
edges) -> A = validated cut value -> per-instance score -> arithmetic mean.

Maximization, two anchors: B = cut value of the shipped baseline heuristic
(MQLib BEASLEY1998TS tabu search at the in-task budget, score 0.0) and
K = best known (best of the 37 MQLib literature heuristics x 5 seeds under
the library's evaluation budgets, spot-verified by re-running; score 1.0):

    raw = (A - B) / (K - B),  unclipped (the pure gap ratio)

Instances with K <= B (within a relative tolerance, or with no measured
baseline yet) carry no signal and are excluded from the mean.

Time budget: each instance gets its own wall-clock limit
(PER_INSTANCE_SECONDS, 600 s by default). The solver is expected to
self-limit below that (the shipped baseline uses MAXCUT_SECONDS=540); the
judge kills the process group at the limit, and a killed or crashing run
scores 0 for that instance. Instances are evaluated in parallel
(JUDGE_JOBS workers, each pinned to a core with taskset); the solver only
ever sees one instance at a time. Validation time does not consume the
limit.

The raw unclipped values are reported per instance; raw > 1 means the
submission beat the library-best known value and is investigated,
never silently dropped; under the finalized formula it counts unclipped
(r > 1).

Scoring formula: the judged score is the pure gap ratio r —
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
from concurrent.futures import ThreadPoolExecutor

CHECK_BIN = os.environ.get("CHECK_BIN", "/usr/local/bin/mc_check")
BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
PER_INSTANCE_SECONDS = int(os.environ.get("PER_INSTANCE_SECONDS", "600"))
VERIFY_TIMEOUT = int(os.environ.get("VERIFY_TIMEOUT", "900"))
JUDGE_JOBS = int(os.environ.get("JUDGE_JOBS", "0")) or max(1, (os.cpu_count() or 1))

# Values are floating point (some families have fractional weights); anchors
# compare equal when they agree to this relative tolerance.
REL_TOL = 1e-9


def _tol(*vals):
    return REL_TOL * max(1.0, *(abs(v) for v in vals))


def build_solver(app_dir, timeout=BUILD_TIMEOUT):
    """Run the agent-visible build script; require /app/solver afterwards."""
    script = os.path.join(app_dir, "build.sh")
    if not os.path.exists(script):
        return None, "no /app/build.sh found"
    try:
        p = subprocess.run(
            ["bash", script], cwd=app_dir, stdin=subprocess.DEVNULL, user=65534, group=65534, extra_groups=[],
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


def run_solver(solver, instance_path, out_path, timeout, core=None):
    """Run solver < instance > out_path with a wall-clock timeout, optionally
    pinned to a core via taskset. Returns (seconds_used, None) on success,
    else (seconds_used, reason)."""
    t0 = time.time()
    cmd = [solver] if core is None else ["taskset", "-c", str(core), solver]
    with open(instance_path) as fin, open(out_path, "w") as fout:
        p = subprocess.Popen(
            cmd, stdin=fin, stdout=fout,
            stderr=subprocess.DEVNULL, start_new_session=True, user=65534, group=65534, extra_groups=[],
        )
        try:
            p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
            return time.time() - t0, f"timeout after {round(timeout, 1)}s"
    used = time.time() - t0
    if p.returncode != 0:
        return used, f"solver exited with code {p.returncode}"
    return used, None


def verify_cut(instance_path, out_path):
    """Validate the printed cut with mc_check and return its recomputed
    objective. Returns (value, None) on success, else (None, reason)."""
    try:
        p = subprocess.run(
            [CHECK_BIN, instance_path, out_path],
            capture_output=True, text=True, timeout=VERIFY_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return None, "validator timed out"
    out = (p.stdout or "").strip()
    if p.returncode != 0 or not out.startswith("OK "):
        msg = out or (p.stderr or "").strip()
        return None, f"invalid cut ({msg[-300:]})"
    try:
        return float(out.split()[1]), None
    except (IndexError, ValueError):
        return None, f"unparseable validator output ({out[-300:]})"


def evaluate(solver, instances_dir, reference, work_dir, per_instance_seconds,
             jobs):
    """Run + verify every instance in the reference, in parallel: each
    instance gets its own wall-clock limit and its own core."""
    ncores = max(1, os.cpu_count() or 1)
    jobs = max(1, min(jobs, ncores))

    def one(name, core):
        inst_path = os.path.join(instances_dir, name)
        out_path = os.path.join(work_dir, name + ".out")
        B, K = reference[name]["B"], reference[name]["K"]
        rec = {"B": B, "K": K, "A": None, "raw": None, "score": 0.0,
               "status": "ok"}
        if not os.path.exists(inst_path):
            rec["status"] = "instance file missing on judge side"
            return name, rec
        secs, err = run_solver(solver, inst_path, out_path,
                               per_instance_seconds, core)
        rec["seconds"] = round(secs, 2)
        if err is None:
            val, verr = verify_cut(inst_path, out_path)
            if verr is None:
                rec["A"] = val
            else:
                rec["status"] = verr
        else:
            rec["status"] = err
        if rec["A"] is not None and B is not None and K - B > _tol(K, B):
            rec["raw"] = (rec["A"] - B) / (K - B)
            rec["score"] = min(1.0, max(0.0, rec["raw"]))
        return name, rec

    results = {}
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        futures = [ex.submit(one, name, sorted(os.sched_getaffinity(0))[i % jobs])
                   for i, name in enumerate(sorted(reference))]
        for fut in futures:
            name, rec = fut.result()
            results[name] = rec
    return results


def summarize(results, reference):
    """Mean of the legacy clipped local `score` over participating (K > B)
    instances — not the judged score (the judged score is the unclipped
    gap-ratio mean computed by the metric engine; see module docstring)."""
    def participates(n):
        B, K = reference[n]["B"], reference[n]["K"]
        return B is not None and K - B > _tol(K, B)

    part = [n for n in results if participates(n)]
    total = sum(results[n]["score"] for n in part) / len(part) if part else 0.0
    raws = [results[n]["raw"] for n in part if results[n]["raw"] is not None]
    return {
        "reward": total,
        "participating": len(part),
        "excluded_no_signal": sorted(n for n in results if n not in part),
        "mean_raw_unclipped": (sum(raws) / len(raws)) if raws else None,
        "beat_known_best": sorted(
            n for n in part
            if results[n]["A"] is not None
            and results[n]["A"] > reference[n]["K"] + _tol(reference[n]["K"])
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
    work_dir = os.path.join("/tmp", f"maxcut-score-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)
    os.chown(work_dir, 65534, 65534)

    solver, err = build_solver(app_dir)
    if err:
        return {"reward": 0.0, "build_error": err, "per_instance": {}}
    results = evaluate(solver, instances_dir, reference, work_dir,
                       PER_INSTANCE_SECONDS, JUDGE_JOBS)
    out = summarize(results, reference)
    out["per_instance_seconds"] = PER_INSTANCE_SECONDS
    out["judge_jobs"] = max(1, min(JUDGE_JOBS, os.cpu_count() or 1))
    out["per_instance"] = results
    return out


if __name__ == "__main__":
    print(json.dumps(main(sys.argv), indent=1, sort_keys=True))
