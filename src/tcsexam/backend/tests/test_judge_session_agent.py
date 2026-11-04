"""In-worker agent tunnel-dial retry tests and health-probe
tri-state tests.

``_connect_with_retry`` wraps the agent's WebSocket dial in exponential
backoff so a transient service-side refusal (restart, proxy convergence)
no longer kills a freshly-booted judge session. ``_engine_health`` implements
the three-state judge health contract (ok / starting / error): only the
terminal ``{"status": "error"}`` state is fatal, everything else keeps the
boot wait going. Pure unit tests plus a localhost HTTP server — no sockets
beyond localhost, no network.
"""
from __future__ import annotations

import http.server
import json
import threading

import pytest

from tcsexam.backend.agent_files import judge_session_agent as agent


class _FakeWS:
    def __init__(self, failures: int) -> None:
        self.failures_left = failures
        self.calls = 0

    def connect(self) -> None:
        self.calls += 1
        if self.failures_left > 0:
            self.failures_left -= 1
            raise ConnectionError("refused")


@pytest.fixture
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    delays: list[float] = []
    monkeypatch.setattr(agent.time, "sleep", delays.append)
    return delays


def test_retry_succeeds_after_transient_failures(no_sleep: list[float]) -> None:
    ws = _FakeWS(failures=3)
    agent._connect_with_retry(ws)
    assert ws.calls == 4
    assert no_sleep == [2.0, 4.0, 8.0]  # exponential backoff between attempts


def test_retry_exhaustion_raises_the_last_error(no_sleep: list[float]) -> None:
    ws = _FakeWS(failures=99)
    with pytest.raises(ConnectionError, match="refused"):
        agent._connect_with_retry(ws, attempts=5)
    assert ws.calls == 5
    assert len(no_sleep) == 4  # no sleep after the final failed attempt


def test_retry_delay_is_capped(no_sleep: list[float]) -> None:
    ws = _FakeWS(failures=6)
    agent._connect_with_retry(ws, attempts=7, base_delay=2.0, max_delay=10.0)
    assert no_sleep == [2.0, 4.0, 8.0, 10.0, 10.0, 10.0]


def test_retry_first_attempt_success_sleeps_never(no_sleep: list[float]) -> None:
    ws = _FakeWS(failures=0)
    agent._connect_with_retry(ws)
    assert ws.calls == 1
    assert no_sleep == []


# --------------------------------------------------------------------------- #
# _engine_health tri-state (boot fail-fast)
# --------------------------------------------------------------------------- #
_RESPONSES = {
    "/ok": (200, {"status": "ok"}),
    "/starting": (503, {"status": "starting"}),
    "/error": (503, {"status": "error", "error": "judge assets missing: /judge/bench/run_bench.py"}),
    "/garbage": (503, b"<html>not json</html>"),
}


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        status, payload = _RESPONSES.get(self.path, (404, {"status": "starting"}))
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture
def health_server():
    server = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server.server_address[1]
    server.shutdown()
    thread.join(timeout=5)


def test_engine_health_ok_is_healthy(health_server: int) -> None:
    assert agent._engine_health(health_server, "/ok") == (True, None)


def test_engine_health_starting_keeps_waiting(health_server: int) -> None:
    assert agent._engine_health(health_server, "/starting") == (False, None)


def test_engine_health_error_state_is_fatal(health_server: int) -> None:
    healthy, fatal = agent._engine_health(health_server, "/error")
    assert healthy is False
    assert fatal == "judge assets missing: /judge/bench/run_bench.py"


def test_engine_health_non_json_error_page_keeps_waiting(health_server: int) -> None:
    assert agent._engine_health(health_server, "/garbage") == (False, None)


def test_engine_health_connection_refused_keeps_waiting() -> None:
    # Port 1 is never listening: the server has not come up yet, keep waiting.
    assert agent._engine_health(1, "/health") == (False, None)


def test_engine_health_bypasses_dead_proxy_env(
    health_server: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Judge images may bake http_proxy/https_proxy into their ENV
    # (build leftovers); the worker DNS cannot resolve the proxy host and a
    # plain urlopen to 127.0.0.1 dies on proxy-name resolution. The probe
    # must bypass it.
    monkeypatch.setenv("http_proxy", "http://proxy.invalid:3128")
    monkeypatch.setenv("https_proxy", "http://proxy.invalid:3128")
    monkeypatch.delenv("no_proxy", raising=False)
    assert agent._engine_health(health_server, "/ok") == (True, None)


# --------------------------------------------------------------------------- #
# _tunnel_serve_loop reconnect-after-drop
# --------------------------------------------------------------------------- #
class _FakeProc:
    def __init__(self, alive_polls: int) -> None:
        self.alive_polls = alive_polls

    def poll(self):
        self.alive_polls -= 1
        return None if self.alive_polls > 0 else 1


class _FakeTunnelClient:
    instances: list["_FakeTunnelClient"] = []

    def __init__(self, ws, target_port, read_timeout) -> None:
        self.ready_sent = 0
        _FakeTunnelClient.instances.append(self)

    def send_frame(self, *args) -> None:
        self.ready_sent += 1

    def run_forever(self) -> None:
        return  # the tunnel "drops" immediately every time


@pytest.fixture
def fake_tunnel(monkeypatch: pytest.MonkeyPatch):
    _FakeTunnelClient.instances = []
    monkeypatch.setattr(agent, "WSClient", lambda url, headers: _FakeWS(failures=0))
    monkeypatch.setattr(agent, "TunnelClient", _FakeTunnelClient)
    monkeypatch.setattr(agent.time, "sleep", lambda s: None)
    return _FakeTunnelClient


_CONFIG = {"service_ws_url": "wss://svc.example/v1/tunnel/x"}


def test_serve_loop_redials_and_resends_ready_after_drop(fake_tunnel) -> None:
    # Judge alive for exactly two tunnel rounds, then dead on the poll after
    # the second drop.
    rc = agent._tunnel_serve_loop(_CONFIG, _FakeProc(alive_polls=2), 8082, 60.0, "app", "lbl", {})
    assert rc == 1, "the loop exits 1 once the judge server is gone"
    assert len(_FakeTunnelClient.instances) == 2, "the dropped tunnel is redialed"
    assert all(c.ready_sent == 1 for c in _FakeTunnelClient.instances), (
        "READY is re-sent on every (re)connect"
    )


def test_serve_loop_survives_a_dial_failure_round(monkeypatch, fake_tunnel) -> None:
    calls = {"n": 0}

    class _FlakyWS:
        def connect(self) -> None:
            calls["n"] += 1
            if calls["n"] == 1:
                raise ConnectionError("service restarting")

    monkeypatch.setattr(agent, "WSClient", lambda url, headers: _FlakyWS())
    rc = agent._tunnel_serve_loop(_CONFIG, _FakeProc(alive_polls=4), 8082, 60.0, "app", "lbl", {})
    assert rc == 1
    assert calls["n"] >= 2, "a failed dial round is retried with backoff"
    assert len(_FakeTunnelClient.instances) >= 1
