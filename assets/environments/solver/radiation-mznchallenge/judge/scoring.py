"""Shared scoring logic for the radiation-mznchallenge task.

Used by BOTH sides so the validity check and the formula cannot diverge:
  - agent side:  /app/score_public.py   (public instances, public reference)
  - judge side:  /tests/checker.py      (hidden instances, hidden reference)

Pipeline: run `bash /app/build.sh` (must produce /app/solver) -> for each
instance, run `/app/solver INSTANCE_PATH` with a hard per-instance wall-clock
limit (the solver learns it via env RADIATION_TIME_LIMIT, in seconds) -> take
the LAST complete solution block on stdout ("N = [...];" followed by
"Q = array3d(..., [...]);") -> validate it with check_solution() below and
recompute everything from scratch -> per-instance gap ratio r = (B - A) / (B - K), unclipped -> arithmetic mean.  Instances with B == K carry no signal
and are excluded.

Time budget (2026-09-04, aligned with the official MiniZinc Challenge
rule): each instance gets its own wall-clock limit of PER_INSTANCE_SECONDS
(1200 s — the MiniZinc Challenge per-instance budget). Instances are
evaluated in parallel (JUDGE_JOBS workers, each pinned to a core with
taskset); the solver only ever sees one instance at a time. Validity
checking does not consume the limit.

Scoring contract (260831 rework — shapes at minimum beam-on time):

The problem (as defined by the shipped MiniZinc model radiation.mzn): given
an m x n intensity matrix, choose nonnegative integers N[b] (how many shape
matrices carry beam-on time b) and Q[i,j,b] (how many of those expose cell
(i,j)) such that
  (C1) for every cell (i,j):  Intensity[i,j] = sum_b b * Q[i,j,b]
  (C2) for every row i and every b:
       N[b] >= Q[i,1,b] + sum_{j>=2} max(Q[i,j,b] - Q[i,j-1,b], 0)

Every feasible decomposition obeys a structural lower bound on the total
beam-on time:  weighting the C2 row constraint by b and summing over b gives
  Beamtime = sum_b b*N[b]  >=  t_i   for every row i, where
  t_i = Intensity[i,1] + sum_{j>=2} max(Intensity[i,j]-Intensity[i,j-1],0)
so Beamtime >= LB = max_i t_i.  The judged (and shipped practice) instances
are verified to ADMIT a decomposition with Beamtime == LB, so on them the
bound is exactly attainable.

Under the old lexicographic objective ((m*n+1)*Beamtime + shapes), reaching
Beamtime == LB alone — a structural observation, not search — already
cancelled the dominant (m*n+1)-amplified term against K and scored ~1
without touching the shape minimization, which is the actually hard part.
The reworked scoring therefore makes the bound an ADMISSION TICKET:

  - A solution with Beamtime > LB scores 0 for that instance (reported as
    "beam-on time X above structural lower bound Y"), exactly like an
    invalid one.  Beamtime < LB is impossible by the argument above.
  - A solution with Beamtime == LB is scored on its SHAPE COUNT alone:
    A = sum_b N[b], raw = (B - A) / (B - K) (unclipped gap ratio), where B is
    the baseline pipeline's shape count at Beamtime == LB and K the best
    known shape count at Beamtime == LB (see tests/SAMPLING.md).

check_solution() verifies exactly C1/C2, recomputes Beamtime, the shape
count and the bound LB from the instance — the same code runs on both
sides, and nothing the solver prints beyond the N/Q arrays is trusted.

The raw unclipped values are reported per instance; raw > 1 means the
submission beat the reference shape count K.  That should be rare; it is
surfaced for investigation, never silently dropped;
under the finalized formula it counts unclipped (r > 1).

Formula finalized 2026-09-20: the judged score is the pure gap ratio r —
A=B -> 0, A=K -> 1, beating K -> r > 1, worse than B -> r < 0, with no
[0, 1] clip — averaged over the participating instances by the unified
metric engine (tests/metric/engine.py) from the per-instance raw values
and anchors this file reports. This file's local `score` field still
clips r to [0, 1] and `reward` stays that clipped mean; both are kept
for the retired local-judging pipeline only and are not the judged score.
"""

