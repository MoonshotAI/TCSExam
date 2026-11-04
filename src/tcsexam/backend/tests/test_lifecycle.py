"""Lifecycle tests: per-family lifecycle routes, in-flight reaper skip,
probe-path exclusion from request counting, status-route wiring.
"""
from __future__ import annotations

import asyncio
import time

import pytest

from tcsexam.backend.config import (
    JudgeSessionsConfig,
    judge_sessions_from_dict,
)
from tcsexam.backend.sessions_base import JudgeSession, JudgeSessionStore
from tcsexam.backend.status import (
    RequestCounter,
    StatusCollector,
    classify_path,
    register_status_routes,
)


# --------------------------------------------------------------------------- #
# Lifecycle routes (resolve_lifecycle + yaml parsing)
# --------------------------------------------------------------------------- #
def test_resolve_lifecycle_hit_and_fallback() -> None:
    cfg = judge_sessions_from_dict(
        {
            "idle_ttl_seconds": 3600.0,
            "ttl_seconds": 21600.0,
            "routes": [
                {"match": {"image_contains": "esbmc-svcomp-verify-wall120"}, "idle_ttl_seconds": 14400.0, "ttl_seconds": 43200.0},
                {"match": {"image_contains": "isabelle"}, "idle_ttl_seconds": 14400.0, "ttl_seconds": 43200.0},
                {"match": {"image_contains": "esbmc"}, "idle_ttl_seconds": 7200.0},
            ],
        }
    )
    # First hit wins: the more specific esbmc slow tier precedes the mid tier.
    assert cfg.resolve_lifecycle("ns/bench:esbmc-svcomp-verify-wall120-judge-svc-0.1.0") == (14400.0, 43200.0)
    assert cfg.resolve_lifecycle("ns/bench:isabelle-hol-prove-judge-svc-0.1.0") == (14400.0, 43200.0)
    # Mid tier hit: ttl falls back to the section default.
    assert cfg.resolve_lifecycle("ns/bench:esbmc-base-judge-svc-0.1.0") == (7200.0, 21600.0)
    # No route: all defaults.
    assert cfg.resolve_lifecycle("ns/bench:zydis-judge-1.0") == (3600.0, 21600.0)


def test_routes_parse_lifecycle_fields() -> None:
    cfg = judge_sessions_from_dict(
        {
            "routes": [
                {"match": {"image_contains": "smtrat"}, "idle_ttl_seconds": 14400, "ttl_seconds": 43200},
            ]
        }
    )
    assert cfg.resolve_lifecycle("x/smtrat-judge-svc-0.1.0") == (14400.0, 43200.0)
    with pytest.raises(ValueError):
        judge_sessions_from_dict({"routes": [{"match": {"image_contains": "x"}, "idle_ttl_seconds": -5}]})


# --------------------------------------------------------------------------- #
# Reaper: in-flight skip + per-session idle ttl
# --------------------------------------------------------------------------- #
class _FakeTunnels:
    def __init__(self, in_flight: int = 0, connected: bool = True) -> None:
        self._in_flight = in_flight
        self._connected = connected
        self.session_tokens: dict[str, str] = {}

    def is_connected(self, app_name: str) -> bool:
        return self._connected

    def in_flight(self, app_name: str) -> int:
        return self._in_flight

    async def close(self, app_name: str) -> None:
        self._connected = False
        self.session_tokens.pop(app_name, None)


class _FakeExecutor:
    def __init__(self) -> None:
        self.stopped: list[str] = []

    async def stop_app(self, app_name: str) -> None:
        self.stopped.append(app_name)


def _make_store(tunnels) -> JudgeSessionStore:
    class _Cfg:
        public_base_url = "http://svc.test"

        def public_url(self) -> str:
            return self.public_base_url

    store = JudgeSessionStore.__new__(JudgeSessionStore)
    store._service_config = _Cfg()
    store.cfg = JudgeSessionsConfig(idle_ttl_seconds=3600.0, reaper_interval_seconds=60.0)
    store._executor = _FakeExecutor()
    store._tunnels = tunnels
    from collections import deque

    store._sessions = {}
    store._destroyed = deque()
    store._inflight = {}
    store._provision_tasks = {}
    store._reaper_task = None
    store._journal = None
    return store


def _session(sid: str, *, last_active: float, idle_ttl: float = 0.0) -> JudgeSession:
    return JudgeSession(
        session_id=sid,
        app_name=sid,
        image="img",
        created=last_active - 100,
        last_active=last_active,
        expires=last_active + 999999,
        idle_ttl_seconds=idle_ttl,
    )


def test_reaper_skips_in_flight_session() -> None:
    tunnels = _FakeTunnels(in_flight=1)
    store = _make_store(tunnels)
    old = _session("jsess-old", last_active=time.time() - 7200)  # 2h idle > 1h default
    store._sessions[old.session_id] = old
    asyncio.run(store._reap_once())
    assert old.destroyed is False, "in-flight judging was reaped as idle"
    assert store._executor.stopped == []


def test_reaper_uses_per_session_idle_ttl() -> None:
    tunnels = _FakeTunnels(in_flight=0)
    store = _make_store(tunnels)
    # 2h idle: the default 1h reaps, but the session-level slow tier (4h) holds.
    slow = _session("jsess-slow", last_active=time.time() - 7200, idle_ttl=14400.0)
    fast = _session("jsess-fast", last_active=time.time() - 7200, idle_ttl=3600.0)
    store._sessions[slow.session_id] = slow
    store._sessions[fast.session_id] = fast
    asyncio.run(store._reap_once())
    assert slow.destroyed is False, "slow-tier session reaped before its 4h idle ttl"
    assert fast.destroyed is True, "fast-tier session should be reaped at 1h idle ttl"


# --------------------------------------------------------------------------- #
# Probe-path exclusion from request counting
# --------------------------------------------------------------------------- #
def test_probe_paths_not_counted() -> None:
    assert classify_path("/v1/health") is None
    assert classify_path("/v1/status") is None
    counter = RequestCounter()
    counter.record("/v1/health")
    counter.record("/v1/status")
    counter.record("/v1/judge/sessions")
    snap = counter.snapshot()
    assert snap["last_60s"]["total"] == 1
    assert snap["last_60s"]["by_path"] == {"/v1/judge/sessions": 1}


# --------------------------------------------------------------------------- #
# Status-route wiring
# --------------------------------------------------------------------------- #
def test_register_status_routes_registers_endpoint() -> None:
    from aiohttp import web

    app = web.Application()
    collector = StatusCollector(config=None)
    register_status_routes(app, collector)
    routes = {r.resource.canonical for r in app.router.routes()}
    assert "/v1/status" in routes
    assert app["status_collector"] is collector
