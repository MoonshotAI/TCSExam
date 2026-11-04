"""D3 acceptance: naming consistency (the TCSEXAM header namespace).

The public namespace is X-TCSEXAM-* only. Legacy header names must be dead
on arrival. Covers (all over loopback HTTP; a dedicated service runs with
run_id_mode="required" for the run-id name assertions — no sessions are
booted there, since the in-worker agent's tunnel dial-in carries no run-id;
session-booting assertions run on the default warn-mode service):

- X-Modal-Token-Id / X-Modal-Token-Secret alone -> 401 (not credentials)
- X-FCS-Run-Id -> 400 (missing the required X-TCSEXAM-Run-Id): the legacy
  name is not read at all
- X-FCS-Client-Id -> ignored as a singleflight key (two creates with the
  same legacy client id get two distinct sessions)
- X-Archive-Token -> not the verifier credential (archive stays 404)
- X-Judge-Token -> ignored: alone it authenticates nothing (401), next to
  valid credentials it neither adds nor blocks access
- the positive chain: X-TCSEXAM-Token-Id/Secret authenticate;
  X-TCSEXAM-Run-Id satisfies run_id_mode=required (absent -> 400);
  X-TCSEXAM-Client-Id keys singleflight sharing; X-TCSEXAM-Agent-Name
  surfaces in the /v1/status callers table; X-TCSEXAM-Archive-Token opens
  the archive
- source hygiene: no legacy header-name strings anywhere in
  src/tcsexam/backend/ outside tests/ (tests legitimately name the legacy
  headers to prove their rejection).
"""
from __future__ import annotations

import json
from pathlib import Path

from helpers_cde import (
    AUTH,
    ARCHIVE_TOKEN,
    create_session,
    delete_session,
    get_archive,
    http,
    run_in_threads,
    service_factory,
    service_status,
    session_status,
    submit,
    synth,
    wait_ready,
    windows,
    make_tar_gz,
)

__all__ = ["synth", "windows", "service_factory"]

RUN = {"X-TCSEXAM-Run-Id": "d3-run"}
LEGACY_AUTH = {"X-Modal-Token-Id": "cde-token-id", "X-Modal-Token-Secret": "cde-token-secret"}

LEGACY_PATTERNS = ("X-Modal", "X-FCS", "X-Archive-Token", "X-Judge-Token")


def test_legacy_header_names_are_dead(service_factory):
    # run_id_mode="required" makes the run-id name enforceable; it lives on
    # its own service because the in-worker agent's tunnel dial-in carries no
    # run-id (worker dials are infrastructure, and under "required" the
    # middleware 400s them — a pre-existing config interaction, so the
    # session-booting assertions below run on the default warn-mode service).
    required = service_factory(run_id_mode="required")

    # Legacy service-auth names alone: not credentials. (A valid TCSEXAM
    # run-id rides along so the request reaches the token check — the run-id
    # gate runs first under run_id_mode="required".)
    status, body = http(
        "POST", f"{required.url}/v1/judge/sessions",
        headers={**LEGACY_AUTH, **RUN, "Content-Type": "application/json"},
        body=json.dumps({"judge_image": "registry.example.com/f-judge:1"}).encode(),
    )
    assert status == 401, body

    # Legacy run-id name: unread -> the required TCSEXAM run-id is missing.
    status, body = http(
        "POST", f"{required.url}/v1/judge/sessions",
        headers={**AUTH, "X-FCS-Run-Id": "d3-run", "Content-Type": "application/json"},
        body=json.dumps({"judge_image": "registry.example.com/f-judge:1"}).encode(),
    )
    assert status == 400, body
    assert "X-TCSEXAM-Run-Id" in body.decode()

    handle = service_factory(adapter_kwargs={"create_delay": 0.4})

    # Legacy client-id name: not a singleflight key — two concurrent creates
    # with the SAME legacy client id still get distinct sessions.
    fcs_client = {"X-FCS-Client-Id": "same-client", **RUN}
    resp_a, resp_b = run_in_threads(
        lambda: create_session(handle, headers=fcs_client),
        lambda: create_session(handle, headers=fcs_client),
    )
    assert resp_a["session_id"] != resp_b["session_id"]
    wait_ready(handle, resp_a["session_id"], headers=RUN)
    wait_ready(handle, resp_b["session_id"], headers=RUN)

    # Legacy archive-token name: not the verifier credential.
    resp = create_session(handle, headers=RUN)
    sid = resp["session_id"]
    wait_ready(handle, sid, headers=RUN)
    status, body = submit(handle, sid, make_tar_gz({"s.py": b"d3"}), headers=RUN)
    assert status == 202
    status, body = get_archive(handle, sid, token=None,
                               headers={**RUN, "X-Archive-Token": ARCHIVE_TOKEN})
    assert status == 404, "X-Archive-Token must not open the archive"

    # X-Judge-Token: alone it authenticates nothing; with valid credentials
    # it is ignored (access neither granted nor revoked).
    status, body = http(
        "GET", f"{handle.url}/v1/judge/sessions/{sid}",
        headers={"X-Judge-Token": ARCHIVE_TOKEN},
    )
    assert status == 401
    status, body = session_status(handle, sid, headers={**RUN, "X-Judge-Token": "whatever"})
    assert status == 200

    delete_session(handle, sid, headers=RUN)
    delete_session(handle, resp_a["session_id"], headers=RUN)
    delete_session(handle, resp_b["session_id"], headers=RUN)


