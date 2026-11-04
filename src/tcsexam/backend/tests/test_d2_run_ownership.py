"""D2 acceptance (261024 review fix): run ownership of judge sessions.

The effective run-id (X-TCSEXAM-Run-Id, validated by the auth middleware)
is stored on the session at create time and journaled, so ownership
survives DELETE and service restarts. Every session-level endpoint —
status, relay (submit/submissions/forward), DELETE, archive, the payload
endpoints, and the ?session_ids= reconciliation query — serves only the
owning run; a wrong run-id answers EXACTLY like an unknown sid (the uniform
404 `unknown judge session {sid}`, never 410), and the ?session_ids= query
reports a mismatched sid present=false with its counts withheld. Sessions
created WITHOUT a run-id are unowned and unrestricted (the local/legacy
compat shape). Run-id is a caller-declared label, not a credential — see
docs/backend/service.md "Security boundaries".
"""
from __future__ import annotations

import base64
import json

from helpers_cde import (
    ARCHIVE_H,
    ARCHIVE_TOKEN,
    AUTH,
    cleanup_app,
    create_session,
    delete_session,
    get_archive,
    get_payload,
    get_payload_submissions,
    get_submissions,
    http,
    http_json,
    run_in_threads,
    service_factory,
    session_ids_query,
    session_status,
    submit,
    synth,
    wait_ready,
    wait_until,
    windows,
    make_tar_gz,
)

__all__ = ["synth", "windows", "service_factory"]

RUN_A = {"X-TCSEXAM-Run-Id": "run-a", "X-TCSEXAM-Client-Id": "client-a"}
RUN_B = {"X-TCSEXAM-Run-Id": "run-b", "X-TCSEXAM-Client-Id": "client-b"}


def _session_with_records(handle, headers, *, payload_note: bytes | None = None):
    """One ready session (as `headers`) with one judged submission; returns sid."""
    body = {}
    if payload_note is not None:
        body["judge_payload"] = {"/tmp/d2own/note.txt": base64.b64encode(payload_note).decode()}
    resp = create_session(handle, headers=headers, **body)
    sid = resp["session_id"]
    wait_ready(handle, sid, headers=headers)
    status, body = submit(handle, sid, make_tar_gz({"s.py": b"d2own"}), headers=headers)
    assert status == 202, body

    def _terminal():
        status, merged = get_submissions(handle, sid, headers=headers)
        if status == 200 and merged["count"] == 1 and merged["submissions"][0]["status"] != "running":
            return merged
        return None

    wait_until(_terminal, timeout=30, what="submission judged")
    return sid


def test_wrong_run_denied_everywhere_own_run_normal(service_factory):
    handle = service_factory()
    sid = _session_with_records(handle, RUN_A, payload_note=b"run-a-private")

    unknown_url_tail = "jsess-000000000000"

    # status: wrong run -> the same 404 shape as an unknown sid.
    status, wrong = session_status(handle, sid, headers=RUN_B)
    assert status == 404
    status, unknown = session_status(handle, unknown_url_tail, headers=RUN_B)
    assert status == 404
    assert wrong["error"].replace(sid, "<sid>") == unknown["error"].replace(unknown_url_tail, "<sid>")

    # relay: wrong run cannot submit, read submissions, or forward.
    status, body = submit(handle, sid, make_tar_gz({"s.py": b"x"}), headers=RUN_B)
    assert status == 404
    assert json.loads(body)["error"] == f"unknown judge session {sid}"
    status, body = get_submissions(handle, sid, headers=RUN_B)
    assert status == 404
    status, body = http("GET", f"{handle.url}/v1/judge/sessions/{sid}/health",
                        headers={**AUTH, **RUN_B})
    assert status == 404

    # archive + payload endpoints: wrong run with a VALID archive credential
    # is still the uniform 404 (the verifier of one attempt cannot pull
    # another attempt's records or program packs).
    status, body = get_archive(handle, sid, headers=RUN_B)
    assert status == 404
    status, body = get_payload(handle, sid, headers=RUN_B)
    assert status == 404
    status, body = get_payload_submissions(handle, sid, headers=RUN_B)
    assert status == 404
    status, body = get_payload_submissions(handle, sid, 1, headers=RUN_B)
    assert status == 404

    # delete: wrong run cannot destroy the session.
    status, body = delete_session(handle, sid, headers=RUN_B)
    assert status == 404
    status, unknown_delete = delete_session(handle, unknown_url_tail, headers=RUN_B)
    assert status == 404
    assert body == {"error": f"unknown judge session {sid}"}
    assert unknown_delete == {"error": f"unknown judge session {unknown_url_tail}"}
    status, body = session_status(handle, sid, headers=RUN_A)
    assert status == 200 and body["status"] == "ready", "run-b's delete must not have happened"

    # The owning run: everything works.
    status, body = session_status(handle, sid, headers=RUN_A)
    assert status == 200
    status, merged = get_submissions(handle, sid, headers=RUN_A)
    assert status == 200 and merged["count"] == 1
    status, raw = get_archive(handle, sid, headers=RUN_A)
    assert status == 200 and json.loads(raw)["session_id"] == sid
    status, body = get_payload(handle, sid, headers=RUN_A)
    assert status == 200
    status, body = get_payload_submissions(handle, sid, 1, headers=RUN_A)
    assert status == 200
    status, body = delete_session(handle, sid, headers=RUN_A)
    assert status == 200 and body["stopped"] is True


