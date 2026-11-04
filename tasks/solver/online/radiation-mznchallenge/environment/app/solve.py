#!/usr/bin/env python3
"""Baseline solver for the radiation task (wrapper; see build.sh).

260831 rework: the scoring contract now requires the beam-on time to attain
the structural lower bound LB (the maximum per-row total positive gradient
of the intensity matrix) and scores the SHAPE COUNT alone.  The shipped
baseline is deliberately naive: it prints the deterministic unit-time
construction from construct_lb.py (every cell (i,j) covered by exactly
Intensity[i,j] unit-time shapes; N[1] = LB — always valid, always exactly
at the bound, shape count = LB) and nothing else.  Beating it means
reusing longer beam-on times and coordinating rows so that fewer shapes
suffice — that is the task.

Usage: solve.py INSTANCE_PATH   (invoked through the solver wrapper)
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

out = subprocess.run(
    ["python3", os.path.join(HERE, "construct_lb.py"), sys.argv[1]],
    capture_output=True, text=True, check=True).stdout
sys.stdout.write(out)
sys.stdout.flush()
