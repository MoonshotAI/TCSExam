"""Release-review regressions, using fake workers and controlled async gates."""
from __future__ import annotations

import asyncio
import copy
import json
from types import SimpleNamespace

import pytest
import yaml
from aiohttp import web
from aiohttp.test_utils import make_mocked_request

from tcsexam.backend.auth import make_auth_middleware
from tcsexam.backend.config import BackendConfig, Config, JudgeSessionRoute, JudgeSessionsConfig, load_config
from tcsexam.backend.server import _reap_closed_tunnel, create_app
from tcsexam.backend.sessions import JudgeSessionStore as GroupStore, _write_archive, aggregate_submissions, five_numbers
from tcsexam.backend.tunnel import Tunnel, TunnelManager
from tcsexam.backend.tunnel_protocol import T_RESPONSE_ABORT
from test_session_hibernate import _make_store
from test_singleflight import FakeExecutor, FakeTunnels, _store


@pytest.mark.parametrize("auth", [
    {"token_id": "private-value"},
    {"token_secret": "private-value"},
    {"token_id": "", "token_secret": "private-value"},
    {"token_id": "id", "token_secret": ""},
    {"token_id": "", "token_secret": ""},
    {"token_id": " ", "token_secret": "private-value"},
    {"token_id": 42, "token_secret": "private-value"},
    {"token_id": [], "token_secret": "private-value"},
    {"additional_tokens": [["id", "private-value"]]},
    {"token_id": "id", "token_secret": "private-value", "additional_tokens": None},
    *[{"token_id": "id", "token_secret": "private-value", "additional_tokens": item}
      for item in ["private-value", {}, [["id"]], [["id", "s", "extra"]],
                   [None], [{"id": "private-value"}], [["id", ""]], [[1, "s"]]]],
])
def test_bad_credentials_rejected_by_both_entrypoints(auth, tmp_path, monkeypatch):
    monkeypatch.delenv("TCSEXAM_TOKEN_ID", raising=False)
    monkeypatch.delenv("TCSEXAM_TOKEN_SECRET", raising=False)
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump({"auth": auth}))
    for entrypoint in (lambda: load_config(path), lambda: create_app(Config(**auth), adapter=object())):
        with pytest.raises(ValueError, match="auth\\.") as caught:
            entrypoint()
        assert "private-value" not in str(caught.value)


@pytest.mark.parametrize("auth", [[], "private-value", 42])
def test_invalid_auth_section_reports_configuration_error(auth, tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump({"auth": auth}))
    with pytest.raises(ValueError, match="auth must be a mapping"):
        load_config(path)


def test_unicode_auth_is_total_and_rotation_preserves_pairs():
    async def main():
        config = Config(token_id="主凭据", token_secret="密钥", additional_tokens=[("备用", "旧密钥")])
        config.validate_auth()
        app = web.Application()
        app["config"] = config
        middleware = make_auth_middleware()
        async def handler(request):
            return web.Response(status=204)
        for token_id, secret, status in [
            ("主凭据", "密钥", 204), ("备用", "旧密钥", 204),
            ("主凭据", "旧密钥", 401), ("未知", "密钥", 401),
            ("", "", 401),
        ]:
            request = make_mocked_request("GET", "/v1/protected", app=app, headers={
                "X-TCSEXAM-Token-Id": token_id, "X-TCSEXAM-Token-Secret": secret,
                "X-TCSEXAM-Run-Id": "test",
            })
            assert (await middleware(request, handler)).status == status
    asyncio.run(asyncio.wait_for(main(), 5.0))