import json
import os
import re
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
# Hard per-instance wall-clock limit in seconds (no shared pool: every
# instance gets the same limit, MiniZinc-Challenge style; 2026-09-04 aligned
# to the official MiniZinc Challenge budget of 1200 s per instance).
PER_INSTANCE_SECONDS = float(os.environ.get("PER_INSTANCE_SECONDS", "1200"))


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
    """Parse a radiation .dzn file. Returns (m, n, intensity) with intensity
    a flat row-major list of m*n nonnegative integers."""
    with open(path, errors="replace") as f:
        text = f.read()
    mm = re.search(r"\bm\s*=\s*(\d+)\s*;", text)
    mn = re.search(r"\bn\s*=\s*(\d+)\s*;", text)
    arr = re.search(r"Intensity\s*=\s*\[\|(.*?)\|\]\s*;", text, re.S)
    if not (mm and mn and arr):
        raise ValueError("could not parse m, n and Intensity from the dzn")
    m, n = int(mm.group(1)), int(mn.group(1))
    vals = [int(x) for x in re.findall(r"-?\d+", arr.group(1))]
    if len(vals) != m * n:
        raise ValueError(f"Intensity has {len(vals)} entries, expected {m*n}")
    if any(v < 0 for v in vals):
        raise ValueError("negative intensity value")
    return m, n, vals


def beamtime_lower_bound(m, n, intensity):
    """Structural lower bound on the total beam-on time: the maximum per-row
    total positive gradient of the intensity matrix,
        LB = max_i ( I[i,1] + sum_{j>=2} max(I[i,j]-I[i,j-1], 0) ).
    Any C1/C2-feasible decomposition has Beamtime >= LB (see module doc).
    """
    lb = 0
    for i in range(m):
        base = i * n
        t = intensity[base]
        for j in range(1, n):
            d = intensity[base + j] - intensity[base + j - 1]
            if d > 0:
                t += d
        if t > lb:
            lb = t
    return lb


def _parse_int_list(text, start):
    """Parse a bracketed integer list starting at text[start] == '['.
    Returns (values, end_index_after_closing_bracket) or (None, None)."""
    if start >= len(text) or text[start] != "[":
        return None, None
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                body = text[start + 1:i]
                vals = [int(x) for x in re.findall(r"-?\d+", body)]
                return vals, i + 1
    return None, None


def parse_output(text, m, n):
    """Scan solver stdout for solution blocks. A block is `N = [<ints>];`
    followed (anywhere later) by `Q = array3d(<dims>, [<ints>]);`. Returns
    (N, Q) of the LAST complete block, or (None, None) if none found."""
    best = (None, None)
    for nm in re.finditer(r"\bN\s*=", text):
        lb = text.find("[", nm.end())
        if lb < 0:
            continue
        vals, end = _parse_int_list(text, lb)
        if vals is None:
            continue
        qm = re.search(r"\bQ\s*=\s*array3d\s*\(", text[end:])
        if not qm:
            continue
        qstart = end + qm.end()
        lb = text.find("[", qstart)
        if lb < 0:
            continue
        qvals, qend = _parse_int_list(text, lb)
        if qvals is None:
            continue
        best = (vals, qvals)
    return best


