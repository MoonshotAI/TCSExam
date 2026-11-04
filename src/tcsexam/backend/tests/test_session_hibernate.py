"""Session hibernation tests (no real workers).

Covers:
- config parsing: hibernate_enabled / hibernate_grace_seconds
- _latest_submission_complete: settled / mid-judging / no-submission shapes
- full cycle: ready -> delivered + quiet past grace -> hibernate (probe
  confirms, workers recycled, expires re-anchored, metadata kept) -> wake
  (era base, in-flight accounting, rebuilt ready)
- probe veto: delivered but the probe sees mid-judging -> no hibernate
- idle_ttl path: enabled -> hibernate, disabled -> the legacy destroy
- era union: the merged history after a wake keeps pre-hibernate
  submissions, ids continuous, no duplicates on refetch
- cold-worker call grace and the all-shards-dead session flip
"""
from __future__ import annotations

import asyncio
import json
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


def _config(state_dir, hibernate_enabled=True, **judge_overrides) -> Config:
    judge = dict(
        hibernate_enabled=hibernate_enabled,
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


def test_config_parsing(tmp_path) -> None:
    cfg = _config(tmp_path)
    sessions = cfg.backend.judge_sessions
    assert sessions.hibernate_enabled is True
    assert sessions.hibernate_grace_seconds == 5.0
    cfg2 = _config(tmp_path)
    assert JudgeSessionsConfig().hibernate_grace_seconds == 1800.0
    cfg3 = _config(tmp_path, hibernate_enabled=False)
    assert cfg3.backend.judge_sessions.hibernate_enabled is False


class _FakeExecutor:
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


def test_latest_submission_complete() -> None:
    sess = js.JudgeSession(
        session_id="jsess-t", image="reg/x:1", created=0.0, last_active=0.0, expires=0.0,
        shards=[js.Shard(index=0, app_name="a0"), js.Shard(index=1, app_name="a1")],
    )
    sess.shard_sizes = {0: 2, 1: 2}
    ok_entry = {"submission": 1, "status": "ok", "records": _records(2)}
    full = {0: {"submissions": [ok_entry]}, 1: {"submissions": [ok_entry]}}
    assert js._latest_submission_complete(sess, full), "all shards terminal -> settled"
    running_part = {0: {"submissions": [{"submission": 1, "status": "running", "records": _records(1)}]},
                    1: {"submissions": [ok_entry]}}
    assert not js._latest_submission_complete(sess, running_part), "one shard running -> not settled"
    records_less = {0: {"submissions": [{"submission": 1, "status": "ok", "records": None}]},
                    1: {"submissions": [{"submission": 1, "status": "judge_error", "records": None}]}}
    assert js._latest_submission_complete(sess, records_less), "record-less terminal entries settle"
    missing = {0: {"submissions": [ok_entry]}, 1: {"submissions": []}}
    assert not js._latest_submission_complete(sess, missing), "one shard missing the entry -> not settled"
    assert js._latest_submission_complete(sess, {0: {"submissions": []}, 1: {"submissions": []}}), \
        "no submissions -> settled (nothing in flight)"
    sess.failed_shards = {1: "boom"}
    assert js._latest_submission_complete(sess, {0: {"submissions": [ok_entry]}}), \
        "a failed shard does not block settled"


@pytest.fixture
def store(tmp_path):
    return _make_store(_config(tmp_path))


async def _ready_session(store, image, n_shards):
    session, task = store._register_group(image, None, {"memory_mb": 1024}, 600.0, n_shards)
    task.cancel()
    try:
        await task
    except BaseException:  # noqa: BLE001
        pass
    await store._provision_group(session, image, None, {"memory_mb": 1024}, 600.0)
    return session


def test_full_hibernate_wake_cycle(store, monkeypatch) -> None:
    async def main() -> None:
        session = await _ready_session(store, "reg/x-judge:1", 2)
        assert session.status == "ready"

        payload = {"submissions": [{"submission": 0, "status": "ok", "records": _records(2)}]}
        session.shard_sizes = {0: 2, 1: 2}
        session.shard_payloads = {0: payload, 1: payload}
        session.delivered = True
        session.last_active = time.time() - 10  # > grace(5s)

        async def fake_ok(store_, session_, method, path, *, body=b"", timeout=30):
            return {i: (200, {}, json.dumps(payload).encode()) for i in (0, 1)}

        monkeypatch.setattr(js, "_call_shards", fake_ok)
        await store._reap_once()
        assert session.status == "hibernated", "delivered + quiet past grace -> hibernate"
        assert sorted(store._executor.stopped) == [
            session.shards[0].app_name, session.shards[1].app_name,
        ], "hibernate recycles the whole worker group"
        assert abs(session.expires - (time.time() + 600.0)) < 10, "expires re-anchored to now+ttl"
        assert store.get(session.session_id) is session, "metadata/archive kept"

        # Wake.
        wake_task = store._wake_session(session)
        await wake_task
        assert session.status == "ready", "the wake rebuilds to ready"
        # Worker submission ids are 0-based: archive [0] offsets by 0+1.
        assert session.submit_era_base == 1, "era_base = archived max id + 1"

        # Era union: the fresh worker restarts at local id 0; the archive has #0.
        fresh1 = {"submissions": [{"submission": 0, "status": "ok", "records": _records(2, a=6)}]}

        async def fake_fresh1(store_, session_, method, path, *, body=b"", timeout=30):
            return {i: (200, {}, json.dumps(fresh1).encode()) for i in (0, 1)}

        monkeypatch.setattr(js, "_call_shards", fake_fresh1)
        resp = await js._merged_submissions(store, session)
        body1 = json.loads(resp.body)
        ids1 = [e["submission"] for e in body1["submissions"]]
        assert ids1 == [0, 1], "era union: history [0, 1] continuous, nothing lost"
        assert session.delivered is True, "delivered re-stamped"

        # Second fetch: the fresh worker carries the whole post-wake history
        # (local 0,1) -> no duplicate ids.
        fresh2 = {"submissions": [
            {"submission": 0, "status": "ok", "records": _records(2, a=6)},
            {"submission": 1, "status": "ok", "records": _records(2, a=7)},
        ]}

        async def fake_fresh2(store_, session_, method, path, *, body=b"", timeout=30):
            return {i: (200, {}, json.dumps(fresh2).encode()) for i in (0, 1)}

        monkeypatch.setattr(js, "_call_shards", fake_fresh2)
        resp = await js._merged_submissions(store, session)
        ids2 = [e["submission"] for e in json.loads(resp.body)["submissions"]]
        assert ids2 == [0, 1, 2], "second fetch: no duplicate ids"

    asyncio.run(main())


def test_probe_veto_and_idle_ttl_paths(store, monkeypatch) -> None:
    async def main() -> None:
        session2 = await _ready_session(store, "reg/x-judge:2", 1)
        session2.shard_sizes = {0: 2}
        session2.delivered = True
        session2.last_active = time.time() - 10
        judging = {"submissions": [{"submission": 1, "status": "running", "records": _records(1)}]}
        ok_payload = {"submissions": [{"submission": 1, "status": "ok", "records": _records(2)}]}

        async def fake_judging(store_, session_, method, path, *, body=b"", timeout=30):
            return {0: (200, {}, json.dumps(judging).encode())}

        async def fake_ok(store_, session_, method, path, *, body=b"", timeout=30):
            return {0: (200, {}, json.dumps(ok_payload).encode())}

        monkeypatch.setattr(js, "_call_shards", fake_judging)
        await store._reap_once()
        assert session2.status == "ready", "probe sees mid-judging -> no hibernate"

        # idle_ttl path (hibernate enabled): not delivered but quiet past
        # idle_ttl -> still hibernate (not destroy), probe permitting.
        session2.delivered = False
        session2.last_active = time.time() - 31
        await store._reap_once()
        assert session2.status == "ready", "idle_ttl: probe mid-judging still vetoes"
        monkeypatch.setattr(js, "_call_shards", fake_ok)
        session2.last_active = time.time() - 31
        await store._reap_once()
        assert session2.status == "hibernated", "idle_ttl: settled -> hibernate (not destroy)"

    asyncio.run(main())


def test_hibernate_disabled_falls_back_to_destroy(tmp_path, monkeypatch) -> None:
    async def main() -> None:
        store_off = _make_store(_config(tmp_path, hibernate_enabled=False))
        s3 = await _ready_session(store_off, "reg/x-judge:3", 1)
        s3.last_active = time.time() - 31
        await store_off._reap_once()
        assert store_off.get(s3.session_id) is None, "hibernate disabled: idle_ttl destroys"

    asyncio.run(main())


def test_ready_at_stamped_on_ready_flip(store) -> None:
    async def main() -> None:
        session = await _ready_session(store, "reg/x-judge:1", 1)
        assert session.ready_at > 0

    asyncio.run(main())


def test_cold_worker_call_grace(store) -> None:
    async def main() -> None:
        session = await _ready_session(store, "reg/x-judge:1", 1)

        class _TimeoutTunnels:
            async def call(self, app_name, method, path, body=b""):
                raise TimeoutError("simulated cold worker")

        store._tunnels = _TimeoutTunnels()
        session.ready_at = time.time()  # just flipped ready
        res = await js._call_shards(store, session, "GET", "/submissions", timeout=5)
        assert not session.failed_shards, "transport failure inside the boot grace: not marked"
        assert res == {}, "the failed leg has no result (the caller 502s and backs off)"
        session.ready_at = time.time() - 301  # beyond the grace
        await js._call_shards(store, session, "GET", "/submissions", timeout=5)
        assert 0 in session.failed_shards, "past the grace the shard is marked failed"

    asyncio.run(main())


def test_all_shards_dead_flips_session_failed(tmp_path) -> None:
    async def main() -> None:
        store = _make_store(_config(tmp_path))
        s4 = js.JudgeSession(
            session_id="jsess-dead", image="reg/x:1", created=0.0, last_active=0.0, expires=0.0,
            shards=[js.Shard(index=i, app_name=f"d{i}") for i in range(3)],
            status="ready",
        )
        js._mark_shard_failed(store, s4, 0, "boom0")
        js._mark_shard_failed(store, s4, 1, "boom1")
        assert s4.status == "ready", "2/3 shards dead: the session stays ready"
        js._mark_shard_failed(store, s4, 2, "boom2")
        assert s4.status == "failed", "3/3 dead: the session flips failed"
        assert "create a new judge session" in (s4.error or "")
        js._mark_shard_failed(store, s4, 2, "boom2-again")
        assert s4.error.count("create a new judge session") == 1, "re-marking is idempotent"

    asyncio.run(main())
