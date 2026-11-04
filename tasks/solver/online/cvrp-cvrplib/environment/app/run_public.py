#!/usr/bin/env python3
"""Run your solver on the public practice set locally and print per-instance
results — a convenience runner, not a scorer.

Usage:  python3 /app/run_public.py [jobs]
Rebuilds via /app/build.sh, then runs your solver once per instance with the
same 180 s per-instance wall-clock limit the judge uses (parallel workers,
one per core, each pinned with taskset; the process group is hard-killed at
the limit), validates each printed route set, and recomputes its total
length. It prints, per instance: your total length A, the validity status,
and the two reference values from /app/public_reference.json (B = the
shipped baseline's result, K = a best-known value). It computes NO
aggregate score.

It runs on this development box, outside the judging sandbox — use
`submit.sh` for authoritative measurements.
"""
import json
import math
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

PER_INSTANCE_SECONDS = int(os.environ.get("PER_INSTANCE_SECONDS", "180"))
BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))


def load_instance(path):
    """TSPLIB/CVRPLIB .vrp (EUC_2D): header keys, NODE_COORD_SECTION,
    DEMAND_SECTION, DEPOT_SECTION."""
    with open(path, errors="replace") as f:
        tokens = f.read().split()
    header = {}
    xs, ys, dem = {}, {}, {}
    depot = None
    section = None
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t == "EOF":
            break
        if t in ("NODE_COORD_SECTION", "DEMAND_SECTION", "DEPOT_SECTION"):
            section = t
            i += 1
            continue
        if section == "NODE_COORD_SECTION":
            xs[int(tokens[i])] = float(tokens[i + 1])
            ys[int(tokens[i])] = float(tokens[i + 2])
            i += 3
            continue
        if section == "DEMAND_SECTION":
            dem[int(tokens[i])] = int(tokens[i + 1])
            i += 2
            continue
        if section == "DEPOT_SECTION":
            v = int(tokens[i])
            if v != -1:
                depot = v
            i += 1
            continue
        section = None
        key = t
        i += 1
        if i < len(tokens) and tokens[i] == ":":
            i += 1
        if i < len(tokens):
            header[key] = tokens[i] if key != "COMMENT" else " ".join(
                [tokens[i]] + ([] if i + 1 >= len(tokens) else []))
            i += 1
    n = int(header["DIMENSION"])
    cap = int(header["CAPACITY"])
    return n, cap, depot, xs, ys, dem, header.get("NAME", "")


def fleet_from_name(name):
    import re
    m = re.search(r"-k(\d+)$", name or "")
    return int(m.group(1)) if m else None


def dist(xs, ys, a, b):
    return int(math.floor(math.hypot(xs[a] - xs[b], ys[a] - ys[b]) + 0.5))


def check_cvrp(instance_path, out_path):
    """Return (cost, None) iff the output is a valid CVRP solution; the total
    route length is recomputed from scratch. Otherwise (None, reason)."""
    try:
        n, cap, depot, xs, ys, dem, name = load_instance(instance_path)
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
        vals = [int(t) for t in tokens]
    except ValueError:
        return None, "output contains a non-integer token"
    R = vals[0]
    if R < 1:
        return None, "declared route count R < 1"
    fleet = fleet_from_name(name)
    if fleet is not None and R > fleet:
        return None, f"uses {R} routes, more than the fleet limit {fleet}"
    routes = []
    i = 1
    for _ in range(R):
        if i >= len(vals):
            return None, "ran out of tokens while reading routes"
        m = vals[i]
        i += 1
        if m < 1:
            return None, "a route with fewer than 1 customer"
        if i + m > len(vals):
            return None, "ran out of tokens inside a route"
        routes.append(vals[i:i + m])
        i += m
    if i != len(vals):
        return None, f"trailing tokens: consumed {i}, found {len(vals)}"
    seen = set()
    for r in routes:
        for v in r:
            if v < 1 or v > n:
                return None, f"node {v} out of range 1..{n}"
            if v == depot:
                return None, "depot appears inside a route"
            if v in seen:
                return None, f"node {v} visited more than once"
            seen.add(v)
    if len(seen) != n - 1:
        return None, f"visited {len(seen)} of {n - 1} customers"
    total = 0
    for r in routes:
        if sum(dem[v] for v in r) > cap:
            return None, "a route exceeds the capacity"
        prev = depot
        for v in r:
            total += dist(xs, ys, prev, v)
            prev = v
        total += dist(xs, ys, prev, depot)
    return total, None


def one(args):
    name, inst_path, out_path, solver, budget, core, ref = args
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cmd = ["taskset", "-c", str(core), solver]
    t0 = time.time()
    with open(inst_path) as fin, open(out_path, "w") as fout:
        p = subprocess.Popen(cmd, stdin=fin, stdout=fout,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        try:
            p.wait(timeout=budget)
            note = None
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
            note = "exceeded the per-instance limit; hard-killed"
    secs = time.time() - t0
    if note is None and p.returncode != 0:
        note = f"solver exited with code {p.returncode}"
    value, verr = check_cvrp(inst_path, out_path)
    status = note or verr or "ok"
    return name, value, status, secs, ref


def main():
    jobs = int(sys.argv[1]) if len(sys.argv) > 1 else (os.cpu_count() or 1)
    jobs = max(1, min(jobs, os.cpu_count() or 1))
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
    work = f"/tmp/cvrp-run-public-{os.getpid()}"
    print(f"running {len(names)} public instances with a "
          f"{PER_INSTANCE_SECONDS} s per-instance limit ({jobs} parallel "
          f"workers, pinned cores)...")
    args = [(name, os.path.join(instances_dir, name),
             os.path.join(work, name + ".out"),
             solver, PER_INSTANCE_SECONDS, i % jobs, reference.get(name, {}))
            for i, name in enumerate(names)]
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        for name, value, status, secs, ref in ex.map(one, args):
            print(f"{name}: A={value} {status} (B={ref.get('B')}, "
                  f"K={ref.get('K')}) [{secs:.2f}s]")
    print("done. Reference values B/K per instance are in "
          "/app/public_reference.json.")


if __name__ == "__main__":
    main()
