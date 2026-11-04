"""Public-instance runner for the itc2021-sports-timetabling task
(agent-side convenience).

This is NOT the judging code. It rebuilds /app via `bash /app/build.sh`,
then runs /app/solver on every instance in a directory under ONE SHARED
TIME POOL (the same protocol as judging): the pool size is
PER_INSTANCE_SECONDS (60 s by default) times the instance count, the
solver learns the remaining pool via env ITC2021_TIME_POOL on every run,
and an instance is hard-killed when the pool is exhausted. Each printed
schedule is validated with the official RobinX validator (every hard
constraint recomputed from scratch; any hard violation makes the schedule
invalid) and its soft penalty is recomputed. It reports per-instance
results only: instance name, the recomputed penalty A, validity, and
seconds used. No reference values, no aggregation, no scoring formula.
"""
import json
import os
import re
import signal
import subprocess
import sys
import time

BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
PER_INSTANCE_SECONDS = float(os.environ.get("PER_INSTANCE_SECONDS", "60"))
VALIDATOR = os.environ.get("ITC_VALIDATOR", "/opt/itc2021/RobinX")


def run_validator(validator, instance_path, solution_path, timeout=300):
    """Run the official RobinX validator; return (hard, soft, error)."""
    try:
        p = subprocess.run(
            [validator, "-i", instance_path, "-s", solution_path],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None, None, "validator timed out"
    except OSError as e:
        return None, None, f"validator failed to start: {e}"
    m = re.search(r"Objective:\s+(\d+)\s+(\d+)", p.stdout)
    if not m:
        tail = ((p.stdout or "") + (p.stderr or ""))[-2000:]
        return None, None, f"validator produced no objective: {tail}"
    return int(m.group(1)), int(m.group(2)), None


def check_schedule(instance_path, out_path):
    """Validate the solver output and recompute its penalty from scratch
    with the official validator. Returns (penalty, None) for a valid
    schedule, else (None, reason)."""
    if not os.path.exists(out_path):
        return None, "no output produced"
    if os.path.getsize(out_path) == 0:
        return None, "empty output"
    hard, soft, err = run_validator(VALIDATOR, instance_path, out_path)
    if err:
        return None, err
    if hard != 0:
        return None, f"{hard} hard-constraint violation(s)"
    return soft, None


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
    The solver learns the remaining pool via env ITC2021_TIME_POOL.
    Returns (seconds, None) on success, (seconds, reason) otherwise.
    """
    env = dict(os.environ)
    env["ITC2021_TIME_POOL"] = f"{remaining_pool:.3f}"
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


def main(argv):
    if len(argv) != 3:
        print(f"usage: {argv[0]} APP_DIR INSTANCES_DIR", file=sys.stderr)
        return 2
    app_dir, instances_dir = argv[1], argv[2]
    names = sorted(f for f in os.listdir(instances_dir)
                   if f.endswith(".xml"))
    pool_seconds = float(os.environ.get(
        "TOTAL_TIME_POOL", str(PER_INSTANCE_SECONDS * len(names))))
    solver, err = build_solver(app_dir)
    if err:
        print(json.dumps({"build_error": err}, indent=1))
        return 1
    work_dir = os.path.join("/tmp", f"itc2021-run-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)
    results = {}
    spent = 0.0
    for name in names:
        inst_path = os.path.join(instances_dir, name)
        out_path = os.path.join(work_dir, name + ".out")
        rec = {"A": None, "status": "ok", "seconds": 0.0}
        remaining = pool_seconds - spent
        if remaining <= 0:
            rec["status"] = "time pool exhausted before this instance"
            results[name] = rec
            continue
        seconds, err = run_solver(solver, inst_path, out_path, remaining)
        spent += seconds
        rec["seconds"] = round(seconds, 2)
        if err is None:
            cost, cerr = check_schedule(inst_path, out_path)
            if cerr is None:
                rec["A"] = cost
            else:
                rec["status"] = f"invalid solution ({cerr})"
        else:
            rec["status"] = err
        results[name] = rec
        print(f"{name}: A={rec['A']} {rec['status']} "
              f"({rec['seconds']}s)", flush=True)
    print(json.dumps({"per_instance": results,
                      "pool_seconds": pool_seconds,
                      "pool_seconds_spent": round(spent, 2)},
                     indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
