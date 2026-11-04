"""Judge-session endpoint tests (/v1/judge/sessions/*): recording fake
adapter, REAL tunnel client code (WSClient/TunnelClient in threads, like the
in-worker agent runs them), and a toy judge upstream. No real workers.

Covers: create/status/delete lifecycle, HTTP relay with header passthrough,
the global session cap (transient), platform-failure error classes,
payload/resources/ttl parsing, auth, and the TTL/idle/tunnel-drop reaper.
"""
from __future__ import annotations

import asyncio
import base64
import json
import time
import urllib.error
import urllib.request

import pytest

from conftest import ARCHIVE_TOKEN, TOKEN_ID, TOKEN_SECRET, WORK_DIR, wait_session_ready


class QuotaError(Exception):
    """Name matches a transient platform error."""


class AuthenticationError(Exception):
    """Name matches a non-transient platform error."""


# --------------------------------------------------------------------------- #
# HTTP helpers
# --------------------------------------------------------------------------- #
def _request(url: str, body=None, *, method: str = "POST", auth: bool = True, headers=None):
    """Returns (status, parsed-json-body); HTTP errors are captured, not raised."""
    data = json.dumps(body).encode() if body is not None else None
    hdrs = {"Content-Type": "application/json"}
    if auth:
        hdrs["X-TCSEXAM-Token-Id"] = TOKEN_ID
        hdrs["X-TCSEXAM-Token-Secret"] = TOKEN_SECRET
        if isinstance(body, dict) and body.get("instance_set", "hidden") == "hidden":
            hdrs["X-TCSEXAM-Archive-Token"] = ARCHIVE_TOKEN
    hdrs.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def _create(handle, image="registry.example.com/family-judge:1.0.0", **extra):
    status, resp = _request(
        f"{handle.url}/v1/judge/sessions", {"judge_image": image, **extra}
    )
    # Creation is asynchronous — 202 with status "provisioning"; the
    # tests below exercise the ready session, so wait for the flip here.
    assert status == 202, resp
    assert resp["status"] == "provisioning"
    wait_session_ready(handle, resp["session_id"])
    return resp


# --------------------------------------------------------------------------- #
# Lifecycle
# --------------------------------------------------------------------------- #
def test_create_status_delete_lifecycle(jservice):
    resp = _create(
        jservice,
        resources={"cpu": 8, "memory_mb": 16384, "storage_mb": 40960},
        ttl=7200,
    )
    sid = resp["session_id"]
    assert sid.startswith("jsess-")
    assert resp["base_url"].endswith(f"/v1/judge/sessions/{sid}")

    # Creation went through the adapter with the configured profile, the
    # caller's ttl, and the resource override merged over the spec defaults.
    call = jservice.factory.calls[0]
    assert call["image_url"] == "registry.example.com/family-judge:1.0.0"
    assert call["profile"] == "test-profile"
    assert call["ttl_seconds"] == 7200
    assert call["resources"].cpu_count == 8  # "cpu" alias mapped to cpu_count
    assert call["resources"].memory_mb == 16384
    assert call["resources"].storage_mb == 40960

    # The agent bundle landed in the worker and the agent was started;
    # its config points the tunnel at the session's app name.
    sandbox = jservice.factory.sandboxes[0]
    assert f"{WORK_DIR}/judge_session_agent.py" in sandbox.ctrl.files
    assert f"{WORK_DIR}/sandbox_agent.py" in sandbox.ctrl.files
    assert f"{WORK_DIR}/tunnel_protocol.py" in sandbox.ctrl.files
    agent_config = json.loads(sandbox.ctrl.files[f"{WORK_DIR}/agent_config.json"].decode())
    assert agent_config["app_name"] == sid
    assert agent_config["command"] == "python3 /judge/judge_worker.py"
    assert agent_config["port"] == 8082
    assert any("judge_session_agent.py" in c["args"] for c in sandbox.ctrl.run_calls)

    status, info = _request(f"{jservice.url}/v1/judge/sessions/{sid}", None, method="GET")
    assert status == 200
    assert info["session_id"] == sid
    assert info["tunnel_connected"] is True

    # Delete destroys the worker and is idempotent; status then answers
    # 410 Gone with the terminal contract, never a hanging 404.
    status, resp = _request(f"{jservice.url}/v1/judge/sessions/{sid}", None, method="DELETE")
    assert status == 200 and resp["stopped"] is True
    assert sandbox.deleted == 1
    status, resp = _request(f"{jservice.url}/v1/judge/sessions/{sid}", None, method="DELETE")
    assert status == 200 and resp["stopped"] is False
    status, resp = _request(f"{jservice.url}/v1/judge/sessions/{sid}", None, method="GET")
    assert status == 410
    assert resp == {
        "error": "judge session destroyed",
        "session_id": sid,
        "error_class": "terminal",
    }


