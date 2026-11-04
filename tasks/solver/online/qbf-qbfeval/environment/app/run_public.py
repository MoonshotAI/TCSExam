#!/usr/bin/env python3
"""Run your solver on the PUBLIC instances and print per-instance results.

Usage:  python3 /app/run_public.py
Rebuilds /app/solver via /app/build.sh, runs the public instances
(/opt/qbf-public100) with a per-instance wall-clock budget (900 s, the
QBFEVAL'20 budget), verifies certificates with the qrp2rup + drat-trim
chain, and prints one line per instance: name, solved flag (1/0),
validity status, seconds used. Nothing is aggregated.

This is a local convenience runner only: this dev box is NOT the judging
sandbox (core count, memory, and timing behavior differ). Treat the
results of submit.sh (public practice channel) as authoritative.

To iterate on a few instances only, set QBF_ONLY to a comma-separated
list of instance names, e.g.
    QBF_ONLY=<name1>,<name2> python3 /app/run_public.py
"""
import sys

sys.path.insert(0, "/opt/qbf")
import public_runner

sys.exit(public_runner.main(["run_public.py", "/app", "/opt/qbf-public100",
                             "/app/public_reference.json"]))
