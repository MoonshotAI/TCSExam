#!/usr/bin/env python3
"""Run your solver on the PUBLIC practice instances and report per-instance
results (local convenience runner).

Usage:  python3 /app/run_public.py

Rebuilds /app via `bash /app/build.sh`, runs your solver on the public
practice set in /app/instances with a hard per-instance wall-clock limit
(2 s by default; override with PER_INSTANCE_SECONDS), validates each
parent array and recomputes its score with the ported official scorer,
and prints per-instance results: instance name, your raw score A,
validity, and seconds used. It reads no reference values and computes no
aggregate.

It runs on this development box, outside the judging sandbox — local
measurements may not transfer. Use `submit.sh` for authoritative
measurements in the judging sandbox.
"""
import os
import sys

sys.path.insert(0, "/opt/ahc041")
import public_runner  # noqa: E402

sys.exit(public_runner.main(["run_public.py", "/app", "/app/instances"]))
