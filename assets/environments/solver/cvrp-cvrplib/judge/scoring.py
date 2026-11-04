"""Shared scoring logic for the cvrp-cvrplib task.

Judge-side scoring module (form 2, 2026-09-20): lives in tests/ only — the
judging chain (/tests/checker.py, both channels) imports it; the agent
environment no longer carries any scoring code (the agent-side convenience
runner /app/run_public.py is a self-contained per-instance runner with no
aggregation). The two sides historically shared this file so the formula and
the validity check cannot diverge:

Pipeline: run `bash /app/build.sh` (must produce /app/solver) -> for each
instance, run `solver < instance` with its own wall-clock limit (the process
group is hard-killed at the limit) -> validate the printed routes with
check_cvrp() below (every customer visited exactly once, no depot inside a
route, every route within capacity, at most as many routes as the fleet size
encoded in the instance name's -kK suffix) and recompute the total route
length from the instance coordinates -> A = validated total length ->
per-instance gap ratio r = (B - A) / (B - K), unclipped -> arithmetic mean.
Instances with B == K carry no signal and are excluded from the mean.

Minimization, two anchors: B = total length reported by the shipped baseline
solver (Clarke-Wright savings + deterministic local search; it uses no
randomness and no wall-clock input, so B is a pinned constant, not
machine-speed dependent) and K = the CVRPLIB best-known-solution value (see
PROVENANCE.md); a total length below K is possible in principle on instances
whose library value is not a proven optimum, so raw > 1 is surfaced for
investigation (beat_known_best), never silently dropped;
under the finalized formula it counts unclipped (r > 1).

Distance convention (CVRPLIB, TSPLIB EUC_2D): the distance between two nodes
is the Euclidean distance rounded to the nearest integer, floor(d + 0.5). The
same convention is used by the baseline solver, by this checker, and by the
published best-known values.

Time budget: each instance gets its own wall-clock limit
(PER_INSTANCE_SECONDS). The solver is expected to self-limit below that (the
shipped baseline finishes in seconds); the judge kills the process group at
the limit, and a killed or crashing run scores 0 for that instance. Instances
are evaluated in parallel (JUDGE_JOBS workers, each pinned to a core with
taskset); the solver only ever sees one instance at a time. Validity checking
does not consume the limit.

Formula finalized 2026-09-20: the judged score is the pure gap ratio r —
A=B -> 0, A=K -> 1, beating K -> r > 1, worse than B -> r < 0, with no
[0, 1] clip — averaged over the participating instances by the unified
metric engine (tests/metric/engine.py) from the per-instance raw values
and anchors this file reports. This file's local `score` field still
clips r to [0, 1] and `reward` stays that clipped mean; both are kept
for the retired local-judging pipeline only and are not the judged score.
"""

import json
import math
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
PER_INSTANCE_SECONDS = int(os.environ.get("PER_INSTANCE_SECONDS", "180"))


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


def load_instance(path):
    """TSPLIB/CVRPLIB CVRP format: header keys (NAME, DIMENSION, CAPACITY,
    EDGE_WEIGHT_TYPE), then NODE_COORD_SECTION, DEMAND_SECTION, DEPOT_SECTION,
    EOF. Only EUC_2D instances are used in this task. Returns
    (n, capacity, depot, xs, ys, demand, name) with 1-based node indexing."""
    n = 0
    capacity = None
    depot = None
    name = None
    coords = {}
    demand = {}
    section = None
    with open(path, errors="replace") as f:
        tokens = f.read().split()
    KEYS = {"NAME", "COMMENT", "TYPE", "DIMENSION", "EDGE_WEIGHT_TYPE",
            "EDGE_WEIGHT_FORMAT", "DISPLAY_DATA_TYPE", "CAPACITY",
            "NODE_COORD_SECTION", "DEMAND_SECTION", "DEPOT_SECTION", "EOF"}
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t == "EOF":
            break
        if t in ("NODE_COORD_SECTION", "DEMAND_SECTION", "DEPOT_SECTION"):
            section = t
            i += 1
            continue
        if section and t not in KEYS:
            if section == "NODE_COORD_SECTION" and i + 2 < len(tokens):
                coords[int(tokens[i])] = (float(tokens[i + 1]),
                                          float(tokens[i + 2]))
                i += 3
                continue
            if section == "DEMAND_SECTION" and i + 1 < len(tokens):
                demand[int(tokens[i])] = int(float(tokens[i + 1]))
                i += 2
                continue
            if section == "DEPOT_SECTION":
                v = int(tokens[i])
                if v != -1:
                    depot = v
                i += 1
                continue
        section = None
        if t in ("DIMENSION", "CAPACITY"):
            i += 1
            if i < len(tokens) and tokens[i] == ":":
                i += 1
            if i < len(tokens):
                if t == "DIMENSION":
                    n = int(tokens[i])
                else:
                    capacity = int(tokens[i])
                i += 1
            continue
        # NAME/COMMENT/TYPE/... : skip key, colon and value
        i += 1
        if i < len(tokens) and tokens[i] == ":":
            i += 1
        if t == "NAME":
            if i < len(tokens):
                name = tokens[i]
                i += 1
        elif t == "COMMENT":
            while i < len(tokens) and tokens[i] not in KEYS:
                i += 1
        else:
            i += 1
    if coords:
        n = max(n, max(coords))
    if capacity is None or depot is None or not coords:
        raise ValueError("incomplete instance (need CAPACITY, DEPOT_SECTION, "
                         "NODE_COORD_SECTION)")
    xs = [0.0] * (n + 1)
    ys = [0.0] * (n + 1)
    dem = [0] * (n + 1)
    for v, (x, y) in coords.items():
        xs[v], ys[v] = x, y
    for v, d in demand.items():
        dem[v] = d
    return n, capacity, depot, xs, ys, dem, name