@pytest.mark.parametrize("ready,expected_boot", [(900.0, 900.0), (9000.0, 7200.0)])
def test_single_and_sharded_agents_receive_same_routed_timeouts(ready, expected_boot, tmp_path):
    async def main():
        cfg = JudgeSessionsConfig(read_timeout_seconds=12345, routes=[JudgeSessionRoute(
            image_contains="slow", ready_timeout_seconds=ready, create_ready_timeout_seconds=6789,
        )])
        base, base_executor = _store(cfg)
        executor = FakeExecutor()
        group = GroupStore(executor, Config(state_dir=tmp_path, backend=BackendConfig(judge_sessions=cfg)))
        group.attach_tunnels(FakeTunnels())
        identity = {"run_id": "same-run", "attrs": {"TCSEXAM_AGENT_NAME": "same-agent"}}
        single = base.begin_create(None, "slow-image", None, None, 600, **identity)
        shards = group.begin_create_group(None, "slow-image", None, None, 600, 2, **identity)
        try:
            await asyncio.gather(base._wait_provision(single), group._provision_tasks[shards.session_id])
            for store, worker_executor in [(base, base_executor), (group, executor)]:
                assert all(c["ready_timeout_seconds"] == 6789 for c in worker_executor.calls)
                for worker in worker_executor.registered.values():
                    agent = json.loads(worker.ctrl.files[f"{cfg.work_dir}/agent_config.json"])
                    assert agent["boot_timeout_seconds"] == expected_boot
                    assert agent["read_timeout_seconds"] == 12345
                    assert agent["run_id"] == "same-run"
                    assert agent["agent_name"] == "same-agent"
                # Both paths check agent boot failures between bounded waits.
                assert store._tunnels.wait_calls
                assert all(0 < timeout <= ready for _, timeout in store._tunnels.wait_calls)
        finally:
            await base.shutdown()
            await group.shutdown()
    asyncio.run(asyncio.wait_for(main(), 5.0))


@pytest.mark.parametrize("grouped", [False, True])
def test_singleflight_matches_payload_resources_ttl_and_run(grouped, tmp_path):
    async def main():
        if grouped:
            executor = FakeExecutor()
            store = GroupStore(executor, Config(state_dir=tmp_path))
            # Hold provisioning until every call has exercised the key.
            gate = asyncio.Event()
            original = store._provision_group
            async def provision(*args):
                await gate.wait()
                return await original(*args)
            store._provision_group = provision
            store.attach_tunnels(FakeTunnels())
        else:
            store, executor = _store()
        def begin(*, files=None, resources=None, ttl=None, run="run", **extra):
            args = (("id", "image", "client"), "image", files, resources, ttl)
            if grouped:
                return store.begin_create_group(*args, extra.get("n_shards", 1),
                                                instance_set=extra.get("instance_set", "hidden"),
                                                run_id=run, token_id="id")
            return store.begin_create(*args, run_id=run, token_id="id")
        try:
            first = begin(files={"/a": b"first", "/b": b"second"})
            assert begin(files={"/b": b"second", "/a": b"first"},
                         resources=dict(store.cfg.spec), ttl=store.cfg.ttl_seconds) is first
            variations = [
                begin(files={"/a": b"changed", "/b": b"second"}),
                begin(files={"/different-path": b"first", "/b": b"second"}),
                begin(files={"/a": b"first", "/b": b"second"}, resources={"cpu_count": 2}),
                begin(files={"/a": b"first", "/b": b"second"}, ttl=3600),
                begin(files={"/a": b"first", "/b": b"second"}, run="other-run"),
            ]
            assert len({s.session_id for s in [first, *variations]}) == 6
            if grouped:
                assert begin(files={"/a": b"first", "/b": b"second"}, n_shards=2) is not first
                assert begin(files={"/a": b"first", "/b": b"second"}, instance_set="public") is not first
        finally:
            await store.shutdown()
        assert not executor.registered
    asyncio.run(asyncio.wait_for(main(), 5.0))


def test_equal_anchors_skip_feedback_but_archive_keeps_all_records(tmp_path):
    records = [
        {"instance": f"equal-{status}", "A": a, "B": 1, "K": 1, "status": status}
        for status, a in [("ok", 0), ("ok", 1), ("ok", 2), ("invalid", None), ("error", None)]
    ]
    original = copy.deepcopy(records)
    assert five_numbers(records) == {"better": 0, "equal": 0, "worse": 0, "failed": 1, "delta": 0}
    payload = {"submissions": [{"submission": 0, "status": "ok", "records": records}]}
    feedback = aggregate_submissions([payload])["submissions"][0]
    assert (feedback["better"], feedback["equal"], feedback["worse"], feedback["failed"]) == (0, 0, 0, 1)
    assert len(feedback["records"]) == len(records)
    session = SimpleNamespace(session_id="test", image="image", instance_set="hidden", n_shards=1,
                              created=0, failed_shards={}, shard_payloads={0: payload})
    _write_archive(SimpleNamespace(_config=SimpleNamespace(state_dir=tmp_path)), session)
    archived = json.loads((tmp_path / "judge_archive/test.json").read_text())
    assert archived["shard_payloads"]["0"]["submissions"][0]["records"] == original
    assert records == original


