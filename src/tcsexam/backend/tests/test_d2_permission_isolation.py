"""D2 acceptance: permission isolation.

Two credential layers: the service token pair (model side) and the
verifier-only X-TCSEXAM-Archive-Token. Covers (all over loopback HTTP):

- wrong service token -> 401 everywhere (the auth middleware runs first)
- archive/payload endpoints: wrong archive token and missing archive token
  answer the SAME 404, byte-identical; and for an unknown sid the right
  token answers that same 404 too — "session does not exist" and "bad
  credentials" are indistinguishable (the endpoints' existence never leaks)
- archive_token unconfigured -> the endpoints are disabled entirely
  (uniform 404, with or without the header, even for a journaled session)
- normal model-side credentials (token id/secret only, no archive token)
  cannot create hidden sessions, attach a judge_payload, list sessions, read
  the archive, nor read the original program packs; payload-free public
  self-test and existing-session relay paths still need only the service token
- public creation uses only explicitly mapped public-only images; empty and
  missing mappings reject before worker creation, while hidden never maps
- hidden creation, payload-bearing creation and every list/reconciliation
  query require the archive token; missing, wrong, and unconfigured
  credentials answer the same 403
"""
from __future__ import annotations

import ast
import base64
import json
import os
from pathlib import Path
import socket
import time
import urllib.error
import urllib.request

from helpers_cde import (
    ARCHIVE_H,
    AUTH,
    JUDGE_IMAGE,
    PUBLIC_JUDGE_IMAGE,
    TOKEN_ID,
    TOKEN_SECRET,
    cleanup_app,
    create_session,
    delete_session,
    get_archive,
    get_payload,
    get_payload_submissions,
    get_submissions,
    http,
    service_factory,
    session_status,
    submit,
    synth,
    wait_ready,
    wait_until,
    windows,
    make_tar_gz,
)

__all__ = ["synth", "windows", "service_factory"]

WRONG_AUTH = {"X-TCSEXAM-Token-Id": "nope", "X-TCSEXAM-Token-Secret": "nope"}


def _session_with_records(handle):
    resp = create_session(handle)
    sid = resp["session_id"]
    wait_ready(handle, sid)
    status, body = submit(handle, sid, make_tar_gz({"s.py": b"d2"}))
    assert status == 202

    def _terminal():
        status, merged = get_submissions(handle, sid)
        if status == 200 and merged["count"] == 1 and merged["submissions"][0]["status"] != "running":
            return merged
        return None

    wait_until(_terminal, timeout=30, what="submission judged")
    return sid


def test_wrong_service_token_401(service_factory):
    handle = service_factory()
    sid = _session_with_records(handle)

    status, _ = session_status(handle, sid, headers=WRONG_AUTH)
    assert status == 401
    # The verifier endpoints sit behind the same middleware: 401 first.
    status, body = get_archive(handle, sid, headers=WRONG_AUTH)
    assert status == 401
    assert json.loads(body)["error"].startswith("unauthorized")
    status, body = get_payload_submissions(handle, sid, 1, headers=WRONG_AUTH)
    assert status == 401
    delete_session(handle, sid)


def test_archive_and_payload_uniform_404(service_factory):
    handle = service_factory()
    sid = _session_with_records(handle)

    urls = [
        f"{handle.url}/v1/judge/sessions/{sid}/archive",
        f"{handle.url}/v1/judge/sessions/{sid}/payload",
        f"{handle.url}/v1/judge/sessions/{sid}/payload/submissions",
        f"{handle.url}/v1/judge/sessions/{sid}/payload/submissions/1",
    ]
    from helpers_cde import http

    for url in urls:
        status, missing = http("GET", url, headers=AUTH)  # service auth only
        assert status == 404, (url, missing)
        status, wrong = http(
            "GET", url, headers={**AUTH, "X-TCSEXAM-Archive-Token": "wrong"}
        )
        assert status == 404, (url, wrong)
        assert missing == wrong, f"{url}: missing vs wrong token must be byte-identical"

        # Same shape for an unknown sid: swap the sid in the URL; right token
        # and wrong token again collapse into the same 404.
        unknown_url = url.replace(sid, "jsess-000000000000")
        status, unknown_right = http(
            "GET", unknown_url,
            headers={**AUTH, "X-TCSEXAM-Archive-Token": handle.config.archive_token},
        )
        assert status == 404
        status, unknown_wrong = http(
            "GET", unknown_url, headers={**AUTH, "X-TCSEXAM-Archive-Token": "wrong"}
        )
        assert status == 404
        assert unknown_right == unknown_wrong
        # And the unknown-sid body has the same shape as the existing-sid
        # credential-failure body (only the sid string differs).
        assert json.loads(unknown_right)["error"].startswith("unknown judge session")
        assert json.loads(missing)["error"].startswith("unknown judge session")

    delete_session(handle, sid)


