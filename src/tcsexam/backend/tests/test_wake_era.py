"""Hibernate-wake submission-id era offset regression tests (no real workers).

Background: worker submission ids are 0-based (a wake re-created worker
restarts at 0). ``_wake_session`` must set ``submit_era_base`` to the
archived max id + 1 — taking the max alone collides the first post-wake
submission with the pre-hibernate last id, and the era union then drops the
fresh entry forever.

Covers:
- era_base: 0-based archive [0..N-1] -> N; empty archive -> 0
- era union: the first post-wake submission (fresh local 0) is kept, ids
  stay continuous without collisions, pre/post-hibernate submissions both
  show with their own records (A values distinguish them); a second fetch
  does not duplicate
- an empty-history session's first post-wake submission is not dropped
- in-era status migration: running->ok same-id replacement never live-locks
  (an append-only >seen filter would pin the running entry forever);
  repeated same-era fetches neither drop nor duplicate
- the defensive warning: an out-of-era fresh entry (< era_base, unreachable
  by construction) is dropped with a WARNING
- pack_sha256: aggregate_public passthrough / omitted when absent
- multi-round hibernate-wake: submit -> hibernate -> wake -> submit ->
  hibernate keeps every era's submissions in the archive (the hibernate
  probe and the client fetch share the same _era_union_payloads caliber —
  the probe never truncates history to the current era), including the
  "wake, submit, re-hibernate without a client fetch" shape
"""
from __future__ import annotations

import asyncio
import json
import logging
import tempfile
import time
from pathlib import Path

import pytest

import tcsexam.backend.sessions as js
from tcsexam.backend.config import (
    BackendConfig,
    Config,
    JudgeSessionsConfig,
)
from tcsexam.backend.sessions import JudgeSessionStore


def _config(state_dir, **judge_overrides) -> Config:
    judge = dict(
        hibernate_grace_seconds=5,
        idle_ttl_seconds=30,
        shard_boot_retries=0,
    )
    judge.update(judge_overrides)
    return Config(
        host="127.0.0.1",
        port=0,
        public_base_url="http://test",
        token_id="t",
        token_secret="s",
        state_dir=Path(state_dir),
        backend=BackendConfig(judge_sessions=JudgeSessionsConfig(**judge)),
    )


class _FakeExecutor:
    """The store-facing protocol: presence checks + a recordable stop_app."""

    def __init__(self) -> None:
        self.ready_timeout_seconds = 30.0
        self.stopped: list[str] = []

    async def create_sandbox(self, profile, image, *, ttl_seconds=None, spec=None, **kwargs):
        raise AssertionError("the tests no-op the shard boot; create must not run")

    async def stop_app(self, app_name: str) -> None:
        self.stopped.append(app_name)

    def long_lived_count(self) -> int:
        return 0

    def long_lived_memory_mb(self) -> int:
        return 0


def _make_store(config) -> JudgeSessionStore:
    store = JudgeSessionStore(executor=_FakeExecutor(), config=config)

    async def _noop_boot(session, shard, image, payload_files, spec, ttl, gate):
        return None

    store._boot_shard_with_retry = _noop_boot
    return store


def _records(n, a=5):
    return [{"instance": f"i{k}", "A": a, "B": 3, "K": 10} for k in range(n)]


class _WarnCapture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


async def _ready_session(store, image, n_shards):
    session, task = store._register_group(image, None, {"memory_mb": 1024}, 600.0, n_shards)
    task.cancel()
    try:
        await task
    except BaseException:  # noqa: BLE001
        pass
    await store._provision_group(session, image, None, {"memory_mb": 1024}, 600.0)
    session.shard_sizes = {i: 2 for i in range(n_shards)}
    return session


def _fake(payload_by_shard):
    async def _fake_call(store_, session_, method, path, *, body=b"", timeout=30):
        return {
            i: (200, {}, json.dumps(payload_by_shard[i]).encode())
            for i in payload_by_shard
        }

    return _fake_call


@pytest.fixture
def store(tmp_path):
    return _make_store(_config(tmp_path))


