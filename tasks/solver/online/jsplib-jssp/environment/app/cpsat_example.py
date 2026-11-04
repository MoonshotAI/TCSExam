#!/usr/bin/env python3
"""cpsat_example.py — a ready-to-use CP-SAT solver for this task.

This is the "textbook technique" anchor of the scoring ladder (the L
anchor): the standard interval + no_overlap CP-SAT model with default
parameters, wrapped in the task's anytime output protocol. Submitted
as-is it scores about 0.3 — by design. Beating it means making the
engine work better inside the same 600 s / 1-core budget: model
variants, search parameters, warm-starting from a constructive
heuristic, decomposition, hybrid local search, ...

Run it exactly like the compiled baseline:
    python3 /app/cpsat_example.py INSTANCE_FILE OUTPUT_FILE LIMIT_SECONDS

It writes the incumbent schedule (start-time matrix) to OUTPUT_FILE
atomically on every improvement and exits slightly before the limit.
To use it as your submission, make /app/build.sh produce a /app/solver
wrapper that execs this script (an executable shell script counts).
"""
import os
import sys
import tempfile

from ortools.sat.python import cp_model


def load_instance(path):
    with open(path) as f:
        rows = [l.split() for l in f if l.strip()]
    n, m = int(rows[0][0]), int(rows[0][1])
    ops = []
    for row in rows[1:]:
        ops.append([(int(row[2 * k]), int(row[2 * k + 1])) for k in range(m)])
    return n, m, ops


def main(argv):
    inst, out_path, limit = argv[1], argv[2], float(argv[3])
    n, m, ops = load_instance(inst)
    horizon = sum(d for route in ops for _, d in route)

    model = cp_model.CpModel()
    starts, ends = {}, {}
    per_machine = {}
    for j in range(n):
        for k in range(m):
            mach, dur = ops[j][k]
            s = model.new_int_var(0, horizon, f"s_{j}_{k}")
            e = model.new_int_var(0, horizon, f"e_{j}_{k}")
            iv = model.new_interval_var(s, dur, e, f"i_{j}_{k}")
            starts[(j, k)], ends[(j, k)] = s, e
            per_machine.setdefault(mach, []).append(iv)
            if k > 0:
                model.add(s >= ends[(j, k - 1)])
    for ivs in per_machine.values():
        model.add_no_overlap(ivs)
    makespan = model.new_int_var(0, horizon, "makespan")
    model.add_max_equality(makespan, [ends[(j, m - 1)] for j in range(n)])
    model.minimize(makespan)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = limit * 0.85
    solver.parameters.num_workers = 1  # the judge pins every instance to one core

    def atomic_write(start_values):
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(out_path) or ".")
        with os.fdopen(fd, "w") as f:
            for j in range(n):
                f.write(" ".join(str(start_values[(j, k)])
                                 for k in range(m)) + "\n")
        os.replace(tmp, out_path)

    class AnytimeCallback(cp_model.CpSolverSolutionCallback):
        def on_solution_callback(self):
            atomic_write({k: self.value(v) for k, v in starts.items()})

    cb = AnytimeCallback()
    status = solver.solve(model, cb)
    if status in (cp_model.FEASIBLE, cp_model.OPTIMAL) and not os.path.exists(out_path):
        atomic_write({k: solver.value(v) for k, v in starts.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
