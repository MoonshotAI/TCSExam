#!/usr/bin/env python3
"""Local public-instance runner for the maxcut-mqlib task.

This is a convenience runner for the agent's dev box only — the scoring
logic (anchors, formula, aggregation) is NOT part of it. Pipeline:
run `bash /app/build.sh` (must produce /app/solver) -> run the solver once
per public instance (`solver < instance > out`) with a per-instance
wall-clock limit (PER_INSTANCE_SECONDS, 600 s by default — the solver is
expected to self-limit below that; the shipped baseline uses
MAXCUT_SECONDS=540) -> validate the printed cut with mc_check (exactly n
tokens of 0/1; the weight is recomputed by summing crossing edges).
Runs go in parallel (JUDGE_JOBS workers, each pinned to a core with
taskset); the solver only ever sees one instance at a time; validation
time does not consume the limit.

Prints one record per instance: name, A (validated cut value), validity
status, seconds used. Nothing is aggregated.

This dev box is NOT the judging sandbox: core count, memory, and timing
behavior differ here. Treat the results of submit.sh (public practice
channel) as authoritative.
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


def run_solver(solver, instance_path, out_path, timeout, core=None):
    """Run solver < instance > out_path with a wall-clock timeout, optionally
    pinned to a core via taskset. Returns (seconds_used, None) on success,
    else (seconds_used, reason)."""
    t0 = time.time()
    cmd = [solver] if core is None else ["taskset", "-c", str(core), solver]
    with open(instance_path) as fin, open(out_path, "w") as fout:
        p = subprocess.Popen(
            cmd, stdin=fin, stdout=fout,
            stderr=subprocess.DEVNULL, start_new_session=True,
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
        return None, f"unparseable validator output ({out[-200:]})"


def main(argv):
    if len(argv) != 4:
        print(f"usage: {argv[0]} APP_DIR INSTANCES_DIR REFERENCE_JSON",
              file=sys.stderr)
        return 2
    app_dir, instances_dir, ref_path = argv[1:4]
    with open(ref_path) as f:
        names = sorted(json.load(f)["instances"])
    work_dir = os.path.join("/tmp", f"maxcut-run-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)

    solver, err = build_solver(app_dir)
    if err:
        print(json.dumps({"build_error": err}, indent=1))
        return 1

    jobs = max(1, min(JUDGE_JOBS, os.cpu_count() or 1))

    def one(name, core):
        inst_path = os.path.join(instances_dir, name)
        out_path = os.path.join(work_dir, name + ".out")
        rec = {"instance": name, "A": None, "status": "ok"}
        if not os.path.exists(inst_path):
            rec["status"] = "instance file missing"
            return rec
        secs, err2 = run_solver(solver, inst_path, out_path,
                                PER_INSTANCE_SECONDS, core)
        rec["seconds"] = round(secs, 2)
        if err2 is None:
            val, verr = verify_cut(inst_path, out_path)
            if verr is None:
                rec["A"] = val
            else:
                rec["status"] = verr
        else:
            rec["status"] = err2
        return rec

    results = []
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        futures = [ex.submit(one, name, i % jobs)
                   for i, name in enumerate(names)]
        for fut in futures:
            rec = fut.result()
            results.append(rec)
            print(json.dumps(rec, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
