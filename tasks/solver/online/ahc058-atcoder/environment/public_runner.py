"""Public-instance runner for the ahc058-atcoder task (agent-side
convenience).

This is NOT the judging code. It rebuilds /app via `bash /app/build.sh`,
runs /app/solver on every instance in a directory with a hard per-instance
wall-clock limit (the solver learns it via env AHC_INSTANCE_SECONDS; the
legacy name AHC_TIME_POOL is set to the same value), validates the printed
action sequence and re-simulates it with a bit-faithful port of the
official scorer (signed 64-bit wrap-around, the official action-parsing
and legality rules). It reports per-instance results only: instance name,
the recomputed raw score A, validity, and seconds used. No reference
values, no aggregation, no scoring formula.
"""
import json
import math
import os
import signal
import subprocess
import sys
import time

BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
PER_INSTANCE_SECONDS = float(os.environ.get("PER_INSTANCE_SECONDS", "2"))

MASK64 = (1 << 64) - 1

def i64(x):
    """Signed 64-bit wrap-around, matching Rust i64 arithmetic in release."""
    x &= MASK64
    return x - (1 << 64) if x >= (1 << 63) else x

def load_instance(path):
    """AHC058 format: N L T K, then N values A, then L rows of N costs C."""
    with open(path) as f:
        vals = f.read().split()
    pos = 0

    def nxt():
        nonlocal pos
        if pos >= len(vals):
            raise ValueError("unexpected end of instance file")
        v = int(vals[pos])
        pos += 1
        return v

    N, L, T, K = nxt(), nxt(), nxt(), nxt()
    A = [nxt() for _ in range(N)]
    C = [[nxt() for _ in range(N)] for _ in range(L)]
    return {"N": N, "L": L, "T": T, "K": K, "A": A, "C": C}

def parse_actions(inst, text):
    """Port of the official parse_output. Returns (actions, None) or
    (None, reason). Each action is -1 (nothing) or (level, id)."""
    N, L, T = inst["N"], inst["L"], inst["T"]
    actions = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        toks = line.split()
        try:
            first = int(toks[0])
        except (ValueError, IndexError):
            return None, f"parse error on line: {line!r}"
        if first < -1 or first > L - 1:
            return None, f"level {first} out of range -1..{L - 1}"
        if first == -1:
            actions.append(-1)
        else:
            if len(toks) < 2:
                return None, f"missing id on line: {line!r}"
            try:
                mid = int(toks[1])
            except ValueError:
                return None, f"parse error on line: {line!r}"
            if mid < 0 or mid >= N:
                return None, f"machine id {mid} out of range 0..{N - 1}"
            actions.append((first, mid))
        if len(toks) > (1 if first == -1 else 2):
            return None, f"too many tokens on line: {line!r}"
        if len(actions) == T:
            break
    if len(actions) < T:
        return None, f"not enough actions: expected {T}, got {len(actions)}"
    return actions, None

def simulate(inst, actions):
    """Port of the official compute_score_details. Returns (score, error);
    score is 0 whenever error is non-empty."""
    N, L, T, K = inst["N"], inst["L"], inst["T"], inst["K"]
    A, C = inst["A"], inst["C"]
    B = [[1] * N for _ in range(L)]
    P = [[0] * N for _ in range(L)]
    apples = K
    for t in range(T):
        act = actions[t]
        if act != -1:
            level, mid = act
            cost = i64(C[level][mid] * i64(P[level][mid] + 1))
            if apples < cost:
                return 0, (f"not enough apples at turn {t}: "
                           f"have {apples}, need {cost}")
            apples = i64(apples - cost)
            P[level][mid] += 1
        for level in range(L):
            for mid in range(N):
                if level == 0:
                    apples = i64(apples + i64(i64(A[mid] * B[0][mid])
                                              * P[0][mid]))
                else:
                    B[level - 1][mid] = i64(
                        B[level - 1][mid] + i64(B[level][mid]
                                                * P[level][mid]))
    if apples <= 0:
        return 0, f"non-positive apples at the end: {apples}"
    score = math.floor(100000.0 * math.log2(float(apples)) + 0.5)
    return score, ""

def check_ahc(instance_path, out_path):
    """Return (score, None) for a valid action sequence (score recomputed
    from scratch; 0 if the run went bankrupt), else (None, reason)."""
    try:
        inst = load_instance(instance_path)
    except (ValueError, OSError) as e:
        return None, f"could not load instance: {e}"
    try:
        with open(out_path, errors="replace") as f:
            text = f.read()
    except OSError as e:
        return None, f"could not read solver output: {e}"
    actions, err = parse_actions(inst, text)
    if err is not None:
        return None, err
    score, sim_err = simulate(inst, actions)
    if sim_err:
        # Well-formed but the run breaks the economy rules: official score 0.
        return 0, None
    return score, None

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

def run_solver(solver, instance_path, out_path, limit_seconds, core=None):
    """Run solver < instance > out_path with a hard per-instance wall-clock
    limit, optionally pinned to a core via taskset.

    The solver learns the limit via env AHC_INSTANCE_SECONDS (the legacy
    name AHC_TIME_POOL is set to the same value) and is free to use as
    much of it as it wants on this instance. Returns (seconds, None) on
    success, (seconds, reason) otherwise.
    """
    env = dict(os.environ)
    env["AHC_INSTANCE_SECONDS"] = f"{limit_seconds:.3f}"
    env["AHC_TIME_POOL"] = f"{limit_seconds:.3f}"  # legacy name, same value
    t0 = time.time()
    with open(instance_path) as fin, open(out_path, "w") as fout:
        cmd = [solver]
        if core is not None:
            cmd = ["taskset", "-c", str(core)] + cmd
        p = subprocess.Popen(
            cmd, stdin=fin, stdout=fout, env=env,
            stderr=subprocess.DEVNULL, start_new_session=True,
        )
        try:
            p.wait(timeout=limit_seconds)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
            return time.time() - t0, "per-instance time limit exhausted"
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
                   if f.endswith(".txt"))
    solver, err = build_solver(app_dir)
    if err:
        print(json.dumps({"build_error": err}, indent=1))
        return 1
    work_dir = os.path.join("/tmp", f"ahc058-run-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)
    results = {}
    for name in names:
        inst_path = os.path.join(instances_dir, name)
        out_path = os.path.join(work_dir, name + ".out")
        rec = {"A": None, "status": "ok", "seconds": 0.0}
        seconds, err = run_solver(solver, inst_path, out_path, limit_seconds)
        rec["seconds"] = round(seconds, 2)
        if err is None:
            score, cerr = check_ahc(inst_path, out_path)
            if cerr is None:
                rec["A"] = score
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
