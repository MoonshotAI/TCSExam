#!/usr/bin/env python3
"""Run your solver on the PUBLIC practice instances and print per-instance
results.

Usage:  python3 /app/run_public.py
Rebuilds via /app/build.sh, runs your solver once per public instance with
the same per-instance protocol (600 s wall clock each, mc_check
validation), and prints one record per instance: name, A (validated cut
value), validity status, seconds used. Nothing is aggregated.

This is the only self-test you have: this dev box is NOT the judging
sandbox (core count, memory, and timing behavior differ). Treat timings as estimates and keep margin below the per-instance limit.
"""
import sys

sys.path.insert(0, "/opt/maxcut")
import public_runner

sys.exit(public_runner.main(["run_public.py", "/app", "/app/instances",
                             "/app/public_reference.json"]))