def check_solution(instance_path, out_path):
    """Return (result, None) iff the last complete N/Q block in the output
    is valid, where result = {"objective", "beamtime", "shapes", "lb"} with
    everything recomputed from scratch ("objective" keeps the legacy
    lexicographic value for reporting; scoring uses "beamtime"/"shapes").
    Otherwise (None, reason).  The admission check (beamtime vs lb) is NOT
    done here — that is the scoring layer's job (evaluate())."""
    try:
        m, n, intensity = load_instance(instance_path)
    except (ValueError, OSError) as e:
        return None, f"could not load instance: {e}"
    try:
        with open(out_path, errors="replace") as f:
            text = f.read()
    except OSError as e:
        return None, f"could not read solver output: {e}"
    bt_max = max(intensity) if intensity else 0
    N, Q = parse_output(text, m, n)
    if N is None:
        return None, "no complete N/Q solution block found on stdout"
    if len(N) != bt_max:
        return None, f"N has {len(N)} entries, expected {bt_max}"
    if len(Q) != m * n * bt_max:
        return None, f"Q has {len(Q)} entries, expected {m*n*bt_max}"
    if any(v < 0 for v in N) or any(v < 0 for v in Q):
        return None, "negative entry in N or Q"
    # (C1) per-cell intensity equation: Intensity[i,j] = sum_b b * Q[i,j,b]
    for i in range(m):
        for j in range(n):
            s = 0
            for b in range(bt_max):
                s += (b + 1) * Q[(i * n + j) * bt_max + b]
            if s != intensity[i * n + j]:
                return None, (f"cell ({i+1},{j+1}): sum b*Q = {s} "
                              f"!= intensity {intensity[i*n+j]}")
    # (C2) per-row aperture count: N[b] >= Q[i,1,b] + sum max(diff, 0)
    for b in range(bt_max):
        for i in range(m):
            need = Q[(i * n + 0) * bt_max + b]
            for j in range(1, n):
                d = (Q[(i * n + j) * bt_max + b]
                     - Q[(i * n + j - 1) * bt_max + b])
                if d > 0:
                    need += d
            if N[b] < need:
                return None, (f"row {i+1}, b={b+1}: N={N[b]} < required "
                              f"apertures {need}")
    beamtime = sum((b + 1) * N[b] for b in range(bt_max))
    shapes = sum(N)
    result = {
        "objective": (m * n + 1) * beamtime + shapes,
        "beamtime": beamtime,
        "shapes": shapes,
        "lb": beamtime_lower_bound(m, n, intensity),
    }
    return result, None


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


def _descendants(root_pid):
    """All current descendant PIDs of root_pid (walk /proc ppid links)."""
    children = {}
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        try:
            with open(f"/proc/{name}/stat", errors="replace") as f:
                tail = f.read().rsplit(")", 1)[1].split()
            children[int(name)] = int(tail[1])
        except (OSError, IndexError, ValueError):
            continue
    found = []
    frontier = [root_pid]
    seen = {root_pid}
    while frontier:
        cur = frontier.pop()
        for pid, ppid in children.items():
            if ppid == cur and pid not in seen:
                seen.add(pid)
                found.append(pid)
                frontier.append(pid)
    return found


