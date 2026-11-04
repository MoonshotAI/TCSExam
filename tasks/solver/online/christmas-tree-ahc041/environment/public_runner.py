"""Public-instance runner for the christmas-tree-ahc041 task (agent-side
convenience).

This is NOT the judging code. It rebuilds /app via `bash /app/build.sh`,
runs /app/solver on every instance in a directory with a hard per-instance
wall-clock limit (the solver learns it via env AHC_INSTANCE_SECONDS; the
legacy name AHC_TIME_POOL is set to the same value), validates the printed
parent array and recomputes the score with a behavior-faithful port of the
official scorer (parent edge must exist in G, no directed cycle, every
depth <= H, score = 1 + sum_v (depth(v)+1)*A[v]). It reports per-instance
results only: instance name, the recomputed raw score A, validity, and
seconds used. No reference values, no aggregation, no scoring formula.
"""
import json
import os
import signal
import subprocess
import sys
import time

BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
PER_INSTANCE_SECONDS = float(os.environ.get("PER_INSTANCE_SECONDS", "2"))

def load_instance(path):
    """AHC041 format: N M H, then N weights A, then M edges (u v),
    then N points (x y). Points are part of the input but unused by the
    scorer; they are parsed for completeness."""
    with open(path) as f:
        vals = f.read().split()
    pos = 0

    def nxt(what):
        nonlocal pos
        if pos >= len(vals):
            raise ValueError(f"unexpected end of instance file at {what}")
        v = int(vals[pos])
        pos += 1
        return v

    N, M, H = nxt("N"), nxt("M"), nxt("H")
    A = [nxt("A") for _ in range(N)]
    edges = [(nxt("u"), nxt("v")) for _ in range(M)]
    points = [(nxt("x"), nxt("y")) for _ in range(N)]
    edge_set = set()
    for u, v in edges:
        edge_set.add((min(u, v), max(u, v)))
    return {"N": N, "M": M, "H": H, "A": A, "edges": edges,
            "points": points, "edge_set": edge_set}

def parse_output(inst, text):
    """Port of the official parse_output. Returns (parents, None) for the
    LAST complete block, or (None, reason). Parents are i32 values in
    -1..N-1; extra trailing tokens forming a partial block are an error,
    exactly like the official Unexpected EOF."""
    N = inst["N"]
    toks = text.split()
    blocks = []
    i = 0
    n = len(toks)
    while i < n:
        if i + N > n:
            return None, ("unexpected end of output: partial block of "
                          f"{n - i} parents, need {N}")
        parents = []
        for j in range(N):
            tok = toks[i + j]
            try:
                p = int(tok)
            except ValueError:
                return None, f"parse error on token: {tok!r}"
            if p < I32_MIN or p > I32_MAX:
                return None, f"parent out of i32 range: {tok!r}"
            if p < -1 or p >= N:
                return None, f"parent {p} out of range -1..{N - 1}"
            parents.append(p)
        blocks.append(parents)
        i += N
    if not blocks:
        return None, "empty output"
    return blocks[-1], None

def compute_score(inst, parents):
    """Port of to_tree_nodes + compute_score_details. Returns
    (score, None) for a valid forest, else (None, reason)."""
    N, H, A = inst["N"], inst["H"], inst["A"]
    edge_set = inst["edge_set"]

    par = [0] * N
    for v in range(N):
        p = parents[v]
        if p == -1:
            par[v] = -1
            continue
        if (min(v, p), max(v, p)) not in edge_set:
            return None, (f"edge ({v}, {p}) is not included in the "
                          "original graph")
        par[v] = p

    # Depths by walking parent chains; a chain that loops before reaching
    # a root or a solved vertex is a directed cycle (official: the vertex
    # is never reached by the DFS from in-degree-0 roots).
    depth = [None] * N
    for v in range(N):
        if depth[v] is not None:
            continue
        chain = []
        on_chain = set()
        x = v
        while x != -1 and depth[x] is None:
            if x in on_chain:
                return None, (f"the connected component that contains "
                              f"vertex {v} is not a rooted tree")
            on_chain.add(x)
            chain.append(x)
            x = par[x]
        # base = depth of the node the chain hangs from; a root's parent
        # is -1 and the root itself sits at depth 0, hence base -1.
        base = -1 if x == -1 else depth[x]
        for k, node in enumerate(reversed(chain)):
            depth[node] = base + k + 1

    for v in range(N):
        if depth[v] is None:
            return None, (f"the connected component that contains vertex "
                          f"{v} is not a rooted tree")
    for v in range(N):
        if depth[v] > H:
            return None, f"vertex {v} is too high (h = {depth[v]})"

    score = 1
    for v in range(N):
        score += A[v] * (depth[v] + 1)
    return score, None

def check_ahc041(instance_path, out_path):
    """Return (score, None) for a valid parent array (score recomputed
    from scratch), else (None, reason) / (0, None) for a well-formed but
    rule-breaking output (official score 0)."""
    try:
        inst = load_instance(instance_path)
    except (ValueError, OSError) as e:
        return None, f"could not load instance: {e}"
    try:
        with open(out_path, errors="replace") as f:
            text = f.read()
    except OSError as e:
        return None, f"could not read solver output: {e}"
    parents, err = parse_output(inst, text)
    if err is not None:
        return None, err
    score, verr = compute_score(inst, parents)
    if verr is not None:
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
    work_dir = os.path.join("/tmp", f"christmas-run-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)
    results = {}
    for name in names:
        inst_path = os.path.join(instances_dir, name)
        out_path = os.path.join(work_dir, name + ".out")
        rec = {"A": None, "status": "ok", "seconds": 0.0}
        seconds, err = run_solver(solver, inst_path, out_path, limit_seconds)
        rec["seconds"] = round(seconds, 2)
        if err is None:
            score, cerr = check_ahc041(inst_path, out_path)
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
