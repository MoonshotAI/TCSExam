"""Local public-instance runner for the hs-pace2025 task.

This is a convenience runner for the agent's dev box only. It compiles all
/app/*.cpp, runs the public instances with a per-instance wall-clock limit
(300 s each, the official PACE 2025 hitting-set heuristic-track limit,
handed to the solver via env HS_TIME_POOL), validates the output with the
official PACE 2025 HS Java verifier, and prints one line per instance:
name, A (solution size), validity status, seconds used. Nothing is
aggregated.

This dev box is NOT the judging sandbox: core count, memory, and timing
behavior differ here. Treat the results of submit.sh (public practice
channel) as authoritative.
"""

import glob
import json
import os
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

VERIFIER_JAR = os.environ.get("VERIFIER_JAR", "/opt/hs2025/hs_verifier.jar")
JAVA_XMX = os.environ.get("JAVA_XMX", "4g")
COMPILE_TIMEOUT = int(os.environ.get("COMPILE_TIMEOUT", "300"))
VERIFY_TIMEOUT = int(os.environ.get("VERIFY_TIMEOUT", "300"))
# Official PACE 2025 hitting-set heuristic-track per-instance wall-clock
# limit (seconds).
PER_INSTANCE_SECONDS = float(os.environ.get("PER_INSTANCE_SECONDS", "300"))
JUDGE_JOBS = int(os.environ.get("JUDGE_JOBS", "0")) or max(1, (os.cpu_count() or 1))
INSTANCE_KEY = os.environ.get("HS_INSTANCE_KEY", "/tests/instance.key")
# The Java verifier needs ~3.1 GB RSS on the largest instance; an
# unlucky all-workers-verify-at-once wave would otherwise multiply that
# by JUDGE_JOBS and OOM the judge box. Verifies are ~15 s against 300 s
# solves, so bounding their concurrency costs no meaningful wall time.
VERIFY_CONC = int(os.environ.get("VERIFY_CONC", "4"))
_verify_sem = threading.BoundedSemaphore(max(1, VERIFY_CONC))


def compile_solver(app_dir, work_dir):
    """Compile every top-level .cpp/.cc in app_dir into one binary."""
    srcs = sorted(
        glob.glob(os.path.join(app_dir, "*.cpp"))
        + glob.glob(os.path.join(app_dir, "*.cc"))
    )
    if not srcs:
        return None, "no C++ sources (*.cpp/*.cc) found in /app"
    out = os.path.join(work_dir, "solver")
    cmd = ["g++", "-O2", "-std=c++17", "-o", out] + srcs
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=COMPILE_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None, f"compile timed out after {COMPILE_TIMEOUT}s"
    if p.returncode != 0:
        return None, "compile failed:\n" + (p.stderr or "")[-4000:]
    return out, None


def materialize_instance(instances_dir, name, work_dir):
    """Path of a plain .hgr for `name`, decrypting just-in-time if the
    stored file is the encrypted shape. Returns (path, None) or
    (None, reason)."""
    plain = os.path.join(instances_dir, name + ".hgr")
    if os.path.exists(plain):
        return plain, None
    enc = os.path.join(instances_dir, name + ".hgr.xz.enc")
    if not os.path.exists(enc):
        return None, "instance file missing on judge side"
    if not os.path.exists(INSTANCE_KEY):
        return None, "instance key missing on judge side"
    out = os.path.join(work_dir, name + ".hgr")
    cmd = (f"openssl enc -d -aes-256-ctr -pbkdf2 -pass file:{INSTANCE_KEY}"
           f" -in {enc} | xz -dc > {out}")
    try:
        p = subprocess.run(["bash", "-c", cmd], capture_output=True,
                           text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return None, "instance decrypt timed out"
    if p.returncode != 0 or not os.path.exists(out) or os.path.getsize(out) == 0:
        return None, f"instance decrypt failed: {(p.stderr or '')[-200:]}"
    return out, None


def run_solver(solver, instance_path, sol_path, limit_seconds, core=None):
    """Run solver < instance > sol_path with a hard wall-clock limit,
    optionally pinned to a core via taskset.

    The solver learns the limit via env HS_TIME_POOL and is free to use as
    much of it as it wants on this instance. Returns (seconds, None) on
    success, (seconds, reason) otherwise.
    """
    env = dict(os.environ)
    env["HS_TIME_POOL"] = f"{limit_seconds:.3f}"
    cmd = [solver] if core is None else ["taskset", "-c", str(core), solver]
    t0 = time.time()
    with open(instance_path) as fin, open(sol_path, "w") as fout:
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


def verify_solution(instance_path, sol_path):
    """Official PACE 2025 HS verifier (Java). On success its stdout line is
    'Solution of size <k> is valid!'. Returns (k, None) or (None, reason).
    Concurrency-bounded: the JVM needs ~3.1 GB RSS on the giants."""
    with _verify_sem:
        try:
            p = subprocess.run(
                ["java", f"-Xmx{JAVA_XMX}", "-jar", VERIFIER_JAR,
                 instance_path, sol_path],
                capture_output=True, text=True, timeout=VERIFY_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return None, "verifier timed out"
    out = (p.stdout or "").strip()
    marker = "is valid!"
    if marker in out:
        try:
            seg = [ln for ln in out.splitlines() if marker in ln][0]
            return int(seg.split("Solution of size")[1].split("is valid")[0]), None
        except (ValueError, IndexError):
            return None, f"unparseable verifier output: {out[:200]!r}"
    msg = (p.stderr or "").strip() or out or f"verifier exit {p.returncode}"
    return None, f"invalid solution ({msg[-300:]})"


def main(argv):
    if len(argv) != 4:
        print(f"usage: {argv[0]} APP_DIR INSTANCES_DIR REFERENCE_JSON",
              file=sys.stderr)
        return 2
    app_dir, instances_dir, ref_path = argv[1], argv[2], argv[3]
    # The public practice set is defined by the reference file's keys (the
    # same set submit.sh's public channel judges).
    with open(ref_path) as f:
        reference = json.load(f)["instances"]
    names = sorted(reference)
    work_base = os.environ.get("SCORE_WORK_DIR", "/tmp")
    work_dir = os.path.join(work_base, f"hs2025-run-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)

    solver, err = compile_solver(app_dir, work_dir)
    if err:
        print(f"BUILD FAILED: {err}", file=sys.stderr)
        return 1

    jobs = max(1, min(JUDGE_JOBS, os.cpu_count() or 1))

    def one(name, core):
        sol_path = os.path.join(work_dir, name + ".sol")
        rec = {"A": None, "status": "ok", "seconds": 0.0}
        inst_path, merr = materialize_instance(instances_dir, name, work_dir)
        if merr is not None:
            rec["status"] = merr
            return name, rec
        seconds, rerr = run_solver(solver, inst_path, sol_path,
                                   PER_INSTANCE_SECONDS, core)
        rec["seconds"] = round(seconds, 2)
        if rerr is None:
            size, verr = verify_solution(inst_path, sol_path)
            if verr is None:
                rec["A"] = size
            else:
                rec["status"] = verr
        else:
            rec["status"] = rerr
        if inst_path.startswith(work_dir):
            os.remove(inst_path)
        return name, rec

    with ThreadPoolExecutor(max_workers=jobs) as ex:
        futures = [ex.submit(one, name, i % jobs)
                   for i, name in enumerate(names)]
        for fut in futures:
            name, rec = fut.result()
            a = rec["A"] if rec["A"] is not None else "-"
            print(f"{name}\tA={a}\t{rec['status']}\t{rec['seconds']}s",
                  flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