@pytest.mark.parametrize("image,requested,expected,idle", [
    ("slow-image", None, 1600, 500),
    ("slow-image", 900, 900, 500),
    ("slow-image", 5000, 1800, 500),
    ("slow-image", 1, 60, 500),
    ("ordinary-image", None, 1200, 100),
    ("ordinary-image", 900, 900, 100),
    ("idle-only-image", None, 1200, 20),
])
def test_group_lifecycle_routes_request_precedence_and_wake(image, requested, expected, idle, tmp_path, monkeypatch):
    async def main():
        clock = [1000.0]
        monkeypatch.setattr("tcsexam.backend.sessions.time.time", lambda: clock[0])
        cfg = JudgeSessionsConfig(ttl_seconds=1200, max_ttl_seconds=1800, idle_ttl_seconds=100,
                                  routes=[JudgeSessionRoute("slow", ttl_seconds=1600, idle_ttl_seconds=500),
                                          JudgeSessionRoute("idle-only", idle_ttl_seconds=20)])
        store = _make_store(Config(state_dir=tmp_path, backend=BackendConfig(judge_sessions=cfg)))
        session, task = store._register_group(image, None, None, requested, 2)
        try:
            assert session.expires - session.created == expected
            assert session.ttl == expected
            assert session.idle_ttl_seconds == idle
            clock[0] = 1200.0  # Worker startup consumes wall-clock time.
            await task
            assert session.ready_at == 1200.0
            assert session.expires == 1200.0 + expected
            async def settled(*args, **kwargs):
                return {i: (200, {}, b'{"submissions": []}') for i in range(2)}
            monkeypatch.setattr("tcsexam.backend.sessions._call_shards", settled)
            for asleep, awake in [(2000.0, 3000.0), (5000.0, 7000.0)]:
                clock[0] = asleep
                await store._hibernate_if_settled(session)
                assert session.status == "hibernated"
                assert session.expires == asleep + expected
                clock[0] = awake
                await store._wake_session(session)
                assert session.ttl == expected
                assert session.ready_at == awake
                assert session.expires == awake + expected
                assert session.idle_ttl_seconds == idle
        finally:
            await store.shutdown()
    asyncio.run(asyncio.wait_for(main(), 5.0))


@pytest.mark.parametrize("image,should_reap", [("slow-image", False), ("ordinary-image", False),
                                              ("idle-only-image", True)])
def test_group_idle_reaper_uses_routed_threshold(image, should_reap, tmp_path, monkeypatch):
    async def main():
        cfg = JudgeSessionsConfig(ttl_seconds=1200, idle_ttl_seconds=100, hibernate_enabled=False,
                                  routes=[JudgeSessionRoute("slow", idle_ttl_seconds=500),
                                          JudgeSessionRoute("idle-only", idle_ttl_seconds=20)])
        store = _make_store(Config(state_dir=tmp_path, backend=BackendConfig(judge_sessions=cfg)))
        session, task = store._register_group(image, None, None, None, 1)
        try:
            await task
            monkeypatch.setattr("tcsexam.backend.sessions.time.time", lambda: 1000.0)
            session.expires = 2000.0
            session.last_active = 950.0
            await store._reap_once()
            assert session.destroyed is should_reap
            if not should_reap:
                session.last_active = 1000 - session.idle_ttl_seconds - 1
                await store._reap_once()
                assert session.destroyed
        finally:
            await store.shutdown()
    asyncio.run(asyncio.wait_for(main(), 5.0))


def test_group_singleflight_uses_route_default_lifetime(tmp_path):
    async def main():
        cfg = JudgeSessionsConfig(ttl_seconds=1200, routes=[JudgeSessionRoute("slow", ttl_seconds=1600)])
        store = _make_store(Config(state_dir=tmp_path, backend=BackendConfig(judge_sessions=cfg)))
        key = ("id", "slow-image", "client")
        try:
            implicit = store.begin_create_group(key, "slow-image", None, None, None, 1)
            explicit = store.begin_create_group(key, "slow-image", None, None, 1600, 1)
            different = store.begin_create_group(key, "slow-image", None, None, 1200, 1)
            assert explicit is implicit
            assert different is not implicit
        finally:
            await store.shutdown()
    asyncio.run(asyncio.wait_for(main(), 5.0))


