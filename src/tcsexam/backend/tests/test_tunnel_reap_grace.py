"""Tunnel-close no longer instantly kills the worker (regression tests, no
real workers).

Background: a tunnel drop used to stop the worker on the spot — transient
flaps (gateway/proxy, workers reconnecting within seconds) were amplified
into permanent deaths. Now a live session's shard drop is owned by the
shard-level down-grace (shard_down_grace_ticks reaper ticks): a reconnect
within the grace resets and heals; only a shard still down past the grace is
marked failed and reaped. Apps outside the store's ledger keep the
immediate-teardown path.

Covers:
- claim: a ready/provisioning session's shard drop is claimed, stop_app not
  called
- reconnect within grace: down-ticks reset, shard not failed, worker alive
- past grace: marked failed + worker reaped (both the _mark_down_shards tick
  path and the direct _mark_shard_failed path)
- outside the ledger: unknown app / non-ready session -> immediate reap
- the server-layer callback end to end: claimed -> no delete; unclaimed ->
  delete
"""
from __future__ import annotations

import asyncio
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
from tcsexam.backend.server import _reap_closed_tunnel


def _config(state_dir) -> Config:
    return Config(
        host="127.0.0.1",
        port=0,
        public_base_url="http://test",
        token_id="t",
        token_secret="s",
        state_dir=Path(state_dir),
        backend=BackendConfig(
            judge_sessions=JudgeSessionsConfig(
                shard_down_grace_ticks=4,
                shard_boot_retries=0,
            )
        ),
    )


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


class _FakeTunnels:
    def __init__(self):
        self.connected = set()
        self.session_tokens = {}

    def is_connected(self, app_name):
        return app_name in self.connected

    def in_flight(self, app_name):
        return 0

    async def close(self, app_name):
        self.connected.discard(app_name)
        self.session_tokens.pop(app_name, None)


@pytest.fixture
def env(tmp_path):
    store = JudgeSessionStore(executor=_FakeExecutor(), config=_config(tmp_path))

    async def _noop_boot(session, shard, image, payload_files, spec, ttl, gate):
        return None

    store._boot_shard_with_retry = _noop_boot
    tunnels = _FakeTunnels()
    store.attach_tunnels(tunnels)
    return store, tunnels


async def _ready_session(store, n=2, status="ready"):
    session, task = store._register_group("reg/x-judge:1", None, {"memory_mb": 1024}, 600.0, n)
    task.cancel()
    try:
        await task
    except BaseException:  # noqa: BLE001
        pass
    await store._provision_group(session, "reg/x-judge:1", None, {"memory_mb": 1024}, 600.0)
    if status != "ready":
        session.status = status
    return session


def test_claim_holds_live_session_shards(env) -> None:
    async def main() -> None:
        store, tunnels = env
        session = await _ready_session(store)
        apps = [s.app_name for s in session.shards]
        assert store.claim_shard_tunnel_close(apps[0]) is True
        assert store._executor.stopped == [], "a claimed drop never stops the worker"
        assert store.claim_shard_tunnel_close(apps[1]) is True, "ready-session shards are claimed"

    asyncio.run(main())


def test_reconnect_within_grace_resets_down_ticks(env) -> None:
    async def main() -> None:
        store, tunnels = env
        session = await _ready_session(store)
        apps = [s.app_name for s in session.shards]
        for _ in range(2):
            assert await store._mark_down_shards(session) is False
        assert all(session.shard_down_ticks.get(i) == 2 for i in (0, 1))
        tunnels.connected.add(apps[1])
        now = time.time()
        session.expires = now + 1e6
        session.last_active = now
        await store._reap_once()
        assert 1 not in session.shard_down_ticks, "the reconnected shard's down-ticks reset"
        assert session.failed_shards == {} and store._executor.stopped == []

    asyncio.run(main())


def test_beyond_grace_marks_failed_and_reaps(env) -> None:
    async def main() -> None:
        store, tunnels = env
        session = await _ready_session(store)
        apps = [s.app_name for s in session.shards]
        for _ in range(2):
            await store._mark_down_shards(session)  # 2 ticks each
        tunnels.connected.add(apps[1])
        now = time.time()
        session.expires = now + 1e6
        session.last_active = now
        await store._reap_once()  # shard 1 resets; shard 0 reaches 3
        tunnels.connected.discard(apps[1])
        for _ in range(4):
            await store._mark_down_shards(session)
        assert set(session.failed_shards) == {0, 1}, "both shards failed past the grace"
        await asyncio.sleep(0)
        assert sorted(store._executor.stopped) == sorted(apps), "both workers reaped"
        assert session.status == "failed", "all shards dead: the session flips failed"

    asyncio.run(main())


def test_direct_mark_shard_failed_reaps_synchronously(env) -> None:
    async def main() -> None:
        store, tunnels = env
        session3 = await _ready_session(store, n=1)
        app3 = session3.shards[0].app_name
        js._mark_shard_failed(store, session3, 0, "POST /submit: HTTP 502: no live tunnel")
        await asyncio.sleep(0)
        assert store._executor.stopped == [app3]

    asyncio.run(main())


def test_outside_the_ledger_immediate_teardown(env) -> None:
    async def main() -> None:
        store, tunnels = env
        assert store.claim_shard_tunnel_close("jsess-ghost-s0") is False, "unknown app: not claimed"
        session4 = await _ready_session(store, n=1)
        session4.status = "hibernated"
        assert store.claim_shard_tunnel_close(session4.shards[0].app_name) is False, \
            "hibernated sessions are not claimed (their workers are already recycled)"
        session5 = await _ready_session(store, n=1)
        session5.status = "failed"
        assert store.claim_shard_tunnel_close(session5.shards[0].app_name) is False

    asyncio.run(main())


def test_server_layer_callback_end_to_end(env) -> None:
    async def main() -> None:
        store, tunnels = env
        store._executor.stopped.clear()
        app = {"judge_sessions": store, "executor": store._executor}
        session6 = await _ready_session(store, n=1)
        app6 = session6.shards[0].app_name
        await _reap_closed_tunnel(app, app6)
        assert store._executor.stopped == [], "claimed session: the callback deletes nothing"
        await _reap_closed_tunnel(app, "jsess-ghost-s9")
        assert store._executor.stopped == ["jsess-ghost-s9"], "outside the ledger: immediate delete"
        app_no_store = {"judge_sessions": None, "executor": store._executor}
        await _reap_closed_tunnel(app_no_store, "jsess-ghost-s10")
        assert store._executor.stopped[-1] == "jsess-ghost-s10", "no store: the fallback deletes"

    asyncio.run(main())
