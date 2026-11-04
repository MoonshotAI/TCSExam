#!/usr/bin/env python3
"""Run your solver on the public practice set locally and print per-instance
results — a convenience runner, not a scorer.

Usage:  python3 /app/run_public.py [jobs]
Rebuilds via /app/build.sh, then runs your solver once per instance as
    solver INSTANCE_FILE OUTPUT_FILE LIMIT_SECONDS
with the same 600 s per-instance budget the judge uses (parallel workers,
one per core, each pinned with taskset), and validates each schedule with
/usr/local/bin/jssp_check. It prints, per instance: your makespan A, the
validity status, and the reference values from /app/public_reference.json
(B = the shipped baseline's result, K = a best-known value, L = the
textbook-technique reference level). It computes NO aggregate score.

It runs on this development box, outside the judging sandbox — use
`submit.sh` for authoritative measurements.
"""
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

PER_INSTANCE_BUDGET = int(os.environ.get("PER_INSTANCE_BUDGET", "600"))
GRACE_TIMEOUT = int(os.environ.get("GRACE_TIMEOUT", "10"))
BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
VERIFY_BIN = os.environ.get("VERIFY_BIN", "/usr/local/bin/jssp_check")


def run_solver(solver, inst_path, out_path, budget, core):
    """Invoke solver INSTANCE OUTPUT LIMIT with budget + grace enforcement."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cmd = ["taskset", "-c", str(core), solver, inst_path, out_path, str(budget)]
    t0 = time.time()
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    note = None
    try:
        p.wait(timeout=budget + GRACE_TIMEOUT)
    except subprocess.TimeoutExpired:
        note = f"exceeded limit+grace ({budget}+{GRACE_TIMEOUT}s); SIGTERM sent"
        os.killpg(p.pid, signal.SIGTERM)
        try:
            p.wait(timeout=GRACE_TIMEOUT)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
    return time.time() - t0, note


def verify_solution(inst_path, out_path):
    """jssp_check: (makespan, None) or (None, status)."""
    if not os.path.exists(out_path):
        return None, "no output file"
    try:
        p = subprocess.run([VERIFY_BIN, inst_path, out_path],
                           capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return None, "verifier timed out"
    out = (p.stdout or "").strip()
    if p.returncode == 0 and out.startswith("OK"):
        return int(out.split()[1]), None
    return None, (out or f"verifier exit {p.returncode}")


def one(args):
    name, inst_path, out_path, solver, budget, core, ref = args
    secs, note = run_solver(solver, inst_path, out_path, budget, core)
    value, verr = verify_solution(inst_path, out_path)
    status = verr or note or "ok"
    return name, value, status, secs, ref


def main():
    jobs = int(sys.argv[1]) if len(sys.argv) > 1 else (os.cpu_count() or 1)
    jobs = max(1, min(jobs, os.cpu_count() or 1))
    app_dir = "/app"
    instances_dir = os.path.join(app_dir, "instances")
    with open(os.path.join(app_dir, "public_reference.json")) as f:
        reference = json.load(f)["instances"]

    build_dir = f"/tmp/jssp-run-public-build-{os.getpid()}"
    shutil.copytree(app_dir, build_dir,
                    ignore=shutil.ignore_patterns("instances", "output",
                                                  "solutions", "jsplib"))
    p = subprocess.run(["bash", "build.sh"], cwd=build_dir,
                       stdin=subprocess.DEVNULL, capture_output=True,
                       text=True, timeout=BUILD_TIMEOUT)
    solver = os.path.join(build_dir, "solver")
    if not (os.path.exists(solver) and os.access(solver, os.X_OK)):
        tail = ((p.stdout or "") + (p.stderr or ""))[-2000:]
        sys.exit(f"build.sh did not produce an executable solver\n{tail}")

    names = sorted(os.listdir(instances_dir))
    work = f"/tmp/jssp-run-public-{os.getpid()}"
    print(f"running {len(names)} public instances with a 600 s per-instance "
          f"limit ({jobs} parallel workers, pinned cores)...")
    args = [(name, os.path.join(instances_dir, name),
             os.path.join(work, f"out-{name}", name + ".sol"),
             solver, PER_INSTANCE_BUDGET, i % jobs,
             reference.get(name, {}))
            for i, name in enumerate(names)]
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        for name, value, status, secs, ref in ex.map(one, args):
            if value is not None and status == "ok":
                print(f"{name}: A={value} valid (B={ref.get('B')}, "
                      f"K={ref.get('K')}, L={ref.get('L')}) [{secs:.1f}s]")
            else:
                print(f"{name}: A={value} {status} (B={ref.get('B')}, "
                      f"K={ref.get('K')}, L={ref.get('L')}) [{secs:.1f}s]")
    print("done. Reference values B/K/L per instance are in "
          "/app/public_reference.json.")


if __name__ == "__main__":
    main()
