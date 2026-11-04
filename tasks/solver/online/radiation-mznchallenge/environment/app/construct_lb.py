#!/usr/bin/env python3
"""Deterministic constructor for the radiation task: unit-time floor.

Every cell (i,j) is covered by exactly Intensity[i,j] shape matrices of
beam-on time 1 (Q[i,j,1] = Intensity[i,j]); N[1] is set to the structural
lower bound LB = max_i ( I[i,1] + sum_{j>=2} max(I[i,j]-I[i,j-1],0) ), the
maximum per-row total positive gradient.  Row i then needs exactly
t_i <= LB apertures at level 1 (condition C2), so the block is always
valid, and its beam-on time is exactly LB — the admission ticket of the
reworked scoring is always attained.

This runs in milliseconds, is fully deterministic, and makes no attempt to
reuse longer beam-on times or coordinate rows to cut the shape count (the
shape count here is simply LB) — that is what the search stage is for.
Prints in exactly the model's output format.
"""
import re
import sys


def main(path):
    text = open(path, errors="replace").read()
    m = int(re.search(r"\bm\s*=\s*(\d+)", text).group(1))
    n = int(re.search(r"\bn\s*=\s*(\d+)", text).group(1))
    vals = [int(x) for x in re.findall(
        r"-?\d+", re.search(r"Intensity\s*=\s*\[\|(.*?)\|\]", text,
                            re.S).group(1))]
    bt_max = max(vals)
    lb = 0
    for i in range(m):
        t = vals[i * n]
        for j in range(1, n):
            d = vals[i * n + j] - vals[i * n + j - 1]
            if d > 0:
                t += d
        if t > lb:
            lb = t
    N = [0] * bt_max
    N[0] = lb
    Q = [0] * (m * n * bt_max)
    for idx in range(m * n):
        Q[idx * bt_max] = vals[idx]
    beamtime = lb
    shapes = lb
    objective = (m * n + 1) * beamtime + shapes
    print(f"objective = {objective};")
    print(f"Beamtime = {beamtime};")
    print(f"K = {shapes};")
    print("N = [%s];" % ", ".join(map(str, N)))
    print("Q = array3d(1..%d, 1..%d, 1..%d, [%s]);"
          % (m, n, bt_max, ", ".join(map(str, Q))))
    print("----------")


main(sys.argv[1])
