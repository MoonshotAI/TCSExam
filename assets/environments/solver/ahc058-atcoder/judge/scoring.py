"""Shared scoring logic for the ahc058-atcoder task.

Used by BOTH sides so the formula and the validity check cannot diverge:
  - agent side:  /app/run_public.py     (public instances, public reference)
  - judge side:  /tests/checker.py      (hidden instances, hidden reference)

Pipeline: run `bash /app/build.sh` (must produce /app/solver) -> for each
instance, run `solver < instance` with the PER-INSTANCE wall-clock budget
in env AHC_INSTANCE_SECONDS (hard-killed at the limit) -> validate the
printed action sequence and re-simulate it with
check_ahc() below -> A = the raw AHC058 score
round(100000 * log2(final_apples)) of the (valid) sequence ->
per-instance gap ratio r = (A - B) / (K - B), unclipped -> arithmetic mean.
Instances with K <= B carry no signal and are excluded.

The simulation in check_ahc() is a bit-faithful port of the official
AHC058 scorer (tools/src/lib.rs, compute_score): signed 64-bit wrap-around
on every arithmetic step, the same action-parsing rules (T lines, each
"-1" or "<level> <id>"), the same legality rule (an upgrade whose cost
exceeds the current apples invalidates the run), and the same final score.
The port was cross-checked against the compiled official `vis` binary on
all calibration outputs (see tests/calibration/).

Validity: the output must provide exactly T parseable actions (blank lines
and lines starting with '#' are skipped, as in the official parser). A
parse error, or a simulation error (an unaffordable upgrade, non-positive
apples at the end), scores 0 for that instance; the others still count.
Nothing the solver prints beyond the action sequence is trusted.

Time budget (2026-09-06, aligned with the official AHC058 rule): EACH
INSTANCE gets its own wall-clock limit of PER_INSTANCE_SECONDS (2 s = the
per-test-case limit of the official AtCoder Heuristic Contest 058,
atcoder.jp/contests/ahc058/tasks). There is no shared pool and no
redistribution — the solver sees one instance at a time and may use the
full per-instance budget on it. The budget is handed to the solver via
env AHC_INSTANCE_SECONDS, and the legacy name AHC_TIME_POOL is set to the
same value so solvers written against the old shared-pool contract still
see a correct per-instance limit. Instances are evaluated in parallel
(JUDGE_JOBS workers, each pinned to a core with taskset). Validity
checking does not consume the budget.

The raw unclipped values are reported per instance; raw > 1 means the
submission beat the recorded best-known value K. K here is NOT a proven
optimum — it is the best score found by the task authors' long beam-search
runs (see tests/calibration/) — so raw > 1 is possible in principle; it is
surfaced for investigation, never silently dropped;
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
import math
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
# Per-instance wall-clock budget in seconds (AHC058 official: 2 s per
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


MASK64 = (1 << 64) - 1


def i64(x):
    """Signed 64-bit wrap-around, matching Rust i64 arithmetic in release."""
    x &= MASK64
    return x - (1 << 64) if x >= (1 << 63) else x


def load_instance(path):
    """AHC058 format: N L T K, then N values A, then L rows of N costs C."""
    with open(path) as f:
        vals = f.read().split()
    pos = 0

    def nxt():
        nonlocal pos
        if pos >= len(vals):
            raise ValueError("unexpected end of instance file")
        v = int(vals[pos])
        pos += 1
        return v

    N, L, T, K = nxt(), nxt(), nxt(), nxt()
    A = [nxt() for _ in range(N)]
    C = [[nxt() for _ in range(N)] for _ in range(L)]
    return {"N": N, "L": L, "T": T, "K": K, "A": A, "C": C}


def parse_actions(inst, text):
    """Port of the official parse_output. Returns (actions, None) or
    (None, reason). Each action is -1 (nothing) or (level, id)."""
    N, L, T = inst["N"], inst["L"], inst["T"]
    actions = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        toks = line.split()
        try:
            first = int(toks[0])
        except (ValueError, IndexError):
            return None, f"parse error on line: {line!r}"
        if first < -1 or first > L - 1:
            return None, f"level {first} out of range -1..{L - 1}"
        if first == -1:
            actions.append(-1)
        else:
            if len(toks) < 2:
                return None, f"missing id on line: {line!r}"
            try:
                mid = int(toks[1])
            except ValueError:
                return None, f"parse error on line: {line!r}"
            if mid < 0 or mid >= N:
                return None, f"machine id {mid} out of range 0..{N - 1}"
            actions.append((first, mid))
        if len(toks) > (1 if first == -1 else 2):
            return None, f"too many tokens on line: {line!r}"
        if len(actions) == T:
            break
    if len(actions) < T:
        return None, f"not enough actions: expected {T}, got {len(actions)}"
    return actions, None


def simulate(inst, actions):
    """Port of the official compute_score_details. Returns (score, error);
    score is 0 whenever error is non-empty."""
    N, L, T, K = inst["N"], inst["L"], inst["T"], inst["K"]
    A, C = inst["A"], inst["C"]
    B = [[1] * N for _ in range(L)]
    P = [[0] * N for _ in range(L)]
    apples = K
    for t in range(T):
        act = actions[t]
        if act != -1:
            level, mid = act
            cost = i64(C[level][mid] * i64(P[level][mid] + 1))
            if apples < cost:
                return 0, (f"not enough apples at turn {t}: "
                           f"have {apples}, need {cost}")
            apples = i64(apples - cost)
            P[level][mid] += 1
        for level in range(L):
            for mid in range(N):
                if level == 0:
                    apples = i64(apples + i64(i64(A[mid] * B[0][mid])
                                              * P[0][mid]))
                else:
                    B[level - 1][mid] = i64(
                        B[level - 1][mid] + i64(B[level][mid]
                                                * P[level][mid]))
    if apples <= 0:
        return 0, f"non-positive apples at the end: {apples}"
    score = math.floor(100000.0 * math.log2(float(apples)) + 0.5)
    return score, ""


def check_ahc(instance_path, out_path):
    """Return (score, None) for a valid action sequence (score recomputed
    from scratch; 0 if the run went bankrupt), else (None, reason)."""
    try:
        inst = load_instance(instance_path)
    except (ValueError, OSError) as e:
        return None, f"could not load instance: {e}"
    try:
        with open(out_path, errors="replace") as f:
            text = f.read()
    except OSError as e:
        return None, f"could not read solver output: {e}"
    actions, err = parse_actions(inst, text)
    if err is not None:
        return None, err
    score, sim_err = simulate(inst, actions)
    if sim_err:
        # Well-formed but the run breaks the economy rules: official score 0.
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
            a, cerr = check_ahc(inst_path, out_path)
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
    work_dir = os.path.join("/tmp", f"ahc058-score-{os.getpid()}")
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
