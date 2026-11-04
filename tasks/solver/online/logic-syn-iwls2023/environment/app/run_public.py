#!/usr/bin/env python3
"""Run your solver on the PUBLIC instances and print per-instance results.

Usage:  python3 /app/run_public.py
Rebuilds via /app/build.sh, runs the public practice instances under one
shared total time pool (no per-instance limit; the solver reads the
remaining pool from env LS_TIME_POOL), validates each produced circuit by
exhaustive simulation against the truth table, and prints one line per
instance: name, A (AND-gate count), validity status, seconds used. Nothing
is aggregated.

This is a local convenience runner only: this dev box is NOT the judging
sandbox (core count, memory, and timing behavior differ). Treat the
results of submit.sh (public practice channel) as authoritative.
"""
import sys

sys.path.insert(0, "/opt/ls")
import public_runner

sys.exit(public_runner.main(["run_public.py", "/app", "/app/instances"]))
