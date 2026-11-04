"""Local public-instance runner for the sygus-comp task.

This is a convenience runner for the agent's dev box only. It rebuilds via
/app/build.sh, runs each public practice instance with a per-instance
wall-clock budget (3600 s, the SyGuS-Comp budget, handed to the solver via
env SYGUS_INSTANCE_SECONDS; the process group is hard-killed at the
limit), machine-checks the candidate solution in two steps (grammar
derivability when the synth-fun has a grammar, then negated-spec unsat via
a PRISTINE cvc5, never the agent's build), and prints one line per
instance: name, solved flag (1 = verifiably solved, 0 = not), validity
status, seconds used. Nothing is aggregated.

This dev box is NOT the judging sandbox: core count, memory, and timing
behavior differ here. Treat the results of submit.sh (public practice
channel) as authoritative.
"""

import json
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sygus_check

BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
# Per-instance wall-clock budget (SyGuS-Comp official: 3600 s).
PER_INSTANCE_SECONDS = float(os.environ.get("PER_INSTANCE_SECONDS", "3600"))
# Per-instance timeout for the machine check's SMT query (milliseconds).
VERIFY_TIMEOUT_MS = int(os.environ.get("SYGUS_VERIFY_TIMEOUT_MS", "90000"))


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


def run_solver(solver, instance_path, out_path, timeout, core=None):
    """Run `solver instance > out_path` with a wall-clock timeout, optionally
    pinned to a core via taskset. The solver learns the per-instance budget
    via env SYGUS_INSTANCE_SECONDS. Returns (seconds, None) on success,
    (seconds, reason) otherwise."""
    env = dict(os.environ)
    env["SYGUS_INSTANCE_SECONDS"] = f"{timeout:.3f}"
    t0 = time.time()
    cmd = [solver] if core is None else ["taskset", "-c", str(core), solver]
    with open(out_path, "w") as fout:
        p = subprocess.Popen(
            cmd + [instance_path],
            stdout=fout, env=env,
            stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
            return time.time() - t0, f"timeout after {round(timeout, 1)}s"
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
        reference = json.load(f)
    names = sorted(reference["instances"])
    work_dir = os.path.join("/tmp", f"sygus-run-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)

    solver, err = build_solver(app_dir)
    if err:
        print(f"BUILD FAILED: {err}", file=sys.stderr)
        return 1

    jobs = max(1, min(JUDGE_JOBS, _cpu_quota()))
    cvc5_check = sygus_check.CVC5_CHECK

    def one(name, core):
        inst_path = os.path.join(instances_dir, name)
        rec = {"A": 0, "status": "ok", "seconds": 0.0}
        if not os.path.exists(inst_path):
            rec["status"] = "instance file missing"
            return name, rec
        out_path = os.path.join(work_dir, name + ".out")
        seconds, rerr = run_solver(solver, inst_path, out_path,
                                   PER_INSTANCE_SECONDS, core)
        rec["seconds"] = round(seconds, 2)
        if rerr is not None:
            rec["status"] = rerr
        else:
            try:
                with open(out_path, errors="replace") as f:
                    output = f.read()
            except OSError as e:
                rec["status"] = f"could not read solver output: {e}"
                return name, rec
            try:
                ok, reason = sygus_check.check_answer(
                    inst_path, output, cvc5=cvc5_check,
                    timeout_ms=VERIFY_TIMEOUT_MS)
            except Exception as e:
                # Fail closed: a checker crash rejects this instance only.
                ok, reason = False, f"checker error: {type(e).__name__}: {e}"
            if ok:
                rec["A"] = 1
            else:
                rec["status"] = f"invalid solution ({reason})"
        return name, rec

    with ThreadPoolExecutor(max_workers=jobs) as ex:
        futures = [ex.submit(one, name, i % jobs)
                   for i, name in enumerate(names)]
        for fut in futures:
            name, rec = fut.result()
            print(f"{name}\tsolved={rec['A']}\t{rec['status']}\t"
                  f"{rec['seconds']}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
