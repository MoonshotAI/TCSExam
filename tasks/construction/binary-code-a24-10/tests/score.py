#!/usr/bin/env python3
"""Verifier for the binary-code-a24-10-lean-open task (open proof: largest
binary error-correcting code of length 24 and minimum Hamming distance 10).
Both directions are scored:

  theorem submission_construction :
      ∃ S : Finset (Fin 24 → Fin 2), MinDist10 S ∧ m ≤ S.card   -- A(24,10) ≥ m
  theorem submission_upper :
      ∀ S : Finset (Fin 24 → Fin 2), MinDist10 S → S.card ≤ k   -- A(24,10) ≤ k

where the agent chooses each numeral and proves at least one claim.

Gates, in order; any failure scores 0:
  1. Submission `Task/Basic.lean` exists.
  2. Fixed part integrity: everything up to the `-- END OF FIXED PART` mark
     must match `tests/reference/Basic.lean` (comments stripped,
     whitespace-normalized).
  3. Lexical anti-cheat on the comment-stripped text: no `axiom` / `sorryAx`,
     and no redefinition or soundness tricks (`notation`, `macro`, `syntax`,
     `elab`, `opaque`, `unsafe`, `extern`, `implemented_by`, `initialize`,
     `skipKernelTC`); `sorry` / `admit` outside the CLAIM-marked bodies
     scores 0 (a claim whose body still contains one is simply not scored).
  4. Statement parse: each claim header must match, up to whitespace, the
     pinned pattern in judge.json with a literal numeral (1..16777216).
  5. Compile the submission plus, per scored claim, a judge consistency
     check that re-states the parsed claim against the *root* `MinDist10`
     and proves it from the agent's theorem; then `#print axioms` of the
     check must stay within the allowed set (standard axioms +
     `Lean.ofReduceBool` / `Lean.trustCompiler`, i.e. `native_decide`).

Scoring (accepted submissions only; reward = max over proven claims),
parameters from judge.json:
  construction (cubic, aligned with the solver sibling binary-code-a24-10):
    m <= 2   -> 0          (trivial baseline: the repetition code {0^24, 1^24})
    m > 2    -> ((m - 2) / (136 - 2))^3
    m = 136  -> 1.0 ("record_matched": Laaksonen–Östergård 2016);
    m >= 137 -> "record_broken" (a new result: A(24,10) >= m), scores above 1
    are not capped; m > 268 contradicts the published SDP upper bound
    (Gijswijt–Mittelmann–Schrijver 2012) and is flagged for human review.
  upper bound (same shape, mirrored anchors; designed anchors):
    k >= 1295 -> 0         (trivial: sphere-packing bound floor(2^24/12951))
    k < 1295  -> ((1295 - k) / (1295 - 268))^3
    k = 268  -> 1.0 ("record_matched": Gijswijt–Mittelmann–Schrijver 2012);
    k <= 267 -> "record_broken" (a new result: A(24,10) <= k), scores above 1
    are not capped; k < 136 contradicts the published record construction
    (Laaksonen–Östergård 2016) and is flagged for human review.
The reward file receives the score; a JSON sidecar next to it records the
full verdict (accepted, per-claim status, reason).
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


FIXED_END_MARK_DEFAULT = "-- END OF FIXED PART"
SORRY_OR_ADMIT = re.compile(r"\b(sorry|admit)\b")


def strip_comments(text: str) -> str:
    return _security.strip_comments(text)


def norm_ws(text: str) -> str:
    return " ".join(text.split())


def fixed_part(text: str, mark: str):
    """Everything up to and including the standalone mark line.

    The mark must anchor on a line of its own: the file's docstring also
    mentions `-- END OF FIXED PART` inline (in backticks), and a plain
    `str.find` would match that first and silently truncate the check.
    """
    m = re.search(r"(?m)^" + re.escape(mark) + r"\s*$", text)
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


def parse_claim_n(header: str, pattern: str):
    """Match the (whitespace-normalized) header against the pinned pattern;
    return the captured numeral or None."""
    m = re.fullmatch(pattern, norm_ws(header))
    if not m:
        return None
    return int(m.group(1))


def lean_axioms_ok(output: str, full_name: str, allowed: set) -> bool:
    return _security.axioms_ok(output, full_name, allowed)


def score_construction(m: int, cfg: dict):
    """Return (alpha, record_broken, milestone) for a size-m code."""
    triv, rec = cfg["trivial_m"], cfg["record_m"]
    op, val = cfg["record_broken"].split()[1:]
    val = int(val)
    rb = (m >= val) if op == ">=" else (m <= val)
    alpha = 0.0 if m <= triv else ((m - triv) / (rec - triv)) ** 3
    if m > cfg["proven_upper_bound_m"]:
        ms = "above_proven_upper_bound"
    elif rb:
        ms = "record_broken"
    elif m == rec:
        ms = "record_matched"
    elif m > triv:
        ms = "progress"
    else:
        ms = "baseline"
    return alpha, rb, ms


def score_upper(k: int, cfg: dict):
    """Return (alpha, record_broken, milestone) for a proven upper bound k."""
    base, rec = cfg["baseline_k"], cfg["record_k"]
    op, val = cfg["record_broken"].split()[1:]
    val = int(val)
    rb = (k <= val) if op == "<=" else (k >= val)
    alpha = 0.0 if k >= base else ((base - k) / (base - rec)) ** 3
    if k < cfg["proven_lower_bound_k"]:
        ms = "below_proven_lower_bound"
    elif rb:
        ms = "record_broken"
    elif k == rec:
        ms = "record_matched"
    elif k < base:
        ms = "progress"
    else:
        ms = "baseline"
    return alpha, rb, ms


def run_lean(cwd: str, path: str, timeout: int):
    return _security.run_lean(cwd, path, timeout)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", default=os.environ.get("APP_DIR", "/app"))
    ap.add_argument("--tests", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--reward", default=os.environ.get("REWARD_FILE", "/logs/verifier/reward.txt"))
    ap.add_argument("--lake-cwd", default=None,
                    help="directory to run `lake env lean` in (default: --app)")
    ap.add_argument("--lean-timeout", type=int,
                    default=int(os.environ.get("JUDGE_LEAN_TIMEOUT", "1200")))
    args = ap.parse_args()
    lake_cwd = args.lake_cwd or args.app

    result = {"accepted": False, "reward": 0.0, "claims": {},
              "record_broken": False, "reason": ""}

    def finish(reason: str, alpha: float = 0.0) -> None:
        result["reason"] = reason
        result["reward"] = alpha
        os.makedirs(os.path.dirname(args.reward), exist_ok=True)
        with open(args.reward, "w") as f:
            f.write(f"{alpha:g}")
        sidecar = os.path.join(os.path.dirname(args.reward), "judge_result.json")
        with open(sidecar, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"reward={alpha:g} reason={reason}")
        print(json.dumps(result, ensure_ascii=False))

    with open(os.path.join(args.tests, "judge.json")) as f:
        spec = json.load(f)
    mark = spec.get("fixed_end_mark", FIXED_END_MARK_DEFAULT)
    allowed_axioms = set(spec["allowed_axioms"])
    forbidden = re.compile(r"\b(" + "|".join(re.escape(t) for t in spec["forbidden_tokens"]) + r")\b")
    min_n, max_n = spec.get("min_n", 1), spec.get("max_n", 16777216)

    sub_path = os.path.join(args.app, "Task", "Basic.lean")
    try:
        with open(sub_path) as f:
            submission = f.read()
    except OSError:
        finish("no submission Task/Basic.lean")
        return 0

    source_error = _security.source_error(submission, allow_native=True)
    if source_error:
        finish(source_error)
        return 0

    # ---- fixed part integrity ---------------------------------------------
    with open(os.path.join(args.tests, "reference", "Basic.lean")) as f:
        reference = f.read()

    ref_fixed = fixed_part(reference, mark)
    sub_fixed = fixed_part(submission, mark)
    if ref_fixed is None or sub_fixed is None or norm_ws(strip_comments(ref_fixed)) != norm_ws(strip_comments(sub_fixed)):
        finish("fixed code layer missing or tampered (comments are free)")
        return 0

    # ---- locate claim blocks ------------------------------------------------
    claims = {}
    for c in spec["claims"]:
        blk = find_claim_block(submission, c["name"])
        if blk is None:
            print(f"NOTE: claim {c['name']} not present (direction not attempted)")
            continue
        claims[c["name"]] = (c, blk)

    # ---- lexical anti-cheat --------------------------------------------------
    stripped = strip_comments(submission)
    bad = forbidden.search(stripped)
    if bad:
        finish(f"forbidden token: {bad.group(1)}")
        return 0

    # sorry/admit outside claim bodies?
    segments = []
    prev = 0
    for name in sorted(claims, key=lambda k: claims[k][1][0][0]):
        span = claims[name][1][0]
        segments.append(submission[prev:span[0]])
        prev = span[1]
    segments.append(submission[prev:])
    if any(SORRY_OR_ADMIT.search(strip_comments(seg)) for seg in segments):
        finish("sorry/admit outside claim bodies")
        return 0

    # ---- parse numerals, drop sorry claims ------------------------------------
    scored = {}   # name -> (claim spec, n)
    for name, (c, blk) in claims.items():
        n = parse_claim_n(blk[1], c["header_pattern"])
        if n is None:
            print(f"NOTE: claim {name} header does not match the pinned shape; not scored")
            result["claims"][name] = {"status": "header_mismatch"}
            continue
        if not (min_n <= n <= max_n):
            print(f"NOTE: claim {name} numeral {n} out of range [{min_n}, {max_n}]; not scored")
            result["claims"][name] = {"status": "numeral_out_of_range", "n": n}
            continue
        if SORRY_OR_ADMIT.search(strip_comments(blk[2])):
            print(f"NOTE: claim {name} (n={n}) still contains sorry/admit; not scored")
            result["claims"][name] = {"status": "unproven", "n": n}
            continue
        scored[name] = (c, n)

    if not scored:
        finish("no claim is proven (nothing to score)")
        return 0

    # ---- compile + consistency check + axiom check ----------------------------
    canonical = spec["statement_templates"]
    check_names = {}
    tmpdir = tempfile.mkdtemp(prefix="a24-score-")
    check_path = os.path.join(tmpdir, "JudgeCheck.lean")
    with open(check_path, "w") as f:
        f.write(submission)
        for name, (c, n) in scored.items():
            direction = c["direction"]
            check_stmt = norm_ws(canonical[direction]).replace(
                "MinDist10", "_root_.MinDist10").replace("{k}", str(n))
            check_name = f"binary_code_judge_check_{name}"
            check_names[name] = check_name
            f.write(f"\n\ntheorem {check_name} : {check_stmt} := {name}\n")
            f.write(_security.axiom_audit(check_name, allow_native=True))
    ok, out = run_lean(lake_cwd, check_path, args.lean_timeout)
    if not ok:
        print("compile failed:")
        print("\n".join(out.splitlines()[-25:]))
        finish("compilation failed (or judge consistency check did not typecheck)")
        return 0
    for name, check_name in check_names.items():
        if not lean_axioms_ok(out, check_name, allowed_axioms):
            print("\n".join(out.splitlines()[-10:]))
            finish(f"axiom whitelist violated (claim {name})")
            return 0

    # ---- scoring --------------------------------------------------------------
    best = 0.0
    for name, (c, n) in scored.items():
        direction = c["direction"]
        if direction == "construction":
            alpha, rb, ms = score_construction(n, spec["scoring"]["construction"])
        else:
            alpha, rb, ms = score_upper(n, spec["scoring"]["upper"])
        result["claims"][name] = {"direction": direction, "n": n, "status": "proven",
                                  "alpha": alpha, "milestone": ms, "record_broken": rb}
        print(f"claim {name}: PROVEN at n={n} ({direction}) -> alpha {alpha:.6g}, milestone {ms}")
        result["record_broken"] = result["record_broken"] or rb
        best = max(best, alpha)

    result["accepted"] = True
    reason = "accepted" + (" (RECORD BROKEN)" if result["record_broken"] else "")
    flagged = {n: c for n, c in result["claims"].items()
               if c.get("milestone") in ("below_proven_lower_bound", "above_proven_upper_bound")}
    if flagged:
        reason += (" (CONTRADICTS A PUBLISHED BOUND: implies a checker or "
                   "formalization bug; flagged for mandatory human review: "
                   + ", ".join(sorted(flagged)) + ")")
    finish(reason, best)
    return 0


if __name__ == "__main__":
    sys.exit(main())
