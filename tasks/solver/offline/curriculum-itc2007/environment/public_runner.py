"""Public-instance runner for the curriculum-itc2007 task (agent-side
convenience).

This is NOT the judging code. It rebuilds /app via `bash /app/build.sh`,
runs /app/solver on every instance in a directory (each under its own hard
per-instance wall-clock limit; the solver learns it via env
CTT_TIME_LIMIT), validates the printed timetable with the OFFICIAL
validator binary, and recomputes the soft-constraint cost from scratch.
It reports per-instance results only: instance name, the recomputed cost
A, validity, and seconds used. No reference values, no aggregation, no
scoring formula.

Validity: the official validator recomputes every hard constraint from
scratch (Lectures, Conflicts, Availability, RoomOccupation); a timetable
is valid iff all four hard-violation counts are zero; the cost A is the
validator's own "Total Cost".
"""
import json
import os
import re
import signal
import subprocess
import sys
import time

BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
VALIDATOR = os.environ.get("CTT_VALIDATOR", "/opt/ctt/validator")
CHECK_TIMEOUT = 120
PER_INSTANCE_SECONDS = float(os.environ.get("PER_INSTANCE_SECONDS", "240"))

HARD_RE = re.compile(r"Violations of (Lectures|Conflicts|Availability|"
                     r"RoomOccupation) \(hard\) : (\d+)")
COST_RE = re.compile(r"Total Cost = (\d+)")


def check_ctt(instance_path, out_path):
    """Return (cost, None) iff the output is a feasible timetable; the cost
    is recomputed by the official validator. Otherwise (None, reason)."""
    if not os.path.exists(VALIDATOR):
        return None, f"validator binary missing at {VALIDATOR}"
    try:
        p = subprocess.run(
            [VALIDATOR, instance_path, out_path],
            capture_output=True, text=True, timeout=CHECK_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return None, f"validator timed out after {CHECK_TIMEOUT}s"
    except OSError as e:
        return None, f"could not run validator: {e}"
    out = p.stdout or ""
    if p.returncode != 0:
        tail = (out + (p.stderr or ""))[-500:]
        return None, f"validator exited with code {p.returncode}: {tail}"
    hard = {m.group(1): int(m.group(2)) for m in HARD_RE.finditer(out)}
    if len(hard) != 4:
        return None, "validator output missing hard-constraint summary"
    bad = {k: v for k, v in hard.items() if v != 0}
    if bad:
        return None, "hard constraint violations: " + ", ".join(
            f"{k}={v}" for k, v in sorted(bad.items()))
    m = COST_RE.search(out)
    if not m:
        return None, "validator output missing total cost"
    return int(m.group(1)), None


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


def run_solver(solver, instance_path, out_path, limit_seconds):
    """Run solver < instance > out_path with a hard timeout of
    limit_seconds. The solver learns this run's limit via env
    CTT_TIME_LIMIT. Returns (seconds, None) on success, (seconds, reason)
    otherwise.
    """
    env = dict(os.environ)
    env["CTT_TIME_LIMIT"] = f"{limit_seconds:.3f}"
    t0 = time.time()
    with open(instance_path) as fin, open(out_path, "w") as fout:
        p = subprocess.Popen(
            [solver], stdin=fin, stdout=fout, env=env,
            stderr=subprocess.DEVNULL, start_new_session=True,
        )
        try:
            p.wait(timeout=limit_seconds)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
            return time.time() - t0, f"timeout after {limit_seconds:g}s"
    seconds = time.time() - t0
    if p.returncode != 0:
        return seconds, f"solver exited with code {p.returncode}"
    return seconds, None


def main(argv):
    if len(argv) != 3:
        print(f"usage: {argv[0]} APP_DIR INSTANCES_DIR", file=sys.stderr)
        return 2
    app_dir, instances_dir = argv[1], argv[2]
    limit_seconds = float(os.environ.get(
        "PER_INSTANCE_SECONDS", str(PER_INSTANCE_SECONDS)))
    names = sorted(f for f in os.listdir(instances_dir)
                   if f.endswith(".ctt"))
    solver, err = build_solver(app_dir)
    if err:
        print(json.dumps({"build_error": err}, indent=1))
        return 1
    work_dir = os.path.join("/tmp", f"ctt-run-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)
    results = {}
    for name in names:
        inst_path = os.path.join(instances_dir, name)
        out_path = os.path.join(work_dir, name + ".out")
        rec = {"A": None, "status": "ok", "seconds": 0.0}
        seconds, err = run_solver(solver, inst_path, out_path, limit_seconds)
        rec["seconds"] = round(seconds, 2)
        if err is None:
            cost, cerr = check_ctt(inst_path, out_path)
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
                      "per_instance_seconds": limit_seconds},
                     indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
