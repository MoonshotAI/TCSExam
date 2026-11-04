"""Local public-instance runner for the oscm-pace2024 task.

This is a convenience runner for the agent's dev box only. It rebuilds via
/app/build.sh, runs each public instance with a per-instance wall-clock
limit (1800 s, the official PACE 2024 exact-track limit), validates the
printed ordering (a full permutation of the free layer) and counts its
crossings with the official PACE 2024 verifier code (pace2024-verifier pip
package, segtree counting method), and prints one line per instance:
name, A (number of crossings), validity status, seconds used. Nothing is
aggregated. Reference entries flagged "exclude": true are skipped;
currently every public instance has a reference entry, so all 100 run.

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


def main(argv):
    if len(argv) != 4:
        print(f"usage: {argv[0]} APP_DIR INSTANCES_DIR REFERENCE_JSON",
              file=sys.stderr)
        return 2
    app_dir, instances_dir, ref_path = argv[1], argv[2], argv[3]
    # The public practice set is defined by the reference file (the same
    # set submit.sh's public channel judges); entries flagged "exclude"
    # (no official published solution) are documentation only: never run.
    with open(ref_path) as f:
        reference = json.load(f)["instances"]
    excluded = sorted(n for n, r in reference.items() if r.get("exclude"))
    names = sorted(n for n, r in reference.items() if not r.get("exclude"))
    for n in excluded:
        print(f"{n}\tskipped (excluded in reference)", flush=True)
    work_dir = os.path.join("/tmp", f"oscm-run-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)

    solver, err = build_solver(app_dir)
    if err:
        print(f"BUILD FAILED: {err}", file=sys.stderr)
        return 1

    jobs = max(1, min(JUDGE_JOBS, os.cpu_count() or 1))

    def one(name, core):
        inst_path = os.path.join(instances_dir, name)
        out_path = os.path.join(work_dir, name + ".out")
        rec = {"A": None, "status": "ok"}
        if not os.path.exists(inst_path):
            rec["status"] = "instance file missing"
            return name, rec
        secs, rerr = run_solver(solver, inst_path, out_path,
                                PER_INSTANCE_SECONDS, core)
        rec["seconds"] = round(secs, 2)
        if rerr is None:
            crossings, verr = _count_crossings(inst_path, out_path)
            if verr is None:
                rec["A"] = crossings
            else:
                rec["status"] = verr
        else:
            rec["status"] = rerr
        return name, rec

    with ThreadPoolExecutor(max_workers=jobs) as ex:
        futures = [ex.submit(one, name, i % jobs)
                   for i, name in enumerate(names)]
        for fut in futures:
            name, rec = fut.result()
            a = rec["A"] if rec["A"] is not None else "-"
            print(f"{name}\tA={a}\t{rec['status']}\t"
                  f"{rec.get('seconds', 0.0)}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
