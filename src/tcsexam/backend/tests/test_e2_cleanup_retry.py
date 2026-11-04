"""E2 acceptance: cleanup and retry.

Covers (real local workers, loopback HTTP):

- stop_app / worker.delete are idempotent for repeated and unknown names;
  DELETE is idempotent for known sessions and returns 404 for unknown ids;
  a destroyed session's status answers 410 repeatably
- cleanup is scoped: only resources THIS service created are ever destroyed
  (a foreign worker on the adapter registry is untouched by session
  teardown and by service shutdown)
- creation retry: a first transient creation error backs off and succeeds
  (session ready, exactly one journal register — the retry never double
  registers); a non-transient error is NOT retried
- submission retry is separate from creation retry: a shard-level 4xx
  passes through verbatim and is never retried; a full fan-out failure
  answers 502 with the transient "please try again" wording
- retries and cleanup never erase counts or records: the count is right
  after a retried creation, and the archive survives cleanup
"""
from __future__ import annotations

import asyncio
import json

from helpers_cde import (
    create_session,
    delete_session,
    get_archive,
    get_submissions,
    hidden_count,
    service_factory,
    session_status,
    submit,
    synth,
    wait_ready,
    wait_session_status,
    wait_until,
    windows,
    make_tar_gz,
    write_recorder_judge,
    free_port_range,
    http,
    AUTH,
)

__all__ = ["synth", "windows", "service_factory"]


class InvalidArgumentError(Exception):
    """Name matches a NON_TRANSIENT platform error (never retried)."""


class _ForeignWorker:
    """A worker the service never created, parked on the adapter registry."""

    def __init__(self) -> None:
        self.deleted = False
        self.ctrl = self

    async def read_text(self, path: str) -> str:
        raise FileNotFoundError(path)

    async def delete(self) -> None:
        self.deleted = True


def _journal_lines(handle, sid: str) -> list[dict]:
    path = handle.state_dir / "judge_session_journal.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()
            if json.loads(line).get("sid") == sid]


def test_stop_and_delete_idempotent(service_factory):
    handle = service_factory()
    resp = create_session(handle)
    sid = resp["session_id"]
    wait_ready(handle, sid)

    # Unknown names: silent no-ops, never raised.
    asyncio.run(handle.adapter.stop_app("never-existed"))
    asyncio.run(handle.adapter.stop_app("never-existed"))

    worker = handle.adapter.sandbox_for_app(sid)
    assert worker is not None
    asyncio.run(handle.adapter.stop_app(sid))
    asyncio.run(handle.adapter.stop_app(sid))  # already gone: no-op
    asyncio.run(worker.delete())  # direct delete after stop: idempotent

    status, body = delete_session(handle, "jsess-000000000000")
    assert status == 404 and body == {"error": "unknown judge session jsess-000000000000"}
    status, body = delete_session(handle, sid)
    assert status == 200 and body["stopped"] is True
    status, body = delete_session(handle, sid)
    assert status == 200 and body["stopped"] is False

    status, body = session_status(handle, sid)
    assert status == 410 and body["error_class"] == "terminal"
    status, body = session_status(handle, sid)
    assert status == 410, "410 is terminal and repeatable"


def test_cleanup_scoped_to_own_resources(service_factory):
    handle = service_factory()
    foreign = _ForeignWorker()
    handle.adapter.register_long_lived("foreign-app", foreign)

    resp_a = create_session(handle)
    resp_b = create_session(handle, n_shards=2)
    wait_ready(handle, resp_a["session_id"])
    wait_ready(handle, resp_b["session_id"])
    delete_session(handle, resp_a["session_id"])

    from helpers_cde import cleanup_app

    cleanup_app(handle)  # service shutdown destroys the remaining session

    assert foreign.deleted is False
    assert handle.adapter.sandbox_for_app("foreign-app") is foreign
    handle.adapter._long_lived.pop("foreign-app")
    assert handle.adapter.long_lived_count() == 0


