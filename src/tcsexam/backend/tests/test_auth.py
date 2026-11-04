"""Auth middleware tests: exempt predicates, disabled-when-no-token, the
exact 401 body. Exercised over real HTTP against a minimal app.
"""
from __future__ import annotations

import asyncio
import json
import threading
import urllib.error
import urllib.request

import pytest

import aiohttp.web  # noqa: E402

from tcsexam.backend.auth import (
    UNAUTHORIZED_MESSAGE,
    health_and_apps,
    health_only,
    make_auth_middleware,
)
from tcsexam.backend.config import BaseServiceConfig

TOKEN_ID = "test-token-id"
TOKEN_SECRET = "test-token-secret"


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


def _status(url: str, *, auth: bool = True, secret: str = TOKEN_SECRET) -> int:
    headers = {}
    if auth:
        headers["X-TCSEXAM-Token-Id"] = TOKEN_ID
        headers["X-TCSEXAM-Token-Secret"] = secret
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code


def _app(config: BaseServiceConfig, exempt) -> aiohttp.web.Application:
    app = aiohttp.web.Application(middlewares=[make_auth_middleware(exempt)])
    app["config"] = config

    async def health(request):
        return aiohttp.web.json_response({"status": "ok"})

    async def protected(request):
        return aiohttp.web.json_response({"status": "protected"})

    async def apps_proxy(request):
        return aiohttp.web.json_response({"status": "proxied"})

    app.router.add_get("/v1/health", health)
    app.router.add_get("/v1/protected", protected)
    app.router.add_route("*", "/apps/{app_name}/{tail:.*}", apps_proxy)
    return app


@pytest.fixture
def service():
    config = BaseServiceConfig(token_id=TOKEN_ID, token_secret=TOKEN_SECRET)
    loop, runner, thread, port = _serve(_app(config, health_and_apps))
    yield f"http://127.0.0.1:{port}"
    _stop(loop, runner, thread)


def test_health_is_exempt(service) -> None:
    assert _status(f"{service}/v1/health", auth=False) == 200


def test_missing_token_is_401(service) -> None:
    assert _status(f"{service}/v1/protected", auth=False) == 401


def test_wrong_secret_is_401(service) -> None:
    assert _status(f"{service}/v1/protected", secret="nope") == 401


def test_valid_token_passes(service) -> None:
    assert _status(f"{service}/v1/protected") == 200


def test_apps_proxy_exempt_under_health_and_apps(service) -> None:
    assert _status(f"{service}/apps/some-app/health", auth=False) == 200


def test_401_body_wording(service) -> None:
    req = urllib.request.Request(f"{service}/v1/protected", method="GET")
    try:
        urllib.request.urlopen(req, timeout=10)
        raise AssertionError("expected a 401")
    except urllib.error.HTTPError as exc:
        assert exc.code == 401
        assert json.loads(exc.read()) == {"error": UNAUTHORIZED_MESSAGE}


def test_health_only_shape_blocks_apps() -> None:
    config = BaseServiceConfig(token_id=TOKEN_ID, token_secret=TOKEN_SECRET)
    loop, runner, thread, port = _serve(_app(config, health_only))
    try:
        assert _status(f"http://127.0.0.1:{port}/apps/some-app/health", auth=False) == 401
        assert _status(f"http://127.0.0.1:{port}/v1/health", auth=False) == 200
    finally:
        _stop(loop, runner, thread)


def test_no_token_configured_disables_auth() -> None:
    config = BaseServiceConfig()  # no token_id/secret
    loop, runner, thread, port = _serve(_app(config, health_only))
    try:
        assert _status(f"http://127.0.0.1:{port}/v1/protected", auth=False) == 200
    finally:
        _stop(loop, runner, thread)


def _status_pair(url: str, token_id: str, token_secret: str) -> int:
    req = urllib.request.Request(
        url,
        headers={"X-TCSEXAM-Token-Id": token_id, "X-TCSEXAM-Token-Secret": token_secret},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code


def test_additional_tokens_accepted_during_rotation() -> None:
    """Rotation window: the primary pair AND every additional pair
    pass; anything else still 401s."""
    config = BaseServiceConfig(
        token_id="new-id",
        token_secret="new-secret",
        additional_tokens=[(TOKEN_ID, TOKEN_SECRET), ("old2-id", "old2-secret")],
    )
    loop, runner, thread, port = _serve(_app(config, health_and_apps))
    base = f"http://127.0.0.1:{port}"
    try:
        assert _status_pair(f"{base}/v1/protected", "new-id", "new-secret") == 200
        assert _status_pair(f"{base}/v1/protected", TOKEN_ID, TOKEN_SECRET) == 200
        assert _status_pair(f"{base}/v1/protected", "old2-id", "old2-secret") == 200
        assert _status_pair(f"{base}/v1/protected", "new-id", "nope") == 401
        assert _status_pair(f"{base}/v1/protected", "old2-id", "new-secret") == 401  # mismatched pair
    finally:
        _stop(loop, runner, thread)


def test_additional_tokens_id_must_match_pair() -> None:
    """The window pair is an (id, secret) pair — a valid secret with the
    wrong id is still a 401."""
    config = BaseServiceConfig(
        token_id="new-id",
        token_secret="new-secret",
        additional_tokens=[("legacy-id", "legacy-secret")],
    )
    loop, runner, thread, port = _serve(_app(config, health_and_apps))
    base = f"http://127.0.0.1:{port}"
    try:
        assert _status(f"{base}/v1/protected", secret="legacy-secret") == 401  # id mismatch
    finally:
        _stop(loop, runner, thread)
