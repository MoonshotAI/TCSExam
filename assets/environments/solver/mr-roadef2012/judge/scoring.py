"""Shared scoring logic for the mr-roadef2012 task.

Used by BOTH sides so the formula and the validity check cannot diverge:
  - agent side:  /app/score_public.py   (public instances, public reference)
  - judge side:  /tests/checker.py      (hidden instances, hidden reference)
The judge side uses its own pristine copy of this file under /tests (never
the agent-writable /opt copy) and its own freshly compiled checker binary.

Pipeline: run `bash /app/build.sh` (must produce /app/solver) -> for each
instance, run `solver MODEL INITIAL_ASSIGNMENT OUTPUT` with the
PER-INSTANCE wall-clock budget in env MR_INSTANCE_SECONDS (hard-killed at
the limit) -> validate the produced assignment with the OFFICIAL
ROADEF/EURO 2012 solution checker (vendored C++ source, compiled at image
build / verify time) which recomputes the objective from scratch -> A = that
objective -> per-instance gap ratio r = (B - A) / (B - K), unclipped -> arithmetic mean. Instances with B == K carry no signal and are excluded.

Validity: entirely decided by the official checker binary. It prints
"Solution is valid. Total objective cost is N" on success, "Solution is
invalid." when a hard constraint fails, and aborts on malformed files; only
the first form yields a value. The solver's own claims are never trusted.

Time budget (2026-09-06, aligned with the official ROADEF/EURO 2012 final
rule): EACH INSTANCE gets its own wall-clock limit of PER_INSTANCE_SECONDS
(300 s = the 5 minutes per instance of the official final, on a dedicated
machine — roadef.org/challenge/2012/en/reponse.php). There is no shared
pool and no redistribution — the solver sees one instance at a time and
may use the full per-instance budget on it. The budget is handed to the
solver via env MR_INSTANCE_SECONDS, and the legacy name MR_TIME_POOL is
set to the same value so solvers written against the old shared-pool
contract still see a correct per-instance limit. Instances are evaluated
in parallel (JUDGE_JOBS workers, each pinned to a core with taskset).
Checker runs do not consume the budget. A solver run that is killed
mid-instance leaves whatever OUTPUT file it already wrote — if that file
holds a valid assignment it still counts.

The raw unclipped values are reported per instance; raw > 1 means the
submission beat the reference best known value and is investigated, never silently dropped;
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
CHECK_TIMEOUT = int(os.environ.get("CHECK_TIMEOUT", "180"))
# Per-instance wall-clock budget in seconds (ROADEF/EURO 2012 final
# official: 5 minutes per instance).
PER_INSTANCE_SECONDS = float(os.environ.get("PER_INSTANCE_SECONDS", "300"))
# The official checker binary; the judge side overrides this to its own
# freshly compiled copy.
CHECKER_BIN = os.environ.get("MR_CHECKER_BIN", "/opt/mr/checker")

COST_RE = re.compile(r"Solution is valid\. Total objective cost is (\d+)")


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


def run_solver(solver, model_path, init_path, out_path, limit_seconds,
               core=None):
    """Run solver MODEL INITIAL OUTPUT with a hard per-instance wall-clock
    limit, optionally pinned to a core via taskset.

    The solver learns the limit via env MR_INSTANCE_SECONDS (the legacy
    name MR_TIME_POOL is set to the same value) and is free to use as much
    of it as it wants on this instance. Returns (seconds, None) on exit
    code 0, (seconds, reason) otherwise.
    """
    env = dict(os.environ)
    env["MR_INSTANCE_SECONDS"] = f"{limit_seconds:.3f}"
    env["MR_TIME_POOL"] = f"{limit_seconds:.3f}"  # legacy name, same value
    t0 = time.time()
    with open(out_path, "w") as fout:
        fout.close()
        cmd = [solver, model_path, init_path, out_path]
        if core is not None:
            cmd = ["taskset", "-c", str(core)] + cmd
        p = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, env=env, start_new_session=True,
        )
        try:
            p.wait(timeout=limit_seconds)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
            return time.time() - t0, "per-instance time limit exhausted"
    seconds = time.time() - t0
    if p.returncode != 0:
        return seconds, f"solver exited with code {p.returncode}"
    return seconds, None


def check_solution(model_path, init_path, out_path):
    """Run the official checker. Return (cost, None) iff it reports a valid
    solution; otherwise (None, reason)."""
    if not (os.path.exists(out_path) and os.path.getsize(out_path) > 0):
        return None, "solver produced no output file"
    try:
        p = subprocess.run(
            [CHECKER_BIN, model_path, init_path, out_path],
            stdin=subprocess.DEVNULL, capture_output=True, text=True,
            timeout=CHECK_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return None, f"checker timed out after {CHECK_TIMEOUT}s"
    m = COST_RE.search(p.stdout or "")
    if p.returncode == 0 and m:
        return int(m.group(1)), None
    tail = ((p.stdout or "") + (p.stderr or ""))[-200:].strip()
    return None, f"invalid solution (checker exit {p.returncode}: {tail})"


def evaluate(solver, instances_dir, reference, work_dir, limit_seconds,
             jobs):
    """Run + check every instance in the reference, in parallel: each
    instance gets its own wall-clock limit and its own core."""
    ncores = _cpu_quota()
    jobs = max(1, min(jobs, ncores))

    def one(name, core):
        ent = reference[name]
        model_path = os.path.join(instances_dir, ent["model"])
        init_path = os.path.join(instances_dir, ent["assignment"])
        out_path = os.path.join(work_dir, name + ".out")
        B, K = ent["B"], ent["K"]
        rec = {"B": B, "K": K, "A": None, "raw": None, "score": 0.0,
               "status": "ok", "seconds": 0.0}
        if ent.get("practice_no_anchors") is True:
            rec["practice_no_anchors"] = True
        if not (os.path.exists(model_path) and os.path.exists(init_path)):
            rec["status"] = "instance file missing on judge side"
            return name, rec
        seconds, err = run_solver(solver, model_path, init_path, out_path,
                                  limit_seconds, core)
        rec["seconds"] = round(seconds, 2)
        if err is not None:
            # A killed solver may still have written a valid assignment;
            # the checker decides. Note the timeout in the record.
            cost, cerr = check_solution(model_path, init_path, out_path)
            if cerr is None:
                rec["A"] = cost
                rec["status"] = f"ok (solver note: {err})"
            else:
                rec["status"] = f"{err}; {cerr}"
        else:
            cost, cerr = check_solution(model_path, init_path, out_path)
            if cerr is None:
                rec["A"] = cost
            else:
                rec["status"] = cerr
        if rec["A"] is not None and B is not None and K is not None and B > K:
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


def summarize(results, reference, limit_seconds, jobs):
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
        "judge_jobs": jobs,
        "beat_known_best": sorted(
            n for n in part
            if results[n]["A"] is not None and results[n]["A"] < reference[n]["K"]
        ),
    }


def load_reference(path):
    with open(path) as f:
        data = json.load(f)
    per_inst = data.get("meta", {}).get("per_instance_seconds")
    return data["instances"], float(per_inst or PER_INSTANCE_SECONDS)


def main(argv):
    if len(argv) != 4:
        print(f"usage: {argv[0]} APP_DIR INSTANCES_DIR REFERENCE_JSON",
              file=sys.stderr)
        return 2
    app_dir, instances_dir, ref_path = argv[1], argv[2], argv[3]
    reference, limit_seconds = load_reference(ref_path)
    limit_seconds = float(os.environ.get("PER_INSTANCE_SECONDS",
                                         str(limit_seconds)))
    work_dir = os.path.join("/tmp", f"mr-score-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)

    solver, err = build_solver(app_dir)
    if err:
        return {"reward": 0.0, "build_error": err, "per_instance": {}}
    results = evaluate(solver, instances_dir, reference, work_dir,
                       limit_seconds, JUDGE_JOBS)
    out = summarize(results, reference, limit_seconds,
                    max(1, min(JUDGE_JOBS, _cpu_quota())))
    out["per_instance"] = results
    return out


if __name__ == "__main__":
    print(json.dumps(main(sys.argv), indent=1, sort_keys=True))
