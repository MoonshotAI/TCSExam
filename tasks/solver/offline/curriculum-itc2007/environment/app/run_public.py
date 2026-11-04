#!/usr/bin/env python3
"""Run your solver on the PUBLIC practice instances and report per-instance
results (local convenience runner).

Usage:  python3 /app/run_public.py

Rebuilds /app via `bash /app/build.sh`, runs your solver on the public
practice set in /app/instances with a hard per-instance wall-clock limit
(240 s by default; override with PER_INSTANCE_SECONDS), validates each
timetable with the official validator (/opt/ctt/validator), recomputes its
cost from scratch, and prints per-instance results: instance name, your
cost A, validity, and seconds used. It reads no reference values and
computes no aggregate.

It runs on this development box, outside the judging sandbox — local
measurements may not transfer. Treat timings as estimates and keep margin below the per-instance limit.
"""
import os
import sys

sys.path.insert(0, "/opt/ctt")
import public_runner  # noqa: E402

sys.exit(public_runner.main(["run_public.py", "/app", "/app/instances"]))
