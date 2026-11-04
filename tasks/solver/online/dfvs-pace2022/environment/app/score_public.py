#!/usr/bin/env python3
"""Score your solver on the PUBLIC instances with the exact judging formula.

Usage:  python3 /app/score_public.py
Rebuilds via /app/build.sh, runs the public instances with a per-instance
wall-clock limit of 1800 s each (the official PACE 2022 exact-track
limit), validates with the official verifier (fvs_verify), and reports
per-instance and mean scores. The hidden judging uses the same code
(scoring.py), verifier, formula, and limit — only the instances and the
reference differ.
"""
import json
import sys

sys.path.insert(0, "/opt/dfvs")
import scoring

out = scoring.main(["score_public.py", "/app", "/app/instances",
                    "/app/public_reference.json"])
print(json.dumps(out, indent=1, sort_keys=True))
