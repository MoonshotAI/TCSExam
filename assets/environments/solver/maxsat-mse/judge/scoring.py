"""Shared scoring logic for the maxsat-mse task.

Used by BOTH sides so the formula and the validity check cannot diverge:
  - agent side:  /app/score_public.py   (public instances, public reference)
  - judge side:  /tests/checker.py      (hidden instances, hidden reference)

Pipeline: run `bash /app/build.sh` (must produce /app/solver) -> for each
instance, run `solver < instance` with its own wall-clock limit (the process
group is hard-killed at the limit) -> parse the output (last "o" cost line,
last "v" bitstring assignment line, last "s" status line; "c" comment lines
are ignored) -> validate the answer with check_answer() below (every hard
clause satisfied; the cost recomputed from the assignment equals the declared
"o" value) -> A = validated cost -> per-instance score (B - A) / (B - K)
clipped to [0, 1] -> arithmetic mean. Instances with B <= K carry no signal
and are excluded from the mean.

Minimization, two anchors: B = cost reported by the shipped baseline solver
(Open-WBO 2.1 with a wall-clock soft limit, see PROVENANCE.md; B is pinned in
the reference at authoring time) and K = the best known cost from the MaxSAT
Evaluation registry (proven optimum where the registry lists one). An answer
with cost below K is impossible on instances whose optimum is proven, so a
raw value above 1 is surfaced for investigation (beat_known_best), never
silently clipped away.

Instance format (fixed): the classic WCNF format — "c" comment lines, one
header "p wcnf <n> <m> <top>", then m clause lines "<w> <lit> ... 0" (1-based
signed literals, 0-terminated). Clauses with weight w >= top are hard, the
others soft with weight w. (MSE 2022+ "h-line" files were converted to this
form at authoring time; see PROVENANCE.md.)

Output format (fixed): lines starting with "c" are comments; one status line
"s OPTIMUM FOUND" / "s SATISFIABLE" / "s UNKNOWN"; at least one cost line
"o <integer>"; and exactly one assignment line "v <bitstring>" where the
bitstring has exactly n characters from {0,1}, the i-th character giving the
value of variable i (the MSE 2022+ v-line format). When several o/v lines are
printed, the LAST ones count. The declared cost must equal the cost of the
printed assignment.

Time budget: each instance gets its own wall-clock limit
(PER_INSTANCE_SECONDS). The solver is expected to self-limit below that (the
shipped baseline stops at its internal soft limit, then prints its best
answer); the judge kills the process group at the limit, and a killed or
crashing run scores 0 for that instance. Instances are evaluated in parallel
(JUDGE_JOBS workers, each pinned to a core with taskset); the solver only
ever sees one instance at a time. Answer checking does not consume the limit.
"""

import json
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
PER_INSTANCE_SECONDS = int(os.environ.get("PER_INSTANCE_SECONDS", "300"))


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


def _allowed_cpus():
    """The list of CPU ids this container may run on (cgroup v2
    cpuset.cpus.effective), or None when unrestricted. Used to pin parallel
    solver runs to cores that actually exist in the container's cpuset."""
    try:
        with open("/sys/fs/cgroup/cpuset.cpus.effective") as f:
            cpus = f.read().strip()
        if not cpus:
            return None
        out = []
        for chunk in cpus.split(","):
            if "-" in chunk:
                lo, hi = chunk.split("-", 1)
                out.extend(range(int(lo), int(hi) + 1))
            else:
                out.append(int(chunk))
        return out or None
    except OSError:
        return None


def load_instance(path):
    """Classic WCNF: 'c' comments, header 'p wcnf n m top', then clause lines
    '<w> <lit> ... 0' (0-terminated; weight >= top means hard). The header's m
    is advisory; the clause list is what counts. Variables mentioned nowhere
    still count toward n (from the header). Returns (n, hard, soft) with
    hard a list of literal lists and soft a list of (weight, lits)."""
    n = -1
    top = None
    hard = []
    soft = []
    with open(path, "rb") as f:
        for raw in f:
            if not raw or raw[:1] in (b"c", b"\n", b"\r"):
                continue
            if raw[:1] == b"p":
                parts = raw.split()
                if len(parts) >= 3:
                    try:
                        n = int(parts[2])
                    except ValueError:
                        pass
                    if len(parts) >= 5:
                        try:
                            top = int(parts[4])
                        except ValueError:
                            pass
                continue
            parts = raw.split()
            try:
                w = int(parts[0])
            except (ValueError, IndexError):
                continue
            lits = []
            for t in parts[1:]:
                try:
                    lit = int(t)
                except ValueError:
                    continue
                if lit == 0:
                    break
                lits.append(lit)
            if top is not None and w >= top:
                hard.append(lits)
            else:
                soft.append((w, lits))
    if n < 0:
        raise ValueError("no p wcnf header")
    if top is None:
        raise ValueError("no top in header (cannot tell hard from soft)")
    return n, hard, soft


