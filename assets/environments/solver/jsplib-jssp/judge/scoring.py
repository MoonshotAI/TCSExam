"""Shared scoring logic for the jsplib-jssp task.

Judge-side scoring module (form 2, 2026-09-20): lives in tests/ only — the
judging chain (/tests/checker.py, both channels) imports it; the agent
environment no longer carries any scoring code (the agent-side convenience
runner /app/run_public.py is a self-contained per-instance runner with no
aggregation).

Protocol (per-instance limit): run `bash /app/build.sh` (must produce an
executable /app/solver), then for each instance invoke
    solver INSTANCE_FILE OUTPUT_FILE LIMIT_SECONDS
with LIMIT_SECONDS the per-instance budget (600 s). The solver must keep a
valid best-so-far schedule in OUTPUT_FILE at all times (the shipped
baseline rewrites it atomically on every improvement). When the limit plus
GRACE_TIMEOUT expires we SIGTERM the process group, then SIGKILL after
another grace period; whatever schedule sits in OUTPUT_FILE is then
validated with jssp_check ("OK <makespan>" on stdout). A = the validated
makespan. Instances are evaluated in parallel (JUDGE_JOBS workers, each
pinned to a core with taskset); the solver only ever sees one instance at
a time.

Per-instance gap ratio (formula finalized 2026-09-20): the judged score is
the pure gap ratio r with the UNTRUNCATED ratio
    r = (B - A) / (B - K)      (B = packaged baseline, K = best known)
averaged (arithmetic mean) over the participating instances — no clip, no
transform: A == B -> 0, A == K -> 1.0, beating K -> r > 1, worse than B
-> r < 0. The mean is computed by the unified metric engine
(tests/metric/engine.py) from the per-instance ``raw`` records this file
emits. The third anchor L (the textbook-technique level — the stock
CP-SAT model shipped as /app/cpsat_example.py run under the same budget)
does not define any score: it survives only in the legacy v0 fields below
as a documented reference point. Retired calibers (both 2026-09-20): v0
(clip [0, 1]) and SOL (S = 1/(2 - r), 2026-09-02 migration spec
schema-v4/specs/sol-scoring.md, now a tombstone).

Per-instance record fields:
  - ``raw``    = the untruncated gap ratio r above — the field the metric
                 engine consumes (same field name and semantics as the
                 other gap-ratio problems).
  - ``score``  = the LEGACY v0 three-anchor piecewise score, kept for
                 historical comparison only. With K < L < B it is
                 piecewise linear:
                     A in [B, L]:  0.3 * (B - A) / (B - L)
                     A in [L, K]:  0.3 + 0.7 * (L - A) / (L - K)
                 clipped to [0, 1]. Degenerate anchors fall back
                 gracefully:
                   - no L field, or L >= B: (B - A) / (B - K);
                   - L <= K (saturated): 0.3 + 0.7 * (L - A) / (B - L).
``reward`` in this file's JSON stays the v0 mean of ``score`` for
historical comparison only — the platform reward comes from the metric
engine via fetch_final. The top-level ``sol_score`` is the retired SOL
mean (map-then-mean with S = 1/(2 - r)), also kept for comparison only.

Instances with B == K carry no signal and are excluded from the mean.
raw > 1 means the submission beat the best-known value and is surfaced in
records_broken (raw > 1 <=> A < K when B > K).

Review flag (2026-08-11): every instance whose validated makespan A
reaches or undercuts K (A <= K) is additionally listed in
at_or_below_known_best. records_broken alone misses the boundary case:
on the six classic judged instances the archive upper bounds are public
and schedules attaining them circulate on the public web, so a
memorized replay lands exactly at raw 1.0 (or, on a saturated L <= K
instance, at an unremarkable-looking 0.3) without ever exceeding it.
The list is a marker for human review; it does not change the reward.

Instance files come in two shapes:
  - plain:     <name>.txt            (agent side, /app/instances; judge
                                      side, $TESTS_DIR/instances — the only
                                      shape in use since the 2026-09-12
                                      no-hidden-set rework)
  - encrypted: <name>.txt.xz.enc     (retired hidden-set era, judge side
                                      /opt/jssp-private; archived in
                                      tests/archive-codename-260911/)
The encrypted shape is decrypted just-in-time with the key file
JSSP_INSTANCE_KEY (judge side only; the agent image carries no key).
"""

