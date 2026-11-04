#!/usr/bin/env python3
"""Verifier for cage-girth-lean-open: a Lean 4 certificate that a k-regular
graph of girth >= g exists on at most N vertices (a machine-checked upper
bound on the cage number n(k,g)).

The submission is `/app/Task/Basic.lean`: a fixed definition layer
(`CageGraph`, `WellFormed`, `IsKRegular`, `GirthGE`; checked with comments stripped) plus
one claim theorem

  theorem submission_lower :
    ∃ G : CageGraph, WellFormed G ∧ IsKRegular G k ∧ GirthGE G g ∧ G.n ≤ N

where the agent chooses the numerals k, g (one of the scoring cells) and N
(the smaller the better) and proves the claim.

Pipeline mirrors kissing-d9-lean-open: fixed-part integrity, claim-block
location, lexical anti-cheat (`axiom` / `sorryAx` anywhere, `sorry`/`admit`
outside the claim body), compile with a `#print axioms` probe, axiom
whitelist (standard axioms + Lean.ofReduceBool + Lean.trustCompiler --
`native_decide` IS the intended certificate path here), parse (k, g, N)
from the claim header, score.

Scoring (linear, uncapped; anchors per cell, shared with the solver sibling
task cage-girth):
  score(N) = 0                      for N >= B
  score(N) = (B - N) / (B - K)      for N < B
  N = K   -> 1.0 ("record_matched")
  N < K   -> > 1.0, "record_broken" (a literature-level new result)
  N = LB  -> "cell_closed" (proves n(k,g) = LB, a literature-level result)
  N < LB  -> "below_published_lower_bound": would contradict a published
             theorem; flagged for mandatory human review
The (3,5) cell is closed (n(3,5) = 10, the Petersen graph); sanity anchor,
always scores 0.
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


def parse_claim_cell(header: str, pattern: str):
    """Match the (whitespace-normalized) header against the pinned pattern;
    return (k, g, N) or None."""
    m = re.fullmatch(pattern, norm_ws(header))
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def lean_axioms_ok(stdout: str, full_name: str, allowed: set) -> bool:
    return _security.axioms_ok(stdout, full_name, allowed)


def run_lean(app_dir: str, path: str, timeout: int):
    return _security.run_lean(app_dir, path, timeout)


def score_cell(cfg: dict, n: int):
    """Linear down-score for one cell; returns (score, milestone)."""
    if cfg.get("sanity"):
        return 0.0, "sanity"
    B, K, LB = cfg["baseline_n"], cfg["record_n"], cfg["lower_bound_n"]
    s = 0.0 if n >= B else (B - n) / (B - K)
    if n < LB:
        ms = "below_published_lower_bound"
    elif n == LB:
        ms = "cell_closed"
    elif n < K:
        ms = "record_broken"
    elif n == K:
        ms = "record_matched"
    elif n < B:
        ms = "progress"
    else:
        ms = "baseline"
    return s, ms


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
    namespace = spec.get("namespace", "Cage")
    allowed = set(spec.get("allowed_axioms", ["propext", "Classical.choice", "Quot.sound"]))
    min_n = spec.get("min_n", 1)
    compile_timeout = int(spec.get("compile_timeout_sec", 1200))
    cells = spec["cells"]

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

    # ---- parse (k, g, N), drop sorry claims -------------------------------------
    scored = {}   # name -> (k, g, n)
    for name, (c, blk) in claims.items():
        header = blk[1]
        parsed = parse_claim_cell(header, c["header_pattern"])
        if parsed is None:
            print(f"NOTE: claim {name} header does not match the pinned shape; not scored")
            report["details"].append(f"claim {name}: header tampered or unreadable")
            continue
        k, g, n = parsed
        cell = cells.get(f"{k},{g}")
        if cell is None:
            print(f"NOTE: claim {name} targets unsupported cell ({k},{g}); not scored")
            report["details"].append(
                f"claim {name}: ({k},{g}) is not a scoring cell; allowed: "
                + ", ".join(sorted(cells)))
            continue
        max_n = 2 * cell["baseline_n"]
        if not (min_n <= n <= max_n):
            print(f"NOTE: claim {name} N={n} out of range [{min_n}, {max_n}]; not scored")
            continue
        if SORRY_OR_ADMIT.search(strip_comments(blk[2])):
            print(f"NOTE: claim {name} (cell ({k},{g}), N={n}) still contains sorry/admit; not scored")
            report["claims"][name] = {"cell": [k, g], "n": n, "status": "unproven"}
            continue
        scored[name] = (k, g, n)

    if not scored:
        return fail("no claim is proven (nothing to score)")

    # ---- compile + axioms ---------------------------------------------------------
    tmpdir = tempfile.mkdtemp(prefix="cage-score-")
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
    for name, (k, g, n) in scored.items():
        full = f"{namespace}.{name}"
        if not lean_axioms_ok(out, full, allowed):
            print(f"claim {name}: FAIL (non-standard axioms)")
            report["claims"][name] = {"cell": [k, g], "n": n, "status": "bad_axioms"}
            continue
        cell = cells[f"{k},{g}"]
        s, ms = score_cell(cell, n)
        report["claims"][name] = {"cell": [k, g], "n": n, "status": "proven",
                                  "score": s, "milestone": ms}
        print(f"claim {name}: PROVEN cell ({k},{g}) at N={n} -> score {s:.4f}, milestone {ms}")
        K, LB = cell.get("record_n"), cell.get("lower_bound_n")
        if ms == "record_broken":
            report["details"].append(
                f"{name} with N={n} beats the record {K} for cell ({k},{g}): "
                f"n({k},{g}) <= {n}, a literature-level new result")
        if ms == "cell_closed":
            report["details"].append(
                f"{name} with N={n} reaches the published lower bound {LB}: "
                f"proves n({k},{g}) = {n}, closing the cell — a literature-level result")
        if ms == "below_published_lower_bound":
            report["details"].append(
                f"{name} with N={n} is below the published lower bound "
                f"n({k},{g}) >= {LB}. If the certificate is sound this "
                "contradicts a published theorem — far more likely a "
                "checker/judge bug; flagged for mandatory human review.")
        best = max(best, s)

    report["reward"] = best
    report["valid"] = 1 if best > 0 or scored else 0
    report["score_mode"] = "solver_linear"
    print(f"reward={best:g} mode=solver_linear")
    write_rewards(best)
    return 0


if __name__ == "__main__":
    sys.exit(main())
