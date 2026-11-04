"""Shared scoring logic for the celar-rlfap task.

Used by BOTH sides so the formula and the validity check cannot diverge:
  - agent side:  /app/score_public.py   (public instances, public reference)
  - judge side:  /tests/checker.py      (hidden instances, hidden reference)

Pipeline: run `bash /app/build.sh` (must produce /app/solver) -> for each
instance, run `/app/solver INSTANCE_PATH` with a hard per-instance wall-clock
limit (the solver learns it via env CELAR_TIME_LIMIT, in seconds) -> take the
LAST complete `f = [...];` block on stdout -> validate it with
check_solution() below and recompute the objective from scratch ->
A = recomputed objective -> per-instance gap ratio r = (B - A) / (B - K), unclipped -> arithmetic mean. Instances with B == K carry no signal and are
excluded.

Time budget (aligned with the official MiniZinc Challenge
rule): each instance gets its own wall-clock limit of PER_INSTANCE_SECONDS
(1200 s — the MiniZinc Challenge per-instance budget). Instances are
evaluated in parallel (JUDGE_JOBS workers, each pinned to a core with
taskset); the solver only ever sees one instance at a time. Validity
checking does not consume the limit.

The problem (as defined by the shipped MiniZinc model celar.mzn, the
MiniZinc Challenge reference model): given
  costs[1..4]                     soft-constraint violation costs,
  categories[1..num_categories]   allowed frequency sets,
  domains[1..n]                   category index per variable,
  hard (x, y, k) triples          require |f[x] - f[y]| = k,
  soft (x, y, k, w) tuples        penalize costs[w] when |f[x] - f[y]| <= k,
choose f[1..n] with f[j] in categories[domains[j]] satisfying every hard
constraint and minimizing
      objective = sum over soft j of costs[w[j]] * (|f[x]-f[y]| <= k[j])
check_solution() verifies exactly this and recomputes the objective — the
same code runs on both sides, and nothing the solver prints beyond the f
array is trusted (self-declared objective values are ignored).

The raw unclipped values are reported per instance; raw > 1 means the
submission beat the reference value K (best known value, see
tests/SAMPLING.md). That should be rare; it is surfaced for investigation,
never silently dropped;
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
import re
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
# Hard per-instance wall-clock limit in seconds (no shared pool: every
# instance gets the same limit, MiniZinc-Challenge style; aligned with the official rules
# to the official MiniZinc Challenge budget of 1200 s per instance).
PER_INSTANCE_SECONDS = float(os.environ.get("PER_INSTANCE_SECONDS", "1200"))


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


def load_instance(path):
    """Parse a celar .dzn file. Returns a dict with costs, categories (list
    of lists of ints), domains (1-based category index per var), hard triples
    and soft tuples. Pure integer data, no floats anywhere."""
    with open(path, errors="replace") as f:
        text = f.read()

    def arr(name):
        m = re.search(name + r"\s*=\s*\[(.*?)\]\s*;", text, re.S)
        if not m:
            raise ValueError(f"could not parse {name} from dzn")
        return [int(x) for x in re.findall(r"-?\d+", m.group(1))]

    def scal(name):
        m = re.search(name + r"\s*=\s*(-?\d+)\s*;", text)
        if not m:
            raise ValueError(f"could not parse {name} from dzn")
        return int(m.group(1))

    cats_m = re.search(r"categories\s*=\s*\[(.*?)\]\s*;", text, re.S)
    if not cats_m:
        raise ValueError("could not parse categories from dzn")
    categories = [[int(x) for x in re.findall(r"-?\d+", s)]
                  for s in re.findall(r"\{(.*?)\}", cats_m.group(1), re.S)]
    inst = {
        "costs": arr("costs"),
        "categories": categories,
        "domains": arr("domains"),
        "hard": list(zip(arr("hardctrx"), arr("hardctry"), arr("hardctrk"))),
        "soft": list(zip(arr("softctrx"), arr("softctry"),
                         arr("softctrk"), arr("softctrw"))),
    }
    n = scal("num_variables")
    if len(inst["domains"]) != n:
        raise ValueError(f"domains has {len(inst['domains'])} entries, "
                         f"expected {n}")
    nh = scal("num_hardconstraints")
    if len(inst["hard"]) != nh:
        raise ValueError(f"hard constraints: {len(inst['hard'])} != {nh}")
    ns = scal("num_softconstraints")
    if len(inst["soft"]) != ns:
        raise ValueError(f"soft constraints: {len(inst['soft'])} != {ns}")
    return inst


def parse_output(text, n):
    """Scan solver stdout for `f = [...];` blocks. Returns the values of the
    LAST complete block, or None if none found."""
    best = None
    for fm in re.finditer(r"\bf\s*=", text):
        lb = text.find("[", fm.end())
        if lb < 0:
            continue
        depth = 0
        vals = None
        for i in range(lb, len(text)):
            c = text[i]
            if c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    body = text[lb + 1:i]
                    vals = [int(x) for x in re.findall(r"-?\d+", body)]
                    end = i + 1
                    break
        if vals is None:
            continue
        if re.match(r"\s*;", text[end:end + 8]):
            best = vals
    return best


def check_solution(instance_path, out_path):
    """Return (objective, None) iff the last complete f block in the output
    is valid; the objective is recomputed from scratch. Otherwise
    (None, reason)."""
    try:
        inst = load_instance(instance_path)
    except (ValueError, OSError) as e:
        return None, f"could not load instance: {e}"
    try:
        with open(out_path, errors="replace") as f:
            text = f.read()
    except OSError as e:
        return None, f"could not read solver output: {e}"
    n = len(inst["domains"])
    f = parse_output(text, n)
    if f is None:
        return None, "no complete f = [...]; solution block found on stdout"
    if len(f) != n:
        return None, f"f has {len(f)} entries, expected {n}"
    cats = inst["categories"]
    for j in range(n):
        cat = cats[inst["domains"][j] - 1]
        if f[j] not in cat:
            return None, (f"variable {j+1}: value {f[j]} not in its allowed "
                          f"domain {cat}")
    for (x, y, k) in inst["hard"]:
        if abs(f[x - 1] - f[y - 1]) != k:
            return None, (f"hard constraint |f[{x}]-f[{y}]|={k} violated "
                          f"(|{f[x-1]}-{f[y-1]}|={abs(f[x-1]-f[y-1])})")
    costs = inst["costs"]
    objective = 0
    for (x, y, k, w) in inst["soft"]:
        if abs(f[x - 1] - f[y - 1]) <= k:
            objective += costs[w - 1]
    return objective, None


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


def _descendants(root_pid):
    """All current descendant PIDs of root_pid (walk /proc ppid links)."""
    children = {}
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        try:
            with open(f"/proc/{name}/stat", errors="replace") as f:
                tail = f.read().rsplit(")", 1)[1].split()
            children[int(name)] = int(tail[1])
        except (OSError, IndexError, ValueError):
            continue
    found = []
    frontier = [root_pid]
    seen = {root_pid}
    while frontier:
        cur = frontier.pop()
        for pid, ppid in children.items():
            if ppid == cur and pid not in seen:
                seen.add(pid)
                found.append(pid)
                frontier.append(pid)
    return found


def run_solver(solver, instance_path, out_path, limit_seconds, core=None):
    """Run `solver INSTANCE_PATH > out_path` with a hard wall-clock kill at
    limit_seconds, optionally pinned to a core via taskset. The solver
    learns the limit via env CELAR_TIME_LIMIT.
    A kill is NOT an error per se (the solver may have printed improving
    solutions); whatever complete blocks exist are scored. Returns
    (seconds, None) or (seconds, reason).

    The kill sweeps the whole descendant tree, not just the solver's
    process group: the MiniZinc CLI re-sessions the FlatZinc solver it
    spawns, so a plain killpg leaves the FlatZinc process orphaned and
    burning CPU into the next instance's slot.
    """
    env = dict(os.environ)
    env["CELAR_TIME_LIMIT"] = f"{limit_seconds:.3f}"
    cmd = ([solver, instance_path] if core is None
           else ["taskset", "-c", str(core), solver, instance_path])
    t0 = time.time()
    with open(out_path, "w") as fout:
        p = subprocess.Popen(
            cmd, stdout=fout, env=env,
            stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            p.wait(timeout=limit_seconds)
        except subprocess.TimeoutExpired:
            sweep = _descendants(p.pid)
            os.killpg(p.pid, signal.SIGKILL)
            for pid in sweep:
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
            p.wait()
            return time.time() - t0, None  # killed at the limit; score output
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
            obj, cerr = check_solution(inst_path, out_path)
            if cerr is None:
                rec["A"] = obj
            else:
                rec["status"] = f"invalid solution ({cerr})"
        else:
            rec["status"] = err
        if rec["A"] is not None and B > K:
            rec["raw"] = (B - rec["A"]) / (B - K)
            rec["score"] = min(1.0, max(0.0, rec["raw"]))
        return name, rec

    results = {}
    spent = 0.0
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        futures = [ex.submit(one, name, i % jobs)
                   for i, name in enumerate(sorted(reference))]
        for fut in futures:
            name, rec = fut.result()
            spent += rec["seconds"]
            results[name] = rec
    return results, spent


def summarize(results, reference, limit_seconds, spent):
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
        "per_instance_seconds": limit_seconds,
        "seconds_spent": round(spent, 2),
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
    work_dir = os.path.join("/tmp", f"celar-score-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)
    limit_seconds = float(os.environ.get(
        "PER_INSTANCE_SECONDS", str(PER_INSTANCE_SECONDS)))

    solver, err = build_solver(app_dir)
    if err:
        return {"reward": 0.0, "build_error": err, "per_instance": {}}
    results, spent = evaluate(solver, instances_dir, reference, work_dir,
                              limit_seconds, JUDGE_JOBS)
    out = summarize(results, reference, limit_seconds, spent)
    out["judge_jobs"] = max(1, min(JUDGE_JOBS, _cpu_quota()))
    out["per_instance"] = results
    return out


if __name__ == "__main__":
    print(json.dumps(main(sys.argv), indent=1, sort_keys=True))
