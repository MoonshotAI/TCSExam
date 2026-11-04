#!/usr/bin/env python3
"""Run your solver on the PUBLIC practice instances and report per-instance
results (local convenience runner).

Usage:  python3 /app/run_public.py

Rebuilds /app via `bash /app/build.sh`, then runs your solver on the public
practice set in /app/instances under ONE SHARED TIME POOL (60 s per
instance times the instance count, the same protocol as judging; the
solver learns the remaining pool via ITC2021_TIME_POOL on every run),
validates each schedule with the official validator (/opt/itc2021/RobinX),
recomputes its soft penalty from scratch, and prints per-instance results:
instance name, your penalty A, validity, and seconds used. It reads no
reference values and computes no aggregate.

It runs on this development box, outside the judging sandbox — local
measurements may not transfer. Use `submit.sh` for authoritative
measurements in the judging sandbox.
"""
import os
import sys

sys.path.insert(0, "/opt/itc2021")
import public_runner  # noqa: E402

sys.exit(public_runner.main(["run_public.py", "/app", "/app/instances"]))