def run_solver(solver, instance_path, out_path, limit_seconds, core=None):
    """Run `solver INSTANCE_PATH > out_path` with a hard wall-clock kill at
    limit_seconds, optionally pinned to a core via taskset. The solver
    learns the limit via env RADIATION_TIME_LIMIT.
    A kill is NOT an error per se (the solver may have printed improving
    solutions); whatever complete blocks exist are scored. Returns
    (seconds, None) or (seconds, reason).

    The kill sweeps the whole descendant tree, not just the solver's
    process group: the MiniZinc CLI re-sessions the FlatZinc solver it
    spawns, so a plain killpg leaves the FlatZinc process orphaned and
    burning CPU into the next instance's slot.
    """
    env = dict(os.environ)
    env["RADIATION_TIME_LIMIT"] = f"{limit_seconds:.3f}"
    cmd = ([solver, instance_path] if core is None
           else ["taskset", "-c", str(core), solver, instance_path])
    t0 = time.time()
    with open(out_path, "w") as fout:
        p = subprocess.Popen(
            cmd, stdout=fout, env=env,
            stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            p.wait(timeout=limit_seconds)
        except subprocess.TimeoutExpired:
            sweep = _descendants(p.pid)
            os.killpg(p.pid, signal.SIGKILL)
            for pid in sweep:
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
            p.wait()
            return time.time() - t0, None  # killed at the limit; score output
    seconds = time.time() - t0
    if p.returncode != 0:
        return seconds, f"solver exited with code {p.returncode}"
    return seconds, None


def evaluate(solver, instances_dir, reference, work_dir, limit_seconds,
             jobs):
    """Run + check every instance in the reference, in parallel: each
    instance gets its own wall-clock limit and its own core.

    Scoring (260831 rework): a valid solution must attain the structural
    beam-on-time lower bound LB to score at all (Beamtime > LB -> 0 for
    that instance); scoring is then on the shape count alone,
    raw = (B - A) / (B - K) with B/K shape counts from the reference.
    """
    ncores = _cpu_quota()
    jobs = max(1, min(jobs, ncores))

    def one(name, core):
        inst_path = os.path.join(instances_dir, name)
        out_path = os.path.join(work_dir, name + ".out")
        B, K = reference[name]["B"], reference[name]["K"]
        rec = {"B": B, "K": K, "A": None, "raw": None, "score": 0.0,
               "status": "ok", "seconds": 0.0}
        if reference[name].get("practice_no_anchors") is True:
            rec["practice_no_anchors"] = True
        if not os.path.exists(inst_path):
            rec["status"] = "instance file missing on judge side"
            return name, rec
        seconds, err = run_solver(solver, inst_path, out_path,
                                  limit_seconds, core)
        rec["seconds"] = round(seconds, 2)
        if err is None:
            res, cerr = check_solution(inst_path, out_path)
            if cerr is not None:
                rec["status"] = f"invalid solution ({cerr})"
            else:
                rec["beamtime"] = res["beamtime"]
                rec["lb"] = res["lb"]
                lb_ref = reference[name].get("lb")
                if lb_ref is not None and lb_ref != res["lb"]:
                    rec["status"] = (f"judge-side reference inconsistency "
                                     f"(reference lb {lb_ref} != recomputed "
                                     f"{res['lb']})")
                elif res["beamtime"] > res["lb"]:
                    rec["status"] = (f"beam-on time {res['beamtime']} above "
                                     f"structural lower bound {res['lb']}")
                else:
                    rec["A"] = res["shapes"]
        else:
            rec["status"] = err
        if rec["A"] is not None and B is not None and K is not None and B > K:
            rec["raw"] = (B - rec["A"]) / (B - K)
            rec["score"] = min(1.0, max(0.0, rec["raw"]))
        return name, rec

    results = {}
    spent = 0.0
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        futures = [ex.submit(one, name, i % jobs)
                   for i, name in enumerate(sorted(reference))]
        for fut in futures:
            name, rec = fut.result()
            spent += rec["seconds"]
            results[name] = rec
    return results, spent


def summarize(results, reference, limit_seconds, spent):
    """Mean of the legacy clipped local `score` over participating (B > K)
    instances — not the judged score (the judged score is the unclipped
    gap-ratio mean computed by the metric engine; see module docstring)."""
    practice = sorted(n for n in results
                      if reference[n].get("practice_no_anchors") is True)
    part = [n for n in results
            if reference[n]["B"] is not None and reference[n]["K"] is not None
            and reference[n]["B"] > reference[n]["K"]]
    total = sum(results[n]["score"] for n in part) / len(part) if part else 0.0
    raws = [results[n]["raw"] for n in part if results[n]["raw"] is not None]
    return {
        "reward": total,
        "participating": len(part),
        "excluded_B_equals_K": sorted(n for n in results
                                      if n not in part and n not in practice),
        "practice_no_anchors": practice,
        "mean_raw_unclipped": (sum(raws) / len(raws)) if raws else None,
        "per_instance_seconds": limit_seconds,
        "seconds_spent": round(spent, 2),
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
    work_dir = os.path.join("/tmp", f"radiation-score-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)
    limit_seconds = float(os.environ.get(
        "PER_INSTANCE_SECONDS", str(PER_INSTANCE_SECONDS)))

    solver, err = build_solver(app_dir)
    if err:
        return {"reward": 0.0, "build_error": err, "per_instance": {}}
    results, spent = evaluate(solver, instances_dir, reference, work_dir,
                              limit_seconds, JUDGE_JOBS)
    out = summarize(results, reference, limit_seconds, spent)
    out["judge_jobs"] = max(1, min(JUDGE_JOBS, _cpu_quota()))
    out["per_instance"] = results
    return out


if __name__ == "__main__":
    print(json.dumps(main(sys.argv), indent=1, sort_keys=True))
