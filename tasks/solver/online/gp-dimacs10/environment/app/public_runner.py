#!/usr/bin/env python3
"""Local public-instance runner for the gp-dimacs10 task.

This is a convenience runner for the agent's dev box only — the scoring
logic (anchors, formula, aggregation) is NOT part of it. Pipeline:
run `bash /app/build.sh` (must produce /app/solver) -> for each public
instance, run `solver < instance` with the REMAINING time pool in env
GP_TIME_POOL (hard-killed when the pool is exhausted; no per-instance
limit) -> validate the printed partition with check_gp() (all n tokens in
{0..3}, every block within the 3% balance cap) and recompute its edge
cut. ONE TOTAL TIME POOL covers all instances (PER_INSTANCE_SECONDS, 60
by default, x instance count); validity checking does not consume the
pool.

Prints one record per instance: name, A (recomputed edge cut), validity
status, seconds used. Nothing is aggregated.

This dev box is NOT the judging sandbox: core count, memory, and timing
behavior differ here. Treat the results of submit.sh (public practice
channel) as authoritative.
"""
import bz2
import json
import os
import signal
import subprocess
import sys
import time
from array import array

BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
CHECK_TIMEOUT = 60
PER_INSTANCE_SECONDS = float(os.environ.get("PER_INSTANCE_SECONDS", "60"))

K_BLOCKS = 4
EPSILON_PERCENT = 3


def _open(path):
    """Instances may be stored plain (.graph) or bzip2-compressed (.graph.bz2)."""
    if path.endswith(".bz2"):
        return bz2.open(path, "rt")
    return open(path)


def load_instance(path):
    """METIS/DIMACS10 format -> (n, m, xadj, adjncy) as compact arrays."""
    with _open(path) as f:
        n = m = None
        for line in f:
            s = line.strip()
            if not s or s.startswith("%"):
                continue
            parts = s.split()
            if len(parts) < 2:
                raise ValueError("malformed header line")
            n, m = int(parts[0]), int(parts[1])
            fmt = parts[2] if len(parts) > 2 else "0"
            if fmt != "0":
                raise ValueError(f"weighted graphs unsupported (fmt={fmt})")
            break
        if n is None:
            raise ValueError("empty instance file")
        xadj = array("q", [0])
        adjncy = array("i")
        v = 0
        for line in f:
            s = line.strip()
            if s.startswith("%"):
                continue
            if s:
                adjncy.extend(int(t) - 1 for t in s.split())
            xadj.append(len(adjncy))
            v += 1
            if v == n:
                break
        if v != n:
            raise ValueError(f"expected {n} adjacency lines, found {v}")
        if len(adjncy) != 2 * m:
            raise ValueError(f"expected {2 * m} adjacency tokens, found {len(adjncy)}")
    return n, m, xadj, adjncy


def check_gp(instance_path, out_path):
    """Return (cut, None) iff the output is a valid balanced k-partition; the
    cut is recomputed from scratch. Otherwise (None, reason)."""
    try:
        n, m, xadj, adjncy = load_instance(instance_path)
    except (ValueError, OSError, EOFError) as e:
        return None, f"could not load instance: {e}"
    try:
        with open(out_path, errors="replace") as f:
            tokens = f.read().split()
    except OSError as e:
        return None, f"could not read solver output: {e}"
    if len(tokens) != n:
        return None, f"expected {n} tokens, found {len(tokens)}"
    part = array("i")
    try:
        for t in tokens:
            part.append(int(t))
    except ValueError:
        return None, "output contains a non-integer token"
    for p in part:
        if p < 0 or p >= K_BLOCKS:
            return None, f"block id {p} outside 0..{K_BLOCKS - 1}"
    ceil_nk = (n + K_BLOCKS - 1) // K_BLOCKS
    cap = ((100 + EPSILON_PERCENT) * ceil_nk) // 100
    block_w = [0] * K_BLOCKS
    for p in part:
        block_w[p] += 1
    for b, w in enumerate(block_w):
        if w > cap:
            return None, (f"block {b} has {w} vertices, exceeds the 3% "
                          f"balance cap {cap}")
    crossing = 0
    for u in range(n):
        pu = part[u]
        for e in range(xadj[u], xadj[u + 1]):
            if part[adjncy[e]] != pu:
                crossing += 1
    if crossing % 2:
        return None, "instance adjacency is not symmetric (cannot score)"
    return crossing // 2, None


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

    Instances stored as .bz2 are decompressed on the fly into the solver's
    stdin. The solver learns the remaining pool via env GP_TIME_POOL and is
    free to use as much of it as it wants on this instance. Returns
    (seconds, None) on success, (seconds, reason) otherwise.
    """
    env = dict(os.environ)
    env["GP_TIME_POOL"] = f"{remaining_pool:.3f}"
    t0 = time.time()
    decomp = None
    if instance_path.endswith(".bz2"):
        decomp = subprocess.Popen(["bunzip2", "-kc", instance_path],
                                  stdout=subprocess.PIPE)
        fin = decomp.stdout
    else:
        fin = open(instance_path, "rb")
    with fin, open(out_path, "w") as fout:
        p = subprocess.Popen(
            [solver], stdin=fin, stdout=fout, env=env,
            stderr=subprocess.DEVNULL, start_new_session=True,
        )
        try:
            p.wait(timeout=remaining_pool)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
            if decomp:
                decomp.kill()
            if decomp:
                decomp.wait()
            return time.time() - t0, "time pool exhausted during this instance"
    if decomp:
        decomp.wait()
    seconds = time.time() - t0
    if p.returncode != 0:
        return seconds, f"solver exited with code {p.returncode}"
    return seconds, None


def main(argv):
    if len(argv) != 4:
        print(f"usage: {argv[0]} APP_DIR INSTANCES_DIR REFERENCE_JSON",
              file=sys.stderr)
        return 2
    app_dir, instances_dir, ref_path = argv[1:4]
    with open(ref_path) as f:
        names = sorted(json.load(f)["instances"])
    work_dir = os.path.join("/tmp", f"gp-run-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)
    pool_seconds = float(os.environ.get(
        "TOTAL_TIME_POOL", str(PER_INSTANCE_SECONDS * len(names))))

    solver, err = build_solver(app_dir)
    if err:
        print(json.dumps({"build_error": err}, indent=1))
        return 1

    spent = 0.0
    for name in names:
        inst_path = os.path.join(instances_dir, name)
        if not os.path.exists(inst_path) and os.path.exists(inst_path + ".bz2"):
            inst_path = inst_path + ".bz2"
        out_path = os.path.join(work_dir, name + ".out")
        rec = {"instance": name, "A": None, "status": "ok", "seconds": 0.0}
        if not os.path.exists(inst_path):
            rec["status"] = "instance file missing"
            print(json.dumps(rec, sort_keys=True), flush=True)
            continue
        remaining = pool_seconds - spent
        if remaining <= 0:
            rec["status"] = "time pool exhausted before this instance"
            print(json.dumps(rec, sort_keys=True), flush=True)
            continue
        seconds, err2 = run_solver(solver, inst_path, out_path, remaining)
        spent += seconds
        rec["seconds"] = round(seconds, 2)
        if err2 is None:
            cut, cerr = check_gp(inst_path, out_path)
            if cerr is None:
                rec["A"] = cut
            else:
                rec["status"] = f"invalid solution ({cerr})"
        else:
            rec["status"] = err2
        print(json.dumps(rec, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
