"""Public-instance runner for the celar-rlfap task (agent-side convenience).

This is NOT the judging code. It rebuilds /app via `bash /app/build.sh`,
runs /app/solver on every instance in a directory with a hard per-instance
wall-clock limit (the solver learns it via env CELAR_TIME_LIMIT), validates
the printed f assignment (every value in its allowed set, every hard
equality holds exactly) and recomputes the weighted-violation objective
from scratch. It reports per-instance results only: instance name, the
recomputed objective A, validity, and seconds used. No reference values,
no aggregation, no scoring formula.

The problem (as defined by the shipped MiniZinc model celar.mzn): given
  costs[1..4], categories[1..num_categories] (allowed frequency sets),
  domains[1..n] (category index per variable), hard (x, y, k) triples
  requiring |f[x] - f[y]| = k, and soft (x, y, k, w) tuples penalizing
  costs[w] when |f[x] - f[y]| <= k, choose f[1..n] in the allowed sets
  satisfying every hard constraint while minimizing the total weighted
  violation.
"""
import json
import os
import re
import signal
import subprocess
import sys
import time

BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
PER_INSTANCE_SECONDS = float(os.environ.get("PER_INSTANCE_SECONDS", "1200"))


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


def run_solver(solver, instance_path, out_path, limit_seconds):
    """Run `solver INSTANCE_PATH > out_path` with a hard wall-clock kill at
    limit_seconds. The solver learns the limit via env CELAR_TIME_LIMIT.
    A kill is NOT an error per se (the solver may have printed improving
    solutions); whatever complete blocks exist are checked. Returns
    (seconds, None) or (seconds, reason).

    The kill sweeps the whole descendant tree, not just the solver's
    process group: the MiniZinc CLI re-sessions the FlatZinc solver it
    spawns, so a plain killpg leaves the FlatZinc process orphaned and
    burning CPU into the next instance's slot.
    """
    env = dict(os.environ)
    env["CELAR_TIME_LIMIT"] = f"{limit_seconds:.3f}"
    t0 = time.time()
    with open(out_path, "w") as fout:
        p = subprocess.Popen(
            [solver, instance_path], stdout=fout, env=env,
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
            return time.time() - t0, None  # killed at the limit; check output
    seconds = time.time() - t0
    if p.returncode != 0:
        return seconds, f"solver exited with code {p.returncode}"
    return seconds, None


def main(argv):
    if len(argv) != 3:
        print(f"usage: {argv[0]} APP_DIR INSTANCES_DIR", file=sys.stderr)
        return 2
    app_dir, instances_dir = argv[1], argv[2]
    limit_seconds = float(os.environ.get(
        "PER_INSTANCE_SECONDS", str(PER_INSTANCE_SECONDS)))
    names = sorted(f for f in os.listdir(instances_dir)
                   if f.endswith(".dzn"))
    solver, err = build_solver(app_dir)
    if err:
        print(json.dumps({"build_error": err}, indent=1))
        return 1
    work_dir = os.path.join("/tmp", f"celar-run-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)
    results = {}
    for name in names:
        inst_path = os.path.join(instances_dir, name)
        out_path = os.path.join(work_dir, name + ".out")
        rec = {"A": None, "status": "ok", "seconds": 0.0}
        seconds, err = run_solver(solver, inst_path, out_path, limit_seconds)
        rec["seconds"] = round(seconds, 2)
        if err is None:
            obj, cerr = check_solution(inst_path, out_path)
            if cerr is None:
                rec["A"] = obj
            else:
                rec["status"] = f"invalid solution ({cerr})"
        else:
            rec["status"] = err
        results[name] = rec
        print(f"{name}: A={rec['A']} {rec['status']} "
              f"({rec['seconds']}s)", flush=True)
    print(json.dumps({"per_instance": results,
                      "per_instance_seconds": limit_seconds},
                     indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
