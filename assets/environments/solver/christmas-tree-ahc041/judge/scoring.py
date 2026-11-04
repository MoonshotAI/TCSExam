"""Shared scoring logic for the christmas-tree-ahc041 task.

Used by BOTH sides so the formula and the validity check cannot diverge:
  - agent side:  /app/run_public.py     (public instances, public reference)
  - judge side:  /tests/checker.py      (hidden instances, hidden reference)

Pipeline: run `bash /app/build.sh` (must produce /app/solver) -> for each
instance, run `solver < instance` with the PER-INSTANCE wall-clock budget
in env AHC_INSTANCE_SECONDS (hard-killed at the limit) -> validate the
printed parent array and recompute the score with
check_ahc041() below -> A = the raw AHC041 score
1 + sum_v (depth(v) + 1) * A[v] -> per-instance gap ratio r = (A - B) / (K - B), unclipped -> arithmetic mean. Instances with K <= B carry no
signal and are excluded.

check_ahc041() is a behavior-faithful port of the official AHC041 scorer
(tools/src/lib.rs): parse_output (whitespace tokens grouped into blocks of
N parents, LAST block wins, parents must parse as i32 in -1..N-1, a
partial trailing block is an error), to_tree_nodes (a parent edge must
exist in G, every vertex must be reachable from an in-degree-0 root i.e.
no directed cycle), and compute_score_details (every depth <= H, score is
1 + sum A[v] * (h + 1)). The port was cross-checked against the compiled
official `vis` binary on baseline outputs and randomized adversarial
outputs (see tests/calibration/).

Validity: on any parse/validity error the instance scores 0 with the
reason recorded; the other instances still count. Nothing the solver
prints beyond the parent array is trusted.

Time budget (2026-09-06, aligned with the official AHC041 rule): EACH
INSTANCE gets its own wall-clock limit of PER_INSTANCE_SECONDS (2 s = the
per-test-case limit of the official AtCoder Heuristic Contest 041,
atcoder.jp/contests/ahc041/tasks/ahc041_a). There is no shared pool and
no redistribution — the solver sees one instance at a time and may use
the full per-instance budget on it. The budget is handed to the solver
via env AHC_INSTANCE_SECONDS, and the legacy name AHC_TIME_POOL is set to
the same value so solvers written against the old shared-pool contract
still see a correct per-instance limit. Instances are evaluated in
parallel (JUDGE_JOBS workers, each pinned to a core with taskset).
Validity checking does not consume the budget.

The raw unclipped values are reported per instance; raw > 1 means the
submission beat the recorded best-known value K. K here is NOT a proven
optimum — it is the best score found by the task authors' long simulated-
annealing runs (see tests/calibration/) — so raw > 1 is possible in
principle; it is surfaced for investigation, never silently dropped;
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
# Per-instance wall-clock budget in seconds (AHC041 official: 2 s per
# test case).
PER_INSTANCE_SECONDS = float(os.environ.get("PER_INSTANCE_SECONDS", "2"))

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


I32_MIN = -(1 << 31)
I32_MAX = (1 << 31) - 1


def load_instance(path):
    """AHC041 format: N M H, then N weights A, then M edges (u v),
    then N points (x y). Points are part of the input but unused by the
    scorer; they are parsed for completeness."""
    with open(path) as f:
        vals = f.read().split()
    pos = 0

    def nxt(what):
        nonlocal pos
        if pos >= len(vals):
            raise ValueError(f"unexpected end of instance file at {what}")
        v = int(vals[pos])
        pos += 1
        return v

    N, M, H = nxt("N"), nxt("M"), nxt("H")
    A = [nxt("A") for _ in range(N)]
    edges = [(nxt("u"), nxt("v")) for _ in range(M)]
    points = [(nxt("x"), nxt("y")) for _ in range(N)]
    edge_set = set()
    for u, v in edges:
        edge_set.add((min(u, v), max(u, v)))
    return {"N": N, "M": M, "H": H, "A": A, "edges": edges,
            "points": points, "edge_set": edge_set}


def parse_output(inst, text):
    """Port of the official parse_output. Returns (parents, None) for the
    LAST complete block, or (None, reason). Parents are i32 values in
    -1..N-1; extra trailing tokens forming a partial block are an error,
    exactly like the official Unexpected EOF."""
    N = inst["N"]
    toks = text.split()
    blocks = []
    i = 0
    n = len(toks)
    while i < n:
        if i + N > n:
            return None, ("unexpected end of output: partial block of "
                          f"{n - i} parents, need {N}")
        parents = []
        for j in range(N):
            tok = toks[i + j]
            try:
                p = int(tok)
            except ValueError:
                return None, f"parse error on token: {tok!r}"
            if p < I32_MIN or p > I32_MAX:
                return None, f"parent out of i32 range: {tok!r}"
            if p < -1 or p >= N:
                return None, f"parent {p} out of range -1..{N - 1}"
            parents.append(p)
        blocks.append(parents)
        i += N
    if not blocks:
        return None, "empty output"
    return blocks[-1], None


def compute_score(inst, parents):
    """Port of to_tree_nodes + compute_score_details. Returns
    (score, None) for a valid forest, else (None, reason)."""
    N, H, A = inst["N"], inst["H"], inst["A"]
    edge_set = inst["edge_set"]

    par = [0] * N
    for v in range(N):
        p = parents[v]
        if p == -1:
            par[v] = -1
            continue
        if (min(v, p), max(v, p)) not in edge_set:
            return None, (f"edge ({v}, {p}) is not included in the "
                          "original graph")
        par[v] = p

    # Depths by walking parent chains; a chain that loops before reaching
    # a root or a solved vertex is a directed cycle (official: the vertex
    # is never reached by the DFS from in-degree-0 roots).
    depth = [None] * N
    for v in range(N):
        if depth[v] is not None:
            continue
        chain = []
        on_chain = set()
        x = v
        while x != -1 and depth[x] is None:
            if x in on_chain:
                return None, (f"the connected component that contains "
                              f"vertex {v} is not a rooted tree")
            on_chain.add(x)
            chain.append(x)
            x = par[x]
        # base = depth of the node the chain hangs from; a root's parent
        # is -1 and the root itself sits at depth 0, hence base -1.
        base = -1 if x == -1 else depth[x]
        for k, node in enumerate(reversed(chain)):
            depth[node] = base + k + 1

    for v in range(N):
        if depth[v] is None:
            return None, (f"the connected component that contains vertex "
                          f"{v} is not a rooted tree")
    for v in range(N):
        if depth[v] > H:
            return None, f"vertex {v} is too high (h = {depth[v]})"

    score = 1
    for v in range(N):
        score += A[v] * (depth[v] + 1)
    return score, None


def check_ahc041(instance_path, out_path):
    """Return (score, None) for a valid parent array (score recomputed
    from scratch), else (None, reason) / (0, None) for a well-formed but
    rule-breaking output (official score 0)."""
    try:
        inst = load_instance(instance_path)
    except (ValueError, OSError) as e:
        return None, f"could not load instance: {e}"
    try:
        with open(out_path, errors="replace") as f:
            text = f.read()
    except OSError as e:
        return None, f"could not read solver output: {e}"
    parents, err = parse_output(inst, text)
    if err is not None:
        return None, err
    score, verr = compute_score(inst, parents)
    if verr is not None:
        return 0, None
    return score, None


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


def run_solver(solver, instance_path, out_path, limit_seconds, core=None):
    """Run solver < instance > out_path with a hard per-instance wall-clock
    limit, optionally pinned to a core via taskset.

    The solver learns the limit via env AHC_INSTANCE_SECONDS (the legacy
    name AHC_TIME_POOL is set to the same value) and is free to use as
    much of it as it wants on this instance. Returns (seconds, None) on
    success, (seconds, reason) otherwise.
    """
    env = dict(os.environ)
    env["AHC_INSTANCE_SECONDS"] = f"{limit_seconds:.3f}"
    env["AHC_TIME_POOL"] = f"{limit_seconds:.3f}"  # legacy name, same value
    t0 = time.time()
    with open(instance_path) as fin, open(out_path, "w") as fout:
        cmd = [solver]
        if core is not None:
            cmd = ["taskset", "-c", str(core)] + cmd
        p = subprocess.Popen(
            cmd, stdin=fin, stdout=fout, env=env,
            stderr=subprocess.DEVNULL, start_new_session=True,
        )
        try:
            p.wait(timeout=limit_seconds)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
            return time.time() - t0, "per-instance time limit exhausted"
    seconds = time.time() - t0
    if p.returncode != 0:
        return seconds, f"solver exited with code {p.returncode}"
    return seconds, None


def evaluate(solver, instances_dir, reference, work_dir, limit_seconds,
             jobs):
    """Run + check every instance in the reference, in parallel: each
    instance gets its own wall-clock limit and its own core."""
    ncores = _cpu_quota()
    jobs = max(1, min(jobs, ncores))

    def one(name, core):
        inst_path = os.path.join(instances_dir, name)
        out_path = os.path.join(work_dir, name + ".out")
        B, K = reference[name]["B"], reference[name]["K"]
        rec = {"B": B, "K": K, "A": None, "raw": None, "score": 0.0,
               "status": "ok", "seconds": 0.0}
        if not os.path.exists(inst_path):
            rec["status"] = "instance file missing on judge side"
            return name, rec
        seconds, err = run_solver(solver, inst_path, out_path,
                                  limit_seconds, core)
        rec["seconds"] = round(seconds, 2)
        if err is None:
            a, cerr = check_ahc041(inst_path, out_path)
            if cerr is None:
                rec["A"] = a
            else:
                rec["status"] = f"invalid solution ({cerr})"
        else:
            rec["status"] = err
        if rec["A"] is not None and K > B:
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


def summarize(results, reference, limit_seconds, jobs):
    """Mean of the legacy clipped local `score` over participating (K > B)
    instances — not the judged score (the judged score is the unclipped
    gap-ratio mean computed by the metric engine; see module docstring)."""
    part = [n for n in results if reference[n]["K"] > reference[n]["B"]]
    total = sum(results[n]["score"] for n in part) / len(part) if part else 0.0
    raws = [results[n]["raw"] for n in part if results[n]["raw"] is not None]
    return {
        "reward": total,
        "participating": len(part),
        "excluded_K_le_B": sorted(n for n in results if n not in part),
        "mean_raw_unclipped": (sum(raws) / len(raws)) if raws else None,
        "per_instance_seconds": limit_seconds,
        "judge_jobs": jobs,
        "beat_known_best": sorted(
            n for n in part
            if results[n]["A"] is not None and results[n]["A"] > reference[n]["K"]
        ),
    }


def load_reference(path):
    with open(path) as f:
        data = json.load(f)
    per_inst = data.get("meta", {}).get("per_instance_seconds")
    return data["instances"], float(per_inst or PER_INSTANCE_SECONDS)


def main(argv):
    if len(argv) != 4:
        print(f"usage: {argv[0]} APP_DIR INSTANCES_DIR REFERENCE_JSON",
              file=sys.stderr)
        return 2
    app_dir, instances_dir, ref_path = argv[1], argv[2], argv[3]
    reference, limit_seconds = load_reference(ref_path)
    limit_seconds = float(os.environ.get("PER_INSTANCE_SECONDS",
                                         str(limit_seconds)))
    work_dir = os.path.join("/tmp", f"ahc041-score-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)

    solver, err = build_solver(app_dir)
    if err:
        return {"reward": 0.0, "build_error": err, "per_instance": {}}
    results = evaluate(solver, instances_dir, reference, work_dir,
                       limit_seconds, JUDGE_JOBS)
    out = summarize(results, reference, limit_seconds,
                    max(1, min(JUDGE_JOBS, _cpu_quota())))
    out["per_instance"] = results
    return out


if __name__ == "__main__":
    print(json.dumps(main(sys.argv), indent=1, sort_keys=True))
