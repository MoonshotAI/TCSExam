#!/usr/bin/env python3
"""Run your solver on the public practice set locally and print per-instance
results — a convenience runner, not a scorer.

Usage:  python3 /app/run_public.py
Rebuilds via /app/build.sh, then runs your solver once per instance under one
shared total time pool (30 s per instance x instance count, no per-instance
limit — the same budget rule the judging service uses), validates each printed
packing and recomputes its bin count. It prints, per instance: your bin
count A, the validity status, and the two reference values from
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
    """BPP instance text format: n, C, then n integer weights."""
    with open(path) as f:
        vals = f.read().split()
    n, C = int(vals[0]), int(vals[1])
    w = [int(v) for v in vals[2:]]
    if len(w) != n:
        raise ValueError(f"expected {n} weights, found {len(w)}")
    return n, C, w


def check_bpp(instance_path, out_path):
    """Return (bins, None) iff the output is a valid packing; the bin count
    is recomputed from scratch. Otherwise (None, reason)."""
    try:
        n, C, w = load_instance(instance_path)
    except (ValueError, OSError) as e:
        return None, f"could not load instance: {e}"
    try:
        with open(out_path, errors="replace") as f:
            tokens = f.read().split()
    except OSError as e:
        return None, f"could not read solver output: {e}"
    if len(tokens) != n + 1:
        return None, f"expected {n + 1} tokens, found {len(tokens)}"
    try:
        vals = [int(t) for t in tokens]
    except ValueError:
        return None, "output contains a non-integer token"
    B = vals[0]
    if B < 1:
        return None, "declared bin count B < 1"
    assign = vals[1:]
    load = [0] * B
    for j, b in enumerate(assign):
        if b < 1 or b > B:
            return None, f"bin index {b} out of range 1..{B}"
        load[b - 1] += w[j]
        if load[b - 1] > C:
            return None, f"bin {b} exceeds the capacity"
    return B, None


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
    work = os.path.join("/tmp", f"bpp-run-public-{os.getpid()}")
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
        env["BPP_TIME_POOL"] = f"{remaining:.3f}"
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
            cost, cerr = check_bpp(inst, out)
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
