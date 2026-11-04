#!/usr/bin/env python3
"""Run your solver on the PUBLIC practice instances and print per-instance
results.

Usage:  python3 /app/run_public.py
Rebuilds via `make` in a scratch copy of `/app`, runs your solver once per
public instance with the same per-instance protocol (600 s budget passed
as the LIMIT_SECONDS argument, SIGTERM/SIGKILL after budget + grace,
tour validated with the pristine tsp_check), and prints one record per
instance: name, A (validated tour length), validity status, seconds used.
Nothing is aggregated.

This is a local convenience runner only: this dev box is NOT the judging
sandbox (core count, memory, and timing behavior differ). Treat the
results of submit.sh (public practice channel) as authoritative.
"""
import sys

sys.path.insert(0, "/opt/tsp")
import public_runner

sys.exit(public_runner.main(["run_public.py", "/app", "/app/instances",
                             "/app/public_reference.json"]))