def test_singleflight_key_includes_run_id(service_factory):
    handle = service_factory(adapter_kwargs={"create_delay": 0.4})

    # Same client-id, different run-ids: distinct sessions (one run must
    # never be merged into another run's provisioning session).
    shared_client_a = {"X-TCSEXAM-Run-Id": "run-a", "X-TCSEXAM-Client-Id": "shared-client"}
    shared_client_b = {"X-TCSEXAM-Run-Id": "run-b", "X-TCSEXAM-Client-Id": "shared-client"}
    resp_a, resp_b = run_in_threads(
        lambda: create_session(handle, headers=shared_client_a),
        lambda: create_session(handle, headers=shared_client_b),
    )
    assert resp_a["session_id"] != resp_b["session_id"]

    # Control group: same client-id AND same run-id, concurrent — one
    # shared provisioning session (the dedup still works within one run).
    # resp_a must be READY first so its in-flight key has settled: the
    # control pair then becomes the leader of a NEW group.
    wait_ready(handle, resp_a["session_id"], headers=shared_client_a)
    resp_c, resp_d = run_in_threads(
        lambda: create_session(handle, headers=shared_client_a),
        lambda: create_session(handle, headers=shared_client_a),
    )
    assert resp_c["session_id"] == resp_d["session_id"]
    assert resp_c["session_id"] != resp_a["session_id"], (
        "the singleflight key settled after the first create — this is a NEW session"
    )

    wait_ready(handle, resp_b["session_id"], headers=shared_client_b)
    wait_ready(handle, resp_c["session_id"], headers=shared_client_a)
    delete_session(handle, resp_a["session_id"], headers=shared_client_a)
    delete_session(handle, resp_b["session_id"], headers=shared_client_b)
    delete_session(handle, resp_c["session_id"], headers=shared_client_a)


def test_hibernated_session_ownership(service_factory):
    handle = service_factory(hibernate_enabled=True, hibernate_grace_seconds=0.8)
    sid = _session_with_records(handle, RUN_A)

    # Delivered + quiet past the grace: the reaper hibernates (workers
    # recycled, metadata/archive kept).
    def _hibernated():
        status, body = session_status(handle, sid, headers=RUN_A)
        if status == 200 and body.get("status") == "hibernated":
            return body
        return None

    wait_until(_hibernated, timeout=15, what="session hibernated")

    # Wrong run reading the hibernated session's history: uniform 404
    # (the archived-payload read path is ownership-gated too).
    status, body = get_submissions(handle, sid, headers=RUN_B)
    assert status == 404
    assert body["error"] == f"unknown judge session {sid}"

    # The owning run still reads its history without waking the group.
    status, merged = get_submissions(handle, sid, headers=RUN_A)
    assert status == 200
    assert merged["count"] == 1

    delete_session(handle, sid, headers=RUN_A)