def test_model_credentials_cannot_read_records(service_factory):
    """The model side holds ONLY the token id/secret (the archive token is
    baked into the task package's tests/, mounted at verify time only)."""
    handle = service_factory()
    sid = _session_with_records(handle)

    # Service auth passes the middleware; the verifier gate answers 404.
    status, body = get_archive(handle, sid, token=None)
    assert status == 404
    status, body = get_payload(handle, sid, token=None)
    assert status == 404
    status, body = get_payload_submissions(handle, sid, token=None)
    assert status == 404
    status, body = get_payload_submissions(handle, sid, 1, token=None)
    assert status == 404

    # Sanity: with the verifier credential the same URLs answer 200.
    status, body = get_archive(handle, sid)
    assert status == 200
    status, body = get_payload_submissions(handle, sid, 1)
    assert status == 200

    delete_session(handle, sid)


def test_unconfigured_archive_token_disables_endpoints(service_factory, tmp_path):
    state_dir = tmp_path / "shared-state"
    handle = service_factory(state_dir=state_dir)
    sid = _session_with_records(handle)
    delete_session(handle, sid)
    cleanup_app(handle)

    # A service WITHOUT archive_token: the endpoints are disabled — uniform
    # 404 with or without the header, even for a journaled session.
    bare = service_factory(state_dir=state_dir, archive_token="")
    from helpers_cde import http

    for tail in ("archive", "payload", "payload/submissions", "payload/submissions/1"):
        url = f"{bare.url}/v1/judge/sessions/{sid}/{tail}"
        status, without_header = http("GET", url, headers=AUTH)
        assert status == 404, (url, without_header)
        status, with_header = http(
            "GET", url, headers={**AUTH, "X-TCSEXAM-Archive-Token": "anything"}
        )
        assert status == 404
        assert without_header == with_header


def test_model_credentials_cannot_create_hidden_or_start_worker(service_factory):
    handle = service_factory()
    url = f"{handle.url}/v1/judge/sessions"
    responses = []
    for payload in (
        {"judge_image": "registry.example.com/family-judge:1.0.0"},
        {"judge_image": "registry.example.com/family-judge:1.0.0", "instance_set": "hidden"},
    ):
        status, body = http("POST", url, headers=AUTH, json_body=payload)
        assert status == 403
        responses.append(body)

    status, wrong = http(
        "POST",
        url,
        headers={**AUTH, "X-TCSEXAM-Archive-Token": "wrong"},
        json_body={"judge_image": "registry.example.com/family-judge:1.0.0", "instance_set": "hidden"},
    )
    assert status == 403
    responses.append(wrong)
    assert len(set(responses)) == 1
    assert json.loads(responses[0]) == {"error": "valid archive token required"}
    assert handle.adapter.create_attempts == 0
    assert not handle.app["judge_sessions"]._sessions


def test_verifier_hidden_create_keeps_service_token_session_access(service_factory):
    handle = service_factory()
    status, created = http(
        "POST",
        f"{handle.url}/v1/judge/sessions",
        headers={**AUTH, **ARCHIVE_H},
        json_body={"judge_image": JUDGE_IMAGE},
    )
    assert status == 202, created
    created_body = json.loads(created)
    assert created_body["image"] == JUDGE_IMAGE
    sid = created_body["session_id"]
    wait_ready(handle, sid)
    assert handle.adapter.create_images == [JUDGE_IMAGE]

    status, info = session_status(handle, sid, headers=AUTH)
    assert status == 200
    assert info["instance_set"] == "hidden"
    status, body = submit(handle, sid, make_tar_gz({"s.py": b"d2-hidden"}), headers=AUTH)
    assert status == 202, body

    def _terminal():
        status, merged = get_submissions(handle, sid, headers=AUTH)
        if status == 200 and merged["count"] == 1 and merged["submissions"][0]["status"] != "running":
            return merged
        return None

    merged = wait_until(_terminal, timeout=30, what="hidden submission judged with service token")
    assert merged["count"] == 1


