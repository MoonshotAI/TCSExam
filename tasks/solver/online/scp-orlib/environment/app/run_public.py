#!/usr/bin/env python3
"""Run your solver on the public practice set locally and print per-instance
results — a convenience runner, not a scorer.

Usage:  python3 /app/run_public.py
Rebuilds via /app/build.sh, then runs your solver once per instance under one
shared total time pool (30 s per instance x instance count, no per-instance
limit — the same budget rule the judging service uses), validates each printed
cover and recomputes its cost. It prints, per instance: your cost A, the
validity status, and the two reference values from
/app/public_reference.json (B = the shipped baseline's result, K = a
best-known value). It computes NO aggregate score.

It runs on this development box, outside the judging sandbox — use
`submit.sh` for authoritative measurements.
"""
import json
import os
import signal
import subprocess
import sys
import time

PER_INSTANCE_SECONDS = float(os.environ.get("PER_INSTANCE_SECONDS", "30"))
BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))


def load_instance(path):
    """Canonical layout: m, n, then n costs, then m row blocks."""
    with open(path) as f:
        vals = f.read().split()
    m, n = int(vals[0]), int(vals[1])
    costs = [int(v) for v in vals[2:2 + n]]
    pos = 2 + n
    rows = []
    for _ in range(m):
        k = int(vals[pos])
        pos += 1
        rows.append([int(v) for v in vals[pos:pos + k]])
        pos += k
    if pos != len(vals):
        raise ValueError(f"trailing tokens: consumed {pos}, found {len(vals)}")
    return m, n, costs, rows


def check_scp(instance_path, out_path):
    """Return (cost, None) iff the output is a valid cover; the cost is
    recomputed from scratch. Otherwise (None, reason)."""
    try:
        m, n, costs, rows = load_instance(instance_path)
    except (ValueError, OSError, IndexError) as e:
        return None, f"could not load instance: {e}"
    try:
        with open(out_path, errors="replace") as f:
            tokens = f.read().split()
    except OSError as e:
        return None, f"could not read solver output: {e}"
    if not tokens:
        return None, "empty output"
    try:
        sel = [int(t) for t in tokens]
    except ValueError:
        return None, "output contains a non-integer token"
    if len(sel) != len(set(sel)):
        return None, "a column index appears more than once"
    for j in sel:
        if j < 1 or j > n:
            return None, f"column index {j} out of range 1..{n}"
    selset = set(sel)
    for i, cols in enumerate(rows, start=1):
        if not any(j in selset for j in cols):
            return None, f"row {i} is not covered"
    return sum(costs[j - 1] for j in sel), None


def main():
    app_dir = "/app"
    instances_dir = os.path.join(app_dir, "instances")
    with open(os.path.join(app_dir, "public_reference.json")) as f:
        reference = json.load(f)["instances"]

    p = subprocess.run(["bash", "build.sh"], cwd=app_dir,
                       stdin=subprocess.DEVNULL, capture_output=True,
                       text=True, timeout=BUILD_TIMEOUT)
    solver = os.path.join(app_dir, "solver")
    if not (os.path.exists(solver) and os.access(solver, os.X_OK)):
        tail = ((p.stdout or "") + (p.stderr or ""))[-2000:]
        sys.exit(f"build.sh did not produce an executable /app/solver\n{tail}")

    names = sorted(os.listdir(instances_dir))
    pool = PER_INSTANCE_SECONDS * len(names)
    spent = 0.0
    work = os.path.join("/tmp", f"scp-run-public-{os.getpid()}")
    os.makedirs(work, exist_ok=True)
    print(f"running {len(names)} public instances under one shared pool of "
          f"{pool:.0f} s (30 s x count, no per-instance limit)...")
    for name in names:
        inst = os.path.join(instances_dir, name)
        out = os.path.join(work, name + ".out")
        remaining = pool - spent
        if remaining <= 0:
            print(f"{name}: time pool exhausted before this instance")
            continue
        env = dict(os.environ)
        env["SCP_TIME_POOL"] = f"{remaining:.3f}"
        t0 = time.time()
        with open(inst) as fin, open(out, "w") as fout:
            proc = subprocess.Popen([solver], stdin=fin, stdout=fout, env=env,
                                    stderr=subprocess.DEVNULL,
                                    start_new_session=True)
            try:
                proc.wait(timeout=remaining)
                err = None
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
                err = "time pool exhausted during this instance"
        seconds = time.time() - t0
        spent += seconds
        if err is None and proc.returncode != 0:
            err = f"solver exited with code {proc.returncode}"
        if err is None:
            cost, cerr = check_scp(inst, out)
            if cerr is None:
                ref = reference.get(name, {})
                print(f"{name}: A={cost} valid "
                      f"(B={ref.get('B')}, K={ref.get('K')}) [{seconds:.2f}s]")
            else:
                print(f"{name}: invalid solution ({cerr}) [{seconds:.2f}s]")
        else:
            print(f"{name}: {err} [{seconds:.2f}s]")
    print(f"pool spent: {spent:.2f} s of {pool:.0f} s. Reference values B/K "
          f"per instance are in /app/public_reference.json.")


if __name__ == "__main__":
    main()
