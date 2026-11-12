#!/usr/bin/env python3
"""Verifier for tcsexam/tsp-gap-lean (open-proof, alpha-parameterized).

Pipeline:
  1. Lexical anti-cheat on the comment-stripped submission:
     `axiom` / `sorryAx` / `native_decide` / `sorry` / `admit` /
     `implemented_by` / `extern` / `unsafe` / `opaque` anywhere -> reward 0.
     (There are no checkpoint slots in this task: any `sorry` is fatal.)
  2. Fixed-part integrity: everything up to the line starting with
     `-- END OF FIXED PART` must match tests/reference/Basic.lean
     (comments stripped, whitespace-normalized). The marker is matched at line start —
     the task's own header comment mentions the marker literally.
  3. Interface presence: `certN`, `certCost`, `claimedAlpha`, `main`.
  4. Probe: append to the submission text
       open TSPGap
       example : GapBound certN certCost claimedAlpha := main
       #print axioms main
       #eval certN
       #eval (claimedAlpha.num, claimedAlpha.den)
     and compile with `lake env lean`. The `example` forces `main` to prove
     exactly the packaged statement for the submitted data; `#print axioms`
     must stay within the standard axioms; the `#eval`s report `n` and the
     claimed `alpha` (a normalized rational) for scoring.
  5. Reward (see judge.json), same linear uncapped curve as the solver
     sibling tsp-gap-n15:
       reward = max(0, (alpha - baseline) / (standing - baseline))
     with baseline = 11/10 (Petersen-level sanity) and standing = 76/61
     (largest Benoit–Boyd family value, n = 20). Uncapped above 1.
     Flags: record_broken = alpha strictly past the Benoit–Boyd family
                            value at the submitted n (per-n table in
                            judge.json; n = 15/16 records are SWvZ
                            counterexamples);
            beyond_table4 = alpha > 27/22 at any n (informational).
"""

import argparse
from fractions import Fraction
import json
import os
import re
import subprocess
import sys
import tempfile

# Load the image-owned shared checks without using the submission's import path.
import importlib.util as _import_util
_security_spec = _import_util.spec_from_file_location(
    "tcsexam_lean_security", os.path.join(os.path.dirname(os.path.abspath(__file__)), "lean_security.py"))
_security = _import_util.module_from_spec(_security_spec)
_security_spec.loader.exec_module(_security)


FIXED_END_MARK = "-- END OF FIXED PART"
FORBIDDEN_ANYWHERE = re.compile(
    r"\b(axiom|sorryAx|native_decide|sorry|admit|implemented_by|extern|unsafe|opaque)\b"
)


def strip_comments(text: str) -> str:
    return _security.strip_comments(text)


def norm_ws(text: str) -> str:
    return " ".join(text.split())


def lean_axioms_ok(stdout: str, full_name: str, allowed: set) -> bool:
    return _security.axioms_ok(stdout, full_name, allowed)


def run_lean(app_dir: str, path: str, timeout: int):
    return _security.run_lean(app_dir, path, timeout)


def parse_evals(stdout: str):
    """Extract `certN` and `claimedAlpha` from the probe's #eval output."""
    nums = re.findall(r"(?m)^\s*(\d+)\s*$", stdout)
    pair = re.search(r"(?m)^\s*\(\s*(-?\d+)\s*,\s*(\d+)\s*\)\s*$", stdout)
    if not nums or not pair:
        return None, None
    n = int(nums[-1])
    num, den = int(pair.group(1)), int(pair.group(2))
    if den <= 0:
        return None, None
    return n, Fraction(num, den)


