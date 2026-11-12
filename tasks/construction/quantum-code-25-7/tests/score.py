#!/usr/bin/env python3
"""Verifier for the quantum-code-25-7-lean-open task (open proof: the best
qubit stabilizer code [[25,7]] — largest minimum distance).

The submission is `/app/Task/Basic.lean`: a fixed definition layer
(`Pauli25` as two `BitVec 25` masks; `IsStabilizer` = pairwise commutation
+ GF(2) rank 18; `DistanceGE gens d` = exact distance-at-least-d check in
the N(S) \\ S semantics: exhaustive weight sweep with membership in the
generated group; checked with comments stripped) plus one claim theorem between CLAIM
markers

  theorem submission : ∃ gens : Fin 18 → Pauli25, IsStabilizer gens ∧ DistanceGE gens d

where the agent chooses the numeral `d` — the larger the better. A proven
claim certifies that a [[25,7,d]] quantum code exists.

Gates, in order; any failure scores 0:
  1. Submission `Task/Basic.lean` exists.
  2. Fixed part integrity: everything up to the `-- END OF FIXED PART` mark
     must match `tests/reference/Basic.lean` (comments stripped,
     whitespace-normalized).
  3. Lexical anti-cheat on the comment-stripped text: no `axiom` /
     `sorryAx`, and no redefinition or soundness tricks (`notation`,
     `macro`, `syntax`, `elab`, `opaque`, `unsafe`, `extern`,
     `implemented_by`, `initialize`, `skipKernelTC`) anywhere;
     `sorry` / `admit` only inside the CLAIM-marked body. `native_decide`
     is allowed.
  4. Statement parse: the claim header must match, up to whitespace, the
     pinned template in judge.json with a literal numeral; a body that
     still contains sorry/admit is simply not scored.
  5. Compile the submission plus a judge consistency check that re-states
     the parsed claim against the *root* `IsStabilizer` / `DistanceGE` and
     proves it from the agent's theorem; then `#print axioms` of the check
     must stay within the allowed set (standard axioms +
     `Lean.ofReduceBool` / `Lean.trustCompiler`, i.e. `native_decide`).

Scoring (accepted submissions only), parameters from judge.json; identical
curve to the solver sibling task quantum-code-25-7:
  d <= 1 -> 0 (trivial [[25,7,1]] baseline: 18 ancillas pinned to |0>);
  ((d - 1) / 4)^3 otherwise, uncapped; d = 5 -> 1.0 ("record_matched",
  codetables.de entry standing since 2005-06-24); d = 6 ->
  "record_broken" (a new literature-level lower bound); d = 7 ->
  "closed" (meets the proven Rains quantum LP upper bound — the parameter
  point is settled exactly); d >= 8 contradicts the proven upper bound and
  is flagged "above_proven_upper_bound" for mandatory human review.
The reward file receives the score; a JSON sidecar next to it records the
full verdict (accepted, claim, d, score, milestone, reason).
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
STANDARD_EXTRA = {"Lean.ofReduceBool", "Lean.trustCompiler"}
SORRY_OR_ADMIT = re.compile(r"\b(sorry|admit)\b")


def strip_comments(text: str) -> str:
    return _security.strip_comments(text)


def norm_ws(text: str) -> str:
    return " ".join(text.split())


def squash(text: str) -> str:
    """Remove all whitespace (for template matching)."""
    return "".join(text.split())


def template_regex(template: str) -> "re.Pattern":
    """Build a full-match regex from a whitespace-free template with {k}."""
    body = re.escape(squash(template)).replace(re.escape("{k}"), r"(\d+)")
    return re.compile(body + r"\Z")


def fixed_part(text: str, mark: str):
    """Everything up to and including the standalone FIXED_END_MARK line.

    The mark must anchor on a line of its own: the file's docstring also
    mentions the mark inline (in backticks), and a plain `str.find` would
    match that first and silently truncate the check.
    """
    m = re.search(r"(?m)^" + re.escape(mark) + r"\s*$", text)
    if m is None:
        return None
    nl = text.find("\n", m.start())
    return text[: (nl + 1) if nl != -1 else len(text)]


def find_claim_block(text: str, name: str):
    """Locate `theorem <name>` with its CLAIM BEGIN/END markers.

    Returns (block_span, header_text, body_text) or None. Header is the
    text between `theorem <name>` and the first `:=` before the BEGIN
    mark; body is the text between the BEGIN and END marker lines.
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


def lean_axioms_ok(output: str, full_name: str, allowed: set) -> bool:
    return _security.axioms_ok(output, full_name, allowed)


def score_lower(m: int, cfg: dict):
    """Return (alpha, record_broken, milestone) for a proven distance m."""
    base, rec = cfg["baseline_m"], cfg["record_m"]
    rb = m >= cfg["record_broken_from"]
    alpha = 0.0 if m <= base else ((m - base) / (rec - base)) ** 3
    if m > cfg["proven_upper_bound_m"]:
        ms = "above_proven_upper_bound"
    elif "closed_at" in cfg and m == cfg["closed_at"]:
        ms = "closed"
    elif rb:
        ms = "record_broken"
    elif m == rec:
        ms = "record_matched"
    elif m > base:
        ms = "progress"
    else:
        ms = "baseline"
    return alpha, rb, ms


