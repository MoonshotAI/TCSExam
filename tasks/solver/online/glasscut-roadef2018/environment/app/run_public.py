#!/usr/bin/env python3
"""Run your solver on the PUBLIC instances and print per-instance results.

Usage:  python3 /app/run_public.py
Rebuilds via /app/build.sh, runs the public practice instances under the
official dual time limits (a 3-minute run and a 1-hour run per instance),
validates the cutting patterns and recomputes their waste, then prints one
line per instance: both tiers' waste values, the official per-instance
composite, validity status, and seconds used. Nothing is aggregated.

This is a local convenience runner only: this dev box is NOT the judging
sandbox (core count, memory, timing, and limit enforcement all differ).
Treat the results of submit.sh (public practice channel) as authoritative.
"""
import sys

sys.path.insert(0, "/opt/glasscut")
import public_runner

sys.exit(public_runner.main(["run_public.py", "/app", "/app/instances",
                             "/app/public_reference.json"]))
