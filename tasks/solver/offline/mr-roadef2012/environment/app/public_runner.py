"""Local public-instance runner for the mr-roadef2012 task.

This is a convenience runner for the agent's dev box only. It rebuilds via
/app/build.sh, runs the public practice set (the instances listed in
/app/public_reference.json) with a per-instance
wall-clock budget handed to the solver via env MR_INSTANCE_SECONDS (the
legacy name MR_TIME_POOL is set to the same value; hard-killed at the
limit), validates each produced assignment with the OFFICIAL ROADEF/EURO
2012 solution checker (vendored C++ source, compiled at image build time)
which recomputes the objective from scratch, and prints one line per
instance: name, A (that objective), validity status, seconds used. Nothing
is aggregated.

This dev box is NOT the judging sandbox: core count, memory, and timing
behavior differ here. Treat timings as estimates and keep margin below the per-instance limit.

Validity: entirely decided by the official checker binary. It prints
"Solution is valid. Total objective cost is N" on success, "Solution is
invalid." when a hard constraint fails, and aborts on malformed files;
only the first form yields a value. The solver's own claims are never
trusted.

Time budget: EACH INSTANCE gets its own wall-clock limit of
PER_INSTANCE_SECONDS (300 s = the 5 minutes per instance of the official
final). Instances are run in parallel (JUDGE_JOBS workers, each pinned to
a core with taskset). Checker runs do not consume the budget. A solver
run that is killed mid-instance leaves whatever OUTPUT file it already
wrote — if that file holds a valid assignment it still counts.
"""

import json
import os
import re
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
CHECK_TIMEOUT = int(os.environ.get("CHECK_TIMEOUT", "180"))
# Per-instance wall-clock budget in seconds (ROADEF/EURO 2012 final
# official: 5 minutes per instance).
PER_INSTANCE_SECONDS = float(os.environ.get("PER_INSTANCE_SECONDS", "300"))
# The official checker binary; the judge side overrides this to its own
# freshly compiled copy.
CHECKER_BIN = os.environ.get("MR_CHECKER_BIN", "/opt/mr/checker")

COST_RE = re.compile(r"Solution is valid\. Total objective cost is (\d+)")


def _cpu_quota():
    """Effective CPU count honoring cgroup limits (the judge container gets
    cpus=4; os.cpu_count() would report the HOST's cores and oversubscribe).
    Reads cgroup v2 cpu.max and cpuset, falls back to os.cpu_count()."""
    quota = None
    try:
        with open("/sys/fs/cgroup/cpu.max") as f:
            parts = f.read().split()
        if parts[0] != "max":
            quota = max(1, int(float(parts[0]) // float(parts[1])))
    except (OSError, ValueError, IndexError, ZeroDivisionError):
        pass
    try:
        with open("/sys/fs/cgroup/cpuset.cpus.effective") as f:
            cpus = f.read().strip()
        if cpus:
            n = 0
            for chunk in cpus.split(","):
                if "-" in chunk:
                    lo, hi = chunk.split("-", 1)
                    n += int(hi) - int(lo) + 1
                else:
                    n += 1
            quota = min(quota, n) if quota else n
    except (OSError, ValueError):
        pass
    return quota or (os.cpu_count() or 1)


JUDGE_JOBS = int(os.environ.get("JUDGE_JOBS", "0")) or _cpu_quota()


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


def run_solver(solver, model_path, init_path, out_path, limit_seconds,
               core=None):
    """Run solver MODEL INITIAL OUTPUT with a hard per-instance wall-clock
    limit, optionally pinned to a core via taskset.

    The solver learns the limit via env MR_INSTANCE_SECONDS (the legacy
    name MR_TIME_POOL is set to the same value) and is free to use as much
    of it as it wants on this instance. Returns (seconds, None) on exit
    code 0, (seconds, reason) otherwise.
    """
    env = dict(os.environ)
    env["MR_INSTANCE_SECONDS"] = f"{limit_seconds:.3f}"
    env["MR_TIME_POOL"] = f"{limit_seconds:.3f}"  # legacy name, same value
    t0 = time.time()
    with open(out_path, "w") as fout:
        fout.close()
        cmd = [solver, model_path, init_path, out_path]
        if core is not None:
            cmd = ["taskset", "-c", str(core)] + cmd
        p = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, env=env, start_new_session=True,
        )
        try:
            p.wait(timeout=limit_seconds)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
            return time.time() - t0, "per-instance time limit exhausted"
    seconds = time.time() - t0
    if p.returncode != 0:
        return seconds, f"solver exited with code {p.returncode}"
    return seconds, None


def check_solution(model_path, init_path, out_path):
    """Run the official checker. Return (cost, None) iff it reports a valid
    solution; otherwise (None, reason)."""
    if not (os.path.exists(out_path) and os.path.getsize(out_path) > 0):
        return None, "solver produced no output file"
    try:
        p = subprocess.run(
            [CHECKER_BIN, model_path, init_path, out_path],
            stdin=subprocess.DEVNULL, capture_output=True, text=True,
            timeout=CHECK_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return None, f"checker timed out after {CHECK_TIMEOUT}s"
    m = COST_RE.search(p.stdout or "")
    if p.returncode == 0 and m:
        return int(m.group(1)), None
    tail = ((p.stdout or "") + (p.stderr or ""))[-200:].strip()
    return None, f"invalid solution (checker exit {p.returncode}: {tail})"


def main(argv):
    if len(argv) != 4:
        print(f"usage: {argv[0]} APP_DIR INSTANCES_DIR REFERENCE_JSON",
              file=sys.stderr)
        return 2
    app_dir, instances_dir, ref_path = argv[1], argv[2], argv[3]
    # The public practice set is defined by the reference file.
    with open(ref_path) as f:
        reference = json.load(f)["instances"]
    names = sorted(reference)
    limit_seconds = float(os.environ.get(
        "PER_INSTANCE_SECONDS", str(PER_INSTANCE_SECONDS)))
    work_dir = os.path.join("/tmp", f"mr-run-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)

    solver, err = build_solver(app_dir)
    if err:
        print(f"BUILD FAILED: {err}", file=sys.stderr)
        return 1

    jobs = max(1, min(JUDGE_JOBS, _cpu_quota()))

    def one(name, core):
        model_path = os.path.join(instances_dir, reference[name]["model"])
        init_path = os.path.join(instances_dir,
                                 reference[name]["assignment"])
        out_path = os.path.join(work_dir, name + ".out")
        rec = {"A": None, "status": "ok"}
        seconds, rerr = run_solver(solver, model_path, init_path, out_path,
                                   limit_seconds, core)
        rec["seconds"] = round(seconds, 2)
        if rerr is not None:
            # A killed solver may still have written a valid assignment;
            # the checker decides.
            cost, cerr = check_solution(model_path, init_path, out_path)
            if cerr is None:
                rec["A"] = cost
                rec["status"] = f"ok (solver note: {rerr})"
            else:
                rec["status"] = f"{rerr}; {cerr}"
        else:
            cost, cerr = check_solution(model_path, init_path, out_path)
            if cerr is None:
                rec["A"] = cost
            else:
                rec["status"] = cerr
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
