#!/usr/bin/env python3
"""Verifier for circles-in-square-n100-lean-open: a Lean 4 certificate that
a valid packing of 100 equal circles of radius r in the unit square exists
with rational centers (a certified lower bound on the optimal radius at
n = 100).

Pipeline mirrors kissing-d9-lean-open: fixed-part integrity, claim-block
location, lexical anti-cheat (`axiom` / `sorryAx` anywhere, `sorry`/`admit`
outside the claim body), compile with a statement probe, `#print axioms`
whitelist (standard axioms + Lean.ofReduceBool + Lean.trustCompiler --
`native_decide` IS the intended certificate path here), parse r from the
claim header, score.

The claimed radius r is written in the claim as a plain decimal literal
(`CircleConfig 0.05 S`). The judge parses it digit-by-digit with
fractions.Fraction — exactly as Lean's `OfScientific` elaborates the same
literal to a `Rat`, and exactly as the solver sibling's checker parses
decimal strings. No floating point anywhere in the anchor comparison.

Scoring, mode `solver_cubic` (anchors shared with the solver sibling
circles-in-square-n100, whose checker stores the record as the exact
fraction 25700535887/500000000000):
  lower: r <= 0.05                -> 0      (baseline: the 10x10 grid)
         r > 0.05                 -> ((r - 1/20) / (record - 1/20))^3,
                                      uncapped; record = 0.0514010717743403 (PECS repository value, 2026-09-20 anchor correction)
                                      (Packomania csq printed table value,
                                      n = 100 row, checked 2026-08-15)
         r == record              -> 1.0, record_matched
         r > record (verified)    -> > 1.0, record_broken (a new world
                                      record at n = 100)
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from fractions import Fraction

# Load the image-owned shared checks without using the submission's import path.
import importlib.util as _import_util
_security_spec = _import_util.spec_from_file_location(
    "tcsexam_lean_security", os.path.join(os.path.dirname(os.path.abspath(__file__)), "lean_security.py"))
_security = _import_util.module_from_spec(_security_spec)
_security_spec.loader.exec_module(_security)


FIXED_END_MARK = "-- END OF FIXED PART"
FORBIDDEN_ANYWHERE = re.compile(r"\b(axiom|sorryAx)\b")
SORRY_OR_ADMIT = re.compile(r"\b(sorry|admit)\b")


def strip_comments(text: str) -> str:
    return _security.strip_comments(text)


def norm_ws(text: str) -> str:
    return " ".join(text.split())


def fixed_part(text: str):
    """Everything up to and including the standalone FIXED_END_MARK line.

    The mark must anchor on a line of its own: the file's docstring also
    mentions `-- END OF FIXED PART` inline (in backticks), and a plain
    `str.find` would match that first and silently truncate the check.
    """
    m = re.search(r"(?m)^" + re.escape(FIXED_END_MARK) + r"\s*$", text)
    if m is None:
        return None
    nl = text.find("\n", m.start())
    return text[: (nl + 1) if nl != -1 else len(text)]


def find_claim_block(text: str, name: str):
    """Locate `theorem <name>` with its CLAIM BEGIN/END markers.

    Returns (block_span, header_text, body_text) or None. Header is the text
    between `theorem <name>` and the first `:=` before the BEGIN mark; body
    is the text between the BEGIN and END marker lines.
    """
    m = re.search(r"(?m)^theorem\s+" + re.escape(name) + r"\b", text)
    if not m:
        return None
    begin = re.search(
        r"(?m)^\s*-- CLAIM " + re.escape(name) + r" BEGIN\s*$", text[m.end():]
    )
    end = re.search(
        r"(?m)^\s*-- CLAIM " + re.escape(name) + r" END\s*$", text[m.end():]
    )
    if not begin or not end or end.start() < begin.end():
        return None
    begin_abs = (m.end() + begin.start(), m.end() + begin.end())
    end_abs = (m.end() + end.start(), m.end() + end.end())
    nl = text.find("\n", begin_abs[1])
    if nl == -1:
        return None
    body = text[nl + 1: end_abs[0]]
    header_region = text[m.end():begin_abs[0]]
    ci = header_region.find(":=")
    if ci == -1:
        return None
    header = header_region[:ci]
    return (m.start(), end_abs[1]), header, body


def parse_claim_r(header: str, pattern: str):
    """Match the (whitespace-normalized) header against the pinned pattern;
    return the captured decimal radius as an exact Fraction or None."""
    m = re.fullmatch(pattern, norm_ws(header))
    if not m:
        return None
    try:
        return Fraction(m.group(1))
    except (ValueError, ZeroDivisionError):
        return None


def lean_axioms_ok(stdout: str, full_name: str, allowed: set) -> bool:
    return _security.axioms_ok(stdout, full_name, allowed)


def run_lean(app_dir: str, path: str, timeout: int):
    return _security.run_lean(app_dir, path, timeout)


def score_lower(r: Fraction, mode: str, cfg: dict):
    """Cubic interpolation on the verified radius; anchors are exact
    fractions shared with the solver sibling's checker."""
    base = Fraction(cfg["baseline_r"])
    rec = Fraction(cfg["record_r"])
    if mode == "solver_cubic":
        s = 0.0 if r <= base else float(((r - base) / (rec - base)) ** 3)
    else:  # alpha_milestone
        s = 1.0 if r >= rec else float(((r - base) / (rec - base)) ** 3)
    # record-break tolerance (project rule 260916): beating the record counts
    # only when the relative margin exceeds 1e-6; rounding-representation
    # residue below it is record_matched, not record_broken.
    if r > rec and (r - rec) / rec > _RECORD_TOL:
        ms = "record_broken"
    elif r >= rec:
        ms = "record_matched"
    elif mode == "solver_cubic" and r <= base:
        ms = "baseline"
    elif mode == "solver_cubic":
        ms = "progress"
    else:
        ms = "verified"
    return s, ms


