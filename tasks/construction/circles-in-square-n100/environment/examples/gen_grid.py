#!/usr/bin/env python3
"""Grid generator for circles-in-square-n100.

The k x k grid puts centers at ((i + 1/2)/k, (j + 1/2)/k) and supports radius
exactly 1/(2k): adjacent centers are 1/k = 2r apart and the outer ring sits
exactly r from the boundary, so every constraint holds with equality — the
grid always passes exact verification at r = 1/(2k).

Only the 10x10 grid satisfies the n = 100 premise of the task (k = 10 gives
exactly 100 circles). Other k are useful for debugging your own tooling only
— the checker rejects any center count other than 100.

Usage:
  python3 gen_grid.py OUT.json              # the 10x10 grid, r = 0.05
  python3 gen_grid.py OUT.json 10 0.0501    # same grid, overclaimed radius
                                            # (rejected: exact verification fails)
  python3 gen_grid.py OUT.json 8            # 8x8 grid: 64 circles, rejected (n != 100)
"""
import json
import sys


def grid(k, radius=None):
    r = radius if radius is not None else 1.0 / (2 * k)
    # exact short decimals: (2i+1)/(2k) for k = 10 has at most 2 decimals
    centers = [[f"{(2 * i + 1) / (2 * k):.10f}".rstrip("0"),
                f"{(2 * j + 1) / (2 * k):.10f}".rstrip("0")]
               for i in range(k) for j in range(k)]
    return {"n": k * k,
            "radius": f"{r:.10f}".rstrip("0"),
            "centers": centers,
            "comment": f"{k}x{k} grid, r = 1/{2 * k}"
                       + (" (overclaimed)" if radius is not None else "")}


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "/app/submission.json"
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    radius = float(sys.argv[3]) if len(sys.argv) > 3 else None
    doc = grid(k, radius)
    with open(out_path, "w") as f:
        json.dump(doc, f)
    print(f"wrote {out_path}: {k}x{k} grid, n = {k * k}, radius = {doc['radius']}"
          " (only k = 10 satisfies the n = 100 premise)")


if __name__ == "__main__":
    main()