def reward_and_flags(n, alpha: Fraction, spec: dict):
    base = Fraction(spec["baseline_alpha"])      # 11/10: Petersen-level sanity
    standing = Fraction(spec["standing_alpha"])  # 76/61: largest family value
    reward = max(0.0, float((alpha - base) / (standing - base)))
    rec = {int(k): Fraction(v) for k, v in spec["record_per_n"].items()}
    record_broken = bool(rec.get(n) is not None and alpha > rec[n])
    beyond_table4 = alpha > Fraction(spec["table4_max"])
    return reward, record_broken, beyond_table4


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", default=os.environ.get("APP_DIR", "/app"))
    ap.add_argument("--tests", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--reward", default=os.environ.get("REWARD_FILE", "/logs/verifier/reward.txt"))
    args = ap.parse_args()

    def write_reward(value: float) -> None:
        os.makedirs(os.path.dirname(args.reward), exist_ok=True)
        with open(args.reward, "w") as f:
            f.write(f"{value:g}")

    with open(os.path.join(args.tests, "judge.json")) as f:
        spec = json.load(f)
    namespace = spec.get("namespace", "TSPGap")
    main_theorem = spec.get("main_theorem", "main")
    full_name = f"{namespace}.{main_theorem}"
    allowed_axioms = set(spec["standard_axioms"])
    probe_timeout = int(spec.get("probe_timeout_sec", 1700))

    with open(os.path.join(args.tests, "reference", "Basic.lean")) as f:
        reference = f.read()

    sub_path = os.path.join(args.app, "Task", "Basic.lean")
    try:
        with open(sub_path) as f:
            submission = f.read()
    except OSError:
        print("FAIL: no submission Task/Basic.lean")
        write_reward(0)
        return 0

    source_error = _security.source_error(submission, allow_native=True)
    if source_error:
        print("FAIL: " + source_error)
        write_reward(0)
        return 0

    # ---- fixed part integrity -------------------------------------------------
    # NOTE: the marker must be matched at line start — a plain text.find
    # lands inside the header comment of this task's own Basic.lean (which
    # mentions `-- END OF FIXED PART` literally) and would protect only the
    # first ~30 lines.
    def fixed_part(text: str):
        m = re.search(r"(?m)^-- END OF FIXED PART.*$", text)
        if m is None:
            return None
        return text[: m.end()]

    ref_fixed, sub_fixed = fixed_part(reference), fixed_part(submission)
    if ref_fixed is None or sub_fixed is None or norm_ws(strip_comments(ref_fixed)) != norm_ws(strip_comments(sub_fixed)):
        print("FAIL: fixed code block missing or tampered (comments are free)")
        write_reward(0)
        return 0

    # ---- lexical anti-cheat ----------------------------------------------------
    stripped = strip_comments(submission)
    m = FORBIDDEN_ANYWHERE.search(stripped)
    if m:
        print(f"FAIL: forbidden token ({m.group(0)})")
        write_reward(0)
        return 0

    # ---- interface presence -----------------------------------------------------
    for d in spec["interface_defs"] + [f"theorem {main_theorem}"]:
        kind, name = d.split(" ", 1) if " " in d else ("def", d)
        if not re.search(rf"(?m)^[ \t]*{kind}\s+{re.escape(name)}\b", stripped):
            print(f"FAIL: interface name `{name}` ({kind}) missing")
            write_reward(0)
            return 0

    # ---- probe -------------------------------------------------------------------
    fd, probe_path = tempfile.mkstemp(prefix="tspgap-probe-", suffix=".lean")
    with os.fdopen(fd, "w") as f:
        f.write(submission)
        f.write(
            f"\nopen {namespace}\n"
            f"example : GapBound certN certCost claimedAlpha := {main_theorem}\n"
            f"{_security.axiom_audit(full_name, allow_native=True)}"
            f"#eval certN\n"
            f"#eval (claimedAlpha.num, claimedAlpha.den)\n"
        )
    ok, out = run_lean(args.app, probe_path, timeout=probe_timeout)
    if not ok:
        print("FAIL: probe compile failed (submission does not build, or `main` "
              "does not prove `GapBound certN certCost claimedAlpha`)")
        print("  " + "\n  ".join(out.splitlines()[-15:]))
        write_reward(0)
        return 0

    if not lean_axioms_ok(out, full_name, allowed_axioms):
        print("FAIL: `main` depends on non-standard axioms")
        print("  " + "\n  ".join(out.splitlines()[-15:]))
        write_reward(0)
        return 0

    n, alpha = parse_evals(out)
    if n is None:
        print("FAIL: could not read certN / claimedAlpha from probe output")
        write_reward(0)
        return 0

    reward, record_broken, beyond_table4 = reward_and_flags(n, alpha, spec)
    report = {
        "n": n,
        "alpha": f"{alpha.numerator}/{alpha.denominator}",
        "alpha_float": float(alpha),
        "reward": reward,
        "record_broken": record_broken,
        "beyond_table4": beyond_table4,
        "in_range_15_20": 15 <= n <= 20,
    }
    print(json.dumps(report, indent=2))
    write_reward(reward)
    return 0


if __name__ == "__main__":
    sys.exit(main())