def test_era_base_and_first_wake_submission(store, monkeypatch) -> None:
    async def main() -> None:
        sess = await _ready_session(store, "reg/x-judge:era", 2)
        pre = {"submissions": [
            {"submission": 0, "status": "ok", "records": _records(2, a=5)},
            {"submission": 1, "status": "ok", "records": _records(2, a=5)},
        ]}
        sess.shard_payloads = {0: pre, 1: pre}
        await store._wake_session(sess)
        assert sess.submit_era_base == 2, "archive [0,1] -> era_base=2"

        fresh1 = {"submissions": [{"submission": 0, "status": "ok", "records": _records(2, a=6)}]}
        monkeypatch.setattr(js, "_call_shards", _fake({0: fresh1, 1: fresh1}))
        resp = await js._merged_submissions(store, sess)
        body = json.loads(resp.body)
        ids = [e["submission"] for e in body["submissions"]]
        assert ids == [0, 1, 2], "merged history continuous without collisions"
        a_by_id = {
            e["submission"]: sorted({r.get("A") for r in (e.get("records") or [])})
            for e in body["submissions"]
        }
        assert a_by_id.get(0) == [5] and a_by_id.get(1) == [5], "pre-hibernate submissions kept"
        assert a_by_id.get(2) == [6], "the post-wake submission lands at #2"

        fresh2 = {"submissions": [
            {"submission": 0, "status": "ok", "records": _records(2, a=6)},
            {"submission": 1, "status": "ok", "records": _records(2, a=7)},
        ]}
        monkeypatch.setattr(js, "_call_shards", _fake({0: fresh2, 1: fresh2}))
        resp = await js._merged_submissions(store, sess)
        ids2 = [e["submission"] for e in json.loads(resp.body)["submissions"]]
        assert ids2 == [0, 1, 2, 3], "second fetch: no duplicates"

    asyncio.run(main())


def test_empty_history_first_post_wake_submission_kept(store, monkeypatch) -> None:
    async def main() -> None:
        sess0 = await _ready_session(store, "reg/x-judge:empty", 2)
        empty = {"submissions": []}
        sess0.shard_payloads = {0: empty, 1: empty}
        await store._wake_session(sess0)
        assert sess0.submit_era_base == 0, "empty archive -> era_base=0"
        fresh1 = {"submissions": [{"submission": 0, "status": "ok", "records": _records(2, a=6)}]}
        monkeypatch.setattr(js, "_call_shards", _fake({0: fresh1, 1: fresh1}))
        resp = await js._merged_submissions(store, sess0)
        ids0 = [e["submission"] for e in json.loads(resp.body)["submissions"]]
        assert ids0 == [0]

        # Empty shard archive with a nonzero era base: fresh entries are all
        # kept (offset onto the continuous sequence).
        sess0.submit_era_base = 3
        sess0.shard_payloads = {0: {"submissions": []}, 1: {"submissions": []}}
        resp = await js._merged_submissions(store, sess0)
        ids0b = [e["submission"] for e in json.loads(resp.body)["submissions"]]
        assert ids0b == [3]

    asyncio.run(main())


def test_in_era_running_to_ok_replacement(store, monkeypatch) -> None:
    async def main() -> None:
        sess_r = await _ready_session(store, "reg/x-judge:flip", 2)
        sess_r.submit_era_base = 2
        archived_flip = {"submissions": [
            {"submission": 0, "status": "ok", "records": _records(2, a=5)},
            {"submission": 1, "status": "ok", "records": _records(2, a=5)},
            {"submission": 2, "status": "running", "records": None},
        ]}
        sess_r.shard_payloads = {0: archived_flip, 1: archived_flip}
        flip_ok = {"submissions": [{"submission": 0, "status": "ok", "records": _records(2, a=6)}]}
        monkeypatch.setattr(js, "_call_shards", _fake({0: flip_ok, 1: flip_ok}))
        resp = await js._merged_submissions(store, sess_r)
        body_flip = json.loads(resp.body)
        ids_flip = [e["submission"] for e in body_flip["submissions"]]
        assert ids_flip == [0, 1, 2]
        st_flip = {e["submission"]: e["status"] for e in body_flip["submissions"]}
        assert st_flip.get(2) == "ok", "in-era #2 flips running -> ok (same-id replacement)"
        a_flip = sorted({r.get("A") for r in body_flip["submissions"][2].get("records") or []})
        assert a_flip == [6]

        # Same-era second fetch: replacement dedup, history neither lost nor duplicated.
        resp = await js._merged_submissions(store, sess_r)
        ids_flip2 = [e["submission"] for e in json.loads(resp.body)["submissions"]]
        assert ids_flip2 == [0, 1, 2]

    asyncio.run(main())


def test_out_of_era_fresh_entry_dropped_with_warning(store, monkeypatch) -> None:
    async def main() -> None:
        sess_w = await _ready_session(store, "reg/x-judge:warn", 2)
        sess_w.submit_era_base = 3
        sess_w.shard_payloads = {
            0: {"submissions": [{"submission": 0, "status": "ok", "records": _records(2)}]},
            1: {"submissions": [{"submission": 0, "status": "ok", "records": _records(2)}]},
        }
        bogus = {"submissions": [{"submission": -1, "status": "ok", "records": _records(2)}]}
        capture = _WarnCapture()
        js.LOGGER.addHandler(capture)
        try:
            monkeypatch.setattr(js, "_call_shards", _fake({0: bogus, 1: bogus}))
            resp = await js._merged_submissions(store, sess_w)
        finally:
            js.LOGGER.removeHandler(capture)
        ids_w = [e["submission"] for e in json.loads(resp.body)["submissions"]]
        assert ids_w == [0], "the out-of-era fresh entry is dropped (history untouched)"
        warn_lines = [r.getMessage() for r in capture.records if r.levelno >= logging.WARNING]
        assert any("era union dropping fresh submission" in m for m in warn_lines)

    asyncio.run(main())


