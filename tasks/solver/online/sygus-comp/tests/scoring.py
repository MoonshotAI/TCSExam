"""Shared scoring logic for the sygus-comp task.

Used by BOTH sides so the formula and the validity check cannot diverge:
  - agent side:  /app/score_public.py   (public instances, public reference)
  - judge side:  /tests/checker.py      (hidden instances, hidden reference)

Pipeline: run `bash /app/build.sh` (must produce /app/solver) -> for each
instance, run `solver INSTANCE.sl` with the per-instance wall-clock budget
in env SYGUS_INSTANCE_SECONDS (the process group is hard-killed at the
limit) -> the solver's stdout is a candidate solution in SyGuS define-fun
form -> the two-step machine check in sygus_check.py (grammar derivability
when the synth-fun has a grammar, then negated-spec unsat via a PRISTINE
cvc5, never the agent's build) decides validity -> per-instance A in
{0, 1} solved flags.

Every claimed solution is fully falsifiable by the machine check (unlike
an SMT unsat claim), so there is no wrong-answer penalty: an invalid
solution, a crash, a nonzero exit, or no output scores 0 for that
instance and nothing more.

Time budget (aligned with the official SyGuS-Comp rule): EACH
INSTANCE gets its own wall-clock limit of PER_INSTANCE_SECONDS (3600 s,
the SyGuS-Comp budget); there is no shared pool and no redistribution —
the solver sees one instance at a time and may use the full per-instance
budget on it. Instances are evaluated in parallel (JUDGE_JOBS workers,
each pinned to a core with taskset). Answer checking does not consume the
limit. On the judge side the instance list may be a shard slice (the
checker restricts the reference via INSTANCE_SHARD); each shard reports
its slice's participating count and the service merges shard scores
weighted by it, reproducing the unsharded mean exactly.

Score (per-instance values are binary solved flags):
    per-instance raw = (A - B) / (K - B) for participating instances
                       (K > B); instances with K <= B carry no signal and
                       are excluded from the mean
    B = whether the unmodified baseline (stock cvc5 default SyGuS
        configuration) verifiably solves the instance within the same
        3600 s budget, measured on the judging-equivalent machine at task
        construction (see tests/SAMPLING.md for the protocol)
    K = whether the reference run solves it within the same budget (see
        tests/SAMPLING.md for the reference configuration)
    judged score (260920 finalized): solve-count gap ratio
                       r = (S_A - S_B) / (S_K - S_B), unclipped,
                       computed by the metric engine from this
                       file's records
    reward (this file's legacy local aggregate) = mean of
                       clip(raw, 0, 1) over participating
                       instances — not the judged score

The unclipped per-instance raw is reported alongside; raw > 1 means the
submission beat the reference on an instance and is investigated and
counts unclipped (r > 1) under the finalized formula. Instances the reference could not solve (K = 0) that
the agent solves are listed under `breakthrough`.
"""

import json
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sygus_check

BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
# Per-instance wall-clock budget (SyGuS-Comp official: 3600 s).
PER_INSTANCE_SECONDS = float(os.environ.get("PER_INSTANCE_SECONDS", "3600"))
# Per-instance timeout for the machine check's SMT query (milliseconds).
VERIFY_TIMEOUT_MS = int(os.environ.get("SYGUS_VERIFY_TIMEOUT_MS", "90000"))


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


