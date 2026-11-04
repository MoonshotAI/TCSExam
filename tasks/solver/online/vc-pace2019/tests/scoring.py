"""Shared scoring logic for the vc-pace2019 (exact vertex cover) task.

Used by BOTH sides so the protocol and the verifier cannot diverge:
  - agent side:  /app/score_public.py   (public instances, public reference)
  - judge side:  /tests/checker.py      (hidden instances, hidden reference)

Protocol (per-instance limit, the official PACE 2019 exact-track form):
  copy /app -> `bash build.sh` (must produce ./solver) -> for each
  instance, invoke
      solver < instance.gr > instance.vc
  with the per-instance wall-clock budget in env VC_TIME_LIMIT (1800 s by
  default, the official PACE 2019 exact-track limit). When the budget is
  exhausted we SIGTERM the process group; after GRACE_TIMEOUT, SIGKILL.
  The judge runs these calls in parallel (JUDGE_JOBS workers, each pinned
  to a core). The printed .vc file (if any) is then validated with the
  official PACE 2019 checker (vc_validate: stdout verdict ends with
  "|SUCCESS" iff the cover is valid; it also enforces that the declared
  size k in the `s vc n k` header equals the number of vertex lines).

An instance counts as SOLVED when the printed cover is valid and its
size equals K, the reference value of the instance (a proven optimum
for 81 judged instances, a pinned best-known upper bound for 19 — see
reference.json / SAMPLING.md). A valid cover SMALLER than K is a genuine
record: it also counts as SOLVED (the instruction has always promised
"doing better than the reference still counts as solved") and is
additionally flagged records_broken — 260924 ruling: the scorer aligns
to the instruction; the flag registers the event for the K-table
re-check, the solved credit stands, and K itself is never ratcheted
from a run (260917 anchor policy). A valid cover larger than K, an
invalid one, or no output all count as not solved.

Reward = (solved - B) / (N - B), where solved = number
of instances solved, N = number of judged instances (those with a proven
optimum in the reference), B = number solved by the untouched baseline
under the same protocol, stored as top-level "B" in the reference JSON.
Scoring formula: the judged score is this gap ratio unclipped
(solved=B -> 0, solved=N -> 1), computed by the metric engine
(tests/metric/engine.py) from the per-instance solved records and anchors
this file reports. This file's local `reward` still clips the ratio to
[0, 1] for the retired local-judging pipeline and is not the judged score.
The raw unclipped value is always recorded as "raw_reward". While B is
null (baseline measurement pending) the reward is null and only the
solved count is reported. Valid covers with size BELOW K are listed in
"records_broken" with the actual size: the solved credit stands; the
list exists so the K table can be re-checked (a below-K cover against a
PROVEN optimum would point at a checker or reference defect; against a
pinned best-known bound it is an expected record, registered but never
ratcheted into K).
"""

import json
import os
import shutil
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

VERIFY_BIN = os.environ.get("VERIFY_BIN", "/usr/local/bin/vc_validate")
BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
# Official PACE 2019 exact-track per-instance wall-clock limit (seconds).
PER_INSTANCE_BUDGET = int(os.environ.get("PER_INSTANCE_BUDGET", "1800"))
GRACE_TIMEOUT = int(os.environ.get("GRACE_TIMEOUT", "10"))  # limit -> TERM -> +grace -> KILL
JUDGE_JOBS = int(os.environ.get("JUDGE_JOBS", "0")) or max(1, (os.cpu_count() or 1))
VERIFY_TIMEOUT = 600