def test_ownership_survives_delete(service_factory):
    handle = service_factory()
    sid = _session_with_records(handle, RUN_A, payload_note=b"run-a-private")
    status, body = delete_session(handle, sid, headers=RUN_A)
    assert status == 200 and body["stopped"] is True

    # Wrong run after DELETE: status/archive/payload all answer the uniform
    # 404 — NEVER the 410 destroyed shape (existence must not leak), even
    # with the valid archive credential.
    status, body = session_status(handle, sid, headers=RUN_B)
    assert status == 404
    assert body["error"] == f"unknown judge session {sid}"
    status, body = get_archive(handle, sid, headers=RUN_B)
    assert status == 404
    status, body = get_payload(handle, sid, headers=RUN_B)
    assert status == 404
    status, body = get_payload_submissions(handle, sid, 1, headers=RUN_B)
    assert status == 404

    # The owning run keeps the post-release retention behavior: 410 on
    # status, archive + payload still readable with the archive credential.
    status, body = session_status(handle, sid, headers=RUN_A)
    assert status == 410
    assert body["error_class"] == "terminal"
    status, raw = get_archive(handle, sid, headers=RUN_A)
    assert status == 200 and json.loads(raw)["session_id"] == sid
    status, body = get_payload(handle, sid, headers=RUN_A)
    assert status == 200
    status, body = get_payload_submissions(handle, sid, 1, headers=RUN_A)
    assert status == 200


def test_ownership_survives_restart(service_factory, tmp_path):
    state_dir = tmp_path / "restarted"
    handle = service_factory(state_dir=state_dir)
    sid = _session_with_records(handle, RUN_A)

    # Full shutdown (the sessions are destroyed), then a fresh app over the
    # same state_dir: the journal replays the ownership record.
    cleanup_app(handle)
    restarted = service_factory(state_dir=state_dir)

    # Wrong run: everything 404 / invisible after the restart too.
    status, body = session_status(restarted, sid, headers=RUN_B)
    assert status == 404
    status, body = get_archive(restarted, sid, headers=RUN_B)
    assert status == 404
    status, body = get_payload_submissions(restarted, sid, 1, headers=RUN_B)
    assert status == 404
    recon = session_ids_query(restarted, [sid], headers=RUN_B)
    assert recon["sessions"][0]["present"] is False
    assert recon["sessions"][0]["submissions"] == 0
    assert recon["total_submissions"] == 0

    # The owning run: the count and the records are still there.
    recon = session_ids_query(restarted, [sid], headers=RUN_A)
    assert recon["sessions"][0]["present"] is True
    assert recon["sessions"][0]["submissions"] == 1
    assert recon["total_submissions"] == 1
    status, raw = get_archive(restarted, sid, headers=RUN_A)
    assert status == 200 and json.loads(raw)["session_id"] == sid


def test_unowned_session_open_to_legacy_callers(service_factory):
    """Sessions created WITHOUT a run-id are unowned: callers that never
    send run-ids (local runs, legacy clients) keep working, and a caller
    that DOES send one is not locked out either. This compat shape is
    pinned deliberately — ownership only ever restricts OWNED sessions."""
    handle = service_factory()
    sid = _session_with_records(handle, None)

    # No run-id anywhere: full access.
    status, body = session_status(handle, sid)
    assert status == 200
    status, merged = get_submissions(handle, sid)
    assert status == 200 and merged["count"] == 1
    status, raw = get_archive(handle, sid)
    assert status == 200

    # A run-id-carrying caller is not locked out of an unowned session.
    status, body = session_status(handle, sid, headers=RUN_B)
    assert status == 200
    status, body = delete_session(handle, sid, headers=RUN_B)
    assert status == 200 and body["stopped"] is True


