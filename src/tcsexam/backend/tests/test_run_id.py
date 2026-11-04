"""Run-id caller-identity tests: the auth middleware's
X-TCSEXAM-Run-Id handling (warn / required / off + throttled warning logs),
session and worker tagging (run_id fields, labels, group_name slug), and
the /v1/status callers aggregation including the "" bucket.

All stub/fake based: no real workers, no network beyond localhost.
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
import types
import urllib.error
import urllib.request

import pytest

import aiohttp.web  # noqa: E402

from conftest import ARCHIVE_TOKEN, TOKEN_ID, TOKEN_SECRET, wait_session_ready

from tcsexam.backend.adapter import BasePlatformAdapter
from tcsexam.backend.auth import (
    RUN_ID_HEADER,
    is_valid_run_id,
    make_auth_middleware,
)
from tcsexam.backend.config import BaseServiceConfig, JudgeSessionsConfig
from tcsexam.backend.errors import INVALID_RUN_ID_MESSAGE
from tcsexam.backend.sessions_base import JudgeSessionStore, run_id_slug
from tcsexam.backend.status import RequestCounter, StatusCollector

RUN_ID = "fbgemm-v1-k3-20260827-01"


# --------------------------------------------------------------------------- #
# Pure-function units
# --------------------------------------------------------------------------- #
def test_is_valid_run_id_boundaries() -> None:
    assert is_valid_run_id(RUN_ID)
    assert is_valid_run_id("a" * 128)  # the length cap, inclusive
    assert is_valid_run_id("with space")  # 0x20 is printable ASCII
    assert is_valid_run_id("~")  # 0x7E, the top of printable ASCII
    assert not is_valid_run_id("")
    assert not is_valid_run_id("a" * 129)
    assert not is_valid_run_id("has\ttab")
    assert not is_valid_run_id("has\x7fdel")
    assert not is_valid_run_id("非ascii")


def test_run_id_slug_rules() -> None:
    assert run_id_slug(RUN_ID) == RUN_ID
    assert run_id_slug("a/b c:d.e") == "a-b-c-d-e"  # unsafe chars collapse to -
    assert run_id_slug("x" * 50) == "x" * 40  # truncated to 40 chars
    assert run_id_slug("ok-1_2") == "ok-1_2"  # - and _ are kept


# --------------------------------------------------------------------------- #
# Middleware over real HTTP (minimal app, same pattern as test_auth.py)
# --------------------------------------------------------------------------- #
def _serve(app: aiohttp.web.Application):
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()

    async def _start():
        runner = aiohttp.web.AppRunner(app)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        return runner, site._server.sockets[0].getsockname()[1]

    runner, port = asyncio.run_coroutine_threadsafe(_start(), loop).result(timeout=30)
    return loop, runner, thread, port


def _stop(loop, runner, thread) -> None:
    asyncio.run_coroutine_threadsafe(runner.cleanup(), loop).result(timeout=30)
    loop.call_soon_threadsafe(loop.stop)
    thread.join(timeout=10)


def _app(config: BaseServiceConfig) -> tuple[aiohttp.web.Application, RequestCounter]:
    counter = RequestCounter()
    app = aiohttp.web.Application(middlewares=[make_auth_middleware(counter=counter)])
    app["config"] = config

    async def protected(request):
        # Echo the request context the middleware stamped.
        return aiohttp.web.json_response({"run_id": request.get("run_id") or ""})

    app.router.add_get("/v1/protected", protected)
    return app, counter


def _get(url: str, headers: dict | None = None) -> tuple[int, dict]:
    hdrs = {"X-TCSEXAM-Token-Id": TOKEN_ID, "X-TCSEXAM-Token-Secret": TOKEN_SECRET}
    hdrs.update(headers or {})
    req = urllib.request.Request(url, headers=hdrs, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


@pytest.fixture
def warn_service():
    config = BaseServiceConfig(token_id=TOKEN_ID, token_secret=TOKEN_SECRET)
    app, counter = _app(config)
    loop, runner, thread, port = _serve(app)
    yield types.SimpleNamespace(
        url=f"http://127.0.0.1:{port}", counter=counter, config=config
    )
    _stop(loop, runner, thread)


def test_warn_mode_valid_header_lands_in_request_context(warn_service) -> None:
    status, body = _get(f"{warn_service.url}/v1/protected", {RUN_ID_HEADER: RUN_ID})
    assert status == 200
    assert body["run_id"] == RUN_ID
    assert warn_service.counter.caller_snapshot() == [
        {"token_id": TOKEN_ID, "run_id": RUN_ID, "agent_name": "", "count": 1}
    ]


def test_warn_mode_missing_header_serves_and_throttles_warning(warn_service, caplog) -> None:
    with caplog.at_level(logging.WARNING, logger="tcsexam.backend.auth"):
        status, body = _get(f"{warn_service.url}/v1/protected")
        assert status == 200 and body["run_id"] == ""
        # Same (token, ip, path) within a minute: no second warning.
        status, _ = _get(f"{warn_service.url}/v1/protected")
        assert status == 200
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    text = warnings[0].getMessage()
    assert "missing" in text
    assert TOKEN_ID in text and "/v1/protected" in text
    assert "served normally" in text
    # Missing-header requests aggregate under the "" bucket.
    assert warn_service.counter.caller_snapshot() == [
        {"token_id": TOKEN_ID, "run_id": "", "agent_name": "", "count": 2}
    ]


def test_warn_mode_malformed_header_warns_and_treats_as_missing(warn_service, caplog) -> None:
    with caplog.at_level(logging.WARNING, logger="tcsexam.backend.auth"):
        status, body = _get(f"{warn_service.url}/v1/protected", {RUN_ID_HEADER: "x" * 200})
        assert status == 200 and body["run_id"] == ""
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "malformed" in warnings[0].getMessage()
    assert warn_service.counter.caller_snapshot() == [
        {"token_id": TOKEN_ID, "run_id": "", "agent_name": "", "count": 1}
    ]


def test_required_mode_rejects_missing_and_malformed() -> None:
    config = BaseServiceConfig(
        token_id=TOKEN_ID, token_secret=TOKEN_SECRET, run_id_mode="required"
    )
    app, _counter = _app(config)
    loop, runner, thread, port = _serve(app)
    url = f"http://127.0.0.1:{port}/v1/protected"
    try:
        status, body = _get(url)
        assert status == 400
        assert body == {"error": INVALID_RUN_ID_MESSAGE}
        status, _ = _get(url, {RUN_ID_HEADER: "x" * 129})
        assert status == 400
        status, body = _get(url, {RUN_ID_HEADER: "a" * 128})
        assert status == 200 and body["run_id"] == "a" * 128
    finally:
        _stop(loop, runner, thread)


def test_off_mode_does_not_read_the_header() -> None:
    config = BaseServiceConfig(
        token_id=TOKEN_ID, token_secret=TOKEN_SECRET, run_id_mode="off"
    )
    app, counter = _app(config)
    loop, runner, thread, port = _serve(app)
    url = f"http://127.0.0.1:{port}/v1/protected"
    try:
        status, body = _get(url, {RUN_ID_HEADER: RUN_ID})
        assert status == 200
        assert body["run_id"] == "", "off mode must not stamp the request context"
        assert counter.caller_snapshot() == [], "off mode must not feed caller counting"
    finally:
        _stop(loop, runner, thread)


def test_exempt_paths_skip_run_id_handling() -> None:
    config = BaseServiceConfig(
        token_id=TOKEN_ID, token_secret=TOKEN_SECRET, run_id_mode="required"
    )
    app, counter = _app(config)

    async def health(request):
        return aiohttp.web.json_response({"status": "ok"})

    app.router.add_get("/v1/health", health)
    loop, runner, thread, port = _serve(app)
    try:
        # No token, no run-id: the liveness probe is exempt from both gates.
        req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/health", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            assert resp.status == 200
        assert counter.caller_snapshot() == []
    finally:
        _stop(loop, runner, thread)


def test_probe_paths_do_not_feed_caller_counting() -> None:
    # /v1/status (the ops poll) is authenticated traffic but
    # is not *caller* traffic — it must not enter the callers table.
    async def status(request):
        return aiohttp.web.json_response({"ok": True})

    config = BaseServiceConfig(token_id=TOKEN_ID, token_secret=TOKEN_SECRET)
    app, counter = _app(config)
    app.router.add_get("/v1/status", status)
    loop, runner, thread, port = _serve(app)
    try:
        code, _ = _get(f"http://127.0.0.1:{port}/v1/status")
        assert code == 200
        assert counter.caller_snapshot() == [], "status poll must not be counted as a caller"
        # A real caller path on the same service is still counted.
        code, _ = _get(f"http://127.0.0.1:{port}/v1/protected", {RUN_ID_HEADER: RUN_ID})
        assert code == 200
        assert counter.caller_snapshot() == [
            {"token_id": TOKEN_ID, "run_id": RUN_ID, "agent_name": "", "count": 1}
        ]
    finally:
        _stop(loop, runner, thread)


def test_unknown_run_id_mode_falls_back_to_warn(warn_service, caplog) -> None:
    warn_service.config.run_id_mode = "bogus"  # create_app rejects this at startup
    with caplog.at_level(logging.WARNING, logger="tcsexam.backend.auth"):
        status, body = _get(f"{warn_service.url}/v1/protected")
    assert status == 200 and body["run_id"] == ""
    assert any(r.levelno == logging.WARNING for r in caplog.records)


# --------------------------------------------------------------------------- #
# Adapter tagging passthrough (unit level)
# --------------------------------------------------------------------------- #
class _KwFactory:
    """Records the _create_worker keyword arguments."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return types.SimpleNamespace()


