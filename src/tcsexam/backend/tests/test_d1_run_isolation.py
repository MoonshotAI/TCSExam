"""D1 acceptance: run isolation.

Same token, same source address (loopback for both runs — a shared-egress
shape): two runs (different X-TCSEXAM-Run-Id / X-TCSEXAM-Client-Id) must
never merge. Covers (all over loopback HTTP):

- concurrent creates with different client ids do NOT share a provisioning
  session (the singleflight key carries client_id)
- concurrent creates with NO client id NEVER share (a shared egress address
  must not merge unrelated runs into one provisioning session)
- concurrent creates with the same client id DO share (singleflight control
  group: one session, one worker creation)
- submission counts are independent per session
- archive/payload layers are independent per session (each run's pack bytes
  land only in its own session's records)
- run identity is stable across requests: every request carrying the same
  X-TCSEXAM-Run-Id (+ X-TCSEXAM-Agent-Name) merges into one callers row at
  /v1/status
"""
from __future__ import annotations

import json

from helpers_cde import (
    AUTH,
    create_session,
    delete_session,
    get_archive,
    get_payload_submissions,
    get_submissions,
    run_in_threads,
    service_factory,
    session_ids_query,
    session_status,
    sha256_hex,
    submit,
    synth,
    wait_ready,
    wait_until,
    windows,
    make_tar_gz,
)
from tcsexam.backend.config import SubmissionCapConfig

__all__ = ["synth", "windows", "service_factory"]

RUN_A = {"X-TCSEXAM-Run-Id": "run-a", "X-TCSEXAM-Agent-Name": "agent-a",
         "X-TCSEXAM-Client-Id": "client-a"}
RUN_B = {"X-TCSEXAM-Run-Id": "run-b", "X-TCSEXAM-Agent-Name": "agent-b",
         "X-TCSEXAM-Client-Id": "client-b"}


def _terminal(handle, sid, *, headers=None):
    def _poll():
        status, merged = get_submissions(handle, sid, headers=headers)
        if status == 200 and merged["count"] >= 1 and all(
            e["status"] != "running" for e in merged["submissions"]
        ):
            return merged
        return None

    return wait_until(_poll, timeout=30, what=f"{sid} judged")


def test_concurrent_creates_never_merge_without_client_id(service_factory):
    handle = service_factory(adapter_kwargs={"create_delay": 0.4})

    # Different run ids AND different client ids: distinct sessions.
    resp_a, resp_b = run_in_threads(
        lambda: create_session(handle, headers=RUN_A),
        lambda: create_session(handle, headers=RUN_B),
    )
    assert resp_a["session_id"] != resp_b["session_id"]

    # No client id at all (two unrelated runs behind the same egress):
    # still distinct sessions — sharing requires the explicit header.
    resp_c, resp_d = run_in_threads(
        lambda: create_session(handle),
        lambda: create_session(handle),
    )
    assert resp_c["session_id"] != resp_d["session_id"]
    assert len({resp_a["session_id"], resp_b["session_id"],
                resp_c["session_id"], resp_d["session_id"]}) == 4

    # Owned sessions are polled/destroyed under their own run-id (the
    # ownership check answers other run-ids — including no run-id — 404).
    for sid, headers in ((resp_a["session_id"], RUN_A), (resp_b["session_id"], RUN_B),
                         (resp_c["session_id"], None), (resp_d["session_id"], None)):
        wait_ready(handle, sid, headers=headers)
        delete_session(handle, sid, headers=headers)


def test_same_client_id_shares_singleflight(service_factory):
    handle = service_factory(adapter_kwargs={"create_delay": 0.4})
    resp_a, resp_b = run_in_threads(
        lambda: create_session(handle, headers=RUN_A),
        lambda: create_session(handle, headers=RUN_A),
    )
    assert resp_a["session_id"] == resp_b["session_id"], (
        "same token + same client id + same image: one shared provisioning session"
    )
    wait_ready(handle, resp_a["session_id"], headers=RUN_A)
    # One shared group create: exactly one worker was ever created.
    assert handle.adapter.create_attempts == 1
    delete_session(handle, resp_a["session_id"], headers=RUN_A)