def test_session_ids_query_scoped_by_run(service_factory):
    handle = service_factory()
    sid_a = _session_with_records(handle, RUN_A)
    sid_b = _session_with_records(handle, RUN_B)

    # run-a's view: its own session present with its count; run-b's sid is
    # indistinguishable from an unknown sid (present=false, count withheld,
    # never entering the chain total).
    recon = session_ids_query(handle, [sid_a, sid_b], headers=RUN_A)
    rows = {r["session_id"]: r for r in recon["sessions"]}
    assert rows[sid_a]["present"] is True
    assert rows[sid_a]["submissions"] == 1
    assert rows[sid_b]["present"] is False
    assert rows[sid_b]["submissions"] == 0
    assert recon["total_submissions"] == 1

    # Symmetric for run-b.
    recon = session_ids_query(handle, [sid_a, sid_b], headers=RUN_B)
    rows = {r["session_id"]: r for r in recon["sessions"]}
    assert rows[sid_b]["present"] is True
    assert rows[sid_b]["submissions"] == 1
    assert rows[sid_a]["present"] is False
    assert recon["total_submissions"] == 1

    # A run-id-less query sees NEITHER owned session.
    recon = session_ids_query(handle, [sid_a, sid_b])
    rows = {r["session_id"]: r for r in recon["sessions"]}
    assert rows[sid_a]["present"] is False
    assert rows[sid_b]["present"] is False
    assert recon["total_submissions"] == 0

    delete_session(handle, sid_a, headers=RUN_A)
    delete_session(handle, sid_b, headers=RUN_B)


def test_archive_credential_still_required_for_owner(service_factory):
    """Ownership does not replace the archive credential: the owning run
    without X-TCSEXAM-Archive-Token still gets the uniform 404 (the two
    gates stack)."""
    handle = service_factory()
    sid = _session_with_records(handle, RUN_A)

    status, body = get_archive(handle, sid, token=None, headers=RUN_A)
    assert status == 404
    status, body = get_archive(handle, sid, token="wrong", headers=RUN_A)
    assert status == 404
    status, raw = get_archive(handle, sid, token=ARCHIVE_TOKEN, headers=RUN_A)
    assert status == 200

    delete_session(handle, sid, headers=RUN_A)


def test_all_listing_modes_filter_run_ownership(service_factory):
    """A shared egress and service token do not reveal another run's rows.

    The identity query is still diagnostic, but its rows and totals must
    honor the same run ownership as the ordinary list and chain query.
    Unowned sessions remain visible for legacy compatibility.
    """
    handle = service_factory()
    sid_a = _session_with_records(handle, RUN_A)
    sid_b = _session_with_records(handle, RUN_B)
    sid_legacy = _session_with_records(handle, None)

    def check_lists():
        for headers, expected in (
            (RUN_A, {sid_a, sid_legacy}),
            (RUN_B, {sid_b, sid_legacy}),
            ({}, {sid_legacy}),
        ):
            auth = {**AUTH, **ARCHIVE_H, **headers}
            status, rows = http_json("GET", f"{handle.url}/v1/judge/sessions", headers=auth)
            assert status == 200
            assert {row["session_id"] for row in rows} == expected
            for identity in ("self", "127.0.0.1"):
                status, body = http_json(
                    "GET", f"{handle.url}/v1/judge/sessions?client_ip={identity}", headers=auth
                )
                assert status == 200
                assert {row["session_id"] for row in body["sessions"]} == expected
                assert body["total_submissions"] == len(expected)

    check_lists()
    delete_session(handle, sid_a, headers=RUN_A)
    check_lists()  # The retained destroyed row has the same ownership.
    delete_session(handle, sid_b, headers=RUN_B)
    delete_session(handle, sid_legacy)


def test_delete_unknown_and_wrong_run_match_and_owner_remains_idempotent(service_factory, tmp_path):
    state_dir = tmp_path / "delete-restart"
    handle = service_factory(state_dir=state_dir)
    sid = _session_with_records(handle, RUN_A)
    unknown = "jsess-000000000000"

    def denied_and_idempotent(service):
        wrong_status, wrong = delete_session(service, sid, headers=RUN_B)
        unknown_status, missing = delete_session(service, unknown, headers=RUN_B)
        assert wrong_status == unknown_status == 404
        assert wrong == {"error": f"unknown judge session {sid}"}
        assert missing == {"error": f"unknown judge session {unknown}"}
        assert wrong["error"].replace(sid, "<sid>") == missing["error"].replace(unknown, "<sid>")
        status, body = delete_session(service, sid, headers=RUN_A)
        assert status == 200 and body == {"ok": True, "stopped": False}

    status, body = delete_session(handle, sid, headers=RUN_A)
    assert status == 200 and body["stopped"] is True
    denied_and_idempotent(handle)
    cleanup_app(handle)
    restarted = service_factory(state_dir=state_dir)
    denied_and_idempotent(restarted)
