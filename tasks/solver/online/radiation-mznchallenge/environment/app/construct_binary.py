#!/usr/bin/env python3
"""Deterministic constructor for the radiation task: binary decomposition.

Every cell's intensity is written in binary; for each bit position k with
value b = 2^k, the bit matrix is exposed by shapes of beam-on time b, so
cell (i,j) receives exactly its prescribed intensity. Q[i,j,b] is the bit
of Intensity[i,j] at position k; N[b] is the maximum per-row interval
count of that bit matrix (necessary and sufficient by condition C2).
This runs in milliseconds, always produces a valid decomposition, and
prints it in exactly the model's output format. It makes no attempt to
coordinate rows or reuse shapes — that is what the search stage is for.
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
    N = [0] * bt_max
    Q = [0] * (m * n * bt_max)
    k = 0
    while (1 << k) <= bt_max:
        b = (1 << k) - 1  # 0-based index of beam-on time 2^k
        bits = [(v >> k) & 1 for v in vals]
        need_max = 0
        for i in range(m):
            row = bits[i * n:(i + 1) * n]
            need = row[0] + sum(1 for j in range(1, n)
                                if row[j] > row[j - 1])
            need_max = max(need_max, need)
        N[b] = need_max
        for idx in range(m * n):
            Q[idx * bt_max + b] = bits[idx]
        k += 1
    beamtime = sum((b + 1) * N[b] for b in range(bt_max))
    shapes = sum(N)
    objective = (m * n + 1) * beamtime + shapes
    print(f"objective = {objective};")
    print(f"Beamtime = {beamtime};")
    print(f"K = {shapes};")
    print("N = [%s];" % ", ".join(map(str, N)))
    print("Q = array3d(1..%d, 1..%d, 1..%d, [%s]);"
          % (m, n, bt_max, ", ".join(map(str, Q))))
    print("----------")


main(sys.argv[1])