def build_solver(app_dir, work_dir):
    """Copy app_dir into a scratch dir, run `bash build.sh`, expect ./solver."""
    build_dir = os.path.join(work_dir, "build")
    try:
        shutil.copytree(app_dir, build_dir)
    except OSError as e:
        return None, f"failed to copy /app: {e}"
    script = os.path.join(build_dir, "build.sh")
    if not os.path.exists(script):
        return None, "no build.sh found in /app"
    try:
        p = subprocess.run(["bash", "build.sh"], cwd=build_dir,
                           stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=BUILD_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None, f"build.sh timed out after {BUILD_TIMEOUT}s"
    solver = os.path.join(build_dir, "solver")
    if not (os.path.isfile(solver) and os.access(solver, os.X_OK)):
        tail = ((p.stdout or "") + (p.stderr or ""))[-3000:]
        return None, (f"build.sh finished but did not produce an executable "
                      f"solver\n{tail}")
    return solver, None


def run_instance(solver, inst_path, out_path, budget, core=None):
    """Run `solver < inst_path > out_path` with VC_TIME_LIMIT set and a
    hard wall-clock budget (SIGTERM at budget, SIGKILL after grace),
    optionally pinned to a core via taskset.

    Returns (elapsed_seconds, note) where note is None on clean exit.
    """
    env = dict(os.environ)
    env["VC_TIME_LIMIT"] = str(budget)
    cmd = [solver] if core is None else ["taskset", "-c", str(core), solver]
    t0 = time.time()
    with open(inst_path) as fin, open(out_path, "w") as fout:
        p = subprocess.Popen(cmd, stdin=fin, stdout=fout, env=env,
                             stderr=subprocess.DEVNULL,
                             start_new_session=True)
        note = None
        try:
            p.wait(timeout=budget)
        except subprocess.TimeoutExpired:
            note = f"time limit exhausted ({budget}s); SIGTERM sent"
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
    elapsed = round(time.time() - t0, 2)
    if note is None and p.returncode != 0:
        note = f"solver exited with code {p.returncode}"
    return elapsed, note


def verify_vc(inst_path, vc_path):
    """Official checker: stdout verdict ends with '|SUCCESS' iff valid.
    Returns (size, None) with the declared cover size k on success, else
    (None, reason)."""
    if not os.path.exists(vc_path) or os.path.getsize(vc_path) == 0:
        return None, "no output produced (limit exhausted or skipped)"
    try:
        p = subprocess.run(
            [VERIFY_BIN, inst_path, vc_path],
            capture_output=True, text=True, timeout=VERIFY_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return None, "verifier timed out"
    if not (p.stdout or "").rstrip().endswith("|SUCCESS"):
        msg = ((p.stdout or "") + (p.stderr or "")).strip()
        return None, f"invalid vertex cover ({msg[-300:]})"
    # The checker has enforced: header `s vc n k` present exactly once,
    # k == number of vertex lines, all vertices in range, all edges covered.
    try:
        with open(vc_path, errors="replace") as f:
            for line in f:
                tok = line.split()
                if tok and tok[0] == "s":
                    return int(tok[3]), None
        return None, "no solution line (s vc ...) found in output"
    except (OSError, ValueError, IndexError) as e:
        return None, f"unparseable output ({e})"


def evaluate(solver, instances_dir, work_dir, reference, budget, jobs):
    """Run + validate every instance in parallel: each instance gets its
    own budget and its own core."""
    ncores = max(1, os.cpu_count() or 1)
    jobs = max(1, min(jobs, ncores))

    def one(name, core):
        inst_path = os.path.join(instances_dir, name + ".gr")
        K = reference[name]["K"]
        rec = {"K": K, "A": None, "solved": False, "status": "ok"}
        if not os.path.exists(inst_path):
            rec["status"] = "instance file missing on judge side"
            return name, rec
        out_path = os.path.join(work_dir, name + ".vc")
        elapsed, note = run_instance(solver, inst_path, out_path,
                                     budget, core)
        rec["seconds"] = elapsed
        if note:
            rec["status"] = note
        size, verr = verify_vc(inst_path, out_path)
        if verr is not None:
            if rec["status"] == "ok":
                rec["status"] = verr
            return name, rec
        rec["A"] = size
        if size == K:
            rec["solved"] = True
        elif size < K:
            # A valid cover SMALLER than the reference K — a genuine
            # record. 260924 ruling: counts as SOLVED (the instruction
            # promises it) and is flagged records_broken for the K-table
            # re-check; registered, never ratcheted into K, never zeroed.
            # Cover sizes are integers, so any A < K differs from K by at
            # least 1 — far outside the 1e-6 relative float-noise band
            # (A == K stays the plain solved case, never flagged). The
            # status keeps the "ok" prefix (the worker normalizes it to
            # status ok / A=1, same as any solved key) and carries the
            # flag plus the actual size into the public feedback and the
            # hidden archive.
            rec["solved"] = True
            rec["records_broken"] = True
            rec["status"] = (
                f"ok (solved: valid cover of size {size} BELOW the "
                f"reference K — records_broken; the K table will be "
                f"re-checked, the solved credit stands)")
        else:
            rec["status"] = "valid but above optimum"
        return name, rec

    results = {}
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        futures = [ex.submit(one, name, i % jobs)
                   for i, name in enumerate(sorted(reference))]
        for fut in futures:
            name, rec = fut.result()
            results[name] = rec
    return results


def summarize(results, reference, baseline_solved):
    """reward = (solved - B) / (N - B) with the legacy local clip [0, 1]
    (not the judged score — the judged score is the unclipped ratio via
    the metric engine; see module docstring); raw kept alongside."""
    solved = sum(1 for n in results if results[n]["solved"])
    total = len(results)
    records = sorted(
        ({"instance": n, "A": results[n]["A"], "K": reference[n]["K"]}
         for n in results
         if results[n]["A"] is not None and results[n]["A"] < reference[n]["K"]),
        key=lambda r: r["instance"],
    )
    out = {
        "solved": solved,
        "total": total,
        "B": baseline_solved,
        # Valid covers below K: solved credit stands (260924 ruling); the
        # list registers the records for the K-table re-check.
        "records_broken": records,
        "n_records_broken": len(records),
    }
    if baseline_solved is None:
        out["reward"] = None
        out["raw_reward"] = None
        out["note"] = ("baseline solved count B not filled in the reference "
                       "yet; reward pending baseline measurement")
    elif baseline_solved >= total:
        out["reward"] = None
        out["raw_reward"] = None
        out["note"] = (f"degenerate anchors: baseline solved B={baseline_solved} "
                       f">= total={total}; formula undefined")
    else:
        raw = (solved - baseline_solved) / (total - baseline_solved)
        out["raw_reward"] = raw
        out["reward"] = min(1.0, max(0.0, raw))
    return out


def load_reference(path):
    with open(path) as f:
        return json.load(f)


def main(argv):
    if len(argv) != 4:
        print(f"usage: {argv[0]} APP_DIR INSTANCES_DIR REFERENCE_JSON", file=sys.stderr)
        return 2
    app_dir, instances_dir, ref_path = argv[1], argv[2], argv[3]
    doc = load_reference(ref_path)
    # Every instance in the reference is judgable and judged: the public
    # side's former K-null keys now carry pinned best-known upper bounds
    # (same harvest-127283 peaty incumbent provenance as the hidden side).
    reference = doc["instances"]
    baseline_solved = doc.get("B")
    work_dir = os.path.join("/tmp", f"vc-score-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)

    solver, err = build_solver(app_dir, work_dir)
    if err:
        return {"reward": 0.0, "build_error": err, "per_instance": {}}
    results = evaluate(solver, instances_dir, work_dir, reference,
                       PER_INSTANCE_BUDGET, JUDGE_JOBS)
    out = summarize(results, reference, baseline_solved)
    out["per_instance_budget"] = PER_INSTANCE_BUDGET
    out["judge_jobs"] = max(1, min(JUDGE_JOBS, os.cpu_count() or 1))
    out["per_instance"] = results
    return out


if __name__ == "__main__":
    print(json.dumps(main(sys.argv), indent=1, sort_keys=True))
