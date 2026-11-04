#!/usr/bin/env python3
"""Verify a QBF solver's answer for one QDIMACS instance.

Shared by BOTH sides so the check cannot diverge:
  - agent side:  qbf_verify CLI (this file on PATH)
  - judge side:  /opt/qbf/scoring.py imports check()

No trust in labels, no trust in the solver: a claimed answer only counts
when it is backed by a machine-verified certificate. The certificate is a
(long-distance) Q-resolution proof in Qute's compact QRP-style format (what
`qute --trace <file>` emits) or in classic ASCII QRP format (what
`depqbf --trace` emits, with the `r SAT` / `r UNSAT` trailer line). The
verification chain has two independent stages:

  1. qrp2rup (Peitl, proof checker + strategy extractor) parses the proof,
     checks its resolution DAG, extracts the winning strategy, and emits
       - <proof>.cert  the strategy as a CNF circuit,
       - <proof>.cnf   the ORIGINAL matrix with the strategy plugged in
                       (qrp2rup reads the matrix from the QDIMACS file we
                       pass — this is what binds the check to the actual
                       instance),
       - <proof>.rup   a DRUP proof that the combined CNF is unsatisfiable.
  2. drat-trim (the SAT competition proof checker) verifies <proof>.rup
     against <proof>.cnf. "Strategy + matrix is UNSAT" is recomputed from
     scratch, so a proof produced for a different instance, a fabricated
     proof, or a replayed certificate cannot pass: the extracted strategy
     would not win on THIS matrix, the combined CNF would be satisfiable,
     and no DRUP proof of unsatisfiability can verify.

Direction check: the proof's own verdict must match the claimed one.
  - Qute format: the concluding constraint (the last proof line with an
    empty literal list) carries Qute's clause/term flag in its second
    column: 1 = term/cube proof (formula TRUE), 0 = clause proof (FALSE).
  - classic QRP: the trailer line `r SAT` (TRUE) / `r UNSAT` (FALSE).

Known upstream quirks, handled here (all conservative — they can only turn
a bad acceptance into a rejection, never the reverse):
  - qrp2rup writes a garbage placeholder line `p cnf ____ ____` as the
    second line of the combined CNF; it is stripped before drat-trim.
  - qrp2rup sometimes omits the final empty-clause line from the .rup even
    though its internal log reports CONFLICT; a single `0` line is appended
    in that case. This is safe: drat-trim independently checks whether the
    empty clause follows by reverse unit propagation — appending the claim
    can never make an invalid proof pass.
  - For FALSE claims we additionally require every matrix clause to appear
    verbatim in the combined CNF (they do for a correct qrp2rup run; for
    TRUE claims the matrix clauses appear with strategy variables
    substituted, so verbatim inclusion does not apply).

check(qdimacs, out, proof_path) -> (ok, reason). The official label is
never consulted: a verified certificate decides alone.

CLI:  qbf_verify instance.qdimacs solver_output.txt [proof.qrp]
prints `SUCCEED` (exit 0) or `FAILED: <reason>` (exit 1).
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

QRP2RUP = os.environ.get("QRP2RUP", "/opt/qbf/qrp2rup")
DRAT_TRIM = os.environ.get("DRAT_TRIM", "/opt/qbf/drat-trim")
QRP2RUP_TIMEOUT = int(os.environ.get("QRP2RUP_TIMEOUT", "300"))
DRAT_TIMEOUT = int(os.environ.get("DRAT_CHECK_TIMEOUT", "600"))
PROOF_MAX_BYTES = int(os.environ.get("QBF_PROOF_MAX_BYTES", str(2 * 1024**3)))


def parse_qdimacs(path):
    """QDIMACS -> (nvars, prefix, clauses).

    prefix is a list of ('a'|'e', [vars]) blocks; clauses are lists of
    nonzero ints. Tolerates comment lines (c ...) anywhere.
    """
    nvars = None
    prefix = []
    clauses = []
    current = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("c"):
                continue
            if line.startswith("p"):
                parts = line.split()
                if len(parts) >= 4 and parts[1] == "cnf":
                    nvars = int(parts[2])
                continue
            if line.startswith("a") or line.startswith("e"):
                parts = line.split()
                quant = parts[0]
                vars_ = [int(t) for t in parts[1:] if t != "0"]
                prefix.append((quant, vars_))
                continue
            if line.startswith("%"):  # old QDIMACS trailer
                break
            for tok in line.split():
                try:
                    lit = int(tok)
                except ValueError:
                    continue
                if lit == 0:
                    clauses.append(current)
                    current = []
                else:
                    current.append(lit)
    if current:  # tolerate a missing final 0
        clauses.append(current)
    if nvars is None:
        nvars = max((abs(l) for c in clauses for l in c), default=0)
    return nvars, prefix, clauses


def parse_output(path):
    """Solver stdout -> status: 'true' | 'false' | 'unknown' | None.

    The LAST s-line wins. Only `s TRUE` and `s FALSE` are verdicts.
    """
    status = None
    with open(path, errors="replace") as f:
        for line in f:
            if line.startswith("s"):
                body = line[1:].strip().upper()
                if body.startswith("TRUE"):
                    status = "true"
                elif body.startswith("FALSE"):
                    status = "false"
                elif body.startswith("UNKNOWN"):
                    status = "unknown"
    return status


def proof_verdict(proof_path):
    """Extract the verdict the proof itself claims.

    Returns ('true'|'false'|'unknown', format_name, error_or_None).
    """
    is_classic_qrp = None
    last_empty_flag = None
    trailer = None
    try:
        with open(proof_path, errors="replace") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("c"):
                    continue
                if s.startswith("p qrp"):
                    is_classic_qrp = True
                    continue
                if s.startswith("a ") or s.startswith("e "):
                    continue
                if s.startswith("r ") or s.startswith("s "):
                    body = s[2:].strip().upper()
                    if body.startswith("SAT") or body == "TRUE":
                        trailer = "true"
                    elif body.startswith("UNSAT") or body == "FALSE":
                        trailer = "false"
                    continue
                if is_classic_qrp is None:
                    is_classic_qrp = False
                if not is_classic_qrp:
                    # Qute style: <id> <clause/term flag> <lits...> 0 <parents...> 0
                    toks = s.split()
                    if len(toks) < 3:
                        continue
                    try:
                        flag = int(toks[1])
                    except ValueError:
                        continue
                    lits = []
                    for tok in toks[2:]:
                        try:
                            v = int(tok)
                        except ValueError:
                            break
                        if v == 0:
                            break
                        lits.append(v)
                    if not lits:
                        last_empty_flag = flag
    except OSError as e:
        return None, None, f"could not read proof file: {e}"
    if is_classic_qrp is None:
        return None, None, "proof file is empty"
    if is_classic_qrp:
        if trailer is None:
            return None, "qrp", ("classic QRP proof has no `r SAT` / "
                                 "`r UNSAT` verdict trailer line")
        return trailer, "qrp", None
    if last_empty_flag is None:
        return None, "qute", "no concluding (empty) constraint found in proof"
    return ("true" if last_empty_flag == 1 else "false"), "qute", None


def _strip_placeholder_line(cnf_path):
    """Remove qrp2rup's garbage `p cnf ____ ____` placeholder line in place."""
    with open(cnf_path, errors="replace") as f:
        lines = f.readlines()
    kept = [l for l in lines
            if not (l.startswith("p cnf") and "_" in l)]
    if len(kept) != len(lines):
        with open(cnf_path, "w") as f:
            f.writelines(kept)


