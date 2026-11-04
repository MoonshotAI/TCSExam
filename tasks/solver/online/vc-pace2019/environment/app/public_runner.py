"""Local public-instance runner for the vc-pace2019 (exact vertex cover)
task.

This is a convenience runner for the agent's dev box only. Protocol
(per-instance limit, the official PACE 2019 exact-track form): copy /app
-> `bash build.sh` (must produce ./solver) -> for each instance, invoke
    solver < instance.gr > instance.vc
with the per-instance wall-clock budget in env VC_TIME_LIMIT (1800 s by
default, the official PACE 2019 exact-track limit). When the budget is
exhausted the runner SIGTERMs the process group; after GRACE_TIMEOUT,
SIGKILL. Calls run in parallel (JUDGE_JOBS workers, each pinned to a
core). The printed .vc file (if any) is then validated with the official
PACE 2019 checker (vc_validate: stdout verdict ends with "|SUCCESS" iff
the cover is valid; it also enforces that the declared size k in the
`s vc n k` header equals the number of vertex lines). It prints one line
per instance: name, A (cover size), validity status, seconds used.
Nothing is aggregated.

This dev box is NOT the judging sandbox: core count, memory, and timing
behavior differ here. Treat the results of submit.sh (public practice
channel) as authoritative.
"""

import json
import os
import shutil
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

VERIFY_BIN = os.environ.get("VERIFY_BIN", "/usr/local/bin/vc_validate")
BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
# Official PACE 2019 exact-track per-instance wall-clock limit (seconds).
PER_INSTANCE_BUDGET = int(os.environ.get("PER_INSTANCE_BUDGET", "1800"))
GRACE_TIMEOUT = int(os.environ.get("GRACE_TIMEOUT", "10"))  # limit -> TERM -> +grace -> KILL
JUDGE_JOBS = int(os.environ.get("JUDGE_JOBS", "0")) or max(1, (os.cpu_count() or 1))
VERIFY_TIMEOUT = 600


def build_solver(app_dir, work_dir):
    """Copy app_dir into a scratch dir, run `bash build.sh`, expect ./solver."""
    build_dir = os.path.join(work_dir, "build")
    try:
        shutil.copytree(app_dir, build_dir)
    except OSError as e:
        return None, f"failed to copy /app: {e}"
    script = os.path.join(build_dir, "build.sh")
    if not os.path.exists(script):
        return None, "no build.sh found in /app"
    try:
        p = subprocess.run(["bash", "build.sh"], cwd=build_dir,
                           stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=BUILD_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None, f"build.sh timed out after {BUILD_TIMEOUT}s"
    solver = os.path.join(build_dir, "solver")
    if not (os.path.isfile(solver) and os.access(solver, os.X_OK)):
        tail = ((p.stdout or "") + (p.stderr or ""))[-3000:]
        return None, (f"build.sh finished but did not produce an executable "
                      f"solver\n{tail}")
    return solver, None


def run_instance(solver, inst_path, out_path, budget, core=None):
    """Run `solver < inst_path > out_path` with VC_TIME_LIMIT set and a
    hard wall-clock budget (SIGTERM at budget, SIGKILL after grace),
    optionally pinned to a core via taskset.

    Returns (elapsed_seconds, note) where note is None on clean exit.
    """
    env = dict(os.environ)
    env["VC_TIME_LIMIT"] = str(budget)
    cmd = [solver] if core is None else ["taskset", "-c", str(core), solver]
    t0 = time.time()
    with open(inst_path) as fin, open(out_path, "w") as fout:
        p = subprocess.Popen(cmd, stdin=fin, stdout=fout, env=env,
                             stderr=subprocess.DEVNULL,
                             start_new_session=True)
        note = None
        try:
            p.wait(timeout=budget)
        except subprocess.TimeoutExpired:
            note = f"time limit exhausted ({budget}s); SIGTERM sent"
            try:
                os.killpg(p.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                p.wait(timeout=GRACE_TIMEOUT)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
                p.wait()
                note += "; SIGKILL needed"
    elapsed = round(time.time() - t0, 2)
    if note is None and p.returncode != 0:
        note = f"solver exited with code {p.returncode}"
    return elapsed, note


def verify_vc(inst_path, vc_path):
    """Official checker: stdout verdict ends with '|SUCCESS' iff valid.
    Returns (size, None) with the declared cover size k on success, else
    (None, reason)."""
    if not os.path.exists(vc_path) or os.path.getsize(vc_path) == 0:
        return None, "no output produced (limit exhausted or skipped)"
    try:
        p = subprocess.run(
            [VERIFY_BIN, inst_path, vc_path],
            capture_output=True, text=True, timeout=VERIFY_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return None, "verifier timed out"
    if not (p.stdout or "").rstrip().endswith("|SUCCESS"):
        msg = ((p.stdout or "") + (p.stderr or "")).strip()
        return None, f"invalid vertex cover ({msg[-300:]})"
    # The checker has enforced: header `s vc n k` present exactly once,
    # k == number of vertex lines, all vertices in range, all edges covered.
    try:
        with open(vc_path, errors="replace") as f:
            for line in f:
                tok = line.split()
                if tok and tok[0] == "s":
                    return int(tok[3]), None
        return None, "no solution line (s vc ...) found in output"
    except (OSError, ValueError, IndexError) as e:
        return None, f"unparseable output ({e})"


def main(argv):
    if len(argv) != 4:
        print(f"usage: {argv[0]} APP_DIR INSTANCES_DIR REFERENCE_JSON",
              file=sys.stderr)
        return 2
    app_dir, instances_dir, ref_path = argv[1], argv[2], argv[3]
    # The public practice set is defined by the reference file (the same
    # set submit.sh's public channel judges); every key runs and gets an A.
    with open(ref_path) as f:
        reference = json.load(f)["instances"]
    names = sorted(reference)
    work_dir = os.path.join("/tmp", f"vc-run-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)

    solver, err = build_solver(app_dir, work_dir)
    if err:
        print(f"BUILD FAILED: {err}", file=sys.stderr)
        return 1

    jobs = max(1, min(JUDGE_JOBS, os.cpu_count() or 1))

    def one(name, core):
        inst_path = os.path.join(instances_dir, name + ".gr")
        K = reference[name]["K"]
        rec = {"A": None, "status": "ok"}
        if not os.path.exists(inst_path):
            rec["status"] = "instance file missing"
            return name, rec
        out_path = os.path.join(work_dir, name + ".vc")
        elapsed, note = run_instance(solver, inst_path, out_path,
                                     PER_INSTANCE_BUDGET, core)
        rec["seconds"] = elapsed
        if note:
            rec["status"] = note
        size, verr = verify_vc(inst_path, out_path)
        if verr is not None:
            if rec["status"] == "ok":
                rec["status"] = verr
            return name, rec
        rec["A"] = size
        if size == K:
            rec["status"] = "ok (solved: valid cover of size K)"
        elif size < K:
            # 260924 ruling, same as the judge side: a valid cover below
            # the reference K counts as SOLVED and is flagged
            # records_broken (registered for the K-table re-check).
            rec["status"] = (
                f"ok (solved: valid cover of size {size} BELOW the "
                f"reference K — records_broken; the K table will be "
                f"re-checked, the solved credit stands)")
        else:
            rec["status"] = "valid but above optimum"
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