class _TaggingAdapter(BasePlatformAdapter):
    def __init__(self, factory) -> None:
        super().__init__(create_retries=0, ready_timeout_seconds=30.0)
        self.factory = factory

    async def _create_worker(self, profile, image_url, **kwargs):
        return await self.factory(profile=profile, image_url=image_url, **kwargs)


def _adapter(factory) -> _TaggingAdapter:
    return _TaggingAdapter(factory)


def test_create_sandbox_passes_group_name_and_labels() -> None:
    factory = _KwFactory()
    asyncio.run(
        _adapter(factory).create_sandbox(
            "p", "img", group_name="grp--run-1", labels={"run_id": "run-1", "token_id": "tcsexam"}
        )
    )
    call = factory.calls[0]
    assert call["group_name"] == "grp--run-1"
    assert call["labels"] == {"run_id": "run-1", "token_id": "tcsexam"}


def test_create_sandbox_without_tagging_passes_none() -> None:
    """No run-id: the fixed _create_worker signature still receives
    group_name/labels — as None (never silently dropped)."""
    factory = _KwFactory()
    asyncio.run(_adapter(factory).create_sandbox("p", "img"))
    call = factory.calls[0]
    assert call["group_name"] is None
    assert call["labels"] is None


# --------------------------------------------------------------------------- #
# Store-level session/worker tagging (the single-worker base store)
# --------------------------------------------------------------------------- #
class _StoreFakeCtrl:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    async def write_bytes(self, path: str, data: bytes, parents: bool = False) -> None:
        self.files[path] = data

    async def read_text(self, path: str) -> str:
        return self.files.get(path, b"").decode()

    async def run(self, args, **kwargs):
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")