def test_unknown_resource_keys_are_silently_dropped(jservice):
    """Forward compatibility: unknown resource knobs never reach the adapter's
    WorkerResources (cpu/mem aliases map, the rest is ignored)."""
    resp = _create(jservice, resources={"cpu_count": 6, "bogus_knob": 5})
    call = jservice.factory.calls[0]
    assert call["resources"].cpu_count == 6
    assert not hasattr(call["resources"], "bogus_knob")
    status, resp = _request(
        f"{jservice.url}/v1/judge/sessions/{resp['session_id']}", None, method="DELETE"
    )
    assert status == 200


def test_uploaded_agent_files_are_the_flat_package_files(jservice):
    """The uploaded files are byte-identical to the package's flat agent
    files and keep the bare-name import shape."""
    from tcsexam.backend.agent_files import agent_file_path

    _create(jservice)
    files = jservice.factory.sandboxes[0].ctrl.files
    for name in ("judge_session_agent.py", "sandbox_agent.py", "tunnel_protocol.py"):
        assert files[f"{WORK_DIR}/{name}"] == agent_file_path(name).read_bytes()
    assert b"from sandbox_agent import" in files[f"{WORK_DIR}/judge_session_agent.py"]
    assert b"from tunnel_protocol import" in files[f"{WORK_DIR}/sandbox_agent.py"]


