"""Shared scoring logic for the qbf-qbfeval task.

Used by BOTH sides so the formula and the verifier cannot diverge:
  - agent side:  /app/score_public.py   (public 13 instances, public reference)
  - judge side:  /tests/checker.py      (judged 57 instances, judge reference)

Pipeline: run `bash /app/build.sh` (must produce /app/solver) -> for each
instance, run `solver < instance.qdimacs` with the per-instance wall-clock
budget in env QBF_INSTANCE_SECONDS (the process group is hard-killed at
the limit) and the proof destination in env QBF_PROOF_PATH -> check the
answer (verify_qbf.check: both TRUE and FALSE claims need a certificate
that passes the qrp2rup + drat-trim chain — the official label is never
consulted) -> per-instance A in {0, 1} solved flags.

Instances may be stored as plain `<name>.qdimacs` or compressed
`<name>.qdimacs.xz`; the latter are decompressed to the work dir
just-in-time (and removed right after) so the full instance pool never has
to sit on disk at once.

Time budget (aligned with the official QBFEVAL'20 rule): EACH
INSTANCE gets its own wall-clock limit of PER_INSTANCE_SECONDS (900 s CPU,
the QBFEVAL'20 budget; memory 32 GB at the competition, the judging
sandbox is sized per-worker accordingly); there is no shared pool and no
redistribution — the solver sees one instance at a time and may use the
full per-instance budget on it. Instances are evaluated in parallel
(JUDGE_JOBS workers, each pinned to a core with taskset). Certificate
checking (qrp2rup + drat-trim) does not consume the limit. On the judge
side the instance list may be a shard slice (the checker restricts the
reference via INSTANCE_SHARD); each shard reports its slice's
participating count and the service merges shard scores weighted by it,
reproducing the unsharded mean exactly.

Score (decision problem, so per-instance values are binary):
    per-instance raw = (A - B) / (K - B) for participating instances
                       (K > B); instances with K <= B carry no signal and
                       are excluded from the mean
    B = whether the baseline (qute wrapper, proof-producing) verifiably
        solves the instance within the same 900 s budget, measured on the
        judging-equivalent machine (see tests/SAMPLING.md)
    K = whether the reference solver (QBFEVAL'20 PCNF track winner) solved
        the instance under the competition 900 s budget (official result)
    judged score (260920 finalized): solve-count gap ratio
                       r = (S_A - S_B) / (S_K - S_B), unclipped,
                       computed by the metric engine from this
                       file's records
    reward (this file's legacy local aggregate) = mean of
                       clip(raw, 0, 1) over participating
                       instances — not the judged score

The unclipped per-instance raw is reported alongside; raw > 1 means the
submission beat the reference solver on an instance and is investigated
and counts unclipped (r > 1) under the finalized formula. Instances the reference could not solve (K = 0)
that the agent solves are listed under `breakthrough`.

QBF_ONLY (optional env): comma-separated instance names — restrict the run
to that subset. Used by the agent-side self-scoring for quick iterations;
the judge never sets it.
"""

import json
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_qbf

BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
# Per-instance wall-clock budget (QBFEVAL'20 official: 900 s CPU).
PER_INSTANCE_SECONDS = float(os.environ.get("PER_INSTANCE_SECONDS", "900"))


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


def materialize(instances_dir, name, work_dir):
    """Return the path of a decompressed .qdimacs for `name`.

    Accepts `<name>.qdimacs` directly; `<name>.qdimacs.xz` is decompressed
    into the work dir. Returns (path, cleanup_path_or_None, error_or_None).
    """
    plain = os.path.join(instances_dir, name + ".qdimacs")
    if os.path.exists(plain):
        return plain, None, None
    packed = os.path.join(instances_dir, name + ".qdimacs.xz")
    if os.path.exists(packed):
        dest = os.path.join(work_dir, name + ".qdimacs")
        try:
            with open(packed, "rb") as fin, open(dest, "wb") as fout:
                subprocess.run(["xz", "-dc"], stdin=fin, stdout=fout,
                               check=True)
        except Exception as e:
            return None, None, f"decompress failed: {e}"
        return dest, dest, None
    return None, None, "instance file missing on judge side"