def parse_output(out_path):
    """Return (status, cost, bits): the LAST s/o/v line values, each None if
    absent. 'c' lines and anything else are ignored."""
    status = None
    cost = None
    bits = None
    with open(out_path, "rb") as f:
        for raw in f:
            if not raw:
                continue
            c0 = raw[:1]
            if c0 == b"s":
                status = raw[1:].strip().decode("ascii", "replace")
            elif c0 == b"o":
                parts = raw.split()
                if len(parts) >= 2:
                    try:
                        cost = int(parts[1])
                    except ValueError:
                        pass
            elif c0 == b"v":
                parts = raw.split()
                if len(parts) >= 2:
                    bits = b"".join(parts[1:]).decode("ascii", "replace")
    return status, cost, bits


def check_answer(instance_path, out_path):
    """Return (cost, None) iff the output carries a valid answer; the cost is
    recomputed from the assignment. Otherwise (None, reason)."""
    try:
        n, hard, soft = load_instance(instance_path)
    except (ValueError, OSError) as e:
        return None, f"could not load instance: {e}"
    try:
        status, declared, bits = parse_output(out_path)
    except OSError as e:
        return None, f"could not read solver output: {e}"
    if declared is None:
        return None, "no o (cost) line in output"
    if bits is None:
        return None, "no v (assignment) line in output"
    if status is not None and status == "UNSATISFIABLE":
        return None, "claims UNSATISFIABLE, but the hard clauses are satisfiable"
    if len(bits) != n:
        return None, f"v-line length {len(bits)} != nvars {n}"
    val = bytearray(n + 1)
    for i, ch in enumerate(bits):
        if ch == "1":
            val[i + 1] = 1
        elif ch != "0":
            return None, f"v-line contains non-binary char {ch!r}"
    for lits in hard:
        sat = False
        for lit in lits:
            v = lit if lit > 0 else -lit
            if v <= n and ((val[v] == 1) == (lit > 0)):
                sat = True
                break
        if not sat:
            return None, f"hard clause falsified ({len(lits)} lits)"
    cost = 0
    for w, lits in soft:
        sat = False
        for lit in lits:
            v = lit if lit > 0 else -lit
            if v <= n and ((val[v] == 1) == (lit > 0)):
                sat = True
                break
        if not sat:
            cost += w
    if cost != declared:
        return None, (f"declared cost {declared} != recomputed cost {cost} "
                      f"of the printed assignment")
    return cost, None


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
    pinned to an allowed core via taskset. Returns (seconds_used, None) on
    success, else (seconds_used, reason)."""
    t0 = time.time()
    allowed = _allowed_cpus()
    if core is None or allowed is None:
        cmd = [solver]
    else:
        cmd = ["taskset", "-c", str(allowed[core % len(allowed)]), solver]
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


def evaluate(solver, instances_dir, reference, work_dir, per_instance_seconds,
             jobs):
    """Run + verify every instance in the reference, in parallel: each
    instance gets its own wall-clock limit and its own core."""
    ncores = _cpu_quota()
    jobs = max(1, min(jobs, ncores))

    def one(name, core):
        inst_path = os.path.join(instances_dir, name)
        out_path = os.path.join(work_dir, name + ".out")
        B, K = reference[name]["B"], reference[name]["K"]
        rec = {"B": B, "K": K, "A": None, "raw": None, "score": 0.0,
               "status": "ok"}
        if not os.path.exists(inst_path):
            rec["status"] = "instance file missing on judge side"
            return name, rec
        secs, err = run_solver(solver, inst_path, out_path,
                               per_instance_seconds, core)
        rec["seconds"] = round(secs, 2)
        if err is None:
            cost, cerr = check_answer(inst_path, out_path)
            if cerr is None:
                rec["A"] = cost
            else:
                rec["status"] = f"invalid answer ({cerr})"
        else:
            rec["status"] = err
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
    """Mean of clipped scores over participating (B > K) instances."""
    part = [n for n in results
            if reference[n]["B"] > reference[n]["K"]]
    total = sum(results[n]["score"] for n in part) / len(part) if part else 0.0
    raws = [results[n]["raw"] for n in part if results[n]["raw"] is not None]
    return {
        "reward": total,
        "participating": len(part),
        "excluded_no_signal": sorted(n for n in results if n not in part),
        "mean_raw_unclipped": (sum(raws) / len(raws)) if raws else None,
        "beat_known_best": sorted(
            n for n in part
            if results[n]["A"] is not None
            and results[n]["A"] < reference[n]["K"]
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
    work_dir = os.path.join("/tmp", f"maxsat-score-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)

    solver, err = build_solver(app_dir)
    if err:
        return {"reward": 0.0, "build_error": err, "per_instance": {}}
    results = evaluate(solver, instances_dir, reference, work_dir,
                       PER_INSTANCE_SECONDS, JUDGE_JOBS)
    out = summarize(results, reference)
    out["per_instance_seconds"] = PER_INSTANCE_SECONDS
    out["judge_jobs"] = max(1, min(JUDGE_JOBS, _cpu_quota()))
    out["per_instance"] = results
    return out


if __name__ == "__main__":
    print(json.dumps(main(sys.argv), indent=1, sort_keys=True))
