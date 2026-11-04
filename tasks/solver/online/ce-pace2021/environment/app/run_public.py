#!/usr/bin/env python3
"""Run your solver on the PUBLIC instances and print per-instance results.

Usage:  python3 /app/run_public.py

This is a local convenience runner: it rebuilds via /app/build.sh, runs
every public instance with a per-instance wall-clock limit (600 s each,
the official PACE 2021 heuristic-track limit), validates the output with
the official verifier (ce_verify), and prints one line per instance:
name, A (size of the edit set), validity status, seconds used. Nothing is
aggregated.

This dev box is NOT the judging sandbox: core count, memory, and timing
behavior differ here, and the per-instance limit enforcement differs too.
Treat the results of submit.sh (public practice channel) as authoritative.
"""
import json
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

VERIFY_BIN = os.environ.get("VERIFY_BIN", "/usr/local/bin/ce_verify")
BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
PER_INSTANCE_SECONDS = int(os.environ.get("PER_INSTANCE_SECONDS", "600"))
VERIFY_TIMEOUT = int(os.environ.get("VERIFY_TIMEOUT", "300"))
JOBS = int(os.environ.get("JOBS", "0")) or max(1, (os.cpu_count() or 1))

APP_DIR = "/app"
INSTANCES_DIR = "/app/instances"


def build_solver(app_dir, timeout=BUILD_TIMEOUT):
    """Run the build script; require /app/solver afterwards."""
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


def verify_edits(instance_path, out_path):
    """Official PACE 2021 verifier: prints 'OK' iff applying the edit set
    yields a cluster graph (disjoint union of cliques). NOTE: the official
    verifier exits 0 even when it reports a P3 witness, so validity is
    decided by its stdout, not the exit code. Returns (size, None) with
    size = number of non-empty lines of the edit set, else (None, reason)."""
    try:
        p = subprocess.run(
            [VERIFY_BIN, instance_path, out_path],
            capture_output=True, text=True, timeout=VERIFY_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return None, "verifier timed out"
    if p.returncode != 0:
        msg = (p.stderr or "").strip() or (p.stdout or "").strip()
        return None, f"verifier failed ({msg[-300:]})"
    if not (p.stdout or "").lstrip().startswith("OK"):
        msg = (p.stdout or "").strip()
        return None, f"not a cluster editing ({msg[-300:]})"
    try:
        with open(out_path, errors="replace") as f:
            size = sum(1 for line in f if line.strip())
    except OSError as e:
        return None, f"could not read solver output: {e}"
    return size, None


def main():
    solver, err = build_solver(APP_DIR)
    if err:
        print(f"BUILD FAILED: {err}", file=sys.stderr)
        return 1

    names = sorted(os.listdir(INSTANCES_DIR))
    work_dir = os.path.join("/tmp", f"ce-run-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)
    jobs = max(1, min(JOBS, os.cpu_count() or 1))

    def one(name, core):
        inst_path = os.path.join(INSTANCES_DIR, name)
        out_path = os.path.join(work_dir, name + ".out")
        rec = {"A": None, "status": "ok"}
        secs, rerr = run_solver(solver, inst_path, out_path,
                                PER_INSTANCE_SECONDS, core)
        rec["seconds"] = round(secs, 2)
        if rerr is None:
            size, verr = verify_edits(inst_path, out_path)
            if verr is None:
                rec["A"] = size
            else:
                rec["status"] = verr
        else:
            rec["status"] = rerr
        return name, rec

    results = {}
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        futures = [ex.submit(one, name, i % jobs)
                   for i, name in enumerate(names)]
        for fut in futures:
            name, rec = fut.result()
            results[name] = rec
            a = rec["A"] if rec["A"] is not None else "-"
            print(f"{name}\tA={a}\t{rec['status']}\t{rec['seconds']}s",
                  flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