def _ensure_empty_conclusion(rup_path):
    """Append the empty clause line if the .rup does not end with one.

    Safe: drat-trim re-checks whether the empty clause actually follows by
    RUP; the appended line is a claim, not a fact.

    Reads only the file tail: .rup files can be gigabytes.
    """
    with open(rup_path, "rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(max(0, size - 65536))
        tail = f.read().decode(errors="replace")
    lines = [l.split() for l in tail.strip().splitlines() if l.strip()]
    if lines and lines[-1] == ["0"]:
        return
    with open(rup_path, "a") as f:
        if size and not tail.endswith("\n"):
            f.write("\n")
        f.write("0\n")


def run_certificate_chain(qdimacs_path, proof_path, claimed):
    """Run qrp2rup + drat-trim. Returns (True, None) or (False, reason)."""
    qdimacs_path = os.path.abspath(qdimacs_path)
    if not proof_path:
        return False, ("solver claimed a verdict but provided no proof file "
                       "(QBF_PROOF_PATH was not used)")
    proof_path = os.path.abspath(proof_path)
    if not os.path.exists(proof_path):
        return False, ("solver claimed a verdict but the proof file is "
                       "missing (QBF_PROOF_PATH was not used)")
    size = os.path.getsize(proof_path)
    if size == 0:
        return False, "proof file is empty"
    if size > PROOF_MAX_BYTES:
        return False, (f"proof file too large ({size} bytes > "
                       f"{PROOF_MAX_BYTES} cap)")
    if not os.path.exists(QRP2RUP):
        return False, f"judge-side qrp2rup missing at {QRP2RUP}"
    if not os.path.exists(DRAT_TRIM):
        return False, f"judge-side drat-trim missing at {DRAT_TRIM}"

    verdict, fmt, err = proof_verdict(proof_path)
    if err is not None:
        return False, err
    if verdict != claimed:
        return False, (f"proof verdict mismatch: solver claimed `{claimed}` "
                       f"but the proof concludes `{verdict}` ({fmt} format)")

    work = tempfile.mkdtemp(prefix="qbf-verify-")
    try:
        local_proof = os.path.join(work, "proof.qrp")
        shutil.copyfile(proof_path, local_proof)
        try:
            p = subprocess.run([QRP2RUP, local_proof, qdimacs_path],
                               cwd=work, capture_output=True, text=True,
                               timeout=QRP2RUP_TIMEOUT)
        except subprocess.TimeoutExpired:
            return False, (f"qrp2rup timed out after {QRP2RUP_TIMEOUT}s "
                           "(counts as unverified)")
        if p.returncode != 0:
            tail = "\n".join(((p.stdout or "") + (p.stderr or ""))
                             .strip().splitlines()[-3:])
            return False, f"qrp2rup rejected the proof (exit {p.returncode}: {tail})"
        combined = local_proof + ".cnf"
        rup = local_proof + ".rup"
        if not (os.path.exists(combined) and os.path.exists(rup)):
            return False, "qrp2rup did not produce the combined CNF / DRUP proof"
        _strip_placeholder_line(combined)

        if claimed == "false":
            # Belt and suspenders: the combined CNF of a FALSE proof must
            # contain every matrix clause verbatim.
            try:
                _, _, clauses = parse_qdimacs(qdimacs_path)
                # counts preserves duplicate matrix clauses; appeared tracks
                # which clause forms were seen in the combined CNF. The
                # combined CNF is streamed one clause at a time — it can be
                # gigabytes, so it must never be materialized.
                counts = {}
                for c in clauses:
                    fz = frozenset(c)
                    counts[fz] = counts.get(fz, 0) + 1
                appeared = set()
                current = []
                with open(combined, errors="replace") as f:
                    for cline in f:
                        if cline.startswith("p") or cline.startswith("c"):
                            continue
                        for tok in cline.split():
                            try:
                                v = int(tok)
                            except ValueError:
                                continue
                            if v == 0:
                                fz = frozenset(current)
                                if fz in counts:
                                    appeared.add(fz)
                                current = []
                            else:
                                current.append(v)
                missing = sum(n for fz, n in counts.items()
                              if fz not in appeared)
                if missing:
                    return False, (f"combined CNF misses {missing} matrix "
                                   "clause(s) of the instance")
            except Exception as e:
                return False, f"could not audit combined CNF: {e}"

        _ensure_empty_conclusion(rup)
        try:
            p = subprocess.run([DRAT_TRIM, combined, rup],
                               capture_output=True, text=True,
                               timeout=DRAT_TIMEOUT)
        except subprocess.TimeoutExpired:
            return False, (f"drat-trim check timed out after {DRAT_TIMEOUT}s "
                           "(counts as unverified)")
        out = p.stdout or ""
        # Judge on the status line, not the exit code (drat-trim exits 1
        # even for some verified trivial-UNSAT cases).
        if "s VERIFIED" in out:
            return True, None
        tail = "\n".join((out + (p.stderr or "")).strip().splitlines()[-3:])
        return False, f"DRUP proof not verified (drat-trim exit {p.returncode}: {tail})"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def check(qdimacs_path, output_path, proof_path=None):
    """Returns (True, None) on an accepted answer, else (False, reason)."""
    try:
        parse_qdimacs(qdimacs_path)
    except Exception as e:  # judge-side instance must parse; treat as infra ok
        return False, f"could not parse instance: {e}"
    try:
        status = parse_output(output_path)
    except Exception as e:
        return False, f"could not parse solver output: {e}"
    if status not in ("true", "false"):
        return False, "no `s TRUE` / `s FALSE` line in solver output"
    return run_certificate_chain(qdimacs_path, proof_path, status)


def main(argv):
    if len(argv) not in (3, 4):
        print(f"usage: {argv[0]} instance.qdimacs solver_output.txt [proof.qrp]",
              file=sys.stderr)
        return 2
    proof = argv[3] if len(argv) == 4 else None
    ok, reason = check(argv[1], argv[2], proof)
    if ok:
        print("SUCCEED")
        return 0
    print(f"FAILED: {reason}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