_RECORD_TOL = Fraction(1, 1000000)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", default=os.environ.get("APP_DIR", "/app"))
    ap.add_argument("--tests", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--reward", default=os.environ.get("REWARD_FILE", "/logs/verifier/reward.txt"))
    ap.add_argument("--reward-json", default=os.environ.get("REWARD_JSON", "/logs/verifier/score-details.json"))
    args = ap.parse_args()

    report = {"reward": 0.0, "valid": 0, "claims": {}, "details": []}

    def write_rewards(value: float) -> None:
        for path, payload in ((args.reward, f"{value:g}"), (args.reward_json, json.dumps(report, indent=1))):
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w") as f:
                    f.write(payload)
            except OSError:
                pass

    def fail(msg: str) -> int:
        print(f"FAIL: {msg}")
        report["details"].append(f"FAIL: {msg}")
        write_rewards(0.0)
        return 0

    with open(os.path.join(args.tests, "judge.json")) as f:
        spec = json.load(f)
    namespace = spec.get("namespace", "CSQ100")
    mode = spec.get("score_mode", "alpha_milestone")
    allowed = set(spec.get("allowed_axioms", ["propext", "Classical.choice", "Quot.sound"]))
    compile_timeout = int(spec.get("compile_timeout_sec", 1200))

    with open(os.path.join(args.tests, "reference", "Basic.lean")) as f:
        reference = f.read()

    sub_path = os.path.join(args.app, "Task", "Basic.lean")
    try:
        with open(sub_path) as f:
            submission = f.read()
    except OSError:
        return fail("no submission Task/Basic.lean")

    source_error = _security.source_error(submission, allow_native=True)
    if source_error:
        return fail(source_error)

    # ---- fixed part integrity ------------------------------------------------
    ref_fixed, sub_fixed = fixed_part(reference), fixed_part(submission)
    if ref_fixed is None or sub_fixed is None or norm_ws(strip_comments(ref_fixed)) != norm_ws(strip_comments(sub_fixed)):
        return fail("fixed code block missing or tampered (comments are free)")

    # ---- locate claim blocks ---------------------------------------------------
    claims = {}
    for c in spec["claims"]:
        blk = find_claim_block(submission, c["name"])
        if blk is None:
            print(f"NOTE: claim {c['name']} not present (direction not attempted)")
            continue
        claims[c["name"]] = (c, blk)

    # ---- lexical anti-cheat ----------------------------------------------------
    stripped = strip_comments(submission)
    if FORBIDDEN_ANYWHERE.search(stripped):
        return fail("forbidden token (axiom / sorryAx)")

    # sorry/admit outside claim bodies?
    segments = []
    prev = 0
    for name in sorted(claims, key=lambda k: claims[k][1][0][0]):
        span = claims[name][1][0]
        segments.append(submission[prev:span[0]])
        prev = span[1]
    segments.append(submission[prev:])
    if any(SORRY_OR_ADMIT.search(strip_comments(seg)) for seg in segments):
        return fail("sorry/admit outside claim bodies")

    # ---- parse r, drop sorry claims ---------------------------------------------
    scored = {}   # name -> (direction, r)
    for name, (c, blk) in claims.items():
        header = blk[1]
        r = parse_claim_r(header, c["header_pattern"])
        if r is None:
            print(f"NOTE: claim {name} header does not match the pinned shape; not scored")
            report["details"].append(f"claim {name}: header tampered or unreadable")
            continue
        if SORRY_OR_ADMIT.search(strip_comments(blk[2])):
            print(f"NOTE: claim {name} (r={float(r)}) still contains sorry/admit; not scored")
            report["claims"][name] = {"r": str(r), "status": "unproven"}
            continue
        scored[name] = (c["direction"], r)

    if not scored:
        return fail("no claim is proven (nothing to score)")

    # ---- compile + axioms ---------------------------------------------------------
    tmpdir = tempfile.mkdtemp(prefix="csqn100-score-")
    variant = os.path.join(tmpdir, "Check.lean")
    with open(variant, "w") as f:
        f.write(submission)
        for name in scored:
            f.write(_security.axiom_audit(f'{namespace}.{name}', allow_native=True))
    ok, out = run_lean(args.app, variant, compile_timeout)
    if not ok:
        print("submission does not compile:")
        print("\n".join(out.splitlines()[-25:]))
        return fail("compilation failed (see verifier log)")

    # ---- score ---------------------------------------------------------------------
    best = 0.0
    for name, (direction, r) in scored.items():
        full = f"{namespace}.{name}"
        if not lean_axioms_ok(out, full, allowed):
            print(f"claim {name}: FAIL (non-standard axioms)")
            report["claims"][name] = {"r": str(r), "status": "bad_axioms"}
            continue
        if direction != "lower":
            print(f"NOTE: claim {name} has unknown direction {direction!r}; not scored")
            continue
        cfg = spec["scoring"]["lower"]
        s, ms = score_lower(r, mode, cfg)
        report["claims"][name] = {"direction": direction, "r": str(r),
                                  "r_float": float(r), "status": "proven",
                                  "score": s, "milestone": ms}
        print(f"claim {name}: PROVEN at r={float(r)} ({direction}) -> score {s:.6f}, milestone {ms}")
        if ms == "record_broken":
            report["details"].append(
                f"{name} with r={r} is strictly above the Packomania printed "
                "table value 0.0514010717743403 (PECS repo): the optimal radius for 100 equal "
                "circles in the unit square is >= the certified r, a new result")
        best = max(best, s)

    report["reward"] = best
    report["valid"] = 1 if best > 0 or scored else 0
    report["score_mode"] = mode
    print(f"reward={best:g} mode={mode}")
    write_rewards(best)
    return 0


if __name__ == "__main__":
    sys.exit(main())
