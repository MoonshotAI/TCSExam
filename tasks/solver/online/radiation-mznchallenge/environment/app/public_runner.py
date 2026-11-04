"""Local public-instance runner for the radiation-mznchallenge task.

This is a convenience runner for the agent's dev box only. It rebuilds via
/app/build.sh, runs the public practice instances with a hard per-instance
wall-clock limit (locally 60 s by default for quick iteration — set
PER_INSTANCE_SECONDS to override; the judging sandbox uses its own
per-instance budget), validates the printed N/Q solutions and recomputes
beamtime / shape count / the structural lower bound from scratch, and
prints one line per instance: name, A (shape count), beamtime, lb,
validity status, seconds used. Nothing is aggregated. A solution whose
beam-on time exceeds the structural lower bound is reported without a
value (the same admission rule the judging applies).

This dev box is NOT the judging sandbox: core count, memory, and timing
behavior differ here. Treat the results of submit.sh (public practice
channel) as authoritative.
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
    """Parse a radiation .dzn file. Returns (m, n, intensity) with intensity
    a flat row-major list of m*n nonnegative integers."""
    with open(path, errors="replace") as f:
        text = f.read()
    mm = re.search(r"\bm\s*=\s*(\d+)\s*;", text)
    mn = re.search(r"\bn\s*=\s*(\d+)\s*;", text)
    arr = re.search(r"Intensity\s*=\s*\[\|(.*?)\|\]\s*;", text, re.S)
    if not (mm and mn and arr):
        raise ValueError("could not parse m, n and Intensity from the dzn")
    m, n = int(mm.group(1)), int(mn.group(1))
    vals = [int(x) for x in re.findall(r"-?\d+", arr.group(1))]
    if len(vals) != m * n:
        raise ValueError(f"Intensity has {len(vals)} entries, expected {m*n}")
    if any(v < 0 for v in vals):
        raise ValueError("negative intensity value")
    return m, n, vals


def beamtime_lower_bound(m, n, intensity):
    """Structural lower bound on the total beam-on time: the maximum per-row
    total positive gradient of the intensity matrix,
        LB = max_i ( I[i,1] + sum_{j>=2} max(I[i,j]-I[i,j-1], 0) ).
    Any C1/C2-feasible decomposition has Beamtime >= LB (see module doc).
    """
    lb = 0
    for i in range(m):
        base = i * n
        t = intensity[base]
        for j in range(1, n):
            d = intensity[base + j] - intensity[base + j - 1]
            if d > 0:
                t += d
        if t > lb:
            lb = t
    return lb


def _parse_int_list(text, start):
    """Parse a bracketed integer list starting at text[start] == '['.
    Returns (values, end_index_after_closing_bracket) or (None, None)."""
    if start >= len(text) or text[start] != "[":
        return None, None
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                body = text[start + 1:i]
                vals = [int(x) for x in re.findall(r"-?\d+", body)]
                return vals, i + 1
    return None, None


def parse_output(text, m, n):
    """Scan solver stdout for solution blocks. A block is `N = [<ints>];`
    followed (anywhere later) by `Q = array3d(<dims>, [<ints>]);`. Returns
    (N, Q) of the LAST complete block, or (None, None) if none found."""
    best = (None, None)
    for nm in re.finditer(r"\bN\s*=", text):
        lb = text.find("[", nm.end())
        if lb < 0:
            continue
        vals, end = _parse_int_list(text, lb)
        if vals is None:
            continue
        qm = re.search(r"\bQ\s*=\s*array3d\s*\(", text[end:])
        if not qm:
            continue
        qstart = end + qm.end()
        lb = text.find("[", qstart)
        if lb < 0:
            continue
        qvals, qend = _parse_int_list(text, lb)
        if qvals is None:
            continue
        best = (vals, qvals)
    return best


def check_solution(instance_path, out_path):
    """Return (result, None) iff the last complete N/Q block in the output
    is valid, where result = {"objective", "beamtime", "shapes", "lb"} with
    everything recomputed from scratch ("objective" keeps the legacy
    lexicographic value for reporting; scoring uses "beamtime"/"shapes").
    Otherwise (None, reason).  The admission check (beamtime vs lb) is NOT
    done here — that is the scoring layer's job (evaluate())."""
    try:
        m, n, intensity = load_instance(instance_path)
    except (ValueError, OSError) as e:
        return None, f"could not load instance: {e}"
    try:
        with open(out_path, errors="replace") as f:
            text = f.read()
    except OSError as e:
        return None, f"could not read solver output: {e}"
    bt_max = max(intensity) if intensity else 0
    N, Q = parse_output(text, m, n)
    if N is None:
        return None, "no complete N/Q solution block found on stdout"
    if len(N) != bt_max:
        return None, f"N has {len(N)} entries, expected {bt_max}"
    if len(Q) != m * n * bt_max:
        return None, f"Q has {len(Q)} entries, expected {m*n*bt_max}"
    if any(v < 0 for v in N) or any(v < 0 for v in Q):
        return None, "negative entry in N or Q"
    # (C1) per-cell intensity equation: Intensity[i,j] = sum_b b * Q[i,j,b]
    for i in range(m):
        for j in range(n):
            s = 0
            for b in range(bt_max):
                s += (b + 1) * Q[(i * n + j) * bt_max + b]
            if s != intensity[i * n + j]:
                return None, (f"cell ({i+1},{j+1}): sum b*Q = {s} "
                              f"!= intensity {intensity[i*n+j]}")
    # (C2) per-row aperture count: N[b] >= Q[i,1,b] + sum max(diff, 0)
    for b in range(bt_max):
        for i in range(m):
            need = Q[(i * n + 0) * bt_max + b]
            for j in range(1, n):
                d = (Q[(i * n + j) * bt_max + b]
                     - Q[(i * n + j - 1) * bt_max + b])
                if d > 0:
                    need += d
            if N[b] < need:
                return None, (f"row {i+1}, b={b+1}: N={N[b]} < required "
                              f"apertures {need}")
    beamtime = sum((b + 1) * N[b] for b in range(bt_max))
    shapes = sum(N)
    result = {
        "objective": (m * n + 1) * beamtime + shapes,
        "beamtime": beamtime,
        "shapes": shapes,
        "lb": beamtime_lower_bound(m, n, intensity),
    }
    return result, None


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
    learns the limit via env RADIATION_TIME_LIMIT.
    A kill is NOT an error per se (the solver may have printed improving
    solutions); whatever complete blocks exist are scored. Returns
    (seconds, None) or (seconds, reason).

    The kill sweeps the whole descendant tree, not just the solver's
    process group: the MiniZinc CLI re-sessions the FlatZinc solver it
    spawns, so a plain killpg leaves the FlatZinc process orphaned and
    burning CPU into the next instance's slot.
    """
    env = dict(os.environ)
    env["RADIATION_TIME_LIMIT"] = f"{limit_seconds:.3f}"
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


def main(argv):
    if len(argv) != 4:
        print(f"usage: {argv[0]} APP_DIR INSTANCES_DIR REFERENCE_JSON",
              file=sys.stderr)
        return 2
    app_dir, instances_dir, ref_path = argv[1], argv[2], argv[3]
    # The public practice set is defined by the reference file's keys (the
    # same set submit.sh's public channel judges).
    with open(ref_path) as f:
        reference = json.load(f)["instances"]
    names = sorted(reference)
    limit_seconds = float(os.environ.get(
        "PER_INSTANCE_SECONDS", str(PER_INSTANCE_SECONDS)))
    work_dir = os.path.join("/tmp", f"radiation-run-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)

    solver, err = build_solver(app_dir)
    if err:
        print(f"BUILD FAILED: {err}", file=sys.stderr)
        return 1

    jobs = max(1, min(JUDGE_JOBS, _cpu_quota()))

    def one(name, core):
        inst_path = os.path.join(instances_dir, name)
        out_path = os.path.join(work_dir, name + ".out")
        rec = {"A": None, "status": "ok", "seconds": 0.0}
        if not os.path.exists(inst_path):
            rec["status"] = "instance file missing"
            return name, rec
        seconds, rerr = run_solver(solver, inst_path, out_path,
                                   limit_seconds, core)
        rec["seconds"] = round(seconds, 2)
        if rerr is None:
            res, cerr = check_solution(inst_path, out_path)
            if cerr is not None:
                rec["status"] = f"invalid solution ({cerr})"
            else:
                rec["beamtime"] = res["beamtime"]
                rec["lb"] = res["lb"]
                if res["beamtime"] > res["lb"]:
                    rec["status"] = (f"beam-on time {res['beamtime']} above "
                                     f"structural lower bound {res['lb']}")
                else:
                    rec["A"] = res["shapes"]
        else:
            rec["status"] = rerr
        return name, rec

    with ThreadPoolExecutor(max_workers=jobs) as ex:
        futures = [ex.submit(one, name, i % jobs)
                   for i, name in enumerate(names)]
        for fut in futures:
            name, rec = fut.result()
            a = rec["A"] if rec["A"] is not None else "-"
            bt = rec.get("beamtime", "-")
            lb = rec.get("lb", "-")
            print(f"{name}\tA={a}\tbeamtime={bt}\tlb={lb}\t"
                  f"{rec['status']}\t{rec['seconds']}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