def test_relay_submit_and_header_passthrough(jservice):
    sid = _create(jservice)["session_id"]
    base = f"{jservice.url}/v1/judge/sessions/{sid}"

    status, resp = _request(f"{base}/health", None, method="GET")
    assert status == 200 and resp["status"] == "ok"

    status, resp = _request(
        f"{base}/submit", {"submission_kind": "file", "code": "", "submission_role": "agent"}
    )
    assert status == 200, resp
    assert resp["submission_uuid"] == "toy-uuid-1"

    status, resp = _request(f"{base}/submissions", None, method="GET")
    assert status == 200 and resp["submissions"] == []

    # A custom header rides through the relay to the judge server.
    req = urllib.request.Request(
        f"{base}/evaluate",
        data=json.dumps({"submission_role": "final", "code": ""}).encode(),
        headers={
            "Content-Type": "application/json",
            "X-TCSEXAM-Token-Id": TOKEN_ID,
            "X-TCSEXAM-Token-Secret": TOKEN_SECRET,
            "X-TCSExam-Role-Token": "final-token-123",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        resp = json.loads(r.read())
    assert resp["status"] == "done"
    assert resp["role_token_seen"] == "final-token-123"

    # Relay to an unknown session 404s (service-level, before any tunnel).
    status, _ = _request(f"{jservice.url}/v1/judge/sessions/jsess-nope/health", None, method="GET")
    assert status == 404


def test_session_cap_is_transient(jservice):
    _create(jservice)
    _create(jservice)
    status, resp = _request(f"{jservice.url}/v1/judge/sessions", {"judge_image": "x/y:1"})
    assert status == 503
    assert resp["error_class"] == "transient"
    assert "please try again" in resp["error"]


def test_create_platform_failures_are_classified(jservice):
    """The POST itself is 202; the creation outcome lands on the
    session status ("failed" + the wire-contract error wording)."""
    from conftest import wait_session_settled

    jservice.factory.fail_with = QuotaError("pool full")
    jservice.executor.create_retry_delay_seconds = 0.1  # don't sleep out the wait
    status, resp = _request(f"{jservice.url}/v1/judge/sessions", {"judge_image": "x/y:1"})
    assert status == 202, resp
    session = wait_session_settled(jservice, resp["session_id"])
    assert session.status == "failed"
    assert "QuotaError" in session.error
    assert "please try again" in session.error
    status, info = _request(
        f"{jservice.url}/v1/judge/sessions/{resp['session_id']}", None, method="GET"
    )
    assert status == 200
    assert info["status"] == "failed"
    assert info["error"] == session.error

    jservice.factory.fail_with = AuthenticationError("bad token")
    status, resp = _request(f"{jservice.url}/v1/judge/sessions", {"judge_image": "x/y:1"})
    assert status == 202, resp
    session = wait_session_settled(jservice, resp["session_id"])
    assert session.status == "failed"
    assert "please try again" not in session.error


def test_bad_requests(jservice):
    status, resp = _request(f"{jservice.url}/v1/judge/sessions", {})
    assert status == 400 and "judge_image" in resp["error"]
    status, _ = _request(
        f"{jservice.url}/v1/judge/sessions", {"judge_image": "x", "resources": "nope"}
    )
    assert status == 400
    status, resp = _request(
        f"{jservice.url}/v1/judge/sessions",
        {"judge_image": "x", "judge_payload": {"relative/path.py": "AAAA"}},
    )
    assert status == 400 and "absolute" in resp["error"]
    status, resp = _request(
        f"{jservice.url}/v1/judge/sessions",
        {"judge_image": "x", "judge_payload": {"/judge/x.py": "!!!not-base64!!!"}},
    )
    assert status == 400 and "base64" in resp["error"]
    status, resp = _request(
        f"{jservice.url}/v1/judge/sessions",
        {"judge_image": "x", "instance_set": "sideways"},
    )
    assert status == 400 and "instance_set" in resp["error"]


def test_judge_payload_reaches_agent_config(jservice):
    """The create-time judge_payload rides into the worker's agent_config
    (the same payload the persistence layer archives)."""
    content = base64.b64encode(b"# override\n").decode()
    _create(jservice, judge_payload={"/judge/judge_worker.py": content})
    sandbox = jservice.factory.sandboxes[0]
    agent_config = json.loads(sandbox.ctrl.files[f"{WORK_DIR}/agent_config.json"].decode())
    assert agent_config["payload_files"] == {"/judge/judge_worker.py": content}


def test_auth_required(jservice):
    status, _ = _request(
        f"{jservice.url}/v1/judge/sessions", {"judge_image": "x"}, auth=False
    )
    assert status == 401
    sid = _create(jservice)["session_id"]
    status, _ = _request(
        f"{jservice.url}/v1/judge/sessions/{sid}/health", None, method="GET", auth=False
    )
    assert status == 401


# --------------------------------------------------------------------------- #
# Reaper
# --------------------------------------------------------------------------- #
def _reap_once(handle) -> None:
    store = handle.app["judge_sessions"]
    asyncio.run_coroutine_threadsafe(store._reap_once(), handle.loop).result(timeout=10)


def test_reaper_task_started(jservice):
    store = jservice.app["judge_sessions"]
    assert store._reaper_task is not None and not store._reaper_task.done()


def test_idle_reaper_destroys_idle_session(jservice):
    store = jservice.app["judge_sessions"]
    store.cfg.idle_ttl_seconds = 0.3
    sid = _create(jservice)["session_id"]
    sandbox = jservice.factory.sandboxes[0]
    _reap_once(jservice)  # still fresh: nothing happens
    assert sandbox.deleted == 0
    time.sleep(0.5)
    _reap_once(jservice)
    assert sandbox.deleted == 1, "idle session was not reaped"
    assert store.get(sid) is None


def test_expired_session_is_reaped(jservice):
    store = jservice.app["judge_sessions"]
    sid = _create(jservice, ttl=60)["session_id"]  # clamped to the 60s floor
    session = store.get(sid)
    # The TTL is re-anchored at the ready flip: expires == ready + ttl.
    assert session.expires - session.ready_at <= 61
    session.expires = time.time() - 1  # simulate TTL expiry
    _reap_once(jservice)
    assert store.get(sid) is None
    assert jservice.factory.sandboxes[0].deleted == 1


def test_tunnel_drop_marks_shard_failed_after_grace_ticks(jservice):
    """Sharded-store tunnel-drop semantics: the drop is HELD first (the
    worker survives so the agent can redial — down-ticks only accumulate);
    a shard still down after shard_down_grace_ticks reaper ticks is marked
    failed and its worker reaped; a single-shard session then flips failed
    (kept for outcome polling, not instantly destroyed)."""
    store = jservice.app["judge_sessions"]
    sid = _create(jservice)["session_id"]
    session = store.get(sid)
    sandbox = jservice.factory.sandboxes[0]
    jservice.harness.close_agents()  # the worker's tunnel client dies
    deadline = time.time() + 30
    while time.time() < deadline:
        if not jservice.app["tunnels"].is_connected(sid):
            break
        time.sleep(0.2)
    for _ in range(store.cfg.shard_down_grace_ticks - 1):
        _reap_once(jservice)
    assert store.get(sid) is not None, "a fresh tunnel drop is held for the down-grace"
    assert session.failed_shards == {}, "within the grace the shard is not failed yet"
    assert sandbox.deleted == 0, "the worker survives the grace window"
    _reap_once(jservice)  # the tick that crosses the grace
    assert 0 in session.failed_shards, "a shard down beyond the grace must be marked failed"
    assert session.status == "failed", "all shards dead: the session flips failed"
    deadline = time.time() + 10
    while time.time() < deadline and sandbox.deleted == 0:
        time.sleep(0.05)
    assert sandbox.deleted == 1, "the failed shard's worker must be reaped"


def test_shutdown_destroys_all_sessions(jservice):
    _create(jservice)
    sandbox = jservice.factory.sandboxes[0]
    asyncio.run_coroutine_threadsafe(
        jservice.app["judge_sessions"].shutdown(), jservice.loop
    ).result(timeout=10)
    assert sandbox.deleted == 1