class ControlledSocket:
    """Explicit gates force replacement/closure interleavings without sleeps."""
    def __init__(self, *, block_close=False, block_prepare=False):
        self.prepared = asyncio.Event()
        self.prepare_allowed = asyncio.Event()
        self.close_started = asyncio.Event()
        self.close_allowed = asyncio.Event()
        self.closed = asyncio.Event()
        self.close_code = 1000
        if not block_prepare:
            self.prepare_allowed.set()
        if not block_close:
            self.close_allowed.set()

    async def prepare(self, request):
        self.prepared.set()
        await self.prepare_allowed.wait()

    def __aiter__(self):
        return self

    async def __anext__(self):
        await self.closed.wait()
        raise StopAsyncIteration

    async def close(self):
        self.close_started.set()
        await self.close_allowed.wait()
        self.closed.set()

    def exception(self):
        return None


def test_close_aborts_pending_clears_registration_and_is_idempotent():
    async def main():
        callbacks = []
        manager = TunnelManager(on_tunnel_closed=callbacks.append)
        tunnel = Tunnel("app", ControlledSocket())
        manager._tunnels["app"] = tunnel
        event = asyncio.Event()
        event.set()
        manager._connect_events["app"] = event
        manager.session_tokens.update({"app": "secret", "unknown": "stale"})
        queue = asyncio.Queue()
        tunnel.pending[b"request"] = queue

        await manager.close("app")

        assert queue.get_nowait() == (T_RESPONSE_ABORT, b"session destroyed")
        assert tunnel.pending == {}
        assert tunnel.closed
        assert tunnel.ws.closed.is_set()
        assert not manager.is_connected("app")
        assert manager.connected_count() == 0
        assert "app" not in manager._tunnels
        assert not event.is_set()
        assert manager.session_tokens == {"unknown": "stale"}
        assert callbacks == ["app"]

        await manager.close("app")
        await manager.close("unknown")
        assert callbacks == ["app"]
        assert manager.session_tokens == {}

    asyncio.run(asyncio.wait_for(main(), 5.0))


def test_natural_reconnect_allowed_but_closed_app_rejected(monkeypatch):
    sockets = [ControlledSocket(), ControlledSocket(), ControlledSocket()]

    async def main():
        manager = TunnelManager()
        pending = iter(sockets)
        monkeypatch.setattr(web, "WebSocketResponse", lambda **kwargs: next(pending))
        request = SimpleNamespace(match_info={"app_name": "app"}, remote="test")

        first = asyncio.create_task(manager.handle_ws(request))
        await sockets[0].prepared.wait()
        await sockets[0].close()
        await first
        assert "app" not in manager._closed_apps
        assert manager.connected_count() == 0

        second = asyncio.create_task(manager.handle_ws(request))
        await sockets[1].prepared.wait()
        assert manager.is_connected("app")
        assert manager.connected_count() == 1
        tunnel = manager._tunnels["app"]
        tunnel.pending[b"request"] = asyncio.Queue()
        manager.session_tokens["app"] = "secret"
        await manager.close("app")
        await second
        await manager.close("app")

        response = await manager.handle_ws(request)
        assert response.status == 404
        assert not sockets[2].prepared.is_set()
        assert not manager.is_connected("app")
        assert manager.connected_count() == 0
        assert manager.in_flight("app") == 0
        assert manager.ready_info("app") is None
        assert tunnel.pending == {}
        assert "app" not in manager.session_tokens

    run_socket_scenario(main(), sockets)


def test_close_during_prepare_never_registers(monkeypatch):
    sockets = [ControlledSocket(block_prepare=True)]

    async def main():
        manager = TunnelManager()
        monkeypatch.setattr(web, "WebSocketResponse", lambda **kwargs: sockets[0])
        request = SimpleNamespace(match_info={"app_name": "app"}, remote="test")
        handler = asyncio.create_task(manager.handle_ws(request))
        await sockets[0].prepared.wait()

        await manager.close("app")
        sockets[0].prepare_allowed.set()
        result = await handler

        assert result is sockets[0]
        assert sockets[0].closed.is_set()
        assert "app" not in manager._tunnels
        assert manager.connected_count() == 0
        assert manager.in_flight("app") == 0
        assert manager.ready_info("app") is None

    run_socket_scenario(main(), sockets)


