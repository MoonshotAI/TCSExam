#!/usr/bin/env python3
"""TCSExam open-conjecture verifier — canonical verifier for the
"prove or refute v1" open-conjecture task family.

This file is copied verbatim into each task package as tests/score.py.
Nothing below is task-specific: the per-task configuration lives in
tests/checkpoints.json (slot names, weights, namespace) and
tests/reference/Basic.lean (the reference statements).  Do not edit the copy
inside a task package; edit this template and re-copy.

Accepted checkpoints.json layouts:
  - "mains": ["conj", "refuted"], the two mains also listed in "checkpoints"
    (distinguished by kind/role)                       (alon-jaeger-tarsi, log-rank)
  - "main_slots": ["conj", "refuted"], "checkpoints" lists only the special
    cases                                            (tuza, explicit-rigid-matrix)
  - "conjecture": "conj" / "refutation": "refuted", both mains also listed in
    "checkpoints" with weight 0                      (aaronson-ambainis)
  - "slots": {"full_credit": ["conj", "refuted"]}, "checkpoints" lists only
    the special cases                                (caccetta-haggkvist)

Scoring pipeline, with the origin of each rule:

  1. Fixed-part integrity: everything up to `-- END OF FIXED PART` must match
     the reference verbatim (whitespace-normalized)              -> else 0.
     (Whole family; the definition zone is the contract the agent must not
     renegotiate.)

  2. Slot structure and declaration order: the slot theorems (the two mains
     plus the special cases) must be present exactly once, in the reference
     order                                                        -> else 0.
     Moving a declaration could allow an auxiliary `False` derived from it
     to appear above the remaining slots; the order check rejects this.

  3. Statement integrity: every slot header must match the reference verbatim
     (whitespace-normalized)                                      -> else 0.

  4. Shared source checks reject metaprogramming commands (including run_cmd
     and run_tac) before compilation. Strings and comments are lexed separately.
     Additional task-specific lexical checks:
     - `axiom` / `sorryAx` / `native_decide` / `admitGoal` / `byAsSorry` /
       `skipKernelTC` / `implemented_by` anywhere                 -> 0.
       (Whole family; each token is a way to smuggle an unproven statement
       past the kernel or past the `#print axioms` audit.)
     - `notation` / `macro` / `syntax` / `elab` / `macro_rules` /
       `initialize` declarations in the writable zone (outside the slots)
                                                                   -> 0.
       (Text-level pinning cannot stop
       semantic-layer rewriting — a writable-zone `notation` can reinterpret
       the tokens of the fixed zone or of the slot statements while leaving
       the text intact.  No honest proof needs these declarations.)

  5. sorry / admit inside a slot body -> that slot scores 0.  A sorry in the
     writable helper layer is not scanned for: any slot whose proof depends
     on it fails the `#print axioms` whitelist, because `sorryAx` is never
     allowed.  (Whole family.)

  6. Full credit (the two main slots): grade the slot in isolation —
     compile a grader-side variant and require `#print axioms` to stay within
     {propext, Classical.choice, Quot.sound}.
     - Mutual exclusion (origin: aaronson-ambainis): when grading a main
       slot, the contradictory twin is DELETED from the variant, never
       injected as an axiom.  Injecting both `Conjecture` and `¬ Conjecture`
       would make every slot vacuously provable by `absurd`; deleting the
       twin removes the whole attack class instead of relying on the axiom
       whitelist alone to catch it.
     - The special-case slots are injected as axioms carrying the reference
       signatures (so helper code between slots still parses), but they are
       NOT whitelisted: a main theorem must stand on the definitions alone
       (origin: alon-jaeger-tarsi).
     Passing any main slot -> reward 1.0.  Both mains passing makes the submission invalid and yields zero.

  7. Partial credit (each special case): graded the same way in isolation —
     BOTH main slots are deleted (they are never injected as axioms:
     a special case routed through the unproven conjecture is worth nothing,
     the "borrow the main theorem" hole exercised in the alon-jaeger-tarsi
     and log-rank-conjecture validation runs), the sibling special cases are
     injected as axioms AND whitelisted (they may form a chain).
     reward = (passed special-case weights) / (total special-case weights).

  8. Ex-falso harvest probe: a slot body referencing a helper-layer
     `theorem X : False` scores 0 for that slot and is flagged
     `SUSPECT exfalso-harvest` — the slot is then discharged by ex falso
     from a packaged falsehood, which proves nothing about the slot.
     Only the exact-`False` shape is scanned, NOT `theorem X : ¬ ...`
     (origin: aaronson-ambainis): the `refuted` slot is itself a
     `¬`-theorem, so refutation-side helper lemmas legitimately have
     `¬`-conclusions; scanning `¬` would flag honest refutation work.

  9. Axiom names are printed in full and compared exactly against the standard
     axioms and the explicitly permitted grader-injected checkpoint axioms.

 10. reward = 1.0 if any main slot passes, else the weighted fraction of
     special cases passed.  A per-slot verdict record is also written to
     judge_result.json next to the reward file (origin: log-rank-conjecture;
     diagnostics only, no effect on the score).
"""