class _StoreFakeWorker:
    def __init__(self) -> None:
        self.ctrl = _StoreFakeCtrl()

    async def delete(self) -> None:
        pass


class _StoreFakeExecutor:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.registered: dict = {}

    async def create_sandbox(self, profile, image, *, ttl_seconds=None, spec=None, **kwargs):
        self.calls.append(
            {"profile": profile, "image": image, "ttl_seconds": ttl_seconds, "spec": spec, **kwargs}
        )
        return _StoreFakeWorker()

    def register_long_lived(self, app_name: str, sandbox) -> None:
        self.registered[app_name] = sandbox

    async def stop_app(self, app_name: str) -> None:
        self.registered.pop(app_name, None)


class _StoreFakeTunnels:
    def __init__(self) -> None:
        self.session_tokens: dict[str, str] = {}
        self.closed: set[str] = set()

    async def wait_connected(self, app_name: str, timeout: float) -> bool:
        return app_name not in self.closed

    def is_connected(self, app_name: str) -> bool:
        return app_name not in self.closed

    async def close(self, app_name: str) -> None:
        self.closed.add(app_name)
        self.session_tokens.pop(app_name, None)


def _store(worker_group: str = "") -> tuple[JudgeSessionStore, _StoreFakeExecutor]:
    executor = _StoreFakeExecutor()
    service_config = BaseServiceConfig(
        host="127.0.0.1", port=8420, advertise_host="127.0.0.1",
        token_id=TOKEN_ID, token_secret=TOKEN_SECRET,
    )
    # The base store reads the worker-group tagging prefix off the service
    # config (load_config fills it from TCSEXAM_WORKER_GROUP / the YAML key).
    service_config.worker_group = worker_group
    store = JudgeSessionStore(executor, JudgeSessionsConfig(), service_config)
    store.attach_tunnels(_StoreFakeTunnels())
    return store, executor


