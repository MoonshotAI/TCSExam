#!/usr/bin/env python3
"""Run your solver on the PUBLIC instances and print per-instance results.

Usage:  python3 /app/run_public.py
Rebuilds via /app/build.sh, runs the public instances with a per-instance
wall-clock limit of 1800 s each (the official PACE 2024 exact-track
limit), validates the ordering (a full permutation
of the free layer) and counts crossings with the official PACE 2024
verifier, then prints one line per instance: name, A (crossings),
validity status, seconds used. Nothing is aggregated.

This is a local convenience runner only: this dev box is NOT the judging
sandbox (core count, memory, and timing behavior differ). Treat the
results of submit.sh (public practice channel) as authoritative.
"""
import sys

sys.path.insert(0, "/opt/ocm")
import public_runner

sys.exit(public_runner.main(["run_public.py", "/app", "/app/instances",
                             "/app/public_reference.json"]))
