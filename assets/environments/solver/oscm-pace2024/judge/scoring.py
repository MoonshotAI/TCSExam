"""Shared scoring logic for the oscm-pace2024 task.

Used by BOTH sides so the formula and the verifier cannot diverge:
  - agent side:  /app/score_public.py   (public instances, public reference)
  - judge side:  /tests/checker.py      (hidden instances, hidden reference)

Pipeline: run `bash /app/build.sh` (must produce /app/solver) -> run the
solver once per instance -> validate the printed ordering and count its
crossings with the official PACE 2024 verifier code (pace2024-verifier pip
package, segtree counting method) -> A = number of crossings -> per-instance gap ratio r = (B - A) / (B - K), unclipped -> arithmetic mean.
Instances with B == K carry no signal and are excluded. Reference entries
flagged "exclude": true (e.g. instances with no official published
solution) are carried for documentation only — never run, never scored.

Validity: the official verifier reads the solution as a list of vertex ids
and only rejects ids outside the free layer; we additionally require the
output to be a full permutation of the n2 free-layer vertices (what the PACE
rules demand). The crossing count itself is computed by the unmodified
official code path (read_graph + set_order + countcrossings_segtree).

Time budget: each instance gets its own wall-clock limit
(PER_INSTANCE_SECONDS, 1800 s by default — the official PACE 2024
exact-track per-instance limit). Instances are evaluated in parallel
(JUDGE_JOBS workers, each pinned to a core). Verification time does not
consume the limit.

The raw unclipped values are reported per instance; raw > 1 means the
submission beat the best known solution (here: the proven optimum) and is
investigated, never silently dropped;
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
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
PER_INSTANCE_SECONDS = int(os.environ.get("PER_INSTANCE_SECONDS", "1800"))
JUDGE_JOBS = int(os.environ.get("JUDGE_JOBS", "0")) or max(1, (os.cpu_count() or 1))
VERIFY_TIMEOUT = int(os.environ.get("VERIFY_TIMEOUT", "300"))

# Hard wall-clock cap for one crossing-count computation. Counting is
# O(m log n2) on instances with m <= ~33k edges, so seconds; the cap only
# guards against pathological solver outputs.
def _count_crossings(instance_path, out_path):
    """Official PACE 2024 verifier code path. Returns (crossings, None) or
    (None, reason). The ordering must be a permutation of the free layer."""
    try:
        from pace2024_verifier.pace import read_graph
    except ImportError as e:  # pragma: no cover - image always has it
        return None, f"official verifier not importable: {e}"
    try:
        g = read_graph(instance_path)
    except Exception as e:
        return None, f"verifier could not read instance: {e}"
    n1, n2 = g.left, len(g.right)
    try:
        order = []
        with open(out_path, errors="replace") as f:
            for line in f:
                line = line.strip()
                if line:
                    order.append(int(line))
    except (OSError, ValueError) as e:
        return None, f"solver output is not a list of vertex ids: {e}"
    expect = set(range(n1 + 1, n1 + n2 + 1))
    got = set(order)
    if len(order) != n2 or got != expect:
        missing = len(expect - got)
        extra = len(got - expect)
        return None, (f"not a permutation of the {n2} free vertices "
                      f"(lines={len(order)}, missing={missing}, foreign={extra})")
    try:
        g.set_order(order)
        crossings = g.countcrossings_segtree()
    except Exception as e:
        return None, f"official verifier failed to count crossings: {e}"
    return crossings, None


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
    """Run solver < instance > out_path with a wall-clock timeout.
    Returns (seconds_used, None) on success, else (seconds_used, reason)."""
    t0 = time.time()
    with open(instance_path) as fin, open(out_path, "w") as fout:
        cmd = [solver] if core is None else ["taskset", "-c", str(core), solver]
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
        rec = {"B": B, "K": K, "A": None, "raw": None, "score": 0.0,
               "status": "ok"}
        if reference[name].get("practice_no_anchors") is True:
            rec["practice_no_anchors"] = True
        if not os.path.exists(inst_path):
            rec["status"] = "instance file missing on judge side"
            return name, rec
        secs, err = run_solver(solver, inst_path, out_path,
                               per_instance_seconds, core)
        rec["seconds"] = round(secs, 2)
        if err is None:
            t0 = time.time()
            crossings, verr = _count_crossings(inst_path, out_path)
            rec["verify_seconds"] = round(time.time() - t0, 2)
            if verr is None:
                rec["A"] = crossings
            else:
                rec["status"] = verr
        else:
            rec["status"] = err
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


def summarize(results, reference):
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
    # Entries flagged "exclude" (e.g. no official published solution) are
    # carried in the reference for documentation only: never run, never
    # scored.
    excluded = sorted(n for n, r in reference.items() if r.get("exclude"))
    reference = {n: r for n, r in reference.items() if not r.get("exclude")}
    work_dir = os.path.join("/tmp", f"oscm-score-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)

    solver, err = build_solver(app_dir)
    if err:
        return {"reward": 0.0, "build_error": err, "per_instance": {}}
    results = evaluate(solver, instances_dir, reference, work_dir,
                       PER_INSTANCE_SECONDS, JUDGE_JOBS)
    out = summarize(results, reference)
    out["excluded_by_reference"] = excluded
    out["per_instance_seconds"] = PER_INSTANCE_SECONDS
    out["judge_jobs"] = max(1, min(JUDGE_JOBS, os.cpu_count() or 1))
    out["per_instance"] = results
    return out


if __name__ == "__main__":
    print(json.dumps(main(sys.argv), indent=1, sort_keys=True))
