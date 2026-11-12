#!/usr/bin/env python3
"""Verifier for the capset-d7-lean task (open proof: dimension-7 cap set).

Gates, in order; any failure scores 0:
  1. Submission `Task/Basic.lean` exists.
  2. Fixed part integrity: everything up to the `-- END OF FIXED PART` mark
     must match `tests/reference/Basic.lean` (comments stripped,
     whitespace-normalized).
  3. Lexical anti-cheat on the comment-stripped text: no `axiom` / `sorryAx` /
     `sorry` / `admit`, and no redefinition or soundness tricks (`notation`,
     `macro`, `syntax`, `elab`, `opaque`, `unsafe`, `extern`,
     `implemented_by`, `initialize`, `skipKernelTC`).
  4. Statement parse: a top-level (namespace depth 0) theorem
     `capset_d7_main` whose statement matches, up to whitespace, exactly one
     of the two templates in judge.json with a literal numeral k:
       construction: `∃ S : Finset (Fin 7 → ZMod 3), IsCap S ∧ S.card ≥ k`
       upper bound:  `¬ ∃ S : Finset (Fin 7 → ZMod 3), IsCap S ∧ S.card ≥ k`
  5. Compile the submission plus a judge consistency check that re-states the
     parsed claim against the *root* `IsCap` and proves it from the agent's
     theorem; then `#print axioms` of the check must stay within the allowed
     set (standard axioms + `Lean.ofReduceBool`, i.e. `native_decide`).

Scoring (accepted submissions only), milestones from judge.json:
  construction: alpha = max((k - 128) / (236 - 128), 0), uncapped above 1;
                k >= 237 sets record_broken (published record: 236).
  upper bound:  alpha = max((2188 - k) / (2188 - 289), 0), uncapped above 1;
                k <= 288 sets record_broken (published bound: no 289-cap).
The reward file receives alpha; a JSON sidecar next to it records the full
verdict (accepted, direction, k, alpha, record_broken, reason).
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


def find_main_theorem(stripped: str, name: str):
    """Locate `theorem <name>` at namespace depth 0; return its statement
    text (between the name and the first `:=`), or None."""
    declaration = re.compile(r"[ \t]*theorem\s+" + re.escape(name) + r"\b")
    depth = 0
    for m in re.finditer(r"(?m)^[^\n]*$", stripped):
        line = m.group(0)
        tm = declaration.match(stripped, m.start())
        if tm:
            if depth != 0:
                return None
            rest = stripped[tm.end():]
            ci = rest.find(":=")
            if ci == -1:
                return None
            return rest[:ci]
        if re.match(r"\s*namespace\b", line):
            depth += 1
        elif re.match(r"\s*end\b", line):
            depth = max(0, depth - 1)
    return None


def lean_axioms_ok(output: str, full_name: str, allowed: set) -> bool:
    return _security.axioms_ok(output, full_name, allowed)


def milestone(direction: str, k: int, spec: dict):
    """Return (alpha, record_broken) for the given direction and k."""
    m = spec["milestones"][direction]
    base, rec = m["baseline_k"], m["record_k"]
    op, val = m["record_broken"].split()[1:]
    val = int(val)
    rb = (k >= val) if op == ">=" else (k <= val)
    if direction == "construction":
        alpha = (k - base) / (rec - base)
    else:
        alpha = (base - k) / (base - rec)
    # No cap at 1.0: going past the record must outscore matching it.
    return max(alpha, 0.0), rb


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

    result = {"accepted": False, "direction": None, "k": None,
              "alpha": 0.0, "record_broken": False, "reason": ""}

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
    name = spec.get("main_theorem", "capset_d7_main")
    mark = spec.get("fixed_end_mark", FIXED_END_MARK_DEFAULT)
    allowed_axioms = set(spec["allowed_axioms"]) | STANDARD_EXTRA
    forbidden = re.compile(r"\b(" + "|".join(re.escape(t) for t in spec["forbidden_tokens"]) + r")\b")
    templates = {d: template_regex(t) for d, t in spec["statement_templates"].items()}
    canonical = spec["statement_templates"]

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

    def fixed_part(text: str):
        idx = text.find(mark)
        if idx == -1:
            return None
        nl = text.find("\n", idx)
        return text[: (nl + 1) if nl != -1 else len(text)]

    ref_fixed, sub_fixed = fixed_part(reference), fixed_part(submission)
    if ref_fixed is None or sub_fixed is None or norm_ws(strip_comments(ref_fixed)) != norm_ws(strip_comments(sub_fixed)):
        finish("fixed code layer missing or tampered (comments are free)")
        return 0

    # ---- lexical anti-cheat --------------------------------------------------
    stripped = strip_comments(submission)
    bad = forbidden.search(stripped)
    if bad:
        finish(f"forbidden token: {bad.group(1)}")
        return 0

    # ---- statement parse ------------------------------------------------------
    stmt = find_main_theorem(stripped, name)
    if stmt is None:
        finish(f"top-level theorem {name} not found (or inside a namespace)")
        return 0
    stmt_sq = squash(stmt).lstrip(":")
    direction, k = None, None
    for d, rx in templates.items():
        m = rx.match(stmt_sq)
        if m:
            direction, k = d, int(m.group(1))
            break
    if direction is None:
        finish(f"statement of {name} does not match either template")
        return 0

    # ---- compile + axiom check --------------------------------------------------
    # canonical statement with single spaces and rooted IsCap (namespace-proof)
    check_stmt = norm_ws(canonical[direction]).replace("IsCap", "_root_.IsCap").replace("{k}", str(k))
    check_name = "capset_judge_check"
    tmpdir = tempfile.mkdtemp(prefix="capset-score-")
    check_path = os.path.join(tmpdir, "JudgeCheck.lean")
    with open(check_path, "w") as f:
        f.write(submission)
        f.write(f"\n\ntheorem {check_name} : {check_stmt} := {name}\n")
        f.write(_security.axiom_audit(check_name, allow_native=True))
    ok, out = run_lean(lake_cwd, check_path, args.lean_timeout)
    if not ok:
        print("compile failed:")
        print("\n".join(out.splitlines()[-25:]))
        finish("compilation failed (or judge consistency check did not typecheck)")
        return 0
    if not lean_axioms_ok(out, check_name, allowed_axioms):
        print("\n".join(out.splitlines()[-10:]))
        finish("axiom whitelist violated")
        return 0

    # ---- milestones --------------------------------------------------------------
    alpha, rb = milestone(direction, k, spec)
    result.update(accepted=True, direction=direction, k=k, record_broken=rb)
    finish("accepted" + (" (RECORD BROKEN)" if rb else ""), alpha)
    return 0


if __name__ == "__main__":
    sys.exit(main())
