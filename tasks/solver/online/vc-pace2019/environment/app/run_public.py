#!/usr/bin/env python3
"""Run your solver on the PUBLIC instances and print per-instance results.

Usage:  python3 /app/run_public.py
Rebuilds via /app/build.sh, runs your solver once per public instance with
the same per-instance protocol (1800 s each, SIGTERM/SIGKILL, vc_validate),
and prints one line per instance: name, A (cover size), validity status,
seconds used. Nothing is aggregated.

This is a local convenience runner only: this dev box is NOT the judging
sandbox (core count, memory, and timing behavior differ). Treat the
results of submit.sh (public practice channel) as authoritative.
"""
import sys

sys.path.insert(0, "/opt/vc")
import public_runner

sys.exit(public_runner.main(["run_public.py", "/app", "/app/instances",
                             "/app/public_reference.json"]))
