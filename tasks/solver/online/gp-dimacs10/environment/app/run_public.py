#!/usr/bin/env python3
"""Run your solver on the PUBLIC practice instances and print per-instance
results.

Usage:  python3 /app/run_public.py
Rebuilds via /app/build.sh, runs your solver once per public instance
under one shared time pool (60 s per instance x instance count, handed
through GP_TIME_POOL; no per-instance limit), validates the partitions,
and prints one record per instance: name, A (recomputed edge cut),
validity status, seconds used. Nothing is aggregated.

This is a local convenience runner only: this dev box is NOT the judging
sandbox (core count, memory, and timing behavior differ). Treat the
results of submit.sh (public practice channel) as authoritative.
"""
import sys

sys.path.insert(0, "/opt/gp")
import public_runner

sys.exit(public_runner.main(["run_public.py", "/app", "/app/instances",
                             "/app/public_reference.json"]))
