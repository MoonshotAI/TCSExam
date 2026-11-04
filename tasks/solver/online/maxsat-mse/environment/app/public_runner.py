"""Local public-instance runner for the maxsat-mse task.

This is a convenience runner for the agent's dev box only. It rebuilds via
/app/build.sh, runs the public practice instances (those listed in
/app/public_reference.json) with a per-instance
wall-clock limit (the process group is hard-killed at the limit), parses
the output (last "o" cost line, last "v" bitstring assignment line, last
"s" status line; "c" comment lines are ignored), validates the answer with
check_answer() below (every hard clause satisfied; the cost recomputed
from the assignment equals the declared "o" value), and prints one line
per instance: name, A (validated cost), validity status, seconds used.
Nothing is aggregated.

This dev box is NOT the judging sandbox: core count, memory, and timing
behavior differ here. Treat the results of submit.sh (public practice
channel) as authoritative.

Instance format (fixed): the classic WCNF format — "c" comment lines, one
header "p wcnf <n> <m> <top>", then m clause lines "<w> <lit> ... 0"
(1-based signed literals, 0-terminated). Clauses with weight w >= top are
hard, the others soft with weight w.

Output format (fixed): lines starting with "c" are comments; one status
line "s OPTIMUM FOUND" / "s SATISFIABLE" / "s UNKNOWN"; at least one cost
line "o <integer>"; and exactly one assignment line "v <bitstring>" where
the bitstring has exactly n characters from {0,1}, the i-th character
giving the value of variable i. When several o/v lines are printed, the
LAST ones count. The declared cost must equal the cost of the printed
assignment.

Time budget: each instance gets its own wall-clock limit
(PER_INSTANCE_SECONDS). The solver is expected to self-limit below that;
the runner kills the process group at the limit. Instances are run in
parallel (JUDGE_JOBS workers, each pinned to a core with taskset); the
solver
only ever sees one instance at a time. Answer checking does not consume
the limit.
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


def main(argv):
    if len(argv) != 4:
        print(f"usage: {argv[0]} APP_DIR INSTANCES_DIR REFERENCE_JSON",
              file=sys.stderr)
        return 2
    app_dir, instances_dir, ref_path = argv[1], argv[2], argv[3]
    # The public practice set is defined by the reference file's keys
    # (the same set submit.sh's public channel judges).
    with open(ref_path) as f:
        names = sorted(json.load(f)["instances"])
    work_dir = os.path.join("/tmp", f"maxsat-run-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)

    solver, err = build_solver(app_dir)
    if err:
        print(f"BUILD FAILED: {err}", file=sys.stderr)
        return 1

    jobs = max(1, min(JUDGE_JOBS, _cpu_quota()))

    def one(name, core):
        inst_path = os.path.join(instances_dir, name)
        out_path = os.path.join(work_dir, name + ".out")
        rec = {"A": None, "status": "ok"}
        secs, rerr = run_solver(solver, inst_path, out_path,
                                PER_INSTANCE_SECONDS, core)
        rec["seconds"] = round(secs, 2)
        if rerr is None:
            cost, cerr = check_answer(inst_path, out_path)
            if cerr is None:
                rec["A"] = cost
            else:
                rec["status"] = f"invalid answer ({cerr})"
        else:
            rec["status"] = rerr
        return name, rec

    with ThreadPoolExecutor(max_workers=jobs) as ex:
        futures = [ex.submit(one, name, i % jobs)
                   for i, name in enumerate(names)]
        for fut in futures:
            name, rec = fut.result()
            a = rec["A"] if rec["A"] is not None else "-"
            print(f"{name}\tA={a}\t{rec['status']}\t{rec['seconds']}s",
                  flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
