#!/usr/bin/env python3
"""Run your solver on the PUBLIC instances and print per-instance results.

Usage:  python3 /app/run_public.py
Rebuilds via /app/build.sh, runs the public practice set (each instance
with its own wall-clock budget, handed to the solver via env
MR_INSTANCE_SECONDS), validates each produced assignment with the official
ROADEF/EURO 2012 solution checker, and prints one line per instance:
name, A (objective cost), validity status, seconds used. Nothing is
aggregated.

This is the only self-test you have: this dev box is NOT the judging
sandbox (core count, memory, and timing behavior differ). Treat timings as estimates and keep margin below the per-instance limit.
"""
import sys

sys.path.insert(0, "/opt/mr")
import public_runner

sys.exit(public_runner.main(["run_public.py", "/app", "/app/instances",
                             "/app/public_reference.json"]))
