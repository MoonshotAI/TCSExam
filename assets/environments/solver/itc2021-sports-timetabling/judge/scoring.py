"""Shared scoring logic for the itc2021-sports-timetabling task (ITC2021
sports timetabling, RobinX XML format).

Used by BOTH sides so the formula and the validity check cannot diverge:
  - agent side:  /app/score_public.py   (public instances, public reference)
  - judge side:  /tests/checker.py      (hidden instances, hidden reference)

Pipeline: run `bash /app/build.sh` (must produce /app/solver) -> for each
instance, run `solver < instance.xml` with the REMAINING time pool in env
ITC2021_TIME_POOL (hard-killed when the pool is exhausted; no per-instance
limit) -> validate the schedule with the official RobinX Validator 2.0
binary (hard violations > 0 means invalid) -> A = recomputed soft penalty
of the (valid) schedule -> per-instance gap ratio r = (B - A) / (B - K), unclipped -> arithmetic mean over participating instances (B > K). Instances
whose B anchor is null (the shipped baseline could not produce a valid
schedule under judging conditions, honestly recorded) carry the explicit
marker anchor_baseline_unsolved and do not participate in the mean; the
model's A on them is still validated and archived.

Instance/solution formats: the official ITC2021 XML formats (RobinX
classification, Van Bulck, Goossens, Schönberger & Guajardo, EJOR 2020;
instances from the International Timetabling Competition 2021). The solver
reads an instance (<Instance> ...) on stdin and writes a schedule
(<Solution> ... <Games><ScheduledMatch home= away= slot=/> ... ) on stdout.

VALIDITY: the official validator recomputes every constraint from scratch
(the declared objective value in the solution metadata is ignored). Any
hard-constraint violation (its first objective column is nonzero) makes the
schedule invalid and scores 0 for that instance. This includes the
built-in constraints the validator always enforces: every game scheduled
(BA1), at most one game per team per slot (BA2), and the phased structure
for gameMode=P instances (each half of the season must be a complete round
robin).

Time budget: ONE TOTAL TIME POOL covers all instances — there is no
per-instance limit. The pool size is
    TOTAL_POOL = PER_INSTANCE_SECONDS * number_of_instances
and the solver reads the remaining pool from env ITC2021_TIME_POOL on every
run. When the pool is used up, every instance without a verified result
scores 0 for that instance. Validity checking does not consume the pool.

The raw unclipped values are reported per instance; raw > 1 means the
submission beat the best-known published value and is investigated, never silently dropped;
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

BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
# Per-instance reference seconds; total pool = this value x instance count.
# The judge enforces the pool globally, NOT per instance.
PER_INSTANCE_SECONDS = float(os.environ.get("PER_INSTANCE_SECONDS", "60"))
VALIDATOR = os.environ.get("ITC_VALIDATOR", "/opt/itc2021/RobinX")


def run_validator(validator, instance_path, solution_path, timeout=300):
    """Run the official RobinX validator; return (hard, soft, error)."""
    try:
        p = subprocess.run(
            [validator, "-i", instance_path, "-s", solution_path],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None, None, "validator timed out"
    except OSError as e:
        return None, None, f"validator failed to start: {e}"
    m = re.search(r"Objective:\s+(\d+)\s+(\d+)", p.stdout)
    if not m:
        tail = ((p.stdout or "") + (p.stderr or ""))[-2000:]
        return None, None, f"validator produced no objective: {tail}"
    return int(m.group(1)), int(m.group(2)), None


def check_schedule(instance_path, out_path):
    """Validate the solver output and recompute its penalty from scratch
    with the official validator. Returns (penalty, None) for a valid
    schedule, else (None, reason)."""
    if not os.path.exists(out_path):
        return None, "no output produced"
    if os.path.getsize(out_path) == 0:
        return None, "empty output"
    hard, soft, err = run_validator(VALIDATOR, instance_path, out_path)
    if err:
        return None, err
    if hard != 0:
        return None, f"{hard} hard-constraint violation(s)"
    return soft, None


# ---------------------------------------------------------------------------
# Judging pipeline (shared by the public self-score and the hidden judge)
# ---------------------------------------------------------------------------

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

    The solver learns the remaining pool via env ITC2021_TIME_POOL and is
    free to use as much of it as it wants on this instance. Returns
    (seconds, None) on success, (seconds, reason) otherwise.
    """
    env = dict(os.environ)
    env["ITC2021_TIME_POOL"] = f"{remaining_pool:.3f}"
    t0 = time.time()
    with open(instance_path) as fin, open(out_path, "w") as fout:
        p = subprocess.Popen(
            [solver], stdin=fin, stdout=fout, env=env,
            stderr=subprocess.DEVNULL, start_new_session=True,
        )
        try:
            p.wait(timeout=remaining_pool)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
            return time.time() - t0, "time pool exhausted during this instance"
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
        out_path = os.path.join(work_dir, name + ".out")
        B, K = reference[name]["B"], reference[name]["K"]
        rec = {"B": B, "K": K, "A": None, "raw": None, "score": 0.0,
               "status": "ok", "seconds": 0.0}
        if B is None:
            # B=null (anchor state where the baseline cannot submit a valid schedule under scoring conditions; decision ③ on 260912)
            # matching this) is marked explicitly: judge_worker accepts it as ok and retains A in
            # the record; a missing anchor without this marker remains a pipeline error (the guard is unchanged).
            rec["anchor_baseline_unsolved"] = True
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
            cost, cerr = check_schedule(inst_path, out_path)
            if cerr is None:
                rec["A"] = cost
            else:
                rec["status"] = f"invalid solution ({cerr})"
        else:
            rec["status"] = err
        if (rec["A"] is not None and B is not None and K is not None
                and B > K):
            rec["raw"] = (B - rec["A"]) / (B - K)
            rec["score"] = min(1.0, max(0.0, rec["raw"]))
        results[name] = rec
    return results, spent


def summarize(results, reference, pool_seconds, spent):
    """Mean of the legacy clipped local `score` over participating (B > K)
    instances — not the judged score (the judged score is the unclipped
    gap-ratio mean computed by the metric engine; see module docstring)."""
    def participates(n):
        B, K = reference[n]["B"], reference[n]["K"]
        return B is not None and K is not None and B > K
    part = [n for n in results if participates(n)]
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
    work_dir = os.path.join("/tmp", f"itc2021-score-{os.getpid()}")
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
