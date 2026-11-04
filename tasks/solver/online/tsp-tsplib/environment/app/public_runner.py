#!/usr/bin/env python3
"""Local public-instance runner for the tsp-tsplib task.

This is a convenience runner for the agent's dev box only — the scoring
logic (anchors, formula, aggregation) is NOT part of it. Pipeline:
copy /app into a scratch dir and run `make` (must produce ./solver) ->
for each public instance, invoke
    solver SINGLE_INSTANCE_DIR OUTPUT_DIR LIMIT_SECONDS
with the per-instance budget in seconds (PER_INSTANCE_BUDGET, 600 by
default; when budget + GRACE_TIMEOUT is exceeded the runner SIGTERMs the
process group, and SIGKILLs after another grace). The produced .tour is
then validated with the pristine tsp_check (prints "valid <length>").
Runs go in parallel (JUDGE_JOBS workers, each pinned to a core with
taskset); the solver only ever sees one instance at a time.

Prints one record per instance: name, A (validated tour length),
validity status, seconds used. Nothing is aggregated.

This dev box is NOT the judging sandbox: core count, memory, and timing
behavior differ here. Treat the results of submit.sh (public practice
channel) as authoritative.
"""
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

VERIFY_BIN = os.environ.get("VERIFY_BIN", "/usr/local/bin/tsp_check")
BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "300"))
PER_INSTANCE_BUDGET = int(os.environ.get("PER_INSTANCE_BUDGET", "600"))
GRACE_TIMEOUT = int(os.environ.get("GRACE_TIMEOUT", "10"))  # limit+grace -> TERM
JUDGE_JOBS = int(os.environ.get("JUDGE_JOBS", "0")) or max(1, (os.cpu_count() or 1))
VERIFY_TIMEOUT = 300


def build_solver(app_dir, work_dir):
    """Copy app_dir into a scratch dir, run `make`, expect ./solver."""
    build_dir = os.path.join(work_dir, "build")
    try:
        shutil.copytree(app_dir, build_dir)
    except OSError as e:
        return None, f"failed to copy /app: {e}"
    try:
        p = subprocess.run(["make", "-j4"], cwd=build_dir,
                           capture_output=True, text=True, timeout=BUILD_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None, f"build timed out after {BUILD_TIMEOUT}s"
    if p.returncode != 0:
        return None, "`make` failed:\n" + (p.stderr or "")[-4000:]
    solver = os.path.join(build_dir, "solver")
    if not (os.path.isfile(solver) and os.access(solver, os.X_OK)):
        return None, "`make` succeeded but did not produce an executable ./solver"
    return solver, None


def run_pool(solver, instances_dir, out_dir, pool, core=None):
    """Invoke the solver once with the given pool; enforce pool + grace,
    optionally pinned to a core via taskset.

    Returns (elapsed_seconds, note) where note is None on clean exit.
    """
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    cmd = [solver, instances_dir, out_dir, str(pool)]
    if core is not None:
        cmd = ["taskset", "-c", str(core)] + cmd
    p = subprocess.Popen(cmd,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    note = None
    try:
        p.wait(timeout=pool + GRACE_TIMEOUT)
    except subprocess.TimeoutExpired:
        note = f"exceeded pool+grace ({pool}+{GRACE_TIMEOUT}s); SIGTERM sent"
        try:
            os.killpg(p.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            p.wait(timeout=GRACE_TIMEOUT)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
            note += "; SIGKILL needed"
    return round(time.time() - t0, 2), note


def verify_tour(instance_path, tour_path):
    """tsp_check: exit 0 + stdout 'valid <length>'. Returns (length, err)."""
    try:
        p = subprocess.run(
            [VERIFY_BIN, instance_path, tour_path],
            capture_output=True, text=True, timeout=VERIFY_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return None, "verifier timed out"
    out = (p.stdout or "").strip()
    if p.returncode != 0 or not out.startswith("valid "):
        msg = out or (p.stderr or "").strip() or f"verifier exit {p.returncode}"
        return None, f"invalid tour ({msg[-300:]})"
    try:
        return int(out.split()[1]), None
    except (ValueError, IndexError) as e:
        return None, f"unparseable verifier output ({e})"


def main(argv):
    if len(argv) != 4:
        print(f"usage: {argv[0]} APP_DIR INSTANCES_DIR REFERENCE_JSON",
              file=sys.stderr)
        return 2
    app_dir, instances_dir, ref_path = argv[1:4]
    with open(ref_path) as f:
        names = sorted(json.load(f)["instances"])
    work_dir = os.path.join("/tmp", f"tsp-run-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)

    solver, err = build_solver(app_dir, work_dir)
    if err:
        print(json.dumps({"build_error": err}, indent=1))
        return 1

    jobs = max(1, min(JUDGE_JOBS, os.cpu_count() or 1))

    def one(name, core):
        inst_path = os.path.join(instances_dir, name + ".tsp")
        rec = {"instance": name, "A": None, "status": "ok"}
        if not os.path.exists(inst_path):
            rec["status"] = "instance file missing"
            return rec
        single_dir = os.path.join(work_dir, f"in-{name}")
        out_dir = os.path.join(work_dir, f"out-{name}")
        os.makedirs(single_dir, exist_ok=True)
        link = os.path.join(single_dir, name + ".tsp")
        if not os.path.exists(link):
            os.symlink(inst_path, link)
        elapsed, note = run_pool(solver, single_dir, out_dir,
                                 PER_INSTANCE_BUDGET, core)
        rec["seconds"] = elapsed
        if note:
            rec["status"] = note
        tour_path = os.path.join(out_dir, name + ".tour")
        if not os.path.exists(tour_path) or os.path.getsize(tour_path) == 0:
            if rec["status"] == "ok":
                rec["status"] = "no output produced (limit exhausted or skipped)"
            return rec
        length, verr = verify_tour(inst_path, tour_path)
        if verr is None:
            rec["A"] = length
        else:
            rec["status"] = verr
        return rec

    with ThreadPoolExecutor(max_workers=jobs) as ex:
        futures = [ex.submit(one, name, i % jobs)
                   for i, name in enumerate(names)]
        for fut in futures:
            rec = fut.result()
            print(json.dumps(rec, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