def run_solver(solver, instance_path, out_path, proof_path, budget, core=None):
    """Run solver < instance > out_path with the per-instance wall-clock
    budget, optionally pinned to a core via taskset.

    The solver learns the budget via env QBF_INSTANCE_SECONDS. Whatever the
    verdict, it must write its certificate to the path in env
    QBF_PROOF_PATH. Returns (seconds, None) on success, (seconds, reason)
    otherwise.
    """
    env = dict(os.environ)
    env["QBF_INSTANCE_SECONDS"] = f"{budget:.3f}"
    env["QBF_PROOF_PATH"] = proof_path
    cmd = [solver] if core is None else ["taskset", "-c", str(core), solver]
    t0 = time.time()
    with open(instance_path) as fin, open(out_path, "w") as fout:
        p = subprocess.Popen(
            cmd, stdin=fin, stdout=fout, env=env,
            stderr=subprocess.DEVNULL, start_new_session=True,
        )
        try:
            p.wait(timeout=budget)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
            return time.time() - t0, f"timeout after {round(budget, 1)}s"
    seconds = time.time() - t0
    # QBF evaluation convention: exit 10 = true, 20 = false.
    # Both (and plain 0) mean the solver ran fine; the answer check decides.
    if p.returncode not in (0, 10, 20):
        return seconds, f"solver exited with code {p.returncode}"
    return seconds, None


def evaluate(solver, instances_dir, reference, work_dir, jobs):
    """Run + verify every instance in the reference, in parallel: each
    instance gets its own wall-clock limit and its own core."""
    ncores = _cpu_quota()
    jobs = max(1, min(jobs, ncores))

    def one(name, core):
        out_path = os.path.join(work_dir, name + ".out")
        proof_path = os.path.join(work_dir, name + ".qrp")
        B, K = reference[name]["B"], reference[name]["K"]
        rec = {"B": B, "K": K, "A": 0, "raw": None, "score": 0.0,
               "status_label": reference[name].get("status", "true"),
               "status": "ok", "seconds": 0.0}
        inst_path, cleanup, err = materialize(instances_dir, name, work_dir)
        if err is not None:
            rec["status"] = err
            return name, rec
        seconds, err = run_solver(solver, inst_path, out_path, proof_path,
                                  PER_INSTANCE_SECONDS, core)
        rec["seconds"] = round(seconds, 2)
        if err is None:
            ok, reason = verify_qbf.check(inst_path, out_path, proof_path)
            if ok:
                rec["A"] = 1
            else:
                rec["status"] = f"answer rejected ({reason})"
        else:
            rec["status"] = err
        for path in (cleanup, out_path, proof_path):
            if path:
                try:
                    os.remove(path)
                except OSError:
                    pass
        if K > B:
            rec["raw"] = (rec["A"] - B) / (K - B)
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
    """Mean of the legacy clipped local `score` over participating (K > B)
    instances — not the judged score (the judged score is the solve-count
    gap ratio (S_A - S_B) / (S_K - S_B), unclipped, computed by the metric
    engine; see module docstring)."""
    part = [n for n in results
            if reference[n]["K"] > reference[n]["B"]]
    total = sum(results[n]["score"] for n in part) / len(part) if part else 0.0
    raws = [results[n]["raw"] for n in part if results[n]["raw"] is not None]
    s_a = sum(r["A"] for r in results.values())
    s_b = sum(reference[n]["B"] for n in results)
    s_k = sum(reference[n]["K"] for n in results)
    return {
        "reward": total,
        # Solve-count gap ratio (the judged aggregate, 260920
        # finalized): the metric engine's solve-count path maps
        # this top-level ratio, unclipped; the per-instance detail is
        # diagnostic only (emitted as per_instance_detail in main) and
        # must not drive the per-instance computation — solve-count r is
        # itself an aggregate.
        "raw_unclipped": (s_a - s_b) / (s_k - s_b) if s_k > s_b else None,
        "participating": len(part),
        "excluded_no_signal": sorted(n for n in results if n not in part),
        "mean_raw_unclipped": (sum(raws) / len(raws)) if raws else None,
        "solved_agent": s_a,
        "solved_baseline": s_b,
        "solved_reference": s_k,
        "n_instances": len(results),
        "per_instance_seconds": PER_INSTANCE_SECONDS,
        "breakthrough": sorted(n for n in results
                               if results[n]["A"] == 1
                               and reference[n]["K"] == 0),
    }


def load_reference(path):
    with open(path) as f:
        data = json.load(f)
    instances = data["instances"]
    only = os.environ.get("QBF_ONLY")
    if only:
        keep = set(only.split(","))
        instances = {n: r for n, r in instances.items() if n in keep}
    return instances


def main(argv):
    if len(argv) != 4:
        print(f"usage: {argv[0]} APP_DIR INSTANCES_DIR REFERENCE_JSON",
              file=sys.stderr)
        return 2
    app_dir, instances_dir, ref_path = argv[1], argv[2], argv[3]
    reference = load_reference(ref_path)
    work_dir = os.path.join("/tmp", f"qbf-score-{os.getpid()}")
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
