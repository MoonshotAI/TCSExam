"""Shared scoring logic for the logic-syn-iwls2023 task.

Used by BOTH sides so the formula and the validity check cannot diverge:
  - agent side:  /app/score_public.py   (public instances, public reference)
  - judge side:  /tests/checker.py      (hidden instances, hidden reference)
The judge side uses its own pristine copies of this file and aiglib.py
under /tests (never the agent-writable /app copies).

Pipeline: run `bash /app/build.sh` (must produce /app/solver) -> for each
instance, run `solver TRUTH_FILE OUTPUT_AIG` with the REMAINING time pool
in env LS_TIME_POOL (hard-killed when the pool is exhausted; no
per-instance limit) -> validate the produced circuit: parse binary AIGER
(aiglib; latches, property sections, malformed or oversized files are
rejected), simulate it exhaustively over all 2^n input patterns and
compare against the reference truth table bit for bit -> A = number of
two-input AND gates -> per-instance gap ratio r = (B - A) / (B - K), unclipped -> arithmetic mean. Instances with B == K carry no signal and are
excluded.

Validity: entirely decided by the aiglib check — functional equivalence
against the truth table by exhaustive simulation. The solver's own claims
are never trusted; there is nothing to trust but the circuit file itself.

Time budget: ONE TOTAL TIME POOL covers all instances — there is no
per-instance limit. The pool size is
    TOTAL_POOL = PER_INSTANCE_SECONDS * number_of_instances
The solver learns the remaining pool from env LS_TIME_POOL on every run
and decides how to distribute it; when the pool is used up, every instance
without a verified circuit scores 0. Checker runs do not consume the pool.
A solver run that is killed mid-instance leaves whatever OUTPUT file it
already wrote — if that file holds a valid equivalent circuit it still
counts.

The raw unclipped values are reported per instance; raw > 1 means the
submission beat the reference best known value and is investigated, never silently dropped;
under the finalized formula it counts unclipped (r > 1).

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
import signal
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aiglib

BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
CHECK_TIMEOUT = int(os.environ.get("CHECK_TIMEOUT", "300"))
# Per-instance reference seconds; total pool = this value x instance count.
# The judge enforces the pool globally, NOT per instance.
PER_INSTANCE_SECONDS = float(os.environ.get("PER_INSTANCE_SECONDS", "180"))
# Hard caps against denial-of-service submissions.
MAX_AIG_FILE_BYTES = 64 * 1024 * 1024
MAX_AND_GATES = 2_000_000


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


def run_solver(solver, truth_path, out_path, remaining_pool):
    """Run solver TRUTH OUTPUT with hard timeout = remaining pool.

    The solver learns the remaining pool via env LS_TIME_POOL and is free
    to use as much of it as it wants on this instance. Returns
    (seconds, None) on exit code 0, (seconds, reason) otherwise.
    """
    env = dict(os.environ)
    env["LS_TIME_POOL"] = f"{remaining_pool:.3f}"
    t0 = time.time()
    with open(out_path, "w"):
        pass  # truncate any stale output from a previous run
    p = subprocess.Popen(
        [solver, truth_path, out_path],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, env=env, start_new_session=True,
    )
    try:
        p.wait(timeout=remaining_pool)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        p.wait()
        return time.time() - t0, "time pool exhausted during this instance"
    seconds = time.time() - t0
    if p.returncode != 0:
        return seconds, f"solver exited with code {p.returncode}"
    return seconds, None


def check_circuit(truth_path, out_path):
    """Validate the produced circuit against the truth table.

    Return (and_count, None) iff the file is a well-formed combinational
    binary AIGER circuit computing exactly the reference function;
    otherwise (None, reason).
    """
    if not (os.path.exists(out_path) and os.path.getsize(out_path) > 0):
        return None, "solver produced no output file"
    if os.path.getsize(out_path) > MAX_AIG_FILE_BYTES:
        return None, f"output file exceeds {MAX_AIG_FILE_BYTES} bytes"
    t0 = time.time()
    try:
        with open(truth_path) as f:
            n, masks = aiglib.parse_truth(f.read())
    except ValueError as e:
        return None, f"judge-side truth file broken: {e}"
    try:
        with open(out_path, "rb") as f:
            data = f.read()
        aig = aiglib.parse_aiger(data, max_and=MAX_AND_GATES)
    except aiglib.AigerError as e:
        return None, f"invalid AIGER: {e}"
    try:
        err = aiglib.check_circuit(aig, n, masks)
    except ValueError as e:
        return None, f"simulation failed: {e}"
    if time.time() - t0 > CHECK_TIMEOUT:
        return None, f"checker timed out after {CHECK_TIMEOUT}s"
    if err is not None:
        return None, err
    return aig.n_ands, None


def evaluate(solver, instances_dir, reference, work_dir, pool_seconds):
    """Run + check every instance in the reference under one shared pool."""
    results = {}
    spent = 0.0
    for name in sorted(reference):
        ent = reference[name]
        truth_path = os.path.join(instances_dir, ent["truth"])
        out_path = os.path.join(work_dir, name + ".aig")
        B, K = ent["B"], ent["K"]
        rec = {"B": B, "K": K, "A": None, "raw": None, "score": 0.0,
               "status": "ok", "seconds": 0.0}
        if not os.path.exists(truth_path):
            rec["status"] = "instance file missing on judge side"
            results[name] = rec
            continue
        remaining = pool_seconds - spent
        if remaining <= 0:
            rec["status"] = "time pool exhausted before this instance"
            results[name] = rec
            continue
        seconds, err = run_solver(solver, truth_path, out_path, remaining)
        spent += seconds
        rec["seconds"] = round(seconds, 2)
        if err is not None:
            # A killed solver may still have written a valid circuit;
            # the checker decides. Note the timeout in the record.
            cost, cerr = check_circuit(truth_path, out_path)
            if cerr is None:
                rec["A"] = cost
                rec["status"] = f"ok (solver note: {err})"
            else:
                rec["status"] = f"{err}; {cerr}"
        else:
            cost, cerr = check_circuit(truth_path, out_path)
            if cerr is None:
                rec["A"] = cost
            else:
                rec["status"] = cerr
        if rec["A"] is not None and B > K:
            rec["raw"] = (B - rec["A"]) / (B - K)
            rec["score"] = min(1.0, max(0.0, rec["raw"]))
        results[name] = rec
    return results, spent


def summarize(results, reference, pool_seconds, spent):
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
        "pool_seconds": pool_seconds,
        "pool_seconds_spent": round(spent, 2),
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
    work_dir = os.path.join("/tmp", f"ls-score-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)
    pool_seconds = float(os.environ.get(
        "TOTAL_TIME_POOL", str(PER_INSTANCE_SECONDS * len(reference))))

    solver, err = build_solver(app_dir)
    if err:
        return {"reward": 0.0, "build_error": err, "per_instance": {}}
    results, spent = evaluate(solver, instances_dir, reference, work_dir,
                              pool_seconds)
    out = summarize(results, reference, pool_seconds, spent)
    out["per_instance"] = results
    return out


if __name__ == "__main__":
    print(json.dumps(main(sys.argv), indent=1, sort_keys=True))
