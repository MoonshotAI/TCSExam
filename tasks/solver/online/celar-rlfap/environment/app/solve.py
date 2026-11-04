#!/usr/bin/env python3
"""Baseline solver for the celar task (wrapper; see build.sh).

Two deterministic stages:

  1. min-conflicts constructor (seconds, always prints a complete block) —
     printed immediately, so the solver always leaves a usable solution on
     stdout no matter when the wall-clock kill arrives;
  2. OR-Tools CP-SAT on the reference model (celar.mzn), pinned to one
     search worker, fixed seed 42, and a deterministic-time budget of 30 (a
     machine-independent operation count) — its improving solutions are
     streamed through as they are printed.

The judge scores the LAST complete `f = [...];` block on stdout. CP-SAT's
first solution can in principle be worse than the constructor's, so if the
constructor was better than everything CP-SAT printed, the constructor's
block is printed once more at the end (keeping the last block the best).

Usage: solve.py INSTANCE_PATH   (invoked through the solver wrapper)
"""
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("/opt/celar", "/work", HERE):
    if os.path.exists(os.path.join(p, "public_runner.py")):
        sys.path.insert(0, p)
        break
import public_runner


def best_block(text, inst):
    """(objective, block_text) of the last complete f block in text,
    validated by the real checker, or None."""
    blocks = []
    for fm in re.finditer(r"\bf\s*=", text):
        lb = text.find("[", fm.end())
        if lb < 0:
            continue
        depth = 0
        vals = None
        for i in range(lb, len(text)):
            c = text[i]
            if c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        else:
            continue
        tail = text.find(";", end)
        if tail < 0:
            continue
        blocks.append(text[fm.start():tail + 1])
    if not blocks:
        return None
    with tempfile.NamedTemporaryFile("w", suffix=".out", delete=False) as t:
        t.write(blocks[-1] + "\n----------\n")
        tmp = t.name
    obj, err = public_runner.check_solution(inst, tmp)
    os.unlink(tmp)
    if err is not None:
        return None
    return obj, blocks[-1]


def main():
    inst = sys.argv[1]
    con = subprocess.run(
        ["python3", os.path.join(HERE, "construct.py"), inst],
        capture_output=True, text=True, check=True).stdout
    sys.stdout.write(con)
    sys.stdout.flush()
    cb = best_block(con, inst)

    p = subprocess.Popen(
        ["minizinc", "--solver", "cp-sat", "--fzn-flags",
         '--params "num_workers:1 random_seed:42 '
         'max_deterministic_time:30"',
         os.path.join(HERE, "celar.mzn"), inst],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    chunks = []
    while True:
        chunk = p.stdout.read(65536)
        if not chunk:
            break
        chunks.append(chunk)
        sys.stdout.write(chunk)
        sys.stdout.flush()
    p.wait()
    sb = best_block("".join(chunks), inst)

    if cb is not None and (sb is None or cb[0] < sb[0]):
        sys.stdout.write(cb[1] + "\n----------\n")
        sys.stdout.flush()


main()