import json
import os
import shutil
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

VERIFY_BIN = os.environ.get("VERIFY_BIN", "/usr/local/bin/jssp_check")
BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
PER_INSTANCE_BUDGET = int(os.environ.get("PER_INSTANCE_BUDGET", "600"))
GRACE_TIMEOUT = int(os.environ.get("GRACE_TIMEOUT", "10"))
JUDGE_JOBS = int(os.environ.get("JUDGE_JOBS", "0")) or max(1, (os.cpu_count() or 1))
VERIFY_TIMEOUT = int(os.environ.get("VERIFY_TIMEOUT", "120"))
INSTANCE_KEY = os.environ.get("JSSP_INSTANCE_KEY", "/tests/instance.key")


def build_solver(app_dir, work_dir):
    """Copy app_dir into a scratch dir, run build.sh, expect ./solver."""
    build_dir = os.path.join(work_dir, "build")
    try:
        shutil.copytree(app_dir, build_dir,
                        ignore=shutil.ignore_patterns("instances", "output",
                                                      "__pycache__"))
    except OSError as e:
        return None, f"failed to copy /app: {e}"
    script = os.path.join(build_dir, "build.sh")
    if not os.path.exists(script):
        return None, "no /app/build.sh found"
    try:
        p = subprocess.run(["bash", script], cwd=build_dir,
                           stdin=subprocess.DEVNULL,
                           capture_output=True, text=True,
                           timeout=BUILD_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None, f"build.sh timed out after {BUILD_TIMEOUT}s"
    solver = os.path.join(build_dir, "solver")
    if not (os.path.isfile(solver) and os.access(solver, os.X_OK)):
        tail = ((p.stdout or "") + (p.stderr or ""))[-3000:]
        return None, (f"build.sh finished (exit {p.returncode}) but did not "
                      f"produce an executable solver\n{tail}")
    return solver, None


def materialize_instance(instances_dir, name, work_dir):
    """Path of a plain .txt for `name`, decrypting just-in-time if the
    stored file is the encrypted shape. Returns (path, cleanup_flag, None)
    or (None, False, reason)."""
    plain = os.path.join(instances_dir, name + ".txt")
    if os.path.exists(plain):
        return plain, False, None
    enc = os.path.join(instances_dir, name + ".txt.xz.enc")
    if not os.path.exists(enc):
        return None, False, "instance file missing on judge side"
    if not os.path.exists(INSTANCE_KEY):
        return None, False, "instance key missing on judge side"
    out = os.path.join(work_dir, name + ".txt")
    cmd = (f"openssl enc -d -aes-256-ctr -pbkdf2 -pass file:{INSTANCE_KEY}"
           f" -in {enc} | xz -dc > {out}")
    try:
        p = subprocess.run(["bash", "-c", cmd], capture_output=True,
                           text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return None, False, "instance decrypt timed out"
    if p.returncode != 0 or not os.path.exists(out) or os.path.getsize(out) == 0:
        return None, False, f"instance decrypt failed: {(p.stderr or '')[-200:]}"
    return out, True, None


def run_solver(solver, inst_path, out_path, budget, core=None):
    """Invoke solver INSTANCE OUTPUT LIMIT; enforce budget + grace with
    SIGTERM then SIGKILL. Returns (elapsed_seconds, note); note None on
    clean exit."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    t0 = time.time()
    cmd = [solver, inst_path, out_path, str(budget)]
    if core is not None:
        cmd = ["taskset", "-c", str(core)] + cmd
    p = subprocess.Popen(cmd, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    note = None
    try:
        p.wait(timeout=budget + GRACE_TIMEOUT)
    except subprocess.TimeoutExpired:
        note = f"exceeded limit+grace ({budget}+{GRACE_TIMEOUT}s); SIGTERM sent"
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


def verify_solution(inst_path, out_path):
    """jssp_check: (makespan, None) or (None, status)."""
    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        return None, "no output produced (limit exhausted or solver wrote nothing)"
    try:
        p = subprocess.run([VERIFY_BIN, inst_path, out_path],
                           capture_output=True, text=True,
                           timeout=VERIFY_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None, "verifier timed out"
    out = (p.stdout or "").strip()
    if p.returncode == 0 and out.startswith("OK "):
        try:
            return int(out.split()[1]), None
        except (ValueError, IndexError):
            return None, f"unparseable verifier output ({out[:100]})"
    msg = out or (p.stderr or "").strip() or f"verifier exit {p.returncode}"
    return None, f"invalid schedule ({msg[-300:]})"


def piecewise_raw(A, B, K, L):
    """Three-anchor piecewise raw score; see the module docstring."""
    if L is None or L >= B:
        return (B - A) / (B - K)
    if A >= L:
        return 0.3 * (B - A) / (B - L)
    if L > K:
        return 0.3 + 0.7 * (L - A) / (L - K)
    return 0.3 + 0.7 * (L - A) / (B - L)  # L <= K: saturated instance


def evaluate(solver, instances_dir, work_dir, reference, per_instance_budget,
             jobs):
    """Run + validate every instance in the reference, in parallel: each
    instance gets its own budget and its own core."""
    ncores = max(1, os.cpu_count() or 1)
    jobs = max(1, min(jobs, ncores))

    def one(name, core):
        B, K = reference[name]["B"], reference[name]["K"]
        L = reference[name].get("L")
        rec = {"B": B, "K": K, "L": L, "A": None, "raw": None,
               "score": 0.0, "status": "ok"}
        inst_path, cleanup, err = materialize_instance(instances_dir, name,
                                                       work_dir)
        if err is not None:
            rec["status"] = err
            return name, rec
        out_path = os.path.join(work_dir, f"out-{name}", name + ".sol")
        secs, note = run_solver(solver, inst_path, out_path,
                                per_instance_budget, core)
        rec["seconds"] = secs
        if note:
            rec["status"] = note
        value, verr = verify_solution(inst_path, out_path)
        if verr is None:
            rec["A"] = value
        elif rec["status"] == "ok":
            rec["status"] = verr
        if cleanup:
            os.remove(inst_path)
        if rec["A"] is not None and B > K:
            # Gap-ratio raw (judged via the metric engine); v0 piecewise
            # kept in "score" only.
            rec["raw"] = (B - rec["A"]) / (B - K)
            rec["score"] = min(1.0, max(0.0, piecewise_raw(rec["A"], B, K, L)))
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
    """Legacy v0 mean of clipped scores + retired SOL mean over
    participating (B > K) instances. Neither is the judged score: the
    judged score is the metric engine's unclipped mean of ``raw``."""
    part = [n for n in results if reference[n]["B"] > reference[n]["K"]]
    total = sum(results[n]["score"] for n in part) / len(part) if part else 0.0
    raws = [results[n]["raw"] for n in part if results[n]["raw"] is not None]
    # Retired SOL aggregate (kept for historical comparison only): map each
    # untruncated per-instance raw FIRST, then average (failed instances
    # carry raw None and contribute 0).
    sol = (sum(1.0 / max(2.0 - results[n]["raw"], 1e-9)
               if results[n]["raw"] is not None else 0.0
               for n in part) / len(part)) if part else 0.0
    records = sorted(
        ({"instance": n, "A": results[n]["A"], "K": reference[n]["K"],
          "raw": round(results[n]["raw"], 4)}
         for n in part
         if results[n]["raw"] is not None and results[n]["raw"] > 1.0),
        key=lambda r: r["instance"],
    )
    # Review flag: A <= K on a participating instance (see module
    # docstring). Independent of the raw value so the boundary cases
    # (raw exactly 1.0, or an unremarkable raw on a saturated L <= K
    # instance) are caught as well. Marker only; no reward effect.
    at_or_below = sorted(
        ({"instance": n, "A": results[n]["A"], "K": reference[n]["K"],
          "raw": (round(results[n]["raw"], 4)
                  if results[n]["raw"] is not None else None)}
         for n in part
         if results[n]["A"] is not None
         and results[n]["A"] <= reference[n]["K"]),
        key=lambda r: r["instance"],
    )
    return {
        "reward": total,
        "sol_score": sol,
        "participating": len(part),
        "excluded_B_equals_K": sorted(n for n in results if n not in part),
        "mean_raw_unclipped": (sum(raws) / len(raws)) if raws else None,
        "records_broken": records,
        "n_records_broken": len(records),
        "at_or_below_known_best": at_or_below,
        "n_at_or_below_known_best": len(at_or_below),
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
    work_dir = os.path.join("/tmp", f"jssp-score-{os.getpid()}")
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