import argparse
import concurrent.futures as futures
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
FALSE_LEMMA_DECL = re.compile(r"(?m)^[ \t]*theorem\s+([\w']+)\s*(?:\([^)]*\)\s*)*:\s*False\b")
FIXED_END_MARK = "-- END OF FIXED PART"


def strip_comments(text: str) -> str:
    return _security.strip_comments(text)


def norm_ws(text: str) -> str:
    return " ".join(text.split())


def find_checkpoint_block(text: str, name: str):
    """Return (block_start, header_end, body_start, body_end, block_end) char
    offsets of the slot theorem in `text`, or None.

    block:  from the `theorem <name>` keyword to the END marker line (incl.).
    header: from after `theorem <name>` to the first `:=` before the BEGIN mark.
    body:   between the BEGIN and END marker lines.

    Theorem names may end with `'` (e.g. `..._coeffs'`): a trailing `\\b`
    after `re.escape(name)` fails there (a `'` followed by whitespace is not a
    word boundary), and an unprimed prefix would otherwise match the primed
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
    begin = re.search(
        r"(?m)^\s*-- CHECKPOINT " + re.escape(name) + r" BEGIN\s*$", text[m.end():]
    )
    end = re.search(
        r"(?m)^\s*-- CHECKPOINT " + re.escape(name) + r" END\s*$", text[m.end():]
    )
    if not begin or not end or end.start() < begin.end():
        return None
    begin_abs = (m.end() + begin.start(), m.end() + begin.end())
    end_abs = (m.end() + end.start(), m.end() + end.end())
    # body = between the newline after BEGIN line and the start of END line
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


def lean_axioms_ok(stdout: str, full_name: str, extra_allowed: set) -> bool:
    return _security.axioms_ok(stdout, full_name, STANDARD_AXIOMS | extra_allowed)


def axiom_report(stdout: str, full_name: str) -> str:
    """Return the last `#print axioms` report for `full_name` in `stdout`
    (from the declaration name through the closing `]` of the axiom list),
    or "" if there is none.  Diagnostics for whitelist-FAIL cases, where the
    compile succeeded but the axiom set is rejected: without this the grader
    gives no hint which axiom name tripped the whitelist."""
    reports = list(
        re.finditer(re.escape(full_name) + r"'?\s+(depends on axioms:|does not depend on any axioms)", stdout)
    )
    if not reports:
        return ""
    last = reports[-1]
    end = stdout.find("]", last.end())
    if end == -1:
        return stdout[last.start():]
    return stdout[last.start():end + 1]


def exfalso_harvest(submission: str, body: str) -> str:
    """Names of helper-layer `theorem X : False` declarations referenced in
    `body`, "" when clean.  Such a reference means the slot is discharged by
    ex falso from an injected statement (the harvest pattern): it proves
    nothing about the slot and signals that some injected or packaged
    statement is false, so the slot scores 0 and the run is flagged for
    review.  Only exact-`False` conclusions are scanned (rule 8): `¬`-shaped
    helpers are legitimate on the refutation side."""

    decls = set(FALSE_LEMMA_DECL.findall(strip_comments(submission)))
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


def run_lean(app_dir: str, path: str, timeout: int = 900):
    return _security.run_lean(app_dir, path, timeout)


def load_spec(spec):
    """Normalize the four checkpoints.json layouts (see module docstring).

    Returns (namespace, mains, specials, slot_order, weights):
      namespace  — Lean namespace wrapping the slot theorems
      mains      — [conj, refuted] full-credit slot names, in order
      specials   — special-case slot names, in reference order
      slot_order — all slot names in reference order (mains first when the
                   checkpoints list does not contain them)
      weights    — {special name: weight} (default 1)
    """
    namespace = spec.get("namespace")
    if not namespace:
        raise SystemExit("FATAL: checkpoints.json has no namespace")
    mains = None
    if isinstance(spec.get("mains"), list):
        mains = list(spec["mains"])
    elif isinstance(spec.get("main_slots"), list):
        mains = list(spec["main_slots"])
    elif "conjecture" in spec and "refutation" in spec:
        mains = [spec["conjecture"], spec["refutation"]]
    elif isinstance(spec.get("slots"), dict) and isinstance(spec["slots"].get("full_credit"), list):
        mains = list(spec["slots"]["full_credit"])
    if len(mains or []) != 2:
        raise SystemExit("FATAL: checkpoints.json declares no conj/refuted main pair")
    checkpoints = spec["checkpoints"]
    cp_names = [cp["name"] for cp in checkpoints]
    slot_order = [m for m in mains if m not in cp_names] + cp_names
    specials = [n for n in slot_order if n not in set(mains)]
    weights = {cp["name"]: cp.get("weight", 1) for cp in checkpoints if cp["name"] in set(specials)}
    return namespace, mains, specials, slot_order, weights


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", default=os.environ.get("APP_DIR", "/app"))
    ap.add_argument("--tests", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--reward", default=os.environ.get("REWARD_FILE", "/logs/verifier/reward.txt"))
    args = ap.parse_args()

    result = {"reward": 0.0, "main_passed": [], "slots": {}, "reason": ""}

    def write_reward(value: float) -> None:
        os.makedirs(os.path.dirname(args.reward), exist_ok=True)
        with open(args.reward, "w") as f:
            f.write(f"{value:g}")
        try:
            sidecar = os.path.join(os.path.dirname(args.reward), "judge_result.json")
            with open(sidecar, "w") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
        except OSError:
            pass  # diagnostics only; never block scoring on the side record

    def fail(reason: str) -> int:
        print(f"FAIL: {reason}")
        result["reason"] = reason
        write_reward(0)
        return 0

    with open(os.path.join(args.tests, "checkpoints.json")) as f:
        spec = json.load(f)
    namespace, mains, specials, slot_order, weights = load_spec(spec)
    mains_set = set(mains)

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

    # ---- fixed part integrity (rule 1) --------------------------------------
    def fixed_part(text: str):
        idx = text.find(FIXED_END_MARK)
        if idx == -1:
            return None
        nl = text.find("\n", idx)
        return text[: (nl + 1) if nl != -1 else len(text)]

    ref_fixed, sub_fixed = fixed_part(reference), fixed_part(submission)
    if ref_fixed is None or sub_fixed is None or norm_ws(ref_fixed) != norm_ws(sub_fixed):
        return fail("fixed definition block missing or tampered")

    # ---- locate slot blocks ---------------------------------------------------
    ref_blocks, sub_blocks = {}, {}
    structural_ok = True
    for name in slot_order:
        rb = find_checkpoint_block(reference, name)
        sb = find_checkpoint_block(submission, name)
        if rb is None:
            return fail(f"reference missing slot {name} (grader-side bug)")
        ref_blocks[name] = rb
        if sb is None:
            print(f"NOTE: submission missing slot block {name}")
            structural_ok = False
            continue
        sub_blocks[name] = sb

    # ---- slot declaration order (rule 2) --------------------------------------
    slot_set = set(slot_order)

    def decl_order(text: str):
        # comment-stripped, so `theorem` inside comments cannot spoof the order
        return [
            m.group(1)
            for m in re.finditer(r"(?m)^[ \t]*theorem\s+([\w']+)", strip_comments(text))
            if m.group(1) in slot_set
        ]

    ref_order, sub_order = decl_order(reference), decl_order(submission)
    if sub_order != ref_order:
        if sorted(sub_order) == sorted(ref_order):
            return fail("slot declaration order changed")
        return fail("slot declaration missing or duplicated")

    # ---- statement integrity (rule 3) -----------------------------------------
    if structural_ok:
        for name in slot_order:
            rh = norm_ws(reference[ref_blocks[name][1][0]:ref_blocks[name][1][1]])
            sh = norm_ws(submission[sub_blocks[name][1][0]:sub_blocks[name][1][1]])
            if rh != sh:
                return fail(f"statement of slot {name} tampered")

    # ---- lexical anti-cheat (rule 4, anywhere part) ---------------------------
    stripped = strip_comments(submission)
    if FORBIDDEN_ANYWHERE.search(stripped):
        return fail("forbidden token (axiom / sorryAx / native_decide / ...)")

    slot_clean = {}
    outside_segments = []
    if structural_ok:
        # rule 5: sorry/admit inside a slot body zeroes that slot; the helper
        # layer is not scanned for sorry (dependence on a sorry-carrying
        # helper is caught per slot by the axiom whitelist).
        prev = 0
        for name in slot_order:
            blk = sub_blocks.get(name)
            if blk is None:
                continue
            outside_segments.append(submission[prev:blk[0][0]])
            prev = blk[0][1]
        outside_segments.append(submission[prev:])
        for name in slot_order:
            if name not in sub_blocks:
                slot_clean[name] = False
                continue
            body = strip_comments(submission[sub_blocks[name][2][0]:sub_blocks[name][2][1]])
            slot_clean[name] = not SORRY_OR_ADMIT.search(body)
    else:
        slot_clean = {name: False for name in slot_order}

    # ---- semantic-layer rewriting ban (rule 4, writable zone only) ------------
    # notation/macro/syntax/elab declarations in the writable zone could
    # reinterpret the tokens of the fixed zone or of the slot statements
    # while leaving the text intact;
    # these declarations are not needed for a proof.
    for seg in outside_segments:
        if META_DECL.search(strip_comments(seg)):
            return fail("notation/macro/syntax/elab declaration in the writable zone")

    # ---- variant generation (rules 6 and 7) ------------------------------------
    def extend_start_back(start: int) -> int:
        """Extend a removal span backwards over the slot's own decorations —
        at most ONE `/-- ... -/` docstring plus any `-- @[...]` annotation
        comment lines around it — so the removal leaves no orphan docstring
        behind (a stray `/--` is a hard error in Lean 4).

        Exactly one docstring is stripped, never a second one: after the
        slot's own docstring comes off, the text above can end with an
        unrelated comment block (e.g. a `/-! ... -/` module doc introducing
        the slot zone), and looping back for another `-/` would eat real code
        up to the next `/--` far above ."""
        def strip_annotations(tail: str) -> str:
            while True:
                ls = tail.rfind("\n") + 1
                if tail[ls:].lstrip().startswith(("-- @[", "--@[")):
                    tail = tail[:ls].rstrip()
                else:
                    return tail

        tail = submission[:start].rstrip()
        tail = strip_annotations(tail)
        if tail.endswith("-/"):
            open_idx = tail.rfind("/--")
            if open_idx != -1:
                tail = tail[:open_idx].rstrip()
        tail = strip_annotations(tail)
        return len(tail)

    def deletes_for(target: str) -> set:
        """Slots deleted outright (never axiom-injected) when grading `target`
        (rule 6 mutual exclusion): the contradictory twin for a main target —
        injecting both `Conjecture` and `¬ Conjecture` would make every slot
        vacuously provable by `absurd` — and both mains for a special-case
        target (rule 7: the main slots are never injected as axioms there)."""
        if target in mains_set:
            return mains_set - {target}
        return set(mains_set)

    def make_variant(target: str):
        """Submission with every slot except `target` either replaced by an
        axiom carrying the reference signature or deleted (see deletes_for);
        grader-side only, the submission itself is never modified."""
        pieces = []
        prev = 0
        for name in slot_order:
            if name == target or name not in sub_blocks:
                continue
            blk = sub_blocks[name][0]
            if name in deletes_for(target):
                pieces.append(submission[prev:extend_start_back(blk[0])])
            else:
                pieces.append(submission[prev:blk[0]])
                ref_header = reference[ref_blocks[name][1][0]:ref_blocks[name][1][1]]
                pieces.append(f"axiom {name} {ref_header}")
            prev = blk[1]
        pieces.append(submission[prev:])
        return "".join(pieces)

    def extra_allowed_for(target: str) -> set:
        """Grader-injected axioms a slot may legitimately depend on.
        Main slots must stand on the definitions alone (rule 6); special
        cases may build on the other special cases (they may form a chain)
        but never on the main slots (rule 7)."""
        if target in mains_set:
            return set()
        return {f"{namespace}.{s}" for s in specials if s != target}

    # ---- compile jobs -------------------------------------------------------------
    jobs = {}
    tmpdir = tempfile.mkdtemp(prefix="open-score-v1-")
    if structural_ok:
        for name in slot_order:
            if not slot_clean.get(name, False):
                continue
            path = os.path.join(tmpdir, f"Check_{name}.lean")
            with open(path, "w") as f:
                f.write(make_variant(name))
                f.write(_security.axiom_audit(f'{namespace}.{name}', allow_native=False))
            jobs[name] = path

    results = {}
    with futures.ThreadPoolExecutor(max_workers=3) as pool:
        futs = {pool.submit(run_lean, args.app, path): key for key, path in jobs.items()}
        for fut in futures.as_completed(futs):
            key = futs[fut]
            ok, out = fut.result()
            results[key] = (ok, out)

    # ---- evaluate ------------------------------------------------------------------
    passed = {}
    for name in slot_order:
        if name not in results:
            print(f"slot {name}: SKIP (missing/sorry) -> 0")
            passed[name] = False
            result["slots"][name] = "skip"
            continue
        ok, out = results[name]
        body_txt = submission[sub_blocks[name][2][0]:sub_blocks[name][2][1]] if name in sub_blocks else ""
        harvest = exfalso_harvest(submission, body_txt)
        if harvest:
            passed[name] = False
            result["slots"][name] = "suspect"
            print(f"slot {name}: SUSPECT exfalso-harvest ({harvest}) -> 0; an injected "
                  "statement is likely false, flag for review")
            continue
        if ok and lean_axioms_ok(out, f"{namespace}.{name}", extra_allowed_for(name)):
            passed[name] = True
            result["slots"][name] = "pass"
            print(f"slot {name}: PASS")
        else:
            passed[name] = False
            result["slots"][name] = "fail"
            print(f"slot {name}: FAIL")
            if not ok:
                print("  " + "\n  ".join(out.splitlines()[-15:]))
                note = env_broken_note(out)
                if note:
                    print("  " + note)
            else:
                report = axiom_report(out, f"{namespace}.{name}")
                print("  #print axioms report: "
                      + (" ".join(report.split()) if report else "<none found>"))

    main_passed = [m for m in mains if passed.get(m, False)]
    if len(main_passed) > 1:
        result["main_passed"] = main_passed
        return fail("inconsistent submission: both contradictory main slots passed")
    total_w = sum(weights.values())
    earned_w = sum(weights[n] for n in specials if passed.get(n, False))
    partial = earned_w / total_w if total_w else 0.0
    reward = 1.0 if main_passed else partial
    result["main_passed"] = main_passed
    result["reward"] = reward
    result["reason"] = (f"full credit via {main_passed}" if main_passed
                        else f"partial credit {partial:.3f}")
    print(f"main_passed={main_passed} partial={partial:.3f} reward={reward:.3f}")
    write_reward(reward)
    return 0


if __name__ == "__main__":
    sys.exit(main())