def test_create_retry_transient_then_success(service_factory):
    handle = service_factory(
        shard_boot_retries=1,
        shard_boot_retry_delay_seconds=0.05,
        adapter_kwargs={"fail_next_creates": [RuntimeError("sandbox pool temporarily full")]},
    )
    resp = create_session(handle)
    sid = resp["session_id"]

    ready = wait_ready(handle, sid, timeout=30)
    assert ready["status"] == "ready"
    assert handle.adapter.create_attempts == 2, "first attempt transient -> one retry"

    # The retry never double-registers: exactly one register event, and the
    # submission count is right afterwards.
    registers = [e for e in _journal_lines(handle, sid) if e["type"] == "register"]
    assert len(registers) == 1
    status, body = submit(handle, sid, make_tar_gz({"s.py": b"e2"}))
    assert status == 202
    assert hidden_count(handle, sid) == 1

    delete_session(handle, sid)


def test_create_no_retry_on_non_transient(service_factory):
    handle = service_factory(
        shard_boot_retries=2,
        shard_boot_retry_delay_seconds=0.05,
        ready_timeout_seconds=3,
        adapter_kwargs={"fail_next_creates": [InvalidArgumentError("bad image spec")]},
    )
    resp = create_session(handle)
    sid = resp["session_id"]

    failed = wait_session_status(handle, sid, "failed", timeout=30)
    assert handle.adapter.create_attempts == 1, "non-transient creation errors are never retried"
    assert "InvalidArgumentError" in failed["error"]
    assert "transient platform error" not in failed["error"]
    delete_session(handle, sid)


def test_submit_4xx_passthrough_and_full_fanout_502(service_factory, tmp_path, synth):
    # 4xx: the shard's own verdict passes through verbatim, never retried.
    script = write_recorder_judge(tmp_path)
    handle = service_factory(
        judge_port=free_port_range(8),
        command=f"python3 {script}",
    )
    resp = create_session(handle)
    sid = resp["session_id"]
    wait_ready(handle, sid)
    status, body = submit(handle, sid, b"BADTAR bytes")
    assert status == 400
    assert json.loads(body)["error"] == "bad submission tar (recorder)"
    status, merged = get_submissions(handle, sid)
    assert status == 200
    status, raw = get_archive(handle, sid)
    archive = json.loads(raw)
    assert archive["shard_payloads"]["0"]["bad_submits"] == 1, "no shard-level retry of a 4xx"
    delete_session(handle, sid)

    # Full fan-out failure: 502 with the transient hint (client retries),
    # distinct from the 4xx pass-through.
    handle2 = service_factory()
    resp = create_session(handle2)
    sid2 = resp["session_id"]
    wait_ready(handle2, sid2)
    synth.kill_port(handle2.config.backend.judge_sessions.judge_port)
    status, body = http(
        "POST", f"{handle2.url}/v1/judge/sessions/{sid2}/submit",
        headers={**AUTH, "Content-Type": "application/gzip"},
        body=make_tar_gz({"s.py": b"e2"}),
    )
    assert status == 502, body
    assert b"no live shard accepted the submission" in body
    assert b"please try again" in body
    delete_session(handle2, sid2)


def test_cleanup_preserves_records(service_factory):
    handle = service_factory()
    resp = create_session(handle)
    sid = resp["session_id"]
    wait_ready(handle, sid)
    status, body = submit(handle, sid, make_tar_gz({"s.py": b"keep"}))
    assert status == 202

    def _terminal():
        status, merged = get_submissions(handle, sid)
        if status == 200 and merged["count"] == 1 and merged["submissions"][0]["status"] != "running":
            return merged
        return None

    wait_until(_terminal, timeout=30, what="submission judged")

    delete_session(handle, sid)
    # Cleanup erased the worker, never the count nor the records.
    assert hidden_count(handle, sid) == 1
    status, raw = get_archive(handle, sid)
    assert status == 200
    assert json.loads(raw)["shard_payloads"]["0"]["submissions"][0]["status"] == "ok"
