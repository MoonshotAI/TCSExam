"""Shared scoring logic for the coloring-dimacs task.

Judge side only — no
scoring code ships in the agent environment:
  - judge side:  /tests/checker.py      (hidden instances, hidden reference)
The agent-side local convenience runner (/app/run_public.py via
/opt/coloring/public_runner.py) re-implements only the build/run/validate
machinery and deliberately shares no anchors or formula.

Pipeline: run `bash /app/build.sh` (must produce /app/solver) -> for each
instance, run `solver < instance` with its own wall-clock limit (the process
group is hard-killed at the limit) -> validate the printed coloring with
check_coloring() below (one color per vertex, every edge bichromatic) and
RECOMPUTE the number of colors actually used -> A = recomputed color count ->
per-instance gap ratio r = (B - A) / (B - K), unclipped -> arithmetic mean.
Instances with B <= K carry no signal and are excluded from the mean.

Minimization, two anchors: B = number of colors reported by the shipped
baseline solver (a textbook TabuCol whose default self-limit is a fixed
iteration budget with a fixed RNG seed, so B is a pinned constant, not
machine-speed dependent) and K = the best known number of colors from the
literature tables (see PROVENANCE.md); a coloring with fewer colors than K is
possible in principle on instances whose literature value is not a proven
optimum, so raw > 1 is surfaced for investigation (beat_known_best), never silently dropped;
under the finalized formula it counts unclipped (r > 1).

Time budget: each instance gets its own wall-clock limit
(PER_INSTANCE_SECONDS). The solver is expected to self-limit below that (the
shipped baseline stops at its iteration budget or COLOR_SECONDS, whichever
comes first, and then prints its best coloring so far); the judge kills the
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
    `e` lines. Returns (n, adj) with adj a list of sorted neighbor lists."""
    n = -1
    vmax = 0
    edges = set()
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
                if u > v:
                    u, v = v, u
                edges.add((u - 1, v - 1))
                if u > vmax:
                    vmax = u
                if v > vmax:
                    vmax = v
    if n < vmax:
        n = vmax
    if n < 0:
        raise ValueError("no p line and no edges")
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    return n, adj


def check_coloring(instance_path, out_path):
    """Return (ncolors, None) iff the output is a valid proper coloring; the
    number of colors is recomputed from scratch (the declared count is NOT
    trusted). Otherwise (None, reason)."""
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
        return None, "declared color count k < 1"
    if len(vals) != n + 1:
        return None, f"expected {n + 1} tokens (k + n colors), found {len(vals)}"
    colors = vals[1:]
    seen_colors = set()
    for v, c in enumerate(colors):
        if c < 1 or c > n:
            return None, f"color {c} of vertex {v + 1} out of range 1..{n}"
        seen_colors.add(c)
    # every edge must join two different colors (recomputed from the graph)
    for u in range(n):
        cu = colors[u]
        for v in adj[u]:
            if v > u and colors[v] == cu:
                return None, f"monochromatic edge between {u + 1} and {v + 1}"
    return len(seen_colors), None


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
            ncolors, cerr = check_coloring(inst_path, out_path)
            if cerr is None:
                rec["A"] = ncolors
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
    work_dir = os.path.join("/tmp", f"coloring-score-{os.getpid()}")
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