def test_pack_sha256_aggregate_public_passthrough() -> None:
    pub_payload = {
        "submissions": [{
            "submission": 0, "ts": 1.0, "status": "ok", "detail": "",
            "records": [{"instance": "p0", "A": 2, "B": 1, "K": 4, "status": "ok", "detail": ""}],
            "pack_sha256": "ab" * 32,
        }]
    }
    out = js.aggregate_public([pub_payload], n_shards=1)
    assert out["submissions"][0].get("pack_sha256") == "ab" * 32
    old_worker = {
        "submissions": [{
            "submission": 0, "ts": 1.0, "status": "ok", "detail": "",
            "records": [{"instance": "p0", "A": 2, "B": 1, "K": 4, "status": "ok", "detail": ""}],
        }]
    }
    out2 = js.aggregate_public([old_worker], n_shards=1)
    assert "pack_sha256" not in out2["submissions"][0]
    out3 = js.aggregate_public([old_worker, pub_payload], n_shards=2)
    assert out3["submissions"][0].get("pack_sha256") == "ab" * 32


def test_multi_round_hibernate_wake_archive_keeps_all_eras(tmp_path, monkeypatch) -> None:
    async def main() -> None:
        store_m = _make_store(_config(tmp_path))
        sess_m, task_m = store_m._register_group(
            "reg/x-judge:multi", None, {"memory_mb": 1024}, 600.0, 2
        )
        task_m.cancel()
        try:
            await task_m
        except BaseException:  # noqa: BLE001
            pass
        await store_m._provision_group(sess_m, "reg/x-judge:multi", None, {"memory_mb": 1024}, 600.0)
        sess_m.shard_sizes = {0: 2, 1: 2}

        # Per-shard on-duty worker state (0-based ids; a wake = fresh workers
        # = state cleared).
        workers: dict[int, list] = {0: [], 1: []}

        async def _live_call(store_, session_, method, path, *, body=b"", timeout=30):
            return {
                i: (200, {}, json.dumps({"submissions": list(workers[i])}).encode())
                for i in (0, 1)
            }

        def _submit(a):
            for i in (0, 1):
                workers[i].append({
                    "submission": len(workers[i]), "ts": time.time(), "status": "ok",
                    "records": _records(2, a=a), "detail": "",
                })

        def _archive_ids():
            return sorted(e["submission"] for e in sess_m.shard_payloads[0]["submissions"])

        monkeypatch.setattr(js, "_call_shards", _live_call)
        # Era 1: submit (A=5) -> fetch/deliver -> hibernate.
        _submit(5)
        await js._merged_submissions(store_m, sess_m)
        await store_m._hibernate_if_settled(sess_m)
        assert sess_m.status == "hibernated"
        assert _archive_ids() == [0]

        # Wake -> era 2: fresh workers (state cleared), submit (A=6) -> fetch
        # -> re-hibernate.
        await store_m._wake_session(sess_m)
        workers[0].clear()
        workers[1].clear()
        _submit(6)
        resp = await js._merged_submissions(store_m, sess_m)
        ids_m2 = [e["submission"] for e in json.loads(resp.body)["submissions"]]
        assert ids_m2 == [0, 1]
        await store_m._hibernate_if_settled(sess_m)
        assert _archive_ids() == [0, 1], "re-hibernate keeps every era (the probe never truncates)"

        # Wake -> era 3: submit (A=7) and re-hibernate WITHOUT a client fetch.
        await store_m._wake_session(sess_m)
        assert sess_m.submit_era_base == 2
        workers[0].clear()
        workers[1].clear()
        _submit(7)
        await store_m._hibernate_if_settled(sess_m)
        assert _archive_ids() == [0, 1, 2], "the probe runs the same era union itself"
        a3 = {
            e["submission"]: sorted({r.get("A") for r in (e.get("records") or [])})
            for e in sess_m.shard_payloads[0]["submissions"]
        }
        assert a3.get(0) == [5] and a3.get(1) == [6] and a3.get(2) == [7]

        # The archive file (the verifier's ingredient layer) and the
        # hibernated in-memory history are equally complete.
        arch = json.loads(
            (tmp_path / "judge_archive" / f"{sess_m.session_id}.json").read_text()
        )
        file_ids = sorted(e["submission"] for e in arch["shard_payloads"]["0"]["submissions"])
        assert file_ids == [0, 1, 2]
        resp_mem = js._submissions_from_memory(store_m, sess_m)
        mem_ids = [e["submission"] for e in json.loads(resp_mem.body)["submissions"]]
        assert mem_ids == [0, 1, 2]

    asyncio.run(main())
