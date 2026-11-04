"""Shared scoring logic for the ds-pace2025 task.

Used by BOTH sides so the formula and the verifier cannot diverge:
  - agent side:  /app/score_public.py   (public instances, public reference)
  - judge side:  /tests/checker.py      (hidden instances, hidden reference)

Pipeline: compile all /app/*.cpp -> for each instance, run the solver with
its own wall-clock limit in env DS_TIME_POOL (hard-killed on expiry; the
official PACE 2025 per-instance limit is 300 s) -> validate with the
official PACE 2025 Java verifier -> per-instance gap ratio r = (B - A) / (B - K), unclipped -> arithmetic mean over instances with B > K. Instances
are evaluated in parallel (JUDGE_JOBS workers, each pinned to a core).

Formula finalized 2026-09-20: the judged score is the pure gap ratio r —
A=B -> 0, A=K -> 1, beating K -> r > 1, worse than B -> r < 0, with no
[0, 1] clip — averaged over the participating instances by the unified
metric engine (tests/metric/engine.py) from the per-instance raw values
and anchors this file reports. This file's local `score` field still
clips r to [0, 1] and `reward` stays that clipped mean; both are kept
for the retired local-judging pipeline only and are not the judged score.
"""

import glob
import json
import os
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

VERIFIER_JAR = os.environ.get("VERIFIER_JAR", "/opt/ds2025/ds_verifier.jar")
JAVA_XMX = os.environ.get("JAVA_XMX", "4g")
COMPILE_TIMEOUT = int(os.environ.get("COMPILE_TIMEOUT", "300"))
VERIFY_TIMEOUT = int(os.environ.get("VERIFY_TIMEOUT", "300"))
# Official PACE 2025 per-instance wall-clock limit (seconds).
PER_INSTANCE_SECONDS = float(os.environ.get("PER_INSTANCE_SECONDS", "300"))
JUDGE_JOBS = int(os.environ.get("JUDGE_JOBS", "0")) or max(1, (os.cpu_count() or 1))
# The Java verifier needs ~3.1 GB RSS on the largest instances; an
# unlucky all-workers-verify-at-once wave would otherwise multiply that
# by JUDGE_JOBS and OOM the judge box. Verifies are ~15 s against 300 s
# solves, so bounding their concurrency costs no meaningful wall time.
VERIFY_CONC = int(os.environ.get("VERIFY_CONC", "4"))
_verify_sem = threading.BoundedSemaphore(max(1, VERIFY_CONC))


def compile_solver(app_dir, work_dir):
    """Compile every top-level .cpp/.cc in app_dir into one binary."""
    srcs = sorted(
        glob.glob(os.path.join(app_dir, "*.cpp"))
        + glob.glob(os.path.join(app_dir, "*.cc"))
    )
    if not srcs:
        return None, "no C++ sources (*.cpp/*.cc) found in /app"
    out = os.path.join(work_dir, "solver")
    cmd = ["g++", "-O2", "-std=c++17", "-o", out] + srcs
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=COMPILE_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None, f"compile timed out after {COMPILE_TIMEOUT}s"
    if p.returncode != 0:
        return None, "compile failed:\n" + (p.stderr or "")[-4000:]
    return out, None


def run_solver(solver, instance_path, sol_path, limit_seconds, core=None):
    """Run solver < instance > sol_path with a hard wall-clock limit,
    optionally pinned to a core via taskset.

    The solver learns the limit via env DS_TIME_POOL and is free to use as
    much of it as it wants on this instance. Returns (seconds, None) on
    success, (seconds, reason) otherwise.
    """
    env = dict(os.environ)
    env["DS_TIME_POOL"] = f"{limit_seconds:.3f}"
    cmd = [solver] if core is None else ["taskset", "-c", str(core), solver]
    t0 = time.time()
    with open(instance_path) as fin, open(sol_path, "w") as fout:
        p = subprocess.Popen(
            cmd, stdin=fin, stdout=fout, env=env,
            stderr=subprocess.DEVNULL, start_new_session=True,
        )
        try:
            p.wait(timeout=limit_seconds)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
            return time.time() - t0, "time limit exhausted during this instance"
    seconds = time.time() - t0
    if p.returncode != 0:
        return seconds, f"solver exited with code {p.returncode}"
    return seconds, None


def verify_solution(instance_path, sol_path):
    """Official PACE 2025 DS verifier (Java). On success its stdout line is
    'Solution of size <k> is valid!'. Returns (k, None) or (None, reason).
    Concurrency-bounded: the JVM needs ~3.1 GB RSS on the giants."""
    with _verify_sem:
        try:
            p = subprocess.run(
                ["java", f"-Xmx{JAVA_XMX}", "-jar", VERIFIER_JAR,
                 instance_path, sol_path],
                capture_output=True, text=True, timeout=VERIFY_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return None, "verifier timed out"
    out = (p.stdout or "").strip()
    marker = "is valid!"
    if marker in out:
        try:
            seg = [ln for ln in out.splitlines() if marker in ln][0]
            return int(seg.split("Solution of size")[1].split("is valid")[0]), None
        except (ValueError, IndexError):
            return None, f"unparseable verifier output: {out[:200]!r}"
    msg = (p.stderr or "").strip() or out or f"verifier exit {p.returncode}"
    return None, f"invalid solution ({msg[-300:]})"


def evaluate(solver, instances_dir, reference, work_dir, per_instance_seconds,
             jobs):
    """Run + verify every instance in the reference, in parallel: each
    instance gets its own wall-clock limit and its own core."""
    ncores = max(1, os.cpu_count() or 1)
    jobs = max(1, min(jobs, ncores))

    def one(name, core):
        inst_path = os.path.join(instances_dir, name + ".gr")
        sol_path = os.path.join(work_dir, name + ".sol")
        B, K = reference[name]["B"], reference[name]["K"]
        rec = {"B": B, "K": K, "A": None, "raw": None, "score": 0.0,
               "status": "ok", "seconds": 0.0}
        if not os.path.exists(inst_path):
            rec["status"] = "instance file missing on judge side"
            return name, rec
        seconds, err = run_solver(solver, inst_path, sol_path,
                                  per_instance_seconds, core)
        rec["seconds"] = round(seconds, 2)
        if err is None:
            size, verr = verify_solution(inst_path, sol_path)
            if verr is None:
                rec["A"] = size
            else:
                rec["status"] = verr
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


def summarize(results, reference, per_instance_seconds, jobs):
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
        "per_instance_seconds": per_instance_seconds,
        "judge_jobs": jobs,
    }


def load_reference(path):
    with open(path) as f:
        data = json.load(f)
    return data["instances"]


def main(argv):
    if len(argv) != 4:
        print(f"usage: {argv[0]} APP_DIR INSTANCES_DIR REFERENCE_JSON", file=sys.stderr)
        return 2
    app_dir, instances_dir, ref_path = argv[1], argv[2], argv[3]
    reference = load_reference(ref_path)
    work_dir = os.path.join("/tmp", f"ds2025-score-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)

    solver, err = compile_solver(app_dir, work_dir)
    if err:
        return {"reward": 0.0, "compile_error": err, "per_instance": {}}
    results = evaluate(solver, instances_dir, reference, work_dir,
                       PER_INSTANCE_SECONDS, JUDGE_JOBS)
    out = summarize(results, reference,
                    PER_INSTANCE_SECONDS,
                    max(1, min(JUDGE_JOBS, os.cpu_count() or 1)))
    out["per_instance"] = results
    return out


if __name__ == "__main__":
    print(json.dumps(main(sys.argv), indent=1, sort_keys=True))
