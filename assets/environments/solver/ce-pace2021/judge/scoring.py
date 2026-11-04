"""Shared scoring logic for the ce-pace2021 task.

Used by BOTH sides so the formula and the verifier cannot diverge:
  - agent side:  /app/score_public.py   (public instances, public reference)
  - judge side:  /tests/checker.py      (hidden instances, hidden reference)

Pipeline: run `bash /app/build.sh` (must produce /app/solver) -> run the
solver once per instance -> validate the printed edit set with the official
PACE 2021 verifier (ce_verify) -> A = size of the (valid) edit set ->
per-instance score -> arithmetic mean.
Instances with B == K carry no signal and are excluded.

Per-instance scoring (SOL, 2026-09-02 migration): the judged score is the
SOL formula of schema-v4/specs/sol-scoring.md, S = 1/(2 - r) per instance
with the UNTRUNCATED ratio
    r = (B - A) / (B - K)      (B = packaged baseline, K = best known)
mapped per instance FIRST, then averaged (arithmetic mean) over the
participating instances. Anchor properties: A == B -> 0.5, A == K -> 1.0,
worse than B decays smoothly toward 0, beating K grows past 1.0 unclipped.
The third anchor L (textbook vertex-move local-search level) no longer
defines any score: it survives only in the legacy v0 fields below as a
documented reference point.

Per-instance record fields:
  - ``raw``    = the untruncated SOL ratio r above. This is the field the
                 judge-side SOL re-scoring (judge_worker._sol_rescore)
                 remaps per instance; same field name and semantics as the
                 other 58 SOL problems.
  - ``score``  = the LEGACY v0 three-anchor piecewise score, kept for
                 historical comparison only (judge_worker reports it as
                 score_v0). With K < L < B it is piecewise linear:
                     A in [B, L]:  0.3 * (B - A) / (B - L)
                     A in [L, K]:  0.3 + 0.7 * (L - A) / (L - K)
                 clipped to [0, 1]. Degenerate anchors fall back
                 gracefully:
                   - no L field, or L >= B: (B - A) / (B - K);
                   - L <= K (saturated): 0.3 + 0.7 * (L - A) / (B - L).
``reward`` stays the v0 mean of ``score`` so a v0-vs-SOL comparison
remains possible; the top-level ``sol_score`` is the SOL mean computed
here with the same map-then-mean order (judge_worker recomputes it from
the per-instance raw values — the two must agree).

Time budget: each instance gets its own wall-clock limit
(PER_INSTANCE_SECONDS, 600 s by default — the official PACE 2021
heuristic-track per-instance limit). Instances are evaluated in parallel
(JUDGE_JOBS workers, each pinned to a core with taskset); the solver only
ever sees one instance at a time. Verification time does not consume the
limit.

The raw unclipped values are reported per instance; raw > 1 means the
submission beat the best known solution (champion result) and is
investigated, not silently clipped away.
"""

import json
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

VERIFY_BIN = os.environ.get("VERIFY_BIN", "/usr/local/bin/ce_verify")
BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
PER_INSTANCE_SECONDS = int(os.environ.get("PER_INSTANCE_SECONDS", "600"))
VERIFY_TIMEOUT = int(os.environ.get("VERIFY_TIMEOUT", "300"))
JUDGE_JOBS = int(os.environ.get("JUDGE_JOBS", "0")) or max(1, (os.cpu_count() or 1))


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


