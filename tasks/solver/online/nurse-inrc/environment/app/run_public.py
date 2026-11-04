#!/usr/bin/env python3
"""Run your solver on the PUBLIC instances and print per-instance results.

Usage:  python3 /app/run_public.py
Rebuilds via /app/build.sh, runs the public practice instances (each with
its own wall-clock budget, handed to the solver via env
NURSE_INSTANCE_SECONDS), validates the rosters (exact coverage, one shift
per nurse per day) and recomputes their soft-constraint penalties, then
prints one line per instance: name, A (penalty), validity status, seconds
used. Nothing is aggregated.

This is a local convenience runner only: this dev box is NOT the judging
sandbox (core count, memory, and timing behavior differ). Treat the
results of submit.sh (public practice channel) as authoritative.
"""
import sys

sys.path.insert(0, "/opt/nurse")
import public_runner

sys.exit(public_runner.main(["run_public.py", "/app", "/app/instances",
                             "/app/public_reference.json"]))
