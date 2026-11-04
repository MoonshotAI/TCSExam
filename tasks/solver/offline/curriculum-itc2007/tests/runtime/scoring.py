"""Shared scoring logic for the curriculum-itc2007 task.

Used by BOTH sides so the formula and the validity check cannot diverge:
  - agent side:  /app/score_public.py   (public instances, public reference)
  - judge side:  /tests/checker.py      (hidden instances, hidden reference)

Pipeline: run `bash /app/build.sh` (must produce /app/solver) -> for each
instance, run `solver < instance` under a PER-INSTANCE wall-clock limit
(hard-killed at the limit; the solver learns this run's limit from env
CTT_TIME_LIMIT) -> validate the printed timetable with the OFFICIAL ITC 2007
Track 3 validator (the same binary on both sides, see check_ctt below) ->
A = the timetable's soft-constraint cost as recomputed by the validator ->
per-instance gap ratio r = (B - A) / (B - K), unclipped -> arithmetic mean.
Instances with B == K carry no signal and are excluded.

Validity: the official validator (validator.cc by Schaerf & Di Gaspero,
the track organizers) recomputes every hard constraint from scratch:
Lectures (all lectures scheduled, no extras), Conflicts (teacher /
curriculum overlaps), Availability, RoomOccupation. A timetable is valid
iff all four hard-violation counts are zero; the cost A is the validator's
own "Total Cost" (RoomCapacity + 5 x MinWorkingDays days short +
2 x CurriculumCompactness isolated lectures + RoomStability extra rooms).
Nothing the solver prints beyond the timetable lines is trusted. Malformed
lines are skipped by the validator and show up as missing lectures, i.e.
hard violations, so garbage output is always caught.

Time budget (aligned with the official ITC 2007
Track 3 format): a PER-INSTANCE wall-clock limit —
PER_INSTANCE_SECONDS (240 s by default) per instance, enforced with an
OS-level hard kill on the solver's whole process group. There is no shared
pool: an instance that exceeds its limit is killed, that instance scores 0,
and the remaining instances are unaffected. The solver learns the limit via
env CTT_TIME_LIMIT on every run. Validity checking does not consume the
budget.

The raw unclipped values are reported per instance; raw > 1 means the
submission beat the best-known cost K (possible for the four instances
whose optimum is not proven — it is recorded for investigation, never silently dropped;
under the finalized formula it counts unclipped (r > 1)).

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
import re
import signal
import subprocess
import sys
import time

BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
VALIDATOR = os.environ.get("CTT_VALIDATOR", "/opt/ctt/validator")
CHECK_TIMEOUT = 120
# Per-instance wall-clock limit (official-format per-instance budget).
PER_INSTANCE_SECONDS = float(os.environ.get("PER_INSTANCE_SECONDS", "240"))

HARD_RE = re.compile(r"Violations of (Lectures|Conflicts|Availability|"
                     r"RoomOccupation) \(hard\) : (\d+)")
COST_RE = re.compile(r"Total Cost = (\d+)")


def check_ctt(instance_path, out_path):
    """Return (cost, None) iff the output is a feasible timetable; the cost
    is recomputed by the official validator. Otherwise (None, reason)."""
    if not os.path.exists(VALIDATOR):
        return None, f"validator binary missing at {VALIDATOR}"
    try:
        p = subprocess.run(
            [VALIDATOR, instance_path, out_path],
            capture_output=True, text=True, timeout=CHECK_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return None, f"validator timed out after {CHECK_TIMEOUT}s"
    except OSError as e:
        return None, f"could not run validator: {e}"
    out = p.stdout or ""
    if p.returncode != 0:
        tail = (out + (p.stderr or ""))[-500:]
        return None, f"validator exited with code {p.returncode}: {tail}"
    hard = {m.group(1): int(m.group(2)) for m in HARD_RE.finditer(out)}
    if len(hard) != 4:
        return None, "validator output missing hard-constraint summary"
    bad = {k: v for k, v in hard.items() if v != 0}
    if bad:
        return None, "hard constraint violations: " + ", ".join(
            f"{k}={v}" for k, v in sorted(bad.items()))
    m = COST_RE.search(out)
    if not m:
        return None, "validator output missing total cost"
    return int(m.group(1)), None


def build_solver(app_dir, timeout=BUILD_TIMEOUT):
    """Run the agent-visible build script; require /app/solver afterwards."""
    script = os.path.join(app_dir, "build.sh")
    if not os.path.exists(script):
        return None, "no /app/build.sh found"
    try:
        p = subprocess.run(
            ["bash", script], cwd=app_dir, stdin=subprocess.DEVNULL, user=65534, group=65534, extra_groups=[],
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


def run_solver(solver, instance_path, out_path, limit_seconds):
    """Run solver < instance > out_path with a hard timeout of
    limit_seconds (the per-instance limit). The solver learns this run's
    limit via env CTT_TIME_LIMIT. Returns (seconds, None) on success,
    (seconds, reason) otherwise.
    """
    env = dict(os.environ)
    env["CTT_TIME_LIMIT"] = f"{limit_seconds:.3f}"
    t0 = time.time()
    with open(instance_path) as fin, open(out_path, "w") as fout:
        p = subprocess.Popen(
            [solver], stdin=fin, stdout=fout, env=env,
            stderr=subprocess.DEVNULL, start_new_session=True, user=65534, group=65534, extra_groups=[],
        )
        try:
            p.wait(timeout=limit_seconds)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
            return time.time() - t0, f"timeout after {limit_seconds:g}s"
    seconds = time.time() - t0
    if p.returncode != 0:
        return seconds, f"solver exited with code {p.returncode}"
    return seconds, None


def evaluate(solver, instances_dir, reference, work_dir):
    """Run + check every instance in the reference, each under its own
    PER_INSTANCE_SECONDS wall-clock limit."""
    results = {}
    spent = 0.0
    for name in sorted(reference):
        inst_path = os.path.join(instances_dir, name)
        out_path = os.path.join(work_dir, name + ".out")
        B, K = reference[name]["B"], reference[name]["K"]
        rec = {"B": B, "K": K, "A": None, "raw": None, "score": 0.0,
               "status": "ok", "seconds": 0.0}
        if not os.path.exists(inst_path):
            rec["status"] = "instance file missing on judge side"
            results[name] = rec
            continue
        seconds, err = run_solver(solver, inst_path, out_path,
                                  PER_INSTANCE_SECONDS)
        spent += seconds
        rec["seconds"] = round(seconds, 2)
        if err is None:
            cost, cerr = check_ctt(inst_path, out_path)
            if cerr is None:
                rec["A"] = cost
            else:
                rec["status"] = f"invalid solution ({cerr})"
        else:
            rec["status"] = err
        if rec["A"] is not None and B > K:
            rec["raw"] = (B - rec["A"]) / (B - K)
            rec["score"] = min(1.0, max(0.0, rec["raw"]))
        results[name] = rec
    return results, spent


def summarize(results, reference, spent):
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
        "per_instance_seconds": PER_INSTANCE_SECONDS,
        "solver_seconds_spent": round(spent, 2),
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
    work_dir = os.path.join("/tmp", f"ctt-score-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)
    os.chown(work_dir, 65534, 65534)

    solver, err = build_solver(app_dir)
    if err:
        return {"reward": 0.0, "build_error": err, "per_instance": {}}
    results, spent = evaluate(solver, instances_dir, reference, work_dir)
    out = summarize(results, reference, spent)
    out["per_instance"] = results
    return out


if __name__ == "__main__":
    print(json.dumps(main(sys.argv), indent=1, sort_keys=True))