def run_solver(solver, instance_path, out_path, timeout, core=None):
    """Run `solver instance > out_path` with a wall-clock timeout, optionally
    pinned to a core via taskset. The solver learns the per-instance budget
    via env SYGUS_INSTANCE_SECONDS. Returns (seconds, None) on success,
    (seconds, reason) otherwise."""
    env = dict(os.environ)
    env["SYGUS_INSTANCE_SECONDS"] = f"{timeout:.3f}"
    t0 = time.time()
    cmd = [solver] if core is None else ["taskset", "-c", str(core), solver]
    with open(out_path, "w") as fout:
        p = subprocess.Popen(
            cmd + [instance_path],
            stdout=fout, env=env,
            stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
            return time.time() - t0, f"timeout after {round(timeout, 1)}s"
    seconds = time.time() - t0
    if p.returncode != 0:
        return seconds, f"solver exited with code {p.returncode}"
    return seconds, None


def evaluate(solver, instances_dir, reference, work_dir, jobs):
    """Run + machine-check every instance in the reference, in parallel:
    each instance gets its own wall-clock limit and its own core."""
    ncores = _cpu_quota()
    jobs = max(1, min(jobs, ncores))
    names = sorted(reference["instances"])
    cvc5_check = sygus_check.CVC5_CHECK

    def one(name, core):
        inst_path = os.path.join(instances_dir, name)
        ref = reference["instances"][name]
        B, K = ref["B"], ref["K"]
        rec = {"B": B, "K": K, "A": 0, "raw": None, "score": 0.0,
               "status": "ok", "seconds": 0.0}
        if ref.get("practice_no_anchors") is True:
            rec["practice_no_anchors"] = True
        if not os.path.exists(inst_path):
            rec["status"] = "instance file missing on judge side"
            return name, rec
        out_path = os.path.join(work_dir, name + ".out")
        seconds, err = run_solver(solver, inst_path, out_path,
                                  PER_INSTANCE_SECONDS, core)
        rec["seconds"] = round(seconds, 2)
        if err is not None:
            rec["status"] = err
        else:
            try:
                with open(out_path, errors="replace") as f:
                    output = f.read()
            except OSError as e:
                rec["status"] = f"could not read solver output: {e}"
                return name, rec
            try:
                ok, reason = sygus_check.check_answer(
                    inst_path, output, cvc5=cvc5_check,
                    timeout_ms=VERIFY_TIMEOUT_MS)
            except Exception as e:
                # Fail closed: a checker crash (e.g. RecursionError on a
                # pathological nesting bomb) rejects this instance only.
                ok, reason = False, f"checker error: {type(e).__name__}: {e}"
            if ok:
                rec["A"] = 1
            else:
                rec["status"] = f"invalid solution ({reason})"
        if B is not None and K is not None and K > B:
            rec["raw"] = (rec["A"] - B) / (K - B)
            rec["score"] = min(1.0, max(0.0, rec["raw"]))
        return name, rec

    results = {}
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        futures = [ex.submit(one, name, i % jobs)
                   for i, name in enumerate(names)]
        for fut in futures:
            name, rec = fut.result()
            results[name] = rec
    return results


def summarize(results, reference):
    """Mean of the legacy clipped local `score` over participating (K > B)
    instances — not the judged score (the judged score is the solve-count
    gap ratio (S_A - S_B) / (S_K - S_B), unclipped, computed by the metric
    engine; see module docstring)."""
    # Practice keys (flagged practice_no_anchors, anchors null) are judged
    # and reported per-instance but never enter any aggregate: the
    # participating mean, the solve counts S_A/S_B/S_K, and the gap ratio
    # all range over anchored keys only.
    practice = sorted(n for n in results
                      if reference["instances"][n].get("practice_no_anchors")
                      is True)
    anchored = [n for n in results if n not in practice]
    part = [n for n in anchored
            if reference["instances"][n]["K"] > reference["instances"][n]["B"]]
    total = sum(results[n]["score"] for n in part) / len(part) if part else 0.0
    raws = [results[n]["raw"] for n in part if results[n]["raw"] is not None]
    s_a = sum(results[n]["A"] for n in anchored)
    s_b = sum(reference["instances"][n]["B"] for n in anchored)
    s_k = sum(reference["instances"][n]["K"] for n in anchored)
    return {
        "reward": total,
        # Solve-count gap ratio (the judged aggregate, 260920
        # finalized): the metric engine's solve-count path maps
        # this top-level ratio, unclipped; the per-instance detail is
        # diagnostic only (emitted as per_instance_detail in main) and
        # must not drive the per-instance computation — solve-count r is
        # itself an aggregate. S_B/S_K are summed from the (possibly
        # sharded) instance table so slice runs stay slice-consistent.
        "raw_unclipped": (s_a - s_b) / (s_k - s_b) if s_k > s_b else None,
        "participating": len(part),
        "excluded_no_signal": sorted(n for n in anchored if n not in part),
        "practice_no_anchors": practice,
        "mean_raw_unclipped": (sum(raws) / len(raws)) if raws else None,
        "S_A": s_a,
        "S_B": s_b,
        "S_K": s_k,
        "per_instance_seconds": PER_INSTANCE_SECONDS,
        "breakthrough": sorted(
            n for n in results
            if results[n]["A"] == 1 and reference["instances"][n]["K"] == 0),
        "regressed_vs_baseline": sorted(
            n for n in results
            if results[n]["A"] == 0 and reference["instances"][n]["B"] == 1),
    }


def load_reference(path):
    with open(path) as f:
        return json.load(f)


def main(argv):
    if len(argv) != 4:
        print(f"usage: {argv[0]} APP_DIR INSTANCES_DIR REFERENCE_JSON",
              file=sys.stderr)
        return 2
    app_dir, instances_dir, ref_path = argv[1], argv[2], argv[3]
    reference = load_reference(ref_path)
    work_dir = os.path.join("/tmp", f"sygus-score-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)

    solver, err = build_solver(app_dir)
    if err:
        return {"reward": 0.0, "build_error": err, "per_instance": {}}
    results = evaluate(solver, instances_dir, reference, work_dir, JUDGE_JOBS)
    out = summarize(results, reference)
    # Diagnostic only — must NOT be named "per_instance": that key would
    # route the judge worker onto the retired per-instance SOL remix
    # path, the wrong path for solve-count problems (see raw_unclipped in
    # summarize).
    out["per_instance_detail"] = results
    return out


if __name__ == "__main__":
    print(json.dumps(main(sys.argv), indent=1, sort_keys=True))