def verify_edits(instance_path, out_path):
    """Official PACE 2021 verifier: prints 'OK' iff applying the edit set
    yields a cluster graph (disjoint union of cliques). NOTE: the official
    verifier exits 0 even when it reports a P3 witness, so validity is
    decided by its stdout, not the exit code. Returns (size, None) with
    size = number of non-empty lines of the edit set, else (None, reason)."""
    try:
        p = subprocess.run(
            [VERIFY_BIN, instance_path, out_path],
            capture_output=True, text=True, timeout=VERIFY_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return None, "verifier timed out"
    if p.returncode != 0:
        msg = (p.stderr or "").strip() or (p.stdout or "").strip()
        return None, f"verifier failed ({msg[-300:]})"
    if not (p.stdout or "").lstrip().startswith("OK"):
        msg = (p.stdout or "").strip()
        return None, f"not a cluster editing ({msg[-300:]})"
    try:
        with open(out_path, errors="replace") as f:
            size = sum(1 for line in f if line.strip())
    except OSError as e:
        return None, f"could not read solver output: {e}"
    return size, None


def piecewise_raw(A, B, K, L):
    """Three-anchor piecewise raw score; see the module docstring."""
    if L is None or L >= B:
        return (B - A) / (B - K)
    if A >= L:
        return 0.3 * (B - A) / (B - L)
    if L > K:
        return 0.3 + 0.7 * (L - A) / (L - K)
    return 0.3 + 0.7 * (L - A) / (B - L)  # L <= K: saturated instance


def evaluate(solver, instances_dir, reference, work_dir, per_instance_seconds,
             jobs):
    """Run + verify every instance in the reference, in parallel: each
    instance gets its own wall-clock limit and its own core."""
    ncores = max(1, os.cpu_count() or 1)
    jobs = max(1, min(jobs, ncores))

    def one(name, core):
        inst_path = os.path.join(instances_dir, name)
        out_path = os.path.join(work_dir, name + ".out")
        B, K = reference[name]["B"], reference[name]["K"]
        L = reference[name].get("L")
        rec = {"B": B, "K": K, "L": L, "A": None, "raw": None, "score": 0.0,
               "status": "ok"}
        if not os.path.exists(inst_path):
            rec["status"] = "instance file missing on judge side"
            return name, rec
        secs, err = run_solver(solver, inst_path, out_path,
                               per_instance_seconds, core)
        rec["seconds"] = round(secs, 2)
        if err is None:
            size, verr = verify_edits(inst_path, out_path)
            if verr is None:
                rec["A"] = size
            else:
                rec["status"] = verr
        else:
            rec["status"] = err
        if rec["A"] is not None and B > K:
            # SOL raw ratio (judged); v0 piecewise kept in "score" only.
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
    """v0 mean of clipped scores + SOL mean over participating (B > K)."""
    part = [n for n in results if reference[n]["B"] > reference[n]["K"]]
    total = sum(results[n]["score"] for n in part) / len(part) if part else 0.0
    raws = [results[n]["raw"] for n in part if results[n]["raw"] is not None]
    # SOL: map each untruncated per-instance raw FIRST, then average
    # (failed instances carry raw None and contribute 0). Mirrors
    # judge_worker._sol_rescore on this reward JSON — keep in sync.
    sol = (sum(1.0 / max(2.0 - results[n]["raw"], 1e-9)
               if results[n]["raw"] is not None else 0.0
               for n in part) / len(part)) if part else 0.0
    return {
        "reward": total,
        "sol_score": sol,
        "participating": len(part),
        "excluded_B_equals_K": sorted(n for n in results if n not in part),
        "mean_raw_unclipped": (sum(raws) / len(raws)) if raws else None,
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
    work_dir = os.path.join("/tmp", f"ce-score-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)

    solver, err = build_solver(app_dir)
    if err:
        return {"reward": 0.0, "build_error": err, "per_instance": {}}
    results = evaluate(solver, instances_dir, reference, work_dir,
                       PER_INSTANCE_SECONDS, JUDGE_JOBS)
    out = summarize(results, reference)
    out["per_instance_seconds"] = PER_INSTANCE_SECONDS
    out["judge_jobs"] = max(1, min(JUDGE_JOBS, os.cpu_count() or 1))
    out["per_instance"] = results
    return out


if __name__ == "__main__":
    print(json.dumps(main(sys.argv), indent=1, sort_keys=True))