def run_socket_scenario(scenario, sockets):
    async def run():
        task = asyncio.create_task(scenario)
        try:
            # Shield lets the timeout reach cleanup even if a regressed
            # handler's cancellation gets stuck closing a gated predecessor.
            await asyncio.wait_for(asyncio.shield(task), 5.0)
        finally:
            for socket in sockets:
                socket.close_allowed.set()
                socket.closed.set()
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    asyncio.run(run())


def test_three_concurrent_tunnels_keep_newest_and_close_every_predecessor(monkeypatch):
    sockets = [ControlledSocket(block_close=True), ControlledSocket(), ControlledSocket()]
    async def main():
        callbacks = []
        manager = TunnelManager(on_tunnel_closed=callbacks.append)
        pending = iter(sockets)
        monkeypatch.setattr(web, "WebSocketResponse", lambda **kwargs: next(pending))
        request = SimpleNamespace(match_info={"app_name": "app"}, remote="test")
        first = asyncio.create_task(manager.handle_ws(request))
        await sockets[0].prepared.wait()
        second = asyncio.create_task(manager.handle_ws(request))
        await sockets[0].close_started.wait()
        third = asyncio.create_task(manager.handle_ws(request))
        await sockets[1].closed.wait()
        assert manager._tunnels["app"].ws is sockets[2]
        sockets[0].close_allowed.set()
        await asyncio.gather(first, second)
        assert callbacks == []
        assert manager.is_connected("app")
        assert manager._connect_events["app"].is_set()
        assert await manager.wait_connected("app", 0.1)
        await sockets[2].close()
        await third
        assert callbacks == ["app"]
        assert not manager.is_connected("app")
        assert not manager._connect_events["app"].is_set()
        assert all(ws.closed.is_set() for ws in sockets)
    run_socket_scenario(main(), sockets)


def test_cancel_replacement_during_old_close_closes_both_sockets(monkeypatch):
    sockets = [ControlledSocket(block_close=True), ControlledSocket()]
    async def main():
        manager = TunnelManager()
        pending = iter(sockets)
        monkeypatch.setattr(web, "WebSocketResponse", lambda **kwargs: next(pending))
        request = SimpleNamespace(match_info={"app_name": "app"}, remote="test")
        first = asyncio.create_task(manager.handle_ws(request))
        await sockets[0].prepared.wait()
        second = asyncio.create_task(manager.handle_ws(request))
        await sockets[0].close_started.wait()
        second.cancel()
        with pytest.raises(asyncio.CancelledError):
            await second
        assert sockets[1].closed.is_set()
        assert not manager.is_connected("app")
        sockets[0].close_allowed.set()
        await first
        assert sockets[0].closed.is_set()
        assert not manager._connect_events["app"].is_set()
    run_socket_scenario(main(), sockets)


def test_current_close_yielding_to_reconnect_never_calls_reaper(monkeypatch):
    sockets = [ControlledSocket(block_close=True), ControlledSocket()]
    async def main():
        callbacks = []
        manager = TunnelManager(on_tunnel_closed=callbacks.append)
        pending = iter(sockets)
        monkeypatch.setattr(web, "WebSocketResponse", lambda **kwargs: next(pending))
        request = SimpleNamespace(match_info={"app_name": "app"}, remote="test")
        first = asyncio.create_task(manager.handle_ws(request))
        await sockets[0].prepared.wait()
        # The reader has ended, but its close() still yields.
        sockets[0].closed.set()
        await sockets[0].close_started.wait()
        second = asyncio.create_task(manager.handle_ws(request))
        await sockets[1].prepared.wait()
        sockets[0].close_allowed.set()
        await first
        assert callbacks == []
        assert manager._connect_events["app"].is_set()
        await sockets[1].close()
        await second
        assert callbacks == ["app"]
    run_socket_scenario(main(), sockets)


def test_scheduled_close_hook_rechecks_new_connection():
    async def main():
        executor = FakeExecutor()
        async def must_not_stop(name):
            raise AssertionError("reconnected worker must not be reaped")
        executor.stop_app = must_not_stop
        await _reap_closed_tunnel({"executor": executor, "tunnels": FakeTunnels()}, "app")
    asyncio.run(asyncio.wait_for(main(), 5.0))
