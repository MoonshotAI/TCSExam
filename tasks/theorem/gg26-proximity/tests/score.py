#!/usr/bin/env python3
"""Verifier for the bare (single-theorem) variant.

Scoring is all-or-nothing:
  1. Anti-cheat lexical scan (comment-stripped):
     - `axiom` / `sorryAx` / `native_decide` / `admitGoal` / `byAsSorry` /
       `skipKernelTC` / `implemented_by` anywhere                  -> reward 0
     - `notation` / `macro` / `syntax` / `elab` / `macro_rules` /
       `initialize` declarations in the writable zone              -> reward 0
     - `sorry` / `admit` left in the main-theorem slot             -> reward 0
       (a `sorry` in the writable helper layer is not scanned for; if the
        main theorem's proof depends on it, the `#print axioms` check fails,
        since `sorryAx` is never allowed)
     - fixed definition block or the theorem statement tampered  -> reward 0
  2. Assembly check: compile the whole submission unchanged; reward 1 iff it
     builds, the slot body is sorry-free, and `#print axioms` of the main
     theorem stays within the standard axioms (only the LAST report is
     trusted).
  Otherwise reward 0.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# Load the image-owned shared checks without using the submission's import path.
import importlib.util as _import_util
_security_spec = _import_util.spec_from_file_location(
    "tcsexam_lean_security", os.path.join(os.path.dirname(os.path.abspath(__file__)), "lean_security.py"))
_security = _import_util.module_from_spec(_security_spec)
_security_spec.loader.exec_module(_security)


STANDARD_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
FORBIDDEN_ANYWHERE = re.compile(
    r"\b(axiom|sorryAx|native_decide|admitGoal|byAsSorry|skipKernelTC|implemented_by)\b"
)
META_DECL = re.compile(
    r"(?m)^\s*(?:@\[[^\]]*\]\s*)*(scoped\s+|local\s+|private\s+)?"
    r"(notation|macro|syntax|elab|macro_rules|initialize)\b"
)
SORRY_OR_ADMIT = re.compile(r"\b(sorry|admit)\b")
FIXED_END_MARK = "-- END OF FIXED PART"


def strip_comments(text: str) -> str:
    return _security.strip_comments(text)


def norm_ws(text: str) -> str:
    return " ".join(text.split())


def find_checkpoint_block(text: str, name: str):
    """Return (block_start, header_end, body_start, body_end, block_end) char
    offsets of the checkpoint theorem in `text`, or None.

    block:  from the `theorem <name>` keyword to the END marker line (incl.).
    header: from after `theorem <name>` to the first `:=` before the BEGIN mark.
    body:   between the BEGIN and END marker lines.

    Theorem names may end with `'`: a trailing `\b` after `re.escape(name)`
    fails there, and an unprimed prefix would otherwise match the primed
    declaration.  Scan all `theorem` headers and compare the captured
    identifier (`[\\w']+`) for equality instead.
    """
    m = None
    for cand in re.finditer(r"(?m)^[ \t]*theorem\s+([\w']+)", text):
        if cand.group(1) == name:
            m = cand
            break
    if m is None:
        return None
    begin = checkpoint_begin_marker(text, m.end(), name)
    end = checkpoint_end_marker(text, m.end(), name)
    if not begin or not end or end.start() < begin.end():
        return None
    begin_abs = (m.end() + begin.start(), m.end() + begin.end())
    end_abs = (m.end() + end.start(), m.end() + end.end())
    # body = between the newline after BEGIN line and the start of the END
    # marker comment (a glued END marker leaves its proof code in the body)
    nl = text.find("\n", begin_abs[1])
    if nl == -1:
        return None
    body = (nl + 1, end_abs[0])
    # header: from end of `theorem name` to the first `:=` before BEGIN
    header_region = text[m.end():begin_abs[0]]
    ci = header_region.find(":=")
    if ci == -1:
        return None
    header = (m.end(), m.end() + ci)
    # block end = end of the END marker line (exclusive of its newline)
    block = (m.start(), end_abs[1])
    return block, header, body


def checkpoint_begin_marker(text: str, i: int, name: str):
    """Find the `-- CHECKPOINT <name> BEGIN` marker in `text` at or after
    offset i.

    The marker is normally on its own line; a glued form is also accepted --
    the marker comment followed by trailing text on the same line
    (`-- CHECKPOINT X BEGIN  classical`, the 10647952 shape: a tactic the
    model glued into the marker comment, inert in Lean because the whole
    line is a line comment).  The match covers the whole line, so the slot
    body in the caller starts on the NEXT line exactly as in the own-line
    form.  Only indentation may precede the marker on its line -- code
    glued BEFORE the marker stays rejected (the own-line rule covered that
    shape and no submission evidence asks for it).

    Two guards keep lookalikes out (mirroring checkpoint_end_marker; they
    only reject loose-form candidates and a rejection falls back to the
    own-line behaviour):
    - the marker position must not be inside a string literal (odd number
      of unescaped `"` before it on the line);
    - nor inside a block comment (`/-` ... `-/` nesting, string-aware).
    Returns a regex-like match object whose start() is the marker line's
    start and end() the end of the marker line (exclusive of its newline),
    or None.
    """
    pat = re.compile(
        r"(?m)^[ \t]*-- CHECKPOINT " + re.escape(name) + r" BEGIN(?:[ \t]+[^\n]*)?$"
    )
    for cand in pat.finditer(text, i):
        prefix = cand.group(0)[: cand.group(0).index("--")]
        # guard 1: inside a string literal on this line (odd unescaped quotes)
        quotes = 0
        j = 0
        while j < len(prefix):
            c = prefix[j]
            if c == "\\":
                j += 2
                continue
            if c == '"':
                quotes += 1
            j += 1
        if quotes % 2 == 1:
            continue
        # guard 2: inside a block comment at the marker's line
        line_start = cand.start()
        depth = 0
        k = i
        in_str = False
        while k < line_start:
            c = text[k]
            if in_str:
                if c == "\\":
                    k += 2
                    continue
                if c == '"':
                    in_str = False
                k += 1
                continue
            if text.startswith('"/-"', k):
                k += 4
                continue
            if text.startswith('"-/"', k):
                k += 4
                continue
            if text.startswith("/-", k):
                depth += 1
                k += 2
                continue
            if text.startswith("-/", k) and depth > 0:
                depth -= 1
                k += 2
                continue
            if c == '"':
                in_str = True
            k += 1
        if depth > 0:
            continue

        class _M:
            __slots__ = ("_s", "_e")

            def __init__(self, s, e):
                self._s, self._e = s, e

            def start(self):
                return self._s

            def end(self):
                return self._e

        return _M(cand.start() - i, cand.end() - i)
    return None


def checkpoint_end_marker(text: str, i: int, name: str):
    """Find the `-- CHECKPOINT <name> END` marker in `text` at or after offset i.

    The marker is normally on its own line; a glued form is also accepted --
    proof code followed by the marker as a trailing line-comment
    (`exact foo_pf  -- CHECKPOINT X END`).  In that case the match covers the
    whole line and `body` in the caller stops just before the marker comment,
    so the glued proof code stays in the body.

    Two guards keep lookalikes out (they only reject loose-form candidates;
    a rejection falls back to the own-line behaviour):
    - the marker position must not be inside a string literal (odd number of
      unescaped `"` before it on the line);
    - nor inside a block comment (`/-` ... `-/` nesting, string-aware).
    Returns a regex-like match object whose start() is the position of the
    `--` (body cut point) and end() is the end of the marker line (exclusive
    of its newline), or None.
    """
    pat = re.compile(
        r"(?m)^(?P<prefix>.*?)-- CHECKPOINT " + re.escape(name) + r" END[ \t]*$"
    )
    for cand in pat.finditer(text, i):
        prefix = cand.group("prefix")
        # guard 1: inside a string literal on this line (odd unescaped quotes)
        quotes = 0
        j = 0
        while j < len(prefix):
            c = prefix[j]
            if c == "\\":
                j += 2
                continue
            if c == '"':
                quotes += 1
            j += 1
        if quotes % 2 == 1:
            continue
        # guard 2: inside a block comment at the marker's line
        line_start = cand.start()
        depth = 0
        k = i
        in_str = False
        while k < line_start:
            c = text[k]
            if in_str:
                if c == "\\":
                    k += 2
                    continue
                if c == '"':
                    in_str = False
                k += 1
                continue
            if text.startswith('"/-"', k):
                k += 4
                continue
            if text.startswith('"-/"', k):
                k += 4
                continue
            if text.startswith("/-", k):
                depth += 1
                k += 2
                continue
            if text.startswith("-/", k) and depth > 0:
                depth -= 1
                k += 2
                continue
            if c == '"':
                in_str = True
            k += 1
        if depth > 0:
            continue

        class _M:
            __slots__ = ("_s", "_e")

            def __init__(self, s, e):
                self._s, self._e = s, e

            def start(self):
                return self._s

            def end(self):
                return self._e

        return _M(cand.start() + len(cand.group("prefix")) - i, cand.end() - i)
    return None


def lean_axioms_ok(stdout: str, full_name: str) -> bool:
    return _security.axioms_ok(stdout, full_name, STANDARD_AXIOMS)



# Negation lemmas (`¬ P`, `Not P`, `P → False`) are ordinary proof material.
# Their dependencies are checked by the trusted axiom audit after compilation,
# just like the rest of the proof.  `: False` conclusions are collected by
# the scanner below with the prop-binder distinction: an explicit propositional
# hypothesis binder (`h : 2 < G.n` etc.) makes the declaration a curried
# negation -- ordinary reductio material, NOT collected; without one it is
# unconditional ex-falso material (a closed `False` proof, or a
# packaged-spec refutation like `detAlg_false (A : DetAlg M start) : False`
# whose binders the caller discharges without proving anything).
FALSE_DECL_HEAD = re.compile(
    r"(?m)^(?:noncomputable\s+)?(?:private\s+)?(?:protected\s+)?"
    r"(?:theorem|lemma|def)\s+([\w']+)")
HARVEST_BRACKET_CLOSE = {"(": ")", "{": "}", "[": "]"}


def harvest_skip_brackets(text: str, i: int) -> int:
    """Advance past one balanced bracket group starting at text[i] (nesting
    allowed); return i unchanged when text[i] is not an opening bracket."""
    if i >= len(text) or text[i] not in HARVEST_BRACKET_CLOSE:
        return i
    stack = [HARVEST_BRACKET_CLOSE[text[i]]]
    i += 1
    while i < len(text) and stack:
        c = text[i]
        if c in HARVEST_BRACKET_CLOSE:
            stack.append(HARVEST_BRACKET_CLOSE[c])
        elif c == stack[-1]:
            stack.pop()
        i += 1
    return i


def harvest_concludes_false(text: str, i: int) -> bool:
    """Whether the declaration header continuing at offset i (just after the
    declared name) reads `<binders> : False`."""
    while True:
        while i < len(text) and text[i] in " \t\n":
            i += 1
        ni = harvest_skip_brackets(text, i)
        if ni == i:
            break
        i = ni
    while i < len(text) and text[i] in " \t\n":
        i += 1
    if i >= len(text) or text[i] != ":":
        return False
    j = i + 1
    while j < len(text) and text[j] in " \t\n":
        j += 1
    # A result starting with False may still be an ordinary proposition,
    # e.g. `False → False`; only a literal False conclusion is collected.
    return bool(re.match(r"False\s*:=", text[j:]))


# Types that visibly are propositions inside an explicit binder: an infix
# relation, a quantifier, or a negation head.
HARVEST_PROP_TYPE = re.compile(
    r"(?:^|\s)(?:∀|∃|¬)|(?:^|\s)Not\b|[=≠<>≤≥∈∉⊆⊂∼≈≃≅≡↔∣]")


def harvest_has_prop_binder(text: str, i: int) -> bool:
    """Whether the declaration header continuing at offset i (just after the
    declared name) carries an explicit `(...)` binder whose type visibly is
    a proposition -- an infix relation (`h : 2 < G.n`, `h : x ∈ s`,
    `h : a ≠ b`), a quantifier (`h : ∀ x, P x`), or a negation head.  Only
    `(...)` groups count: implicit `{...}` and instance `[...]` arguments
    are discharged by the elaborator rather than proved by the caller, so
    they cannot themselves witness an honest reductio helper -- but leading
    `{...}`/`[...]` groups are SKIPPED while scanning (nesting allowed),
    so the common shape `{n j : ℕ} (hj1 : 1 ≤ j) ... : False` keeps its
    reductio-helper reading (the scan used to stop at the first non-`(`
    binder and dump these into the false-declaration bucket).  A
    declaration whose propositional binders are ALL implicit/instance
    still reads as ex-falso material: the caller never proves an
    elaborator-discharged hypothesis.  Scanning stops at the header's
    conclusion colon or at a non-binder character."""
    while True:
        while i < len(text) and text[i] in " \t\n":
            i += 1
        if i >= len(text) or text[i] not in "({[":
            return False
        if text[i] != "(":
            # implicit/instance binder: skip the balanced group and keep
            # scanning for a later explicit propositional binder
            i = harvest_skip_brackets(text, i)
            continue
        j = i + 1
        depth = 1
        colon = -1
        while j < len(text) and depth:
            c = text[j]
            if c in "({[":
                depth += 1
            elif c in ")}]":
                depth -= 1
                if depth == 0:
                    break
            elif c == ":" and depth == 1 and colon == -1:
                colon = j
            j += 1
        if colon != -1 and HARVEST_PROP_TYPE.search(text[colon + 1:j]):
            return True
        i = j + 1


def exfalso_harvest(submission: str, body: str) -> str:
    """Names of candidate helper-layer harvest declarations referenced in `body`,
    "" when clean.  Collected:

      - `theorem/lemma/def` concluding `False` WITHOUT an explicit
        propositional hypothesis binder (harvest_has_prop_binder): a closed
        `False` proof or a packaged-spec refutation.

    A `: False` declaration WITH such a binder (`c3_break (h : 2 < G.n) ...
    : False`) is a curried negation -- ordinary reductio material -- and is
    not collected.  A reference to a collected declaration means the slot is
    discharged by ex falso from an injected statement (the harvest
    pattern): it proves nothing about the checkpoint and signals that some
    injected or packaged statement is false, so the checkpoint scores 0 and
    the run is flagged for review."""

    stripped = strip_comments(submission)
    decls = set()
    for m in FALSE_DECL_HEAD.finditer(stripped):
        if (harvest_concludes_false(stripped, m.end())
                and not harvest_has_prop_binder(stripped, m.end())):
            decls.add(m.group(1))
    hits = [d for d in sorted(decls) if re.search(r"\b" + re.escape(d) + r"\b", body)]
    return ",".join(hits)


ENV_BROKEN_PAT = re.compile(r"object file .* of module .* does not exist")


def env_broken_note(out: str) -> str:
    """Distinguish a destroyed build environment (e.g. the agent wiped the
    prebuilt mathlib oleans with `lake clean`) from an ordinary compile
    failure, so a zero caused by missing oleans is not misread as a math
    failure."""

    if ENV_BROKEN_PAT.search(out):
        return ("ENV-BROKEN: prebuilt library oleans missing (agent may have "
                "wiped them, e.g. `lake clean`); this score reflects a broken "
                "sandbox, not a math result")
    return ""

def run_lean(app_dir: str, path: str, timeout: int = 1200):
    return _security.run_lean(app_dir, path, timeout)


def prepare_shape_audit(app_dir: str, timeout: int = 1200):
    """Compile the image-owned type inspection before submitted Lean code."""
    module = Path(__file__).with_name("GG26ProofShape.lean")
    target = Path(app_dir) / ".lake/build/lib/lean/GG26ProofShape.olean"
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            ["lake", "env", "lean", "-R", str(module.parent), "-o", str(target), str(module)],
            cwd=app_dir, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "GG26 proof-shape audit compilation timed out"
    return result.returncode == 0, result.stdout + result.stderr


def shape_audit_rejections(output: str, names):
    """Require one exact trusted report for every candidate helper."""
    reports = {}
    for line in output.splitlines():
        if line.startswith("TCSEXAM_GG26_SHAPE "):
            report = json.loads(line.removeprefix("TCSEXAM_GG26_SHAPE "))
            if not isinstance(report, dict):
                raise ValueError("invalid GG26 proof-shape report")
            name = report.get("declaration")
            if name in reports or type(report.get("reject")) is not bool:
                raise ValueError("invalid or duplicate GG26 proof-shape report")
            reports[name] = report["reject"]
    if set(reports) != set(names):
        raise ValueError("missing or unexpected GG26 proof-shape report")
    return [name for name in names if reports[name]]


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

    def fail(msg: str) -> int:
        print(f"FAIL: {msg}")
        write_reward(0)
        return 0

    with open(os.path.join(args.tests, "checkpoints.json")) as f:
        spec = json.load(f)
    checkpoints = spec["checkpoints"]
    assert len(checkpoints) == 1, "bare variant grades exactly one theorem"
    namespace = spec["namespace"]
    main_theorem = spec.get("main_theorem", checkpoints[0]["name"])
    assert checkpoints[0]["name"] == main_theorem

    with open(os.path.join(args.tests, "reference", "Basic.lean")) as f:
        reference = f.read()

    sub_path = os.path.join(args.app, "Task", "Basic.lean")
    try:
        with open(sub_path) as f:
            submission = f.read()
    except OSError:
        return fail("no submission Task/Basic.lean")

    source_error = _security.source_error(submission, allow_native=False)
    if source_error:
        return fail(source_error)

    # ---- fixed part integrity -------------------------------------------------
    def fixed_part(text: str):
        idx = text.find(FIXED_END_MARK)
        if idx == -1:
            return None
        nl = text.find("\n", idx)
        return text[: (nl + 1) if nl != -1 else len(text)]

    ref_fixed, sub_fixed = fixed_part(reference), fixed_part(submission)
    if ref_fixed is None or sub_fixed is None or norm_ws(ref_fixed) != norm_ws(sub_fixed):
        return fail("fixed definition block missing or tampered")

    # ---- locate the main-theorem block, statement integrity --------------------
    rb = find_checkpoint_block(reference, main_theorem)
    sb = find_checkpoint_block(submission, main_theorem)
    if rb is None:
        return fail(f"FATAL: reference missing block {main_theorem}")
    if sb is None:
        return fail(f"submission missing block {main_theorem}")
    rh = norm_ws(reference[rb[1][0]:rb[1][1]])
    sh = norm_ws(submission[sb[1][0]:sb[1][1]])
    if rh != sh:
        return fail(f"statement of {main_theorem} tampered")

    # ---- lexical anti-cheat ----------------------------------------------------
    stripped = strip_comments(submission)
    if FORBIDDEN_ANYWHERE.search(stripped):
        return fail("forbidden token (axiom / sorryAx / native_decide)")

    # ---- semantic-layer rewriting ban (writable zone only) ---------------------
    # notation/macro/syntax/elab/macro_rules/initialize declarations outside the
    # main-theorem slot could reinterpret the tokens of the fixed zone or of the
    # theorem statement while leaving the text intact;
    # these declarations are not needed for a proof.
    for seg in (submission[: sb[0][0]], submission[sb[0][1] :]):
        if META_DECL.search(strip_comments(seg)):
            return fail("notation/macro/syntax/elab declaration in the writable zone (semantic-layer rewriting)")

    # sorry/admit outside the main-theorem slot (the writable helper layer)
    # is not an instant 0: if the main theorem's proof depends on a
    # sorry-carrying auxiliary lemma, the `#print axioms` check below fails
    # (`sorryAx` is never allowed).  The slot body itself must be sorry-free.
    body = strip_comments(submission[sb[2][0]:sb[2][1]])
    if SORRY_OR_ADMIT.search(body):
        return fail("slot still contains sorry/admit")

    # Text scanning only selects candidates. Lean checks their actual binder
    # types, so named propositions and aliases work like visibly written ones.
    harvest = exfalso_harvest(submission, body)
    candidates = harvest.split(",") if harvest else []
    if candidates:
        ok, out = prepare_shape_audit(args.app)
        if not ok:
            print(out)
            return fail("trusted GG26 proof-shape audit does not compile")

    # ---- assembly check ---------------------------------------------------------
    tmpdir = tempfile.mkdtemp(prefix="bare-score-")
    asm_path = os.path.join(tmpdir, "Assembly.lean")
    with open(asm_path, "w") as f:
        if candidates:
            f.write("import GG26ProofShape\n")
        f.write(submission)
        if candidates:
            f.write("\n")
            for name in candidates:
                f.write(f"#tcsexam_gg26_shape {json.dumps(name)} {json.dumps(f'{namespace}.{main_theorem}')}\n")
        f.write(_security.axiom_audit(f'{namespace}.{main_theorem}', allow_native=False))
    ok, out = run_lean(args.app, asm_path)
    if not ok:
        print("assembly build failed:")
        print("  " + "\n  ".join(out.splitlines()[-15:]))
        note = env_broken_note(out)
        if note:
            print("  " + note)
        return fail("assembly does not compile")
    if not lean_axioms_ok(out, f"{namespace}.{main_theorem}"):
        print(out.splitlines()[-5:])
        return fail("non-standard axioms used")
    if candidates:
        try:
            rejected = shape_audit_rejections(out, candidates)
        except (ValueError, TypeError) as error:
            return fail(str(error))
        if rejected:
            return fail("exfalso-harvest: False helper without an explicit propositional hypothesis (" + ",".join(rejected) + ")")

    print(f"assembly_full=True reward=1")
    write_reward(1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
