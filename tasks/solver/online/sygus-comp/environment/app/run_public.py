#!/usr/bin/env python3
"""Run your solver on the PUBLIC instances and print per-instance results.

Usage:  python3 /app/run_public.py
Rebuilds /app solver via /app/build.sh, runs the public practice instances
with a per-instance wall-clock budget (3600 s, the SyGuS-Comp budget),
machine-checks every solution (grammar derivability + negated-spec unsat
via a pristine cvc5), and prints one line per instance: name, solved flag
(1/0), validity status, seconds used. Nothing is aggregated.

This is a local convenience runner only: this dev box is NOT the judging
sandbox (core count, memory, and timing behavior differ). Treat the
results of submit.sh (public practice channel) as authoritative.
"""
import os
import sys

sys.path.insert(0, "/opt/sygus")
import public_runner

APP_DIR = "/app"
INSTANCES_DIR = os.path.join(APP_DIR, "instances")
REFERENCE = os.path.join(APP_DIR, "public_reference.json")

sys.exit(public_runner.main(["run_public.py", APP_DIR, INSTANCES_DIR,
                             REFERENCE]))