KEY = (TOKEN_ID, "registry.example.com/family-judge:1.0.0", "client-1")


def test_store_create_tags_worker_with_run_id() -> None:
    async def main() -> None:
        store, executor = _store(worker_group="svc-group")
        session = await store.create_shared(
            KEY, KEY[1], None, None, None, run_id=RUN_ID, token_id=TOKEN_ID
        )
        call = executor.calls[0]
        assert call["labels"] == {"run_id": RUN_ID, "token_id": TOKEN_ID}
        assert call["group_name"] == f"svc-group--{RUN_ID}"
        assert session.run_id == RUN_ID
        assert session.token_id == TOKEN_ID

    asyncio.run(main())


def test_store_create_without_run_id_keeps_untagged_call_shape() -> None:
    async def main() -> None:
        store, executor = _store(worker_group="svc-group")
        session = await store.create_shared(KEY, KEY[1], None, None, None)
        call = executor.calls[0]
        assert "labels" not in call, "no run-id: the creation call carries no tagging"
        assert "group_name" not in call
        assert session.run_id == ""
        assert session.token_id == ""

    asyncio.run(main())


def test_store_create_group_override_needs_default_group() -> None:
    async def main() -> None:
        store, executor = _store(worker_group="")  # no configured group prefix
        await store.create_shared(KEY, KEY[1], None, None, None, run_id=RUN_ID)
        call = executor.calls[0]
        assert call["labels"] == {"run_id": RUN_ID, "token_id": "-"}
        assert "group_name" not in call, "no configured worker group: labels only"

    asyncio.run(main())


# --------------------------------------------------------------------------- #
# Callers aggregation (StatusCollector level)
# --------------------------------------------------------------------------- #
class _AggSession:
    def __init__(self, image: str, run_id: str, token_id: str) -> None:
        self.image = image
        self.run_id = run_id
        self.token_id = token_id


class _LegacySession:
    """Pre-identity-layer shape: no run_id/token_id attributes."""

    def __init__(self, image: str) -> None:
        self.image = image


class _AggStore:
    def __init__(self, sessions) -> None:
        self._sessions = sessions

    def live_sessions(self):
        return list(self._sessions)


def _collector(sessions, counter) -> StatusCollector:
    return StatusCollector(
        config=BaseServiceConfig(service_name="tcsexam-backend"),
        sessions_store=_AggStore(sessions),
        request_counter=counter,
    )


def test_callers_merge_sessions_and_requests() -> None:
    sessions = [
        _AggSession("reg/a-judge:1", RUN_ID, TOKEN_ID),
        _AggSession("reg/a-judge:1", RUN_ID, TOKEN_ID),
        _AggSession("reg/b-judge:1", "knn-v2-opus-20260827-03", TOKEN_ID),
        _AggSession("reg/c-judge:1", "", TOKEN_ID),  # header-less session
        _LegacySession("reg/d-judge:1"),  # pre-identity shape: not listed
    ]
    counter = RequestCounter()
    for _ in range(5):
        counter.record_caller(TOKEN_ID, RUN_ID)
    for _ in range(3):
        counter.record_caller(TOKEN_ID, "")
    counter.record_caller(TOKEN_ID, "knn-v2-opus-20260827-03", "kimi-code")
    counter.record_caller("-", "")  # a 401 storm request

    callers = _collector(sessions, counter).snapshot()["callers"]
    by_key = {(c["token_id"], c["run_id"], c["agent_name"]): c for c in callers}
    assert by_key[(TOKEN_ID, RUN_ID, "")] == {
        "token_id": TOKEN_ID,
        "run_id": RUN_ID,
        "agent_name": "",
        "sessions": 2,
        "requests_300s": 5,
    }
    # The session carries no agent_name: request and session only merge when
    # all three dimensions match (the request here declared an agent).
    assert by_key[(TOKEN_ID, "knn-v2-opus-20260827-03", "kimi-code")]["requests_300s"] == 1
    assert by_key[(TOKEN_ID, "knn-v2-opus-20260827-03", "")]["sessions"] == 1
    # The "" bucket merges header-less sessions and requests (missing values
    # are "").
    assert by_key[(TOKEN_ID, "", "")]["sessions"] == 1
    assert by_key[(TOKEN_ID, "", "")]["requests_300s"] == 3
    assert by_key[("-", "", "")]["requests_300s"] == 1
    # The legacy-shaped session is nowhere to be found.
    assert all(c["sessions"] != 0 or c["requests_300s"] != 0 for c in callers)
    assert sum(c["sessions"] for c in callers) == 4
    # Sort order: requests_300s desc first.
    assert callers[0]["run_id"] == RUN_ID


