"""Shared scoring logic for the gp-dimacs10 task.

Judge side only — no
scoring code ships in the agent environment:
  - judge side:  /tests/checker.py      (hidden instances, hidden reference)
The agent-side local convenience runner (/app/run_public.py via
/opt/gp/public_runner.py) re-implements only the build/run/validate
machinery and deliberately shares no anchors or formula.

Pipeline: run `bash /app/build.sh` (must produce /app/solver) -> for each
instance, run `solver < instance` with the REMAINING time pool in env
GP_TIME_POOL (hard-killed when the pool is exhausted; no per-instance
limit) -> validate the printed partition and recompute its edge cut with
check_gp() below -> A = cut of the (valid) partition -> per-instance gap ratio r = (B - A) / (B - K), unclipped -> arithmetic mean. Instances with
B == K carry no signal and are excluded.

The task is fixed at k = 4 blocks with a 3% balance tolerance in the
Walshaw archive convention: a partition is valid iff every block holds at
most floor(1.03 * n / 4) vertices. Validity + objective are recomputed
from the instance and the printed partition alone; nothing the solver
claims about itself is trusted.

Graph format: METIS/DIMACS10 — optional '%' comment lines, a header line
"n m", then n lines where line i lists the neighbours of vertex i (1-based
ids). All judging/public instances are undirected and unweighted.

Time budget: ONE TOTAL TIME POOL covers all instances — there is no
per-instance limit. The pool size is
    TOTAL_POOL = PER_INSTANCE_SECONDS * number_of_instances
and the solver learns the remaining pool via env GP_TIME_POOL on every
run; when the pool is used up, every instance without a verified result
scores 0. Validity checking does not consume the pool.

The raw unclipped values are reported per instance; raw > 1 means the
submission beat the reference best cut and is investigated, never silently dropped;
under the finalized formula it counts unclipped (r > 1).

Scoring formula: the judged score is the pure gap ratio r —
A=B -> 0, A=K -> 1, beating K -> r > 1, worse than B -> r < 0, with no
[0, 1] clip — averaged over the participating instances by the unified
metric engine (tests/metric/engine.py) from the per-instance raw values
and anchors this file reports. This file's local `score` field still
clips r to [0, 1] and `reward` stays that clipped mean; both are kept
for the retired local-judging pipeline only and are not the judged score.
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
# Per-instance reference seconds; total pool = this value x instance count.
# The judge enforces the pool globally, NOT per instance.
PER_INSTANCE_SECONDS = float(os.environ.get("PER_INSTANCE_SECONDS", "60"))

K_BLOCKS = 4
# Balance rule (DIMACS10 rules §1.1.1): block weight <= (1+eps)*ceil(n/k)
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
        xadj = array("q", [0])  # 64-bit offsets
        adjncy = array("i")     # 32-bit vertex ids (n < 2^31)
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
    # official form: cap = floor((1+eps) * ceil(n/k)); ceil first, then scale
    ceil_nk = (n + K_BLOCKS - 1) // K_BLOCKS
    cap = ((100 + EPSILON_PERCENT) * ceil_nk) // 100
    block_w = [0] * K_BLOCKS
    for p in part:
        block_w[p] += 1
    for b, w in enumerate(block_w):
        if w > cap:
            return None, (f"block {b} has {w} vertices, exceeds the 3% "
                          f"balance cap {cap}")
    # recompute the edge cut: directed crossing arcs, halved
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


def evaluate(solver, instances_dir, reference, work_dir, pool_seconds):
    """Run + check every instance in the reference under one shared pool."""
    results = {}
    spent = 0.0
    for name in sorted(reference):
        inst_path = os.path.join(instances_dir, name)
        if not os.path.exists(inst_path) and os.path.exists(inst_path + ".bz2"):
            inst_path = inst_path + ".bz2"  # compressed storage on disk
        out_path = os.path.join(work_dir, name + ".out")
        B, K = reference[name]["B"], reference[name]["K"]
        rec = {"B": B, "K": K, "A": None, "raw": None, "score": 0.0,
               "status": "ok", "seconds": 0.0}
        if not os.path.exists(inst_path):
            rec["status"] = "instance file missing on judge side"
            results[name] = rec
            continue
        remaining = pool_seconds - spent
        if remaining <= 0:
            rec["status"] = "time pool exhausted before this instance"
            results[name] = rec
            continue
        seconds, err = run_solver(solver, inst_path, out_path, remaining)
        spent += seconds
        rec["seconds"] = round(seconds, 2)
        if err is None:
            cut, cerr = check_gp(inst_path, out_path)
            if cerr is None:
                rec["A"] = cut
            else:
                rec["status"] = f"invalid solution ({cerr})"
        else:
            rec["status"] = err
        if rec["A"] is not None and B > K:
            rec["raw"] = (B - rec["A"]) / (B - K)
            rec["score"] = min(1.0, max(0.0, rec["raw"]))
        results[name] = rec
    return results, spent


def summarize(results, reference, pool_seconds, spent):
    """Mean of the legacy clipped local `score` over participating (B > K)
    instances — not the judged score (the judged score is the unclipped
    gap-ratio mean computed by the metric engine; see module docstring)."""
    part = [n for n in results if reference[n]["B"] > reference[n]["K"]]
    total = sum(results[n]["score"] for n in part) / len(part) if part else 0.0
    raws = [results[n]["raw"] for n in part if results[n]["raw"] is not None]
    return {
        "reward": total,
        "participating": len(part),
        "excluded_B_equals_K": sorted(n for n in results if n not in part),
        "mean_raw_unclipped": (sum(raws) / len(raws)) if raws else None,
        "pool_seconds": pool_seconds,
        "pool_seconds_spent": round(spent, 2),
        "beat_known_best": sorted(
            n for n in part
            if results[n]["A"] is not None and results[n]["A"] < reference[n]["K"]
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
    work_dir = os.path.join("/tmp", f"gp-score-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)
    pool_seconds = float(os.environ.get(
        "TOTAL_TIME_POOL", str(PER_INSTANCE_SECONDS * len(reference))))

    solver, err = build_solver(app_dir)
    if err:
        return {"reward": 0.0, "build_error": err, "per_instance": {}}
    results, spent = evaluate(solver, instances_dir, reference, work_dir,
                              pool_seconds)
    out = summarize(results, reference, pool_seconds, spent)
    out["per_instance"] = results
    return out


if __name__ == "__main__":
    print(json.dumps(main(sys.argv), indent=1, sort_keys=True))
