#!/usr/bin/env python3
"""json_to_lean.py — turn a JSON edge-list certificate (the solver sibling's
format: {"n": N, "edges": [[u, v], ...]}) into a Lean literal edge list for
use inside a witness definition:

    def myEdges : List (Nat × Nat) := [<output of this script>]

Usage: python3 json_to_lean.py graph.json           # print the Lean list
       python3 json_to_lean.py graph.json --def myEdges   # whole def line

The script does NOT check the graph: validity is decided by the Lean
predicates (`WellFormed`, `C3C4Free`) under `native_decide`. Example:
/examples/example_n124_greedy.json converts to a 483-edge witness proving
submission_lower at m = 483 (exercises the
whole pipeline).
"""
import json
import sys


def main():
    path = sys.argv[1]
    cert = json.load(open(path))
    edges = cert["edges"]
    n = cert["n"]
    lit = "[" + ", ".join(f"({u}, {v})" for u, v in edges) + "]"
    if len(sys.argv) > 2 and sys.argv[2] == "--def":
        name = sys.argv[3] if len(sys.argv) > 3 else "myEdges"
        print(f"def {name} : List (Nat × Nat) := {lit}")
        print(f"-- {len(edges)} edges on n={n}; prove with", file=sys.stderr)
        print(f"-- exact ⟨ofEdges {n} {name}, by native_decide, "
              f"by native_decide, by native_decide⟩", file=sys.stderr)
    else:
        print(lit)


if __name__ == "__main__":
    main()
