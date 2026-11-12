#!/usr/bin/env python3
"""Verifier for ramsey-r46-lean (open-proof: no ground truth, no checkpoints).

The submission is `/app/Task/Basic.lean`: a fixed definition layer
(`Coloring`, `MonoFree`; checked with comments stripped) plus two claim theorems

  theorem submission_lower : ∃ c : Coloring N, MonoFree c      -- R(4,6) >= N+1
  theorem submission_upper : ∀ c : Coloring N, ¬ MonoFree c    -- R(4,6) <= N

where the agent chooses each numeral N and proves at least one claim.

Chain:
  1. lexical gate (comment-stripped): `axiom` / `sorryAx` anywhere -> 0;
     `sorry` / `admit` outside the CLAIM-marked bodies -> 0; fixed definition code tampered -> 0 (comments are free). (`native_decide` is allowed in this
     task; its axioms are whitelisted instead.)
  2. parse each claim header with a pinned pattern (only the numeral is
     free) to read N; a claim whose body still contains sorry/admit is
     simply not scored.
  3. compile the submission unchanged (plus one `#print axioms` line per
     scored claim) with `lake env lean`; every scored claim must depend
     only on whitelisted axioms (propext, Classical.choice, Quot.sound,
     Lean.ofReduceBool, Lean.trustCompiler).
  4. score each direction from its N (see judge.json; two modes, default
     `solver_cubic`), reward = max over proven claims.

Scoring, mode `solver_cubic` (default; parity with the solver sibling
ramsey-r46 for the lower direction, mirrored for the upper):
  lower: N < 4   -> 0      (vacuous: K_<4 has no 4-subsets)
         N <= 24 -> 0      (baseline: valid colorings exist since R(4,5)=25)
         else ((N-24)/11)^3 (N=35 -> 1.0 "record_matched", Exoo 2012;
                            N>=36 -> > 1, uncapped, "record_broken")
  upper: N >= 56 -> 0      (Erdos-Szekeres trivial bound C(8,3)=56)
         else ((56-N)/15)^3 (N=41 -> 1.0 "record_matched", formally
                            published bound McKay-Radziszowski 1997;
                            N<=40 -> > 1, uncapped, "record_broken";
                            N=40 ties the survey-reported claim,
                            Angeltveit-McKay 2024 pers. comm.)
Mode `alpha_milestone` (any verified non-vacuous claim earns the alpha
credit, the record anchors only add uncapped bonus):
  lower: N < 4 -> 0; 4..35 -> 1.0; N >= 36 -> ((N-24)/11)^3 (> 1)
  upper: N >= 41 -> 1.0 (N > 41 is weaker than the literature but still a
         verified proof); N <= 40 -> ((56-N)/15)^3 (> 1)
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


def parse_claim_n(header: str, pattern: str):
    """Match the (whitespace-normalized) header against the pinned pattern;
    return the captured numeral N or None."""
    m = re.fullmatch(pattern, norm_ws(header))
    if not m:
        return None
    return int(m.group(1))


def lean_axioms_ok(stdout: str, full_name: str, allowed: set) -> bool:
    return _security.axioms_ok(stdout, full_name, allowed)


def run_lean(app_dir: str, path: str, timeout: int):
    return _security.run_lean(app_dir, path, timeout)


def score_lower(n: int, mode: str, cfg: dict):
    rec, base = cfg["record_n"], cfg["baseline_n"]
    if n < cfg["vacuous_below"]:
        return 0.0, "vacuous"
    if mode == "solver_cubic":
        s = 0.0 if n <= base else ((n - base) / (rec - base)) ** 3
    else:  # alpha_milestone
        s = 1.0 if n <= rec else ((n - base) / (rec - base)) ** 3
    if n >= cfg["record_broken_from"]:
        ms = "record_broken"
    elif n == rec:
        ms = "record_matched"
    elif mode == "solver_cubic" and n <= base:
        ms = "baseline"
    elif mode == "solver_cubic":
        ms = "progress"
    else:
        ms = "verified"
    return s, ms


def score_upper(n: int, mode: str, cfg: dict):
    rec, triv = cfg["record_n"], cfg["trivial_n"]
    if mode == "solver_cubic":
        s = 0.0 if n >= triv else ((triv - n) / (triv - rec)) ** 3
    else:  # alpha_milestone
        s = 1.0 if n >= rec else ((triv - n) / (triv - rec)) ** 3
    if n < cfg["record_n"]:
        ms = "record_broken"
    elif n == rec:
        ms = "record_matched"
    elif mode == "solver_cubic" and n >= triv:
        ms = "baseline"
    elif mode == "solver_cubic":
        ms = "progress"
    else:
        ms = "verified"
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
    namespace = spec.get("namespace", "R46")
    mode = spec.get("score_mode", "solver_cubic")
    allowed = set(spec.get("allowed_axioms", [
        "propext", "Classical.choice", "Quot.sound",
        "Lean.ofReduceBool", "Lean.trustCompiler"]))
    min_n, max_n = spec.get("min_n", 1), spec.get("max_n", 64)
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

    # ---- parse N, drop sorry claims ---------------------------------------------
    scored = {}   # name -> (direction, n)
    for name, (c, blk) in claims.items():
        header = blk[1]
        n = parse_claim_n(header, c["header_pattern"])
        if n is None:
            print(f"NOTE: claim {name} header does not match the pinned shape; not scored")
            report["details"].append(f"claim {name}: header tampered or unreadable")
            continue
        if not (min_n <= n <= max_n):
            print(f"NOTE: claim {name} N={n} out of range [{min_n}, {max_n}]; not scored")
            continue
        if SORRY_OR_ADMIT.search(strip_comments(blk[2])):
            print(f"NOTE: claim {name} (N={n}) still contains sorry/admit; not scored")
            report["claims"][name] = {"n": n, "status": "unproven"}
            continue
        scored[name] = (c["direction"], n)

    if not scored:
        return fail("no claim is proven (nothing to score)")

    # ---- compile + axioms ---------------------------------------------------------
    tmpdir = tempfile.mkdtemp(prefix="r46-score-")
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
    for name, (direction, n) in scored.items():
        full = f"{namespace}.{name}"
        if not lean_axioms_ok(out, full, allowed):
            print(f"claim {name}: FAIL (non-whitelisted axioms)")
            report["claims"][name] = {"n": n, "status": "bad_axioms"}
            continue
        cfg = spec["scoring"]["lower" if direction == "lower" else "upper"]
        s, ms = score_lower(n, mode, cfg) if direction == "lower" else score_upper(n, mode, cfg)
        report["claims"][name] = {"direction": direction, "n": n, "status": "proven",
                                  "score": s, "milestone": ms}
        print(f"claim {name}: PROVEN at N={n} ({direction}) -> score {s:.4f}, milestone {ms}")
        if ms == "record_broken":
            report["details"].append(
                f"{name} with N={n} is beyond the published record: "
                + (f"R(4,6) >= {n + 1}, a new result" if direction == "lower"
                   else f"R(4,6) <= {n}, beyond the formally published "
                   f"record 41 (McKay-Radziszowski 1997)"))
        best = max(best, s)

    report["reward"] = best
    report["valid"] = 1 if best > 0 or scored else 0
    report["score_mode"] = mode
    print(f"reward={best:g} mode={mode}")
    write_rewards(best)
    return 0


if __name__ == "__main__":
    sys.exit(main())