def test_public_create_submit_and_read_without_archive_token(service_factory):
    handle = service_factory()
    status, created = http(
        "POST",
        f"{handle.url}/v1/judge/sessions",
        headers=AUTH,
        json_body={"judge_image": JUDGE_IMAGE, "instance_set": "public"},
    )
    assert status == 202, created
    created_body = json.loads(created)
    assert created_body["image"] == PUBLIC_JUDGE_IMAGE
    sid = created_body["session_id"]
    wait_ready(handle, sid)
    assert handle.app["judge_sessions"].get(sid).image == PUBLIC_JUDGE_IMAGE
    assert handle.adapter.create_images == [PUBLIC_JUDGE_IMAGE]

    worker = handle.adapter.workers[0]
    agent_config = json.loads(
        (worker.root / "tcsexam-backend" / "agent_config.json").read_text()
    )
    assert agent_config["env"] == {"INSTANCE_SET": "public"}
    assert handle.config.archive_token not in json.dumps(agent_config)

    status, info = session_status(handle, sid, headers=AUTH)
    assert status == 200
    assert info["image"] == PUBLIC_JUDGE_IMAGE
    status, body = submit(handle, sid, make_tar_gz({"s.py": b"d2-public"}), headers=AUTH)
    assert status == 202, body

    def _terminal():
        status, merged = get_submissions(handle, sid, headers=AUTH)
        if status == 200 and merged["count"] == 1 and merged["submissions"][0]["status"] != "running":
            return merged
        return None

    merged = wait_until(_terminal, timeout=30, what="public submission judged without archive token")
    assert merged["count"] == 1


def test_public_create_rejects_empty_image_map(service_factory):
    handle = service_factory(public_image_map={}, judge_port=1)
    status, body = http(
        "POST",
        f"{handle.url}/v1/judge/sessions",
        headers=AUTH,
        json_body={"judge_image": JUDGE_IMAGE, "instance_set": "public"},
    )
    assert status == 403
    assert json.loads(body) == {"error": "public judge image is not allowed"}
    assert handle.adapter.create_attempts == 0
    assert not handle.app["judge_sessions"]._sessions


def test_public_create_rejects_unregistered_image(service_factory):
    handle = service_factory(judge_port=1)
    status, body = http(
        "POST",
        f"{handle.url}/v1/judge/sessions",
        headers=AUTH,
        json_body={
            "judge_image": "registry.example.com/unregistered-judge:1",
            "instance_set": "public",
        },
    )
    assert status == 403
    assert json.loads(body) == {"error": "public judge image is not allowed"}
    assert handle.adapter.create_attempts == 0
    assert not handle.app["judge_sessions"]._sessions


def test_public_payload_requires_verifier_token(service_factory):
    handle = service_factory()
    request_body = {
        "judge_image": JUDGE_IMAGE,
        "instance_set": "public",
        "judge_payload": {
            "/tmp/tcsexam-public-only.txt": base64.b64encode(b"public data\n").decode(),
        },
    }
    url = f"{handle.url}/v1/judge/sessions"
    denials = []
    for headers in (AUTH, {**AUTH, "X-TCSEXAM-Archive-Token": "wrong"}):
        status, body = http("POST", url, headers=headers, json_body=request_body)
        assert status == 403
        denials.append(body)

    bare = service_factory(archive_token="", judge_port=1)
    status, body = http(
        "POST",
        f"{bare.url}/v1/judge/sessions",
        headers={**AUTH, "X-TCSEXAM-Archive-Token": "anything"},
        json_body=request_body,
    )
    assert status == 403
    denials.append(body)
    assert len(set(denials)) == 1
    assert json.loads(denials[0]) == {"error": "valid archive token required"}
    assert handle.adapter.create_attempts == 0
    assert bare.adapter.create_attempts == 0
    assert not handle.app["judge_sessions"]._sessions
    assert not bare.app["judge_sessions"]._sessions

    status, created = http(
        "POST", url, headers={**AUTH, **ARCHIVE_H}, json_body=request_body
    )
    assert status == 202, created
    created_body = json.loads(created)
    assert created_body["image"] == PUBLIC_JUDGE_IMAGE
    sid = created_body["session_id"]
    wait_ready(handle, sid)
    assert handle.adapter.create_images == [PUBLIC_JUDGE_IMAGE]

    worker = handle.adapter.workers[0]
    agent_config = json.loads(
        (worker.root / "tcsexam-backend" / "agent_config.json").read_text()
    )
    assert agent_config["payload_files"] == request_body["judge_payload"]
    assert handle.config.archive_token not in json.dumps(agent_config)