def test_runs_isolated_end_to_end(service_factory):
    handle = service_factory(submission_cap=SubmissionCapConfig(enabled=True, default=10))
    resp_a = create_session(handle, headers=RUN_A)
    resp_b = create_session(handle, headers=RUN_B)
    sid_a, sid_b = resp_a["session_id"], resp_b["session_id"]
    assert sid_a != sid_b
    wait_ready(handle, sid_a, headers=RUN_A)
    wait_ready(handle, sid_b, headers=RUN_B)

    pack_a = make_tar_gz({"run": b"a"})
    pack_b = make_tar_gz({"run": b"b"})
    for _ in range(2):
        status, body = submit(handle, sid_a, pack_a, headers=RUN_A)
        assert status == 202, body
    status, body = submit(handle, sid_b, pack_b, headers=RUN_B)
    assert status == 202, body

    # Counts are independent per session — and scoped per run: each run's
    # reconciliation view covers its own session only (the other run's sid
    # reports present=false, withheld from the chain total).
    recon_a = session_ids_query(handle, [sid_a, sid_b], headers=RUN_A)
    rows_a = {r["session_id"]: r for r in recon_a["sessions"]}
    assert rows_a[sid_a]["submissions"] == 2
    assert rows_a[sid_a]["present"] is True
    assert rows_a[sid_b]["present"] is False
    assert rows_a[sid_b]["submissions"] == 0
    assert recon_a["total_submissions"] == 2
    recon_b = session_ids_query(handle, [sid_a, sid_b], headers=RUN_B)
    rows_b = {r["session_id"]: r for r in recon_b["sessions"]}
    assert rows_b[sid_b]["submissions"] == 1
    assert rows_b[sid_b]["present"] is True
    assert rows_b[sid_a]["present"] is False
    assert recon_b["total_submissions"] == 1

    _terminal(handle, sid_a, headers=RUN_A)
    _terminal(handle, sid_b, headers=RUN_B)

    # Each run's records carry only its own pack (archive + verbatim body).
    status, raw = get_archive(handle, sid_a, headers=RUN_A)
    assert status == 200
    archive_a = json.loads(raw)
    assert archive_a["session_id"] == sid_a
    assert archive_a["shard_payloads"]["0"]["submissions"][0]["pack_sha256"] == sha256_hex(pack_a)
    status, raw = get_archive(handle, sid_b, headers=RUN_B)
    assert status == 200
    archive_b = json.loads(raw)
    assert archive_b["session_id"] == sid_b
    assert archive_b["shard_payloads"]["0"]["submissions"][0]["pack_sha256"] == sha256_hex(pack_b)

    status, body = get_payload_submissions(handle, sid_a, 1, headers=RUN_A)
    assert status == 200 and sha256_hex(body) == sha256_hex(pack_a)
    status, body = get_payload_submissions(handle, sid_b, 1, headers=RUN_B)
    assert status == 200 and sha256_hex(body) == sha256_hex(pack_b)

    # Identity stability: every run-a request (create, submits, fetches, and
    # this explicit status read) merges into ONE callers row.
    status, _ = session_status(handle, sid_a, headers=RUN_A)
    assert status == 200
    from helpers_cde import service_status

    callers = service_status(handle, headers=RUN_A)["callers"]
    rows_a = [r for r in callers if r["run_id"] == "run-a"]
    assert len(rows_a) == 1, f"run-a must merge into one callers row: {rows_a}"
    assert rows_a[0]["agent_name"] == "agent-a"
    assert rows_a[0]["token_id"] == "cde-token-id"
    assert rows_a[0]["requests_300s"] >= 6
    rows_b = [r for r in callers if r["run_id"] == "run-b"]
    assert len(rows_b) == 1 and rows_b[0]["agent_name"] == "agent-b"

    delete_session(handle, sid_a, headers=RUN_A)
    delete_session(handle, sid_b, headers=RUN_B)