def test_caller_snapshot_top_n_and_tie_break() -> None:
    counter = RequestCounter()
    for i in range(25):  # beyond the Top-20 cap
        for _ in range(i + 1):
            counter.record_caller(TOKEN_ID, f"run-{i:02d}")
    snap = counter.caller_snapshot()
    assert len(snap) == 20
    assert snap[0] == {"token_id": TOKEN_ID, "run_id": "run-24", "agent_name": "", "count": 25}
    counts = [c["count"] for c in snap]
    assert counts == sorted(counts, reverse=True)


def test_caller_snapshot_prunes_beyond_window() -> None:
    clock_holder = {"t": 1000.0}
    counter = RequestCounter(now=lambda: clock_holder["t"])
    counter.record_caller(TOKEN_ID, RUN_ID)
    clock_holder["t"] += 301
    counter.record_caller(TOKEN_ID, RUN_ID)
    assert counter.caller_snapshot() == [
        {"token_id": TOKEN_ID, "run_id": RUN_ID, "agent_name": "", "count": 1}
    ]


# --------------------------------------------------------------------------- #
# End to end over the live service (fake adapter, jservice fixture)
# --------------------------------------------------------------------------- #
def _post_session(handle, headers: dict | None = None) -> tuple[int, dict]:
    hdrs = {
        "Content-Type": "application/json",
        "X-TCSEXAM-Token-Id": TOKEN_ID,
        "X-TCSEXAM-Token-Secret": TOKEN_SECRET,
        "X-TCSEXAM-Archive-Token": ARCHIVE_TOKEN,
    }
    hdrs.update(headers or {})
    req = urllib.request.Request(
        f"{handle.url}/v1/judge/sessions",
        data=json.dumps({"judge_image": "registry.example.com/family-judge:1.0.0"}).encode(),
        headers=hdrs,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def _get_json(url: str, headers: dict | None = None) -> tuple[int, dict]:
    hdrs = {"X-TCSEXAM-Token-Id": TOKEN_ID, "X-TCSEXAM-Token-Secret": TOKEN_SECRET}
    hdrs.update(headers or {})
    req = urllib.request.Request(url, headers=hdrs, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_end_to_end_run_id_counted_in_callers(jservice) -> None:
    """Over the wired (sharded) service: the run-id is validated by the
    middleware and feeds the /v1/status callers table; the sharded session
    carries its caller identity, so its row merges into the run's bucket
    (sessions: 1)."""
    status, created = _post_session(jservice, {RUN_ID_HEADER: RUN_ID})
    assert status == 202, created
    sid = created["session_id"]
    wait_session_ready(jservice, sid)

    status, info = _get_json(
        f"{jservice.url}/v1/judge/sessions/{sid}", {RUN_ID_HEADER: RUN_ID}
    )
    assert status == 200

    # /v1/status callers: the run is visible with its requests.
    status, snap = _get_json(f"{jservice.url}/v1/status")
    assert status == 200
    by_key = {(c["token_id"], c["run_id"], c["agent_name"]): c for c in snap["callers"]}
    entry = by_key[(TOKEN_ID, RUN_ID, "")]
    assert entry["sessions"] == 1
    assert entry["requests_300s"] == 2  # the create + the session status read
    # The agent's tunnel WS connect carries no run-id: the "" bucket stays
    # visible alongside adopted traffic.
    assert (TOKEN_ID, "", "") in by_key


def test_end_to_end_without_run_id_stays_in_the_empty_bucket(jservice) -> None:
    status, created = _post_session(jservice)
    assert status == 202, created
    wait_session_ready(jservice, created["session_id"])

    status, snap = _get_json(f"{jservice.url}/v1/status")
    assert status == 200
    assert all(c["run_id"] == "" for c in snap["callers"])
