#!/usr/bin/env python3
"""Verifier for mols-n10-lean-open: a Lean 4 certificate that a family of k
pairwise orthogonal Latin squares of order n exists (a certified lower bound
N(n) >= k).

Pipeline mirrors the lean-open family (vdw-w27 / kissing-d9): fixed-part
integrity, claim-block location, lexical anti-cheat (`axiom` / `sorryAx`
anywhere, `sorry` / `admit` outside the claim body), compile with a
statement probe, `#print axioms` whitelist (standard axioms +
Lean.ofReduceBool + Lean.trustCompiler -- `native_decide` IS the intended
certificate path here), parse (n, k) from the claim header, score.

Scoring, mode `solver_linear_per_grid` (anchors shared with the solver
sibling mols-n10):
  grid order n (10/12/14/15/18/20/21/22/24/26), baseline B, record K:
      score = max(0, (k - B) / (K - B)), uncapped
  k = K -> 1.0 ("record_matched"); k > K -> "record_broken" (a new result;
  k = 3 at n = 10 would settle a 66-year-old problem).  Claims at orders
  outside the grid (e.g. the sanity pair at n = 3) compile and are
  axiom-checked but score 0 ("off_grid").  k >= n contradicts the
  pigeonhole bound N(n) <= n - 1 -- mathematically impossible, so a valid
  certificate would imply a predicate/judge bug; flagged
  "exceeds_pigeonhole" for mandatory human review.
"""

import argparse
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


def parse_claim_nk(header: str, pattern: str):
    """Match the (whitespace-normalized) header against the pinned pattern;
    return the captured numerals (n, k) or None."""
    m = re.fullmatch(pattern, norm_ws(header))
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def lean_axioms_ok(stdout: str, full_name: str, allowed: set) -> bool:
    return _security.axioms_ok(stdout, full_name, allowed)


def run_lean(app_dir: str, path: str, timeout: int):
    return _security.run_lean(app_dir, path, timeout)


def score_cell(k: int, anchors: dict):
    """Linear per-grid score, uncapped, floored at 0."""
    return max(0.0, (k - anchors["baseline_k"]) /
               (anchors["record_k"] - anchors["baseline_k"]))


def milestone(k: int, anchors: dict):
    if k > anchors["record_k"]:
        return "record_broken"
    if k == anchors["record_k"]:
        return "record_matched"
    if k == anchors["baseline_k"]:
        return "baseline"
    if k < anchors["baseline_k"]:
        return "below_baseline"
    return "progress"


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
    namespace = spec.get("namespace", "MOLS")
    grid = spec.get("grid", {})
    allowed = set(spec.get("allowed_axioms", ["propext", "Classical.choice", "Quot.sound"]))
    min_n, max_n = spec.get("min_n", 2), spec.get("max_n", 30)
    min_k, max_k = spec.get("min_k", 1), spec.get("max_k", 29)
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
    for name in sorted(claims, key=lambda k2: claims[k2][1][0][0]):
        span = claims[name][1][0]
        segments.append(submission[prev:span[0]])
        prev = span[1]
    segments.append(submission[prev:])
    if any(SORRY_OR_ADMIT.search(strip_comments(seg)) for seg in segments):
        return fail("sorry/admit outside claim bodies")

    # ---- parse (n, k), drop sorry claims ----------------------------------------
    scored = {}   # name -> (n, k)
    for name, (c, blk) in claims.items():
        nk = parse_claim_nk(blk[1], c["header_pattern"])
        if nk is None:
            print(f"NOTE: claim {name} header does not match the pinned shape; not scored")
            report["details"].append(f"claim {name}: header tampered or unreadable")
            continue
        n, k = nk
        if not (min_n <= n <= max_n) or not (min_k <= k <= max_k):
            print(f"NOTE: claim {name} (n={n}, k={k}) out of range; not scored")
            continue
        if SORRY_OR_ADMIT.search(strip_comments(blk[2])):
            print(f"NOTE: claim {name} (n={n}, k={k}) still contains sorry/admit; not scored")
            report["claims"][name] = {"n": n, "k": k, "status": "unproven"}
            continue
        scored[name] = (n, k)

    if not scored:
        return fail("no claim is proven (nothing to score)")

    # ---- compile + axioms ---------------------------------------------------------
    tmpdir = tempfile.mkdtemp(prefix="mols-score-")
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
    for name, (n, k) in scored.items():
        full = f"{namespace}.{name}"
        if not lean_axioms_ok(out, full, allowed):
            print(f"claim {name}: FAIL (non-standard axioms)")
            report["claims"][name] = {"n": n, "k": k, "status": "bad_axioms"}
            continue
        anchors = grid.get(str(n))
        if anchors is None:
            s, ms = 0.0, "off_grid"
            report["details"].append(
                f"{name} with n={n}, k={k}: order outside the scoring grid "
                f"{sorted(int(x) for x in grid)} — a valid certificate, unscored")
        else:
            s, ms = score_cell(k, anchors), milestone(k, anchors)
            if k >= n:
                ms = "exceeds_pigeonhole"
        report["claims"][name] = {"n": n, "k": k, "status": "proven",
                                  "score": s, "milestone": ms}
        print(f"claim {name}: PROVEN at n={n}, k={k} -> score {s:.4f}, milestone {ms}")
        if ms == "record_broken":
            msg = (f"{name} with n={n}, k={k} is beyond the published record "
                   f"N({n}) >= {anchors['record_k']}: a new result")
            if n == 10:
                msg += ("; three pairwise orthogonal Latin squares of order 10 "
                        "settle a problem open since Parker 1959 (66 years)")
            report["details"].append(msg)
        if ms == "exceeds_pigeonhole":
            report["details"].append(
                f"{name} with n={n}, k={k} contradicts the pigeonhole bound "
                f"N(n) <= n - 1: at most {n - 1} pairwise orthogonal Latin "
                f"squares of order {n} can exist. A valid such certificate is "
                f"mathematically impossible — far more likely a predicate or "
                f"judge bug; flagged for mandatory human review.")
        best = max(best, s)

    report["reward"] = best
    report["valid"] = 1 if best > 0 or scored else 0
    report["score_mode"] = spec.get("score_mode", "solver_linear_per_grid")
    print(f"reward={best:g} mode={report['score_mode']}")
    write_rewards(best)
    return 0


if __name__ == "__main__":
    sys.exit(main())