def score_upper(k: int, cfg: dict):
    """Return (alpha, record_broken, milestone) for a proven upper bound k.
    (Unused by this task; kept for template symmetry.)"""
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
                    default=int(os.environ.get("JUDGE_LEAN_TIMEOUT", "1500")))
    args = ap.parse_args()
    lake_cwd = args.lake_cwd or args.app

    result = {"accepted": False, "claims": {}, "alpha": 0.0,
              "record_broken": False, "milestone": "invalid", "reason": ""}

    def finish(reason: str, alpha: float = 0.0) -> None:
        result["reason"] = reason
        result["alpha"] = alpha
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
    allowed_axioms = set(spec["allowed_axioms"]) | STANDARD_EXTRA
    forbidden = re.compile(r"\b(" + "|".join(re.escape(t) for t in spec["forbidden_tokens"]) + r")\b")
    compile_timeout = int(spec.get("compile_timeout_sec", args.lean_timeout))
    root_pins = spec.get("root_pins", [])

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
    ref_fixed, sub_fixed = fixed_part(reference, mark), fixed_part(submission, mark)
    if ref_fixed is None or sub_fixed is None or norm_ws(strip_comments(ref_fixed)) != norm_ws(strip_comments(sub_fixed)):
        finish("fixed code layer missing or tampered (comments are free)")
        return 0

    # ---- lexical anti-cheat --------------------------------------------------
    stripped = strip_comments(submission)
    bad = forbidden.search(stripped)
    if bad:
        finish(f"forbidden token: {bad.group(1)}")
        return 0

    # ---- locate claim blocks ---------------------------------------------------
    claims = {}
    for c in spec["claims"]:
        blk = find_claim_block(submission, c["name"])
        if blk is None:
            print(f"NOTE: claim {c['name']} not present (direction not attempted)")
            continue
        claims[c["name"]] = (c, blk)

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

    # ---- parse numerals, drop sorry claims --------------------------------------
    scored = {}   # name -> (claim spec, n)
    for name, (c, blk) in claims.items():
        stmt_sq = squash(blk[1]).lstrip(":")
        rx = template_regex(c["header_template"])
        m = rx.match(stmt_sq)
        if not m:
            print(f"NOTE: claim {name} header does not match the pinned shape; not scored")
            result["claims"][name] = {"status": "header_mismatch"}
            continue
        n = int(m.group(1))
        if not (1 <= n <= int(c.get("max_n", 4096))):
            print(f"NOTE: claim {name} numeral {n} out of range; not scored")
            result["claims"][name] = {"n": n, "status": "out_of_range"}
            continue
        if SORRY_OR_ADMIT.search(strip_comments(blk[2])):
            print(f"NOTE: claim {name} (n={n}) still contains sorry/admit; not scored")
            result["claims"][name] = {"n": n, "status": "unproven"}
            continue
        scored[name] = (c, n)

    if not scored:
        finish("no claim is proven (nothing to score)")
        return 0

    # ---- compile + consistency check + axiom check --------------------------------
    tmpdir = tempfile.mkdtemp(prefix="qc257-score-")
    check_path = os.path.join(tmpdir, "JudgeCheck.lean")
    check_names = {}
    with open(check_path, "w") as f:
        f.write(submission)
        for name, (c, n) in scored.items():
            check_stmt = norm_ws(c["header_template"])
            for pin in root_pins:
                check_stmt = check_stmt.replace(pin, f"_root_.{pin}")
            check_stmt = check_stmt.replace("{k}", str(n))
            check_name = f"qc257_judge_check_{name}"
            check_names[name] = check_name
            f.write(f"\n\ntheorem {check_name} : {check_stmt} := {name}\n")
            f.write(_security.axiom_audit(check_name, allow_native=True))
    ok, out = run_lean(lake_cwd, check_path, compile_timeout)
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
    best, best_ms = 0.0, "baseline"
    for name, (c, n) in scored.items():
        if c["direction"] == "upper":
            alpha, rb, ms = score_upper(n, spec["scoring"]["upper"])
        else:
            alpha, rb, ms = score_lower(n, spec["scoring"]["lower"])
        result["claims"][name] = {"direction": c["direction"], "d": n,
                                  "status": "proven", "score": alpha,
                                  "milestone": ms, "record_broken": rb}
        print(f"claim {name}: PROVEN at d={n} ({c['direction']}) -> "
              f"score {alpha:.6f}, milestone {ms}")
        if rb:
            result["record_broken"] = True
        if alpha > best:
            best, best_ms = alpha, ms

    result.update(accepted=True, alpha=best, milestone=best_ms)
    reason = "accepted" + (" (RECORD BROKEN)" if result["record_broken"] else "")
    flagged = {v["milestone"] for v in result["claims"].values()
               if v.get("status") == "proven"}
    if "closed" in flagged:
        reason += (" (CLOSED: d = 7 meets the proven Rains quantum LP upper "
                   "bound — the best [[25,7]] code is settled exactly)")
    if "above_proven_upper_bound" in flagged:
        reason += (" (ABOVE PROVEN UPPER BOUND 7: contradicts the proven "
                   "Rains quantum LP bound; implies a checker or formalization "
                   "bug — flagged for mandatory human review)")
    finish(reason, best)
    return 0


if __name__ == "__main__":
    sys.exit(main())
