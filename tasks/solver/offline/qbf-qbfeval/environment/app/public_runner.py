"""Local public-instance runner for the qbf-qbfeval task.

This is a convenience runner for the agent's dev box only. It rebuilds via
/app/build.sh, runs the public instances with a per-instance wall-clock
budget (900 s, the QBFEVAL'20 budget, handed to the solver via env
QBF_INSTANCE_SECONDS; the proof destination goes in env QBF_PROOF_PATH),
checks each answer with the qrp2rup + drat-trim certificate chain
(verify_qbf.check — both TRUE and FALSE claims need a certificate that
passes; the official label is never consulted), and prints one line per
instance: name, solved flag (1 = verifiably solved, 0 = not), validity
status, seconds used. Nothing is aggregated.

This dev box is NOT the judging sandbox: core count, memory, and timing
behavior differ here. Treat timings as estimates and keep margin below the per-instance limit.

Instances may be stored as plain `<name>.qdimacs` or compressed
`<name>.qdimacs.xz`; the latter are decompressed to the work dir
just-in-time (and removed right after).

QBF_ONLY (optional env): comma-separated instance names — restrict the run
to that subset for quick iterations.
"""

import json
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_qbf

BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
# Per-instance wall-clock budget (QBFEVAL'20 official: 900 s CPU).
PER_INSTANCE_SECONDS = float(os.environ.get("PER_INSTANCE_SECONDS", "900"))


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


def materialize(instances_dir, name, work_dir):
    """Return the path of a decompressed .qdimacs for `name`.

    Accepts `<name>.qdimacs` directly; `<name>.qdimacs.xz` is decompressed
    into the work dir. Returns (path, cleanup_path_or_None, error_or_None).
    """
    plain = os.path.join(instances_dir, name + ".qdimacs")
    if os.path.exists(plain):
        return plain, None, None
    packed = os.path.join(instances_dir, name + ".qdimacs.xz")
    if os.path.exists(packed):
        dest = os.path.join(work_dir, name + ".qdimacs")
        try:
            with open(packed, "rb") as fin, open(dest, "wb") as fout:
                subprocess.run(["xz", "-dc"], stdin=fin, stdout=fout,
                               check=True)
        except Exception as e:
            return None, None, f"decompress failed: {e}"
        return dest, dest, None
    return None, None, "instance file missing on judge side"


def run_solver(solver, instance_path, out_path, proof_path, budget, core=None):
    """Run solver < instance > out_path with the per-instance wall-clock
    budget, optionally pinned to a core via taskset.

    The solver learns the budget via env QBF_INSTANCE_SECONDS. Whatever the
    verdict, it must write its certificate to the path in env
    QBF_PROOF_PATH. Returns (seconds, None) on success, (seconds, reason)
    otherwise.
    """
    env = dict(os.environ)
    env["QBF_INSTANCE_SECONDS"] = f"{budget:.3f}"
    env["QBF_PROOF_PATH"] = proof_path
    cmd = [solver] if core is None else ["taskset", "-c", str(core), solver]
    t0 = time.time()
    with open(instance_path) as fin, open(out_path, "w") as fout:
        p = subprocess.Popen(
            cmd, stdin=fin, stdout=fout, env=env,
            stderr=subprocess.DEVNULL, start_new_session=True,
        )
        try:
            p.wait(timeout=budget)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
            return time.time() - t0, f"timeout after {round(budget, 1)}s"
    seconds = time.time() - t0
    # QBF evaluation convention: exit 10 = true, 20 = false.
    # Both (and plain 0) mean the solver ran fine; the answer check decides.
    if p.returncode not in (0, 10, 20):
        return seconds, f"solver exited with code {p.returncode}"
    return seconds, None


def main(argv):
    if len(argv) != 4:
        print(f"usage: {argv[0]} APP_DIR INSTANCES_DIR REFERENCE_JSON",
              file=sys.stderr)
        return 2
    app_dir, instances_dir, ref_path = argv[1], argv[2], argv[3]
    # The public practice set is defined by the reference file's keys.
    with open(ref_path) as f:
        reference = json.load(f)["instances"]
    names = sorted(reference)
    only = os.environ.get("QBF_ONLY", "").strip()
    if only:
        wanted = {x.strip() for x in only.split(",") if x.strip()}
        names = [n for n in names if n in wanted]
    work_dir = os.path.join("/tmp", f"qbf-run-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)

    solver, err = build_solver(app_dir)
    if err:
        print(f"BUILD FAILED: {err}", file=sys.stderr)
        return 1

    jobs = max(1, min(JUDGE_JOBS, _cpu_quota()))

    def one(name, core):
        out_path = os.path.join(work_dir, name + ".out")
        proof_path = os.path.join(work_dir, name + ".qrp")
        rec = {"A": 0, "status": "ok", "seconds": 0.0}
        inst_path, cleanup, merr = materialize(instances_dir, name, work_dir)
        if merr is not None:
            rec["status"] = merr
            return name, rec
        seconds, rerr = run_solver(solver, inst_path, out_path, proof_path,
                                   PER_INSTANCE_SECONDS, core)
        rec["seconds"] = round(seconds, 2)
        if rerr is None:
            ok, reason = verify_qbf.check(inst_path, out_path, proof_path)
            if ok:
                rec["A"] = 1
            else:
                rec["status"] = f"answer rejected ({reason})"
        else:
            rec["status"] = rerr
        for path in (cleanup, out_path, proof_path):
            if path:
                try:
                    os.remove(path)
                except OSError:
                    pass
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