def fleet_from_name(name):
    """The fleet size is part of the instance identity: the NAME (and file
    name) of every instance in this task ends with '-kK', meaning at most K
    routes may be used. Returns None if the name carries no such suffix."""
    if not name:
        return None
    p = name.rfind("-k")
    if p < 0 or p + 2 >= len(name):
        return None
    suffix = name[p + 2:]
    if not suffix.isdigit():
        return None
    v = int(suffix)
    return v if v > 0 else None


def _dist(xs, ys, a, b):
    return int(math.floor(math.hypot(xs[a] - xs[b], ys[a] - ys[b]) + 0.5))


def check_cvrp(instance_path, out_path):
    """Return (cost, None) iff the output is a valid CVRP solution; the total
    route length is recomputed from scratch. Otherwise (None, reason).

    Expected output: token R (number of routes), then for each route a token m
    followed by the m 1-based node ids of its customers in visit order. The
    depot must not appear. Validity: R >= 1, R <= the fleet size (the -kK
    suffix of the instance NAME), every m >= 1, every customer (every node
    except the depot) appears exactly once across all routes, all ids in
    range, no duplicates, every route's total demand within capacity.
    """
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
                return None, f"customer {v} visited twice"
            seen.add(v)
    expected = set(range(1, n + 1)) - {depot}
    if seen != expected:
        missing = sorted(expected - seen)
        first_missing = missing[0] if missing else "?"
        return None, (f"{len(missing)} customers not visited "
                      f"(first: {first_missing})")
    total = 0
    for r in routes:
        load = sum(dem[v] for v in r)
        if load > cap:
            return None, f"route exceeds the capacity ({load} > {cap})"
        prev = depot
        for v in r:
            total += _dist(xs, ys, prev, v)
            prev = v
        total += _dist(xs, ys, prev, depot)
    return total, None


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


def evaluate(solver, instances_dir, reference, work_dir, per_instance_seconds,
             jobs):
    """Run + verify every instance in the reference, in parallel: each
    instance gets its own wall-clock limit and its own core."""
    ncores = _cpu_quota()
    jobs = max(1, min(jobs, ncores))

    def one(name, core):
        inst_path = os.path.join(instances_dir, name)
        out_path = os.path.join(work_dir, name + ".out")
        B, K = reference[name]["B"], reference[name]["K"]
        rec = {"B": B, "K": K, "A": None, "raw": None, "score": 0.0,
               "status": "ok"}
        if not os.path.exists(inst_path):
            rec["status"] = "instance file missing on judge side"
            return name, rec
        secs, err = run_solver(solver, inst_path, out_path,
                               per_instance_seconds, core)
        rec["seconds"] = round(secs, 2)
        if err is None:
            cost, cerr = check_cvrp(inst_path, out_path)
            if cerr is None:
                rec["A"] = cost
            else:
                rec["status"] = f"invalid solution ({cerr})"
        else:
            rec["status"] = err
        if rec["A"] is not None and B > K:
            rec["raw"] = (B - rec["A"]) / (B - K)
            rec["score"] = min(1.0, max(0.0, rec["raw"]))
        return name, rec

    results = {}
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        futures = [ex.submit(one, name, i % jobs)
                   for i, name in enumerate(sorted(reference))]
        for fut in futures:
            name, rec = fut.result()
            results[name] = rec
    return results


def summarize(results, reference):
    """Mean of the legacy clipped local `score` over participating (B > K)
    instances — not the judged score (the judged score is the unclipped
    gap-ratio mean computed by the metric engine; see module docstring)."""
    part = [n for n in results
            if reference[n]["B"] > reference[n]["K"]]
    total = sum(results[n]["score"] for n in part) / len(part) if part else 0.0
    raws = [results[n]["raw"] for n in part if results[n]["raw"] is not None]
    return {
        "reward": total,
        "participating": len(part),
        "excluded_no_signal": sorted(n for n in results if n not in part),
        "mean_raw_unclipped": (sum(raws) / len(raws)) if raws else None,
        "beat_known_best": sorted(
            n for n in part
            if results[n]["A"] is not None
            and results[n]["A"] < reference[n]["K"]
        ),
    }


def load_reference(path):
    with open(path) as f:
        data = json.load(f)
    return data["instances"]


def main(argv):
    if len(argv) != 4:
        print(f"usage: {argv[0]} APP_DIR INSTANCES_DIR REFERENCE_JSON",
              file=sys.stderr)
        return 2
    app_dir, instances_dir, ref_path = argv[1], argv[2], argv[3]
    reference = load_reference(ref_path)
    work_dir = os.path.join("/tmp", f"cvrp-score-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)

    solver, err = build_solver(app_dir)
    if err:
        return {"reward": 0.0, "build_error": err, "per_instance": {}}
    results = evaluate(solver, instances_dir, reference, work_dir,
                       PER_INSTANCE_SECONDS, JUDGE_JOBS)
    out = summarize(results, reference)
    out["per_instance_seconds"] = PER_INSTANCE_SECONDS
    out["judge_jobs"] = max(1, min(JUDGE_JOBS, _cpu_quota()))
    out["per_instance"] = results
    return out


if __name__ == "__main__":
    print(json.dumps(main(sys.argv), indent=1, sort_keys=True))
