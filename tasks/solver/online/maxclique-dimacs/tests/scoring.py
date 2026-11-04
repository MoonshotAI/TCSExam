"""Shared scoring logic for the maxclique-dimacs task.

Judge side only — no
scoring code ships in the agent environment:
  - judge side:  /tests/checker.py      (hidden instances, hidden reference)
The agent-side local convenience runner (/app/run_public.py via
/opt/maxclique/public_runner.py) re-implements only the build/run/validate
machinery and deliberately shares no anchors or formula.

Pipeline: run `bash /app/build.sh` (must produce /app/solver) -> for each
instance, run `solver < instance` with its own wall-clock limit (the process
group is hard-killed at the limit) -> validate the printed clique with
check_clique() below (every vertex in range, no duplicates, every pair
adjacent in the graph) and recompute its size -> A = validated clique size ->
per-instance gap ratio r = (A - B) / (K - B), unclipped -> arithmetic mean.
Instances with K <= B carry no signal and are excluded from the mean.

Maximization, two anchors: B = clique size reported by the shipped baseline
solver (the anytime MaxCliqueDyn, whose default self-limit is a fixed search
-node budget, so B is a pinned constant, not machine-speed dependent) and
K = the best known clique size from the literature mirror page (see
PROVENANCE.md); a clique larger than K is possible in principle on instances
whose literature value is not a proven optimum, so raw > 1 is surfaced for
investigation (beat_known_best), never silently dropped;
under the finalized formula it counts unclipped (r > 1).

Time budget: each instance gets its own wall-clock limit
(PER_INSTANCE_SECONDS). The solver is expected to self-limit below that (the
shipped baseline stops at its node budget or MAXCLIQUE_SECONDS, whichever
comes first, and then prints its best clique so far); the judge kills the
process group at the limit, and a killed or crashing run scores 0 for that
instance. Instances are evaluated in parallel (JUDGE_JOBS workers, each
pinned to a core with taskset); the solver only ever sees one instance at a
time. Validity checking does not consume the limit.

Scoring formula: the judged score is the pure gap ratio r —
A=B -> 0, A=K -> 1, beating K -> r > 1, worse than B -> r < 0, with no
[0, 1] clip — averaged over the participating instances by the unified
metric engine (tests/metric/engine.py) from the per-instance raw values
and anchors this file reports. This file's local `score` field still
clips r to [0, 1] and `reward` stays that clipped mean; both are kept
for the retired local-judging pipeline only and are not the judged score.
"""

import json
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
CHECK_TIMEOUT = int(os.environ.get("CHECK_TIMEOUT", "300"))
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
    """DIMACS ASCII graph: `c` comment lines, one `p edge n m` header, then
    `e u v` lines (1-based endpoints). The header's m is advisory (some
    library files count both edge directions); the graph is built from the
    `e` lines. Returns (n, adj) with adj a list of integer bitsets."""
    n = -1
    vmax = 0
    edges = []
    with open(path, errors="replace") as f:
        for line in f:
            if not line or line[0] in "c\r\n":
                continue
            c0 = line[0]
            if c0 == "p":
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        n = int(parts[2])
                    except ValueError:
                        pass
            elif c0 == "e":
                parts = line.split()
                if len(parts) < 3:
                    continue
                try:
                    u = int(parts[1])
                    v = int(parts[2])
                except ValueError:
                    continue
                if u == v or u < 1 or v < 1:
                    continue
                edges.append((u - 1, v - 1))
                if u > vmax:
                    vmax = u
                if v > vmax:
                    vmax = v
    if n < vmax:
        n = vmax
    if n < 0:
        raise ValueError("no p line and no edges")
    adj = [0] * n
    for u, v in edges:
        adj[u] |= 1 << v
        adj[v] |= 1 << u
    return n, adj


def check_clique(instance_path, out_path):
    """Return (size, None) iff the output is a valid clique; the size is
    recomputed from scratch. Otherwise (None, reason)."""
    try:
        n, adj = load_instance(instance_path)
    except (ValueError, OSError) as e:
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
    k = vals[0]
    if k < 1:
        return None, "declared clique size k < 1"
    if len(vals) != k + 1:
        return None, f"expected {k + 1} tokens, found {len(vals)}"
    vs = vals[1:]
    seen = set()
    for v in vs:
        if v < 1 or v > n:
            return None, f"vertex {v} out of range 1..{n}"
        if v in seen:
            return None, f"vertex {v} duplicated"
        seen.add(v)
    idx = [v - 1 for v in vs]
    for i in range(k):
        ai = adj[idx[i]]
        for j in range(i + 1, k):
            if not (ai >> idx[j]) & 1:
                return None, f"non-edge between {idx[i] + 1} and {idx[j] + 1}"
    return k, None


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
            size, cerr = check_clique(inst_path, out_path)
            if cerr is None:
                rec["A"] = size
            else:
                rec["status"] = f"invalid solution ({cerr})"
        else:
            rec["status"] = err
        if rec["A"] is not None and K > B:
            rec["raw"] = (rec["A"] - B) / (K - B)
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
    """Mean of the legacy clipped local `score` over participating (K > B)
    instances — not the judged score (the judged score is the unclipped
    gap-ratio mean computed by the metric engine; see module docstring)."""
    part = [n for n in results
            if reference[n]["K"] > reference[n]["B"]]
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
            and results[n]["A"] > reference[n]["K"]
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
    work_dir = os.path.join("/tmp", f"maxclique-score-{os.getpid()}")
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
