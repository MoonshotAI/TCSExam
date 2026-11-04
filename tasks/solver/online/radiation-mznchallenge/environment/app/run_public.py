#!/usr/bin/env python3
"""Run your solver on the PUBLIC instances and print per-instance results.

Usage:  python3 /app/run_public.py
Rebuilds via /app/build.sh, runs the public practice instances with a hard
per-instance wall-clock limit (locally 60 s by default for quick
iteration — set PER_INSTANCE_SECONDS to override; the judging sandbox uses
its own per-instance budget), validates the printed N/Q solutions and
recomputes beamtime / shape count / the structural lower bound, then
prints one line per instance: name, A (shape count), beamtime, lb,
validity status, seconds used. Nothing is aggregated.

This is a local convenience runner only: this dev box is NOT the judging
sandbox (core count, memory, and timing behavior differ). Treat the
results of submit.sh (public practice channel) as authoritative.
"""
import os
import sys

os.environ.setdefault("PER_INSTANCE_SECONDS", "60")
sys.path.insert(0, "/opt/radiation")
import public_runner

sys.exit(public_runner.main(["run_public.py", "/app", "/app/instances",
                             "/app/public_reference.json"]))