def test_list_and_reconciliation_require_archive_token(service_factory):
    handle = service_factory()
    sid = _session_with_records(handle)
    base = f"{handle.url}/v1/judge/sessions"
    for url in (base, f"{base}?session_ids={sid}", f"{base}?client_ip=self"):
        status, missing = http("GET", url, headers=AUTH)
        assert status == 403, (url, missing)
        status, wrong = http(
            "GET", url, headers={**AUTH, "X-TCSEXAM-Archive-Token": "wrong"}
        )
        assert status == 403, (url, wrong)
        assert missing == wrong

        status, visible = http("GET", url, headers={**AUTH, **ARCHIVE_H})
        assert status == 200, (url, visible)
        assert sid.encode() in visible


def test_unconfigured_archive_token_rejects_hidden_create_and_list(service_factory):
    handle = service_factory(archive_token="")
    url = f"{handle.url}/v1/judge/sessions"
    status, without_header = http(
        "POST", url, headers=AUTH, json_body={"judge_image": "registry.example.com/family-judge:1.0.0"}
    )
    assert status == 403
    status, with_header = http(
        "POST",
        url,
        headers={**AUTH, "X-TCSEXAM-Archive-Token": "anything"},
        json_body={"judge_image": "registry.example.com/family-judge:1.0.0", "instance_set": "hidden"},
    )
    assert status == 403
    assert without_header == with_header
    assert handle.adapter.create_attempts == 0

    for suffix in ("", "?session_ids=jsess-a", "?client_ip=self"):
        status, missing = http("GET", url + suffix, headers=AUTH)
        assert status == 403
        status, configured = http(
            "GET", url + suffix, headers={**AUTH, "X-TCSEXAM-Archive-Token": "anything"}
        )
        assert status == 403
        assert missing == configured


def test_real_verifier_client_create_and_reconcile_over_http(service_factory):
    handle = service_factory()
    path = (
        Path(__file__).resolve().parents[4]
        / "tasks/solver/online/ds-pace2025/tests/fetch_final.py"
    )
    names = {
        "_std_headers", "http_get_json", "http_call", "terminal_destroyed",
        "terminal_answer", "terminal_fail", "infra_fail", "create_session",
        "wait_ready", "chain_reconcile",
    }
    tree = ast.parse(path.read_text())
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert len(functions) == len(names)

    def fail(message):
        raise AssertionError(message)

    scope = {
        "os": os, "socket": socket, "time": time, "json": json,
        "urllib": __import__("urllib"),
        "TOKEN_ID": TOKEN_ID, "TOKEN_SECRET": TOKEN_SECRET,
        "SERVICE_BASE": handle.url, "JUDGE_IMAGE": "registry.example.com/family-judge:1.0.0",
        "SESSION_TTL": 60, "N_SHARDS": 1, "RESOURCES": {},
        "CREATE_RETRIES": 1, "CREATE_RETRY_BACKOFF": 0,
        "READY_POLLS": 200, "READY_INTERVAL": 0.01,
        "CHAIN_QUERY_RETRIES": 1, "CHAIN_QUERY_BACKOFF": 0, "CHAIN_QUERY_TIMEOUT": 10,
        "infra_fail": fail, "terminal_fail": fail,
    }
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), "exec"), scope)
    token = handle.config.archive_token
    sid = scope["create_session"](token)
    assert scope["wait_ready"](sid) is None

    reconciled = scope["chain_reconcile"]([sid], token)
    assert reconciled["total"] == 0
    assert reconciled["sessions"][sid] == {
        "submissions": 0, "public_submissions": 0, "present": True,
    }
    run_id = os.environ.get("TCSEXAM_RUN_ID") or os.environ.get("HOSTNAME") or socket.gethostname()
    status, _ = delete_session(handle, sid, headers={"X-TCSEXAM-Run-Id": run_id})
    assert status == 200