def test_tcsexam_header_names_full_chain(service_factory):
    required = service_factory(run_id_mode="required")

    # Missing X-TCSEXAM-Run-Id under run_id_mode=required: 400.
    status, body = http(
        "POST", f"{required.url}/v1/judge/sessions",
        headers={**AUTH, "Content-Type": "application/json"},
        body=json.dumps({"judge_image": "registry.example.com/f-judge:1"}).encode(),
    )
    assert status == 400
    assert "X-TCSEXAM-Run-Id" in body.decode()

    handle = service_factory(adapter_kwargs={"create_delay": 0.4})

    # X-TCSEXAM-Client-Id is the singleflight key (control group).
    named = {**RUN, "X-TCSEXAM-Client-Id": "d3-client", "X-TCSEXAM-Agent-Name": "d3-agent"}
    resp_a, resp_b = run_in_threads(
        lambda: create_session(handle, headers=named),
        lambda: create_session(handle, headers=named),
    )
    assert resp_a["session_id"] == resp_b["session_id"]
    sid = resp_a["session_id"]
    wait_ready(handle, sid, headers=named)

    # X-TCSEXAM-Agent-Name surfaces in the callers table.
    status, body = submit(handle, sid, make_tar_gz({"s.py": b"d3"}), headers=named)
    assert status == 202
    callers = service_status(handle, headers=named)["callers"]
    rows = [r for r in callers if r["run_id"] == "d3-run"]
    assert len(rows) == 1 and rows[0]["agent_name"] == "d3-agent"

    # X-TCSEXAM-Archive-Token opens the archive (after the first fetch
    # aggregates it).
    from helpers_cde import get_submissions, wait_until

    def _terminal():
        status, merged = get_submissions(handle, sid, headers=named)
        if status == 200 and merged["count"] == 1 and merged["submissions"][0]["status"] != "running":
            return merged
        return None

    wait_until(_terminal, timeout=30, what="submission judged")
    status, body = get_archive(handle, sid, token=ARCHIVE_TOKEN, headers=RUN)
    assert status == 200
    assert json.loads(body)["session_id"] == sid

    delete_session(handle, sid, headers=named)


def test_no_legacy_header_strings_in_backend_source():
    """Grep the backend package for legacy header names. tests/ is excluded:
    test modules legitimately construct legacy headers to prove rejection
    (this file included) and carry migration provenance notes."""
    backend_root = Path(__file__).resolve().parents[1]
    assert backend_root.name == "backend"
    hits: list[str] = []
    scanned = 0
    for path in sorted(backend_root.rglob("*.py")):
        if "tests" in path.relative_to(backend_root).parts:
            continue
        scanned += 1
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            if any(pattern in line for pattern in LEGACY_PATTERNS):
                hits.append(f"{path.relative_to(backend_root)}:{lineno}: {line.strip()}")
    assert scanned > 10, "the scan must cover the backend source files"
    assert not hits, "legacy header names in backend source:\n" + "\n".join(hits)
