"""Shared scoring logic for the tw-heuristic (treewidth) task.

Used by BOTH sides so the formula and the verifier cannot diverge:
  - agent side:  /app/score_public.py   (public instances, public reference)
  - judge side:  /tests/checker.py      (hidden instances, hidden reference)

Protocol (per-instance limit, the official PACE 2017 heuristic-track form):
  copy /app -> `make` (must produce ./solver) -> for each instance, invoke
      solver SINGLE_INSTANCE_DIR OUTPUT_DIR LIMIT_SECONDS
  where SINGLE_INSTANCE_DIR holds just that one instance and LIMIT_SECONDS
  is the official per-instance budget (1800 s by default). The solver
  contract (INSTANCES_DIR OUTPUT_DIR POOL_SECONDS) is unchanged — it simply
  sees one instance at a time; the judge runs these calls in parallel
  (JUDGE_JOBS workers, each pinned to a core). After the limit plus
  GRACE_TIMEOUT expires we SIGTERM the process group, then SIGKILL after
  another grace period; the .td file (if any) is validated with the
  official td-validate checker (width = max bag size - 1, from the s-line).
  Instances with no valid .td score 0.

Per-instance gap ratio r = (B - A) / (B - K), unclipped; B = baseline width
(FlowCutter via the baseline driver with equal time slices), K = best-known
reference width. Instances with B == K carry no signal and are excluded from
the mean. Raw unclipped values are always recorded; any raw > 1 (beat the
reference) is additionally surfaced in the top-level "records_broken" list.

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
import shutil
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

VERIFY_BIN = os.environ.get("VERIFY_BIN", "/usr/local/bin/td-validate")
BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "300"))
PER_INSTANCE_BUDGET = int(os.environ.get("PER_INSTANCE_BUDGET", "1800"))
GRACE_TIMEOUT = int(os.environ.get("GRACE_TIMEOUT", "10"))  # limit+grace -> TERM
JUDGE_JOBS = int(os.environ.get("JUDGE_JOBS", "0")) or max(1, (os.cpu_count() or 1))
VERIFY_TIMEOUT = 120


def build_solver(app_dir, work_dir):
    """Copy app_dir into a scratch dir, run `make`, expect ./solver."""
    build_dir = os.path.join(work_dir, "build")
    try:
        shutil.copytree(app_dir, build_dir)
    except OSError as e:
        return None, f"failed to copy /app: {e}"
    try:
        p = subprocess.run(["make", "-j4"], cwd=build_dir,
                           capture_output=True, text=True, timeout=BUILD_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None, f"build timed out after {BUILD_TIMEOUT}s"
    if p.returncode != 0:
        return None, "`make` failed:\n" + (p.stderr or "")[-4000:]
    solver = os.path.join(build_dir, "solver")
    if not (os.path.isfile(solver) and os.access(solver, os.X_OK)):
        return None, "`make` succeeded but did not produce an executable ./solver"
    return solver, None


def run_pool(solver, instances_dir, out_dir, pool, core=None):
    """Invoke the solver once with the given pool; enforce pool + grace,
    optionally pinned to a core via taskset.

    Returns (elapsed_seconds, note) where note is None on clean exit.
    """
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    cmd = [solver, instances_dir, out_dir, str(pool)]
    if core is not None:
        cmd = ["taskset", "-c", str(core)] + cmd
    p = subprocess.Popen(cmd,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    note = None
    try:
        p.wait(timeout=pool + GRACE_TIMEOUT)
    except subprocess.TimeoutExpired:
        note = f"exceeded pool+grace ({pool}+{GRACE_TIMEOUT}s); SIGTERM sent"
        try:
            os.killpg(p.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            p.wait(timeout=GRACE_TIMEOUT)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
            note += "; SIGKILL needed"
    return round(time.time() - t0, 2), note


def verify_td(instance_path, td_path):
    """Official td-validate: exit 0 + 'valid' on stderr. Width from the s-line."""
    try:
        p = subprocess.run(
            [VERIFY_BIN, instance_path, td_path],
            capture_output=True, text=True, timeout=VERIFY_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return None, "verifier timed out"
    # td-validate prints its verdict to stderr: exactly "valid" (exit 0) on
    # success, "invalid..." or "Error: ..." (exit 1) on failure.
    out = ((p.stdout or "") + (p.stderr or "")).strip()
    if p.returncode != 0 or out != "valid":
        msg = out or f"verifier exit {p.returncode}"
        return None, f"invalid decomposition ({msg[-300:]})"
    # td-validate has confirmed the declared max bag size equals the real one.
    # s-line: `s td <bags> <maxbag> <n>` -> width = maxbag - 1 (token 3!).
    try:
        with open(td_path) as f:
            for line in f:
                if line.startswith("c") or not line.strip():
                    continue
                tok = line.split()
                if tok[0] == "s":
                    return int(tok[3]) - 1, None
        return None, "no solution line (s td ...) found in output"
    except (OSError, ValueError, IndexError) as e:
        return None, f"unparseable output ({e})"


def evaluate(solver, instances_dir, work_dir, reference, per_instance_budget,
             jobs):
    """Run + validate every instance in parallel: each instance gets a
    single-instance directory, its own budget, and its own core."""
    ncores = max(1, os.cpu_count() or 1)
    jobs = max(1, min(jobs, ncores))

    def one(name, core):
        inst_path = os.path.join(instances_dir, name + ".gr")
        B, K = reference[name]["B"], reference[name]["K"]
        rec = {"B": B, "K": K, "A": None, "raw": None, "score": 0.0, "status": "ok"}
        if not os.path.exists(inst_path):
            rec["status"] = "instance file missing on judge side"
            return name, rec
        single_dir = os.path.join(work_dir, f"in-{name}")
        out_dir = os.path.join(work_dir, f"out-{name}")
        os.makedirs(single_dir, exist_ok=True)
        link = os.path.join(single_dir, name + ".gr")
        if not os.path.exists(link):
            os.symlink(inst_path, link)
        elapsed, note = run_pool(solver, single_dir, out_dir,
                                 per_instance_budget, core)
        rec["seconds"] = elapsed
        if note:
            rec["status"] = note
        td_path = os.path.join(out_dir, name + ".td")
        if not os.path.exists(td_path) or os.path.getsize(td_path) == 0:
            if rec["status"] == "ok":
                rec["status"] = "no output produced (limit exhausted or skipped)"
            return name, rec
        width, verr = verify_td(inst_path, td_path)
        if verr is None:
            rec["A"] = width
        else:
            rec["status"] = verr
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
    part = [n for n in results if reference[n]["B"] > reference[n]["K"]]
    total = sum(results[n]["score"] for n in part) / len(part) if part else 0.0
    raws = [results[n]["raw"] for n in part if results[n]["raw"] is not None]
    records = sorted(
        ({"instance": n, "A": results[n]["A"], "K": reference[n]["K"],
          "raw": round(results[n]["raw"], 4)}
         for n in part
         if results[n]["raw"] is not None and results[n]["raw"] > 1.0),
        key=lambda r: r["instance"],
    )
    return {
        "reward": total,
        "participating": len(part),
        "excluded_B_equals_K": sorted(n for n in results if n not in part),
        "mean_raw_unclipped": (sum(raws) / len(raws)) if raws else None,
        "records_broken": records,
        "n_records_broken": len(records),
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
    work_dir = os.path.join("/tmp", f"tw-score-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)

    solver, err = build_solver(app_dir, work_dir)
    if err:
        return {"reward": 0.0, "build_error": err, "per_instance": {}}
    results = evaluate(solver, instances_dir, work_dir, reference,
                       PER_INSTANCE_BUDGET, JUDGE_JOBS)
    out = summarize(results, reference)
    out["per_instance_budget"] = PER_INSTANCE_BUDGET
    out["judge_jobs"] = max(1, min(JUDGE_JOBS, os.cpu_count() or 1))
    out["per_instance"] = results
    return out


if __name__ == "__main__":
    print(json.dumps(main(sys.argv), indent=1, sort_keys=True))
