#!/usr/bin/env python3
"""Verifier for the bare (single-theorem) variant of the Coester-Poon
3-taxi task (tcsexam/lean-three-taxi).

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
    for cand in re.finditer(r"(?m)^theorem\s+([\w']+)", text):
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



# Helper-layer declaration heads: named theorems, lemmas and definitions of
# any flavour (graph nodes for the reference scan in exfalso_harvest).
DECL_HEAD = re.compile(
    r"(?m)^(?:noncomputable\s+)?(?:private\s+)?(?:protected\s+)?"
    r"(?:theorem|lemma|def|abbrev|instance)\s+([\w']+)")

# Proposition-class declaration heads (theorems and lemmas): the subset of
# fixed-layer declarations a negation helper can be paired against in the
# harvest combination.  Fixed-layer def/abbrev/instance names are data, not
# task-side propositions -- in compiling Lean the pair positions
# (`absurd P X_false`, `X_false P`) hold proof terms, which data
# declarations can never be -- so `X_false (Gn n) ...` applying a helper to
# a fixed-layer game/graph constructor is ordinary mathematics (9584074's
# xi1_not_opt_of_improving), not a refutation of a task-side statement.
# (The fixed layer never contains `axiom`: the token is forbidden anywhere
# in the submission.)
PROP_DECL_HEAD = re.compile(
    r"(?m)^(?:noncomputable\s+)?(?:private\s+)?(?:protected\s+)?"
    r"(?:theorem|lemma)\s+([\w']+)")
# Harvestable false-statement declarations: a theorem/lemma/def whose
# conclusion is literally `False`, with binders of any form -- explicit
# `(...)`, implicit `{...}`, instance `[...]` (nesting allowed), or none.
# A `False` declaration carrying an explicit propositional hypothesis binder
# (harvest_has_prop_binder, e.g. `c3_break (hG : 2 < G.n) ... : False`;
# leading implicit/instance binders before it are skipped, not fatal) is
# negation-shaped ordinary mathematics -- a by_contra helper whose
# conclusion is the negation of its own hypotheses -- so it is judged by
# the harvest pair (group 2), not by reference.  Only a `False` declaration
# WITHOUT such a binder is unconditional ex-falso material: a closed proof
# of `False`, or a refutation of a packaged specification
# (`detAlg_false (A : DetAlg M start) : False`, the shape this check was
# built to catch) whose binders the caller discharges without proving
# anything.
# Declarations concluding in a negation (`¬ P`, `Not P`, `P → False`) are
# collected too, but a negation alone is NOT harvest material: ordinary
# proofs legitimately prove negation lemmas and reference them from the
# slots.  A negation helper trips the check only in the harvest pair --
# applied to a task-side name (another checkpoint, an axiom in the
# per-checkpoint variant, or a fixed-layer packaged assumption) inside the
# slot's dependency closure: P exists as an axiom AND is proved false in
# the same proof (see harvest_contradiction_use).
FALSE_DECL_HEAD = re.compile(
    r"(?m)^(?:noncomputable\s+)?(?:private\s+)?(?:protected\s+)?"
    r"(?:theorem|lemma|def)\s+([\w']+)")
HARVEST_IDENT = re.compile(r"[\w']+")
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
    return bool(re.match(r"False\b", text[j:j + 6]))


def harvest_concludes_negation(text: str, i: int) -> bool:
    """Whether the declaration header continuing at offset i (just after the
    declared name) reads `<binders> : <proposition>` with a negation
    proposition: `¬ ...`, `Not ...`, or `... → False` (balanced outer
    parentheses stripped)."""
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
    m = re.search(r":=", text[j:])
    if not m:
        return False
    prop = " ".join(text[j:j + m.start()].split())
    # strip balanced outer parentheses: `(¬ P)` reads as a negation too
    while prop.startswith("(") and prop.endswith(")"):
        depth = 0
        wraps = True
        for k, c in enumerate(prop):
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0 and k < len(prop) - 1:
                    wraps = False
                    break
        if not wraps or depth != 0:
            break
        prop = prop[1:-1].strip()
    return (
        prop.startswith("¬")
        or bool(re.match(r"Not\b", prop))
        or prop.replace(" ", "").endswith("→False")
    )


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


# The harvest pair, tokenized one proof line at a time (the natural forms
# `absurd P X_false` / `X_false P` sit on one line; a multi-line application
# is out of scope for this textual check).
HARVEST_LINE_TOKEN = re.compile(r"[\w'.]+|[(){}[\]]")
HARVEST_DECL_KEYWORD = {"theorem", "lemma", "def", "abbrev", "instance", "example"}


def harvest_arg_head(tokens, k):
    """Head symbol (last dot-component) of the term starting at tokens[k],
    skipping opening brackets; ("", k) at end of input.  Also returns the
    index just past the term's bracket group, so a following argument head
    can be read off."""
    opened = 0
    while k < len(tokens) and tokens[k] in "({[":
        opened += 1
        k += 1
    if k >= len(tokens):
        return "", k
    head = tokens[k].rsplit(".", 1)[-1]
    k += 1
    while opened and k < len(tokens):
        if tokens[k] in "({[":
            opened += 1
        elif tokens[k] in ")}]":
            opened -= 1
        k += 1
    return head, k


def harvest_contradiction_use(text: str, neg_names, task_names) -> str:
    """The harvest pair inside `text` (a slot body or one helper-layer
    declaration span): a collected negation helper applied to a task-side
    name -- `absurd P X_false`, `absurd (P h₁ h₂) X_false`, `X_false P`,
    `(X_false (P h)).elim` and the like.  Returns the negation helper's
    name, or "" when no such pair occurs.  Declaration-head positions are
    skipped (`theorem X_false : ¬ P` is collection, not use)."""
    for line in text.split("\n"):
        tokens = HARVEST_LINE_TOKEN.findall(line)
        for k, tok in enumerate(tokens):
            if tok == "absurd":
                h1, nxt = harvest_arg_head(tokens, k + 1)
                h2, _ = harvest_arg_head(tokens, nxt)
                if h1 in task_names and h2 in neg_names:
                    return h2
            elif (tok.rsplit(".", 1)[-1] in neg_names
                  and k > 0 and tokens[k - 1] not in HARVEST_DECL_KEYWORD):
                h, _ = harvest_arg_head(tokens, k + 1)
                if h in task_names:
                    return tok.rsplit(".", 1)[-1]
    return ""


def exfalso_harvest(submission: str, body: str, slot_names) -> str:
    """Names of helper-layer harvest declarations referenced from `body`,
    directly or through other helper-layer declarations; "" when clean.

    Two shapes are collected from the agent-writable region (checkpoint
    statements' own spans excluded):

    1. `theorem/lemma/def X ... : False` with NO explicit propositional
       hypothesis binder -- a reference to X means the slot is discharged
       by ex falso from an inconsistent environment (a closed proof of
       `False`, or a refutation of a packaged specification): it proves
       nothing about the checkpoint and signals that some injected or
       packaged statement is false, so the checkpoint scores 0 and the run
       is flagged for review.  The same declaration WITH such a binder
       (harvest_has_prop_binder) is a curried negation -- ordinary
       reductio material -- and joins group 2's harvest-pair judgement.
    2. `theorem/lemma/def X ... : ¬ P` / `Not P` / `P → False`, and
       negation-shaped `False` declarations from group 1 -- harvest
       material only in the harvest pair (harvest_contradiction_use): the
       slot's dependency closure applies X to a task-side name (another
       checkpoint -- an axiom in the per-checkpoint variant -- or a
       fixed-layer theorem/lemma, i.e. a packaged proposition; fixed-layer
       def/abbrev/instance names are data and never pair), i.e. P exists
       as an axiom AND is proved false in the same proof.  A plain
       reference to a negation lemma is ordinary mathematics and stays
       clean.

    Collection is restricted to the agent-writable region (everything below
    the fixed part): the fixed layer and the slot statements are task
    content and legitimately carry negation conclusions, while the harvest
    pattern is always agent-written.  The reference scan walks the
    helper-layer declaration graph, so a false declaration reached through
    an auxiliary lemma (never named in the slot itself) is still caught."""

    stripped = strip_comments(submission)
    fixed_idx = submission.find(FIXED_END_MARK)
    if fixed_idx == -1:
        region_start = 0
    else:
        nl = submission.find("\n", fixed_idx)
        region_start = (nl + 1) if nl != -1 else len(submission)
    # each checkpoint's own span (statement through header) is excluded from
    # collection, so a checkpoint statement is never itself harvest material,
    # while a same-named declaration elsewhere (e.g. in a namespace) still is
    excluded = []
    for name in slot_names:
        blk = find_checkpoint_block(submission, name)
        if blk is not None:
            excluded.append((blk[0][0], blk[2][0]))
    false_decls, neg_decls = set(), set()
    for m in FALSE_DECL_HEAD.finditer(stripped):
        if m.start() < region_start:
            continue
        if any(a <= m.start() < b for a, b in excluded):
            continue
        if harvest_concludes_false(stripped, m.end()):
            if harvest_has_prop_binder(stripped, m.end()):
                # negation-shaped: an honest reductio helper (by_contra
                # material); harvest only in the contradiction pair
                neg_decls.add(m.group(1))
            else:
                false_decls.add(m.group(1))
        elif harvest_concludes_negation(stripped, m.end()):
            neg_decls.add(m.group(1))
    if not false_decls and not neg_decls:
        return ""
    # task-side names a negation helper can be paired against: the fixed
    # layer's PROPOSITION declarations (theorem/lemma, the packaged
    # assumptions; def/abbrev/instance names are data and never pair, see
    # PROP_DECL_HEAD) and the checkpoint names (injected as axioms in the
    # per-checkpoint variants)
    task_names = {m.group(1) for m in PROP_DECL_HEAD.finditer(stripped)
                  if m.start() < region_start} | set(slot_names)
    body = strip_comments(body)
    # a declaration's span runs from its own head to the next declaration
    # head; references are token matches (a `\b`-regex would never fire after
    # a primed name like `foo'`, `'` not being a word character)
    heads = [m for m in DECL_HEAD.finditer(stripped) if m.start() >= region_start]
    spans = {}
    for k, m in enumerate(heads):
        end = heads[k + 1].start() if k + 1 < len(heads) else len(stripped)
        spans.setdefault(m.group(1), []).append(stripped[m.start():end])
    seeds = {t for t in HARVEST_IDENT.findall(body)
             if t in spans or t in false_decls}
    hits = set(seeds) & false_decls
    seen = set(seeds)
    worklist = [s for s in seeds if s in spans]
    while worklist:
        name = worklist.pop()
        for span in spans.get(name, []):
            for tok in HARVEST_IDENT.findall(span):
                if tok in false_decls:
                    hits.add(tok)
                elif tok in spans and tok not in seen:
                    seen.add(tok)
                    worklist.append(tok)
    # the harvest pair, over the whole dependency closure (the slot body
    # itself first, then every reached helper span)
    if neg_decls:
        closure = [body]
        for name in seen:
            closure.extend(spans.get(name, []))
        for text in closure:
            neg_hit = harvest_contradiction_use(text, neg_decls, task_names)
            if neg_hit:
                hits.add("neg:" + neg_hit)
                break
    return ",".join(sorted(hits))


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
    slot_names = {cp["name"] for cp in checkpoints}  # for the exfalso-harvest exclusion spans
    assert len(checkpoints) == 1, "bare variant grades exactly one theorem"
    namespace = spec.get("namespace", "PosBodyChasing")
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

    harvest = exfalso_harvest(submission, body, slot_names)
    if harvest:
        print(f"SUSPECT exfalso-harvest ({harvest}): an injected or packaged statement is likely false; flag for review")
        write_reward(0)
        return 0

    # ---- assembly check ---------------------------------------------------------
    tmpdir = tempfile.mkdtemp(prefix="posbody-chasing-bare-score-")
    asm_path = os.path.join(tmpdir, "Assembly.lean")
    with open(asm_path, "w") as f:
        f.write(submission)
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

    print(f"assembly_full=True reward=1")
    write_reward(1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
