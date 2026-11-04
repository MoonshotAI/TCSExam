"""Shared scoring logic for the dfvs-pace2022 task.

Used by BOTH sides so the formula and the verifier cannot diverge:
  - agent side:  /app/score_public.py   (public instances, public reference)
  - judge side:  /tests/checker.py      (hidden instances, hidden reference)

Pipeline: run `bash /app/build.sh` (must produce /app/solver) -> for each
instance, run `solver < instance` with the per-instance wall-clock limit
in env DFVS_TIME_POOL (process group hard-killed with SIGKILL when the
limit expires; output of a killed run is discarded, the instance scores
0) -> validate the printed feedback vertex set with the official PACE
2022 verifier (fvs_verify) -> A = size of the (valid) set -> per-instance
score (B - A) / (B - K) clipped to [0, 1] -> arithmetic mean. Instances
with B == K carry no signal and are excluded.

Time budget: each instance gets its own wall-clock limit
(PER_INSTANCE_SECONDS, 1800 s by default — the official PACE 2022
exact-track per-instance limit). The solver learns the limit via env
DFVS_TIME_POOL on every run. Instances are evaluated in parallel
(JUDGE_JOBS workers, each pinned to a core). Verification time does not
consume the limit.

The raw unclipped values are reported per instance; raw > 1 means the
submission beat the best known solution (champion result) and is
investigated, not silently clipped away.
"""

import json
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

VERIFY_BIN = os.environ.get("VERIFY_BIN", "/usr/local/bin/fvs_verify")
BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
VERIFY_TIMEOUT = 60
# Official PACE 2022 exact-track per-instance wall-clock limit (seconds).
PER_INSTANCE_SECONDS = float(os.environ.get("PER_INSTANCE_SECONDS", "1800"))
JUDGE_JOBS = int(os.environ.get("JUDGE_JOBS", "0")) or max(1, (os.cpu_count() or 1))


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


def run_solver(solver, instance_path, out_path, limit_seconds, core=None):
    """Run solver < instance > out_path with a hard wall-clock limit,
    optionally pinned to a core via taskset.

    The solver learns the limit via env DFVS_TIME_POOL and is free to use as
    much of it as it wants on this instance. Returns (seconds, None) on
    success, (seconds, reason) otherwise.
    """
    env = dict(os.environ)
    env["DFVS_TIME_POOL"] = f"{limit_seconds:.3f}"
    cmd = [solver] if core is None else ["taskset", "-c", str(core), solver]
    t0 = time.time()
    with open(instance_path) as fin, open(out_path, "w") as fout:
        p = subprocess.Popen(
            cmd, stdin=fin, stdout=fout, env=env,
            stderr=subprocess.DEVNULL, start_new_session=True,
        )
        try:
            p.wait(timeout=limit_seconds)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
            return time.time() - t0, "time limit exhausted during this instance"
    seconds = time.time() - t0
    if p.returncode != 0:
        return seconds, f"solver exited with code {p.returncode}"
    return seconds, None


def verify_fvs(instance_path, out_path):
    """Official verifier: exit 0 (+ 'OK') iff the output is a feedback vertex
    set. Returns (size, None) on success, else (None, reason). Size is the
    number of non-empty lines (duplicates are already rejected by the
    official verifier, so non-empty line count == set size)."""
    try:
        p = subprocess.run(
            [VERIFY_BIN, instance_path, out_path],
            capture_output=True, text=True, timeout=VERIFY_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return None, "verifier timed out"
    if p.returncode != 0:
        msg = (p.stderr or "").strip() or (p.stdout or "").strip()
        return None, f"invalid feedback vertex set ({msg[-300:]})"
    try:
        with open(out_path, errors="replace") as f:
            size = sum(1 for line in f if line.strip())
    except OSError as e:
        return None, f"could not read solver output: {e}"
    return size, None


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
               "status": "ok", "seconds": 0.0}
        if not os.path.exists(inst_path):
            rec["status"] = "instance file missing on judge side"
            return name, rec
        seconds, err = run_solver(solver, inst_path, out_path,
                                  per_instance_seconds, core)
        rec["seconds"] = round(seconds, 2)
        if err is None:
            size, verr = verify_fvs(inst_path, out_path)
            if verr is None:
                rec["A"] = size
            else:
                rec["status"] = verr
        else:
            rec["status"] = err
        if rec["A"] is not None and B > K:
            rec["raw"] = (B - rec["A"]) / (B - K)
            rec["score"] = min(1.0, max(0.0, rec["raw"]))
        return name, rec

    results = {}
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        futures = [ex.submit(one, name, i % jobs)
                   for i, name in enumerate(sorted(reference))]
        for fut in futures:
            name, rec = fut.result()
            results[name] = rec
    return results


def summarize(results, reference, per_instance_seconds, jobs):
    """Mean of clipped scores over participating (B > K) instances."""
    part = [n for n in results if reference[n]["B"] > reference[n]["K"]]
    total = sum(results[n]["score"] for n in part) / len(part) if part else 0.0
    raws = [results[n]["raw"] for n in part if results[n]["raw"] is not None]
    return {
        "reward": total,
        "participating": len(part),
        "excluded_B_equals_K": sorted(n for n in results if n not in part),
        "mean_raw_unclipped": (sum(raws) / len(raws)) if raws else None,
        "per_instance_seconds": per_instance_seconds,
        "judge_jobs": jobs,
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
    work_dir = os.path.join("/tmp", f"dfvs-score-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)

    solver, err = build_solver(app_dir)
    if err:
        return {"reward": 0.0, "compile_error": err, "per_instance": {}}
    results = evaluate(solver, instances_dir, reference, work_dir,
                       PER_INSTANCE_SECONDS, JUDGE_JOBS)
    out = summarize(results, reference,
                    PER_INSTANCE_SECONDS,
                    max(1, min(JUDGE_JOBS, os.cpu_count() or 1)))
    out["per_instance"] = results
    return out


if __name__ == "__main__":
    print(json.dumps(main(sys.argv), indent=1, sort_keys=True))
