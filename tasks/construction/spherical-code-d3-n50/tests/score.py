#!/usr/bin/env python3
"""Verifier for spherical-code-d3-n50-lean-open: a Lean 4 certificate that
50 nonzero rational vectors in Q^3 exist with every normalized pairwise
inner product <= T (a certified upper bound on the optimal maximal cosine
of the N = 50 Tammes problem).

Pipeline mirrors kissing-d9-lean-open: fixed-part integrity, claim-block
location, lexical anti-cheat (`axiom` / `sorryAx` anywhere, `sorry`/`admit`
outside the claim body), compile with a statement probe, `#print axioms`
whitelist (standard axioms + Lean.ofReduceBool + Lean.trustCompiler --
`native_decide` IS the intended certificate path here), parse the threshold
T = num/den from the claim header, score.

Scoring, mode `solver_cubic` (anchors shared with the solver sibling
spherical-code-d3-n50):
  T >= BASE   -> 0       (BASE = 0.9045852811944625, the deterministic
                          Fibonacci-spiral baseline of the sibling task)
  RECORD < T < BASE -> ((BASE - T) / (BASE - RECORD))^3
  T == RECORD -> 1.0     (record line, set 1 ulp below the printed table
                          value 0.868173209127 of Cohn's spherical code
                          table, hence below the true record r*; milestone
                          record_matched)
  T < RECORD  -> record_broken, uncapped (a certified strict improvement
                          over Szekely 1974; flagged for human review)
Claims are scored only for 0 < T <= 1. The printed reward is floored to 6
decimals, as in the sibling checker (rounding never inflates the score).
"""

import argparse
import json
import math
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
    m = re.search(r"(?m)^[ \t]*theorem\s+" + re.escape(name) + r"\b", text)
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


def parse_claim_t(header: str, pattern: str):
    """Match the (whitespace-normalized) header against the pinned pattern;
    return the threshold T = num/den as an exact Fraction, or None."""
    m = re.fullmatch(pattern, norm_ws(header))
    if not m:
        return None
    num, den = int(m.group(1)), int(m.group(2))
    if den == 0:
        return None
    return Fraction(num, den)


def lean_axioms_ok(stdout: str, full_name: str, allowed: set) -> bool:
    return _security.axioms_ok(stdout, full_name, allowed)


def run_lean(app_dir: str, path: str, timeout: int):
    return _security.run_lean(app_dir, path, timeout)


def floor6(s: float) -> float:
    """Printed reward: floored to 6 decimals (never rounds the score up)."""
    return math.floor(s * 10 ** 6) / 10 ** 6


def score_upper_t(t: Fraction, cfg: dict):
    """Cubic interpolation on the certified threshold, smaller is better.

    All milestone comparisons are exact rational arithmetic; only the final
    interpolation uses float64 (relative error ~1e-16, immaterial), and the
    printed reward is floored to 6 decimals so rounding never inflates it.
    """
    base = Fraction(cfg["baseline"])
    record = Fraction(cfg["record"])
    if t >= base:
        return 0.0, "baseline"
    f_base, f_record, f_t = float(base), float(record), float(t)
    s = floor6(((f_base - f_t) / (f_base - f_record)) ** 3)
    # record-break tolerance (project rule 260916): beating the record counts
    # only when the relative margin exceeds 1e-6; rounding-representation
    # residue below it is record_matched, not record_broken.
    if t < record and (record - t) / record > _RECORD_TOL:
        ms = "record_broken"
    elif t <= record:
        ms = "record_matched"
    else:
        ms = "progress"
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
    namespace = spec.get("namespace", "SCN50")
    mode = spec.get("score_mode", "solver_cubic")
    allowed = set(spec.get("allowed_axioms", ["propext", "Classical.choice", "Quot.sound"]))
    t_max = Fraction(spec["scoring"]["upper"].get("t_max", "1"))
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

    # ---- parse T, drop sorry claims ---------------------------------------------
    scored = {}   # name -> (direction, t)
    for name, (c, blk) in claims.items():
        header = blk[1]
        t = parse_claim_t(header, c["header_pattern"])
        if t is None:
            print(f"NOTE: claim {name} header does not match the pinned shape; not scored")
            report["details"].append(f"claim {name}: header tampered or unreadable")
            continue
        if not (0 < t <= t_max):
            print(f"NOTE: claim {name} T={t} out of range (0, {t_max}]; not scored")
            continue
        if SORRY_OR_ADMIT.search(strip_comments(blk[2])):
            print(f"NOTE: claim {name} (T={t}) still contains sorry/admit; not scored")
            report["claims"][name] = {"t": str(t), "status": "unproven"}
            continue
        scored[name] = (c["direction"], t)

    if not scored:
        return fail("no claim is proven (nothing to score)")

    # ---- compile + axioms ---------------------------------------------------------
    tmpdir = tempfile.mkdtemp(prefix="scn50-score-")
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
    for name, (direction, t) in scored.items():
        full = f"{namespace}.{name}"
        if not lean_axioms_ok(out, full, allowed):
            print(f"claim {name}: FAIL (non-standard axioms)")
            report["claims"][name] = {"t": str(t), "status": "bad_axioms"}
            continue
        cfg = spec["scoring"]["upper"]
        s, ms = score_upper_t(t, cfg)
        report["claims"][name] = {"direction": direction, "t": str(t), "status": "proven",
                                  "score": s, "milestone": ms}
        print(f"claim {name}: PROVEN at T={t} ({direction}) -> score {s:.6f}, milestone {ms}")
        if ms == "record_broken":
            report["details"].append(
                f"{name} with T={t} is below the record line 0.8681732091268975, "
                "which is itself below the true record value r* = "
                "0.8681732091268974516747... (Szekely 1974, tracked by Cohn's "
                "spherical code table): a certified strict improvement of the "
                "N = 50 Tammes record — a new result, flagged for mandatory "
                "human review")
        best = max(best, s)

    report["reward"] = best
    report["valid"] = 1 if best > 0 or scored else 0
    report["score_mode"] = mode
    print(f"reward={best:g} mode={mode}")
    write_rewards(best)
    return 0


if __name__ == "__main__":
    sys.exit(main())
