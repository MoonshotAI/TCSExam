"""Local public-instance runner for the logic-syn-iwls2023 task.

This is a convenience runner for the agent's dev box only. It rebuilds via
/app/build.sh, runs the public practice instances under one shared total
time pool (PER_INSTANCE_SECONDS x instance count, no per-instance limit —
the solver learns the remaining pool from env LS_TIME_POOL on every run and
decides how to distribute it; hard-killed when the pool is exhausted),
validates each produced circuit by exhaustive simulation against the truth
table, and prints one line per instance: name, A (number of two-input AND
gates), validity status, seconds used. Nothing is aggregated.

This dev box is NOT the judging sandbox: core count, memory, and timing
behavior differ here. Treat the results of submit.sh (public practice
channel) as authoritative.

Validity: entirely decided by the aiglib check — functional equivalence
against the truth table by exhaustive simulation. The solver's own claims
are never trusted; there is nothing to trust but the circuit file itself.

A solver run that is killed mid-instance leaves whatever OUTPUT file it
already wrote — if that file holds a valid equivalent circuit it still
counts.
"""

import json
import os
import signal
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aiglib

BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
CHECK_TIMEOUT = int(os.environ.get("CHECK_TIMEOUT", "300"))
# Per-instance reference seconds; total pool = this value x instance count.
# The judge enforces the pool globally, NOT per instance.
PER_INSTANCE_SECONDS = float(os.environ.get("PER_INSTANCE_SECONDS", "180"))
# Hard caps against denial-of-service submissions.
MAX_AIG_FILE_BYTES = 64 * 1024 * 1024
MAX_AND_GATES = 2_000_000


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


def run_solver(solver, truth_path, out_path, remaining_pool):
    """Run solver TRUTH OUTPUT with hard timeout = remaining pool.

    The solver learns the remaining pool via env LS_TIME_POOL and is free
    to use as much of it as it wants on this instance. Returns
    (seconds, None) on exit code 0, (seconds, reason) otherwise.
    """
    env = dict(os.environ)
    env["LS_TIME_POOL"] = f"{remaining_pool:.3f}"
    t0 = time.time()
    with open(out_path, "w"):
        pass  # truncate any stale output from a previous run
    p = subprocess.Popen(
        [solver, truth_path, out_path],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, env=env, start_new_session=True,
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


def check_circuit(truth_path, out_path):
    """Validate the produced circuit against the truth table.

    Return (and_count, None) iff the file is a well-formed combinational
    binary AIGER circuit computing exactly the reference function;
    otherwise (None, reason).
    """
    if not (os.path.exists(out_path) and os.path.getsize(out_path) > 0):
        return None, "solver produced no output file"
    if os.path.getsize(out_path) > MAX_AIG_FILE_BYTES:
        return None, f"output file exceeds {MAX_AIG_FILE_BYTES} bytes"
    t0 = time.time()
    try:
        with open(truth_path) as f:
            n, masks = aiglib.parse_truth(f.read())
    except ValueError as e:
        return None, f"judge-side truth file broken: {e}"
    try:
        with open(out_path, "rb") as f:
            data = f.read()
        aig = aiglib.parse_aiger(data, max_and=MAX_AND_GATES)
    except aiglib.AigerError as e:
        return None, f"invalid AIGER: {e}"
    try:
        err = aiglib.check_circuit(aig, n, masks)
    except ValueError as e:
        return None, f"simulation failed: {e}"
    if time.time() - t0 > CHECK_TIMEOUT:
        return None, f"checker timed out after {CHECK_TIMEOUT}s"
    if err is not None:
        return None, err
    return aig.n_ands, None


def main(argv):
    if len(argv) != 3:
        print(f"usage: {argv[0]} APP_DIR INSTANCES_DIR", file=sys.stderr)
        return 2
    app_dir, instances_dir = argv[1], argv[2]
    names = sorted(f[:-len(".truth")] for f in os.listdir(instances_dir)
                   if f.endswith(".truth"))
    if not names:
        print(f"no instances (*.truth) found in {instances_dir}",
              file=sys.stderr)
        return 2
    work_dir = os.path.join("/tmp", f"ls-run-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)
    pool_seconds = float(os.environ.get(
        "TOTAL_TIME_POOL", str(PER_INSTANCE_SECONDS * len(names))))

    solver, err = build_solver(app_dir)
    if err:
        print(f"BUILD FAILED: {err}", file=sys.stderr)
        return 1

    spent = 0.0
    for name in names:
        truth_path = os.path.join(instances_dir, name + ".truth")
        out_path = os.path.join(work_dir, name + ".aig")
        remaining = pool_seconds - spent
        if remaining <= 0:
            print(f"{name}\tA=-\ttime pool exhausted before this instance",
                  flush=True)
            continue
        seconds, rerr = run_solver(solver, truth_path, out_path, remaining)
        spent += seconds
        if rerr is not None:
            # A killed solver may still have written a valid circuit;
            # the checker decides.
            cost, cerr = check_circuit(truth_path, out_path)
            if cerr is None:
                print(f"{name}\tA={cost}\tok (solver note: {rerr})"
                      f"\t{seconds:.2f}s", flush=True)
            else:
                print(f"{name}\tA=-\t{rerr}; {cerr}\t{seconds:.2f}s",
                      flush=True)
        else:
            cost, cerr = check_circuit(truth_path, out_path)
            if cerr is None:
                print(f"{name}\tA={cost}\tok\t{seconds:.2f}s", flush=True)
            else:
                print(f"{name}\tA=-\t{cerr}\t{seconds:.2f}s", flush=True)
    print(f"pool: {spent:.2f}s of {pool_seconds:.0f}s used", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
