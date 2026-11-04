#!/bin/bash
# Baseline build: install the naive enumeration synthesizer as /app/solver.
# The factory baseline is `naive_sygus.py` — the simplest honest SyGuS
# solver: bottom-up grammar enumeration checked candidate-by-candidate
# with the task's own machine check (no CEGIS, no portfolio, no tuning).
# cvc5 remains available at /app/cvc5 as a tool YOU can build a stronger
# solver around. If you add your own sources, edit this script to build
# them — the judge runs exactly this script and then invokes /app/solver
# once per instance as `/app/solver INSTANCE.sl`.
set -e
cp /app/naive_sygus.py /app/solver
chmod +x /app/solver
